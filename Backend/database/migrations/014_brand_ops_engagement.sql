-- Migration: Brand Ops Engagement System
-- Created: 2026-01-23
-- Description: Closed-loop Brand Ops system for auto-engagement tracking and optimization

-- =============================================================================
-- AGENT RUNS - Full observability for all agent actions
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Agent identification
    agent_type VARCHAR(50) NOT NULL,  -- 'auto_commenter', 'content_generator', 'scheduler'
    agent_version VARCHAR(20) DEFAULT '1.0.0',
    run_id VARCHAR(100) UNIQUE,       -- External run ID for tracing
    
    -- Inputs
    platform VARCHAR(50),
    account_id VARCHAR(100),
    target_url TEXT,
    input_context JSONB,              -- Full context passed to agent
    prompt_version VARCHAR(50),       -- Version of prompt used
    prompt_text TEXT,                 -- Full prompt sent to AI
    
    -- Outputs
    output_content TEXT,              -- Generated content (comment, post, etc.)
    output_metadata JSONB,            -- Additional output data
    
    -- Tool calls and traces
    tool_calls JSONB,                 -- [{tool: 'openai', input: {...}, output: {...}, duration_ms: 123}]
    trace_id VARCHAR(100),            -- OpenTelemetry trace ID
    
    -- Performance
    total_duration_ms INTEGER,
    ai_tokens_used INTEGER,
    ai_cost_usd DECIMAL(10, 6),
    
    -- Status
    status VARCHAR(50) DEFAULT 'running',  -- running, success, failed, partial
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT valid_agent_type CHECK (agent_type IN ('auto_commenter', 'content_generator', 'scheduler', 'analytics', 'dm_responder'))
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_type_date ON agent_runs(agent_type, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_platform ON agent_runs(platform);

-- =============================================================================
-- ENGAGEMENT ACTIONS - Track all engagement actions (comments, likes, DMs)
-- =============================================================================
CREATE TABLE IF NOT EXISTS engagement_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source (our action)
    agent_run_id UUID REFERENCES agent_runs(id),
    action_type VARCHAR(50) NOT NULL,  -- 'comment', 'like', 'follow', 'dm', 'share'
    
    -- Platform info
    platform VARCHAR(50) NOT NULL,
    our_account_id VARCHAR(100),
    our_username VARCHAR(100),
    
    -- Target post/user
    target_post_url TEXT,
    target_post_id VARCHAR(100),
    target_username VARCHAR(100),
    target_user_id VARCHAR(100),
    
    -- Post context (what we saw)
    post_caption TEXT,
    post_image_description TEXT,      -- AI vision analysis
    post_hashtags TEXT[],
    post_mentions TEXT[],
    post_engagement_at_time JSONB,    -- {likes: N, comments: N, shares: N}
    
    -- Comments context
    top_comments JSONB,               -- [{username, text, likes}]
    
    -- Our action
    action_content TEXT,              -- Comment text, DM text, etc.
    action_metadata JSONB,            -- Additional action data
    
    -- AI generation details
    ai_prompt_used TEXT,
    ai_model VARCHAR(50),
    ai_temperature DECIMAL(3, 2),
    ai_tokens_input INTEGER,
    ai_tokens_output INTEGER,
    ai_cost_usd DECIMAL(10, 6),
    
    -- Status and verification
    status VARCHAR(50) DEFAULT 'pending',  -- pending, posted, verified, failed, deleted
    verified_at TIMESTAMPTZ,
    verification_method VARCHAR(50),  -- 'page_check', 'api', 'manual'
    
    -- Performance tracking (updated later)
    received_likes INTEGER DEFAULT 0,
    received_replies INTEGER DEFAULT 0,
    led_to_follow BOOLEAN DEFAULT FALSE,
    led_to_dm BOOLEAN DEFAULT FALSE,
    led_to_conversion BOOLEAN DEFAULT FALSE,
    
    -- UTM and attribution
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    utm_content VARCHAR(100),         -- post_id or content_id
    content_id VARCHAR(100),          -- For attribution tracking
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    posted_at TIMESTAMPTZ,
    
    CONSTRAINT valid_action_type CHECK (action_type IN ('comment', 'like', 'follow', 'dm', 'share', 'save'))
);

CREATE INDEX IF NOT EXISTS idx_engagement_platform_date ON engagement_actions(platform, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_engagement_status ON engagement_actions(status);
CREATE INDEX IF NOT EXISTS idx_engagement_target_user ON engagement_actions(target_username);

-- =============================================================================
-- CONTENT PERFORMANCE SCORES - Scoring for optimization
-- =============================================================================
CREATE TABLE IF NOT EXISTS content_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference
    engagement_action_id UUID REFERENCES engagement_actions(id),
    post_id UUID,  -- Reference to posts table if applicable
    
    -- Raw metrics (at scoring time)
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    avg_watch_time_sec DECIMAL(10, 2),
    saves INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    profile_visits INTEGER DEFAULT 0,
    link_clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    
    -- Normalized scores (0-100 vs 30-day platform median)
    attention_score DECIMAL(5, 2),    -- Based on views, watch time
    engagement_score DECIMAL(5, 2),   -- Based on saves, shares, comments
    traffic_score DECIMAL(5, 2),      -- Based on clicks, profile visits
    conversion_score DECIMAL(5, 2),   -- Based on actual conversions
    
    -- Composite score
    total_score DECIMAL(5, 2),        -- Weighted combination
    score_percentile INTEGER,         -- Rank vs other content (1-100)
    
    -- Classification
    classification VARCHAR(50),       -- 'winner', 'promising', 'average', 'flop'
    
    -- Insights
    winning_factors JSONB,            -- {hook_type: 'contrarian', cta: 'comment keyword'}
    improvement_suggestions TEXT[],
    
    -- Timestamps
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    metrics_pulled_at TIMESTAMPTZ,
    
    CONSTRAINT valid_classification CHECK (classification IN ('winner', 'promising', 'average', 'flop'))
);

-- =============================================================================
-- PROMPT VERSIONS - Track prompt evolution
-- =============================================================================
CREATE TABLE IF NOT EXISTS prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    prompt_name VARCHAR(100) NOT NULL,  -- 'instagram_comment', 'threads_reply', etc.
    version VARCHAR(20) NOT NULL,
    
    -- Content
    system_prompt TEXT,
    user_prompt_template TEXT,
    
    -- Parameters
    model VARCHAR(50) DEFAULT 'gpt-4o',
    temperature DECIMAL(3, 2) DEFAULT 0.9,
    max_tokens INTEGER DEFAULT 50,
    
    -- Performance
    times_used INTEGER DEFAULT 0,
    avg_score DECIMAL(5, 2),
    success_rate DECIMAL(5, 4),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deprecated_at TIMESTAMPTZ,
    
    UNIQUE(prompt_name, version)
);

-- =============================================================================
-- DAILY AGGREGATES - For dashboards and optimization
-- =============================================================================
CREATE TABLE IF NOT EXISTS engagement_daily_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    date DATE NOT NULL,
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(100),
    
    -- Volume
    total_actions INTEGER DEFAULT 0,
    comments_posted INTEGER DEFAULT 0,
    likes_given INTEGER DEFAULT 0,
    follows_given INTEGER DEFAULT 0,
    dms_sent INTEGER DEFAULT 0,
    
    -- Success rates
    actions_verified INTEGER DEFAULT 0,
    actions_failed INTEGER DEFAULT 0,
    verification_rate DECIMAL(5, 4),
    
    -- Engagement received
    replies_received INTEGER DEFAULT 0,
    follows_received INTEGER DEFAULT 0,
    dms_received INTEGER DEFAULT 0,
    
    -- Costs
    total_ai_tokens INTEGER DEFAULT 0,
    total_ai_cost_usd DECIMAL(10, 4) DEFAULT 0,
    
    -- Performance
    avg_content_score DECIMAL(5, 2),
    top_performing_action_id UUID,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(date, platform, account_id)
);

-- =============================================================================
-- VIEWS FOR DASHBOARDS
-- =============================================================================

-- Executive Scorecard
CREATE OR REPLACE VIEW engagement_executive_scorecard AS
SELECT 
    DATE_TRUNC('week', date) as week,
    platform,
    SUM(total_actions) as total_engagement_actions,
    SUM(comments_posted) as total_comments,
    SUM(actions_verified) as verified_actions,
    AVG(verification_rate) as avg_verification_rate,
    SUM(follows_received) as new_follows_from_engagement,
    SUM(total_ai_cost_usd) as weekly_ai_cost,
    AVG(avg_content_score) as avg_content_score
FROM engagement_daily_stats
GROUP BY DATE_TRUNC('week', date), platform
ORDER BY week DESC, platform;

-- Content Lab - Winners by hook/prompt/time
CREATE OR REPLACE VIEW engagement_content_lab AS
SELECT 
    ea.platform,
    ea.action_type,
    pv.prompt_name,
    pv.version as prompt_version,
    EXTRACT(HOUR FROM ea.posted_at) as hour_posted,
    COUNT(*) as action_count,
    AVG(cs.total_score) as avg_score,
    COUNT(*) FILTER (WHERE cs.classification = 'winner') as winners,
    COUNT(*) FILTER (WHERE cs.classification = 'flop') as flops
FROM engagement_actions ea
LEFT JOIN agent_runs ar ON ea.agent_run_id = ar.id
LEFT JOIN prompt_versions pv ON ar.prompt_version = pv.version
LEFT JOIN content_scores cs ON cs.engagement_action_id = ea.id
WHERE ea.posted_at > NOW() - INTERVAL '30 days'
GROUP BY ea.platform, ea.action_type, pv.prompt_name, pv.version, EXTRACT(HOUR FROM ea.posted_at)
ORDER BY avg_score DESC NULLS LAST;

-- Agent Health
CREATE OR REPLACE VIEW agent_health_dashboard AS
SELECT 
    agent_type,
    DATE(started_at) as date,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'success') as successful,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    AVG(total_duration_ms) as avg_duration_ms,
    SUM(ai_tokens_used) as total_tokens,
    SUM(ai_cost_usd) as total_cost,
    COUNT(*) FILTER (WHERE retry_count > 0) as runs_with_retries
FROM agent_runs
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type, DATE(started_at)
ORDER BY date DESC, agent_type;

COMMENT ON TABLE agent_runs IS 'Full observability for all agent actions - traces, inputs, outputs, costs';
COMMENT ON TABLE engagement_actions IS 'All engagement actions with full context for optimization loop';
COMMENT ON TABLE content_scores IS 'Performance scores for content optimization';
COMMENT ON TABLE prompt_versions IS 'Version control for prompts - enables A/B testing';
