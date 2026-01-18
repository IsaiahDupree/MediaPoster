-- Instagram Trending Music table
-- Stores discovered trending music from Instagram reels

CREATE TABLE IF NOT EXISTS instagram_trending_music (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    artist TEXT,
    duration_sec FLOAT,
    usage_count INTEGER DEFAULT 0,
    audio_url TEXT,
    cover_url TEXT,
    is_trending BOOLEAN DEFAULT FALSE,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    source_post_id TEXT,
    genre TEXT,
    mood TEXT,
    local_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ig_music_trending ON instagram_trending_music(is_trending);
CREATE INDEX IF NOT EXISTS idx_ig_music_usage ON instagram_trending_music(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_ig_music_discovered ON instagram_trending_music(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_ig_music_genre ON instagram_trending_music(genre);
CREATE INDEX IF NOT EXISTS idx_ig_music_mood ON instagram_trending_music(mood);

COMMENT ON TABLE instagram_trending_music IS 'Trending music discovered from Instagram reels via RapidAPI crawler';
