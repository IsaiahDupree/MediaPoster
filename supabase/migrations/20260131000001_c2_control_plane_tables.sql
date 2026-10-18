-- Command & Control (C2) Tables for MediaPoster
-- Migration: 20260131000001_c2_control_plane_tables.sql
-- Description: Tables for Control Plane API job tracking and event storage

-- C2 Jobs Table
-- Tracks all commands submitted via the Control Plane API
CREATE TABLE IF NOT EXISTS c2_jobs (
    job_id UUID PRIMARY KEY,
    command_id VARCHAR(100) NOT NULL,
    correlation_id UUID,
    command VARCHAR(100) NOT NULL,
    args JSONB DEFAULT '{}',
    state VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    stage VARCHAR(100),
    percent INTEGER DEFAULT 0,
    result JSONB,
    error_code VARCHAR(50),
    error_message TEXT,
    idempotency_key VARCHAR(255),
    priority VARCHAR(20) DEFAULT 'normal',
    timeout_s INTEGER DEFAULT 3600,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_c2_jobs_state ON c2_jobs(state);
CREATE INDEX IF NOT EXISTS idx_c2_jobs_command ON c2_jobs(command);
CREATE INDEX IF NOT EXISTS idx_c2_jobs_correlation_id ON c2_jobs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_c2_jobs_created_at ON c2_jobs(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_c2_jobs_idempotency ON c2_jobs(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- C2 Job Events Table
-- Stores events emitted during job execution
CREATE TABLE IF NOT EXISTS c2_job_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES c2_jobs(job_id) ON DELETE CASCADE,
    correlation_id UUID,
    type VARCHAR(50) NOT NULL,
    stage VARCHAR(100),
    percent INTEGER,
    message TEXT,
    data JSONB DEFAULT '{}',
    cursor VARCHAR(100),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stored_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_c2_job_events_job_id ON c2_job_events(job_id);
CREATE INDEX IF NOT EXISTS idx_c2_job_events_type ON c2_job_events(type);
CREATE INDEX IF NOT EXISTS idx_c2_job_events_cursor ON c2_job_events(cursor);
CREATE INDEX IF NOT EXISTS idx_c2_job_events_timestamp ON c2_job_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_c2_job_events_correlation_id ON c2_job_events(correlation_id);

-- Add updated_at trigger
DROP TRIGGER IF EXISTS update_c2_jobs_updated_at ON c2_jobs;
CREATE TRIGGER update_c2_jobs_updated_at 
    BEFORE UPDATE ON c2_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views

-- Active Jobs View
CREATE OR REPLACE VIEW c2_active_jobs AS
SELECT 
    job_id,
    command_id,
    command,
    state,
    stage,
    percent,
    priority,
    created_at,
    started_at,
    EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER as running_seconds
FROM c2_jobs
WHERE state IN ('QUEUED', 'RUNNING')
ORDER BY 
    CASE priority 
        WHEN 'high' THEN 1 
        WHEN 'normal' THEN 2 
        WHEN 'low' THEN 3 
    END,
    created_at;

-- Job Performance Summary
CREATE OR REPLACE VIEW c2_job_performance AS
SELECT 
    command,
    state,
    COUNT(*) as total_jobs,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))::INTEGER as avg_duration_s,
    COUNT(CASE WHEN state = 'SUCCEEDED' THEN 1 END) as succeeded,
    COUNT(CASE WHEN state = 'FAILED' THEN 1 END) as failed,
    COUNT(CASE WHEN state = 'CANCELLED' THEN 1 END) as cancelled
FROM c2_jobs
WHERE started_at IS NOT NULL
GROUP BY command, state
ORDER BY total_jobs DESC;

-- Recent Errors View
CREATE OR REPLACE VIEW c2_recent_errors AS
SELECT 
    job_id,
    command,
    error_code,
    error_message,
    completed_at
FROM c2_jobs
WHERE state = 'FAILED'
ORDER BY completed_at DESC
LIMIT 100;

-- Comments
COMMENT ON TABLE c2_jobs IS 'Jobs submitted via Control Plane API (port 9100)';
COMMENT ON TABLE c2_job_events IS 'Events emitted during job execution';
COMMENT ON VIEW c2_active_jobs IS 'Currently active (queued or running) jobs';
COMMENT ON VIEW c2_job_performance IS 'Job execution performance metrics';
COMMENT ON VIEW c2_recent_errors IS 'Recent job failures for debugging';
