-- TEMPORARY: Add file_content column to pdf_documents table
-- IMPORTANT: Make sure pdf_documents table exists first!
-- If you get "relation does not exist" error, run COMPLETE_SETUP.sql instead

-- First, check if table exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'pdf_documents'
    ) THEN
        RAISE EXCEPTION 'pdf_documents table does not exist. Please run COMPLETE_SETUP.sql first!';
    END IF;
END $$;

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

-- Verify the column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'pdf_documents' 
AND column_name = 'file_content';

