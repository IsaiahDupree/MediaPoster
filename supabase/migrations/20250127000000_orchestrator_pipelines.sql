-- ARCH-001: Master Orchestrator Pipeline Tracking
-- ================================================
-- Tables for tracking end-to-end pipeline execution

-- Orchestrator pipelines table (tracks full pipeline runs)
CREATE TABLE IF NOT EXISTS orchestrator_pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id TEXT UNIQUE NOT NULL,  -- Short ID for UI (e.g., "a1b2c3d4")

    -- Pipeline configuration
    theme TEXT NOT NULL,
    num_parts INTEGER DEFAULT 3,
    character TEXT,
    publish_platforms TEXT[] DEFAULT ARRAY['tiktok', 'instagram', 'youtube'],
    schedule_tweets BOOLEAN DEFAULT TRUE,
    tweets_per_day INTEGER DEFAULT 12,
    offer_url TEXT,

    -- Execution tracking
    status TEXT NOT NULL DEFAULT 'initializing',
    steps_completed TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    duration_seconds INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (COALESCE(completed_at, failed_at, NOW()) - started_at))::INTEGER
    ) STORED,

    -- Outputs
    video_path TEXT,
    stitched_video TEXT,
    analysis_result JSONB,
    published_count INTEGER DEFAULT 0,
    tweets_scheduled INTEGER DEFAULT 0,

    -- Error tracking
    error TEXT,

    -- Correlation
    correlation_id TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipelines_pipeline_id ON orchestrator_pipelines(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipelines_status ON orchestrator_pipelines(status);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipelines_started_at ON orchestrator_pipelines(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipelines_correlation_id ON orchestrator_pipelines(correlation_id);

-- Orchestrator pipeline steps table (tracks individual pipeline steps)
CREATE TABLE IF NOT EXISTS orchestrator_pipeline_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id TEXT NOT NULL REFERENCES orchestrator_pipelines(pipeline_id) ON DELETE CASCADE,

    -- Step details
    step_name TEXT NOT NULL,  -- e.g., "video_generation", "content_analysis", "publishing"
    step_order INTEGER NOT NULL,  -- 0-based ordering
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    duration_seconds INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (COALESCE(completed_at, failed_at, NOW()) - started_at))::INTEGER
    ) STORED,

    -- Output
    output JSONB,
    error TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(pipeline_id, step_name)
);

-- Index for fast step lookups
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipeline_steps_pipeline_id ON orchestrator_pipeline_steps(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipeline_steps_status ON orchestrator_pipeline_steps(status);
CREATE INDEX IF NOT EXISTS idx_orchestrator_pipeline_steps_order ON orchestrator_pipeline_steps(pipeline_id, step_order);

-- Offer traffic tracking table (ARCH-005)
CREATE TABLE IF NOT EXISTS offer_traffic (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- UTM parameters
    utm_campaign TEXT NOT NULL,
    utm_source TEXT NOT NULL DEFAULT 'twitter',
    utm_medium TEXT NOT NULL DEFAULT 'social',
    utm_content TEXT,  -- Variant identifier for A/B testing

    -- Visitor tracking
    user_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    referrer TEXT,

    -- Timing
    clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for analytics queries
CREATE INDEX IF NOT EXISTS idx_offer_traffic_campaign ON offer_traffic(utm_campaign);
CREATE INDEX IF NOT EXISTS idx_offer_traffic_clicked_at ON offer_traffic(clicked_at DESC);
CREATE INDEX IF NOT EXISTS idx_offer_traffic_campaign_content ON offer_traffic(utm_campaign, utm_content);

-- Offer conversions table (ARCH-005)
CREATE TABLE IF NOT EXISTS offer_conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- UTM parameters (to link back to traffic)
    utm_campaign TEXT NOT NULL,
    utm_content TEXT,

    -- Conversion details
    conversion_type TEXT NOT NULL,  -- purchase, signup, trial, etc.
    user_id TEXT,
    revenue NUMERIC(10, 2),
    conversion_data JSONB DEFAULT '{}'::JSONB,

    -- Timing
    converted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for analytics queries
CREATE INDEX IF NOT EXISTS idx_offer_conversions_campaign ON offer_conversions(utm_campaign);
CREATE INDEX IF NOT EXISTS idx_offer_conversions_converted_at ON offer_conversions(converted_at DESC);
CREATE INDEX IF NOT EXISTS idx_offer_conversions_type ON offer_conversions(conversion_type);

-- =========================================================================
-- VIEWS & FUNCTIONS
-- =========================================================================

-- View: Pipeline summary with computed metrics
CREATE OR REPLACE VIEW pipeline_summary AS
SELECT
    p.pipeline_id,
    p.theme,
    p.status,
    p.started_at,
    p.completed_at,
    p.duration_seconds,
    p.steps_completed,
    (
        SELECT COUNT(*)
        FROM orchestrator_pipeline_steps s
        WHERE s.pipeline_id = p.pipeline_id
    ) AS total_steps,
    p.video_path,
    p.published_count,
    p.tweets_scheduled,
    p.error
FROM orchestrator_pipelines p
ORDER BY p.started_at DESC;

-- Function: Get pipeline summary (for API)
CREATE OR REPLACE FUNCTION get_pipeline_summary(p_pipeline_id TEXT)
RETURNS TABLE (
    pipeline_id TEXT,
    theme TEXT,
    status TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    steps_completed INTEGER,
    total_steps BIGINT,
    video_path TEXT,
    published_count INTEGER,
    tweets_scheduled INTEGER,
    error TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.pipeline_id,
        p.theme,
        p.status,
        p.started_at,
        p.completed_at,
        p.duration_seconds,
        ARRAY_LENGTH(p.steps_completed, 1) AS steps_completed,
        (
            SELECT COUNT(*)
            FROM orchestrator_pipeline_steps s
            WHERE s.pipeline_id = p.pipeline_id
        ) AS total_steps,
        p.video_path,
        p.published_count,
        p.tweets_scheduled,
        p.error
    FROM orchestrator_pipelines p
    WHERE p.pipeline_id = p_pipeline_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get pipeline metrics (for dashboard)
CREATE OR REPLACE FUNCTION get_pipeline_metrics(days INTEGER DEFAULT 30)
RETURNS TABLE (
    total_pipelines BIGINT,
    successful_pipelines BIGINT,
    failed_pipelines BIGINT,
    success_rate NUMERIC,
    avg_duration_seconds NUMERIC,
    total_videos_generated BIGINT,
    total_posts_published BIGINT,
    total_tweets_scheduled BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) AS total_pipelines,
        COUNT(*) FILTER (WHERE status = 'completed') AS successful_pipelines,
        COUNT(*) FILTER (WHERE status = 'failed') AS failed_pipelines,
        CASE
            WHEN COUNT(*) > 0 THEN
                ROUND((COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC / COUNT(*)) * 100, 2)
            ELSE 0
        END AS success_rate,
        AVG(duration_seconds) FILTER (WHERE status = 'completed') AS avg_duration_seconds,
        COUNT(*) FILTER (WHERE stitched_video IS NOT NULL) AS total_videos_generated,
        SUM(published_count) AS total_posts_published,
        SUM(tweets_scheduled) AS total_tweets_scheduled
    FROM orchestrator_pipelines
    WHERE started_at > NOW() - INTERVAL '1 day' * days;
END;
$$ LANGUAGE plpgsql;

-- Function: Get offer campaign analytics (ARCH-005)
CREATE OR REPLACE FUNCTION get_offer_campaign_analytics(
    p_utm_campaign TEXT,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_clicks BIGINT,
    unique_clicks BIGINT,
    total_conversions BIGINT,
    conversion_rate NUMERIC,
    total_revenue NUMERIC,
    avg_order_value NUMERIC,
    roi_percentage NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH traffic_stats AS (
        SELECT
            COUNT(*) AS clicks,
            COUNT(DISTINCT ip_address) AS unique_visitors
        FROM offer_traffic
        WHERE utm_campaign = p_utm_campaign
          AND clicked_at > NOW() - INTERVAL '1 day' * p_days
    ),
    conversion_stats AS (
        SELECT
            COUNT(*) AS conversions,
            SUM(revenue) AS revenue
        FROM offer_conversions
        WHERE utm_campaign = p_utm_campaign
          AND converted_at > NOW() - INTERVAL '1 day' * p_days
    )
    SELECT
        t.clicks AS total_clicks,
        t.unique_visitors AS unique_clicks,
        c.conversions AS total_conversions,
        CASE
            WHEN t.unique_visitors > 0 THEN
                ROUND((c.conversions::NUMERIC / t.unique_visitors) * 100, 2)
            ELSE 0
        END AS conversion_rate,
        COALESCE(c.revenue, 0) AS total_revenue,
        CASE
            WHEN c.conversions > 0 THEN ROUND(c.revenue / c.conversions, 2)
            ELSE 0
        END AS avg_order_value,
        CASE
            WHEN t.clicks > 0 THEN
                ROUND(((c.revenue - (t.clicks * 0.10)) / (t.clicks * 0.10)) * 100, 2)
            ELSE 0
        END AS roi_percentage
    FROM traffic_stats t
    CROSS JOIN conversion_stats c;
END;
$$ LANGUAGE plpgsql;

-- =========================================================================
-- ROW LEVEL SECURITY (RLS)
-- =========================================================================

-- Enable RLS on all tables
ALTER TABLE orchestrator_pipelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE orchestrator_pipeline_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE offer_traffic ENABLE ROW LEVEL SECURITY;
ALTER TABLE offer_conversions ENABLE ROW LEVEL SECURITY;

-- Policies: Allow all operations for authenticated users
CREATE POLICY "Allow all for authenticated users" ON orchestrator_pipelines
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for authenticated users" ON orchestrator_pipeline_steps
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for authenticated users" ON offer_traffic
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for authenticated users" ON offer_conversions
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- =========================================================================
-- TRIGGERS
-- =========================================================================

-- Trigger: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_orchestrator_pipelines_updated_at
    BEFORE UPDATE ON orchestrator_pipelines
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orchestrator_pipeline_steps_updated_at
    BEFORE UPDATE ON orchestrator_pipeline_steps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- COMMENTS
-- =========================================================================

COMMENT ON TABLE orchestrator_pipelines IS 'ARCH-001: Tracks end-to-end pipeline executions (Sora → Analyze → Publish → Tweet)';
COMMENT ON TABLE orchestrator_pipeline_steps IS 'ARCH-001: Tracks individual steps within a pipeline execution';
COMMENT ON TABLE offer_traffic IS 'ARCH-005: Tracks clicks/visits to offer URLs from promotional content';
COMMENT ON TABLE offer_conversions IS 'ARCH-005: Tracks conversions (purchases, signups) from offers';
COMMENT ON FUNCTION get_pipeline_summary IS 'ARCH-007: API function to retrieve pipeline status';
COMMENT ON FUNCTION get_pipeline_metrics IS 'ARCH-007: API function to retrieve aggregated pipeline metrics';
COMMENT ON FUNCTION get_offer_campaign_analytics IS 'ARCH-005: API function to retrieve offer campaign performance';
