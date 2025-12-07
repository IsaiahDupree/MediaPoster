-- Add file_size column to videos table for large file support
-- This supports iPhone libraries with multi-GB video files

-- Add file_size column (BIGINT supports up to 9.2 exabytes)
ALTER TABLE videos ADD COLUMN IF NOT EXISTS file_size BIGINT;

-- Add index for querying by size (useful for filtering large files)
CREATE INDEX IF NOT EXISTS idx_videos_file_size ON videos(file_size);

-- Add comment for documentation
COMMENT ON COLUMN videos.file_size IS 'File size in bytes - supports large iPhone videos up to GB scale';

-- Verify the column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'videos' AND column_name = 'file_size';
