-- ============================================================================
-- CLOSED-LOOP CONTENT SYSTEM SCHEMA
-- ============================================================================
-- Architecture: Publish → Measure → Review → Extract Patterns → Update Playbook → Generate → Repeat
-- 
-- Core principle: A video isn't one data point. It's a TIME SERIES with
-- multiple review windows (1h, 6h, 24h, 72h, 7d...)
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- A) CONTENT + CREATIVE DNA
-- ============================================================================

-- Source types for content
CREATE TYPE content_source_type AS ENUM (
    'UGC',           -- User generated (talking head, vlogs)
    'SORA',          -- Sora AI generated
    'AI_EDIT',       -- AI-assisted editing
    'SCREEN_RECORD', -- Screen recordings, tutorials
    'BROLL',         -- B-roll footage
    'REMIX'          -- Remixed/repurposed content
);

-- Format types
CREATE TYPE content_format_type AS ENUM (
    'talking_head',
    'broll',
    'slideshow',
    'meme',
    'demo',
    'testimonial',
    'voiceover',
    'tutorial',
    'reaction',
    'duet',
    'compilation'
);

-- CTA types
CREATE TYPE cta_type AS ENUM (
    'comment',
    'link',
    'dm',
    'subscribe',
    'checkout',
    'follow',
    'share',
    'save',
    'none'
);

-- Content items - the creative asset itself
CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Basic info
    title VARCHAR(500),
    internal_name VARCHAR(255),
    
    -- Content DNA
    source_type content_source_type NOT NULL DEFAULT 'UGC',
    format_type content_format_type,
    aspect_ratio VARCHAR(10), -- '9:16', '16:9', '1:1', '4:5'
    duration_sec INTEGER,
    
    -- Script/text content
    script_id UUID,
    transcript_text TEXT,
    transcript_summary TEXT, -- AI-generated summary
    hook_text TEXT, -- First 1-2 lines (crucial for retention)
    
    -- CTA & offer
    cta_type cta_type DEFAULT 'none',
    offer_id UUID,
    
    -- Organization
    brand_id UUID,
    campaign_id UUID,
    niche_id UUID,
    
    -- File references
    original_video_id UUID REFERENCES original_videos(id),
    clip_id UUID REFERENCES clips(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_content_items_source ON content_items(source_type);
CREATE INDEX idx_content_items_format ON content_items(format_type);
CREATE INDEX idx_content_items_created ON content_items(created_at);

-- Creative features - structured tags for querying patterns
CREATE TYPE emotion_type AS ENUM (
    'curiosity',
    'fear',
    'status',
    'relief',
    'aspiration',
    'frustration',
    'excitement',
    'urgency',
    'nostalgia',
    'inspiration'
);

CREATE TYPE pov_type AS ENUM (
    'founder',
    'customer',
    'narrator',
    'educator',
    'entertainer',
    'expert',
    'friend'
);

CREATE TYPE proof_type AS ENUM (
    'demo',
    'metric',
    'testimonial',
    'authority',
    'comparison',
    'before_after',
    'social_proof',
    'none'
);

CREATE TYPE editing_style AS ENUM (
    'fast_cuts',
    'captions_heavy',
    'lo_fi',
    'cinematic',
    'minimal',
    'high_energy',
    'calm',
    'documentary'
);

CREATE TABLE IF NOT EXISTS creative_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_item_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    
    -- Pattern references
    hook_pattern_id UUID,
    topic_cluster_id UUID,
    
    -- Emotional/structural tags
    emotion emotion_type,
    pov pov_type,
    proof_type proof_type,
    editing_style editing_style,
    
    -- Audio/visual
    sound_id VARCHAR(255), -- Platform sound ID
    sound_name VARCHAR(500),
    visual_motifs TEXT[], -- Keywords array
    
    -- Pacing
    avg_shot_duration_sec NUMERIC(5,2),
    cuts_per_minute NUMERIC(5,2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_creative_features_content ON creative_features(content_item_id);
CREATE INDEX idx_creative_features_emotion ON creative_features(emotion);
CREATE INDEX idx_creative_features_hook ON creative_features(hook_pattern_id);

-- ============================================================================
-- B) POSTING LAYER (same creative posted many places)
-- ============================================================================

CREATE TYPE platform_type AS ENUM (
    'tiktok',
    'instagram_reels',
    'instagram_feed',
    'youtube_shorts',
    'youtube',
    'twitter',
    'linkedin',
    'facebook',
    'threads',
    'pinterest',
    'bluesky'
);

CREATE TYPE posting_status AS ENUM (
    'draft',
    'scheduled',
    'posting',
    'posted',
    'failed',
    'pulled',
    'archived'
);

CREATE TABLE IF NOT EXISTS postings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_item_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    
    -- Platform info
    platform platform_type NOT NULL,
    account_id INTEGER, -- Blotato account ID
    platform_post_id VARCHAR(255), -- ID on the platform
    platform_url TEXT,
    
    -- Timing
    scheduled_at TIMESTAMP WITH TIME ZONE,
    posted_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status posting_status DEFAULT 'draft',
    
    -- Content variations per platform
    caption_text TEXT,
    hashtags TEXT[],
    link_used TEXT,
    
    -- Experiment tracking
    experiment_id UUID,
    variant_label VARCHAR(50), -- 'A', 'B', 'control', etc.
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_postings_content ON postings(content_item_id);
CREATE INDEX idx_postings_platform ON postings(platform);
CREATE INDEX idx_postings_status ON postings(status);
CREATE INDEX idx_postings_posted ON postings(posted_at);
CREATE INDEX idx_postings_account ON postings(account_id);

-- ============================================================================
-- C) METRICS AS TIME SERIES (where winners are found)
-- ============================================================================

-- Raw metric snapshots at various time points
CREATE TABLE IF NOT EXISTS metric_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    posting_id UUID NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    
    -- Timing
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    hours_since_post NUMERIC(10,2),
    
    -- Core metrics
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    
    -- Watch metrics (when available)
    watch_time_sec INTEGER,
    avg_view_duration_sec NUMERIC(10,2),
    completion_rate NUMERIC(5,4), -- 0.0000 to 1.0000
    
    -- Conversion metrics
    ctr NUMERIC(5,4),
    profile_visits INTEGER DEFAULT 0,
    link_clicks INTEGER DEFAULT 0,
    follows INTEGER DEFAULT 0,
    
    -- Revenue (if tracked)
    revenue NUMERIC(10,2),
    purchases INTEGER DEFAULT 0,
    
    -- Platform-specific
    platform_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_metric_snapshots_posting ON metric_snapshots(posting_id);
CREATE INDEX idx_metric_snapshots_captured ON metric_snapshots(captured_at);
CREATE INDEX idx_metric_snapshots_hours ON metric_snapshots(hours_since_post);

-- Derived/computed metrics per posting per window
CREATE TABLE IF NOT EXISTS derived_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    posting_id UUID NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    window_id UUID NOT NULL, -- References review_windows
    
    -- Computed at this window
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Velocity metrics
    velocity_views_per_hour NUMERIC(10,2),
    velocity_likes_per_hour NUMERIC(10,2),
    
    -- Rate metrics
    engagement_rate NUMERIC(5,4), -- (likes + comments + shares) / views
    share_rate NUMERIC(5,4),
    save_rate NUMERIC(5,4),
    hold_rate NUMERIC(5,4), -- Proxy for retention
    conversion_rate NUMERIC(5,4),
    
    -- Normalized score (0-100, relative to baseline)
    normalized_score NUMERIC(5,2),
    
    -- Comparison baselines used
    platform_baseline NUMERIC(5,2),
    account_baseline NUMERIC(5,2),
    format_baseline NUMERIC(5,2),
    
    UNIQUE(posting_id, window_id)
);

CREATE INDEX idx_derived_metrics_posting ON derived_metrics(posting_id);
CREATE INDEX idx_derived_metrics_window ON derived_metrics(window_id);
CREATE INDEX idx_derived_metrics_score ON derived_metrics(normalized_score);

-- ============================================================================
-- D) REVIEW WINDOWS + SCORING RULES
-- ============================================================================

-- Review windows define checkback periods per platform
CREATE TABLE IF NOT EXISTS review_windows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    platform platform_type NOT NULL,
    name VARCHAR(50) NOT NULL, -- '1h', '6h', '24h', '72h', '7d', '14d'
    
    -- Time range
    start_hour INTEGER NOT NULL,
    end_hour INTEGER NOT NULL,
    
    -- Scoring weights (how much each metric matters at this window)
    primary_metric_weights JSONB DEFAULT '{
        "velocity": 0.3,
        "engagement_rate": 0.25,
        "share_rate": 0.2,
        "retention": 0.25
    }'::jsonb,
    
    -- Thresholds for classification
    thresholds JSONB DEFAULT '{
        "winner": {"min_score": 70, "min_velocity_percentile": 75},
        "ok": {"min_score": 40, "min_velocity_percentile": 40},
        "loser": {"max_score": 40}
    }'::jsonb,
    
    -- Actions to trigger at this window
    auto_actions JSONB DEFAULT '[]'::jsonb,
    
    is_active BOOLEAN DEFAULT true,
    
    UNIQUE(platform, name)
);

-- Seed default review windows
INSERT INTO review_windows (platform, name, start_hour, end_hour, primary_metric_weights) VALUES
    -- TikTok: fast burn, velocity matters early
    ('tiktok', '1h', 0, 1, '{"velocity": 0.5, "engagement_rate": 0.3, "share_rate": 0.2}'),
    ('tiktok', '6h', 1, 6, '{"velocity": 0.4, "engagement_rate": 0.3, "share_rate": 0.2, "retention": 0.1}'),
    ('tiktok', '24h', 6, 24, '{"velocity": 0.3, "engagement_rate": 0.3, "share_rate": 0.2, "retention": 0.2}'),
    ('tiktok', '72h', 24, 72, '{"velocity": 0.2, "engagement_rate": 0.3, "share_rate": 0.25, "retention": 0.25}'),
    
    -- Instagram Reels: slower discovery, retention matters more
    ('instagram_reels', '24h', 0, 24, '{"velocity": 0.35, "engagement_rate": 0.3, "save_rate": 0.2, "retention": 0.15}'),
    ('instagram_reels', '72h', 24, 72, '{"velocity": 0.25, "engagement_rate": 0.3, "save_rate": 0.25, "retention": 0.2}'),
    ('instagram_reels', '7d', 72, 168, '{"velocity": 0.2, "engagement_rate": 0.3, "save_rate": 0.25, "retention": 0.25}'),
    
    -- YouTube Shorts: longer tail, retention is king
    ('youtube_shorts', '24h', 0, 24, '{"velocity": 0.3, "engagement_rate": 0.25, "retention": 0.3, "ctr": 0.15}'),
    ('youtube_shorts', '7d', 24, 168, '{"velocity": 0.2, "engagement_rate": 0.25, "retention": 0.35, "ctr": 0.2}'),
    ('youtube_shorts', '14d', 168, 336, '{"velocity": 0.15, "engagement_rate": 0.25, "retention": 0.4, "ctr": 0.2}')
ON CONFLICT (platform, name) DO NOTHING;

-- Review labels
CREATE TYPE review_label AS ENUM (
    'winner',
    'needs_iteration',
    'loser',
    'pending',
    'outlier'
);

-- Next actions after review
CREATE TYPE review_next_action AS ENUM (
    'iterate_hook',
    'iterate_edit',
    'iterate_caption',
    'repost_variant',
    'scale_variations',
    'kill_concept',
    'analyze_further',
    'no_action'
);

-- Failure reason tags
CREATE TYPE failure_reason AS ENUM (
    'weak_hook',
    'bad_pacing',
    'wrong_audience',
    'unclear_offer',
    'low_energy',
    'poor_audio',
    'too_long',
    'too_short',
    'wrong_timing',
    'saturated_topic',
    'weak_cta',
    'confusing_message',
    'technical_issue'
);

-- Reviews table - the systematic review process
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    posting_id UUID NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    window_id UUID NOT NULL REFERENCES review_windows(id),
    
    -- Timing
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Scores
    auto_score NUMERIC(5,2), -- System-computed
    human_score NUMERIC(5,2), -- Manual override
    final_score NUMERIC(5,2) GENERATED ALWAYS AS (COALESCE(human_score, auto_score)) STORED,
    
    -- Classification
    label review_label DEFAULT 'pending',
    
    -- Failure analysis
    failure_reasons failure_reason[],
    
    -- Notes and actions
    notes TEXT,
    next_action review_next_action DEFAULT 'no_action',
    
    -- Who reviewed
    reviewed_by VARCHAR(100), -- 'system' or user ID
    
    UNIQUE(posting_id, window_id)
);

CREATE INDEX idx_reviews_posting ON reviews(posting_id);
CREATE INDEX idx_reviews_window ON reviews(window_id);
CREATE INDEX idx_reviews_label ON reviews(label);
CREATE INDEX idx_reviews_score ON reviews(final_score);

-- ============================================================================
-- E) TREND INTELLIGENCE
-- ============================================================================

CREATE TYPE trend_type AS ENUM (
    'sound',
    'hook',
    'topic',
    'format',
    'editing_style',
    'hashtag',
    'challenge',
    'template'
);

CREATE TABLE IF NOT EXISTS trend_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    platform platform_type NOT NULL,
    trend_type trend_type NOT NULL,
    
    -- Identity
    name VARCHAR(500) NOT NULL,
    platform_identifier VARCHAR(255), -- Sound ID, hashtag, etc.
    
    -- Scoring
    trend_score NUMERIC(5,2), -- 0-100 how hot
    velocity NUMERIC(10,2), -- Growth rate
    
    -- Discovery
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Examples
    examples JSONB DEFAULT '[]'::jsonb, -- Array of post URLs/IDs
    
    -- Analysis
    notes TEXT,
    why_it_works TEXT, -- AI summary
    
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_trend_items_platform ON trend_items(platform);
CREATE INDEX idx_trend_items_type ON trend_items(trend_type);
CREATE INDEX idx_trend_items_score ON trend_items(trend_score DESC);
CREATE INDEX idx_trend_items_discovered ON trend_items(discovered_at);

-- Trend recommendations (filtered by relevance to your niche)
CREATE TABLE IF NOT EXISTS trend_recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trend_item_id UUID NOT NULL REFERENCES trend_items(id) ON DELETE CASCADE,
    niche_id UUID,
    
    -- Fit scoring
    fit_score NUMERIC(5,2), -- Combined relevance
    relevance_score NUMERIC(5,2), -- Matches ICP/niche
    feasibility_score NUMERIC(5,2), -- Can we produce it?
    offer_alignment_score NUMERIC(5,2), -- Drives action?
    
    -- Suggestions
    suggested_angles JSONB DEFAULT '[]'::jsonb,
    suggested_formats JSONB DEFAULT '[]'::jsonb, -- UGC/AI mix
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    
    is_used BOOLEAN DEFAULT false
);

CREATE INDEX idx_trend_recommendations_trend ON trend_recommendations(trend_item_id);
CREATE INDEX idx_trend_recommendations_fit ON trend_recommendations(fit_score DESC);

-- ============================================================================
-- F) PROMPT + PLAYBOOK MEMORY
-- ============================================================================

CREATE TYPE prompt_purpose AS ENUM (
    'brief_generation',
    'script',
    'hook',
    'storyboard',
    'caption',
    'iteration',
    'analysis',
    'insight_extraction'
);

CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    name VARCHAR(255) NOT NULL,
    purpose prompt_purpose NOT NULL,
    
    -- Template content
    template_text TEXT NOT NULL,
    system_prompt TEXT,
    
    -- Required context
    required_context_fields JSONB DEFAULT '[]'::jsonb,
    
    -- Versioning
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_prompt_templates_purpose ON prompt_templates(purpose);
CREATE INDEX idx_prompt_templates_active ON prompt_templates(is_active);

-- Log every prompt run for traceability
CREATE TABLE IF NOT EXISTS prompt_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES prompt_templates(id),
    
    -- Inputs
    inputs_json JSONB NOT NULL,
    context_pack JSONB, -- The RAG-style context fed
    
    -- Output
    output_text TEXT,
    output_structured JSONB, -- Parsed output if applicable
    
    -- Model info
    model_used VARCHAR(100),
    tokens_used INTEGER,
    latency_ms INTEGER,
    
    -- Linking
    linked_content_item_id UUID REFERENCES content_items(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_prompt_runs_template ON prompt_runs(template_id);
CREATE INDEX idx_prompt_runs_content ON prompt_runs(linked_content_item_id);
CREATE INDEX idx_prompt_runs_created ON prompt_runs(created_at);

-- Playbook rules - the evolving "what works" library
CREATE TYPE rule_type AS ENUM (
    'hook',
    'pacing',
    'offer',
    'structure',
    'editing',
    'caption',
    'timing',
    'audience',
    'sound',
    'visual'
);

CREATE TABLE IF NOT EXISTS playbook_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    niche_id UUID,
    platform platform_type,
    
    rule_type rule_type NOT NULL,
    rule_text TEXT NOT NULL,
    
    -- Evidence
    evidence_links JSONB DEFAULT '[]'::jsonb, -- Posting/review IDs that support this
    supporting_count INTEGER DEFAULT 0,
    
    -- Confidence
    confidence_score NUMERIC(5,2) DEFAULT 50.0, -- 0-100
    
    -- Metadata
    last_validated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_playbook_rules_type ON playbook_rules(rule_type);
CREATE INDEX idx_playbook_rules_platform ON playbook_rules(platform);
CREATE INDEX idx_playbook_rules_confidence ON playbook_rules(confidence_score DESC);

-- ============================================================================
-- G) CONTENT SLOTS (daily mix planning)
-- ============================================================================

CREATE TYPE slot_objective AS ENUM (
    'reach',
    'nurture',
    'convert',
    'engage',
    'experiment'
);

CREATE TABLE IF NOT EXISTS content_slots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- When
    slot_date DATE NOT NULL,
    slot_time TIME,
    
    -- Where
    platform platform_type NOT NULL,
    account_id INTEGER,
    
    -- What type
    slot_type content_source_type NOT NULL,
    objective slot_objective DEFAULT 'reach',
    
    -- Constraints
    required_offer_id UUID,
    required_topic_cluster UUID,
    required_format content_format_type,
    
    -- Assignment
    assigned_content_id UUID REFERENCES content_items(id),
    assigned_posting_id UUID REFERENCES postings(id),
    
    -- Status
    is_filled BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_content_slots_date ON content_slots(slot_date);
CREATE INDEX idx_content_slots_platform ON content_slots(platform);
CREATE INDEX idx_content_slots_filled ON content_slots(is_filled);

-- ============================================================================
-- H) INSIGHTS (extracted learnings from reviews)
-- ============================================================================

CREATE TYPE insight_type AS ENUM (
    'winner_pattern',
    'failure_pattern',
    'trend_opportunity',
    'timing_insight',
    'audience_insight',
    'format_insight'
);

CREATE TABLE IF NOT EXISTS insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    insight_type insight_type NOT NULL,
    
    -- What we learned
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    
    -- Scope
    platform platform_type,
    niche_id UUID,
    source_type content_source_type,
    
    -- Evidence
    supporting_postings UUID[], -- Array of posting IDs
    sample_size INTEGER,
    
    -- Confidence
    confidence_score NUMERIC(5,2),
    
    -- Actions
    recommended_actions JSONB DEFAULT '[]'::jsonb,
    
    -- Lifecycle
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_insights_type ON insights(insight_type);
CREATE INDEX idx_insights_platform ON insights(platform);
CREATE INDEX idx_insights_confidence ON insights(confidence_score DESC);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: Latest metrics for each posting
CREATE OR REPLACE VIEW v_posting_latest_metrics AS
SELECT DISTINCT ON (posting_id)
    ms.*,
    p.platform,
    p.content_item_id,
    p.posted_at
FROM metric_snapshots ms
JOIN postings p ON p.id = ms.posting_id
ORDER BY posting_id, captured_at DESC;

-- View: Posting performance summary
CREATE OR REPLACE VIEW v_posting_performance AS
SELECT 
    p.id AS posting_id,
    p.platform,
    p.posted_at,
    ci.source_type,
    ci.format_type,
    ci.title,
    lm.views,
    lm.likes,
    lm.comments,
    lm.shares,
    lm.saves,
    CASE WHEN lm.views > 0 
        THEN ROUND((lm.likes + lm.comments + lm.shares)::numeric / lm.views * 100, 2)
        ELSE 0 
    END AS engagement_rate,
    r.final_score,
    r.label,
    r.next_action
FROM postings p
JOIN content_items ci ON ci.id = p.content_item_id
LEFT JOIN v_posting_latest_metrics lm ON lm.posting_id = p.id
LEFT JOIN reviews r ON r.posting_id = p.id
WHERE p.status = 'posted';

-- View: Category performance comparison
CREATE OR REPLACE VIEW v_category_performance AS
SELECT 
    ci.source_type,
    COUNT(*) AS total_posts,
    ROUND(AVG(lm.views), 0) AS avg_views,
    ROUND(AVG(lm.likes), 0) AS avg_likes,
    ROUND(AVG(lm.shares), 0) AS avg_shares,
    ROUND(AVG(
        CASE WHEN lm.views > 0 
            THEN (lm.likes + lm.comments + lm.shares)::numeric / lm.views * 100
            ELSE 0 
        END
    ), 2) AS avg_engagement_rate,
    ROUND(AVG(r.final_score), 1) AS avg_score,
    COUNT(*) FILTER (WHERE r.label = 'winner') AS winners,
    COUNT(*) FILTER (WHERE r.label = 'loser') AS losers
FROM postings p
JOIN content_items ci ON ci.id = p.content_item_id
LEFT JOIN v_posting_latest_metrics lm ON lm.posting_id = p.id
LEFT JOIN reviews r ON r.posting_id = p.id
WHERE p.status = 'posted'
GROUP BY ci.source_type;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Schedule metric snapshots for a posting
CREATE OR REPLACE FUNCTION schedule_metric_snapshots(posting_uuid UUID)
RETURNS void AS $$
DECLARE
    p_platform platform_type;
    window RECORD;
BEGIN
    SELECT platform INTO p_platform FROM postings WHERE id = posting_uuid;
    
    FOR window IN 
        SELECT * FROM review_windows WHERE platform = p_platform AND is_active = true
    LOOP
        -- This would integrate with your job scheduler
        -- For now, just log the intention
        RAISE NOTICE 'Scheduled snapshot for posting % at window %', posting_uuid, window.name;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function: Compute derived metrics for a posting at a window
CREATE OR REPLACE FUNCTION compute_derived_metrics(posting_uuid UUID, window_uuid UUID)
RETURNS void AS $$
DECLARE
    p_platform platform_type;
    rw RECORD;
    earliest_snapshot RECORD;
    latest_snapshot RECORD;
    hours_elapsed NUMERIC;
    v_velocity NUMERIC;
    v_engagement_rate NUMERIC;
    v_share_rate NUMERIC;
    v_save_rate NUMERIC;
BEGIN
    -- Get window details
    SELECT * INTO rw FROM review_windows WHERE id = window_uuid;
    SELECT platform INTO p_platform FROM postings WHERE id = posting_uuid;
    
    -- Get snapshots in window range
    SELECT * INTO earliest_snapshot 
    FROM metric_snapshots 
    WHERE posting_id = posting_uuid AND hours_since_post >= rw.start_hour
    ORDER BY hours_since_post ASC LIMIT 1;
    
    SELECT * INTO latest_snapshot 
    FROM metric_snapshots 
    WHERE posting_id = posting_uuid AND hours_since_post <= rw.end_hour
    ORDER BY hours_since_post DESC LIMIT 1;
    
    IF earliest_snapshot IS NULL OR latest_snapshot IS NULL THEN
        RETURN;
    END IF;
    
    -- Compute metrics
    hours_elapsed := GREATEST(latest_snapshot.hours_since_post - earliest_snapshot.hours_since_post, 1);
    v_velocity := (latest_snapshot.views - COALESCE(earliest_snapshot.views, 0)) / hours_elapsed;
    v_engagement_rate := CASE WHEN latest_snapshot.views > 0 
        THEN (latest_snapshot.likes + latest_snapshot.comments + latest_snapshot.shares)::numeric / latest_snapshot.views
        ELSE 0 END;
    v_share_rate := CASE WHEN latest_snapshot.views > 0 
        THEN latest_snapshot.shares::numeric / latest_snapshot.views
        ELSE 0 END;
    v_save_rate := CASE WHEN latest_snapshot.views > 0 
        THEN latest_snapshot.saves::numeric / latest_snapshot.views
        ELSE 0 END;
    
    -- Upsert derived metrics
    INSERT INTO derived_metrics (
        posting_id, window_id, velocity_views_per_hour, 
        engagement_rate, share_rate, save_rate
    ) VALUES (
        posting_uuid, window_uuid, v_velocity,
        v_engagement_rate, v_share_rate, v_save_rate
    )
    ON CONFLICT (posting_id, window_id) DO UPDATE SET
        velocity_views_per_hour = EXCLUDED.velocity_views_per_hour,
        engagement_rate = EXCLUDED.engagement_rate,
        share_rate = EXCLUDED.share_rate,
        save_rate = EXCLUDED.save_rate,
        computed_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Auto-schedule snapshots when posting goes live
CREATE OR REPLACE FUNCTION trigger_schedule_snapshots()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'posted' AND (OLD.status IS NULL OR OLD.status != 'posted') THEN
        PERFORM schedule_metric_snapshots(NEW.id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_posting_schedule_snapshots
    AFTER INSERT OR UPDATE ON postings
    FOR EACH ROW
    EXECUTE FUNCTION trigger_schedule_snapshots();

-- ============================================================================
-- SEED DATA: Hook patterns library
-- ============================================================================

CREATE TABLE IF NOT EXISTS hook_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    pattern_template TEXT NOT NULL,
    examples TEXT[],
    best_for content_format_type[],
    avg_retention_boost NUMERIC(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO hook_patterns (name, pattern_template, examples, best_for) VALUES
    ('Controversy opener', 'Hot take or controversial statement', ARRAY['Most people are doing X wrong', 'Unpopular opinion:'], ARRAY['talking_head', 'voiceover']::content_format_type[]),
    ('Pattern interrupt', 'Unexpected visual or audio', ARRAY['*crash sound*', 'Wait, what?'], ARRAY['talking_head', 'meme']::content_format_type[]),
    ('Direct address', 'Speak directly to viewer pain point', ARRAY['If you''re struggling with X...', 'This is for the people who...'], ARRAY['talking_head', 'tutorial']::content_format_type[]),
    ('Transformation tease', 'Show end result first', ARRAY['Here''s how I went from X to Y', 'Before vs After'], ARRAY['demo', 'testimonial']::content_format_type[]),
    ('Secret reveal', 'Promise insider knowledge', ARRAY['Nobody talks about this but...', 'The thing they don''t tell you...'], ARRAY['talking_head', 'voiceover']::content_format_type[]),
    ('Number hook', 'Specific number creates curiosity', ARRAY['3 things I wish I knew...', '7 signs you''re...'], ARRAY['talking_head', 'slideshow']::content_format_type[]),
    ('Question hook', 'Open loop with question', ARRAY['Ever wonder why...?', 'What if I told you...'], ARRAY['talking_head', 'voiceover']::content_format_type[]),
    ('Story hook', 'Start mid-story', ARRAY['So there I was...', 'I can''t believe this happened...'], ARRAY['talking_head', 'voiceover']::content_format_type[])
ON CONFLICT DO NOTHING;

COMMIT;
