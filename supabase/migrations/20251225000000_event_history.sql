-- Event History Table for Pub/Sub System
-- Stores all events for debugging, replay, and analytics

CREATE TABLE IF NOT EXISTS event_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(255) NOT NULL,  -- Original event ID from EventBus
    topic VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,
    correlation_id VARCHAR(255),
    payload JSONB NOT NULL DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_event_history_topic ON event_history(topic);
CREATE INDEX IF NOT EXISTS idx_event_history_timestamp ON event_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_event_history_correlation_id ON event_history(correlation_id);
CREATE INDEX IF NOT EXISTS idx_event_history_source ON event_history(source);
CREATE INDEX IF NOT EXISTS idx_event_history_topic_timestamp ON event_history(topic, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_event_history_event_id ON event_history(event_id);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_event_history_correlation_timestamp ON event_history(correlation_id, timestamp DESC);

-- Function to clean up old events (keep last 30 days by default)
CREATE OR REPLACE FUNCTION cleanup_old_event_history(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM event_history 
    WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- View for recent events by topic
CREATE OR REPLACE VIEW v_recent_events_by_topic AS
SELECT 
    topic,
    COUNT(*) as event_count,
    MAX(timestamp) as last_event_at,
    MIN(timestamp) as first_event_at
FROM event_history
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY topic
ORDER BY event_count DESC;

-- View for event statistics
CREATE OR REPLACE VIEW v_event_statistics AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    topic,
    COUNT(*) as event_count,
    COUNT(DISTINCT correlation_id) as unique_workflows,
    COUNT(DISTINCT source) as unique_sources
FROM event_history
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', timestamp), topic
ORDER BY hour DESC, event_count DESC;

COMMENT ON TABLE event_history IS 'Stores all pub/sub events for debugging, replay, and analytics';
COMMENT ON COLUMN event_history.event_id IS 'Original event ID from EventBus (for deduplication)';
COMMENT ON COLUMN event_history.topic IS 'Event topic (e.g., media.analysis.completed)';
COMMENT ON COLUMN event_history.correlation_id IS 'Links related events in a workflow';
COMMENT ON COLUMN event_history.payload IS 'Event-specific data';
COMMENT ON COLUMN event_history.metadata IS 'Tracing, retry info, etc.';

