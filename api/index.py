"""Vercel serverless function - Main API router."""
from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

@app.route('/')
@app.route('/api')
def index():
    """API index."""
    return jsonify({
        'name': 'ASFC Aviation Chat API',
        'version': '1.0',
        'status': 'online',
        'endpoints': {
            'chat': '/api/chat',
            'health': '/api/health',
            'files': '/api/files (read-only)'
        },
        'note': 'Vercel deployment - Chat functionality only. PDF upload/delete requires full backend.'
    })

@app.route('/api/health')
def health():
    """Health check."""
    return jsonify({'status': 'ok'})

handler = app



