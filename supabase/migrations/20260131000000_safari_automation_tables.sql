-- Safari Automation Tables for MediaPoster
-- Migration: 20260131000000_safari_automation_tables.sql
-- Description: Tables for storing Safari Automation commands, videos, events, and sessions

-- Safari Commands Table
-- Stores all commands sent to Safari Automation service (port 7070)
CREATE TABLE IF NOT EXISTS safari_commands (
    command_id UUID PRIMARY KEY,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    payload JSONB,
    result JSONB,
    target JSONB,
    error_message TEXT,
    idempotency_key VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_safari_commands_type ON safari_commands(type);
CREATE INDEX IF NOT EXISTS idx_safari_commands_status ON safari_commands(status);
CREATE INDEX IF NOT EXISTS idx_safari_commands_created_at ON safari_commands(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_safari_commands_idempotency ON safari_commands(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- Safari Videos Table
-- Catalog of Sora videos generated via Safari Automation
CREATE TABLE IF NOT EXISTS safari_videos (
    video_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command_id UUID REFERENCES safari_commands(command_id) ON DELETE SET NULL,
    prompt TEXT,
    character VARCHAR(100),
    duration VARCHAR(20),
    aspect_ratio VARCHAR(20),
    raw_path TEXT,
    raw_size_bytes BIGINT,
    cleaned_path TEXT,
    cleaned_size_bytes BIGINT,
    thumbnail_path TEXT,
    status VARCHAR(50) DEFAULT 'GENERATING',
    sora_draft_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_safari_videos_command ON safari_videos(command_id);
CREATE INDEX IF NOT EXISTS idx_safari_videos_status ON safari_videos(status);
CREATE INDEX IF NOT EXISTS idx_safari_videos_character ON safari_videos(character);
CREATE INDEX IF NOT EXISTS idx_safari_videos_created_at ON safari_videos(created_at DESC);

-- Watermark Removals Table
-- Tracks watermark removal operations
CREATE TABLE IF NOT EXISTS watermark_removals (
    removal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID REFERENCES safari_videos(video_id) ON DELETE SET NULL,
    command_id UUID REFERENCES safari_commands(command_id) ON DELETE SET NULL,
    input_path TEXT NOT NULL,
    output_path TEXT,
    input_size_bytes BIGINT,
    output_size_bytes BIGINT,
    method VARCHAR(50) DEFAULT 'lama',
    processing_time_ms INTEGER,
    success BOOLEAN DEFAULT false,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_watermark_removals_video ON watermark_removals(video_id);
CREATE INDEX IF NOT EXISTS idx_watermark_removals_command ON watermark_removals(command_id);
CREATE INDEX IF NOT EXISTS idx_watermark_removals_success ON watermark_removals(success);

-- Safari Events Table
-- Persists telemetry events from Safari Automation (port 7071)
CREATE TABLE IF NOT EXISTS safari_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command_id UUID REFERENCES safari_commands(command_id) ON DELETE CASCADE,
    correlation_id UUID,
    type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'info',
    payload JSONB,
    cursor VARCHAR(100),
    emitted_at TIMESTAMPTZ NOT NULL,
    stored_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_safari_events_command ON safari_events(command_id);
CREATE INDEX IF NOT EXISTS idx_safari_events_type ON safari_events(type);
CREATE INDEX IF NOT EXISTS idx_safari_events_cursor ON safari_events(cursor);
CREATE INDEX IF NOT EXISTS idx_safari_events_emitted_at ON safari_events(emitted_at DESC);

-- Safari Sessions Table
-- Tracks Safari browser sessions
CREATE TABLE IF NOT EXISTS safari_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform VARCHAR(50) NOT NULL,
    account_id UUID,
    status VARCHAR(50) DEFAULT 'active',
    browser_pid INTEGER,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_safari_sessions_platform ON safari_sessions(platform);
CREATE INDEX IF NOT EXISTS idx_safari_sessions_status ON safari_sessions(status);

-- Add updated_at triggers (using existing function from schema.sql)
DROP TRIGGER IF EXISTS update_safari_commands_updated_at ON safari_commands;
CREATE TRIGGER update_safari_commands_updated_at 
    BEFORE UPDATE ON safari_commands 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_safari_videos_updated_at ON safari_videos;
CREATE TRIGGER update_safari_videos_updated_at 
    BEFORE UPDATE ON safari_videos 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_safari_sessions_updated_at ON safari_sessions;
CREATE TRIGGER update_safari_sessions_updated_at 
    BEFORE UPDATE ON safari_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views

-- Watermark-Free Videos Summary
CREATE OR REPLACE VIEW watermark_free_videos AS
SELECT 
    v.video_id,
    v.prompt,
    v.character,
    v.duration,
    v.cleaned_path,
    v.cleaned_size_bytes,
    v.status,
    c.type as command_type,
    c.status as command_status,
    v.created_at
FROM safari_videos v
LEFT JOIN safari_commands c ON v.command_id = c.command_id
WHERE v.cleaned_path IS NOT NULL
ORDER BY v.created_at DESC;

-- Command Performance Summary
CREATE OR REPLACE VIEW safari_command_performance AS
SELECT 
    type,
    status,
    COUNT(*) as total_commands,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)::INTEGER as avg_duration_ms,
    COUNT(CASE WHEN status = 'SUCCEEDED' THEN 1 END) as succeeded,
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed
FROM safari_commands
WHERE started_at IS NOT NULL
GROUP BY type, status
ORDER BY total_commands DESC;

-- Comments
COMMENT ON TABLE safari_commands IS 'Commands sent to Safari Automation service (port 7070)';
COMMENT ON TABLE safari_videos IS 'Sora videos generated via Safari Automation';
COMMENT ON TABLE watermark_removals IS 'Watermark removal operations tracking';
COMMENT ON TABLE safari_events IS 'Telemetry events from Safari Automation (port 7071)';
COMMENT ON TABLE safari_sessions IS 'Safari browser session tracking';
COMMENT ON VIEW watermark_free_videos IS 'All videos with watermark removed';
COMMENT ON VIEW safari_command_performance IS 'Command execution performance metrics';
