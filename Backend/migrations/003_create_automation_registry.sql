-- Migration: BM-007 Automation Registry
-- Database table and API for tracking all automations, their status, schedule, and resource needs

CREATE TABLE IF NOT EXISTS automations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    automation_type TEXT NOT NULL, -- 'post_scheduler', 'safari_automation', 'metrics_fetcher', 'worker', 'custom'
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'paused', 'disabled', 'error'

    -- Scheduling
    schedule_type TEXT, -- 'cron', 'interval', 'one_time', 'event_driven', null
    schedule_config JSONB, -- { cron: "0 * * * *", interval_seconds: 3600, event: "post.published" }
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    last_run_status TEXT, -- 'success', 'failure', 'timeout'
    last_run_error TEXT,

    -- Resource Management
    resource_requirements JSONB, -- { cpu: 'low', memory: 'medium', requires_safari: true }
    estimated_duration_seconds INTEGER,
    priority INTEGER DEFAULT 5, -- 1-10, higher = more important
    max_concurrent_runs INTEGER DEFAULT 1,
    current_runs INTEGER DEFAULT 0,

    -- Configuration
    config JSONB, -- Automation-specific configuration
    enabled BOOLEAN DEFAULT true,

    -- Metrics
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    average_duration_seconds FLOAT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    tags TEXT[]
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_automations_status ON automations(status);
CREATE INDEX IF NOT EXISTS idx_automations_type ON automations(automation_type);
CREATE INDEX IF NOT EXISTS idx_automations_next_run ON automations(next_run_at) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_automations_tags ON automations USING gin(tags);

-- Automation run history
CREATE TABLE IF NOT EXISTS automation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,

    -- Execution details
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds FLOAT,
    status TEXT NOT NULL, -- 'running', 'success', 'failure', 'timeout', 'cancelled'
    error_message TEXT,

    -- Resource usage
    cpu_usage_percent FLOAT,
    memory_usage_mb FLOAT,

    -- Results
    result_data JSONB, -- Automation-specific result data
    logs TEXT,

    -- Context
    triggered_by TEXT, -- 'schedule', 'manual', 'event', 'system'
    trigger_metadata JSONB
);

-- Indexes for run history
CREATE INDEX IF NOT EXISTS idx_automation_runs_automation ON automation_runs(automation_id);
CREATE INDEX IF NOT EXISTS idx_automation_runs_started ON automation_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_status ON automation_runs(status);

-- Function to update automation metrics after run
CREATE OR REPLACE FUNCTION update_automation_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update when run completes
    IF NEW.status IN ('success', 'failure') AND OLD.status = 'running' THEN
        UPDATE automations
        SET
            total_runs = total_runs + 1,
            successful_runs = successful_runs + CASE WHEN NEW.status = 'success' THEN 1 ELSE 0 END,
            failed_runs = failed_runs + CASE WHEN NEW.status = 'failure' THEN 1 ELSE 0 END,
            last_run_at = NEW.completed_at,
            last_run_status = NEW.status,
            last_run_error = NEW.error_message,
            average_duration_seconds = (
                COALESCE(average_duration_seconds * total_runs, 0) + COALESCE(NEW.duration_seconds, 0)
            ) / (total_runs + 1),
            current_runs = GREATEST(0, current_runs - 1),
            updated_at = NOW()
        WHERE id = NEW.automation_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update metrics
DROP TRIGGER IF EXISTS trigger_update_automation_metrics ON automation_runs;
CREATE TRIGGER trigger_update_automation_metrics
    AFTER UPDATE ON automation_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_automation_metrics();

-- Function to increment current_runs when starting
CREATE OR REPLACE FUNCTION increment_current_runs()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'running' THEN
        UPDATE automations
        SET current_runs = current_runs + 1
        WHERE id = NEW.automation_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to increment current runs
DROP TRIGGER IF EXISTS trigger_increment_current_runs ON automation_runs;
CREATE TRIGGER trigger_increment_current_runs
    AFTER INSERT ON automation_runs
    FOR EACH ROW
    EXECUTE FUNCTION increment_current_runs();

-- Comments
COMMENT ON TABLE automations IS 'BM-007: Registry of all system automations with scheduling and resource tracking';
COMMENT ON TABLE automation_runs IS 'BM-007: Execution history and metrics for automation runs';
COMMENT ON COLUMN automations.resource_requirements IS 'Expected resource needs: cpu (low/medium/high), memory (low/medium/high), requires_safari, requires_gpu';
COMMENT ON COLUMN automations.schedule_config IS 'Schedule configuration based on schedule_type: cron string, interval in seconds, or event name';
