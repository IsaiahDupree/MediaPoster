-- Fix account_id column type in posted_content table
-- The column should be TEXT to store Blotato account IDs (like "710")

-- Drop the column if it exists with wrong type and recreate
DO $$ 
BEGIN
    -- Check if column exists and alter if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'posted_content' AND column_name = 'account_id'
    ) THEN
        -- Alter the column type to TEXT
        ALTER TABLE posted_content ALTER COLUMN account_id TYPE TEXT USING account_id::TEXT;
    END IF;
END $$;

-- Ensure the column exists as TEXT
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS account_id TEXT;
