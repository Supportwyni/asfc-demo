"""Upload existing PDF files and chunks to Supabase database."""
import sys
import json
import base64
import os
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.client import get_client
from backend.database.repository import PDFRepository, ChunkRepository
from backend.database.models import PDFDocument, Chunk
from backend.database.config import SUPABASE_URL, SUPABASE_KEY
from backend.config import CHUNK_DIR
from backend.rag import query_openrouter
from datetime import datetime


def find_pdf_files(pdf_dir: Path) -> List[Path]:
    """Find all PDF files in directory."""
    pdf_files = list(pdf_dir.glob("*.pdf"))
    return pdf_files


def read_chunk_file(chunk_file: Path) -> List[Dict]:
    """Read chunks from JSONL file."""
    chunks = []
    if not chunk_file.exists():
        return chunks
    
    with open(chunk_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"[WARNING] Failed to parse chunk: {e}")
    return chunks


def get_llm_analysis(chunks: List[Dict]) -> Optional[Dict]:
    """Get LLM analysis for document."""
    if not chunks:
        return None
    
    try:
        # Get first few chunks for analysis
        sample_text = "\n\n".join([chunk.get('text', '')[:500] for chunk in chunks[:3]])
        
        messages = [
            {
                "role": "system",
                "content": "You are a document analysis assistant. Analyze the provided document content and return a JSON summary."
            },
            {
                "role": "user",
                "content": f"""Analyze this document excerpt and provide a JSON summary with:
- title: Document title
- summary: Brief summary (2-3 sentences)
- topics: Array of main topics
- key_points: Array of 3-5 key points

Document excerpt:
{sample_text[:2000]}

Return ONLY valid JSON, no markdown formatting."""
            }
        ]
        
        llm_response = query_openrouter(messages)
        if llm_response:
            # Try to extract JSON
            try:
                cleaned = llm_response.strip()
                if cleaned.startswith('```'):
                    cleaned = cleaned.split('```')[1]
                    if cleaned.startswith('json'):
                        cleaned = cleaned[4:]
                cleaned = cleaned.strip()
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return {"raw_analysis": llm_response}
    except Exception as e:
        print(f"[WARNING] LLM analysis failed: {e}")
        return None
    
    return None


def upload_pdf_and_chunks(pdf_file: Path, chunk_file: Path, pdf_dir: Path) -> bool:
    """Upload a single PDF file and its chunks to database."""
    filename = pdf_file.name
    
    print(f"\n{'='*60}")
    print(f"Processing: {filename}")
    print(f"{'='*60}")
    
    # Step 1: Read PDF file content
    print(f"[1] Reading PDF file...")
    try:
        with open(pdf_file, 'rb') as f:
            pdf_content = f.read()
        file_size = len(pdf_content)
        print(f"    [OK] Read {file_size:,} bytes")
    except Exception as e:
        print(f"    [ERROR] Failed to read PDF: {e}")
        return False
    
    # Step 2: Read chunks
    print(f"[2] Reading chunks from {chunk_file.name}...")
    chunks_data = read_chunk_file(chunk_file)
    if not chunks_data:
        print(f"    [ERROR] No chunks found in {chunk_file.name}")
        return False
    print(f"    [OK] Found {len(chunks_data)} chunks")
    
    # Step 3: Check if PDF already exists in database
    print(f"[3] Checking if PDF already exists in database...")
    document_id = None
    try:
        existing = PDFRepository.get_by_filename(filename)
        if existing:
            print(f"    [WARNING] PDF already exists (ID: {existing.get('id')})")
            print(f"    [INFO] Will update existing record")
            document_id = existing.get('id')
    except Exception as e:
        error_msg = str(e).lower()
        if "getaddrinfo" in error_msg or "11001" in error_msg or "connect" in error_msg:
            print(f"    [WARNING] Cannot connect to Supabase - will create new record")
            print(f"    [INFO] Make sure Supabase project is active and URL is correct")
        else:
            print(f"    [WARNING] Could not check existing records: {e}")
        document_id = None
    
    # Step 4: Get LLM analysis
    print(f"[4] Getting LLM analysis...")
    llm_metadata = get_llm_analysis(chunks_data)
    if llm_metadata:
        print(f"    [OK] LLM analysis completed: {llm_metadata.get('title', 'N/A')}")
    else:
        print(f"    [WARNING] LLM analysis skipped or failed")
    
    # Step 5: Create/Update PDF document record
    print(f"[5] Saving PDF to database...")
    try:
        # Count pages (estimate from chunks)
        pages = set()
        for chunk in chunks_data:
            pages.add(chunk.get('page', 0))
        pages_count = len(pages) if pages else 1
        
        if document_id is None:
            # Create new record
            pdf_doc = PDFDocument(
                filename=filename,
                file_size=file_size,
                status="processed",
                chunks_count=len(chunks_data),
                pages_count=pages_count,
                file_content=pdf_content,
                metadata=llm_metadata
            )
            db_record = PDFRepository.create(pdf_doc)
            document_id = db_record.get('id')
            print(f"    [OK] Created PDF record (ID: {document_id})")
        else:
            # Update existing record
            PDFRepository.update_status(
                filename, 
                "processed",
                chunks_count=len(chunks_data),
                pages_count=pages_count
            )
            if llm_metadata:
                PDFRepository.update_metadata(filename, llm_metadata)
            print(f"    [OK] Updated PDF record (ID: {document_id})")
    except Exception as e:
        print(f"    [ERROR] Failed to save PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Upload chunks
    print(f"[6] Uploading {len(chunks_data)} chunks to database...")
    try:
        db_chunks = []
        for idx, chunk_data in enumerate(chunks_data):
            chunk = Chunk(
                document_id=document_id,
                source=chunk_data.get('source', filename),
                page=chunk_data.get('page', 0),
                text=chunk_data.get('text', ''),
                chunk_index=idx
            )
            db_chunks.append(chunk)
        
        if db_chunks:
            # Check if chunks already exist
            try:
                existing_chunks = ChunkRepository.get_by_source(filename)
                if existing_chunks:
                    print(f"    ⚠ Found {len(existing_chunks)} existing chunks")
                    response = input("    Delete existing chunks and re-upload? (y/n): ").strip().lower()
                    if response == 'y':
                        # Delete existing chunks
                        client = get_client()
                        client.table("chunks").delete().eq("source", filename).execute()
                        print(f"    [OK] Deleted existing chunks")
                    else:
                        print(f"    [WARNING] Keeping existing chunks, skipping upload")
                        return True
            except Exception as e:
                print(f"    [WARNING] Could not check existing chunks: {e}")
            
            ChunkRepository.create_batch(db_chunks)
            print(f"    [OK] Uploaded {len(db_chunks)} chunks")
    except Exception as e:
        print(f"    [ERROR] Failed to upload chunks: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n[SUCCESS] {filename} uploaded successfully!")
    print(f"    - PDF file: {file_size:,} bytes")
    print(f"    - Chunks: {len(chunks_data)}")
    print(f"    - Pages: {pages_count}")
    print(f"    - Document ID: {document_id}")
    
    return True


def main():
    """Main function to upload all existing PDFs and chunks."""
    print("=" * 60)
    print("Upload Existing PDFs and Chunks to Database")
    print("=" * 60)
    
    # Check for batch mode (skip prompts)
    batch_mode = os.getenv("BATCH_MODE", "false").lower() == "true" or "--batch" in sys.argv
    if batch_mode:
        print("[INFO] Running in BATCH MODE - will upload all files without prompts")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return False
    
    # Find PDF directory
    pdf_dir = project_root / "pdf"
    if not pdf_dir.exists():
        pdf_dir = project_root / "pdfs"
    if not pdf_dir.exists():
        pdf_dir = project_root / "data"
    
    print(f"\n[INFO] Looking for PDFs in: {pdf_dir}")
    pdf_files = find_pdf_files(pdf_dir)
    
    if not pdf_files:
        print(f"[ERROR] No PDF files found in {pdf_dir}")
        print(f"[INFO] Please place PDF files in: {pdf_dir}")
        return False
    
    print(f"[INFO] Found {len(pdf_files)} PDF file(s)")
    
    # Process each PDF
    success_count = 0
    failed_count = 0
    
    for pdf_file in pdf_files:
        # Find corresponding chunk file
        chunk_filename = pdf_file.stem + ".jsonl"
        chunk_file = CHUNK_DIR / chunk_filename
        
        if not chunk_file.exists():
            print(f"\n[WARNING] No chunk file found for {pdf_file.name}")
            print(f"    Expected: {chunk_file}")
            response = input("    Skip this PDF? (y/n): ").strip().lower()
            if response == 'y':
                continue
            else:
                print("    You can process it later through the admin panel")
                continue
        
        if upload_pdf_and_chunks(pdf_file, chunk_file, pdf_dir):
            success_count += 1
        else:
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Upload Summary")
    print("=" * 60)
    print(f"Successfully uploaded: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Total processed: {success_count + failed_count}")
    
    return success_count > 0


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Upload cancelled by user")
        sys.exit(1)

