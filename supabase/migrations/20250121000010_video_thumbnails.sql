-- Add thumbnail support to videos table
-- Migration 009: Video Thumbnails

ALTER TABLE videos
ADD COLUMN thumbnail_path TEXT,
ADD COLUMN thumbnail_generated_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN best_frame_score DECIMAL(5,3);

-- Add comment
COMMENT ON COLUMN videos.thumbnail_path IS 'Path to generated thumbnail image';
COMMENT ON COLUMN videos.thumbnail_generated_at IS 'When thumbnail was generated';
COMMENT ON COLUMN videos.best_frame_score IS 'Quality score of selected thumbnail frame (0-1)';

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_videos_thumbnail_generated 
  ON videos(thumbnail_generated_at) 
  WHERE thumbnail_path IS NOT NULL;

-- Index for videos without thumbnails (for batch processing)
CREATE INDEX IF NOT EXISTS idx_videos_no_thumbnail
  ON videos(id)
  WHERE thumbnail_path IS NULL;
