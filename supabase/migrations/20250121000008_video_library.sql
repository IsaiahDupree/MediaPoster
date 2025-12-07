-- Phase 2: Video Library & Content Analysis
-- Stores references to video files (local, drive, s3) and their analysis data

CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL, -- Removed FK constraint for now (no auth system yet)
    source_type TEXT NOT NULL CHECK (source_type IN ('local', 'gdrive', 'supabase', 's3', 'other')),
    source_uri TEXT NOT NULL, -- path, file ID, or URL
    file_name TEXT,
    duration_sec INTEGER,
    resolution TEXT, -- '1920x1080' etc
    aspect_ratio TEXT, -- '9:16', '16:9'
    content_item_id UUID REFERENCES content_items(id) ON DELETE SET NULL, -- Link to content system for cross-platform posting
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS video_analysis (
    video_id UUID PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,
    transcript TEXT,
    topics TEXT[], -- ['AI news', 'cat meme']
    hooks TEXT[], -- standout hook lines
    tone TEXT, -- 'educational', 'comedic'
    pacing TEXT, -- 'fast', 'medium', 'slow'
    key_moments JSONB, -- [{start, end, summary, suggested_caption}, ...]
    pre_social_score NUMERIC, -- 0-100
    analysis_version TEXT, -- model / prompt version
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_videos_user ON videos(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_source ON videos(source_type);
CREATE INDEX IF NOT EXISTS idx_videos_content_item ON videos(content_item_id);
CREATE INDEX IF NOT EXISTS idx_video_analysis_score ON video_analysis(pre_social_score);

-- Note: RLS disabled for now since we don't have auth yet
-- ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE video_analysis ENABLE ROW LEVEL SECURITY;

-- Comments for documentation
COMMENT ON TABLE videos IS 'Video file references (local paths, Drive IDs, S3 URLs) - media stored externally, only metadata here';
COMMENT ON TABLE video_analysis IS 'AI analysis results for videos: transcripts, hooks, key moments, social score';
COMMENT ON COLUMN videos.content_item_id IS 'Links to content_items for cross-platform posting and unified stats tracking';
