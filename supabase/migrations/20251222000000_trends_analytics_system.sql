-- ============================================================================
-- TRENDS & ANALYTICS SYSTEM (Standalone)
-- ============================================================================
-- This is a separate system from the main MediaPoster content management.
-- It tracks external trends from social media platforms and app stores.
-- ============================================================================

-- ============================================================================
-- SOCIAL MEDIA TRENDS
-- ============================================================================

-- Trending hashtags across platforms
CREATE TABLE IF NOT EXISTS trend_hashtags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL, -- tiktok, instagram, twitter, youtube
    hashtag TEXT NOT NULL,
    rank INTEGER,
    post_count BIGINT,
    view_count BIGINT,
    growth_rate DECIMAL(10, 4), -- % growth in last 24h
    category TEXT, -- entertainment, music, comedy, education, etc.
    region TEXT DEFAULT 'global', -- US, global, UK, etc.
    is_sponsored BOOLEAN DEFAULT false,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, hashtag, snapshot_at)
);

-- Trending sounds/audio
CREATE TABLE IF NOT EXISTS trend_sounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL, -- tiktok, instagram
    sound_id TEXT,
    sound_name TEXT NOT NULL,
    artist_name TEXT,
    rank INTEGER,
    usage_count BIGINT,
    growth_rate DECIMAL(10, 4),
    duration_seconds INTEGER,
    is_original BOOLEAN DEFAULT false,
    region TEXT DEFAULT 'global',
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, sound_id, snapshot_at)
);

-- Trending topics/keywords
CREATE TABLE IF NOT EXISTS trend_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    topic TEXT NOT NULL,
    rank INTEGER,
    mention_count BIGINT,
    sentiment_score DECIMAL(5, 4), -- -1 to 1
    growth_rate DECIMAL(10, 4),
    related_hashtags TEXT[], -- array of related hashtags
    category TEXT,
    region TEXT DEFAULT 'global',
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, topic, snapshot_at)
);

-- Trending creators/influencers
CREATE TABLE IF NOT EXISTS trend_creators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    follower_count BIGINT,
    follower_growth BIGINT, -- gained in period
    engagement_rate DECIMAL(10, 4),
    avg_views BIGINT,
    content_category TEXT,
    verified BOOLEAN DEFAULT false,
    rank INTEGER,
    region TEXT DEFAULT 'global',
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    profile_url TEXT,
    avatar_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, username, snapshot_at)
);

-- Trending video formats/styles
CREATE TABLE IF NOT EXISTS trend_formats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    format_name TEXT NOT NULL, -- "get ready with me", "storytime", "POV", etc.
    description TEXT,
    example_count BIGINT,
    avg_engagement_rate DECIMAL(10, 4),
    growth_rate DECIMAL(10, 4),
    typical_duration_seconds INTEGER,
    best_posting_times JSONB, -- {"monday": ["9:00", "18:00"], ...}
    rank INTEGER,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, format_name, snapshot_at)
);

-- ============================================================================
-- APP STORE ANALYTICS
-- ============================================================================

-- App rankings
CREATE TABLE IF NOT EXISTS appstore_rankings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store TEXT NOT NULL, -- apple, google
    app_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    developer TEXT,
    category TEXT NOT NULL, -- social, photo_video, entertainment, etc.
    chart_type TEXT NOT NULL, -- free, paid, grossing
    rank INTEGER NOT NULL,
    previous_rank INTEGER,
    rank_change INTEGER, -- positive = moved up
    rating DECIMAL(3, 2),
    rating_count BIGINT,
    price DECIMAL(10, 2),
    region TEXT DEFAULT 'US',
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    icon_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(store, app_id, chart_type, region, snapshot_at)
);

-- App metrics over time
CREATE TABLE IF NOT EXISTS appstore_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store TEXT NOT NULL,
    app_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    daily_downloads_estimate BIGINT,
    monthly_downloads_estimate BIGINT,
    daily_revenue_estimate DECIMAL(12, 2),
    monthly_revenue_estimate DECIMAL(12, 2),
    rating DECIMAL(3, 2),
    rating_count BIGINT,
    review_count BIGINT,
    update_frequency_days INTEGER,
    last_update_at TIMESTAMPTZ,
    version TEXT,
    size_mb DECIMAL(10, 2),
    region TEXT DEFAULT 'US',
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(store, app_id, region, snapshot_at)
);

-- App reviews sentiment
CREATE TABLE IF NOT EXISTS appstore_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store TEXT NOT NULL,
    app_id TEXT NOT NULL,
    review_id TEXT,
    rating INTEGER, -- 1-5
    title TEXT,
    content TEXT,
    author TEXT,
    sentiment_score DECIMAL(5, 4),
    key_topics TEXT[],
    is_featured BOOLEAN DEFAULT false,
    helpful_count INTEGER,
    review_date TIMESTAMPTZ,
    version_reviewed TEXT,
    region TEXT DEFAULT 'US',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(store, review_id)
);

-- ============================================================================
-- INDUSTRY BENCHMARKS
-- ============================================================================

CREATE TABLE IF NOT EXISTS industry_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    category TEXT NOT NULL, -- content niche
    metric_name TEXT NOT NULL, -- engagement_rate, avg_views, follower_growth
    metric_value DECIMAL(15, 6),
    percentile_25 DECIMAL(15, 6),
    percentile_50 DECIMAL(15, 6),
    percentile_75 DECIMAL(15, 6),
    percentile_90 DECIMAL(15, 6),
    sample_size INTEGER,
    time_period TEXT, -- daily, weekly, monthly
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, category, metric_name, time_period, snapshot_at)
);

-- ============================================================================
-- TREND ALERTS & NOTIFICATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS trend_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type TEXT NOT NULL, -- new_trend, viral_sound, trending_topic, app_ranking_change
    platform TEXT,
    title TEXT NOT NULL,
    description TEXT,
    importance TEXT DEFAULT 'medium', -- low, medium, high, critical
    trend_data JSONB, -- the actual trend data
    is_read BOOLEAN DEFAULT false,
    is_dismissed BOOLEAN DEFAULT false,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User's saved/tracked trends
CREATE TABLE IF NOT EXISTS saved_trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trend_type TEXT NOT NULL, -- hashtag, sound, topic, creator, format, app
    trend_id UUID NOT NULL, -- reference to the trend table
    platform TEXT,
    notes TEXT,
    tags TEXT[],
    notify_on_change BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- COMPETITOR TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS tracked_competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, username)
);

CREATE TABLE IF NOT EXISTS competitor_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID REFERENCES tracked_competitors(id) ON DELETE CASCADE,
    follower_count BIGINT,
    following_count BIGINT,
    post_count BIGINT,
    avg_likes BIGINT,
    avg_comments BIGINT,
    avg_views BIGINT,
    engagement_rate DECIMAL(10, 4),
    top_hashtags TEXT[],
    posting_frequency DECIMAL(5, 2), -- posts per day
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_trend_hashtags_platform_time ON trend_hashtags(platform, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_hashtags_rank ON trend_hashtags(platform, rank) WHERE rank <= 50;
CREATE INDEX IF NOT EXISTS idx_trend_sounds_platform_time ON trend_sounds(platform, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_topics_platform_time ON trend_topics(platform, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_creators_platform_time ON trend_creators(platform, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_appstore_rankings_store_time ON appstore_rankings(store, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_appstore_rankings_category ON appstore_rankings(store, category, chart_type, rank);
CREATE INDEX IF NOT EXISTS idx_trend_alerts_unread ON trend_alerts(is_read, created_at DESC) WHERE NOT is_read;
CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_time ON competitor_snapshots(competitor_id, snapshot_at DESC);

-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

-- Latest trends per platform
CREATE OR REPLACE VIEW latest_hashtag_trends AS
SELECT DISTINCT ON (platform, hashtag) *
FROM trend_hashtags
ORDER BY platform, hashtag, snapshot_at DESC;

CREATE OR REPLACE VIEW latest_sound_trends AS
SELECT DISTINCT ON (platform, sound_id) *
FROM trend_sounds
ORDER BY platform, sound_id, snapshot_at DESC;

CREATE OR REPLACE VIEW top_trending_now AS
SELECT 
    'hashtag' as trend_type,
    platform,
    hashtag as name,
    rank,
    growth_rate,
    snapshot_at
FROM trend_hashtags
WHERE snapshot_at > NOW() - INTERVAL '24 hours'
AND rank <= 10
UNION ALL
SELECT 
    'sound' as trend_type,
    platform,
    sound_name as name,
    rank,
    growth_rate,
    snapshot_at
FROM trend_sounds
WHERE snapshot_at > NOW() - INTERVAL '24 hours'
AND rank <= 10
UNION ALL
SELECT 
    'topic' as trend_type,
    platform,
    topic as name,
    rank,
    growth_rate,
    snapshot_at
FROM trend_topics
WHERE snapshot_at > NOW() - INTERVAL '24 hours'
AND rank <= 10
ORDER BY platform, trend_type, rank;

-- App store leaders
CREATE OR REPLACE VIEW appstore_leaders AS
SELECT DISTINCT ON (store, category, chart_type) *
FROM appstore_rankings
WHERE rank <= 10
ORDER BY store, category, chart_type, snapshot_at DESC, rank;
