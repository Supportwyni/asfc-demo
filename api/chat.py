"""Vercel serverless function for chat endpoint."""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rag import ask_with_rag

app = Flask(__name__)

# Enable CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    try:
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        response = ask_with_rag(question)
        
        return jsonify({
            'response': response,
            'success': True
        })
    
    except Exception as e:
        print(f"[ERROR] Exception in /api/chat: {str(e)}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})

# Vercel requires the app to be exported
handler = app



