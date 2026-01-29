-- Migration: Orchestrator Pipeline Tables (ARCH-001)
-- Date: 2026-01-28
-- Purpose: Add tables for Master Orchestrator Service to track pipeline execution

-- Orchestrator Pipelines Table
CREATE TABLE IF NOT EXISTS orchestrator_pipelines (
    pipeline_id VARCHAR(255) PRIMARY KEY,

    -- Configuration
    theme TEXT NOT NULL,
    num_parts INTEGER DEFAULT 3,
    character VARCHAR(255),
    publish_platforms TEXT[], -- Array of platform names
    schedule_tweets BOOLEAN DEFAULT true,
    tweets_per_day INTEGER DEFAULT 12,
    offer_url TEXT,

    -- State tracking
    status VARCHAR(50) NOT NULL DEFAULT 'initializing', -- initializing, generating_video, analyzing, publishing, scheduling_tweets, completed, failed
    correlation_id UUID NOT NULL,

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,

    -- Outputs
    stitched_video TEXT,
    analysis_result JSONB,
    published_count INTEGER DEFAULT 0,
    tweets_scheduled INTEGER DEFAULT 0,

    -- Error tracking
    error TEXT,

    -- Metadata
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Orchestrator Pipeline Steps Table
CREATE TABLE IF NOT EXISTS orchestrator_pipeline_steps (
    id SERIAL PRIMARY KEY,
    pipeline_id VARCHAR(255) NOT NULL REFERENCES orchestrator_pipelines(pipeline_id) ON DELETE CASCADE,

    -- Step details
    step_name VARCHAR(100) NOT NULL, -- sora_generation, video_stitching, content_analysis, publishing, twitter_campaign
    step_order INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed, skipped

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,

    -- Results
    output JSONB,
    error TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(pipeline_id, step_name)
);

-- Offer Traffic Tracking Table (ARCH-005)
CREATE TABLE IF NOT EXISTS offer_traffic_tracking (
    id SERIAL PRIMARY KEY,
    pipeline_id VARCHAR(255) REFERENCES orchestrator_pipelines(pipeline_id) ON DELETE CASCADE,

    -- Offer details
    offer_url TEXT NOT NULL,
    offer_name VARCHAR(255),

    -- Traffic source
    platform VARCHAR(50) NOT NULL, -- twitter, instagram, tiktok, etc.
    post_url TEXT,
    campaign_id VARCHAR(255),

    -- Metrics
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    revenue_usd DECIMAL(10, 2) DEFAULT 0.00,

    -- Timestamps
    tracked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    first_click_at TIMESTAMP WITH TIME ZONE,
    last_click_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analytics Feedback Loop Table (ARCH-006)
CREATE TABLE IF NOT EXISTS analytics_feedback (
    id SERIAL PRIMARY KEY,
    pipeline_id VARCHAR(255) REFERENCES orchestrator_pipelines(pipeline_id) ON DELETE CASCADE,

    -- Performance data
    platform VARCHAR(50) NOT NULL,
    post_url TEXT,

    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    engagement_rate FLOAT,

    -- AI feedback
    performance_rating VARCHAR(20), -- excellent, good, average, poor
    ai_insights TEXT, -- AI-generated insights about what worked/didn't work
    optimization_suggestions JSONB, -- Array of suggestions for improvement

    -- Timestamps
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analyzed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipelines_status ON orchestrator_pipelines(status);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipelines_started_at ON orchestrator_pipelines(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipelines_correlation_id ON orchestrator_pipelines(correlation_id);

CREATE INDEX IF NOT EXISTS idx_orchestrator_pipeline_steps_pipeline ON orchestrator_pipeline_steps(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipeline_steps_status ON orchestrator_pipeline_steps(status);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipeline_steps_order ON orchestrator_pipeline_steps(pipeline_id, step_order);

CREATE INDEX IF NOT EXISTS idx_offer_traffic_tracking_pipeline ON offer_traffic_tracking(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_offer_traffic_tracking_platform ON offer_traffic_tracking(platform);
CREATE INDEX IF NOT EXISTS idx_offer_traffic_tracking_tracked_at ON offer_traffic_tracking(tracked_at DESC);

CREATE INDEX IF NOT EXISTS idx_analytics_feedback_pipeline ON analytics_feedback(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_analytics_feedback_platform ON analytics_feedback(platform);
CREATE INDEX IF NOT EXISTS idx_analytics_feedback_measured_at ON analytics_feedback(measured_at DESC);

-- Comments
COMMENT ON TABLE orchestrator_pipelines IS 'Tracks end-to-end pipeline executions orchestrated by MasterOrchestrator (ARCH-001)';
COMMENT ON TABLE orchestrator_pipeline_steps IS 'Individual steps within each pipeline execution with timing and outputs';
COMMENT ON TABLE offer_traffic_tracking IS 'Tracks traffic and conversions from social media posts to offer URLs (ARCH-005)';
COMMENT ON TABLE analytics_feedback IS 'Stores AI-analyzed performance feedback for content optimization (ARCH-006)';
