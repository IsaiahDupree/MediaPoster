-- Migration: Create top_engaged_followers table
-- Created: 2025-12-20
-- Purpose: Store follower engagement data for the Followers/Top Fans page

CREATE TABLE IF NOT EXISTS top_engaged_followers (
    id SERIAL PRIMARY KEY,
    follower_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    profile_url TEXT,
    avatar_url TEXT,
    follower_count INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    
    -- Engagement metrics
    engagement_score FLOAT DEFAULT 0.0,
    engagement_tier TEXT DEFAULT 'lurker', -- super_fan, active, lurker, inactive
    total_interactions INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    avg_sentiment FLOAT DEFAULT 0.5,
    
    -- Activity tracking
    first_interaction TIMESTAMP WITH TIME ZONE,
    last_interaction TIMESTAMP WITH TIME ZONE,
    
    -- Ranking
    rank INTEGER,
    platform_rank INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(platform, follower_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_followers_platform ON top_engaged_followers(platform);
CREATE INDEX IF NOT EXISTS idx_followers_tier ON top_engaged_followers(engagement_tier);
CREATE INDEX IF NOT EXISTS idx_followers_score ON top_engaged_followers(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_followers_last_interaction ON top_engaged_followers(last_interaction DESC);

-- Comments
COMMENT ON TABLE top_engaged_followers IS 'Tracks most engaged followers across platforms';
COMMENT ON COLUMN top_engaged_followers.engagement_tier IS 'super_fan (top 5%), active (top 20%), lurker (occasional), inactive (no recent activity)';
