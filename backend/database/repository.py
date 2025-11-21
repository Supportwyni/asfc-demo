"""Database repository for CRUD operations."""
from typing import List, Optional, Dict, Any
import numpy as np
from backend.database.client import get_client
from backend.database.models import PDFDocument, ChatMessage, Chunk
from backend.embeddings import generate_embedding, generate_embeddings_batch
from backend.config import USE_SEMANTIC_SEARCH


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))
    except Exception as e:
        print(f"[ERROR] Cosine similarity calculation failed: {e}")
        return 0.0


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
    
    @staticmethod
    def update(document_id: int, document: PDFDocument) -> Dict[str, Any]:
        """Update an existing PDF document record."""
        client = get_client()
        data = document.dict(exclude_none=True)
        
        # Convert file_content bytes to base64 for Supabase storage
        if 'file_content' in data and data['file_content'] is not None:
            import base64
            data['file_content'] = base64.b64encode(data['file_content']).decode('utf-8')
        
        # Remove id from update data (it's used in the where clause)
        update_data = {k: v for k, v in data.items() if k != 'id'}
        
        result = client.table("pdf_documents").update(update_data).eq("id", document_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    def delete(document_id: int) -> bool:
        """Delete a PDF document record."""
        client = get_client()
        result = client.table("pdf_documents").delete().eq("id", document_id).execute()
        return True


class ChunkRepository:
    """Repository for chunk operations."""
    
    @staticmethod
    def create(chunk: Chunk) -> Dict[str, Any]:
        """Create a new chunk record with embedding."""
        client = get_client()
        data = chunk.dict(exclude_none=True)
        
        # Generate embedding if not already provided
        if not data.get('embedding') and chunk.text:
            embedding = generate_embedding(chunk.text)
            if embedding:
                data['embedding'] = embedding
        
        result = client.table("chunks").insert(data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    def create_batch(chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """Create multiple chunks in batch with embeddings."""
        client = get_client()
        
        # Generate embeddings for chunks that don't have them
        texts_to_embed = []
        indices_to_embed = []
        for i, chunk in enumerate(chunks):
            if not chunk.embedding and chunk.text:
                texts_to_embed.append(chunk.text)
                indices_to_embed.append(i)
        
        # Generate embeddings in batch
        if texts_to_embed:
            embeddings = generate_embeddings_batch(texts_to_embed, batch_size=10)
            for idx, embedding in zip(indices_to_embed, embeddings):
                if embedding:
                    chunks[idx].embedding = embedding
        
        data = [chunk.dict(exclude_none=True) for chunk in chunks]
        
        result = client.table("chunks").insert(data).execute()
        return result.data if result.data else []
    
    @staticmethod
    def search_by_text(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search chunks using semantic search (preferred) or text search (fallback).
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
        
        Returns:
            List of matching chunks ordered by relevance
        """
        client = get_client()
        
        # Try semantic search first if enabled
        if USE_SEMANTIC_SEARCH:
            query_embedding = generate_embedding(query)
            if query_embedding:
                try:
                    # Use PostgreSQL vector similarity search via Supabase RPC
                    # Note: This requires a PostgreSQL function for cosine similarity
                    # We'll use a workaround with raw SQL if RPC doesn't work
                    
                    # Try to use vector similarity search
                    # Format: SELECT *, 1 - (embedding <=> query_embedding) as similarity
                    # where <=> is cosine distance operator in pgvector
                    
                    # Convert embedding to string format for PostgreSQL
                    embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                    
                    # Use Supabase's RPC or raw query for vector search
                    # For now, we'll fetch all chunks and compute similarity in Python
                    # (This is not ideal for large datasets, but works)
                    
                    # Alternative: Use Supabase PostgREST with a custom function
                    # For production, you should create a PostgreSQL function
                    
                    # Fallback: Get chunks and compute similarity
                    all_chunks_result = client.table("chunks").select("*").not_.is_("embedding", "null").limit(1000).execute()
                    
                    if all_chunks_result.data:
                        chunks_with_similarity = []
                        for chunk in all_chunks_result.data:
                            chunk_embedding = chunk.get('embedding')
                            if chunk_embedding:
                                # Compute cosine similarity
                                similarity = cosine_similarity(query_embedding, chunk_embedding)
                                chunks_with_similarity.append((similarity, chunk))
                        
                        # Sort by similarity and return top results
                        chunks_with_similarity.sort(key=lambda x: x[0], reverse=True)
                        return [chunk for _, chunk in chunks_with_similarity[:limit]]
                
                except Exception as e:
                    print(f"[WARNING] Semantic search failed, falling back to text search: {e}")
        
        # Fallback to text-based search
        query_words = query.lower().split()
        query_words = [w.strip() for w in query_words if len(w.strip()) > 2]  # Filter out short words
        
        if not query_words:
            # Fallback to original method if no valid words
            result = client.table("chunks").select("*").ilike("text", f"%{query}%").limit(limit).execute()
            return result.data if result.data else []
        
        # Search for chunks containing ANY of the query words
        # Use OR logic: chunk contains word1 OR word2 OR word3...
        all_results = []
        seen_ids = set()
        
        for word in query_words:
            word_result = client.table("chunks").select("*").ilike("text", f"%{word}%").limit(limit * 2).execute()
            if word_result.data:
                for chunk in word_result.data:
                    chunk_id = chunk.get('id')
                    if chunk_id and chunk_id not in seen_ids:
                        seen_ids.add(chunk_id)
                        all_results.append(chunk)
        
        # Return up to limit results
        return all_results[:limit]
    
    @staticmethod
    def search_semantic(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Semantic search using vector embeddings.
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
        
        Returns:
            List of matching chunks ordered by similarity
        """
        query_embedding = generate_embedding(query)
        if not query_embedding:
            # Fallback to text search if embedding generation fails
            return ChunkRepository.search_by_text(query, limit)
        
        client = get_client()
        
        # Get chunks with embeddings
        # Note: For better performance with large datasets, use PostgreSQL vector search
        # For now, we'll fetch chunks and compute similarity
        all_chunks_result = client.table("chunks").select("*").not_.is_("embedding", "null").limit(2000).execute()
        
        if not all_chunks_result.data:
            # No chunks with embeddings, fallback to text search
            return ChunkRepository.search_by_text(query, limit)
        
        chunks_with_similarity = []
        for chunk in all_chunks_result.data:
            chunk_embedding = chunk.get('embedding')
            if chunk_embedding:
                # Compute cosine similarity
                similarity = cosine_similarity(query_embedding, chunk_embedding)
                chunks_with_similarity.append((similarity, chunk))
        
        # Sort by similarity and return top results
        chunks_with_similarity.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in chunks_with_similarity[:limit]]
    
    @staticmethod
    def get_by_source(source: str) -> List[Dict[str, Any]]:
        """
        Get all chunks from a specific source PDF.
        Supports both exact match and partial match (e.g., "Bulletin-113" matches "Bulletin-113-*.pdf").
        """
        client = get_client()
        
        # First try exact match
        result = client.table("chunks").select("*").eq("source", source).execute()
        if result.data:
            return result.data
        
        # If no exact match, try prefix match (for cases like "Bulletin-113" matching "Bulletin-113-*.pdf")
        # Use ilike for case-insensitive partial matching
        result = client.table("chunks").select("*").ilike("source", f"{source}%").execute()
        if result.data:
            return result.data
        
        # Also try matching with .pdf extension
        result = client.table("chunks").select("*").ilike("source", f"{source}.pdf").execute()
        if result.data:
            return result.data
        
        return []
    
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

