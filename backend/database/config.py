"""Supabase database configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load environment variables
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), override=True)
else:
    load_dotenv(override=True)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Anon key for regular operations
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # Service role key for storage/admin operations
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD", "asfc9812!")

# PostgreSQL direct connection (optional, for direct DB access)
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING", "")

# Database connection settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))

