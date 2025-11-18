"""Database models for Supabase tables."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class PDFDocument(BaseModel):
    """PDF document model."""
    id: Optional[int] = None
    filename: str
    uploaded_at: Optional[datetime] = None
    chunks_count: Optional[int] = None
    pages_count: Optional[int] = None
    file_size: Optional[int] = None
    status: str = "processed"  # processed, processing, error
    metadata: Optional[Dict[str, Any]] = None
    file_content: Optional[bytes] = None  # TEMPORARY: PDF file content stored in database


class ChatMessage(BaseModel):
    """Chat message model."""
    id: Optional[int] = None
    user_id: Optional[str] = None
    question: str
    response: str
    created_at: Optional[datetime] = None
    sources: Optional[list[str]] = None  # List of source PDFs used
    metadata: Optional[Dict[str, Any]] = None


class Chunk(BaseModel):
    """Text chunk model."""
    id: Optional[int] = None
    document_id: Optional[int] = None
    source: str  # PDF filename
    page: int
    text: str
    chunk_index: Optional[int] = None
    created_at: Optional[datetime] = None

