-- Create agent_events table (AC-005)
-- Append-only event timeline for debugging and observability

CREATE TYPE agent_event_type AS ENUM (
    'started',
    'step',
    'action',
    'decision',
    'error',
    'completed',
    'failed',
    'paused',
    'resumed'
);

CREATE TYPE agent_event_status AS ENUM (
    'pending',
    'running',
    'success',
    'failed',
    'skipped'
);

CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    run_id UUID NOT NULL,
    event_type agent_event_type NOT NULL,
    status agent_event_status NOT NULL DEFAULT 'success',
    step INTEGER NOT NULL DEFAULT 0,
    topic VARCHAR(255),
    message TEXT NOT NULL,
    details JSONB,
    error TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_agent_events_agent_id ON agent_events(agent_id);
CREATE INDEX idx_agent_events_run_id ON agent_events(run_id);
CREATE INDEX idx_agent_events_agent_run ON agent_events(agent_id, run_id);
CREATE INDEX idx_agent_events_topic ON agent_events(topic);
CREATE INDEX idx_agent_events_step ON agent_events(step);
CREATE INDEX idx_agent_events_created_at ON agent_events(created_at);

-- Add comment
COMMENT ON TABLE agent_events IS 'Append-only event log for agent operations (AC-005)';
