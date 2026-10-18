-- ============================================================================
-- SOCIAL MEDIA ANALYTICS EXTENSION
-- Extends existing social_accounts table with comprehensive analytics tracking
-- For all 9 platforms: TikTok, Instagram, YouTube, Twitter, Facebook,
-- Pinterest, Bluesky, Threads, LinkedIn
-- ============================================================================

-- ============================================================================
-- ANALYTICS MONITORING CONFIG
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_analytics_config (
    id SERIAL PRIMARY KEY,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    
    -- Monitoring Settings
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    fetch_frequency INTERVAL DEFAULT '24 hours',
    last_fetched_at TIMESTAMP,
    next_fetch_at TIMESTAMP,
    
    -- What to Track
    track_posts BOOLEAN DEFAULT TRUE,
    track_comments BOOLEAN DEFAULT FALSE,
    track_demographics BOOLEAN DEFAULT FALSE,
    posts_per_fetch INTEGER DEFAULT 50,
    
    -- API Provider
    provider_name VARCHAR(100), -- 'rapidapi_tiktok', 'graph_api', etc.
    provider_config JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(social_account_id)
);

COMMENT ON TABLE social_analytics_config IS 'Configuration for analytics monitoring per social account';

-- ============================================================================
-- DAILY ANALYTICS SNAPSHOTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_analytics_snapshots (
    id SERIAL PRIMARY KEY,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    
    -- Core Metrics (Universal)
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    
    -- Engagement Totals
    total_likes BIGINT DEFAULT 0,
    total_comments BIGINT DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    total_shares BIGINT DEFAULT 0,
    total_saves BIGINT DEFAULT 0,
    total_impressions BIGINT DEFAULT 0,
    
    -- Platform-Specific Metrics  
    subscribers_count INTEGER DEFAULT 0, -- YouTube
    pins_count INTEGER DEFAULT 0, -- Pinterest
    boards_count INTEGER DEFAULT 0, -- Pinterest
    retweets_count BIGINT DEFAULT 0, -- Twitter/X
    reactions_count BIGINT DEFAULT 0, -- Facebook
    watch_time_minutes BIGINT DEFAULT 0, -- YouTube
    
    -- Calculated Metrics
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    avg_likes_per_post DECIMAL(10,2) DEFAULT 0,
    avg_comments_per_post DECIMAL(10,2) DEFAULT 0,
    avg_views_per_post DECIMAL(10,2) DEFAULT 0,
    
    -- Growth (vs previous day)
    follower_growth INTEGER DEFAULT 0,
    engagement_growth DECIMAL(10,2) DEFAULT 0,
    
    -- Reach
    reach INTEGER DEFAULT 0,
    profile_visits INTEGER DEFAULT 0,
    
    -- Metadata
    data_source VARCHAR(50),
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(social_account_id, snapshot_date)
);

CREATE INDEX idx_analytics_snapshots_account ON social_analytics_snapshots(social_account_id);
CREATE INDEX idx_analytics_snapshots_date ON social_analytics_snapshots(snapshot_date DESC);

COMMENT ON TABLE social_analytics_snapshots IS 'Daily snapshots of account-level metrics across all platforms';

-- ============================================================================
-- SOCIAL POSTS (Extended from platform_posts)
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_posts_analytics (
    id SERIAL PRIMARY KEY,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    
    -- Post Identifiers
    external_post_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    post_url TEXT NOT NULL,
    short_code VARCHAR(100),
    
    -- Content
    caption TEXT,
    title VARCHAR(500),
    description TEXT,
    
    -- Media
    media_type VARCHAR(50), -- 'video','image','carousel','story','reel','short'
    media_count INTEGER DEFAULT 1,
    thumbnail_url TEXT,
    media_url TEXT,
    media_urls JSONB,
    
    -- Video Details
    duration INTEGER,
    is_short_form BOOLEAN DEFAULT FALSE,
    has_audio BOOLEAN DEFAULT TRUE,
    
    -- Status
    is_pinned BOOLEAN DEFAULT FALSE,
    is_ad BOOLEAN DEFAULT FALSE,
    visibility VARCHAR(50) DEFAULT 'public',
    
    -- Location
    location_name VARCHAR(255),
    
    -- Timestamps
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Link to Internal Content
    video_id UUID, -- Link to videos table
    clip_id UUID, -- Link to clips table
    
    -- Full API Response
    raw_data JSONB,
    
    UNIQUE(platform, external_post_id)
);

CREATE INDEX idx_social_posts_account ON social_posts_analytics(social_account_id);
CREATE INDEX idx_social_posts_url ON social_posts_analytics(post_url);
CREATE INDEX idx_social_posts_posted_at ON social_posts_analytics(posted_at DESC);
CREATE INDEX idx_social_posts_video ON social_posts_analytics(video_id) WHERE video_id IS NOT NULL;
CREATE INDEX idx_social_posts_clip ON social_posts_analytics(clip_id) WHERE clip_id IS NOT NULL;

COMMENT ON TABLE social_posts_analytics IS 'Social media posts tracked for analytics (separate from publishing queue)';

-- ============================================================================
-- POST PERFORMANCE METRICS (Historical Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_post_metrics (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES social_posts_analytics(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    snapshot_hour INTEGER, -- For intraday tracking
    
    -- Core Engagement
    likes_count BIGINT DEFAULT 0,
    comments_count BIGINT DEFAULT 0,
    views_count BIGINT DEFAULT 0,
    shares_count BIGINT DEFAULT 0,
    saves_count BIGINT DEFAULT 0,
    
    -- Platform-Specific
    retweets_count BIGINT DEFAULT 0,
    quote_tweets_count BIGINT DEFAULT 0,
    reactions_count BIGINT DEFAULT 0,
    repins_count BIGINT DEFAULT 0,
    
    -- Reach & Impressions
    impressions BIGINT DEFAULT 0,
    reach BIGINT DEFAULT 0,
    unique_viewers BIGINT DEFAULT 0,
    
    -- Video Metrics
    watch_time_seconds BIGINT DEFAULT 0,
    avg_watch_percentage DECIMAL(5,2) DEFAULT 0,
    completion_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Audience Actions
    profile_visits BIGINT DEFAULT 0,
    follows_from_post BIGINT DEFAULT 0,
    link_clicks BIGINT DEFAULT 0,
    
    -- Calculated
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    viral_score DECIMAL(10,2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(post_id, snapshot_date, snapshot_hour)
);

CREATE INDEX idx_post_metrics_post ON social_post_metrics(post_id);
CREATE INDEX idx_post_metrics_date ON social_post_metrics(snapshot_date DESC);
CREATE INDEX idx_post_metrics_views ON social_post_metrics(views_count DESC);

COMMENT ON TABLE social_post_metrics IS 'Historical performance data for social posts with hourly granularity';

-- ============================================================================
-- HASHTAGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_hashtags (
    id SERIAL PRIMARY KEY,
    hashtag VARCHAR(255) NOT NULL UNIQUE,
    total_uses BIGINT DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    avg_engagement_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS social_post_hashtags (
    post_id INTEGER NOT NULL REFERENCES social_posts_analytics(id) ON DELETE CASCADE,
    hashtag_id INTEGER NOT NULL REFERENCES social_hashtags(id) ON DELETE CASCADE,
    position INTEGER,
    PRIMARY KEY (post_id, hashtag_id)
);

-- ============================================================================
-- COMMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES social_posts_analytics(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    external_comment_id VARCHAR(255) NOT NULL,
    
    comment_text TEXT,
    author_username VARCHAR(255),
    author_id VARCHAR(255),
    
    parent_comment_id INTEGER REFERENCES social_comments(id),
    is_reply BOOLEAN DEFAULT FALSE,
    
    likes_count INTEGER DEFAULT 0,
    is_creator_reply BOOLEAN DEFAULT FALSE,
    
    sentiment VARCHAR(20),
    sentiment_score DECIMAL(3,2),
    
    commented_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(platform, external_comment_id)
);

CREATE INDEX idx_social_comments_post ON social_comments(post_id);
CREATE INDEX idx_social_comments_creator ON social_comments(is_creator_reply) WHERE is_creator_reply = TRUE;

-- ============================================================================
-- AUDIENCE DEMOGRAPHICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_audience_demographics (
    id SERIAL PRIMARY KEY,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    
    -- Age Groups (percentages)
    age_13_17 DECIMAL(5,2) DEFAULT 0,
    age_18_24 DECIMAL(5,2) DEFAULT 0,
    age_25_34 DECIMAL(5,2) DEFAULT 0,
    age_35_44 DECIMAL(5,2) DEFAULT 0,
    age_45_plus DECIMAL(5,2) DEFAULT 0,
    
    -- Gender (percentages)
    gender_male DECIMAL(5,2) DEFAULT 0,
    gender_female DECIMAL(5,2) DEFAULT 0,
    gender_other DECIMAL(5,2) DEFAULT 0,
    
    -- Top Locations
    top_countries JSONB,
    top_cities JSONB,
    top_languages JSONB,
    
    -- Activity Patterns
    peak_hours JSONB,
    peak_days JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(social_account_id, snapshot_date)
);

-- ============================================================================
-- API USAGE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_api_usage (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    
    request_count INTEGER DEFAULT 1,
    success BOOLEAN DEFAULT TRUE,
    latency_ms INTEGER,
    error_message TEXT,
    
    date DATE DEFAULT CURRENT_DATE,
    requested_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_social_api_usage_date ON social_api_usage(date, provider_name);

-- ============================================================================
-- FETCH JOBS
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_fetch_jobs (
    id SERIAL PRIMARY KEY,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    posts_fetched INTEGER DEFAULT 0,
    comments_fetched INTEGER DEFAULT 0,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_social_fetch_jobs_account ON social_fetch_jobs(social_account_id);
CREATE INDEX idx_social_fetch_jobs_status ON social_fetch_jobs(status);

-- ============================================================================
-- VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW social_analytics_latest AS
SELECT 
    sa.id,
    sa.handle AS username,
    sa.platform,
    sa.display_name,
    sa.status AS account_status,
    sas.snapshot_date AS last_snapshot_date,
    sas.followers_count,
    sas.following_count,
    sas.posts_count,
    sas.total_views,
    sas.total_likes,
    sas.total_comments,
    sas.engagement_rate,
    sas.follower_growth,
    sac.monitoring_enabled,
    sac.last_fetched_at
FROM social_accounts sa
LEFT JOIN social_analytics_config sac ON sa.id = sac.social_account_id
LEFT JOIN LATERAL (
    SELECT * FROM social_analytics_snapshots
    WHERE social_account_id = sa.id
    ORDER BY snapshot_date DESC
    LIMIT 1
) sas ON TRUE;

CREATE OR REPLACE VIEW social_post_performance AS
SELECT 
    p.id,
    p.platform,
    p.post_url,
    p.caption,
    p.media_type,
    p.posted_at,
    m.views_count AS current_views,
    m.likes_count AS current_likes,
    m.comments_count AS current_comments,
    m.engagement_rate,
    m.snapshot_date AS last_updated,
    sa.handle AS account_username
FROM social_posts_analytics p
JOIN social_accounts sa ON p.social_account_id = sa.id
LEFT JOIN LATERAL (
    SELECT * FROM social_post_metrics
    WHERE post_id = p.id
    ORDER BY snapshot_date DESC, snapshot_hour DESC NULLS LAST
    LIMIT 1
) m ON TRUE
WHERE p.deleted_at IS NULL;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$ 
BEGIN
    RAISE NOTICE '✅ Social Media Analytics Extension Created!';
    RAISE NOTICE '📊 Tables: 12 analytics tables created';
    RAISE NOTICE '🔗 Integrated with existing social_accounts table';
    RAISE NOTICE '🎯 Ready for all 9 platforms';
END $$;
