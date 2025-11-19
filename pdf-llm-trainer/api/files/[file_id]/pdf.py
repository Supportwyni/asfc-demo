"""Vercel serverless function for getting PDF file."""
import sys
import base64
from pathlib import Path
from flask import Response, jsonify

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.database.repository import PDFRepository

def handler(request):
    """Get PDF file by ID."""
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    try:
        # Get file_id from URL path
        file_id = request.path.split('/')[-2] if '/files/' in request.path else None
        if not file_id or not file_id.isdigit():
            return jsonify({
                'success': False,
                'error': 'Invalid file ID'
            }), 400, {'Access-Control-Allow-Origin': '*'}
        
        file_id = int(file_id)
        pdf_doc = PDFRepository.get_by_id(file_id)
        
        if not pdf_doc:
            return jsonify({
                'success': False,
                'error': 'PDF not found'
            }), 404, {'Access-Control-Allow-Origin': '*'}
        
        file_content_b64 = pdf_doc.get('file_content')
        if not file_content_b64:
            return jsonify({
                'success': False,
                'error': 'PDF file content not available'
            }), 404, {'Access-Control-Allow-Origin': '*'}
        
        file_content = base64.b64decode(file_content_b64)
        filename = pdf_doc.get('filename', 'document.pdf')
        
        return Response(
            file_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'inline; filename="{filename}"',
                'Content-Length': str(len(file_content)),
                'Access-Control-Allow-Origin': '*'
            }
        )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500, {'Access-Control-Allow-Origin': '*'}

