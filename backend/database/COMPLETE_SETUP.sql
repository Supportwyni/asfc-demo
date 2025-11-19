-- Complete Supabase Database Setup for ASFC
-- Run this SQL in your Supabase SQL Editor to create all tables and columns

-- PDF Documents Table (creates table if it doesn't exist)
CREATE TABLE IF NOT EXISTS pdf_documents (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    chunks_count INTEGER DEFAULT 0,
    pages_count INTEGER DEFAULT 0,
    file_size BIGINT,
    status VARCHAR(50) DEFAULT 'processing',
    metadata JSONB,
    file_content BYTEA, -- TEMPORARY: Store PDF file content in database
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable pgvector extension if available (for vector embeddings)
-- This is optional - if pgvector is not installed, embedding column will be skipped
DO $$ 
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
    RAISE NOTICE 'pgvector extension enabled';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'pgvector extension not available - embedding column will be skipped';
END $$;

-- Chunks Table (for storing PDF text chunks)
CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES pdf_documents(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    page INTEGER NOT NULL,
    text TEXT NOT NULL,
    chunk_index INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add embedding column only if pgvector extension is available
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'chunks' AND column_name = 'embedding'
        ) THEN
            ALTER TABLE chunks ADD COLUMN embedding vector(1536);
            RAISE NOTICE 'Added embedding column to chunks table';
        END IF;
    ELSE
        RAISE NOTICE 'pgvector not available - skipping embedding column';
    END IF;
END $$;

-- Chat Messages Table
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    sources TEXT[], -- Array of source PDF filenames
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_text_search ON chunks USING gin(to_tsvector('english', text));
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdf_documents_filename ON pdf_documents(filename);
CREATE INDEX IF NOT EXISTS idx_pdf_documents_status ON pdf_documents(status);

-- Enable Row Level Security (RLS) - adjust policies as needed
ALTER TABLE pdf_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Basic policies (allow all for now - adjust based on your security needs)
DROP POLICY IF EXISTS "Allow all operations on pdf_documents" ON pdf_documents;
CREATE POLICY "Allow all operations on pdf_documents" ON pdf_documents FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on chunks" ON chunks;
CREATE POLICY "Allow all operations on chunks" ON chunks FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow all operations on chat_messages" ON chat_messages;
CREATE POLICY "Allow all operations on chat_messages" ON chat_messages FOR ALL USING (true);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_pdf_documents_updated_at ON pdf_documents;
CREATE TRIGGER update_pdf_documents_updated_at BEFORE UPDATE ON pdf_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add file_content column if it doesn't exist (for existing tables)
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

-- Verify tables were created
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('pdf_documents', 'chunks', 'chat_messages')
ORDER BY table_name, ordinal_position;

