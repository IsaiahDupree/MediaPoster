-- ============================================================================
-- COMPREHENSIVE SOCIAL MEDIA ANALYTICS SCHEMA
-- For all 9 platforms: TikTok, Instagram, YouTube, Twitter, Facebook, 
-- Pinterest, Bluesky, Threads, LinkedIn
-- Version: 2.0
-- Date: 2025-11-22
-- ============================================================================

-- ============================================================================
-- PART 1: CORE ACCOUNT MANAGEMENT
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_accounts (
    id SERIAL PRIMARY KEY,
    
    -- Basic Info
    platform VARCHAR(50) NOT NULL CHECK (platform IN (
        'tiktok', 'instagram', 'youtube', 'twitter', 'facebook', 
        'pinterest', 'bluesky', 'threads', 'linkedin'
    )),
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    bio TEXT,
    profile_pic_url TEXT,
    external_id VARCHAR(255),
    
    -- Account Type
    is_verified BOOLEAN DEFAULT FALSE,
    is_business BOOLEAN DEFAULT FALSE,
    is_creator BOOLEAN DEFAULT FALSE,
    account_type VARCHAR(50),
    
    -- Contact
    email VARCHAR(255),
    website_url TEXT,
    location VARCHAR(255),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_private BOOLEAN DEFAULT FALSE,
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    blotato_account_id INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_fetched_at TIMESTAMP,
    account_created_at TIMESTAMP,
    
    UNIQUE(platform, username)
);

CREATE INDEX idx_accounts_platform ON social_media_accounts(platform);
CREATE INDEX idx_accounts_active ON social_media_accounts(is_active);

-- ============================================================================
-- PART 2: ANALYTICS SNAPSHOTS (Daily Metrics)
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_analytics_snapshots (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    
    -- Core Metrics
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    total_likes BIGINT DEFAULT 0,
    total_comments BIGINT DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    total_shares BIGINT DEFAULT 0,
    total_saves BIGINT DEFAULT 0,
    total_impressions BIGINT DEFAULT 0,
    
    -- Platform-Specific
    subscribers_count INTEGER DEFAULT 0, -- YouTube
    pins_count INTEGER DEFAULT 0, -- Pinterest
    boards_count INTEGER DEFAULT 0, -- Pinterest
    retweets_count BIGINT DEFAULT 0, -- Twitter
    reactions_count BIGINT DEFAULT 0, -- Facebook
    watch_time_minutes BIGINT DEFAULT 0, -- YouTube
    
    -- Calculated Metrics
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    avg_likes_per_post DECIMAL(10,2) DEFAULT 0,
    avg_comments_per_post DECIMAL(10,2) DEFAULT 0,
    avg_views_per_post DECIMAL(10,2) DEFAULT 0,
    follower_growth INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    profile_visits INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, snapshot_date)
);

CREATE INDEX idx_snapshots_account_date ON social_media_analytics_snapshots(account_id, snapshot_date DESC);

-- ============================================================================
-- PART 3: POSTS/CONTENT (All Media Types)
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_posts (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    
    -- Identifiers
    external_post_id VARCHAR(255) NOT NULL,
    post_url TEXT NOT NULL,
    short_code VARCHAR(100),
    
    -- Content
    caption TEXT,
    description TEXT,
    title VARCHAR(500),
    
    -- Media
    media_type VARCHAR(50), -- 'video','image','carousel','story','reel','short','pin'
    media_count INTEGER DEFAULT 1,
    thumbnail_url TEXT,
    media_url TEXT,
    media_urls JSONB,
    
    -- Video Metadata
    duration INTEGER,
    video_quality VARCHAR(20),
    has_audio BOOLEAN DEFAULT TRUE,
    is_short_form BOOLEAN DEFAULT FALSE,
    
    -- Status Flags
    is_pinned BOOLEAN DEFAULT FALSE,
    is_ad BOOLEAN DEFAULT FALSE,
    is_sponsored BOOLEAN DEFAULT FALSE,
    visibility VARCHAR(50) DEFAULT 'public',
    
    -- Platform-Specific
    youtube_category VARCHAR(100),
    pinterest_board_id VARCHAR(100),
    twitter_thread_id VARCHAR(100),
    instagram_product_tags JSONB,
    
    -- Location
    location_name VARCHAR(255),
    location_lat DECIMAL(10, 6),
    location_lng DECIMAL(10, 6),
    
    -- Timestamps
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    raw_data JSONB,
    UNIQUE(platform, external_post_id)
);

CREATE INDEX idx_posts_account ON social_media_posts(account_id);
CREATE INDEX idx_posts_posted_at ON social_media_posts(posted_at DESC);
CREATE INDEX idx_posts_url ON social_media_posts(post_url);

-- ============================================================================
-- PART 4: POST ANALYTICS (Historical Performance)
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_post_analytics (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES social_media_posts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    snapshot_hour INTEGER,
    
    -- Core Engagement
    likes_count BIGINT DEFAULT 0,
    comments_count BIGINT DEFAULT 0,
    views_count BIGINT DEFAULT 0,
    shares_count BIGINT DEFAULT 0,
    saves_count BIGINT DEFAULT 0,
    
    -- Platform-Specific
    retweets_count BIGINT DEFAULT 0,
    reactions_count BIGINT DEFAULT 0,
    repins_count BIGINT DEFAULT 0,
    
    -- Reach
    impressions BIGINT DEFAULT 0,
    reach BIGINT DEFAULT 0,
    
    -- Video Metrics
    watch_time_seconds BIGINT DEFAULT 0,
    avg_watch_percentage DECIMAL(5,2) DEFAULT 0,
    completion_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Calculated
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    viral_score DECIMAL(10,2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(post_id, snapshot_date, snapshot_hour)
);

CREATE INDEX idx_post_analytics_post_date ON social_media_post_analytics(post_id, snapshot_date DESC);

-- ============================================================================
-- PART 5: HASHTAGS & MENTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_hashtags (
    id SERIAL PRIMARY KEY,
    hashtag VARCHAR(255) NOT NULL UNIQUE,
    platform VARCHAR(50),
    total_uses BIGINT DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    avg_engagement_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS social_media_post_hashtags (
    post_id INTEGER NOT NULL REFERENCES social_media_posts(id) ON DELETE CASCADE,
    hashtag_id INTEGER NOT NULL REFERENCES social_media_hashtags(id) ON DELETE CASCADE,
    position INTEGER,
    PRIMARY KEY (post_id, hashtag_id)
);

CREATE TABLE IF NOT EXISTS social_media_mentions (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES social_media_posts(id) ON DELETE CASCADE,
    mentioned_username VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    mention_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- PART 6: COMMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES social_media_posts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    external_comment_id VARCHAR(255) NOT NULL,
    comment_text TEXT,
    author_username VARCHAR(255),
    author_id VARCHAR(255),
    parent_comment_id INTEGER REFERENCES social_media_comments(id),
    is_reply BOOLEAN DEFAULT FALSE,
    likes_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    is_creator_reply BOOLEAN DEFAULT FALSE,
    sentiment VARCHAR(20),
    sentiment_score DECIMAL(3,2),
    commented_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, external_comment_id)
);

CREATE INDEX idx_comments_post ON social_media_comments(post_id);

-- ============================================================================
-- PART 7: AUDIENCE DEMOGRAPHICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_audience_demographics (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    
    -- Age Groups
    age_13_17 DECIMAL(5,2) DEFAULT 0,
    age_18_24 DECIMAL(5,2) DEFAULT 0,
    age_25_34 DECIMAL(5,2) DEFAULT 0,
    age_35_44 DECIMAL(5,2) DEFAULT 0,
    age_45_plus DECIMAL(5,2) DEFAULT 0,
    
    -- Gender
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
    UNIQUE(account_id, snapshot_date)
);

-- ============================================================================
-- PART 8: CONTENT MAPPING
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_content_mapping (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES social_media_posts(id) ON DELETE CASCADE,
    video_id INTEGER,
    clip_id INTEGER,
    confidence_score DECIMAL(3,2) DEFAULT 0,
    matched_by VARCHAR(50),
    verified BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(post_id)
);

CREATE INDEX idx_mapping_video ON social_media_content_mapping(video_id);
CREATE INDEX idx_mapping_clip ON social_media_content_mapping(clip_id);

-- ============================================================================
-- PART 9: API USAGE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_usage_tracking (
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

CREATE INDEX idx_api_usage_date_provider ON api_usage_tracking(date, provider_name);

-- ============================================================================
-- PART 10: FETCH JOBS
-- ============================================================================

CREATE TABLE IF NOT EXISTS analytics_fetch_jobs (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    posts_fetched INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_jobs_account_status ON analytics_fetch_jobs(account_id, status);

-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

CREATE OR REPLACE VIEW latest_account_analytics AS
SELECT 
    a.*,
    s.snapshot_date,
    s.followers_count,
    s.following_count,
    s.posts_count,
    s.total_likes,
    s.total_comments,
    s.total_views,
    s.engagement_rate,
    s.follower_growth
FROM social_media_accounts a
LEFT JOIN LATERAL (
    SELECT * FROM social_media_analytics_snapshots
    WHERE account_id = a.id
    ORDER BY snapshot_date DESC
    LIMIT 1
) s ON true
WHERE a.is_active = TRUE;

CREATE OR REPLACE VIEW post_performance_trends AS
SELECT 
    p.id,
    p.platform,
    p.post_url,
    p.caption,
    p.posted_at,
    pa_latest.views_count AS current_views,
    pa_latest.likes_count AS current_likes,
    pa_latest.engagement_rate,
    pa_latest.snapshot_date AS last_updated
FROM social_media_posts p
LEFT JOIN LATERAL (
    SELECT * FROM social_media_post_analytics
    WHERE post_id = p.id
    ORDER BY snapshot_date DESC
    LIMIT 1
) pa_latest ON TRUE
WHERE p.deleted_at IS NULL;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE social_media_accounts IS 'All 9 social media accounts with comprehensive metadata';
COMMENT ON TABLE social_media_posts IS 'All posts across platforms with URLs for content matching';
COMMENT ON TABLE social_media_content_mapping IS 'Links social posts to internal videos/clips';
COMMENT ON TABLE social_media_audience_demographics IS 'Audience age, gender, location demographics';
COMMENT ON TABLE api_usage_tracking IS 'Monitors API usage for rate limiting';

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$ 
BEGIN
    RAISE NOTICE '✅ Comprehensive Social Media Schema Created Successfully!';
    RAISE NOTICE '📊 Tables: 12 core tables + views created';
    RAISE NOTICE '🔗 Content mapping ready for videos/clips';
    RAISE NOTICE '📈 Supports all 9 platforms';
    RAISE NOTICE '🎯 Ready for analytics collection!';
END $$;
