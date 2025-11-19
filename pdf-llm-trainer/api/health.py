"""Vercel serverless function for health check."""
from flask import jsonify

def handler(request):
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200, {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

