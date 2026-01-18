-- Migration: Add audio analysis fields for background music detection
-- Part of Background Music Detection feature (Phase 1)

-- Add new columns to video_analysis table for audio/music detection
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS audio_analysis JSONB,
ADD COLUMN IF NOT EXISTS has_background_music BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS audio_type TEXT,
ADD COLUMN IF NOT EXISTS music_confidence NUMERIC(4,3),
ADD COLUMN IF NOT EXISTS speech_ratio NUMERIC(4,3),
ADD COLUMN IF NOT EXISTS music_characteristics JSONB,
ADD COLUMN IF NOT EXISTS copyright_risk TEXT DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS audio_analyzed_at TIMESTAMP WITH TIME ZONE;

-- Add index for filtering by music presence
CREATE INDEX IF NOT EXISTS idx_video_analysis_has_music 
ON video_analysis (has_background_music) 
WHERE has_background_music IS NOT NULL;

-- Add index for audio type filtering
CREATE INDEX IF NOT EXISTS idx_video_analysis_audio_type 
ON video_analysis (audio_type) 
WHERE audio_type IS NOT NULL;

-- Add comment explaining the fields
COMMENT ON COLUMN video_analysis.audio_analysis IS 'Full audio analysis result including segments, characteristics';
COMMENT ON COLUMN video_analysis.has_background_music IS 'Quick boolean flag: true if music detected, false if speech-only';
COMMENT ON COLUMN video_analysis.audio_type IS 'Classification: speech_only, music_only, mixed, silence, ambient';
COMMENT ON COLUMN video_analysis.music_confidence IS 'Confidence score 0.0-1.0 for music detection';
COMMENT ON COLUMN video_analysis.speech_ratio IS 'Ratio of speech to total audio duration 0.0-1.0';
COMMENT ON COLUMN video_analysis.music_characteristics IS 'Music details: tempo_bpm, energy, genre_hints, mood';
COMMENT ON COLUMN video_analysis.copyright_risk IS 'Estimated copyright risk: low, medium, high, unknown';
COMMENT ON COLUMN video_analysis.audio_analyzed_at IS 'Timestamp when audio analysis was performed';
