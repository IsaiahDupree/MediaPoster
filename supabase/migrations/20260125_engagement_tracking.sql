-- ============================================================================
-- Auto-Engagement Comment Tracking
-- ============================================================================
-- Tracks posted comments to prevent duplicates and enforce daily limits.
-- Part of the pub/sub auto-engagement system.

-- Comment tracking table
CREATE TABLE IF NOT EXISTS engagement_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,           -- 'threads', 'instagram', 'tiktok'
    post_url TEXT NOT NULL,           -- URL of the post commented on
    post_username TEXT,               -- Creator of the post
    comment_text TEXT NOT NULL,       -- The comment we posted
    proof_screenshot TEXT,            -- Path to proof screenshot
    engagement_account TEXT,          -- Our account that posted
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate comments on same post per platform
    CONSTRAINT unique_platform_post UNIQUE(platform, post_url)
);

-- Index for daily count queries
CREATE INDEX IF NOT EXISTS idx_engagement_comments_daily 
ON engagement_comments (platform, created_at);

-- Index for recent comments lookup
CREATE INDEX IF NOT EXISTS idx_engagement_comments_platform_recent
ON engagement_comments (platform, created_at DESC);

-- Daily limits configuration table
CREATE TABLE IF NOT EXISTS engagement_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL UNIQUE,
    daily_limit INTEGER NOT NULL DEFAULT 100,
    is_enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default limits for each platform
INSERT INTO engagement_limits (platform, daily_limit, is_enabled) VALUES
    ('threads', 100, true),
    ('instagram', 100, true),
    ('tiktok', 100, true)
ON CONFLICT (platform) DO NOTHING;

-- ============================================================================
-- RLS Policies
-- ============================================================================

-- Enable RLS
ALTER TABLE engagement_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagement_limits ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users (service role)
CREATE POLICY "Allow all for service role on engagement_comments"
ON engagement_comments FOR ALL
USING (true)
WITH CHECK (true);

CREATE POLICY "Allow all for service role on engagement_limits"
ON engagement_limits FOR ALL
USING (true)
WITH CHECK (true);

-- ============================================================================
-- Functions for analytics
-- ============================================================================

-- Get daily comment count for a platform
CREATE OR REPLACE FUNCTION get_engagement_daily_count(p_platform TEXT)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)::INTEGER
        FROM engagement_comments
        WHERE platform = p_platform
        AND created_at >= CURRENT_DATE
    );
END;
$$ LANGUAGE plpgsql;

-- Get engagement summary for all platforms
CREATE OR REPLACE FUNCTION get_engagement_summary()
RETURNS TABLE (
    platform TEXT,
    daily_limit INTEGER,
    is_enabled BOOLEAN,
    today_count BIGINT,
    remaining INTEGER,
    total_all_time BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.platform,
        l.daily_limit,
        l.is_enabled,
        COALESCE(today.cnt, 0) AS today_count,
        GREATEST(0, l.daily_limit - COALESCE(today.cnt, 0)::INTEGER) AS remaining,
        COALESCE(total.cnt, 0) AS total_all_time
    FROM engagement_limits l
    LEFT JOIN (
        SELECT platform, COUNT(*) AS cnt
        FROM engagement_comments
        WHERE created_at >= CURRENT_DATE
        GROUP BY platform
    ) today ON l.platform = today.platform
    LEFT JOIN (
        SELECT platform, COUNT(*) AS cnt
        FROM engagement_comments
        GROUP BY platform
    ) total ON l.platform = total.platform;
END;
$$ LANGUAGE plpgsql;
