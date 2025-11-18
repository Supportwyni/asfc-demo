-- TEMPORARY MIGRATION: Add file_content column to pdf_documents table
-- Run this SQL in your Supabase SQL Editor to add PDF file storage capability
-- This is a temporary solution for manual PDF transfer to database

-- Add file_content column if it doesn't exist
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

-- Note: After testing, you may want to remove this column or move PDFs to Supabase Storage
-- To remove: ALTER TABLE pdf_documents DROP COLUMN file_content;

