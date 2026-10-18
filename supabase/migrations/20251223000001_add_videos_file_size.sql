-- Add missing file_size column to videos table
-- The SQLAlchemy model defines this column but it was missing from the original migration

ALTER TABLE videos ADD COLUMN IF NOT EXISTS file_size BIGINT;

COMMENT ON COLUMN videos.file_size IS 'File size in bytes';
