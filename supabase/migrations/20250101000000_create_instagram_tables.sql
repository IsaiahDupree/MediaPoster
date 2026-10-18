-- Instagram TrendTok Tables
-- Phase 1: Foundation schema for Instagram data ingestion

-- Profiles table
CREATE TABLE IF NOT EXISTS ig_profiles (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT,
    bio TEXT,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    media_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    profile_pic_url TEXT,
    provider TEXT NOT NULL, -- 'rapidapi' | 'official'
    external_url TEXT,
    is_business BOOLEAN,
    category TEXT,
    last_fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ig_profiles_username ON ig_profiles(username);
CREATE INDEX IF NOT EXISTS idx_ig_profiles_provider ON ig_profiles(provider);
CREATE INDEX IF NOT EXISTS idx_ig_profiles_last_fetched ON ig_profiles(last_fetched_at);

-- Media table
CREATE TABLE IF NOT EXISTS ig_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ig_media_id TEXT UNIQUE NOT NULL,
    profile_id TEXT REFERENCES ig_profiles(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL, -- 'REEL' | 'IMAGE' | 'CAROUSEL' | 'VIDEO'
    caption TEXT,
    permalink TEXT,
    thumbnail_url TEXT,
    video_url TEXT,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    play_count INTEGER,
    timestamp TIMESTAMPTZ,
    audio_id TEXT,
    hashtags TEXT[] DEFAULT '{}',
    mentions TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ig_media_profile ON ig_media(profile_id);
CREATE INDEX IF NOT EXISTS idx_ig_media_type ON ig_media(media_type);
CREATE INDEX IF NOT EXISTS idx_ig_media_timestamp ON ig_media(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ig_media_audio ON ig_media(audio_id) WHERE audio_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ig_media_hashtags ON ig_media USING GIN(hashtags);

-- Audio/Sounds table
CREATE TABLE IF NOT EXISTS ig_audio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audio_id TEXT UNIQUE NOT NULL,
    title TEXT,
    artist TEXT,
    duration_ms INTEGER,
    usage_count INTEGER DEFAULT 0,
    velocity_7d FLOAT,
    trending_score FLOAT,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ig_audio_trending ON ig_audio(trending_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_ig_audio_velocity ON ig_audio(velocity_7d DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_ig_audio_usage ON ig_audio(usage_count DESC);

-- Hashtags table
CREATE TABLE IF NOT EXISTS ig_hashtags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag TEXT UNIQUE NOT NULL,
    media_count INTEGER DEFAULT 0,
    velocity_7d FLOAT,
    trending_score FLOAT,
    category TEXT,
    last_updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ig_hashtags_trending ON ig_hashtags(trending_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_ig_hashtags_velocity ON ig_hashtags(velocity_7d DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_ig_hashtags_category ON ig_hashtags(category) WHERE category IS NOT NULL;

-- Trend Cards (format templates)
CREATE TABLE IF NOT EXISTS trend_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    format_type TEXT, -- 'hook_style' | 'pov' | 'tutorial' | 'storytelling'
    example_media_ids TEXT[] DEFAULT '{}',
    velocity_7d FLOAT,
    trending_score FLOAT,
    region TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trend_cards_trending ON trend_cards(trending_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_trend_cards_region ON trend_cards(region);
CREATE INDEX IF NOT EXISTS idx_trend_cards_format ON trend_cards(format_type);

-- Trend Observations (time-series data)
CREATE TABLE IF NOT EXISTS trend_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL, -- 'audio' | 'hashtag' | 'format'
    entity_id TEXT NOT NULL,
    observation_date DATE NOT NULL,
    usage_count INTEGER DEFAULT 0,
    engagement_rate FLOAT,
    region TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(entity_type, entity_id, observation_date, region)
);

CREATE INDEX IF NOT EXISTS idx_trend_obs_entity ON trend_observations(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_trend_obs_date ON trend_observations(observation_date DESC);
CREATE INDEX IF NOT EXISTS idx_trend_obs_region ON trend_observations(region);

-- Analysis Jobs (for video analyzer)
CREATE TABLE IF NOT EXISTS ig_analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID, -- Can reference external video or uploaded file
    media_id TEXT, -- Instagram media ID if analyzing existing IG content
    status TEXT DEFAULT 'pending', -- 'pending' | 'processing' | 'completed' | 'failed'
    transcript TEXT,
    hook_type TEXT,
    pacing TEXT,
    text_density FLOAT,
    matched_trend_cards UUID[] DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ig_analysis_status ON ig_analysis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ig_analysis_created ON ig_analysis_jobs(created_at DESC);

-- Comments for documentation
COMMENT ON TABLE ig_profiles IS 'Instagram profile/account information';
COMMENT ON TABLE ig_media IS 'Instagram posts, reels, images, and carousels';
COMMENT ON TABLE ig_audio IS 'Audio tracks used in reels with trending metrics';
COMMENT ON TABLE ig_hashtags IS 'Hashtags with usage and trending metrics';
COMMENT ON TABLE trend_cards IS 'Content format templates (e.g., Text-Hook Short-Form)';
COMMENT ON TABLE trend_observations IS 'Time-series data for trend velocity calculations';
COMMENT ON TABLE ig_analysis_jobs IS 'Video analysis jobs with AI recommendations';
