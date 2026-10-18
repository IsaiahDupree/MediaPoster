-- Fix schema mismatches identified in endpoint testing
-- Migration: 20250122000000_fix_schema_mismatches
-- Created: 2025-11-22
-- Adds missing tables and columns

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- 1. Add missing video_metadata column to original_videos
-- =====================================================

-- Check if column exists and add it if not
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'original_videos' 
        AND column_name = 'video_metadata'
    ) THEN
        ALTER TABLE original_videos 
        ADD COLUMN video_metadata JSONB;
        
        RAISE NOTICE 'Added video_metadata column to original_videos';
    ELSE
        RAISE NOTICE 'video_metadata column already exists in original_videos';
    END IF;
END $$;

-- =====================================================
-- 2. Create processing_jobs table if not exists
-- =====================================================

CREATE TABLE IF NOT EXISTS processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(100) NOT NULL,
    
    entity_id UUID,
    entity_type VARCHAR(50),
    
    status VARCHAR(50) DEFAULT 'queued',
    progress_percent INTEGER DEFAULT 0,
    
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    result JSONB,
    error_message TEXT,
    
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_entity ON processing_jobs(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created ON processing_jobs(created_at DESC);

COMMENT ON TABLE processing_jobs IS 'Async processing jobs queue for video analysis and other background tasks';

-- =====================================================
-- 3. Create scheduled_posts table if not exists
-- =====================================================

CREATE TABLE IF NOT EXISTS scheduled_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id UUID,
    content_variant_id UUID,
    
    platform VARCHAR(50) NOT NULL,
    platform_account_id TEXT,
    
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    
    publish_response JSONB,
    error_message TEXT,
    platform_post_id TEXT,
    platform_url TEXT,
    
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    
    is_ai_recommended BOOLEAN DEFAULT false,
    recommendation_score FLOAT,
    recommendation_reasoning TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_time ON scheduled_posts(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_platform ON scheduled_posts(platform);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_clip ON scheduled_posts(clip_id);

COMMENT ON TABLE scheduled_posts IS 'Scheduled posts for content publishing across platforms';

-- =====================================================
-- 4. Create posting_goals table if not exists
-- =====================================================

CREATE TABLE IF NOT EXISTS posting_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    goal_type VARCHAR(100) NOT NULL,
    goal_name VARCHAR(255) NOT NULL,
    
    target_metrics JSONB NOT NULL,
    
    priority INTEGER DEFAULT 1,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    
    status VARCHAR(50) DEFAULT 'active',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_posting_goals_user ON posting_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_posting_goals_status ON posting_goals(status);
CREATE INDEX IF NOT EXISTS idx_posting_goals_type ON posting_goals(goal_type);

COMMENT ON TABLE posting_goals IS 'Content posting goals and targets for tracking';

-- =====================================================
-- Success message
-- =====================================================

DO $$ 
BEGIN
    RAISE NOTICE 'Schema fixes applied successfully';
    RAISE NOTICE '- Added video_metadata column to original_videos (if missing)';
    RAISE NOTICE '- Created processing_jobs table (if not exists)';
    RAISE NOTICE '- Created scheduled_posts table (if not exists)';
    RAISE NOTICE '- Created posting_goals table (if not exists)';
END $$;

