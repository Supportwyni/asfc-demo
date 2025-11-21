"""Start the backend API server."""

import sys
from pathlib import Path
import argparse  # Import the argparse module for command-line argument parsing
import socket  # Import the socket module for port availability checking

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.api import app


# --- Helper function: Check if a port is in use ---
def is_port_in_use(host, port):
    """
    Checks if the specified IP and port are currently in use.
    Returns True if the port is occupied, False if available.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            # Try to bind the socket to the given host and port
            s.bind((host, port))
            return False  # Port is available
        except socket.error:
            return True  # Port is in use


if __name__ == "__main__":
    # --- 1. Set up command-line argument parser ---
    parser = argparse.ArgumentParser(
        description="ASFC Backend API Server. Listens on a specified IP and port."
    )
    parser.add_argument(
        "--host",
        "-H",
        type=str,
        default="127.0.0.1",
        help="The IP address to listen on (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        "-P",
        type=int,
        default=5000,
        help="The port number to listen on (default: 5000)",
    )

    # --- 2. Parse command-line arguments ---
    args = parser.parse_args()

    # Get the host and port specified by the user or default values
    listen_host = args.host
    listen_port = args.port
    original_port_specified = (
        listen_port  # Keep track of the port initially specified by user/default
    )

    # --- 3. Port availability checking logic ---
    # If the user did not explicitly specify a port (i.e., using the default 5000),
    # then try 5001 if 5000 is occupied.
    if original_port_specified == 5000:
        if is_port_in_use(listen_host, listen_port):
            print(f"[ERROR] Port {listen_port} is already in use on {listen_host}!")
            print(f"[INFO] Trying port {listen_port + 1} instead...")
            listen_port += 1
            # Check if the next port is also available
            if is_port_in_use(listen_host, listen_port):
                print(f"[ERROR] Port {listen_port} is also in use on {listen_host}.")
                print("Please specify an available port using the --port argument.")
                sys.exit(1)
    # If the user explicitly specified a port, only check that specific port.
    # If it's in use, exit with an error.
    else:
        if is_port_in_use(listen_host, listen_port):
            print(f"[ERROR] Port {listen_port} is already in use on {listen_host}.")
            print("Please specify an available port using the --port argument.")
            sys.exit(1)

    # --- 4. Print server information and start ---
    print("=" * 60)
    print("ASFC Backend API Server")
    print("=" * 60)
    print(f"Starting server on http://{listen_host}:{listen_port}")
    print(f"Frontend should connect to: http://{listen_host}:{listen_port}/api")
    print("=" * 60)

    try:
        app.run(debug=True, port=listen_port, host=listen_host)
    except OSError as e:
        print(f"[ERROR] Failed to start server: {e}")
        sys.exit(1)
