-- MediaPoster Database Schema for Supabase
-- Modular macOS Social Video Automation System

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Original Videos Table
CREATE TABLE IF NOT EXISTS original_videos (
    video_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(255) NOT NULL, -- e.g., 'iPhone Camera Roll', 'iCloud Photos'
    file_path TEXT NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    duration_seconds FLOAT NOT NULL,
    
    date_recorded TIMESTAMP WITH TIME ZONE,
    date_uploaded TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    date_processed TIMESTAMP WITH TIME ZONE,
    
    transcript TEXT,
    topics TEXT[], -- Array of topics/keywords
    keywords TEXT[], -- Extracted keywords
    
    analysis_data JSONB, -- Frame descriptions, scene timestamps, etc.
    metadata JSONB, -- Additional metadata
    
    processing_status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on processing status
CREATE INDEX idx_original_videos_status ON original_videos(processing_status);
CREATE INDEX idx_original_videos_date_recorded ON original_videos(date_recorded DESC);

-- Clips Table
CREATE TABLE IF NOT EXISTS clips (
    clip_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_video_id UUID NOT NULL REFERENCES original_videos(video_id) ON DELETE CASCADE,
    
    segment_start_seconds FLOAT NOT NULL,
    segment_end_seconds FLOAT NOT NULL,
    clip_duration_seconds FLOAT NOT NULL,
    
    file_path TEXT,
    file_size_bytes BIGINT,
    
    hook_text TEXT, -- Catchy title/hook overlay
    caption_text TEXT, -- Main caption for posting
    generated_hashtags TEXT[],
    
    tags TEXT[], -- Content tags: ["tutorial", "AI tool", "hook:listicle", "CTA:yes"]
    content_category VARCHAR(100), -- educational, entertainment, personal_story
    hook_type VARCHAR(100), -- question, listicle, bold_statement, story, negative_hook, tutorial
    has_cta BOOLEAN DEFAULT false,
    visual_elements JSONB, -- {has_progress_bar, emoji_used, text_overlay, etc.}
    target_keyword VARCHAR(255),
    predicted_audience_reaction VARCHAR(100), -- humor, inspirational, shocking
    
    clip_status VARCHAR(50) DEFAULT 'generated', -- generated, staged, posted, deleted, failed
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_clips_parent_video ON clips(parent_video_id);
CREATE INDEX idx_clips_status ON clips(clip_status);
CREATE INDEX idx_clips_hook_type ON clips(hook_type);
CREATE INDEX idx_clips_target_keyword ON clips(target_keyword);

-- Platform Posts Table
CREATE TABLE IF NOT EXISTS platform_posts (
    post_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clip_id UUID NOT NULL REFERENCES clips(clip_id) ON DELETE CASCADE,
    
    platform VARCHAR(50) NOT NULL, -- instagram, tiktok, youtube, twitter, threads
    account_id VARCHAR(255),
    
    blotato_media_id VARCHAR(255),
    blotato_post_id VARCHAR(255),
    platform_post_id VARCHAR(255),
    platform_post_url TEXT,
    
    caption_used TEXT,
    posted_at TIMESTAMP WITH TIME ZONE,
    
    post_status VARCHAR(50) DEFAULT 'pending', -- pending, posted, failed, deleted
    failure_reason TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_platform_posts_clip ON platform_posts(clip_id);
CREATE INDEX idx_platform_posts_platform ON platform_posts(platform);
CREATE INDEX idx_platform_posts_status ON platform_posts(post_status);
CREATE INDEX idx_platform_posts_posted_at ON platform_posts(posted_at DESC);

-- Performance Metrics Table
CREATE TABLE IF NOT EXISTS performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES platform_posts(post_id) ON DELETE CASCADE,
    
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    
    engagement_rate FLOAT, -- Calculated engagement percentage
    watch_time_seconds FLOAT,
    completion_rate FLOAT,
    
    is_initial_check BOOLEAN DEFAULT false,
    minutes_after_post INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_performance_metrics_post ON performance_metrics(post_id);
CREATE INDEX idx_performance_metrics_measured_at ON performance_metrics(measured_at DESC);
CREATE INDEX idx_performance_metrics_initial_check ON performance_metrics(is_initial_check);

-- Highlights Table (Detected highlights before clip generation)
CREATE TABLE IF NOT EXISTS highlights (
    highlight_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES original_videos(video_id) ON DELETE CASCADE,
    
    start_time_seconds FLOAT NOT NULL,
    end_time_seconds FLOAT NOT NULL,
    duration_seconds FLOAT NOT NULL,
    
    highlight_score FLOAT NOT NULL, -- 0-1 score for highlight potential
    detection_signals JSONB, -- Scene changes, audio peaks, key phrases, visual salience
    
    reasoning TEXT, -- AI-generated reasoning for why this is a highlight
    suggested_hook TEXT,
    
    status VARCHAR(50) DEFAULT 'detected', -- detected, approved, rejected, generated_to_clip
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_highlights_video ON highlights(video_id);
CREATE INDEX idx_highlights_score ON highlights(highlight_score DESC);
CREATE INDEX idx_highlights_status ON highlights(status);

-- Processing Jobs Table (For async processing tracking)
CREATE TABLE IF NOT EXISTS processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(100) NOT NULL, -- video_ingestion, ai_analysis, highlight_detection, clip_generation, etc.
    
    entity_id UUID, -- Reference to video_id or clip_id
    entity_type VARCHAR(50), -- original_video, clip, highlight
    
    status VARCHAR(50) DEFAULT 'queued', -- queued, running, completed, failed, cancelled
    progress_percent INTEGER DEFAULT 0,
    
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    result JSONB,
    error_message TEXT,
    
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_type ON processing_jobs(job_type);
CREATE INDEX idx_processing_jobs_entity ON processing_jobs(entity_id);

-- Content Tags Table (For flexible tagging system)
CREATE TABLE IF NOT EXISTS content_tags (
    tag_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_name VARCHAR(100) UNIQUE NOT NULL,
    tag_category VARCHAR(50), -- hook_type, visual_element, content_category, platform_specific
    description TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Clip Tags Junction Table
CREATE TABLE IF NOT EXISTS clip_tags (
    clip_id UUID NOT NULL REFERENCES clips(clip_id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES content_tags(tag_id) ON DELETE CASCADE,
    
    PRIMARY KEY (clip_id, tag_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_clip_tags_clip ON clip_tags(clip_id);
CREATE INDEX idx_clip_tags_tag ON clip_tags(tag_id);

-- AI Service Logs Table (For tracking AI service usage and watermark removal)
CREATE TABLE IF NOT EXISTS ai_service_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    service_name VARCHAR(100) NOT NULL, -- openai_whisper, openai_gpt4_vision, watermark_removal, etc.
    operation VARCHAR(100) NOT NULL,
    
    entity_id UUID,
    entity_type VARCHAR(50),
    
    input_data JSONB,
    output_data JSONB,
    
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6),
    processing_time_ms INTEGER,
    
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_ai_service_logs_service ON ai_service_logs(service_name);
CREATE INDEX idx_ai_service_logs_created_at ON ai_service_logs(created_at DESC);

-- System Settings Table
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value JSONB NOT NULL,
    description TEXT,
    
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default settings
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('hook_templates', '{"question": ["Did you know {fact}?", "Can you believe {statement}?"], "listicle": ["{number} ways to {action}", "Top {number} {things}"], "negative_hook": ["Stop {bad_practice}!", "Never {mistake} again"]}', 'Templates for generating catchy hooks'),
('viral_keywords', '["AI", "productivity", "life hack", "tutorial", "secret", "ultimate guide"]', 'Keywords that tend to perform well'),
('platform_requirements', '{"instagram": {"max_duration": 90, "aspect_ratio": "9:16"}, "tiktok": {"max_duration": 60, "aspect_ratio": "9:16"}, "youtube": {"max_duration": 60, "aspect_ratio": "9:16"}}', 'Platform-specific requirements')
ON CONFLICT (setting_key) DO NOTHING;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to all tables
CREATE TRIGGER update_original_videos_updated_at BEFORE UPDATE ON original_videos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_clips_updated_at BEFORE UPDATE ON clips FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_platform_posts_updated_at BEFORE UPDATE ON platform_posts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_highlights_updated_at BEFORE UPDATE ON highlights FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_processing_jobs_updated_at BEFORE UPDATE ON processing_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON system_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries

-- View: Clip Performance Summary
CREATE OR REPLACE VIEW clip_performance_summary AS
SELECT 
    c.clip_id,
    c.parent_video_id,
    c.hook_type,
    c.content_category,
    c.target_keyword,
    pp.platform,
    pm.views,
    pm.likes,
    pm.comments,
    pm.engagement_rate,
    pp.posted_at,
    pm.measured_at,
    pm.minutes_after_post
FROM clips c
LEFT JOIN platform_posts pp ON c.clip_id = pp.clip_id
LEFT JOIN performance_metrics pm ON pp.post_id = pm.post_id
WHERE pp.post_status = 'posted'
ORDER BY pm.measured_at DESC;

-- View: Best Performing Clips by Hook Type
CREATE OR REPLACE VIEW best_clips_by_hook_type AS
SELECT 
    c.hook_type,
    pp.platform,
    COUNT(*) as clip_count,
    AVG(pm.views) as avg_views,
    AVG(pm.likes) as avg_likes,
    AVG(pm.engagement_rate) as avg_engagement_rate
FROM clips c
JOIN platform_posts pp ON c.clip_id = pp.clip_id
JOIN performance_metrics pm ON pp.post_id = pm.post_id
WHERE pp.post_status = 'posted'
AND pm.is_initial_check = false  -- Use later metrics, not initial
GROUP BY c.hook_type, pp.platform
ORDER BY avg_views DESC;

-- View: Processing Pipeline Status
CREATE OR REPLACE VIEW processing_pipeline_status AS
SELECT 
    ov.video_id,
    ov.file_name,
    ov.processing_status as video_status,
    ov.date_uploaded,
    COUNT(DISTINCT h.highlight_id) as highlights_detected,
    COUNT(DISTINCT c.clip_id) as clips_generated,
    COUNT(DISTINCT pp.post_id) as posts_created,
    COUNT(DISTINCT CASE WHEN pp.post_status = 'posted' THEN pp.post_id END) as posts_live
FROM original_videos ov
LEFT JOIN highlights h ON ov.video_id = h.video_id
LEFT JOIN clips c ON ov.video_id = c.parent_video_id
LEFT JOIN platform_posts pp ON c.clip_id = pp.clip_id
GROUP BY ov.video_id, ov.file_name, ov.processing_status, ov.date_uploaded
ORDER BY ov.date_uploaded DESC;

-- Comments
COMMENT ON TABLE original_videos IS 'Stores metadata and analysis results for original videos from iPhone';
COMMENT ON TABLE clips IS 'Short clips generated from highlights with viral optimizations';
COMMENT ON TABLE platform_posts IS 'Tracks posts made to social media platforms via Blotato';
COMMENT ON TABLE performance_metrics IS 'Time-series performance data for posted clips';
COMMENT ON TABLE highlights IS 'AI-detected highlight segments from original videos';
COMMENT ON TABLE processing_jobs IS 'Async job queue for video processing tasks';
COMMENT ON TABLE ai_service_logs IS 'Logs AI service usage for cost tracking and watermark removal';
