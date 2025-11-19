"""Start the backend API server."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.api import app

if __name__ == '__main__':
    import socket
    
    # Check if port 5000 is available
    port = 5000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    
    if result == 0:
        print(f"[ERROR] Port {port} is already in use!")
        print("[INFO] Trying port 5001 instead...")
        port = 5001
    
    print("=" * 60)
    print("ASFC Backend API Server")
    print("=" * 60)
    print(f"Starting server on http://localhost:{port}")
    print(f"Frontend should connect to: http://localhost:{port}/api")
    print("=" * 60)
    
    try:
        app.run(debug=True, port=port, host='127.0.0.1')
    except OSError as e:
        print(f"[ERROR] Failed to start server: {e}")
        sys.exit(1)

