-- Platform Connectors Configuration
-- Migration: 003_connectors
-- Created: 2025-01-21

-- =====================================================
-- IG_CONNECTIONS: Instagram/Meta OAuth tokens
-- =====================================================

CREATE TABLE IF NOT EXISTS ig_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  everreach_user_id UUID NOT NULL,
  fb_page_id TEXT NOT NULL,
  ig_business_id TEXT NOT NULL,
  access_token TEXT NOT NULL,
  token_expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_synced_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ig_conn_user ON ig_connections(everreach_user_id);
CREATE INDEX IF NOT EXISTS idx_ig_conn_expires ON ig_connections(token_expires_at);

-- =====================================================
-- CONNECTOR_CONFIGS: Generic connector configuration
-- =====================================================

CREATE TABLE IF NOT EXISTS connector_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  connector_type TEXT NOT NULL CHECK (connector_type IN (
    'meta','youtube','tiktok','blotato','linkedin','twitter',
    'pinterest','threads','bluesky','rapidapi','esp'
  )),
  config JSONB NOT NULL,
  is_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, connector_type)
);

CREATE INDEX IF NOT EXISTS idx_connector_user ON connector_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_connector_type ON connector_configs(connector_type);
CREATE INDEX IF NOT EXISTS idx_connector_enabled ON connector_configs(is_enabled) WHERE is_enabled = TRUE;

-- =====================================================
-- Enable RLS
-- =====================================================

ALTER TABLE ig_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_configs ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- Comments
-- =====================================================

COMMENT ON TABLE ig_connections IS 'Instagram/Meta OAuth connection tokens';
COMMENT ON TABLE connector_configs IS 'Generic connector configuration store for all platforms';
COMMENT ON COLUMN connector_configs.config IS 'JSONB containing API keys, OAuth tokens, and connector-specific settings';
