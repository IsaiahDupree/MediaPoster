-- Migration: Create background_jobs table for unified job tracking
-- This replaces in-memory job tracking that was lost on server restart

CREATE TABLE IF NOT EXISTS background_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,  -- 'import', 'extraction', 'render', 'scrape', 'analysis'
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress NUMERIC(5,2) DEFAULT 0,  -- 0.00 to 100.00
    
    -- Input/Output
    input_json JSONB,  -- Job parameters
    output_json JSONB,  -- Job results
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Optional references
    user_id UUID,
    related_id UUID,  -- e.g., video_id, format_id
    related_type TEXT  -- e.g., 'video', 'format'
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_background_jobs_type ON background_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_background_jobs_status ON background_jobs(status);
CREATE INDEX IF NOT EXISTS idx_background_jobs_created ON background_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_background_jobs_type_status ON background_jobs(job_type, status);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_background_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_background_jobs_updated_at ON background_jobs;
CREATE TRIGGER trigger_background_jobs_updated_at
    BEFORE UPDATE ON background_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_background_jobs_updated_at();

-- Comment
COMMENT ON TABLE background_jobs IS 'Unified job tracking for import, extraction, render, and scrape operations. Replaces in-memory tracking.';
