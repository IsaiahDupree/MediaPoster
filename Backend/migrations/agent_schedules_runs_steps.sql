-- ============================================================================
-- AGENT SCHEDULES, RUNS, AND STEPS SCHEMA
-- Automation Center: Agent scheduling, run tracking, and step timeline
-- Features: AC-002, AC-003, AC-004
-- Date: 2026-01-21
-- ============================================================================

-- ============================================================================
-- AC-002: Agent Schedules System
-- Schedule agent runs with cron/interval, enable/disable
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,

    -- Agent configuration
    agent_type VARCHAR(100) NOT NULL, -- 'narrative', 'experiments', 'content_mix', 'weekly_planner', etc.
    topic VARCHAR(255), -- Optional topic/context for the agent
    schedule_name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Scheduling
    interval_seconds INTEGER, -- Run every N seconds (e.g., 3600 = hourly)
    cron_expression VARCHAR(100), -- Cron expression (e.g., '0 9 * * *' = daily at 9am)

    -- Execution times
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(50), -- 'success', 'failed', 'timeout'
    last_run_id UUID,

    -- Status
    enabled BOOLEAN DEFAULT true,

    -- Configuration (agent-specific settings)
    config_json JSONB DEFAULT '{}'::jsonb,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),

    -- Constraints
    CHECK (interval_seconds IS NOT NULL OR cron_expression IS NOT NULL)
);

-- Indexes for schedule lookups
CREATE INDEX IF NOT EXISTS idx_agent_schedules_workspace ON agent_schedules(workspace_id);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_agent_type ON agent_schedules(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_enabled ON agent_schedules(enabled) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_agent_schedules_next_run ON agent_schedules(next_run_at)
WHERE enabled = true AND next_run_at IS NOT NULL;

COMMENT ON TABLE agent_schedules IS 'AC-002: Scheduled agent runs with cron/interval';
COMMENT ON COLUMN agent_schedules.interval_seconds IS 'Run every N seconds (simple interval)';
COMMENT ON COLUMN agent_schedules.cron_expression IS 'Cron expression for complex schedules';
COMMENT ON COLUMN agent_schedules.config_json IS 'Agent-specific configuration (e.g., budgets, parameters)';


-- ============================================================================
-- AC-003: Agent Runs Tracking
-- Track runs with status, progress, heartbeat, artifacts
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES agent_schedules(id) ON DELETE SET NULL,
    workspace_id UUID,

    -- Run identification
    agent_type VARCHAR(100) NOT NULL,
    run_name VARCHAR(255),
    run_number INTEGER, -- Sequential run number for this schedule

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'queued', -- 'queued', 'running', 'success', 'failed', 'timeout', 'cancelled'
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    progress_message TEXT,

    -- Timing
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,

    -- Heartbeat (for detecting stuck runs)
    last_heartbeat_at TIMESTAMPTZ,
    heartbeat_interval_seconds INTEGER DEFAULT 30,

    -- Results
    result_summary TEXT,
    result_data JSONB,
    error_message TEXT,
    error_stack TEXT,

    -- Artifacts (files, reports, etc.)
    artifacts JSONB DEFAULT '[]'::jsonb, -- Array of {name, type, url, size}

    -- Resource usage
    api_calls_made INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,4) DEFAULT 0.0,

    -- Configuration (snapshot of config at run time)
    config_snapshot JSONB,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    triggered_by VARCHAR(100) DEFAULT 'schedule' -- 'schedule', 'manual', 'api', 'event'
);

-- Indexes for run queries
CREATE INDEX IF NOT EXISTS idx_agent_runs_schedule ON agent_runs(schedule_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_workspace ON agent_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_type ON agent_runs(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_queued_at ON agent_runs(queued_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at ON agent_runs(started_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_agent_runs_running ON agent_runs(status, last_heartbeat_at)
WHERE status = 'running';

COMMENT ON TABLE agent_runs IS 'AC-003: Agent run tracking with status, progress, and heartbeat';
COMMENT ON COLUMN agent_runs.progress_percent IS 'Completion percentage (0-100)';
COMMENT ON COLUMN agent_runs.last_heartbeat_at IS 'Last time agent reported it is still alive';
COMMENT ON COLUMN agent_runs.artifacts IS 'Generated files/reports (JSON array)';
COMMENT ON COLUMN agent_runs.config_snapshot IS 'Configuration at time of run (for reproducibility)';


-- ============================================================================
-- AC-004: Agent Steps Timeline
-- Step-by-step tracking with status, duration, summary
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,

    -- Step identification
    step_number INTEGER NOT NULL, -- Sequential order within run
    step_name VARCHAR(255) NOT NULL,
    step_type VARCHAR(100), -- 'analysis', 'generation', 'api_call', 'decision', 'validation', etc.

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'success', 'failed', 'skipped'

    -- Content
    description TEXT,
    input_data JSONB,
    output_data JSONB,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Results
    summary TEXT,
    error_message TEXT,

    -- Resource usage (for this step)
    api_calls_made INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(run_id, step_number)
);

-- Indexes for step queries
CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps(run_id, step_number);
CREATE INDEX IF NOT EXISTS idx_agent_steps_status ON agent_steps(status);
CREATE INDEX IF NOT EXISTS idx_agent_steps_started_at ON agent_steps(started_at DESC NULLS LAST);

COMMENT ON TABLE agent_steps IS 'AC-004: Step-by-step execution timeline for agent runs';
COMMENT ON COLUMN agent_steps.step_number IS 'Sequential order within run (1, 2, 3, ...)';
COMMENT ON COLUMN agent_steps.duration_ms IS 'Step execution time in milliseconds';
COMMENT ON COLUMN agent_steps.summary IS 'Human-readable summary of what this step did';


-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

-- Active schedules (enabled and have next run time)
CREATE OR REPLACE VIEW active_agent_schedules AS
SELECT
    s.id,
    s.workspace_id,
    s.agent_type,
    s.schedule_name,
    s.interval_seconds,
    s.cron_expression,
    s.next_run_at,
    s.last_run_at,
    s.last_run_status,
    s.config_json,
    EXTRACT(EPOCH FROM (s.next_run_at - NOW())) as seconds_until_next_run,
    (SELECT COUNT(*) FROM agent_runs WHERE schedule_id = s.id) as total_runs,
    (SELECT COUNT(*) FROM agent_runs WHERE schedule_id = s.id AND status = 'success') as successful_runs,
    (SELECT COUNT(*) FROM agent_runs WHERE schedule_id = s.id AND status = 'failed') as failed_runs
FROM agent_schedules s
WHERE s.enabled = true
ORDER BY s.next_run_at ASC NULLS LAST;

-- Recent runs (last 100)
CREATE OR REPLACE VIEW recent_agent_runs AS
SELECT
    r.id,
    r.agent_type,
    r.run_name,
    r.status,
    r.progress_percent,
    r.progress_message,
    r.queued_at,
    r.started_at,
    r.completed_at,
    r.duration_seconds,
    r.result_summary,
    r.error_message,
    r.api_calls_made,
    r.tokens_used,
    r.cost_usd,
    s.schedule_name,
    (SELECT COUNT(*) FROM agent_steps WHERE run_id = r.id) as total_steps,
    (SELECT COUNT(*) FROM agent_steps WHERE run_id = r.id AND status = 'success') as completed_steps,
    (SELECT COUNT(*) FROM agent_steps WHERE run_id = r.id AND status = 'failed') as failed_steps
FROM agent_runs r
LEFT JOIN agent_schedules s ON r.schedule_id = s.id
ORDER BY r.queued_at DESC
LIMIT 100;

-- Stuck runs (running but no heartbeat in 5+ minutes)
CREATE OR REPLACE VIEW stuck_agent_runs AS
SELECT
    r.id,
    r.agent_type,
    r.run_name,
    r.started_at,
    r.last_heartbeat_at,
    EXTRACT(EPOCH FROM (NOW() - r.last_heartbeat_at)) / 60 as minutes_since_heartbeat,
    r.progress_percent,
    r.progress_message
FROM agent_runs r
WHERE r.status = 'running'
AND (
    r.last_heartbeat_at IS NULL
    OR r.last_heartbeat_at < NOW() - INTERVAL '5 minutes'
)
ORDER BY r.started_at ASC;


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Calculate next run time based on interval
CREATE OR REPLACE FUNCTION calculate_next_run_interval(
    p_interval_seconds INTEGER,
    p_last_run_at TIMESTAMPTZ DEFAULT NULL
) RETURNS TIMESTAMPTZ AS $$
BEGIN
    IF p_last_run_at IS NULL THEN
        RETURN NOW() + (p_interval_seconds || ' seconds')::INTERVAL;
    ELSE
        RETURN p_last_run_at + (p_interval_seconds || ' seconds')::INTERVAL;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Update schedule's next run time after a run completes
CREATE OR REPLACE FUNCTION update_schedule_next_run()
RETURNS TRIGGER AS $$
DECLARE
    schedule_rec RECORD;
BEGIN
    -- Only update when run completes (status changes to success/failed/timeout)
    IF NEW.status IN ('success', 'failed', 'timeout') AND
       OLD.status = 'running' THEN

        -- Get the schedule
        SELECT * INTO schedule_rec FROM agent_schedules WHERE id = NEW.schedule_id;

        IF FOUND AND schedule_rec.enabled THEN
            -- Update last run info
            UPDATE agent_schedules
            SET
                last_run_at = NEW.completed_at,
                last_run_status = NEW.status,
                last_run_id = NEW.id,
                -- Calculate next run based on interval (cron would need external scheduler)
                next_run_at = CASE
                    WHEN schedule_rec.interval_seconds IS NOT NULL
                    THEN calculate_next_run_interval(schedule_rec.interval_seconds, NEW.completed_at)
                    ELSE next_run_at -- Keep existing for cron schedules
                END,
                updated_at = NOW()
            WHERE id = NEW.schedule_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update schedule after run
DROP TRIGGER IF EXISTS trigger_update_schedule_next_run ON agent_runs;
CREATE TRIGGER trigger_update_schedule_next_run
    AFTER UPDATE ON agent_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_schedule_next_run();

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables
DROP TRIGGER IF EXISTS trigger_agent_schedules_updated_at ON agent_schedules;
CREATE TRIGGER trigger_agent_schedules_updated_at
    BEFORE UPDATE ON agent_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

DROP TRIGGER IF EXISTS trigger_agent_runs_updated_at ON agent_runs;
CREATE TRIGGER trigger_agent_runs_updated_at
    BEFORE UPDATE ON agent_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

DROP TRIGGER IF EXISTS trigger_agent_steps_updated_at ON agent_steps;
CREATE TRIGGER trigger_agent_steps_updated_at
    BEFORE UPDATE ON agent_steps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();


-- ============================================================================
-- SEED DATA (Example schedules)
-- ============================================================================

-- Insert example schedules (optional)
INSERT INTO agent_schedules (agent_type, schedule_name, description, interval_seconds, enabled, config_json)
VALUES
    ('narrative', 'Daily Narrative Cycle', 'Run narrative goals executor every 24 hours', 86400, false, '{"budget_per_run": 5.0}'::jsonb),
    ('experiments', 'Hourly Experiment Check', 'Check experiment results every hour', 3600, false, '{"min_sample_size": 30}'::jsonb),
    ('content_mix', 'Weekly Content Planning', 'Plan content mix every Monday at 9am', 604800, false, '{"days_ahead": 7}'::jsonb)
ON CONFLICT DO NOTHING;


-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ Agent Schedules, Runs, and Steps Schema Created Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE '📊 New Tables:';
    RAISE NOTICE '   - agent_schedules (AC-002: Schedule agent runs)';
    RAISE NOTICE '   - agent_runs (AC-003: Track run status and progress)';
    RAISE NOTICE '   - agent_steps (AC-004: Step-by-step timeline)';
    RAISE NOTICE '';
    RAISE NOTICE '📈 Views:';
    RAISE NOTICE '   - active_agent_schedules (enabled schedules)';
    RAISE NOTICE '   - recent_agent_runs (last 100 runs)';
    RAISE NOTICE '   - stuck_agent_runs (detect stuck/zombie runs)';
    RAISE NOTICE '';
    RAISE NOTICE '⚙️ Functions:';
    RAISE NOTICE '   - calculate_next_run_interval()';
    RAISE NOTICE '   - update_schedule_next_run() [trigger]';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 Ready for Automation Center!';
END $$;
