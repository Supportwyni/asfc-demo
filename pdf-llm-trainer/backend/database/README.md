# Supabase Database Setup

## Configuration

1. Add to your `.env` file:
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_PASSWORD=asfc9812!
```

## Database Schema

Run the SQL in `schema.sql` in your Supabase SQL Editor to create the required tables:

- `pdf_documents` - Stores uploaded PDF metadata
- `chunks` - Stores text chunks from PDFs
- `chat_messages` - Stores chat conversation history

## Installation

```bash
pip install -r ../requirements.txt
```

## Usage

```python
from backend.database.client import get_client
from backend.database.repository import PDFRepository, ChunkRepository

# Get Supabase client
client = get_client()

# Use repositories
pdf_repo = PDFRepository()
chunk_repo = ChunkRepository()
```

## Tables

### pdf_documents
- `id` - Primary key
- `filename` - PDF filename (unique)
- `uploaded_at` - Upload timestamp
- `chunks_count` - Number of chunks created
- `pages_count` - Number of pages
- `file_size` - File size in bytes
- `status` - Processing status
- `metadata` - Additional JSON data

### chunks
- `id` - Primary key
- `document_id` - Foreign key to pdf_documents
- `source` - PDF filename
- `page` - Page number
- `text` - Chunk text content
- `chunk_index` - Chunk order index
- `embedding` - Vector embedding (optional, for semantic search)

### chat_messages
- `id` - Primary key
- `user_id` - User identifier
- `question` - User question
- `response` - AI response
- `sources` - Array of source PDFs used
- `metadata` - Additional JSON data
- `created_at` - Message timestamp

