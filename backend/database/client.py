"""Supabase client initialization."""
from supabase import create_client, Client
from backend.database.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY

_client: Client | None = None
_service_client: Client | None = None


def get_client() -> Client:
    """
    Get or create Supabase client instance (uses anon key).
    
    Returns:
        Supabase client
    """
    global _client
    
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    return _client


def get_service_client() -> Client:
    """
    Get or create Supabase client instance with service role key (bypasses RLS).
    Use this for storage operations and admin tasks.
    
    Returns:
        Supabase client with service role
    """
    global _service_client
    
    if _service_client is None:
        if not SUPABASE_URL:
            raise ValueError("SUPABASE_URL must be set in .env")
        
        # Use service key if available, otherwise fall back to regular key
        key = SUPABASE_SERVICE_KEY if SUPABASE_SERVICE_KEY else SUPABASE_KEY
        if not key:
            raise ValueError("SUPABASE_KEY or SUPABASE_SERVICE_KEY must be set in .env")
        
        _service_client = create_client(SUPABASE_URL, key)
    
    return _service_client


def reset_client():
    """Reset client instance (useful for testing)."""
    global _client, _service_client
    _client = None
    _service_client = None

