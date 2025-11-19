"""Vercel serverless function for health check."""
import json

def handler(request):
    """Health check endpoint."""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'status': 'ok'})
    }
