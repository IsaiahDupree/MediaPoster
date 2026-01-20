-- Background Jobs Migration (JOBS-001)
-- Unified job tracking for import, extraction, render, and scrape operations
-- Date: 2026-01-20

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- BACKGROUND_JOBS TABLE
-- ============================================================================
-- Replaces in-memory job tracking with database persistence
-- Supports: import (Android/iOS), extraction, render, scrape, analysis

CREATE TABLE IF NOT EXISTS background_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Job identification
    job_type VARCHAR(50) NOT NULL, -- import, extraction, render, scrape, analysis
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed, cancelled

    -- Progress tracking
    progress NUMERIC(5, 2) DEFAULT 0, -- 0-100 percentage

    -- Job data
    input_json JSONB, -- Input parameters for the job
    output_json JSONB, -- Output data/results
    error_message TEXT, -- Error details if failed

    -- Related entity (optional)
    related_id UUID, -- e.g., video_id, media_id
    related_type VARCHAR(50), -- e.g., 'video', 'media'

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_background_jobs_job_type ON background_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_background_jobs_status ON background_jobs(status);
CREATE INDEX IF NOT EXISTS idx_background_jobs_created_at ON background_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_background_jobs_related ON background_jobs(related_id, related_type);
CREATE INDEX IF NOT EXISTS idx_background_jobs_status_type ON background_jobs(status, job_type);

-- Composite index for active jobs query
CREATE INDEX IF NOT EXISTS idx_background_jobs_active ON background_jobs(status, job_type, created_at DESC)
WHERE status IN ('pending', 'running');

-- ============================================================================
-- TRIGGER: Update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_background_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_background_jobs_updated_at
    BEFORE UPDATE ON background_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_background_jobs_updated_at();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE background_jobs IS 'Unified job tracking for async operations (JOBS-001)';
COMMENT ON COLUMN background_jobs.job_type IS 'Type: import, extraction, render, scrape, analysis';
COMMENT ON COLUMN background_jobs.status IS 'Status: pending, running, completed, failed, cancelled';
COMMENT ON COLUMN background_jobs.progress IS 'Progress percentage (0-100)';
COMMENT ON COLUMN background_jobs.input_json IS 'Input parameters/configuration for the job';
COMMENT ON COLUMN background_jobs.output_json IS 'Job results/output data';
COMMENT ON COLUMN background_jobs.related_id IS 'Optional reference to related entity (video, media, etc)';
COMMENT ON COLUMN background_jobs.related_type IS 'Type of related entity';
