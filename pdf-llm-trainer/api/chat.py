"""Vercel serverless function for chat endpoint."""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.rag import ask_with_rag

app = Flask(__name__)
CORS(app)

def handler(request):
    """Vercel serverless function handler."""
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    try:
        data = request.get_json() or {}
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        response = ask_with_rag(question)
        
        return jsonify({
            'response': response,
            'success': True
        }), 200, {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500, {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }

