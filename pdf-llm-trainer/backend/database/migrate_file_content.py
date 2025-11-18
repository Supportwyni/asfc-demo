"""Temporary migration script to add file_content column to pdf_documents table."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.config import POSTGRES_CONNECTION_STRING, SUPABASE_URL, SUPABASE_KEY
from backend.database.client import get_client


def run_migration():
    """Run migration to add file_content column using Supabase RPC or direct SQL."""
    print("=" * 60)
    print("PDF File Content Migration")
    print("=" * 60)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return False
    
    # SQL to add file_content column
    migration_sql = """
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'pdf_documents' 
            AND column_name = 'file_content'
        ) THEN
            ALTER TABLE pdf_documents ADD COLUMN file_content BYTEA;
            RAISE NOTICE 'Added file_content column to pdf_documents table';
        ELSE
            RAISE NOTICE 'file_content column already exists';
        END IF;
    END $$;
    """
    
    try:
        print("\n[1] Connecting to Supabase...")
        client = get_client()
        
        print("[2] Checking if column exists...")
        # Try to query the table structure
        try:
            # Check by trying to select the column
            result = client.table("pdf_documents").select("file_content").limit(1).execute()
            print("[INFO] file_content column already exists - skipping migration")
            return True
        except Exception as check_error:
            # Column doesn't exist, proceed with migration
            if "column" in str(check_error).lower() or "does not exist" in str(check_error).lower():
                print("[3] Column not found - running migration...")
            else:
                print(f"[WARNING] Error checking column: {check_error}")
                print("[3] Attempting migration anyway...")
        
        # Use Supabase RPC to execute SQL (if available)
        # Otherwise, we'll need to use direct PostgreSQL connection
        print("[4] Attempting to add column via Supabase...")
        
        # Try using RPC if available
        try:
            # Note: Supabase doesn't directly support arbitrary SQL via RPC
            # We need to use PostgreSQL connection for DDL operations
            print("[INFO] Supabase client doesn't support DDL operations directly")
            print("[INFO] Please run this SQL manually in Supabase SQL Editor:")
            print("\n" + "=" * 60)
            print("SQL Migration:")
            print("=" * 60)
            print(migration_sql)
            print("=" * 60)
            print("\nOr use the PostgreSQL connection string if available.")
            
            # Try PostgreSQL connection as fallback
            if POSTGRES_CONNECTION_STRING:
                print("\n[5] Attempting direct PostgreSQL connection...")
                try:
                    import psycopg2
                    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
                    
                    conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
                    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                    cursor = conn.cursor()
                    
                    cursor.execute(migration_sql)
                    
                    # Verify
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'pdf_documents' 
                        AND column_name = 'file_content';
                    """)
                    result = cursor.fetchone()
                    
                    if result:
                        print("[SUCCESS] Migration completed successfully!")
                        print("    ✓ file_content column added to pdf_documents table")
                        cursor.close()
                        conn.close()
                        return True
                    else:
                        print("[WARNING] Migration executed but column not found")
                    
                    cursor.close()
                    conn.close()
                except Exception as pg_error:
                    print(f"[ERROR] PostgreSQL connection failed: {pg_error}")
                    print("\nPlease run the SQL manually in Supabase SQL Editor")
                    return False
            else:
                print("\n[ERROR] No PostgreSQL connection string available")
                print("Please run the SQL manually in Supabase SQL Editor")
                return False
                
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            print("\nPlease run the SQL manually in Supabase SQL Editor")
            return False
        
    except Exception as e:
        print(f"[ERROR] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease run the SQL manually in Supabase SQL Editor")
        return False


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)

