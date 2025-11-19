"""Verify database setup after running COMPLETE_SETUP.sql"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.client import get_client
from backend.database.config import SUPABASE_URL, SUPABASE_KEY

def verify_setup():
    """Verify that all tables and columns were created correctly."""
    print("=" * 60)
    print("Verifying Database Setup")
    print("=" * 60)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return False
    
    try:
        client = get_client()
        
        print("\n[1] Checking pdf_documents table...")
        try:
            result = client.table("pdf_documents").select("id, filename, file_content").limit(1).execute()
            print("    ✓ pdf_documents table exists")
            print("    ✓ file_content column exists")
        except Exception as e:
            error_msg = str(e).lower()
            if "column" in error_msg and "file_content" in error_msg:
                print("    ✗ file_content column missing!")
                print("    Run: ALTER TABLE pdf_documents ADD COLUMN file_content BYTEA;")
                return False
            elif "relation" in error_msg or "does not exist" in error_msg:
                print("    ✗ pdf_documents table does not exist!")
                print("    Please run COMPLETE_SETUP.sql")
                return False
            else:
                raise
        
        print("\n[2] Checking chunks table...")
        try:
            result = client.table("chunks").select("id").limit(1).execute()
            print("    ✓ chunks table exists")
        except Exception as e:
            error_msg = str(e).lower()
            if "relation" in error_msg or "does not exist" in error_msg:
                print("    ✗ chunks table does not exist!")
                print("    Please run COMPLETE_SETUP.sql")
                return False
            else:
                raise
        
        print("\n[3] Checking chat_messages table...")
        try:
            result = client.table("chat_messages").select("id").limit(1).execute()
            print("    ✓ chat_messages table exists")
        except Exception as e:
            error_msg = str(e).lower()
            if "relation" in error_msg or "does not exist" in error_msg:
                print("    ✗ chat_messages table does not exist!")
                print("    Please run COMPLETE_SETUP.sql")
                return False
            else:
                raise
        
        print("\n[SUCCESS] All tables and columns are set up correctly!")
        print("\nNext steps:")
        print("1. Start the backend server: python -m backend.start")
        print("2. Start the frontend: cd frontend && npm run dev")
        print("3. Upload a PDF file through the admin panel")
        print("4. Check Supabase dashboard to verify PDF was stored")
        
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        if "getaddrinfo" in error_msg or "11001" in error_msg:
            print(f"\n[WARNING] DNS resolution failed - Supabase project might be paused")
            print("1. Go to https://supabase.com/dashboard")
            print("2. Check if project 'vummlugtiwjamyrkbuuc' is active")
            print("3. If paused, click 'Resume' or 'Restore'")
            print("\nIf project is active, the setup is complete!")
            print("You can test the upload functionality once the project is active.")
        else:
            print(f"\n[ERROR] Verification failed: {e}")
            import traceback
            traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verify_setup()
    sys.exit(0 if success else 1)

