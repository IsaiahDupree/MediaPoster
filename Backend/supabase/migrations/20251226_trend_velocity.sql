-- Trend Velocity Tracking Tables
-- Stores time-series data for calculating trend velocity (acceleration)

-- ============================================================================
-- HASHTAG VELOCITY TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS trend_hashtag_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hashtag TEXT NOT NULL,
    media_count BIGINT NOT NULL,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes for time-series queries
    CONSTRAINT unique_hashtag_snapshot UNIQUE (hashtag, snapshot_at)
);

CREATE INDEX IF NOT EXISTS idx_hashtag_snapshots_time 
ON trend_hashtag_snapshots(hashtag, snapshot_at DESC);

-- ============================================================================
-- SOUND/AUDIO VELOCITY TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS trend_sound_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audio_id TEXT NOT NULL,
    title TEXT,
    artist TEXT,
    usage_count BIGINT NOT NULL,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_sound_snapshot UNIQUE (audio_id, snapshot_at)
);

CREATE INDEX IF NOT EXISTS idx_sound_snapshots_time 
ON trend_sound_snapshots(audio_id, snapshot_at DESC);

-- ============================================================================
-- KEYWORD VELOCITY TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS trend_keyword_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL,
    keyword_type TEXT NOT NULL, -- hook, format, phrase, hashtag
    frequency INTEGER NOT NULL,
    avg_engagement FLOAT DEFAULT 0,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_keyword_snapshot UNIQUE (keyword, keyword_type, snapshot_at)
);

CREATE INDEX IF NOT EXISTS idx_keyword_snapshots_time 
ON trend_keyword_snapshots(keyword, snapshot_at DESC);

-- ============================================================================
-- COMPUTED VELOCITY SCORES (materialized view or table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trend_velocity_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trend_type TEXT NOT NULL, -- hashtag, sound, keyword
    trend_id TEXT NOT NULL,   -- hashtag name, audio_id, or keyword
    trend_name TEXT NOT NULL, -- display name
    
    -- Current metrics
    current_count BIGINT NOT NULL,
    
    -- Velocity calculations
    velocity_1d FLOAT DEFAULT 0,  -- 24h change rate
    velocity_7d FLOAT DEFAULT 0,  -- 7d change rate
    velocity_30d FLOAT DEFAULT 0, -- 30d change rate
    
    -- Acceleration (velocity of velocity)
    acceleration FLOAT DEFAULT 0,
    
    -- Final score
    trending_score FLOAT DEFAULT 0,
    
    -- Metadata
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_trend_score UNIQUE (trend_type, trend_id)
);

CREATE INDEX IF NOT EXISTS idx_velocity_scores_type 
ON trend_velocity_scores(trend_type, trending_score DESC);

-- ============================================================================
-- TREND BRIEFS (AI-generated summaries)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trend_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trend_type TEXT NOT NULL,
    trend_id TEXT NOT NULL,
    trend_name TEXT NOT NULL,
    
    -- AI-generated content
    summary TEXT,
    why_trending TEXT,
    content_ideas JSONB DEFAULT '[]',
    example_posts JSONB DEFAULT '[]',
    target_audience TEXT,
    best_posting_time TEXT,
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
    
    CONSTRAINT unique_trend_brief UNIQUE (trend_type, trend_id)
);

CREATE INDEX IF NOT EXISTS idx_trend_briefs_type 
ON trend_briefs(trend_type, generated_at DESC);

-- ============================================================================
-- FUNCTION: Calculate velocity from snapshots
-- ============================================================================
CREATE OR REPLACE FUNCTION calculate_velocity(
    p_trend_type TEXT,
    p_trend_id TEXT,
    p_hours INTEGER DEFAULT 24
) RETURNS FLOAT AS $$
DECLARE
    v_current BIGINT;
    v_previous BIGINT;
    v_velocity FLOAT;
BEGIN
    -- Get current and previous counts based on trend type
    IF p_trend_type = 'hashtag' THEN
        SELECT media_count INTO v_current
        FROM trend_hashtag_snapshots
        WHERE hashtag = p_trend_id
        ORDER BY snapshot_at DESC LIMIT 1;
        
        SELECT media_count INTO v_previous
        FROM trend_hashtag_snapshots
        WHERE hashtag = p_trend_id
        AND snapshot_at <= NOW() - (p_hours || ' hours')::INTERVAL
        ORDER BY snapshot_at DESC LIMIT 1;
        
    ELSIF p_trend_type = 'sound' THEN
        SELECT usage_count INTO v_current
        FROM trend_sound_snapshots
        WHERE audio_id = p_trend_id
        ORDER BY snapshot_at DESC LIMIT 1;
        
        SELECT usage_count INTO v_previous
        FROM trend_sound_snapshots
        WHERE audio_id = p_trend_id
        AND snapshot_at <= NOW() - (p_hours || ' hours')::INTERVAL
        ORDER BY snapshot_at DESC LIMIT 1;
    END IF;
    
    -- Calculate velocity (percentage change)
    IF v_previous IS NULL OR v_previous = 0 THEN
        v_velocity := 0;
    ELSE
        v_velocity := ((v_current - v_previous)::FLOAT / v_previous) * 100;
    END IF;
    
    RETURN COALESCE(v_velocity, 0);
END;
$$ LANGUAGE plpgsql;
