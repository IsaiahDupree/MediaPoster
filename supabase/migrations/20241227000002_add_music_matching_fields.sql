-- Migration: Add music matching fields for automatic background music association
-- Part of Auto Music Matching feature (Phase 1)

-- Add music matching columns to video_analysis table
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS suggested_music_id TEXT,
ADD COLUMN IF NOT EXISTS music_match_score NUMERIC(4,3),
ADD COLUMN IF NOT EXISTS music_match_reasoning TEXT,
ADD COLUMN IF NOT EXISTS music_alternatives JSONB,
ADD COLUMN IF NOT EXISTS music_matched_at TIMESTAMP WITH TIME ZONE;

-- Add music columns to scheduled_posts table
ALTER TABLE scheduled_posts
ADD COLUMN IF NOT EXISTS music_id TEXT,
ADD COLUMN IF NOT EXISTS include_music BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS music_volume NUMERIC(3,2) DEFAULT 0.30;

-- Add index for filtering by music suggestion status
CREATE INDEX IF NOT EXISTS idx_video_analysis_has_music_suggestion 
ON video_analysis (suggested_music_id) 
WHERE suggested_music_id IS NOT NULL;

-- Comments
COMMENT ON COLUMN video_analysis.suggested_music_id IS 'ID of auto-suggested background music track';
COMMENT ON COLUMN video_analysis.music_match_score IS 'Compatibility score 0.0-1.0 for suggested music';
COMMENT ON COLUMN video_analysis.music_match_reasoning IS 'Explanation of why music was matched';
COMMENT ON COLUMN video_analysis.music_alternatives IS 'Array of alternative music options [{music_id, score, reasoning}]';
COMMENT ON COLUMN video_analysis.music_matched_at IS 'When music matching was performed';

COMMENT ON COLUMN scheduled_posts.music_id IS 'Selected background music track ID';
COMMENT ON COLUMN scheduled_posts.include_music IS 'Whether to overlay music when publishing';
COMMENT ON COLUMN scheduled_posts.music_volume IS 'Music volume level 0.0-1.0 (default 0.30)';
