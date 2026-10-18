-- Safari Session Manager
-- Database schema for managing Safari automation sessions across platforms
-- SSM-002: Safari Accounts Table
-- SSM-003: Session Logs Table

-- Safari Accounts Table (SSM-002)
-- Multi-account registry for Safari-automated platforms
CREATE TABLE IF NOT EXISTS safari_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,

    -- Platform identification
    platform VARCHAR(20) NOT NULL,
    username VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),

    -- Session state
    is_active BOOLEAN DEFAULT false,
    is_logged_in BOOLEAN DEFAULT false,
    last_login TIMESTAMPTZ,
    last_check TIMESTAMPTZ,
    last_refresh TIMESTAMPTZ,

    -- Session data (cookies/tokens - encrypted)
    session_data_encrypted TEXT,

    -- Configuration
    refresh_interval_minutes INTEGER DEFAULT 30,
    auto_refresh BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,

    -- Metadata
    notes TEXT,
    tags TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, platform, username)
);

-- Safari Session Logs Table (SSM-003)
-- Comprehensive log of all session events for debugging and analytics
CREATE TABLE IF NOT EXISTS safari_session_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES safari_accounts(id) ON DELETE CASCADE,

    -- Event details
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(20),
    details JSONB,
    error_message TEXT,

    -- Context
    duration_ms INTEGER,
    indicator_found TEXT,
    url TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_safari_accounts_platform ON safari_accounts(platform, is_active);
CREATE INDEX IF NOT EXISTS idx_safari_accounts_user ON safari_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_safari_accounts_login_status ON safari_accounts(is_logged_in, last_check);
CREATE INDEX IF NOT EXISTS idx_safari_session_logs_account ON safari_session_logs(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_safari_session_logs_event_type ON safari_session_logs(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_safari_session_logs_status ON safari_session_logs(status, created_at DESC);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_safari_accounts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER safari_accounts_updated_at
    BEFORE UPDATE ON safari_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_safari_accounts_updated_at();

-- Comments for documentation
COMMENT ON TABLE safari_accounts IS 'Safari automation account registry - tracks login sessions across platforms';
COMMENT ON TABLE safari_session_logs IS 'Log of all Safari session events (logins, refreshes, errors)';

COMMENT ON COLUMN safari_accounts.platform IS 'Platform name: twitter, tiktok, instagram, sora, youtube, threads, reddit';
COMMENT ON COLUMN safari_accounts.is_active IS 'Whether this account is actively being used for automation';
COMMENT ON COLUMN safari_accounts.is_logged_in IS 'Current login status based on last check';
COMMENT ON COLUMN safari_accounts.last_check IS 'Last time login status was verified';
COMMENT ON COLUMN safari_accounts.last_refresh IS 'Last time session was refreshed to prevent timeout';
COMMENT ON COLUMN safari_accounts.refresh_interval_minutes IS 'How often to refresh this session (minutes)';
COMMENT ON COLUMN safari_accounts.auto_refresh IS 'Whether to automatically refresh this session';
COMMENT ON COLUMN safari_accounts.priority IS 'Priority level (higher = more important, checked first)';

COMMENT ON COLUMN safari_session_logs.event_type IS 'Event type: login_check, session_refresh, login_success, login_failed, session_expired, etc.';
COMMENT ON COLUMN safari_session_logs.status IS 'Event status: success, failed, warning, info';
COMMENT ON COLUMN safari_session_logs.details IS 'Additional event details as JSON';
COMMENT ON COLUMN safari_session_logs.duration_ms IS 'Time taken for the operation (milliseconds)';
COMMENT ON COLUMN safari_session_logs.indicator_found IS 'CSS selector or indicator that was found';
