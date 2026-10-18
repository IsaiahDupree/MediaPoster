-- Content Intelligence System - Part 3: North Star Metrics & AI Insights
-- This migration creates tables for weekly aggregated metrics, north star metrics,
-- AI-generated insights, and content recommendations

-- Weekly aggregated metrics (North Star Metrics)
CREATE TABLE IF NOT EXISTS weekly_metrics (
    id BIGSERIAL PRIMARY KEY,
    week_start_date DATE NOT NULL,
    user_id UUID, -- For multi-account support (future)
    
    -- North Star Metric #1: Weekly Engaged Reach
    engaged_reach INTEGER DEFAULT 0, -- Unique people who meaningfully engaged
    engaged_reach_delta_pct DECIMAL, -- % change vs last week
    
    -- North Star Metric #2: Content Leverage Score
    content_leverage_score DECIMAL DEFAULT 0, -- (comments + saves + shares + taps) / posts
    cls_delta_pct DECIMAL,
    
    -- North Star Metric #3: Warm Lead Flow
    warm_lead_flow INTEGER DEFAULT 0, -- link_clicks + dm_starts + email_signups
    warm_lead_flow_delta_pct DECIMAL,
    
    -- Supporting metrics
    total_posts INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    total_watch_time_s BIGINT DEFAULT 0,
    avg_retention_pct DECIMAL,
    
    -- Platform breakdown
    platform_reach JSONB, -- {"tiktok": 1200, "instagram": 800, ...}
    platform_posts JSONB, -- {"tiktok": 5, "instagram": 7, ...}
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(week_start_date, user_id)
);

-- AI-generated insights (pattern detection)
CREATE TABLE IF NOT EXISTS content_insights (
    id BIGSERIAL PRIMARY KEY,
    insight_type TEXT NOT NULL, -- 'hook' | 'retention' | 'cta' | 'visual' | 'timing' | 'format'
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    metric_impact TEXT, -- "+23% avg improvement" | "2.1x higher engagement"
    
    -- What this insight is based on
    based_on_post_ids UUID[], -- Array of platform_post IDs
    based_on_segment_ids BIGINT[], -- Array of segment IDs
    sample_size INTEGER, -- How many posts/segments this pattern was found in
    confidence_score DECIMAL, -- 0-1 statistical confidence
    
    -- Pattern details
    pattern_data JSONB, -- {"hook_type": "pain + identity", "visual_type": "close_up", ...}
    
    -- Recommended actions
    recommended_action JSONB, -- {"type": "generate_hooks", "pattern": "pain + identity", "button_text": "Generate hooks"}
    
    -- Lifecycle
    status TEXT DEFAULT 'active', -- 'active' | 'archived' | 'dismissed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE, -- Insights can be time-limited
    dismissed_at TIMESTAMP WITH TIME ZONE,
    
    -- Tracking
    times_applied INTEGER DEFAULT 0, -- How many times user acted on this
    avg_result_improvement DECIMAL -- Did it actually help?
);

-- Content performance predictions (ML model scores)
CREATE TABLE IF NOT EXISTS content_predictions (
    id BIGSERIAL PRIMARY KEY,
    platform_post_id UUID REFERENCES platform_posts(id) ON DELETE CASCADE,
    predicted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Predictions (before publishing)
    predicted_views INTEGER,
    predicted_engagement_rate DECIMAL,
    predicted_save_rate DECIMAL,
    predicted_cta_response_rate DECIMAL,
    confidence_score DECIMAL, -- 0-1
    
    -- Actual results (after checkbacks)
    actual_views INTEGER,
    actual_engagement_rate DECIMAL,
    actual_save_rate DECIMAL,
    actual_cta_response_rate DECIMAL,
    
    -- Model performance
    prediction_accuracy DECIMAL, -- How close were we?
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content recommendations (what to post next)
CREATE TABLE IF NOT EXISTS content_recommendations (
    id BIGSERIAL PRIMARY KEY,
    recommendation_type TEXT NOT NULL, -- 'post_timing' | 'topic' | 'format' | 'platform' | 'remix'
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    reasoning TEXT, -- Why this recommendation
    
    -- Details
    recommended_data JSONB, -- {"day": "Tuesday", "time": "3-6pm", "platform": "tiktok"}
    
    -- Based on
    based_on_insight_ids BIGINT[], -- References to insights
    expected_improvement TEXT, -- "+15% engagement vs your baseline"
    
    -- Priority
    priority INTEGER DEFAULT 5, -- 1-10
    
    -- Status
    status TEXT DEFAULT 'pending', -- 'pending' | 'accepted' | 'rejected' | 'completed'
    accepted_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Content quality scores (overall health metrics)
CREATE TABLE IF NOT EXISTS content_quality_scores (
    id BIGSERIAL PRIMARY KEY,
    platform_post_id UUID REFERENCES platform_posts(id) ON DELETE CASCADE,
    video_id UUID REFERENCES analyzed_videos(id) ON DELETE CASCADE,
    
    -- Hook quality
    hook_retention_3s DECIMAL, -- 0-1, retention at 3 seconds
    hook_clarity_score DECIMAL, -- 0-1, is the hook clear and specific?
    hook_pattern_score DECIMAL, -- 0-1, does it match proven patterns?
    
    -- Content structure
    segment_balance_score DECIMAL, -- 0-1, good ratio of hook/body/cta?
    pacing_score DECIMAL, -- 0-1, words per minute variance
    
    -- Visual quality
    visual_variety_score DECIMAL, -- 0-1, shot type variety
    text_readability_score DECIMAL, -- 0-1, can you read on-screen text?
    pattern_interrupt_count INTEGER,
    
    -- CTA effectiveness
    cta_clarity_score DECIMAL, -- 0-1, is CTA clear?
    cta_timing_score DECIMAL, -- 0-1, is CTA timed well?
    
    -- Overall
    overall_score DECIMAL, -- 0-100, weighted average
    score_tier TEXT, -- 'excellent' | 'good' | 'average' | 'needs_work'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_weekly_metrics_week ON weekly_metrics(week_start_date);
CREATE INDEX IF NOT EXISTS idx_weekly_metrics_user ON weekly_metrics(user_id);

CREATE INDEX IF NOT EXISTS idx_insights_type ON content_insights(insight_type);
CREATE INDEX IF NOT EXISTS idx_insights_status ON content_insights(status);
CREATE INDEX IF NOT EXISTS idx_insights_created ON content_insights(created_at);
CREATE INDEX IF NOT EXISTS idx_insights_expires ON content_insights(expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_predictions_post ON content_predictions(platform_post_id);
CREATE INDEX IF NOT EXISTS idx_predictions_predicted ON content_predictions(predicted_at);

CREATE INDEX IF NOT EXISTS idx_recommendations_type ON content_recommendations(recommendation_type);
CREATE INDEX IF NOT EXISTS idx_recommendations_status ON content_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_recommendations_priority ON content_recommendations(priority);
CREATE INDEX IF NOT EXISTS idx_recommendations_expires ON content_recommendations(expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_quality_post ON content_quality_scores(platform_post_id);
CREATE INDEX IF NOT EXISTS idx_quality_video ON content_quality_scores(video_id);
CREATE INDEX IF NOT EXISTS idx_quality_tier ON content_quality_scores(score_tier);

-- Enable RLS
ALTER TABLE weekly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_quality_scores ENABLE ROW LEVEL SECURITY;

-- Comments for documentation
COMMENT ON TABLE weekly_metrics IS 'Weekly aggregated North Star Metrics: Engaged Reach, Content Leverage Score, Warm Lead Flow';
COMMENT ON TABLE content_insights IS 'AI-generated insights from pattern detection across videos';
COMMENT ON TABLE content_predictions IS 'ML predictions for content performance before publishing';
COMMENT ON TABLE content_recommendations IS 'Smart recommendations for what to post next';
COMMENT ON TABLE content_quality_scores IS 'Overall content quality scoring across multiple dimensions';
