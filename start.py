"""Start both backend and frontend servers concurrently."""
import subprocess
import sys
import time
import signal
import os
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Store processes for cleanup
backend_process = None
frontend_process = None


def cleanup(backend_proc=None, frontend_proc=None, signum=None, frame=None):
    """Cleanup function to stop both servers."""
    print("\n" + "=" * 60)
    print("Stopping servers...")
    print("=" * 60)
    
    if backend_proc:
        try:
            backend_proc.terminate()
            backend_proc.wait(timeout=5)
            print("✓ Backend stopped")
        except:
            backend_proc.kill()
            print("✓ Backend force stopped")
    
    if frontend_proc:
        try:
            frontend_proc.terminate()
            frontend_proc.wait(timeout=5)
            print("✓ Frontend stopped")
        except:
            frontend_proc.kill()
            print("✓ Frontend force stopped")
    
    print("=" * 60)
    sys.exit(0)


# Global process references
backend_process = None
frontend_process = None


def check_port(port):
    """Check if a port is available."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0


def wait_for_backend(max_wait=30):
    """Wait for backend to be ready."""
    import urllib.request
    import urllib.error
    
    for i in range(max_wait):
        try:
            urllib.request.urlopen('http://localhost:5000/api/health', timeout=1)
            return True
        except:
            time.sleep(1)
    return False


def main():
    """Main function to start both servers."""
    global backend_process, frontend_process
    
    # Register signal handlers
    def signal_handler(signum, frame):
        cleanup(backend_process, frontend_process, signum, frame)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("Starting ASFC Application (Backend + Frontend)")
    print("=" * 60)
    print()
    
    # Check for existing processes on ports
    print("[1/3] Checking ports...")
    if check_port(5000):
        print("   [WARNING] Port 5000 is already in use!")
    if check_port(5173):
        print("   [WARNING] Port 5173 is already in use!")
    print()
    
    # Start backend
    print("[2/3] Starting backend server on http://localhost:5000...")
    try:
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "backend.start"],
            cwd=str(PROJECT_ROOT)
        )
        print(f"   Backend started with PID: {backend_process.pid}")
        
        # Wait for backend to be ready
        print("   Waiting for backend to initialize...")
        if wait_for_backend():
            print("   [OK] Backend is running!")
        else:
            print("   [WARNING] Backend may still be starting...")
    except Exception as e:
        print(f"   [ERROR] Failed to start backend: {e}")
        sys.exit(1)
    
    print()
    
    # Start frontend
    print("[3/3] Starting frontend server on http://localhost:5173...")
    
    # Check if node_modules exists
    frontend_node_modules = FRONTEND_DIR / "node_modules"
    if not frontend_node_modules.exists():
        print("   Installing frontend dependencies...")
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["npm", "install"],
                    cwd=str(FRONTEND_DIR),
                    check=True,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                subprocess.run(
                    ["npm", "install"],
                    cwd=str(FRONTEND_DIR),
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            print("   [OK] Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"   [ERROR] Failed to install dependencies: {e}")
            cleanup(backend_process, None)
            sys.exit(1)
    
    try:
        # On Windows, use shell=True for npm commands
        if sys.platform == "win32":
            frontend_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(FRONTEND_DIR),
                shell=True
            )
        else:
            frontend_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(FRONTEND_DIR)
            )
        print(f"   Frontend started with PID: {frontend_process.pid}")
    except Exception as e:
        print(f"   [ERROR] Failed to start frontend: {e}")
        print(f"   [INFO] Make sure npm is installed and in your PATH")
        cleanup(backend_process, None)
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("Both servers are running!")
    print("=" * 60)
    print()
    print(f"✓ Backend:  http://localhost:5000 (PID: {backend_process.pid})")
    print(f"✓ Frontend: http://localhost:5173 (PID: {frontend_process.pid})")
    print()
    print("Open your browser and go to: http://localhost:5173")
    print()
    print("Press Ctrl+C to stop both servers")
    print()
    
    # Keep script running and wait for processes
    try:
        # Wait for both processes (or until Ctrl+C)
        while backend_process.poll() is None or frontend_process.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    cleanup(backend_process, frontend_process)


if __name__ == "__main__":
    main()

