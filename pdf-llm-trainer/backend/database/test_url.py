"""Test Supabase URL connectivity."""
import sys
from pathlib import Path
import socket

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.config import SUPABASE_URL

print("=" * 60)
print("Testing Supabase URL Connectivity")
print("=" * 60)

if not SUPABASE_URL:
    print("[ERROR] SUPABASE_URL not set in .env")
    sys.exit(1)

print(f"\nSupabase URL: {SUPABASE_URL}")

# Extract hostname
if SUPABASE_URL.startswith("https://"):
    hostname = SUPABASE_URL.replace("https://", "").split("/")[0]
else:
    hostname = SUPABASE_URL.split("/")[0]

print(f"Hostname: {hostname}")

# Try DNS resolution
print(f"\n[1] Testing DNS resolution...")
try:
    ip = socket.gethostbyname(hostname)
    print(f"    [OK] Resolved to IP: {ip}")
except socket.gaierror as e:
    print(f"    [ERROR] DNS resolution failed: {e}")
    print(f"\nPossible issues:")
    print(f"    1. Supabase project might be paused")
    print(f"    2. URL might be incorrect")
    print(f"    3. Network/DNS issue")
    print(f"\nPlease verify:")
    print(f"    - Go to https://supabase.com/dashboard")
    print(f"    - Check project status")
    print(f"    - Copy the exact URL from Settings > API")
    sys.exit(1)

# Try TCP connection
print(f"\n[2] Testing TCP connection to port 443...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((hostname, 443))
    sock.close()
    if result == 0:
        print(f"    [OK] Port 443 is reachable")
    else:
        print(f"    [ERROR] Cannot connect to port 443")
except Exception as e:
    print(f"    [ERROR] Connection test failed: {e}")

print(f"\n[3] Testing Supabase client connection...")
try:
    from backend.database.client import get_client
    client = get_client()
    result = client.table("pdf_documents").select("id").limit(1).execute()
    print(f"    [OK] Supabase connection successful!")
    print(f"    Database is accessible")
except Exception as e:
    print(f"    [ERROR] Supabase client failed: {e}")
    error_msg = str(e).lower()
    if "getaddrinfo" in error_msg or "11001" in error_msg:
        print(f"\n    This is a DNS resolution issue.")
        print(f"    Even though DNS resolved, the Supabase API might not be accessible.")
        print(f"    Please check:")
        print(f"    1. Project is active (not paused)")
        print(f"    2. URL is correct: {SUPABASE_URL}")
        print(f"    3. Try accessing the URL in a browser")

