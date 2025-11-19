-- Supabase Database Schema for ASFC
-- Run this SQL in your Supabase SQL Editor

-- PDF Documents Table
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

-- Chunks Table (for storing PDF text chunks)
CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES pdf_documents(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    page INTEGER NOT NULL,
    text TEXT NOT NULL,
    chunk_index INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    embedding VECTOR(1536) -- For vector search (optional, requires pgvector extension)
);

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
CREATE POLICY "Allow all operations on pdf_documents" ON pdf_documents FOR ALL USING (true);
CREATE POLICY "Allow all operations on chunks" ON chunks FOR ALL USING (true);
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
CREATE TRIGGER update_pdf_documents_updated_at BEFORE UPDATE ON pdf_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

