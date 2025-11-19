"""Vercel serverless function for PDF upload."""
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.pdf_processor import process_uploaded_pdf
from backend.config import CHUNK_DIR
from backend.database.repository import PDFRepository
from backend.database.models import PDFDocument

app = Flask(__name__)

def handler(request):
    """Vercel serverless function handler."""
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400, {'Access-Control-Allow-Origin': '*'}
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400, {'Access-Control-Allow-Origin': '*'}
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only PDF files are allowed.'
            }), 400, {'Access-Control-Allow-Origin': '*'}
        
        file_content = file.read()
        filename = secure_filename(file.filename)
        
        # Process PDF
        result = process_uploaded_pdf(file_content, filename, CHUNK_DIR)
        
        if not result['success']:
            return jsonify(result), 500, {'Access-Control-Allow-Origin': '*'}
        
        # Save to database
        try:
            pdf_doc = PDFDocument(
                filename=filename,
                file_size=len(file_content),
                status="processed",
                chunks_count=result['chunks_created'],
                pages_count=result['pages_processed'],
                file_content=file_content
            )
            db_record = PDFRepository.create(pdf_doc)
            result['document_id'] = db_record.get('id')
        except Exception as e:
            print(f"Database save failed: {e}")
            result['document_id'] = None
        
        return jsonify(result), 200, {'Access-Control-Allow-Origin': '*'}
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500, {'Access-Control-Allow-Origin': '*'}

