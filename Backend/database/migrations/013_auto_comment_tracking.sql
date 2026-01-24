-- Migration: Auto-Comment Tracking
-- Created: 2026-01-23
-- Description: Track all auto-comment activity across platforms

-- Table to store all auto-comments
CREATE TABLE IF NOT EXISTS auto_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Platform info
    platform VARCHAR(50) NOT NULL,  -- 'threads', 'instagram', 'tiktok', etc.
    account_id VARCHAR(100),         -- Our account that posted the comment
    
    -- Post info
    post_url TEXT NOT NULL,
    post_id VARCHAR(100),
    post_username VARCHAR(100),      -- Who made the original post
    
    -- Context extraction
    post_caption TEXT,               -- Text caption of the post
    post_image_context TEXT,         -- AI vision description of image
    post_comments_context TEXT,      -- Summary of top comments
    post_engagement_stats JSONB,     -- likes, comments, shares at time of comment
    
    -- Our comment
    comment_text TEXT NOT NULL,
    ai_prompt_used TEXT,             -- Full prompt sent to AI
    ai_model VARCHAR(50),            -- gpt-4o, etc.
    ai_response_raw TEXT,            -- Raw AI response
    
    -- Cost tracking
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost_usd DECIMAL(10, 6),
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, posted, failed, deleted
    verified BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    posted_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT valid_platform CHECK (platform IN ('threads', 'instagram', 'tiktok', 'twitter', 'youtube'))
);

-- Index for querying by platform and date
CREATE INDEX IF NOT EXISTS idx_auto_comments_platform_date ON auto_comments(platform, created_at DESC);

-- Index for querying by status
CREATE INDEX IF NOT EXISTS idx_auto_comments_status ON auto_comments(status);

-- Index for querying by account
CREATE INDEX IF NOT EXISTS idx_auto_comments_account ON auto_comments(account_id);

-- Daily stats view
CREATE OR REPLACE VIEW auto_comment_daily_stats AS
SELECT 
    DATE(created_at) as date,
    platform,
    COUNT(*) as total_comments,
    COUNT(*) FILTER (WHERE status = 'posted') as successful,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    SUM(estimated_cost_usd) as total_cost_usd,
    SUM(total_tokens) as total_tokens_used
FROM auto_comments
GROUP BY DATE(created_at), platform
ORDER BY date DESC, platform;

-- Hourly rate limiting view
CREATE OR REPLACE VIEW auto_comment_hourly_rate AS
SELECT 
    platform,
    account_id,
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as comments_this_hour
FROM auto_comments
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY platform, account_id, DATE_TRUNC('hour', created_at);

COMMENT ON TABLE auto_comments IS 'Tracks all auto-comments across platforms with full context and cost tracking';
