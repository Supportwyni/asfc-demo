"""Vercel serverless function for file listing (read-only)."""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.repository import PDFRepository

app = Flask(__name__)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

@app.route('/api/files', methods=['GET'])
def list_files():
    """List all uploaded PDF files from database (read-only)."""
    try:
        # Get files from database only
        db_files = PDFRepository.list_all(limit=1000)
        
        files = []
        for db_file in db_files:
            files.append({
                'id': db_file.get('id'),
                'filename': db_file.get('filename', 'unknown'),
                'chunks_count': db_file.get('chunks_count', 0),
                'pages_count': db_file.get('pages_count', 0),
                'uploaded_at': db_file.get('uploaded_at'),
                'status': db_file.get('status', 'unknown'),
                'file_size': db_file.get('file_size', 0),
                'metadata': db_file.get('metadata', {}),
                'source': db_file.get('filename', 'unknown')
            })
        
        files.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files),
            'note': 'PDF upload/delete disabled in Vercel deployment. Use full backend for these features.'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

handler = app



