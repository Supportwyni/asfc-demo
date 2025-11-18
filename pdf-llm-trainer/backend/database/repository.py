"""Database repository for CRUD operations."""
from typing import List, Optional, Dict, Any
from backend.database.client import get_client
from backend.database.models import PDFDocument, ChatMessage, Chunk


class PDFRepository:
    """Repository for PDF document operations."""
    
    @staticmethod
    def create(document: PDFDocument) -> Dict[str, Any]:
        """Create a new PDF document record."""
        client = get_client()
        data = document.dict(exclude_none=True)
        
        # TEMPORARY: Convert file_content bytes to base64 for Supabase storage
        # Supabase/PostgreSQL BYTEA can be stored directly, but Supabase client may need base64
        if 'file_content' in data and data['file_content'] is not None:
            import base64
            # Convert bytes to base64 string for JSON serialization
            data['file_content'] = base64.b64encode(data['file_content']).decode('utf-8')
        
        result = client.table("pdf_documents").insert(data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    def get_by_filename(filename: str) -> Optional[Dict[str, Any]]:
        """Get PDF document by filename."""
        client = get_client()
        result = client.table("pdf_documents").select("*").eq("filename", filename).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def get_by_id(document_id: int) -> Optional[Dict[str, Any]]:
        """Get PDF document by ID."""
        client = get_client()
        result = client.table("pdf_documents").select("*").eq("id", document_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def list_all(limit: int = 100) -> List[Dict[str, Any]]:
        """List all PDF documents."""
        client = get_client()
        result = client.table("pdf_documents").select("*").order("uploaded_at", desc=True).limit(limit).execute()
        return result.data if result.data else []
    
    @staticmethod
    def update_status(filename: str, status: str, chunks_count: Optional[int] = None, pages_count: Optional[int] = None):
        """Update PDF document status."""
        client = get_client()
        update_data = {"status": status}
        if chunks_count is not None:
            update_data["chunks_count"] = chunks_count
        if pages_count is not None:
            update_data["pages_count"] = pages_count
        
        client.table("pdf_documents").update(update_data).eq("filename", filename).execute()
    
    @staticmethod
    def update_metadata(filename: str, metadata: Dict[str, Any]):
        """Update PDF document metadata."""
        client = get_client()
        client.table("pdf_documents").update({"metadata": metadata}).eq("filename", filename).execute()


class ChunkRepository:
    """Repository for chunk operations."""
    
    @staticmethod
    def create(chunk: Chunk) -> Dict[str, Any]:
        """Create a new chunk record."""
        client = get_client()
        data = chunk.dict(exclude_none=True)
        
        result = client.table("chunks").insert(data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    def create_batch(chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """Create multiple chunks in batch."""
        client = get_client()
        data = [chunk.dict(exclude_none=True) for chunk in chunks]
        
        result = client.table("chunks").insert(data).execute()
        return result.data if result.data else []
    
    @staticmethod
    def search_by_text(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search chunks by text content (full-text search)."""
        client = get_client()
        # Note: This requires a full-text search setup in Supabase
        # For now, using basic filtering
        result = client.table("chunks").select("*").ilike("text", f"%{query}%").limit(limit).execute()
        return result.data if result.data else []
    
    @staticmethod
    def get_by_source(source: str) -> List[Dict[str, Any]]:
        """Get all chunks from a specific source PDF."""
        client = get_client()
        result = client.table("chunks").select("*").eq("source", source).execute()
        return result.data if result.data else []
    
    @staticmethod
    def get_by_document_id(document_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document ID."""
        client = get_client()
        result = client.table("chunks").select("*").eq("document_id", document_id).execute()
        return result.data if result.data else []


class ChatRepository:
    """Repository for chat message operations."""
    
    @staticmethod
    def create(message: ChatMessage) -> Dict[str, Any]:
        """Create a new chat message record."""
        client = get_client()
        data = message.dict(exclude_none=True)
        
        result = client.table("chat_messages").insert(data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    def get_by_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat messages for a specific user."""
        client = get_client()
        result = client.table("chat_messages").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return result.data if result.data else []
    
    @staticmethod
    def get_recent(limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chat messages."""
        client = get_client()
        result = client.table("chat_messages").select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data if result.data else []

