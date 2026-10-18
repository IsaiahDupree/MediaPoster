-- Migration: Add media_type field to scheduled_posts for Story/Reel support
-- Part of Story Posting feature

-- Add media_type column to scheduled_posts table
-- Values: 'reel' (default for Instagram), 'story', 'post', 'video', NULL
ALTER TABLE scheduled_posts 
ADD COLUMN IF NOT EXISTS media_type TEXT DEFAULT NULL;

-- Add index for filtering by media type
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_media_type 
ON scheduled_posts (media_type) 
WHERE media_type IS NOT NULL;

-- Add comment explaining the field
COMMENT ON COLUMN scheduled_posts.media_type IS 'Media type for platform-specific posting: reel, story, post, video. Default reel for Instagram.';
