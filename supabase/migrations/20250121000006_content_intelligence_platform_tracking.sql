-- Content Intelligence System - Part 2: Platform Performance & Checkback Tracking
-- This migration creates tables for tracking posts across 9 social media platforms
-- with detailed checkback metrics, comment sentiment, and engagement analysis

-- Platform-specific post tracking (extends content_variants)
CREATE TABLE IF NOT EXISTS platform_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_variant_id UUID REFERENCES content_variants(id) ON DELETE CASCADE,
    clip_id UUID REFERENCES clips(id) ON DELETE SET NULL,
    platform TEXT NOT NULL, -- 'tiktok' | 'instagram' | 'youtube' | 'linkedin' | 'twitter' | 'facebook' | 'pinterest' | 'snapchat' | 'threads'
    platform_post_id TEXT NOT NULL,
    platform_url TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'scheduled', -- 'scheduled' | 'publishing' | 'published' | 'failed' | 'deleted'
    
    -- Metadata
    title TEXT,
    caption TEXT,
    hashtags TEXT[],
    thumbnail_url TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform, platform_post_id)
);

-- Checkback metrics at specific intervals (1h, 6h, 24h, 72h, 7d)
CREATE TABLE IF NOT EXISTS platform_checkbacks (
    id BIGSERIAL PRIMARY KEY,
    platform_post_id UUID REFERENCES platform_posts(id) ON DELETE CASCADE,
    checkback_h INTEGER NOT NULL, -- 1, 6, 24, 72, 168 (hours after publishing)
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Core metrics
    views INTEGER DEFAULT 0,
    unique_viewers INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    
    -- Retention metrics
    avg_watch_time_s DECIMAL,
    avg_watch_pct DECIMAL, -- 0-1
    retention_curve JSONB, -- [{"t_pct": 0.1, "retention": 0.96}, ...]
    
    -- Engagement metrics
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    profile_taps INTEGER DEFAULT 0,
    link_clicks INTEGER DEFAULT 0,
    
    -- Derived rates (calculated)
    like_rate DECIMAL, -- likes / views
    comment_rate DECIMAL, -- comments / views
    share_rate DECIMAL, -- shares / views
    save_rate DECIMAL, -- saves / views
    cta_response_count INTEGER DEFAULT 0, -- Comments matching CTA keywords
    
    -- Engaged reach
    engaged_users INTEGER DEFAULT 0, -- Unique users who engaged (comment/save/share/tap/click)
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform_post_id, checkback_h)
);

-- Comment-level sentiment and theme analysis
CREATE TABLE IF NOT EXISTS post_comments (
    id BIGSERIAL PRIMARY KEY,
    platform_post_id UUID REFERENCES platform_posts(id) ON DELETE CASCADE,
    platform_comment_id TEXT NOT NULL,
    author_handle TEXT,
    author_name TEXT,
    text TEXT NOT NULL,
    created_at_platform TIMESTAMP WITH TIME ZONE,
    
    -- Sentiment analysis
    sentiment_score DECIMAL, -- -1 (negative) to +1 (positive)
    emotion_tags TEXT[], -- ['excited', 'skeptical', 'confused', 'grateful', 'angry']
    intent TEXT, -- 'question' | 'praise' | 'critique' | 'spam' | 'engagement'
    theme_tags TEXT[], -- ['automation_overwhelm', 'want_templates', 'skeptical_of_bots']
    
    -- CTA response tracking
    is_cta_response BOOLEAN DEFAULT FALSE,
    cta_keyword TEXT, -- The keyword they typed (e.g., "Tech", "PROMPT")
    
    -- Moderation
    is_spam BOOLEAN DEFAULT FALSE,
    is_hidden BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform_post_id, platform_comment_id)
);

-- Retention drop events (for detailed analysis)
CREATE TABLE IF NOT EXISTS retention_events (
    id BIGSERIAL PRIMARY KEY,
    platform_post_id UUID REFERENCES platform_posts(id) ON DELETE CASCADE,
    video_id UUID REFERENCES analyzed_videos(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL, -- 'drop' | 'spike' | 'plateau'
    time_s DECIMAL NOT NULL, -- When in the video this happened
    retention_before DECIMAL, -- 0-1
    retention_after DECIMAL, -- 0-1
    delta DECIMAL, -- Change in retention
    
    -- Context at that moment
    segment_id BIGINT REFERENCES video_segments(id) ON DELETE SET NULL,
    local_words TEXT[], -- Words spoken around this time
    frame_snapshot JSONB, -- Frame analysis at this time
    
    -- Analysis
    likely_cause TEXT, -- 'jargon_heavy' | 'no_face' | 'visual_clutter' | 'topic_shift'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- A/B Test tracking for content experiments
CREATE TABLE IF NOT EXISTS content_ab_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_name TEXT NOT NULL,
    hypothesis TEXT, -- What you're testing
    variable_tested TEXT, -- 'hook_type' | 'caption_style' | 'thumbnail' | 'posting_time'
    start_date DATE NOT NULL,
    end_date DATE,
    status TEXT DEFAULT 'active', --'active' | 'completed' | 'paused'
    
    -- Variant posts (array of platform_post IDs)
    variant_a_posts UUID[] DEFAULT '{}',
    variant_b_posts UUID[] DEFAULT '{}',
    
    -- Results (filled when completed)
    winner TEXT, -- 'a' | 'b' | 'tie'
    improvement_pct DECIMAL,
    confidence_score DECIMAL, -- Statistical confidence
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_platform_posts_variant ON platform_posts(content_variant_id);
CREATE INDEX IF NOT EXISTS idx_platform_posts_clip ON platform_posts(clip_id);
CREATE INDEX IF NOT EXISTS idx_platform_posts_platform ON platform_posts(platform);
CREATE INDEX IF NOT EXISTS idx_platform_posts_status ON platform_posts(status);
CREATE INDEX IF NOT EXISTS idx_platform_posts_published ON platform_posts(published_at);
CREATE INDEX IF NOT EXISTS idx_platform_posts_scheduled ON platform_posts(scheduled_for) WHERE status = 'scheduled';

CREATE INDEX IF NOT EXISTS idx_checkbacks_post ON platform_checkbacks(platform_post_id);
CREATE INDEX IF NOT EXISTS idx_checkbacks_time ON platform_checkbacks(checkback_h);
CREATE INDEX IF NOT EXISTS idx_checkbacks_checked ON platform_checkbacks(checked_at);

CREATE INDEX IF NOT EXISTS idx_comments_post ON post_comments(platform_post_id);
CREATE INDEX IF NOT EXISTS idx_comments_sentiment ON post_comments(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_comments_cta ON post_comments(is_cta_response) WHERE is_cta_response = TRUE;
CREATE INDEX IF NOT EXISTS idx_comments_platform_created ON post_comments(created_at_platform);

CREATE INDEX IF NOT EXISTS idx_retention_events_post ON retention_events(platform_post_id);
CREATE INDEX IF NOT EXISTS idx_retention_events_video ON retention_events(video_id);
CREATE INDEX IF NOT EXISTS idx_retention_events_type ON retention_events(event_type);

CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON content_ab_tests(status);
CREATE INDEX IF NOT EXISTS idx_ab_tests_dates ON content_ab_tests(start_date, end_date);

-- Enable RLS
ALTER TABLE platform_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_checkbacks ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE retention_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_ab_tests ENABLE ROW LEVEL SECURITY;

-- Comments for documentation
COMMENT ON TABLE platform_posts IS 'Platform-specific post tracking across 9 social media platforms';
COMMENT ON TABLE platform_checkbacks IS 'Checkback metrics at 1h, 6h, 24h, 72h, 7d intervals';
COMMENT ON TABLE post_comments IS 'Comment-level sentiment and theme analysis with CTA tracking';
COMMENT ON TABLE retention_events IS 'Retention drops/spikes with contextual word and frame data';
COMMENT ON TABLE content_ab_tests IS 'A/B test tracking for content experiments';
