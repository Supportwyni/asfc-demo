"""Test Supabase database connection."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.client import get_client
from backend.database.config import SUPABASE_URL, SUPABASE_KEY

def test_connection():
    """Test Supabase connection."""
    print("=" * 60)
    print("Testing Supabase Connection")
    print("=" * 60)
    
    # Check config
    print(f"\n[1] Configuration Check:")
    print(f"    URL: {SUPABASE_URL}")
    print(f"    Key: {'[OK] Loaded' if SUPABASE_KEY else '[MISSING] NOT SET'}")
    print(f"    Key Length: {len(SUPABASE_KEY) if SUPABASE_KEY else 0}")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n[ERROR] SUPABASE_URL and SUPABASE_KEY must be set in .env file!")
        return False
    
    # Test connection
    print(f"\n[2] Testing Connection:")
    try:
        client = get_client()
        
        # Try to list tables (this will work even if tables don't exist yet)
        # First, try a simple query to see if connection works
        try:
            result = client.table("pdf_documents").select("id").limit(1).execute()
            print(f"    [SUCCESS] Connection successful!")
            print(f"    Database is accessible")
            print(f"    Tables exist: ✓")
            return True
        except Exception as table_error:
            # If table doesn't exist, connection still works
            if "relation" in str(table_error).lower() or "does not exist" in str(table_error).lower():
                print(f"    [WARNING] Connection works but tables don't exist yet")
                print(f"    Please run schema.sql in Supabase SQL Editor")
                print(f"    Error: {table_error}")
                return False
            else:
                raise table_error
    
    except Exception as e:
        print(f"    [ERROR] Connection failed: {e}")
        print(f"\nTroubleshooting:")
        print(f"    1. Check if Supabase project is active")
        print(f"    2. Verify URL: {SUPABASE_URL}")
        print(f"    3. Check network connection")
        print(f"    4. Make sure you've run schema.sql in Supabase SQL Editor")
        return False

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)

