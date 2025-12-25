-- Add title column to videos table for AI-generated titles
ALTER TABLE videos ADD COLUMN IF NOT EXISTS title VARCHAR(150);

-- Add comment explaining the column
COMMENT ON COLUMN videos.title IS 'AI-generated title (~20% of platform character limit)';
