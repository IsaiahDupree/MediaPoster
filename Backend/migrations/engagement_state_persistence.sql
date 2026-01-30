-- Migration: Engagement State Persistence
-- Created: 2026-01-30
-- Description: Store engagement controller state for survival across uvicorn reloads

-- =============================================================================
-- ENGAGEMENT STATE - Singleton state persistence
-- =============================================================================
CREATE TABLE IF NOT EXISTS engagement_state (
    id TEXT PRIMARY KEY DEFAULT 'singleton',
    
    -- Controller state
    state TEXT NOT NULL DEFAULT 'stopped',  -- running, stopped, paused, idle_waiting
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    
    -- Platform states (JSONB for flexibility)
    platforms JSONB DEFAULT '{
        "threads": {"is_enabled": true, "comments_this_hour": 0, "comments_today": 0},
        "instagram": {"is_enabled": true, "comments_this_hour": 0, "comments_today": 0},
        "tiktok": {"is_enabled": true, "comments_this_hour": 0, "comments_today": 0},
        "twitter": {"is_enabled": true, "comments_this_hour": 0, "comments_today": 0}
    }'::jsonb,
    
    -- Configuration
    auto_resume_enabled BOOLEAN DEFAULT true,
    auto_resume_hours FLOAT DEFAULT 0.25,
    comments_per_hour INTEGER DEFAULT 30,
    
    -- Metadata
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_state CHECK (state IN ('stopped', 'running', 'paused', 'idle_waiting'))
);

-- Create initial singleton row if not exists
INSERT INTO engagement_state (id, state) 
VALUES ('singleton', 'stopped')
ON CONFLICT (id) DO NOTHING;

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_engagement_state_updated ON engagement_state(updated_at DESC);

-- Grant permissions
GRANT ALL ON engagement_state TO authenticated;
GRANT ALL ON engagement_state TO anon;
