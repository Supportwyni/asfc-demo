"""Vercel serverless function for listing files."""
import sys
from pathlib import Path
from flask import jsonify

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.database.repository import PDFRepository

def handler(request):
    """List all uploaded PDF files."""
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    try:
        db_files = PDFRepository.list_all(limit=100)
        
        files = []
        for db_file in db_files:
            files.append({
                'id': db_file.get('id'),
                'filename': db_file.get('filename', 'unknown'),
                'chunks_count': db_file.get('chunks_count', 0),
                'pages_count': db_file.get('pages_count', 0),
                'uploaded_at': str(db_file.get('uploaded_at', '')),
                'status': db_file.get('status', 'unknown'),
                'file_size': db_file.get('file_size', 0),
                'metadata': db_file.get('metadata', {}),
                'source': db_file.get('filename', 'unknown')
            })
        
        files.sort(key=lambda x: x['uploaded_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files)
        }), 200, {'Access-Control-Allow-Origin': '*'}
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500, {'Access-Control-Allow-Origin': '*'}

