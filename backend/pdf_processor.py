"""PDF processing module - extracts text and creates chunks."""
import json
import re
from pathlib import Path
from typing import List, Dict
import fitz  # PyMuPDF


def clean_text(text: str) -> str:
    """
    Clean extracted text.
    
    Args:
        text: Raw text from PDF
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove page numbers and headers/footers (common patterns)
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\d+\s*/\s*\d+', '', text)  # Remove "1/10" style page numbers
    
    # Normalize unicode
    text = text.replace('\u2019', "'")  # Right single quotation mark
    text = text.replace('\u201c', '"')  # Left double quotation mark
    text = text.replace('\u201d', '"')  # Right double quotation mark
    text = text.replace('\u2013', '-')  # En dash
    text = text.replace('\u2014', '--')  # Em dash
    
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Target size for each chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                last_punct = text.rfind(punct, start, end)
                if last_punct != -1:
                    end = last_punct + len(punct)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start forward with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def process_pdf(pdf_path: Path, output_dir: Path) -> Dict:
    """
    Process a PDF file and create JSONL chunks.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save JSONL chunks
    
    Returns:
        Dictionary with processing results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get PDF filename without extension
    pdf_name = pdf_path.stem
    output_file = output_dir / f"{pdf_name}.jsonl"
    
    chunks_created = 0
    pages_processed = 0
    
    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        print(f"[PDF] Processing {pdf_name}: {total_pages} pages")
        
        # Process each page
        for page_num in range(total_pages):
            page = doc[page_num]
            
            # Extract text
            text = page.get_text()
            
            if not text or len(text.strip()) < 50:  # Skip pages with too little text
                continue
            
            # Clean text
            cleaned_text = clean_text(text)
            
            if not cleaned_text:
                continue
            
            # Create chunks from page
            page_chunks = chunk_text(cleaned_text, chunk_size=1000, overlap=200)
            
            # Write chunks to JSONL
            with open(output_file, 'a', encoding='utf-8') as f:
                for chunk_content in page_chunks:
                    chunk_data = {
                        "source": pdf_path.name,
                        "page": page_num + 1,
                        "text": chunk_content
                    }
                    f.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')
                    chunks_created += 1
            
            pages_processed += 1
        
        doc.close()
        
        print(f"[PDF] Completed: {chunks_created} chunks from {pages_processed} pages")
        
        return {
            "success": True,
            "filename": pdf_path.name,
            "chunks_created": chunks_created,
            "pages_processed": pages_processed,
            "total_pages": total_pages,
            "output_file": str(output_file)
        }
    
    except Exception as e:
        print(f"[ERROR] Failed to process PDF {pdf_name}: {e}")
        return {
            "success": False,
            "filename": pdf_path.name,
            "error": str(e)
        }


def process_uploaded_pdf(file_content: bytes, filename: str, output_dir: Path) -> Dict:
    """
    Process an uploaded PDF file.
    
    Args:
        file_content: PDF file content as bytes
        filename: Original filename
        output_dir: Directory to save JSONL chunks
    
    Returns:
        Dictionary with processing results
    """
    import tempfile
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(file_content)
        tmp_path = Path(tmp_file.name)
    
    try:
        # Process the PDF
        result = process_pdf(tmp_path, output_dir)
        
        # Clean up temp file
        tmp_path.unlink()
        
        return result
    
    except Exception as e:
        # Clean up temp file on error
        if tmp_path.exists():
            tmp_path.unlink()
        return {
            "success": False,
            "filename": filename,
            "error": str(e)
        }

