-- Migration: Add curation and sentiment columns for AI-Assisted Curation System
-- Date: 2024-12-25

-- Add curation columns to videos table
ALTER TABLE videos ADD COLUMN IF NOT EXISTS curation_status TEXT DEFAULT 'pending';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS auto_curated BOOLEAN DEFAULT FALSE;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS auto_curation_reason TEXT;

-- Add sentiment columns to video_analysis table
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS sentiment_score NUMERIC(4,3);
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS sentiment_label TEXT;
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS transcript_hash TEXT;

-- Create deletion audit log table
CREATE TABLE IF NOT EXISTS deletion_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_by TEXT DEFAULT 'system',
    reason TEXT,
    duplicate_group_id UUID
);

-- Create index on transcript_hash for duplicate detection
CREATE INDEX IF NOT EXISTS idx_video_analysis_transcript_hash ON video_analysis(transcript_hash);

-- Create index on sentiment_score for filtering
CREATE INDEX IF NOT EXISTS idx_video_analysis_sentiment_score ON video_analysis(sentiment_score);

-- Create index on curation_status for filtering
CREATE INDEX IF NOT EXISTS idx_videos_curation_status ON videos(curation_status);

-- Comment on columns
COMMENT ON COLUMN videos.curation_status IS 'Curation status: pending, approved, rejected';
COMMENT ON COLUMN videos.auto_curated IS 'Whether this was auto-curated by AI';
COMMENT ON COLUMN videos.auto_curation_reason IS 'Reason for auto-curation decision';
COMMENT ON COLUMN video_analysis.sentiment_score IS 'Sentiment score from -1.0 (negative) to 1.0 (positive)';
COMMENT ON COLUMN video_analysis.sentiment_label IS 'Sentiment label: very_negative, negative, neutral, positive, very_positive';
COMMENT ON COLUMN video_analysis.transcript_hash IS 'MD5 hash of transcript for duplicate detection';
