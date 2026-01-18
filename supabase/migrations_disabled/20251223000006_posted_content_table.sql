-- Posted Content Tracking Table
-- Tracks content that has been published to social media platforms

CREATE TABLE IF NOT EXISTS posted_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    platform_post_id TEXT,
    platform_url TEXT,
    account_id TEXT,
    account_username TEXT,
    media_id UUID,
    caption TEXT,
    hashtags TEXT[],
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0.0,
    status TEXT DEFAULT 'published',
    error_message TEXT,
    posted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analytics_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_posted_content_platform ON posted_content(platform);
CREATE INDEX IF NOT EXISTS idx_posted_content_media_id ON posted_content(media_id);
CREATE INDEX IF NOT EXISTS idx_posted_content_platform_post_id ON posted_content(platform_post_id);
CREATE INDEX IF NOT EXISTS idx_posted_content_posted_at ON posted_content(posted_at);

COMMENT ON TABLE posted_content IS 'Tracks content published to social media with analytics';
