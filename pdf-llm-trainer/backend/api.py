"""Flask API server for frontend."""
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sys
import os
from pathlib import Path
import base64

from backend.rag import ask_with_rag, query_openrouter
from backend.pdf_processor import process_uploaded_pdf
from backend.config import CHUNK_DIR
from backend.database.repository import PDFRepository, ChunkRepository
from backend.database.models import PDFDocument, Chunk
from datetime import datetime
import json

app = Flask(__name__)
# Enable CORS for all routes and origins
# Allow all origins in production, or specify your Vercel domain
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5273,http://localhost:3000,http://127.0.0.1:5273,http://127.0.0.1:3000").split(",")
CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration for file uploads
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    try:
        data = request.json
        question = data.get('question', '')
        
        if not question:
            print("[ERROR] Empty question received")
            return jsonify({'error': 'Question is required'}), 400
        
        print(f"[REQUEST] Question: {question[:100]}...")
        response = ask_with_rag(question)
        print(f"[SUCCESS] Response generated ({len(response)} chars)")
        
        return jsonify({
            'response': response,
            'success': True
        })
    
    except Exception as e:
        print(f"[ERROR] Exception in /api/chat: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """Handle PDF upload and processing."""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only PDF files are allowed.'
            }), 400
        
        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024}MB'
            }), 400
        
        # Secure filename
        filename = secure_filename(file.filename)
        
        print(f"[UPLOAD] Processing uploaded PDF: {filename}")
        
        # Step 1: Upload PDF file and metadata to database
        # TEMPORARY: Storing PDF file content in database for manual transfer
        print(f"[UPLOAD] Step 1: Saving PDF file and metadata to database...")
        pdf_doc = PDFDocument(
            filename=filename,
            file_size=file_size,
            status="processing",
            chunks_count=0,
            pages_count=0,
            file_content=file_content  # TEMPORARY: Store the actual PDF file content
        )
        
        try:
            db_record = PDFRepository.create(pdf_doc)
            document_id = db_record.get('id')
            print(f"[UPLOAD] PDF saved to database with ID: {document_id}")
        except Exception as e:
            print(f"[WARNING] Failed to save to database: {e}")
            document_id = None
        
        # Step 2: Process PDF to create chunks
        print(f"[UPLOAD] Step 2: Processing PDF and creating chunks...")
        result = process_uploaded_pdf(file_content, filename, CHUNK_DIR)
        
        if not result['success']:
            if document_id:
                PDFRepository.update_status(filename, "error")
            return jsonify(result), 500
        
        # Step 3: Process with OpenRouter LLM to generate summary/metadata
        print(f"[UPLOAD] Step 3: Processing with OpenRouter LLM...")
        llm_result = None
        try:
            # Read first few chunks to get content summary
            chunk_file = CHUNK_DIR / f"{filename.rsplit('.', 1)[0]}.jsonl"
            sample_chunks = []
            if chunk_file.exists():
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i < 3 and line.strip():  # Get first 3 chunks
                            sample_chunks.append(json.loads(line))
            
            if sample_chunks:
                # Create prompt for OpenRouter
                sample_text = "\n\n".join([chunk.get('text', '')[:500] for chunk in sample_chunks])
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
                    # Try to extract JSON from response
                    try:
                        # Remove markdown code blocks if present
                        cleaned = llm_response.strip()
                        if cleaned.startswith('```'):
                            cleaned = cleaned.split('```')[1]
                            if cleaned.startswith('json'):
                                cleaned = cleaned[4:]
                        cleaned = cleaned.strip()
                        llm_result = json.loads(cleaned)
                        print(f"[UPLOAD] LLM analysis completed: {llm_result.get('title', 'N/A')}")
                    except json.JSONDecodeError:
                        # If not JSON, store as text
                        llm_result = {"raw_analysis": llm_response}
                        print(f"[UPLOAD] LLM analysis completed (raw text)")
        except Exception as e:
            print(f"[WARNING] LLM processing failed: {e}")
            llm_result = None
        
        # Step 4: Save chunks to database
        print(f"[UPLOAD] Step 4: Saving chunks to database...")
        chunks_saved = 0
        if chunk_file.exists() and document_id:
            try:
                db_chunks = []
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    for idx, line in enumerate(f):
                        if line.strip():
                            chunk_data = json.loads(line)
                            chunk = Chunk(
                                document_id=document_id,
                                source=chunk_data.get('source', filename),
                                page=chunk_data.get('page', 0),
                                text=chunk_data.get('text', ''),
                                chunk_index=idx
                            )
                            db_chunks.append(chunk)
                
                if db_chunks:
                    ChunkRepository.create_batch(db_chunks)
                    chunks_saved = len(db_chunks)
                    print(f"[UPLOAD] Saved {chunks_saved} chunks to database")
            except Exception as e:
                print(f"[WARNING] Failed to save chunks to database: {e}")
        
        # Step 5: Update PDF document with final status and LLM result
        if document_id:
            try:
                PDFRepository.update_status(filename, "processed", 
                                          chunks_count=result['chunks_created'],
                                          pages_count=result['pages_processed'])
                if llm_result:
                    PDFRepository.update_metadata(filename, llm_result)
                print(f"[UPLOAD] Updated database record with LLM analysis")
            except Exception as e:
                print(f"[WARNING] Failed to update database: {e}")
        
        result['file_size'] = file_size
        result['document_id'] = document_id
        result['llm_analysis'] = llm_result
        result['chunks_saved_to_db'] = chunks_saved
        
        print(f"[UPLOAD] Successfully completed: {result['chunks_created']} chunks from {result['pages_processed']} pages")
        return jsonify(result)
    
    except Exception as e:
        print(f"[ERROR] Exception in /api/upload: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files', methods=['GET'])
def list_files():
    """List all uploaded PDF files from database."""
    try:
        # Try to get files from database first
        try:
            db_files = PDFRepository.list_all(limit=100)
            
            files = []
            for db_file in db_files:
                # Parse uploaded_at if it's a string
                uploaded_at = db_file.get('uploaded_at')
                if isinstance(uploaded_at, str):
                    try:
                        uploaded_at = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                    except:
                        uploaded_at = datetime.now()
                
                files.append({
                    'id': db_file.get('id'),
                    'filename': db_file.get('filename', 'unknown'),
                    'chunks_count': db_file.get('chunks_count', 0),
                    'pages_count': db_file.get('pages_count', 0),
                    'uploaded_at': uploaded_at.isoformat() if isinstance(uploaded_at, datetime) else str(uploaded_at),
                    'status': db_file.get('status', 'unknown'),
                    'file_size': db_file.get('file_size', 0),
                    'metadata': db_file.get('metadata', {}),
                    'source': db_file.get('filename', 'unknown')
                })
            
            # Sort by upload time (newest first)
            files.sort(key=lambda x: x['uploaded_at'], reverse=True)
            
            return jsonify({
                'success': True,
                'files': files,
                'total': len(files)
            })
        except Exception as db_error:
            print(f"[WARNING] Database query failed, falling back to file system: {db_error}")
            # Fallback to file system if database fails
            import json
            from datetime import datetime

            files = []
            chunk_files = list(CHUNK_DIR.glob("*.jsonl"))

            for chunk_file in chunk_files:
                try:
                    # Get file info
                    pdf_name = chunk_file.stem
                    file_path = chunk_file

                    # Count chunks and get metadata
                    chunks_count = 0
                    pages = set()
                    first_chunk = None

                    with open(chunk_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                chunks_count += 1
                                chunk_data = json.loads(line)
                                if first_chunk is None:
                                    first_chunk = chunk_data
                                pages.add(chunk_data.get('page', 0))

                    # Get file modification time
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)

                    files.append({
                        'id': None,
                        'filename': pdf_name,
                        'chunks_count': chunks_count,
                        'pages_count': len(pages),
                        'uploaded_at': mod_time.isoformat(),
                        'status': 'processed',
                        'file_size': 0,
                        'metadata': {},
                        'source': first_chunk.get('source', pdf_name) if first_chunk else pdf_name
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to process file {chunk_file.name}: {e}")
                    continue

            # Sort by upload time (newest first)
            files.sort(key=lambda x: x['uploaded_at'], reverse=True)

            return jsonify({
                'success': True,
                'files': files,
                'total': len(files)
            })

    except Exception as e:
        print(f"[ERROR] Exception in /api/files: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/<int:file_id>/pdf', methods=['GET'])
def get_pdf_file(file_id):
    """Retrieve PDF file content by ID."""
    try:
        print(f"[REQUEST] Getting PDF file ID: {file_id}")
        
        # Get PDF document from database
        pdf_doc = PDFRepository.get_by_id(file_id)
        
        if not pdf_doc:
            print(f"[ERROR] PDF not found: ID {file_id}")
            return jsonify({
                'success': False,
                'error': 'PDF not found'
            }), 404
        
        # Get file_content
        file_content_b64 = pdf_doc.get('file_content')
        
        if not file_content_b64:
            print(f"[ERROR] PDF file content not found for ID {file_id}")
            return jsonify({
                'success': False,
                'error': 'PDF file content not available'
            }), 404
        
        # Decode base64 to bytes
        try:
            file_content = base64.b64decode(file_content_b64)
        except Exception as e:
            print(f"[ERROR] Failed to decode PDF content: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to decode PDF content'
            }), 500
        
        filename = pdf_doc.get('filename', 'document.pdf')
        print(f"[SUCCESS] Returning PDF: {filename} ({len(file_content)} bytes)")
        
        # Return PDF as response with proper headers
        return Response(
            file_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'inline; filename="{filename}"',
                'Content-Length': str(len(file_content))
            }
        )
    
    except Exception as e:
        print(f"[ERROR] Exception in /api/files/<id>/pdf: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("Starting ASFC API server on http://localhost:5000")
    app.run(debug=True, port=5000)

