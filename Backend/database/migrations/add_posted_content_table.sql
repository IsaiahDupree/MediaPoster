-- Migration: Add posted_content table for tracking published social media content
-- Created: 2025-12-14

CREATE TABLE IF NOT EXISTS posted_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Platform info
    platform TEXT NOT NULL,
    platform_post_id TEXT,
    platform_url TEXT,
    
    -- Account info
    account_id TEXT,
    account_username TEXT,
    
    -- Local content reference
    media_id UUID,
    
    -- Content details
    caption TEXT,
    hashtags TEXT[],
    
    -- Analytics
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0.0,
    
    -- Status
    status TEXT DEFAULT 'published',
    error_message TEXT,
    
    -- Timestamps
    posted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analytics_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_posted_content_platform ON posted_content(platform);
CREATE INDEX IF NOT EXISTS idx_posted_content_media_id ON posted_content(media_id);
CREATE INDEX IF NOT EXISTS idx_posted_content_platform_post_id ON posted_content(platform_post_id);
CREATE INDEX IF NOT EXISTS idx_posted_content_posted_at ON posted_content(posted_at);

-- Comment
COMMENT ON TABLE posted_content IS 'Tracks content published to social media platforms with analytics';
