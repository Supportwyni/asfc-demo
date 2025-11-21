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
from backend.database.repository import PDFRepository, ChunkRepository, ChatRepository
from backend.database.models import PDFDocument, Chunk, ChatMessage
from datetime import datetime
import json

app = Flask(__name__)
# Enable CORS for all routes and origins
# Allow all origins in production, or specify your Vercel domain
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000").split(",")
CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
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
        
        # Check if this is a replacement upload
        replace_id = request.form.get('replace_id')
        replace_filename = request.form.get('replace_filename')
        
        # Secure filename
        filename = secure_filename(file.filename)
        
        # If replacing, use the existing filename
        if replace_filename:
            filename = secure_filename(replace_filename)
            print(f"[UPLOAD] Replacing PDF: {filename}")
        elif replace_id:
            # Get existing file to preserve filename
            existing_doc = PDFRepository.get_by_id(int(replace_id))
            if existing_doc:
                filename = existing_doc.get('filename', filename)
                print(f"[UPLOAD] Replacing PDF by ID {replace_id}: {filename}")
        
        print(f"[UPLOAD] Processing uploaded PDF: {filename}")
        
        # Step 1: Upload PDF file to Supabase Storage
        print(f"[UPLOAD] Step 1: Uploading PDF file to Supabase Storage...")
        storage_path = None
        
        try:
            from backend.database.client import get_service_client
            client = get_service_client()  # Use service client for storage operations
            
            # Create storage path: directly in bucket root (no pdf/ folder)
            storage_path = filename
            
            print(f"[UPLOAD] Attempting to upload to storage path: {storage_path}")
            print(f"[UPLOAD] File size: {file_size} bytes")
            
            # Upload to Supabase Storage
            storage_response = client.storage.from_("pdf").upload(
                storage_path,
                file_content,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
            
            print(f"[UPLOAD] PDF uploaded to storage: {storage_path}")
            print(f"[UPLOAD] Storage response: {storage_response}")
            
            # Try to generate signed URL (works for private buckets)
            # We'll generate signed URLs on-demand when files are accessed, not during upload
            public_url = None
            try:
                # Try signed URL first (works for private buckets)
                signed_response = client.storage.from_("pdf").create_signed_url(
                    storage_path,
                    expires_in=3600
                )
                if isinstance(signed_response, dict):
                    public_url = signed_response.get('signedURL') or signed_response.get('signed_url')
                elif hasattr(signed_response, 'signedURL'):
                    public_url = signed_response.signedURL
                else:
                    public_url = str(signed_response)
                print(f"[UPLOAD] Generated signed URL (expires in 1 hour)")
            except Exception as signed_error:
                # Fallback to public URL if bucket is public
                try:
                    public_url = client.storage.from_("pdf").get_public_url(storage_path)
                    print(f"[UPLOAD] Public URL: {public_url}")
                except Exception as url_error:
                    print(f"[WARNING] Could not generate URL (non-critical): {url_error}")
                    public_url = None
            
        except Exception as storage_error:
            print(f"[ERROR] Failed to upload to Supabase Storage: {storage_error}")
            import traceback
            traceback.print_exc()
            # Continue without storage - will store in database as fallback
            storage_path = None
            public_url = None
        
        # Step 2: Save PDF metadata to database
        print(f"[UPLOAD] Step 2: Saving PDF metadata to database...")
        
        # Check if file already exists
        existing_file = PDFRepository.get_by_filename(filename)
        document_id = None
        
        if existing_file and (replace_id or replace_filename):
            # Update existing file
            document_id = existing_file.get('id')
            print(f"[UPLOAD] Updating existing PDF record ID: {document_id}")
            
            # Update metadata (store storage_path and public_url in metadata, keep file_content for processing)
            metadata = existing_file.get('metadata', {}) or {}
            if not isinstance(metadata, dict):
                metadata = {}
            
            if storage_path:
                metadata["storage_path"] = storage_path
            if public_url:
                metadata["public_url"] = public_url
            
            pdf_doc = PDFDocument(
                id=document_id,
                filename=filename,
                file_size=file_size,
                status="processing",
                chunks_count=existing_file.get('chunks_count', 0),
                pages_count=existing_file.get('pages_count', 0),
                file_content=file_content,  # Keep file_content for chunking and database storage
                metadata=metadata if metadata else None
            )
            
            try:
                PDFRepository.update(document_id, pdf_doc)
                print(f"[UPLOAD] PDF updated in database with ID: {document_id}")
            except Exception as e:
                print(f"[WARNING] Failed to update database: {e}")
                document_id = None
        else:
            # Create new file
            metadata = {}
            if storage_path:
                metadata["storage_path"] = storage_path
            if public_url:
                metadata["public_url"] = public_url
            
            pdf_doc = PDFDocument(
                filename=filename,
                file_size=file_size,
                status="processing",
                chunks_count=0,
                pages_count=0,
                file_content=file_content,  # Keep file_content for chunking and database storage
                metadata=metadata if metadata else None
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
                
                # Update metadata with LLM result and ensure storage info is preserved
                if llm_result:
                    # Get current metadata to preserve storage_path and public_url
                    current_doc = PDFRepository.get_by_id(document_id)
                    current_metadata = current_doc.get('metadata', {}) or {} if current_doc else {}
                    if not isinstance(current_metadata, dict):
                        current_metadata = {}
                    
                    # Merge LLM result with existing metadata
                    updated_metadata = {**current_metadata, **llm_result}
                    PDFRepository.update_metadata(filename, updated_metadata)
                    print(f"[UPLOAD] Updated database record with LLM analysis")
                else:
                    print(f"[UPLOAD] No LLM analysis to update")
            except Exception as e:
                print(f"[WARNING] Failed to update database: {e}")
                import traceback
                traceback.print_exc()
        
        result['file_size'] = file_size
        result['document_id'] = document_id
        result['llm_analysis'] = llm_result
        result['chunks_saved_to_db'] = chunks_saved
        result['storage_path'] = storage_path
        result['uploaded_to_storage'] = storage_path is not None
        
        print(f"[UPLOAD] Successfully completed:")
        print(f"  - Chunks created: {result['chunks_created']}")
        print(f"  - Pages processed: {result['pages_processed']}")
        print(f"  - Chunks saved to DB: {chunks_saved}")
        print(f"  - Uploaded to storage: {storage_path is not None}")
        print(f"  - Saved to database: {document_id is not None}")
        
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
    """List all uploaded PDF files from database and Supabase Storage."""
    try:
        from backend.database.client import get_service_client
        
        # Get files from database
        try:
            db_files = PDFRepository.list_all(limit=1000)
            print(f"[DEBUG] Found {len(db_files)} files in database")
            if len(db_files) > 0:
                print(f"[DEBUG] Sample database file: {db_files[0]}")
        except Exception as db_error:
            print(f"[WARNING] Database query failed: {db_error}")
            import traceback
            traceback.print_exc()
            db_files = []
        
        # Create a set of filenames already in database
        db_filenames = {db_file.get('filename') for db_file in db_files if db_file.get('filename')}
        print(f"[DEBUG] Database filenames count: {len(db_filenames)}")
        
        # Get files from Supabase Storage
        storage_files = []
        try:
            service_client = get_service_client()
            # List all files in the pdf bucket
            # Try multiple methods to find files
            storage_list = None
            listing_method = None
            
            # Method 1: Try listing root with no parameter
            try:
                storage_list = service_client.storage.from_("pdf").list()
                if storage_list:
                    files_count = len(storage_list) if isinstance(storage_list, list) else (len(storage_list.data) if hasattr(storage_list, 'data') else 'unknown')
                    print(f"[DEBUG] Root listing (no param) succeeded: {files_count} items")
                    listing_method = "root"
            except Exception as root_error:
                print(f"[DEBUG] Root listing (no param) failed: {root_error}")
            
            # Method 2: Try listing root with empty string
            if not storage_list:
                try:
                    storage_list = service_client.storage.from_("pdf").list("")
                    if storage_list:
                        files_count = len(storage_list) if isinstance(storage_list, list) else (len(storage_list.data) if hasattr(storage_list, 'data') else 'unknown')
                        print(f"[DEBUG] Root listing (empty string) succeeded: {files_count} items")
                        listing_method = "root_empty"
                except Exception as root_error2:
                    print(f"[DEBUG] Root listing (empty string) failed: {root_error2}")
            
            # Method 3: Try listing the "pdf" folder
            if not storage_list:
                try:
                    storage_list = service_client.storage.from_("pdf").list("pdf")
                    if storage_list:
                        files_count = len(storage_list) if isinstance(storage_list, list) else (len(storage_list.data) if hasattr(storage_list, 'data') else 'unknown')
                        print(f"[DEBUG] 'pdf' folder listing succeeded: {files_count} items")
                        listing_method = "pdf_folder"
                except Exception as folder_error:
                    print(f"[DEBUG] 'pdf' folder listing failed: {folder_error}")
                    storage_list = None
            
            if not storage_list:
                print(f"[WARNING] All listing methods failed - no files will be synced from storage")
            
            print(f"[DEBUG] Storage list type: {type(storage_list)}, value: {storage_list}")
            
            # Handle different response formats
            files_to_process = []
            if storage_list:
                # Check if it's a list or has a data attribute
                if isinstance(storage_list, list):
                    files_to_process = storage_list
                elif hasattr(storage_list, 'data'):
                    files_to_process = storage_list.data
                elif isinstance(storage_list, dict) and 'data' in storage_list:
                    files_to_process = storage_list['data']
                elif hasattr(storage_list, '__iter__'):
                    files_to_process = list(storage_list)
                
                if not isinstance(files_to_process, list):
                    files_to_process = []
                
                print(f"[DEBUG] Processing {len(files_to_process)} files from storage")
                
                for storage_file in files_to_process:
                    # Handle both dict and object formats
                    filename = None
                    full_path = None
                    raw_name = None
                    
                    if isinstance(storage_file, dict):
                        raw_name = storage_file.get('name', '')
                        filename = raw_name
                        full_path = storage_file.get('id', '') or raw_name
                    else:
                        raw_name = getattr(storage_file, 'name', '')
                        filename = raw_name
                        full_path = getattr(storage_file, 'id', '') or raw_name
                    
                    # Skip folders (items ending with /)
                    if raw_name and raw_name.endswith('/'):
                        print(f"[DEBUG] Skipping folder: {raw_name}")
                        continue
                    
                    # Extract filename from path - handle different formats:
                    # - "pdf/filename.pdf" -> "filename.pdf"
                    # - "filename.pdf" -> "filename.pdf"
                    if filename:
                        if 'pdf/' in filename:
                            filename = filename.split('pdf/')[-1]
                        # Remove leading slash if present
                        filename = filename.lstrip('/')
                    
                    if full_path:
                        if 'pdf/' in full_path:
                            full_path = full_path.split('pdf/')[-1]
                        full_path = full_path.lstrip('/')
                    
                    # Determine storage_path - files are stored directly in bucket root
                    if filename:
                        # Files are stored directly in bucket root (no pdf/ folder)
                        storage_path = filename
                    else:
                        storage_path = None
                        print(f"[WARNING] Could not extract filename from: {raw_name}")
                        continue
                    
                    print(f"[DEBUG] Processing storage file: raw_name={raw_name}, filename={filename}, storage_path={storage_path}")
                    
                    if filename:
                        # Get file metadata from storage
                        if isinstance(storage_file, dict):
                            file_size = storage_file.get('metadata', {}).get('size', 0) if isinstance(storage_file.get('metadata'), dict) else 0
                            created_at = storage_file.get('created_at', datetime.now().isoformat())
                        else:
                            file_size = getattr(storage_file, 'metadata', {}).get('size', 0) if hasattr(storage_file, 'metadata') else 0
                            created_at = getattr(storage_file, 'created_at', datetime.now().isoformat())
                        
                        # Generate signed URL for this file (works for private buckets)
                        public_url = None
                        paths_to_try = [
                            storage_path,  # Try the stored path first
                            filename,     # Try just filename as fallback
                        ]
                        
                        # Remove duplicates
                        paths_to_try = list(dict.fromkeys(paths_to_try))
                        
                        for path_attempt in paths_to_try:
                            try:
                                # Generate signed URL (expires in 1 hour) - works for private buckets
                                signed_response = service_client.storage.from_("pdf").create_signed_url(
                                    path_attempt,
                                    expires_in=3600
                                )
                                
                                if isinstance(signed_response, dict):
                                    public_url = signed_response.get('signedURL') or signed_response.get('signed_url')
                                elif hasattr(signed_response, 'signedURL'):
                                    public_url = signed_response.signedURL
                                elif hasattr(signed_response, 'signed_url'):
                                    public_url = signed_response.signed_url
                                else:
                                    public_url = str(signed_response)
                                
                                if public_url:
                                    print(f"[DEBUG] Successfully got signed URL for {filename} using path: {path_attempt}")
                                    break  # Success, stop trying
                            except Exception as signed_error:
                                # Fallback to public URL if bucket is public
                                try:
                                    public_url = service_client.storage.from_("pdf").get_public_url(path_attempt)
                                    print(f"[DEBUG] Using public URL as fallback for {filename}")
                                    break
                                except Exception as url_error:
                                    print(f"[DEBUG] Failed to get URL with path '{path_attempt}': {url_error}")
                                    continue
                        
                        if not public_url:
                            print(f"[WARNING] Could not generate public URL for {filename} with any path format")
                            print(f"[WARNING] Tried paths: {paths_to_try}")
                        
                        if filename not in db_filenames:
                            # This file exists in storage but not in database
                            # Create a basic database record for it
                            try:
                                # Create database record
                                pdf_doc = PDFDocument(
                                    filename=filename,
                                    file_size=file_size if file_size else None,
                                    status="processed",  # Assume processed if already in storage
                                    chunks_count=0,
                                    pages_count=0,
                                    metadata={"storage_path": storage_path, "public_url": public_url} if public_url else {"storage_path": storage_path}
                                )
                                
                                db_record = PDFRepository.create(pdf_doc)
                                print(f"[SYNC] Created database record for storage file: {filename}")
                                
                                # Add to db_files list
                                db_files.append({
                                    'id': db_record.get('id'),
                                    'filename': filename,
                                    'chunks_count': 0,
                                    'pages_count': 0,
                                    'uploaded_at': created_at,
                                    'status': 'processed',
                                    'file_size': file_size if file_size else 0,
                                    'metadata': {"storage_path": storage_path, "public_url": public_url} if public_url else {"storage_path": storage_path}
                                })
                            except Exception as sync_error:
                                print(f"[WARNING] Failed to sync storage file {filename} to database: {sync_error}")
                                import traceback
                                traceback.print_exc()
                                # Still add it to the list even if database sync fails
                                storage_files.append({
                                    'id': None,
                                    'filename': filename,
                                    'chunks_count': 0,
                                    'pages_count': 0,
                                    'uploaded_at': created_at,
                                    'status': 'processed',
                                    'file_size': file_size,
                                    'metadata': {"storage_path": storage_path, "public_url": public_url} if public_url else {"storage_path": storage_path}
                                })
                        else:
                            # File exists in database, but update metadata if storage_path is missing
                            # Find the matching database file and update its metadata
                            matching_db_file = next((f for f in db_files if f.get('filename') == filename), None)
                            if matching_db_file:
                                db_metadata = matching_db_file.get('metadata', {}) or {}
                                if not isinstance(db_metadata, dict):
                                    db_metadata = {}
                                
                                # Update storage_path and public_url if missing
                                needs_update = False
                                if not db_metadata.get('storage_path'):
                                    db_metadata['storage_path'] = storage_path
                                    needs_update = True
                                if public_url and not db_metadata.get('public_url'):
                                    db_metadata['public_url'] = public_url
                                    needs_update = True
                                
                                if needs_update:
                                    matching_db_file['metadata'] = db_metadata
                                    print(f"[UPDATE] Updated metadata for {filename} with storage_path")
            
            print(f"[DEBUG] Storage sync complete: {len(storage_files)} files added to storage_files list")
            print(f"[DEBUG] Total db_files after sync: {len(db_files)}")
        except Exception as storage_error:
            print(f"[WARNING] Failed to list storage files: {storage_error}")
            import traceback
            traceback.print_exc()
        
        # Process all files (from database + newly synced)
        files = []
        for db_file in db_files:
            # Parse uploaded_at if it's a string
            uploaded_at = db_file.get('uploaded_at')
            if isinstance(uploaded_at, str):
                try:
                    uploaded_at = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                except:
                    uploaded_at = datetime.now()
            
            # Ensure metadata has public_url if storage_path exists
            metadata = db_file.get('metadata', {}) or {}
            if not isinstance(metadata, dict):
                metadata = {}
            
            # If storage_path exists but no public_url, generate it
            storage_path = metadata.get('storage_path')
            if storage_path and not metadata.get('public_url'):
                public_url = None
                filename_for_url = db_file.get('filename', 'unknown')
                paths_to_try = [
                    storage_path,
                    filename_for_url,
                ]
                
                for path_attempt in paths_to_try:
                    try:
                        from backend.database.client import get_service_client
                        service_client = get_service_client()
                        public_url = service_client.storage.from_("pdf").get_public_url(path_attempt)
                        print(f"[UPDATE] Added public_url to {filename_for_url} using path: {path_attempt}")
                        break
                    except Exception as url_error:
                        print(f"[DEBUG] Failed path '{path_attempt}' for {filename_for_url}: {url_error}")
                        continue
                
                if public_url:
                    metadata['public_url'] = public_url
                else:
                    print(f"[WARNING] Could not generate public_url for {filename_for_url} with any path")
            
            files.append({
                'id': db_file.get('id'),
                'filename': db_file.get('filename', 'unknown'),
                'chunks_count': db_file.get('chunks_count', 0),
                'pages_count': db_file.get('pages_count', 0),
                'uploaded_at': uploaded_at.isoformat() if isinstance(uploaded_at, datetime) else str(uploaded_at),
                'status': db_file.get('status', 'unknown'),
                'file_size': db_file.get('file_size', 0),
                'metadata': metadata,
                'source': db_file.get('filename', 'unknown')
            })
        
        # Add storage-only files (if any failed to sync or weren't in database)
        print(f"[DEBUG] Adding {len(storage_files)} storage-only files to response")
        files.extend(storage_files)
        
        # Sort by upload time (newest first)
        files.sort(key=lambda x: x['uploaded_at'], reverse=True)
        
        print(f"[DEBUG] Final count: {len(files)} files total ({len(db_files)} from DB, {len(storage_files)} from storage)")
        if len(files) == 0:
            print("[WARNING] No files found in database or storage!")
        else:
            print(f"[DEBUG] Sample filenames: {[f.get('filename') for f in files[:5]]}")
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files)
        })
    
    except Exception as e:
        # Fallback: if everything fails, try reading from chunk files
        print(f"[WARNING] Main query failed, falling back to file system: {e}")
        try:
            import json
            files = []
            chunk_files = list(CHUNK_DIR.glob("*.jsonl"))
            
            for chunk_file in chunk_files:
                try:
                    pdf_name = chunk_file.stem
                    file_path = chunk_file
                    
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
                except Exception as file_error:
                    print(f"[ERROR] Failed to process file {chunk_file.name}: {file_error}")
                    continue
            
            files.sort(key=lambda x: x['uploaded_at'], reverse=True)
            
            return jsonify({
                'success': True,
                'files': files,
                'total': len(files)
            })
        except Exception as fallback_error:
            print(f"[ERROR] Fallback also failed: {fallback_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


@app.route('/api/files/<int:file_id>/pdf', methods=['GET'])
def get_pdf_file(file_id):
    """Get PDF file URL from Supabase Storage."""
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
        
        # Check if file is in Supabase Storage
        metadata = pdf_doc.get('metadata', {})
        storage_path = metadata.get('storage_path') if isinstance(metadata, dict) else None
        
        if storage_path:
            # Get public URL from Supabase Storage - try multiple path formats
            from backend.database.client import get_service_client
            client = get_service_client()  # Use service client for storage operations
            
            public_url = None
            filename_for_path = pdf_doc.get('filename', 'document.pdf')
            paths_to_try = [
                storage_path,  # Try the stored path first
                filename_for_path,  # Try just filename
            ]
            
            print(f"[DEBUG] Trying to get URL for file_id={file_id}, storage_path={storage_path}, filename={filename_for_path}")
            
            # First, try to verify file exists by listing storage
            try:
                storage_files = client.storage.from_("pdf").list()
                files_list = []
                if isinstance(storage_files, list):
                    files_list = storage_files
                elif hasattr(storage_files, 'data'):
                    files_list = storage_files.data if isinstance(storage_files.data, list) else []
                elif isinstance(storage_files, dict) and 'data' in storage_files:
                    files_list = storage_files['data'] if isinstance(storage_files['data'], list) else []
                
                print(f"[DEBUG] Found {len(files_list)} files in storage")
                # Check if our file exists
                file_found = False
                for sf in files_list[:10]:  # Check first 10 for debugging
                    sf_name = sf.get('name', '') if isinstance(sf, dict) else getattr(sf, 'name', '')
                    print(f"[DEBUG] Storage file: {sf_name}")
                    if filename_for_path in sf_name or sf_name.endswith(filename_for_path):
                        file_found = True
                        print(f"[DEBUG] Found matching file: {sf_name}")
                        break
            except Exception as list_error:
                print(f"[WARNING] Could not list storage files: {list_error}")
            
            # Try to generate signed URL (works for private buckets)
            signed_url = None
            for path_attempt in paths_to_try:
                try:
                    # Generate signed URL (expires in 1 hour) - works for private buckets
                    signed_url_response = client.storage.from_("pdf").create_signed_url(
                        path_attempt,
                        expires_in=3600  # 1 hour expiration
                    )
                    
                    if isinstance(signed_url_response, dict):
                        signed_url = signed_url_response.get('signedURL') or signed_url_response.get('signed_url')
                    elif hasattr(signed_url_response, 'signedURL'):
                        signed_url = signed_url_response.signedURL
                    elif hasattr(signed_url_response, 'signed_url'):
                        signed_url = signed_url_response.signed_url
                    else:
                        signed_url = str(signed_url_response)
                    
                    if signed_url:
                        print(f"[SUCCESS] Generated signed URL using path: {path_attempt}")
                        print(f"[DEBUG] Signed URL: {signed_url[:100]}...")
                        break
                except Exception as signed_error:
                    print(f"[DEBUG] Signed URL generation failed for '{path_attempt}': {signed_error}")
                    # Try public URL as fallback
                    try:
                        public_url = client.storage.from_("pdf").get_public_url(path_attempt)
                        signed_url = public_url
                        print(f"[SUCCESS] Using public URL as fallback: {path_attempt}")
                        break
                    except:
                        continue
            
            if signed_url:
                print(f"[SUCCESS] Returning signed URL for PDF")
                return jsonify({
                    'success': True,
                    'url': signed_url,
                    'filename': filename_for_path,
                    'type': 'signed_url'
                })
            
            # Fallback: Try to download and serve directly if signed URLs don't work
            if storage_path:
                try:
                    print(f"[INFO] Signed URL failed, downloading PDF from storage: {storage_path}")
                    file_data = client.storage.from_("pdf").download(storage_path)
                    
                    if file_data:
                        print(f"[SUCCESS] Downloaded PDF from storage: {len(file_data)} bytes")
                        return Response(
                            file_data,
                            mimetype='application/pdf',
                            headers={
                                'Content-Disposition': f'inline; filename="{filename_for_path}"',
                                'Content-Length': str(len(file_data))
                            }
                        )
                except Exception as download_error:
                    print(f"[WARNING] Failed to download from storage: {download_error}")
                    # Fall through to file_content fallback
        
        # Fallback: try to get from file_content (for old files)
        file_content_data = pdf_doc.get('file_content')
        
        if not file_content_data:
            print(f"[ERROR] PDF file not found in storage or database for ID {file_id}")
            return jsonify({
                'success': False,
                'error': 'PDF file not available in storage or database'
            }), 404
        
        # Debug: Check what format we got
        print(f"[DEBUG] file_content_data type: {type(file_content_data)}")
        if isinstance(file_content_data, str):
            print(f"[DEBUG] String length: {len(file_content_data)}, first 100 chars: {file_content_data[:100]}")
        elif isinstance(file_content_data, bytes):
            print(f"[DEBUG] Bytes length: {len(file_content_data)}, first 20 bytes: {file_content_data[:20]}")
        
        # Handle different formats: bytes, base64 string, or already decoded
        try:
            if isinstance(file_content_data, bytes):
                # Already bytes, use directly
                file_content = file_content_data
                print(f"[DEBUG] Using bytes directly")
            elif isinstance(file_content_data, str):
                # Try to decode base64
                try:
                    # Check if it's base64 encoded
                    file_content = base64.b64decode(file_content_data, validate=True)
                    print(f"[DEBUG] Successfully decoded base64 string")
                except Exception as decode_error:
                    print(f"[DEBUG] Base64 decode failed: {decode_error}")
                    # Try treating as raw string (shouldn't happen but let's try)
                    file_content = file_content_data.encode('latin-1')
                    print(f"[DEBUG] Encoded string to bytes using latin-1")
            else:
                # Unknown type, try to convert
                print(f"[DEBUG] Unknown type, converting to bytes")
                file_content = bytes(file_content_data)
        except Exception as e:
            print(f"[ERROR] Failed to process PDF content: {e}, type: {type(file_content_data)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Failed to process PDF content: {str(e)}'
            }), 500
        
        filename = pdf_doc.get('filename', 'document.pdf')
        
        # Verify it's a valid PDF by checking magic bytes
        print(f"[DEBUG] Final file_content type: {type(file_content)}, length: {len(file_content)}")
        print(f"[DEBUG] First 20 bytes (hex): {file_content[:20].hex() if len(file_content) >= 20 else 'too short'}")
        print(f"[DEBUG] First 20 bytes (repr): {repr(file_content[:20]) if len(file_content) >= 20 else 'too short'}")
        
        if len(file_content) < 4:
            print(f"[ERROR] File content too short: {len(file_content)} bytes")
            return jsonify({
                'success': False,
                'error': f'Invalid PDF file: file too short ({len(file_content)} bytes)'
            }), 400
        
        if not file_content.startswith(b'%PDF'):
            print(f"[ERROR] File content doesn't appear to be a valid PDF")
            print(f"[ERROR] Starts with (hex): {file_content[:50].hex()}")
            print(f"[ERROR] Starts with (repr): {repr(file_content[:50])}")
            return jsonify({
                'success': False,
                'error': 'Invalid PDF file: file does not start with PDF magic bytes. File may be corrupted or incorrectly stored.'
            }), 400
        
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


@app.route('/api/files/by-name/<path:filename>/pdf', methods=['GET'])
def get_pdf_file_by_name(filename):
    """Get PDF file URL from Supabase Storage by filename."""
    try:
        # Decode URL-encoded filename
        from urllib.parse import unquote
        filename = unquote(filename)
        
        # Remove .pdf extension if present (database stores without extension sometimes)
        if filename.endswith('.pdf'):
            filename_without_ext = filename[:-4]
        else:
            filename_without_ext = filename
        
        print(f"[REQUEST] Getting PDF file by name: {filename} (also trying: {filename_without_ext})")
        
        # Try exact match first
        pdf_doc = PDFRepository.get_by_filename(filename)
        
        # If not found, try without extension
        if not pdf_doc and filename != filename_without_ext:
            print(f"[REQUEST] Trying filename without extension: {filename_without_ext}")
            pdf_doc = PDFRepository.get_by_filename(filename_without_ext)
        
        # If still not found, try with .pdf extension
        if not pdf_doc and not filename.endswith('.pdf'):
            filename_with_ext = filename + '.pdf'
            print(f"[REQUEST] Trying filename with extension: {filename_with_ext}")
            pdf_doc = PDFRepository.get_by_filename(filename_with_ext)
        
        if not pdf_doc:
            # File not in database, try to generate signed URL from storage
            print(f"[INFO] PDF not in database, checking storage: {filename}")
            try:
                from backend.database.client import get_service_client
                service_client = get_service_client()
                storage_path = filename  # Files stored directly in bucket root
                
                # Generate signed URL (works for private buckets)
                signed_response = service_client.storage.from_("pdf").create_signed_url(
                    storage_path,
                    expires_in=3600
                )
                
                if isinstance(signed_response, dict):
                    signed_url = signed_response.get('signedURL') or signed_response.get('signed_url')
                elif hasattr(signed_response, 'signedURL'):
                    signed_url = signed_response.signedURL
                else:
                    signed_url = str(signed_response)
                
                if signed_url:
                    print(f"[SUCCESS] Found PDF in storage with signed URL: {storage_path}")
                    return jsonify({
                        'success': True,
                        'url': signed_url,
                        'filename': filename,
                        'type': 'signed_url'
                    })
            except Exception as storage_error:
                print(f"[ERROR] PDF not found in storage: {storage_error}")
                return jsonify({
                    'success': False,
                    'error': f'PDF not found: "{filename}"'
                }), 404
        
        # Check if file is in Supabase Storage
        metadata = pdf_doc.get('metadata', {})
        storage_path = metadata.get('storage_path') if isinstance(metadata, dict) else None
        filename_for_path = pdf_doc.get('filename', filename)
        
        if not storage_path:
            storage_path = filename_for_path
        
        if storage_path:
            # Generate signed URL (works for private buckets) - standard approach for file serving
            from backend.database.client import get_service_client
            client = get_service_client()
            
            signed_url = None
            paths_to_try = [storage_path, filename_for_path]
            
            for path_attempt in paths_to_try:
                try:
                    # Generate signed URL (expires in 1 hour) - works for private buckets
                    signed_response = client.storage.from_("pdf").create_signed_url(
                        path_attempt,
                        expires_in=3600
                    )
                    
                    if isinstance(signed_response, dict):
                        signed_url = signed_response.get('signedURL') or signed_response.get('signed_url')
                    elif hasattr(signed_response, 'signedURL'):
                        signed_url = signed_response.signedURL
                    elif hasattr(signed_response, 'signed_url'):
                        signed_url = signed_response.signed_url
                    else:
                        signed_url = str(signed_response)
                    
                    if signed_url:
                        print(f"[SUCCESS] Generated signed URL for: {path_attempt}")
                        return jsonify({
                            'success': True,
                            'url': signed_url,
                            'filename': filename_for_path,
                            'type': 'signed_url',
                            'expires_in': 3600
                        })
                except Exception as signed_error:
                    # Fallback to public URL if bucket is public
                    try:
                        public_url = client.storage.from_("pdf").get_public_url(path_attempt)
                        print(f"[SUCCESS] Using public URL: {path_attempt}")
                        return jsonify({
                            'success': True,
                            'url': public_url,
                            'filename': filename_for_path,
                            'type': 'public_url'
                        })
                    except:
                        continue
        
        # Fallback: try to get from file_content (for old files or if storage failed)
        file_content_data = pdf_doc.get('file_content')
        
        if not file_content_data:
            print(f"[ERROR] PDF file content not found for {filename}")
            return jsonify({
                'success': False,
                'error': 'PDF file content not available'
            }), 404
        
        # Debug: Check what format we got
        print(f"[DEBUG] file_content_data type: {type(file_content_data)}")
        if isinstance(file_content_data, str):
            print(f"[DEBUG] String length: {len(file_content_data)}, first 100 chars: {file_content_data[:100]}")
        elif isinstance(file_content_data, bytes):
            print(f"[DEBUG] Bytes length: {len(file_content_data)}, first 20 bytes: {file_content_data[:20]}")
        
        # Handle different formats: bytes, base64 string, or already decoded
        try:
            if isinstance(file_content_data, bytes):
                # Already bytes, use directly
                file_content = file_content_data
                print(f"[DEBUG] Using bytes directly")
            elif isinstance(file_content_data, str):
                # Try to decode base64
                try:
                    # Check if it's base64 encoded
                    file_content = base64.b64decode(file_content_data, validate=True)
                    print(f"[DEBUG] Successfully decoded base64 string")
                except Exception as decode_error:
                    print(f"[DEBUG] Base64 decode failed: {decode_error}")
                    # Try treating as raw string (shouldn't happen but let's try)
                    file_content = file_content_data.encode('latin-1')
                    print(f"[DEBUG] Encoded string to bytes using latin-1")
            else:
                # Unknown type, try to convert
                print(f"[DEBUG] Unknown type, converting to bytes")
                file_content = bytes(file_content_data)
        except Exception as e:
            print(f"[ERROR] Failed to process PDF content: {e}, type: {type(file_content_data)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Failed to process PDF content: {str(e)}'
            }), 500
        
        # Verify it's a valid PDF by checking magic bytes
        print(f"[DEBUG] Final file_content type: {type(file_content)}, length: {len(file_content)}")
        print(f"[DEBUG] First 20 bytes (hex): {file_content[:20].hex() if len(file_content) >= 20 else 'too short'}")
        print(f"[DEBUG] First 20 bytes (repr): {repr(file_content[:20]) if len(file_content) >= 20 else 'too short'}")
        
        if len(file_content) < 4:
            print(f"[ERROR] File content too short: {len(file_content)} bytes")
            return jsonify({
                'success': False,
                'error': f'Invalid PDF file: file too short ({len(file_content)} bytes)'
            }), 400
        
        if not file_content.startswith(b'%PDF'):
            print(f"[ERROR] File content doesn't appear to be a valid PDF")
            print(f"[ERROR] Starts with (hex): {file_content[:50].hex()}")
            print(f"[ERROR] Starts with (repr): {repr(file_content[:50])}")
            return jsonify({
                'success': False,
                'error': 'Invalid PDF file: file does not start with PDF magic bytes. File may be corrupted or incorrectly stored.'
            }), 400
        
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
        print(f"[ERROR] Exception in /api/files/by-name/<filename>/pdf: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def delete_pdf_file(file_id):
    """Delete PDF file from database and storage."""
    try:
        print(f"[DELETE] Deleting PDF file ID: {file_id}")
        
        # Get PDF document from database
        pdf_doc = PDFRepository.get_by_id(file_id)
        
        if not pdf_doc:
            print(f"[ERROR] PDF not found: ID {file_id}")
            return jsonify({
                'success': False,
                'error': 'PDF not found'
            }), 404
        
        filename = pdf_doc.get('filename', 'unknown')
        
        # Delete from Supabase Storage if exists
        try:
            metadata = pdf_doc.get('metadata', {})
            storage_path = metadata.get('storage_path') if isinstance(metadata, dict) else None
            
            # If no storage_path in metadata, use filename directly (files stored in bucket root)
            if not storage_path:
                storage_path = filename
            
            if storage_path:
                try:
                    from backend.database.client import get_service_client
                    service_client = get_service_client()  # Use service client for storage operations
                    service_client.storage.from_("pdf").remove([storage_path])
                    print(f"[DELETE] Deleted from storage: {storage_path}")
                except Exception as storage_error:
                    print(f"[WARNING] Failed to delete from storage: {storage_error}")
                    # Try with filename as fallback
                    try:
                        service_client.storage.from_("pdf").remove([filename])
                        print(f"[DELETE] Deleted from storage using filename: {filename}")
                    except:
                        pass
        except Exception as e:
            print(f"[WARNING] Storage deletion error: {e}")
        
        # Delete chunks associated with this PDF first
        try:
            from backend.database.client import get_service_client
            service_client = get_service_client()
            chunks_deleted = service_client.table("chunks").delete().eq("document_id", file_id).execute()
            print(f"[DELETE] Deleted {len(chunks_deleted.data) if chunks_deleted.data else 0} chunks from database")
        except Exception as chunk_error:
            print(f"[WARNING] Failed to delete chunks: {chunk_error}")
            # Continue with PDF deletion even if chunk deletion fails
        
        # Delete from database
        try:
            PDFRepository.delete(file_id)
            print(f"[SUCCESS] Deleted PDF from database: {filename} (ID: {file_id})")
        except Exception as db_error:
            print(f"[ERROR] Failed to delete from database: {db_error}")
            return jsonify({
                'success': False,
                'error': f'Failed to delete from database: {str(db_error)}'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'PDF "{filename}" deleted successfully'
        })
    
    except Exception as e:
        print(f"[ERROR] Exception in DELETE /api/files/<id>: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/upload-from-folder', methods=['POST'])
def upload_pdfs_from_folder():
    """Upload all PDFs from the local pdf folder to Supabase Storage."""
    try:
        print("[UPLOAD FOLDER] Starting upload of PDFs from local folder...")
        
        from pathlib import Path
        from backend.database.client import get_service_client
        client = get_service_client()  # Use service client for storage operations
        
        # Get pdf folder path (relative to project root)
        project_root = Path(__file__).parent.parent
        pdf_folder = project_root / "pdf"
        
        if not pdf_folder.exists():
            return jsonify({
                'success': False,
                'error': f'PDF folder not found: {pdf_folder}'
            }), 404
        
        # Get all PDF files
        pdf_files = list(pdf_folder.glob("*.pdf"))
        
        if not pdf_files:
            return jsonify({
                'success': False,
                'error': 'No PDF files found in pdf folder'
            }), 404
        
        print(f"[UPLOAD FOLDER] Found {len(pdf_files)} PDF files")
        
        uploaded_count = 0
        skipped_count = 0
        failed_count = 0
        errors = []
        
        for pdf_file in pdf_files:
            filename = pdf_file.name
            
            try:
                # Read PDF file
                with open(pdf_file, 'rb') as f:
                    file_content = f.read()
                
                file_size = len(file_content)
                
                # Verify it's a valid PDF
                if len(file_content) < 4 or not file_content.startswith(b'%PDF'):
                    print(f"[UPLOAD FOLDER] Skipping {filename} - not a valid PDF")
                    skipped_count += 1
                    continue
                
                # Upload to Supabase Storage - directly in bucket root
                storage_path = filename
                
                try:
                    storage_response = client.storage.from_("pdf").upload(
                        storage_path,
                        file_content,
                        file_options={"content-type": "application/pdf", "upsert": "true"}
                    )
                    
                    print(f"[UPLOAD FOLDER] Uploaded {filename} to storage: {storage_path}")
                    uploaded_count += 1
                    
                except Exception as upload_error:
                    error_msg = f"Failed to upload {filename}: {str(upload_error)}"
                    print(f"[UPLOAD FOLDER] {error_msg}")
                    errors.append(error_msg)
                    failed_count += 1
                    continue
                    
            except Exception as e:
                error_msg = f"Error processing {filename}: {str(e)}"
                print(f"[UPLOAD FOLDER] {error_msg}")
                errors.append(error_msg)
                failed_count += 1
                continue
        
        result_message = f"Upload complete: {uploaded_count} uploaded, {skipped_count} skipped, {failed_count} failed"
        print(f"[UPLOAD FOLDER] {result_message}")
        
        return jsonify({
            'success': True,
            'message': result_message,
            'uploaded': uploaded_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'total': len(pdf_files),
            'errors': errors[:10] if errors else []  # Return first 10 errors
        })
    
    except Exception as e:
        print(f"[ERROR] Exception in upload_pdfs_from_folder: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/migrate-to-storage', methods=['POST'])
def migrate_pdfs_to_storage():
    """Migrate existing PDFs from database to Supabase Storage."""
    try:
        print("[MIGRATE] Starting PDF migration to Supabase Storage...")
        
        from backend.database.client import get_service_client
        client = get_service_client()  # Use service client for storage operations
        
        # Get all PDFs from database
        all_files = PDFRepository.list_all(limit=1000)
        
        migrated_count = 0
        failed_count = 0
        skipped_count = 0
        
        for pdf_doc in all_files:
            file_id = pdf_doc.get('id')
            filename = pdf_doc.get('filename', 'unknown')
            metadata = pdf_doc.get('metadata', {}) or {}
            
            # Check if already migrated
            if isinstance(metadata, dict) and metadata.get('storage_path'):
                print(f"[MIGRATE] Skipping {filename} - already in storage")
                skipped_count += 1
                continue
            
            # Get file_content from database
            file_content_data = pdf_doc.get('file_content')
            
            if not file_content_data:
                print(f"[MIGRATE] Skipping {filename} - no file_content in database")
                skipped_count += 1
                continue
            
            # Convert file_content to bytes if needed
            try:
                if isinstance(file_content_data, bytes):
                    file_content = file_content_data
                elif isinstance(file_content_data, str):
                    # Try to decode base64
                    try:
                        file_content = base64.b64decode(file_content_data)
                    except:
                        print(f"[MIGRATE] Failed to decode {filename} - invalid format")
                        failed_count += 1
                        continue
                else:
                    file_content = bytes(file_content_data)
                
                # Verify it's a valid PDF
                if len(file_content) < 4 or not file_content.startswith(b'%PDF'):
                    print(f"[MIGRATE] Skipping {filename} - not a valid PDF")
                    failed_count += 1
                    continue
                
                # Upload to Supabase Storage - directly in bucket root
                storage_path = filename
                
                try:
                    storage_response = client.storage.from_("pdf").upload(
                        storage_path,
                        file_content,
                        file_options={"content-type": "application/pdf", "upsert": "true"}
                    )
                    
                    print(f"[MIGRATE] Uploaded {filename} to storage: {storage_path}")
                    
                    # Update metadata with storage_path
                    if not isinstance(metadata, dict):
                        metadata = {}
                    
                    metadata["storage_path"] = storage_path
                    
                    # Update database record
                    pdf_doc_model = PDFDocument(
                        id=file_id,
                        filename=filename,
                        file_size=pdf_doc.get('file_size'),
                        status=pdf_doc.get('status', 'processed'),
                        chunks_count=pdf_doc.get('chunks_count', 0),
                        pages_count=pdf_doc.get('pages_count', 0),
                        metadata=metadata
                    )
                    
                    PDFRepository.update(file_id, pdf_doc_model)
                    migrated_count += 1
                    print(f"[MIGRATE] Updated database record for {filename}")
                    
                except Exception as upload_error:
                    print(f"[MIGRATE] Failed to upload {filename}: {upload_error}")
                    failed_count += 1
                    continue
                    
            except Exception as e:
                print(f"[MIGRATE] Error processing {filename}: {e}")
                failed_count += 1
                continue
        
        result_message = f"Migration complete: {migrated_count} migrated, {skipped_count} skipped, {failed_count} failed"
        print(f"[MIGRATE] {result_message}")
        
        return jsonify({
            'success': True,
            'message': result_message,
            'migrated': migrated_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'total': len(all_files)
        })
    
    except Exception as e:
        print(f"[ERROR] Exception in migrate_pdfs_to_storage: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/history', methods=['GET', 'POST'])
def chat_history():
    """Save or load chat history."""
    try:
        if request.method == 'POST':
            # Save chat history - only save the latest message pair if it's new
            data = request.json
            messages = data.get('messages', [])
            session_id = data.get('session_id', 'default')
            
            if not messages or len(messages) < 2:
                return jsonify({
                    'success': True,
                    'saved_count': 0
                })
            
            # Get existing messages to avoid duplicates
            existing_messages = ChatRepository.get_by_user(session_id, limit=100)
            existing_questions = {msg.get('question', '') for msg in existing_messages}
            
            # Only save the last message pair if it's new
            saved_count = 0
            if len(messages) >= 2:
                # Check the last two messages
                last_user = messages[-2] if len(messages) >= 2 and messages[-2].get('role') == 'user' else None
                last_assistant = messages[-1] if messages[-1].get('role') == 'assistant' else None
                
                if last_user and last_assistant:
                    user_content = last_user.get('content', '')
                    # Only save if this question hasn't been saved yet
                    if user_content and user_content not in existing_questions:
                        chat_message = ChatMessage(
                            user_id=session_id,
                            question=user_content,
                            response=last_assistant.get('content', ''),
                            metadata={'session_id': session_id}
                        )
                        try:
                            ChatRepository.create(chat_message)
                            saved_count = 1
                        except Exception as e:
                            print(f"[WARNING] Failed to save message: {e}")
            
            print(f"[CHAT HISTORY] Saved {saved_count} new message pairs for session {session_id}")
            return jsonify({
                'success': True,
                'saved_count': saved_count
            })
        
        else:  # GET
            # Load chat history
            session_id = request.args.get('session_id', 'default')
            limit = int(request.args.get('limit', 50))
            
            # Get messages from database
            db_messages = ChatRepository.get_by_user(session_id, limit=limit)
            
            # Convert database format to frontend format
            messages = []
            for msg in reversed(db_messages):  # Reverse to get chronological order
                messages.append({
                    'role': 'user',
                    'content': msg.get('question', '')
                })
                messages.append({
                    'role': 'assistant',
                    'content': msg.get('response', '')
                })
            
            print(f"[CHAT HISTORY] Loaded {len(messages)} messages for session {session_id}")
            return jsonify({
                'success': True,
                'messages': messages
            })
    
    except Exception as e:
        print(f"[ERROR] Exception in /api/chat/history: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("Starting ASFC API server on http://localhost:5000")
    app.run(debug=True, port=5000)

