"""Supabase client initialization."""
from supabase import create_client, Client
from backend.database.config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None


def get_client() -> Client:
    """
    Get or create Supabase client instance.
    
    Returns:
        Supabase client
    """
    global _client
    
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    return _client


def reset_client():
    """Reset client instance (useful for testing)."""
    global _client
    _client = None

