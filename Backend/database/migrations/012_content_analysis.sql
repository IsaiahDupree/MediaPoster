-- Migration: 012_content_analysis
-- Created: 2026-01-21
-- Purpose: Add content_analysis table for sentiment analysis (CUR-002)

CREATE TABLE IF NOT EXISTS content_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    media_id UUID NOT NULL,

    -- Sentiment analysis
    sentiment_score FLOAT,  -- -1.0 to +1.0
    sentiment_label TEXT,   -- negative, neutral, positive
    confidence FLOAT,       -- 0.0 to 1.0

    -- Emotions and themes
    emotions JSONB,         -- {"joy": 0.8, "anger": 0.1, ...}
    themes TEXT[],          -- Detected themes/topics
    reasoning TEXT,         -- AI explanation

    -- Processing metadata
    model_version TEXT,
    processing_time_ms INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_content_analysis_workspace ON content_analysis(workspace_id);
CREATE INDEX IF NOT EXISTS idx_content_analysis_media ON content_analysis(media_id);
CREATE INDEX IF NOT EXISTS idx_content_analysis_sentiment ON content_analysis(sentiment_label);

-- Comments
COMMENT ON TABLE content_analysis IS 'CUR-002: Sentiment analysis results for content';
COMMENT ON COLUMN content_analysis.sentiment_score IS 'Sentiment score from -1.0 (negative) to +1.0 (positive)';
COMMENT ON COLUMN content_analysis.emotions IS 'JSON object with emotion scores (joy, anger, sadness, fear, surprise, disgust)';
COMMENT ON COLUMN content_analysis.themes IS 'Array of detected themes/topics in content';
