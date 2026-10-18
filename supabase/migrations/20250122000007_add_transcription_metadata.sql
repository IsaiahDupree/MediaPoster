-- Migration: Add comprehensive transcription metadata fields
-- Store all available data from OpenAI Whisper transcription

-- Add transcription metadata columns to video_analysis table
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS transcription_data JSONB,              -- Full transcription response (words, segments, etc.)
ADD COLUMN IF NOT EXISTS transcription_language TEXT,           -- Detected language (e.g., 'en', 'es')
ADD COLUMN IF NOT EXISTS transcription_duration_sec NUMERIC(10, 3),  -- Duration in seconds from Whisper
ADD COLUMN IF NOT EXISTS transcription_word_count INTEGER,      -- Total word count
ADD COLUMN IF NOT EXISTS transcription_segment_count INTEGER,   -- Total segment count
ADD COLUMN IF NOT EXISTS words_per_minute NUMERIC(6, 2),        -- Speaking pace
ADD COLUMN IF NOT EXISTS significant_pauses JSONB,              -- Array of pauses > 1s [{after_word, duration, time}]
ADD COLUMN IF NOT EXISTS avg_confidence NUMERIC(6, 4),          -- Average logprob across segments
ADD COLUMN IF NOT EXISTS silence_ratio NUMERIC(4, 3),           -- Ratio of silence/no-speech
ADD COLUMN IF NOT EXISTS transcribed_at TIMESTAMP WITH TIME ZONE;  -- When transcription was performed

-- Add index for filtering by language
CREATE INDEX IF NOT EXISTS idx_video_analysis_transcription_language 
ON video_analysis (transcription_language) 
WHERE transcription_language IS NOT NULL;

-- Add index for pacing analysis
CREATE INDEX IF NOT EXISTS idx_video_analysis_words_per_minute 
ON video_analysis (words_per_minute) 
WHERE words_per_minute IS NOT NULL;

-- Comments explaining the fields
COMMENT ON COLUMN video_analysis.transcription_data IS 'Complete OpenAI Whisper response including words array and segments with timing';
COMMENT ON COLUMN video_analysis.transcription_language IS 'ISO language code detected by Whisper (e.g., en, es, fr)';
COMMENT ON COLUMN video_analysis.transcription_duration_sec IS 'Audio duration in seconds as reported by Whisper';
COMMENT ON COLUMN video_analysis.transcription_word_count IS 'Total number of words transcribed';
COMMENT ON COLUMN video_analysis.transcription_segment_count IS 'Number of segments/sentences in transcription';
COMMENT ON COLUMN video_analysis.words_per_minute IS 'Speaking pace - words per minute';
COMMENT ON COLUMN video_analysis.significant_pauses IS 'Array of pauses longer than 1 second with timing info';
COMMENT ON COLUMN video_analysis.avg_confidence IS 'Average confidence score (avg_logprob) across all segments';
COMMENT ON COLUMN video_analysis.silence_ratio IS 'Ratio of silence/no-speech detected (0.0-1.0)';
COMMENT ON COLUMN video_analysis.transcribed_at IS 'Timestamp when transcription was performed';
