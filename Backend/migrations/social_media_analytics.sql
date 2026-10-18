-- Social Media Analytics Tables
-- Store analytics data for all social media platforms

-- Social Media Accounts (tracking which accounts we monitor)
CREATE TABLE IF NOT EXISTS social_media_accounts (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL, -- 'tiktok', 'instagram', 'youtube', etc.
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    bio TEXT,
    profile_pic_url TEXT,
    external_id VARCHAR(255), -- Platform-specific user ID
    is_verified BOOLEAN DEFAULT FALSE,
    is_business BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE, -- Should we keep tracking this account?
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_fetched_at TIMESTAMP,
    UNIQUE(platform, username)
);

-- Daily Analytics Snapshots (historical tracking)
CREATE TABLE IF NOT EXISTS social_media_analytics_snapshots (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    total_shares INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    avg_likes_per_post DECIMAL(10,2) DEFAULT 0,
    avg_comments_per_post DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, snapshot_date)
);

-- Social Media Posts (individual posts/videos)
CREATE TABLE IF NOT EXISTS social_media_posts (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    external_post_id VARCHAR(255) NOT NULL, -- Platform-specific post ID
    post_url TEXT NOT NULL,
    caption TEXT,
    media_type VARCHAR(50), -- 'video', 'image', 'carousel'
    thumbnail_url TEXT,
    media_url TEXT,
    duration INTEGER, -- Duration in seconds (for videos)
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, external_post_id)
);

-- Post Analytics History (track how posts perform over time)
CREATE TABLE IF NOT EXISTS social_media_post_analytics (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES social_media_posts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    views_count BIGINT DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    saves_count INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(post_id, snapshot_date)
);

-- Hashtag Tracking (track which hashtags are used and perform well)
CREATE TABLE IF NOT EXISTS social_media_hashtags (
    id SERIAL PRIMARY KEY,
    hashtag VARCHAR(255) NOT NULL UNIQUE,
    total_uses INTEGER DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Post-Hashtag Relationship
CREATE TABLE IF NOT EXISTS social_media_post_hashtags (
    post_id INTEGER NOT NULL REFERENCES social_media_posts(id) ON DELETE CASCADE,
    hashtag_id INTEGER NOT NULL REFERENCES social_media_hashtags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, hashtag_id)
);

-- Content Matching (link social posts to our generated content)
CREATE TABLE IF NOT EXISTS social_media_content_mapping (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES social_media_posts(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE SET NULL,
    clip_id UUID REFERENCES clips(id) ON DELETE SET NULL,
    confidence_score DECIMAL(3,2) DEFAULT 0, -- How confident we are in this match (0-1)
    matched_by VARCHAR(50), -- 'manual', 'url', 'content_hash', 'ai'
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(post_id)
);

-- API Usage Tracking (monitor API rate limits)
CREATE TABLE IF NOT EXISTS api_usage_tracking (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 1,
    success BOOLEAN DEFAULT TRUE,
    latency_ms INTEGER,
    error_message TEXT,
    requested_at TIMESTAMP DEFAULT NOW(),
    date DATE DEFAULT CURRENT_DATE
);

-- Scheduled Jobs Tracking
CREATE TABLE IF NOT EXISTS analytics_fetch_jobs (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- 'daily_snapshot', 'full_refresh', 'post_update'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    posts_fetched INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_social_accounts_platform ON social_media_accounts(platform);
CREATE INDEX IF NOT EXISTS idx_social_accounts_username ON social_media_accounts(username);
CREATE INDEX IF NOT EXISTS idx_social_accounts_active ON social_media_accounts(is_active);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_account ON social_media_analytics_snapshots(account_id);
CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_date ON social_media_analytics_snapshots(snapshot_date);

CREATE INDEX IF NOT EXISTS idx_posts_account ON social_media_posts(account_id);
CREATE INDEX IF NOT EXISTS idx_posts_platform_external ON social_media_posts(platform, external_post_id);
CREATE INDEX IF NOT EXISTS idx_posts_url ON social_media_posts(post_url);
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON social_media_posts(posted_at);

CREATE INDEX IF NOT EXISTS idx_post_analytics_post ON social_media_post_analytics(post_id);
CREATE INDEX IF NOT EXISTS idx_post_analytics_date ON social_media_post_analytics(snapshot_date);

CREATE INDEX IF NOT EXISTS idx_api_usage_date ON api_usage_tracking(date);
CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON api_usage_tracking(provider_name);

CREATE INDEX IF NOT EXISTS idx_fetch_jobs_account ON analytics_fetch_jobs(account_id);
CREATE INDEX IF NOT EXISTS idx_fetch_jobs_status ON analytics_fetch_jobs(status);

-- Create view for latest analytics
CREATE OR REPLACE VIEW latest_account_analytics AS
SELECT 
    a.*,
    s.followers_count,
    s.following_count,
    s.posts_count,
    s.total_likes,
    s.total_comments,
    s.total_views,
    s.total_shares,
    s.engagement_rate,
    s.snapshot_date as last_snapshot_date
FROM social_media_accounts a
LEFT JOIN LATERAL (
    SELECT * FROM social_media_analytics_snapshots
    WHERE account_id = a.id
    ORDER BY snapshot_date DESC
    LIMIT 1
) s ON true
WHERE a.is_active = true;

-- Create view for post performance trends
CREATE OR REPLACE VIEW post_performance_trends AS
SELECT 
    p.id,
    p.post_url,
    p.caption,
    p.posted_at,
    pa_first.likes_count as initial_likes,
    pa_latest.likes_count as current_likes,
    pa_latest.views_count as current_views,
    pa_latest.snapshot_date as last_updated,
    (pa_latest.likes_count - pa_first.likes_count) as likes_growth
FROM social_media_posts p
LEFT JOIN LATERAL (
    SELECT * FROM social_media_post_analytics
    WHERE post_id = p.id
    ORDER BY snapshot_date ASC
    LIMIT 1
) pa_first ON true
LEFT JOIN LATERAL (
    SELECT * FROM social_media_post_analytics
    WHERE post_id = p.id
    ORDER BY snapshot_date DESC
    LIMIT 1
) pa_latest ON true;

COMMENT ON TABLE social_media_accounts IS 'Tracks all social media accounts we monitor for analytics';
COMMENT ON TABLE social_media_analytics_snapshots IS 'Daily snapshots of account-level metrics for historical tracking';
COMMENT ON TABLE social_media_posts IS 'Individual posts/videos from social media platforms';
COMMENT ON TABLE social_media_post_analytics IS 'Historical performance data for individual posts';
COMMENT ON TABLE social_media_content_mapping IS 'Links social media posts to our internal content (videos/clips)';
COMMENT ON TABLE api_usage_tracking IS 'Monitors API usage for rate limiting and cost tracking';
