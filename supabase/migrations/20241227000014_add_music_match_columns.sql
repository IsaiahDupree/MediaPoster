-- Add music matching columns to video_analysis table
-- These columns are used by the music suggestion feature

ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS suggested_music_id UUID;
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS music_match_score FLOAT;
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS music_match_reasoning TEXT;
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS music_alternatives JSONB;
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS music_matched_at TIMESTAMPTZ;

COMMENT ON COLUMN video_analysis.suggested_music_id IS 'ID of the suggested music track from music library';
COMMENT ON COLUMN video_analysis.music_match_score IS 'Confidence score (0-1) of the music match';
COMMENT ON COLUMN video_analysis.music_match_reasoning IS 'AI explanation for why this music was suggested';
COMMENT ON COLUMN video_analysis.music_alternatives IS 'Array of alternative music suggestions with scores';
COMMENT ON COLUMN video_analysis.music_matched_at IS 'Timestamp when music matching was performed';
