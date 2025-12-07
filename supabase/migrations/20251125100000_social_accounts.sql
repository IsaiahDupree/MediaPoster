-- Social Accounts Table
-- Core table for tracking connected social media accounts

CREATE TABLE IF NOT EXISTS social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Account Info
    platform VARCHAR(50) NOT NULL CHECK (platform IN (
        'tiktok', 'instagram', 'youtube', 'twitter', 'facebook',
        'pinterest', 'bluesky', 'threads', 'linkedin'
    )),
    handle VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    profile_url TEXT,
    avatar_url TEXT,
    
    -- Account Status
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN (
        'active', 'inactive', 'pending', 'error', 'disconnected'
    )),
    
    -- OAuth/Connection Info
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    external_id VARCHAR(255),
    
    -- Ownership
    user_id UUID,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Timestamps
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, handle)
);

CREATE INDEX IF NOT EXISTS idx_social_accounts_platform ON social_accounts(platform);
CREATE INDEX IF NOT EXISTS idx_social_accounts_user ON social_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_workspace ON social_accounts(workspace_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_status ON social_accounts(status);

-- Enable RLS
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE social_accounts IS 'Connected social media accounts for analytics and publishing';
