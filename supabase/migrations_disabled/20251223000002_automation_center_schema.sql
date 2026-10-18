-- Automation Center Schema
-- Universal run layer for Narrative Builder + Experiments Scheduler

-- =============================================================================
-- AGENT SCHEDULES - Scheduled tasks for agents
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,
    agent_type VARCHAR(50) NOT NULL, -- 'narrative' | 'experiments'
    topic VARCHAR(100) NOT NULL,     -- e.g. narrative.weekly.generate_plan
    schedule_name VARCHAR(100) NOT NULL,
    cron_expr VARCHAR(50),
    interval_seconds INTEGER,
    enabled BOOLEAN DEFAULT TRUE,
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    config_json JSONB DEFAULT '{}',  -- goal_id, experiment_id, account_ids
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_schedules_agent_type ON agent_schedules(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_enabled ON agent_schedules(enabled, next_run_at);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_topic ON agent_schedules(topic);

-- =============================================================================
-- AGENT RUNS - Individual execution runs
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,
    agent_type VARCHAR(50) NOT NULL,
    schedule_id UUID REFERENCES agent_schedules(id),
    status VARCHAR(20) DEFAULT 'queued', -- queued|running|succeeded|failed|canceled|paused
    progress_current INTEGER DEFAULT 0,
    progress_total INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    last_heartbeat_at TIMESTAMPTZ,
    root_context_json JSONB DEFAULT '{}', -- goal_id/week range OR experiment/hypothesis ids
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_type ON agent_runs(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_schedule ON agent_runs(schedule_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created ON agent_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_status ON agent_runs(agent_type, status);

-- =============================================================================
-- AGENT STEPS - Steps within a run
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_key VARCHAR(50) NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    step_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- pending|running|completed|failed|skipped
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms INTEGER,
    summary TEXT,
    input_refs JSONB DEFAULT '[]',
    output_refs JSONB DEFAULT '[]',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_steps_status ON agent_steps(status);
CREATE INDEX IF NOT EXISTS idx_agent_steps_key ON agent_steps(step_key);

-- =============================================================================
-- AGENT EVENTS - Append-only timeline (enhanced from previous)
-- =============================================================================

-- Drop and recreate if needed to add new columns
ALTER TABLE agent_events ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE;
ALTER TABLE agent_events ADD COLUMN IF NOT EXISTS step_id UUID REFERENCES agent_steps(id);
ALTER TABLE agent_events ADD COLUMN IF NOT EXISTS ts TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE agent_events ADD COLUMN IF NOT EXISTS topic VARCHAR(100);
ALTER TABLE agent_events ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'info';
ALTER TABLE agent_events ADD COLUMN IF NOT EXISTS source_service VARCHAR(50);
ALTER TABLE agent_events ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE agent_events ADD COLUMN IF NOT EXISTS payload_json JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_agent_events_run ON agent_events(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_step ON agent_events(step_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_topic ON agent_events(topic);
CREATE INDEX IF NOT EXISTS idx_agent_events_ts ON agent_events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_run_ts ON agent_events(run_id, ts DESC);

-- =============================================================================
-- AGENT ARTIFACTS - Generated outputs from runs
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_id UUID REFERENCES agent_steps(id),
    kind VARCHAR(50) NOT NULL, -- schedule_json|rejection_log|reflection_report|winners_report|plan_json
    name VARCHAR(100),
    uri TEXT,                  -- Supabase storage path or DB ref
    content_json JSONB,        -- Inline JSON content
    metadata_json JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_artifacts_run ON agent_artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_artifacts_kind ON agent_artifacts(kind);

-- =============================================================================
-- VIEWS for easy querying
-- =============================================================================

CREATE OR REPLACE VIEW v_recent_runs AS
SELECT 
    r.id,
    r.agent_type,
    r.status,
    r.progress_current,
    r.progress_total,
    r.started_at,
    r.finished_at,
    r.created_at,
    s.schedule_name,
    s.topic,
    EXTRACT(EPOCH FROM (COALESCE(r.finished_at, NOW()) - r.started_at)) as duration_seconds,
    (SELECT COUNT(*) FROM agent_steps WHERE run_id = r.id) as step_count,
    (SELECT COUNT(*) FROM agent_steps WHERE run_id = r.id AND status = 'completed') as steps_completed,
    (SELECT message FROM agent_events WHERE run_id = r.id ORDER BY ts DESC LIMIT 1) as last_event
FROM agent_runs r
LEFT JOIN agent_schedules s ON r.schedule_id = s.id
ORDER BY r.created_at DESC;

CREATE OR REPLACE VIEW v_run_timeline AS
SELECT 
    e.id,
    e.run_id,
    e.step_id,
    s.step_name,
    e.ts,
    e.topic,
    e.event_type,
    e.severity,
    e.source_service,
    e.message,
    e.payload_json
FROM agent_events e
LEFT JOIN agent_steps s ON e.step_id = s.id
ORDER BY e.ts DESC;

-- =============================================================================
-- SEED DEFAULT SCHEDULES
-- =============================================================================

INSERT INTO agent_schedules (agent_type, topic, schedule_name, interval_seconds, enabled, next_run_at)
VALUES 
    ('narrative', 'narrative.weekly.generate_plan', 'Weekly Plan Generation', 604800, true, NOW() + INTERVAL '1 hour'),
    ('narrative', 'narrative.daily.execute_schedule', 'Daily Posting', 86400, true, NOW() + INTERVAL '30 minutes'),
    ('narrative', 'narrative.weekly.reflect', 'Weekly Reflection', 604800, true, NOW() + INTERVAL '7 days'),
    ('experiments', 'experiments.weekly.plan_experiments', 'Plan Experiments', 604800, true, NOW() + INTERVAL '2 hours'),
    ('experiments', 'experiments.daily.execute_variants', 'Execute Variants', 86400, true, NOW() + INTERVAL '1 hour'),
    ('experiments', 'experiments.daily.analyze_results', 'Analyze Results', 86400, true, NOW() + INTERVAL '6 hours')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE agent_schedules IS 'Scheduled tasks for AI agents (narrative/experiments)';
COMMENT ON TABLE agent_runs IS 'Individual execution runs of agent tasks';
COMMENT ON TABLE agent_steps IS 'Steps within a run, following step taxonomy';
COMMENT ON TABLE agent_events IS 'Append-only timeline of events during runs';
COMMENT ON TABLE agent_artifacts IS 'Generated outputs (JSON, reports, logs) from runs';
