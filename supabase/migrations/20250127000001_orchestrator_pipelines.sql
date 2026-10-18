-- Migration: Orchestrator Pipeline Tracking (ARCH-001)
-- ======================================================
-- Creates tables for tracking orchestrator pipeline executions.
-- Used by MasterOrchestrator service to persist pipeline state.

-- Pipelines table: Track full pipeline runs
CREATE TABLE IF NOT EXISTS orchestrator_pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id VARCHAR(50) UNIQUE NOT NULL,
    theme TEXT NOT NULL,
    num_parts INTEGER DEFAULT 3,
    character VARCHAR(200),

    -- Platform configuration
    publish_platforms TEXT[], -- ['tiktok', 'instagram', 'youtube']
    schedule_tweets BOOLEAN DEFAULT false,
    tweets_per_day INTEGER DEFAULT 12,
    offer_url TEXT,

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'initializing',
    steps_completed TEXT[] DEFAULT '{}',

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,

    -- Outputs
    video_path TEXT,
    stitched_video TEXT,
    analysis_result JSONB,
    published_count INTEGER DEFAULT 0,
    tweets_scheduled INTEGER DEFAULT 0,

    -- Error tracking
    error TEXT,
    error_step VARCHAR(100),

    -- Metadata
    correlation_id VARCHAR(100),
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_status CHECK (status IN (
        'initializing',
        'generating_video',
        'analyzing',
        'publishing',
        'scheduling_tweets',
        'completed',
        'failed'
    ))
);

-- Pipeline steps table: Track individual step execution
CREATE TABLE IF NOT EXISTS orchestrator_pipeline_steps (
    id BIGSERIAL PRIMARY KEY,
    pipeline_id VARCHAR(50) NOT NULL REFERENCES orchestrator_pipelines(pipeline_id) ON DELETE CASCADE,

    -- Step identification
    step_name VARCHAR(100) NOT NULL,
    step_order INTEGER NOT NULL,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,

    -- Performance
    duration_seconds FLOAT,

    -- Outputs and errors
    output JSONB,
    error TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_step_status CHECK (status IN (
        'pending',
        'running',
        'completed',
        'failed',
        'skipped',
        'retrying'
    ))
);

-- Indexes for performance
CREATE INDEX idx_orchestrator_pipelines_status ON orchestrator_pipelines(status, started_at DESC);
CREATE INDEX idx_orchestrator_pipelines_theme ON orchestrator_pipelines USING gin(to_tsvector('english', theme));
CREATE INDEX idx_orchestrator_pipelines_started_at ON orchestrator_pipelines(started_at DESC);
CREATE INDEX idx_orchestrator_pipelines_correlation_id ON orchestrator_pipelines(correlation_id);

CREATE INDEX idx_orchestrator_pipeline_steps_pipeline ON orchestrator_pipeline_steps(pipeline_id, step_order);
CREATE INDEX idx_orchestrator_pipeline_steps_status ON orchestrator_pipeline_steps(status);
CREATE INDEX idx_orchestrator_pipeline_steps_duration ON orchestrator_pipeline_steps(step_name, duration_seconds);

-- Function to automatically calculate step duration
CREATE OR REPLACE FUNCTION calculate_step_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds := EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at));
    ELSIF NEW.failed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds := EXTRACT(EPOCH FROM (NEW.failed_at - NEW.started_at));
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER orchestrator_step_duration_trigger
    BEFORE UPDATE ON orchestrator_pipeline_steps
    FOR EACH ROW
    EXECUTE FUNCTION calculate_step_duration();

-- Function to get pipeline summary
CREATE OR REPLACE FUNCTION get_pipeline_summary(p_pipeline_id VARCHAR(50))
RETURNS TABLE (
    pipeline_id VARCHAR(50),
    theme TEXT,
    status VARCHAR(50),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,
    steps_completed INTEGER,
    total_steps INTEGER,
    video_path TEXT,
    published_count INTEGER,
    tweets_scheduled INTEGER,
    error TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.pipeline_id,
        p.theme,
        p.status,
        p.started_at,
        p.completed_at,
        CASE
            WHEN p.completed_at IS NOT NULL THEN EXTRACT(EPOCH FROM (p.completed_at - p.started_at))
            WHEN p.failed_at IS NOT NULL THEN EXTRACT(EPOCH FROM (p.failed_at - p.started_at))
            ELSE EXTRACT(EPOCH FROM (NOW() - p.started_at))
        END as duration_seconds,
        array_length(p.steps_completed, 1) as steps_completed,
        (SELECT COUNT(*) FROM orchestrator_pipeline_steps WHERE orchestrator_pipeline_steps.pipeline_id = p.pipeline_id) as total_steps,
        p.stitched_video as video_path,
        p.published_count,
        p.tweets_scheduled,
        p.error
    FROM orchestrator_pipelines p
    WHERE p.pipeline_id = p_pipeline_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get pipeline performance metrics
CREATE OR REPLACE FUNCTION get_pipeline_metrics(days INTEGER DEFAULT 30)
RETURNS TABLE (
    total_pipelines BIGINT,
    successful_pipelines BIGINT,
    failed_pipelines BIGINT,
    success_rate NUMERIC,
    avg_duration_seconds FLOAT,
    total_videos_generated BIGINT,
    total_posts_published BIGINT,
    total_tweets_scheduled BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_pipelines,
        COUNT(*) FILTER (WHERE status = 'completed') as successful_pipelines,
        COUNT(*) FILTER (WHERE status = 'failed') as failed_pipelines,
        CASE
            WHEN COUNT(*) > 0 THEN
                ROUND((COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC / COUNT(*)) * 100, 2)
            ELSE 0
        END as success_rate,
        AVG(
            CASE
                WHEN completed_at IS NOT NULL THEN EXTRACT(EPOCH FROM (completed_at - started_at))
                WHEN failed_at IS NOT NULL THEN EXTRACT(EPOCH FROM (failed_at - started_at))
                ELSE NULL
            END
        ) as avg_duration_seconds,
        COUNT(*) FILTER (WHERE stitched_video IS NOT NULL) as total_videos_generated,
        COALESCE(SUM(published_count), 0) as total_posts_published,
        COALESCE(SUM(tweets_scheduled), 0) as total_tweets_scheduled
    FROM orchestrator_pipelines
    WHERE started_at >= NOW() - INTERVAL '1 day' * days;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE orchestrator_pipelines IS 'ARCH-001: Master orchestrator pipeline execution tracking';
COMMENT ON TABLE orchestrator_pipeline_steps IS 'ARCH-001: Individual pipeline step tracking for monitoring and debugging';
COMMENT ON FUNCTION get_pipeline_summary(VARCHAR) IS 'ARCH-001: Get comprehensive summary of a pipeline execution';
COMMENT ON FUNCTION get_pipeline_metrics(INTEGER) IS 'ARCH-001: Get aggregated pipeline performance metrics';
