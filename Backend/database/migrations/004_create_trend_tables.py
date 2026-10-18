"""
Migration: Create Trend Discovery Tables
=========================================
Creates tables for trend entities, media, metrics, clusters, and briefs.
"""

import asyncio
from sqlalchemy import text
from database.connection import engine

MIGRATION_SQL = """
-- =============================================================================
-- TREND ENTITIES (sounds, hashtags, keywords, users)
-- =============================================================================

CREATE TABLE IF NOT EXISTS trend_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    external_id VARCHAR(255),
    name VARCHAR(500) NOT NULL,
    platform VARCHAR(50) DEFAULT 'instagram',
    country VARCHAR(10),
    niche VARCHAR(100),
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    artist VARCHAR(255),
    preview_url TEXT,
    duration_sec FLOAT,
    username VARCHAR(255),
    follower_count INTEGER,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, type, external_id)
);

CREATE INDEX IF NOT EXISTS ix_trend_entity_type ON trend_entities(type);
CREATE INDEX IF NOT EXISTS ix_trend_entity_niche ON trend_entities(niche);
CREATE INDEX IF NOT EXISTS ix_trend_entity_country ON trend_entities(country);

-- =============================================================================
-- TREND MEDIA (raw posts/reels)
-- =============================================================================

CREATE TABLE IF NOT EXISTS trend_media (
    media_id VARCHAR(100) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    author_id VARCHAR(100),
    author_username VARCHAR(255),
    caption TEXT,
    hashtags TEXT[],
    keywords TEXT[],
    media_type VARCHAR(50),
    music_id VARCHAR(100),
    music_title VARCHAR(500),
    music_artist VARCHAR(255),
    play_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    share_count INTEGER,
    save_count INTEGER,
    engagement_rate FLOAT,
    velocity_score FLOAT,
    posted_at TIMESTAMPTZ,
    location_id VARCHAR(100),
    location_name VARCHAR(255),
    language VARCHAR(10),
    thumbnail_url TEXT,
    media_url TEXT,
    raw_data JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_trend_media_music_id ON trend_media(music_id);
CREATE INDEX IF NOT EXISTS ix_trend_media_author_id ON trend_media(author_id);
CREATE INDEX IF NOT EXISTS ix_trend_media_posted_at ON trend_media(posted_at);
CREATE INDEX IF NOT EXISTS ix_trend_media_platform ON trend_media(platform);

-- =============================================================================
-- TREND METRICS DAILY
-- =============================================================================

CREATE TABLE IF NOT EXISTS trend_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES trend_entities(id) ON DELETE CASCADE,
    date TIMESTAMPTZ NOT NULL,
    unique_creators INTEGER DEFAULT 0,
    total_posts INTEGER DEFAULT 0,
    new_posts_24h INTEGER DEFAULT 0,
    median_plays INTEGER,
    median_likes INTEGER,
    median_comments INTEGER,
    avg_engagement_rate FLOAT,
    velocity_score FLOAT,
    saturation_score FLOAT,
    efficiency_score FLOAT,
    trend_score FLOAT,
    velocity_delta_24h FLOAT,
    velocity_delta_7d FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(entity_id, date)
);

CREATE INDEX IF NOT EXISTS ix_trend_metrics_date ON trend_metrics_daily(date);
CREATE INDEX IF NOT EXISTS ix_trend_metrics_trend_score ON trend_metrics_daily(trend_score);

-- =============================================================================
-- TREND CLUSTERS
-- =============================================================================

CREATE TABLE IF NOT EXISTS trend_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500),
    slug VARCHAR(255) UNIQUE,
    summary TEXT,
    format_bullets JSONB,
    content_ideas JSONB,
    primary_sound_id UUID REFERENCES trend_entities(id),
    primary_hashtag VARCHAR(255),
    country VARCHAR(10),
    niche VARCHAR(100),
    velocity_score FLOAT,
    saturation_score FLOAT,
    trend_score FLOAT,
    decay_estimate_days INTEGER,
    geo_distribution JSONB,
    status VARCHAR(50) DEFAULT 'active',
    media_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_trend_cluster_niche ON trend_clusters(niche);
CREATE INDEX IF NOT EXISTS ix_trend_cluster_country ON trend_clusters(country);
CREATE INDEX IF NOT EXISTS ix_trend_cluster_trend_score ON trend_clusters(trend_score);

-- =============================================================================
-- TREND CLUSTER MEDIA (junction)
-- =============================================================================

CREATE TABLE IF NOT EXISTS trend_cluster_media (
    cluster_id UUID REFERENCES trend_clusters(id) ON DELETE CASCADE,
    media_id VARCHAR(100) REFERENCES trend_media(media_id) ON DELETE CASCADE,
    rank INTEGER,
    is_top_example BOOLEAN DEFAULT FALSE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (cluster_id, media_id)
);

-- =============================================================================
-- CONTENT BRIEFS
-- =============================================================================

CREATE TABLE IF NOT EXISTS content_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trend_type VARCHAR(50),
    trend_id VARCHAR(255),
    trend_name VARCHAR(500),
    hook_options JSONB,
    script_outline JSONB,
    recommended_format VARCHAR(50),
    optimal_length_sec JSONB,
    must_include_phrases JSONB,
    differentiation_twist TEXT,
    top_examples JSONB,
    niche VARCHAR(100),
    country VARCHAR(10),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_content_brief_trend_type ON content_briefs(trend_type);
CREATE INDEX IF NOT EXISTS ix_content_brief_niche ON content_briefs(niche);

-- =============================================================================
-- NICHES
-- =============================================================================

CREATE TABLE IF NOT EXISTS niches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    seed_hashtags TEXT[],
    seed_keywords TEXT[],
    seed_accounts TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- QUERY CACHE
-- =============================================================================

CREATE TABLE IF NOT EXISTS query_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_type VARCHAR(100) NOT NULL,
    input_hash VARCHAR(64) NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(query_type, input_hash)
);

CREATE INDEX IF NOT EXISTS ix_query_cache_expires ON query_cache(expires_at);

-- =============================================================================
-- USER SAVED ITEMS
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_saved_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) DEFAULT 'default',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS ix_user_saved_user_id ON user_saved_items(user_id);
CREATE INDEX IF NOT EXISTS ix_user_saved_collection ON user_saved_items(collection_name);

-- =============================================================================
-- EXPERIMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(255),
    variable VARCHAR(100),
    control_desc TEXT,
    variant_desc TEXT,
    success_metric VARCHAR(100),
    target_sample_size INTEGER DEFAULT 4,
    status VARCHAR(50) DEFAULT 'planned',
    control_posts JSONB,
    variant_posts JSONB,
    results JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_experiment_user_id ON experiments(user_id);
CREATE INDEX IF NOT EXISTS ix_experiment_status ON experiments(status);
"""


async def run_migration():
    """Run the migration to create trend tables."""
    async with engine.begin() as conn:
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in MIGRATION_SQL.split(';') if s.strip()]
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"Warning: {e}")
        print("✅ Trend tables migration complete")


if __name__ == "__main__":
    asyncio.run(run_migration())
