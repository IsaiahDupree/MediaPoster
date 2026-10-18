-- Agent Events Table for Pub/Sub Framework
-- Stores events from AI agents for timeline display

CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_agent_events_agent_type ON agent_events(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_events_event_type ON agent_events(event_type);
CREATE INDEX IF NOT EXISTS idx_agent_events_created_at ON agent_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_agent_created ON agent_events(agent_type, created_at DESC);

-- Clean up old events (keep last 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_agent_events()
RETURNS void AS $$
BEGIN
    DELETE FROM agent_events WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE agent_events IS 'Stores events from AI agents for monitoring and timeline display';
COMMENT ON COLUMN agent_events.agent_type IS 'Type of agent: narrative_planner, experiment_runner, etc';
COMMENT ON COLUMN agent_events.event_type IS 'Type of event: thought, action, milestone, etc';
