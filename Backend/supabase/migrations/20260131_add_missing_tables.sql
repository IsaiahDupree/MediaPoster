-- Migration: Add missing tables for services
-- Date: 2026-01-31
-- Services affected: post_scheduler, slot_executor, video_ready_pipeline

-- 1. scheduled_posts - Used by post_scheduler.py
CREATE TABLE IF NOT EXISTS scheduled_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id UUID,
    content_variant_id UUID,
    platform VARCHAR(50) NOT NULL,
    platform_account_id INTEGER,
    scheduled_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    caption TEXT,
    title TEXT,
    hashtags TEXT[],
    account_username VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_time ON scheduled_posts(scheduled_time);

-- 2. weekly_plan_slots - Used by slot_executor.py
CREATE TABLE IF NOT EXISTS weekly_plan_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID,
    slot_date DATE NOT NULL,
    slot_time TIME NOT NULL,
    platform VARCHAR(50) NOT NULL,
    channel VARCHAR(100),
    awareness_level VARCHAR(50),
    fate_target VARCHAR(100),
    cta_strength INTEGER DEFAULT 5,
    target_offer_id UUID,
    target_icp_id UUID,
    status VARCHAR(50) DEFAULT 'scheduled',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_weekly_plan_slots_status ON weekly_plan_slots(status);
CREATE INDEX IF NOT EXISTS idx_weekly_plan_slots_date ON weekly_plan_slots(slot_date);

-- 3. original_videos - Used by video_ready_pipeline.py
CREATE TABLE IF NOT EXISTS original_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_size BIGINT,
    status VARCHAR(50) DEFAULT 'pending',
    source VARCHAR(100),
    ai_title TEXT,
    ai_description TEXT,
    transcript TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_original_videos_status ON original_videos(status);
CREATE INDEX IF NOT EXISTS idx_original_videos_file_path ON original_videos(file_path);

-- 4. analyzed_videos - Used by video_ready_pipeline.py for AI analysis results
CREATE TABLE IF NOT EXISTS analyzed_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_video_id UUID REFERENCES original_videos(id) ON DELETE CASCADE,
    transcript TEXT,
    ai_title TEXT,
    ai_description TEXT,
    ai_hashtags JSONB DEFAULT '[]',
    virality_score FLOAT DEFAULT 0,
    duration_seconds FLOAT DEFAULT 0,
    topics JSONB DEFAULT '[]',
    platform_captions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(original_video_id)
);

CREATE INDEX IF NOT EXISTS idx_analyzed_videos_original ON analyzed_videos(original_video_id);
CREATE INDEX IF NOT EXISTS idx_analyzed_videos_virality ON analyzed_videos(virality_score);

-- 5. platform_accounts - Referenced by multiple services
CREATE TABLE IF NOT EXISTS platform_accounts (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    account_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, username)
);

-- Insert default platform accounts (from blotato_service.py)
INSERT INTO platform_accounts (id, platform, username, display_name, account_id, is_active) VALUES
(228, 'youtube', 'UCnDBsELI2OlaEl5yxA77HNA', 'Isaiah Dupree', '228', TRUE),
(710, 'tiktok', 'isaiah_dupree', 'Isaiah Dupree', '710', TRUE),
(807, 'instagram', 'the_isaiah_dupree', 'Isaiah Dupree', '807', TRUE),
(173, 'threads', 'the_isaiah_dupree_', 'Isaiah Dupree', '173', TRUE)
ON CONFLICT (id) DO NOTHING;
