-- Migration 002: Content Repurposing Engine Tables
-- Creates tables for video repurposing: sources, transcripts, clips, renders
-- PRD: docs/PRD_CONTENT_REPURPOSING_ENGINE.md
-- Features: REPURPOSE-001, REPURPOSE-002

-- Source videos table
CREATE TABLE IF NOT EXISTS repurpose_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(20) NOT NULL, -- 'upload', 'youtube', 'podcast_rss', 'twitch_vod'
    source_url TEXT,
    file_path TEXT,
    duration_seconds INTEGER,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    clips_generated INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_repurpose_sources_user_id ON repurpose_sources(user_id);
CREATE INDEX idx_repurpose_sources_status ON repurpose_sources(status);
CREATE INDEX idx_repurpose_sources_created_at ON repurpose_sources(created_at DESC);

-- Transcripts table
CREATE TABLE IF NOT EXISTS repurpose_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES repurpose_sources(id) ON DELETE CASCADE,
    full_text TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    words JSONB NOT NULL, -- Array of {word, start, end, confidence}
    speakers JSONB, -- Array of {speaker_id, start, end}
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_repurpose_transcripts_source_id ON repurpose_transcripts(source_id);

-- Generated clips table
CREATE TABLE IF NOT EXISTS repurpose_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES repurpose_sources(id) ON DELETE CASCADE,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    title VARCHAR(255),
    transcript_segment TEXT,
    virality_score INTEGER, -- 0-100
    hook_score INTEGER, -- 0-100
    emotion_score INTEGER, -- 0-100
    status VARCHAR(20) DEFAULT 'detected', -- 'detected', 'approved', 'rejected', 'rendered'
    is_approved BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_repurpose_clips_source_id ON repurpose_clips(source_id);
CREATE INDEX idx_repurpose_clips_status ON repurpose_clips(status);
CREATE INDEX idx_repurpose_clips_virality_score ON repurpose_clips(virality_score DESC);

-- Rendered clips table
CREATE TABLE IF NOT EXISTS repurpose_renders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id UUID REFERENCES repurpose_clips(id) ON DELETE CASCADE,
    aspect_ratio VARCHAR(10) NOT NULL, -- '9:16', '1:1', '16:9', '4:5'
    target_platform VARCHAR(20), -- 'tiktok', 'reels', 'shorts', 'twitter', 'instagram'
    file_path TEXT,
    caption_style VARCHAR(50), -- 'karaoke', 'subtitle', 'emphasis', 'minimal'
    render_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    render_config JSONB DEFAULT '{}',
    file_size_bytes BIGINT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_repurpose_renders_clip_id ON repurpose_renders(clip_id);
CREATE INDEX idx_repurpose_renders_status ON repurpose_renders(render_status);

-- Add updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_repurpose_sources_updated_at BEFORE UPDATE ON repurpose_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repurpose_clips_updated_at BEFORE UPDATE ON repurpose_clips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repurpose_renders_updated_at BEFORE UPDATE ON repurpose_renders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE repurpose_sources IS 'Source videos for content repurposing pipeline';
COMMENT ON TABLE repurpose_transcripts IS 'Whisper transcriptions with word-level timing';
COMMENT ON TABLE repurpose_clips IS 'AI-detected highlight clips with virality scoring';
COMMENT ON TABLE repurpose_renders IS 'Rendered clips in various formats and aspect ratios';
