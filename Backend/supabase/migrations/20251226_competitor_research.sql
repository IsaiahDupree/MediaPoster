-- Competitor Research System Tables
-- Migration: 20251226_competitor_research

-- Tracked competitor accounts
CREATE TABLE IF NOT EXISTS competitor_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    user_id TEXT,
    full_name TEXT,
    bio TEXT,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    media_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    profile_pic_url TEXT,
    category TEXT,
    external_url TEXT,
    priority INTEGER DEFAULT 1,  -- 1=high, 2=medium, 3=low
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Competitor content (reels, posts)
CREATE TABLE IF NOT EXISTS competitor_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES competitor_accounts(id) ON DELETE CASCADE,
    media_id TEXT UNIQUE NOT NULL,
    shortcode TEXT,
    media_type TEXT,  -- 'reel', 'post', 'carousel', 'story'
    caption TEXT,
    
    -- Metrics
    play_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    save_count INTEGER DEFAULT 0,
    
    -- Calculated metrics
    engagement_rate NUMERIC,
    viral_score NUMERIC,
    
    -- Media URLs
    video_url TEXT,
    thumbnail_url TEXT,
    
    -- Local storage paths
    local_video_path TEXT,
    local_thumbnail_path TEXT,
    
    -- Audio info
    audio_id TEXT,
    audio_title TEXT,
    audio_artist TEXT,
    audio_url TEXT,
    
    -- Timestamps
    posted_at TIMESTAMP WITH TIME ZONE,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analyzed_at TIMESTAMP WITH TIME ZONE,
    
    -- Analysis results (JSONB for flexibility)
    detected_hooks JSONB,
    content_themes JSONB,
    visual_style JSONB,
    ai_analysis JSONB,
    raw_api_response JSONB
);

-- Analysis learnings extracted from competitor content
CREATE TABLE IF NOT EXISTS competitor_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES competitor_accounts(id) ON DELETE CASCADE,
    learning_type TEXT NOT NULL,  -- 'hook', 'format', 'timing', 'topic', 'style'
    title TEXT NOT NULL,
    description TEXT,
    evidence JSONB,  -- References to content that supports this learning
    confidence_score NUMERIC,
    is_applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_competitor_content_account ON competitor_content(account_id);
CREATE INDEX IF NOT EXISTS idx_competitor_content_media_type ON competitor_content(media_type);
CREATE INDEX IF NOT EXISTS idx_competitor_content_viral_score ON competitor_content(viral_score DESC);
CREATE INDEX IF NOT EXISTS idx_competitor_learnings_type ON competitor_learnings(learning_type);

-- Comments
COMMENT ON TABLE competitor_accounts IS 'Tracked competitor/influencer Instagram accounts';
COMMENT ON TABLE competitor_content IS 'Downloaded content from competitor accounts with metrics';
COMMENT ON TABLE competitor_learnings IS 'AI-extracted learnings and patterns from competitor content';
