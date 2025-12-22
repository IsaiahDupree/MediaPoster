-- =============================================================================
-- NARRATIVE BUILDER DATA MODEL
-- 3-Level Mapping: Creative Asset → Variants → Distribution Instances
-- =============================================================================

-- =============================================================================
-- 1. CREATIVE ASSETS (Enhanced - using existing videos + video_analysis)
-- =============================================================================

-- Add missing columns to video_analysis for complete hydration
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS detected_hook TEXT,
ADD COLUMN IF NOT EXISTS detected_cta TEXT,
ADD COLUMN IF NOT EXISTS pillar_tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS format_tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS hook_type TEXT,
ADD COLUMN IF NOT EXISTS cta_type TEXT;

-- Create rollup metrics for creative assets
CREATE TABLE IF NOT EXISTS creative_asset_metrics (
    video_id UUID PRIMARY KEY REFERENCES videos(id),
    
    -- Aggregated retention metrics (from all distributions)
    avg_hook_rate_3s NUMERIC(5,2),
    avg_view_duration NUMERIC(8,2),
    avg_percent_viewed NUMERIC(5,2),
    avg_completion_rate NUMERIC(5,2),
    
    -- Aggregated engagement metrics
    avg_share_rate NUMERIC(8,6),
    avg_save_rate NUMERIC(8,6),
    avg_comment_rate NUMERIC(8,6),
    avg_follow_rate NUMERIC(8,6),
    
    -- Fatigue tracking
    total_posts INTEGER DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    last_posted_at TIMESTAMPTZ,
    performance_decay_rate NUMERIC(5,2),
    
    -- Sentiment rollup
    avg_sentiment_score NUMERIC(3,2),  -- -1 to +1
    sentiment_themes TEXT[] DEFAULT '{}',
    high_intent_comment_rate NUMERIC(5,2),
    
    -- Timestamps
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 2. CREATIVE VARIANTS (Enhanced - add to existing content_variants)
-- =============================================================================

ALTER TABLE content_variants
ADD COLUMN IF NOT EXISTS edit_type TEXT,  -- 'original', 'hook_swap', 'caption_swap', 'trim', 'crop'
ADD COLUMN IF NOT EXISTS hook_text TEXT,
ADD COLUMN IF NOT EXISTS cta_text TEXT,
ADD COLUMN IF NOT EXISTS caption_text TEXT,
ADD COLUMN IF NOT EXISTS length_bucket TEXT,  -- 'short', 'medium', 'long'
ADD COLUMN IF NOT EXISTS aspect_ratio TEXT,
ADD COLUMN IF NOT EXISTS platform_optimized_for TEXT,
ADD COLUMN IF NOT EXISTS ab_test_group TEXT;

-- Variant-level metrics rollup
CREATE TABLE IF NOT EXISTS variant_metrics (
    variant_id UUID PRIMARY KEY REFERENCES content_variants(id),
    
    -- Retention metrics
    hook_rate_3s NUMERIC(5,2),
    avg_view_duration NUMERIC(8,2),
    avg_percent_viewed NUMERIC(5,2),
    completion_rate NUMERIC(5,2),
    
    -- Engagement rates (normalized per view)
    share_rate NUMERIC(8,6),
    save_rate NUMERIC(8,6),
    comment_rate NUMERIC(8,6),
    follow_rate NUMERIC(8,6),
    profile_visit_rate NUMERIC(8,6),
    
    -- Performance tracking
    total_organic_posts INTEGER DEFAULT 0,
    total_ad_instances INTEGER DEFAULT 0,
    total_impressions BIGINT DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    
    -- Sentiment
    sentiment_score NUMERIC(3,2),
    sentiment_themes TEXT[] DEFAULT '{}',
    
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 3. DISTRIBUTION INSTANCES
-- =============================================================================

-- A) POST INSTANCES (Organic) - Enhance existing posted_content
ALTER TABLE posted_content
ADD COLUMN IF NOT EXISTS variant_id UUID REFERENCES content_variants(id),
ADD COLUMN IF NOT EXISTS hook_rate_3s NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS avg_view_duration NUMERIC(8,2),
ADD COLUMN IF NOT EXISTS avg_percent_viewed NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS completion_rate NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS share_rate NUMERIC(8,6),
ADD COLUMN IF NOT EXISTS save_rate NUMERIC(8,6),
ADD COLUMN IF NOT EXISTS comment_rate NUMERIC(8,6),
ADD COLUMN IF NOT EXISTS follow_rate NUMERIC(8,6),
ADD COLUMN IF NOT EXISTS sentiment_score NUMERIC(3,2),
ADD COLUMN IF NOT EXISTS sentiment_themes TEXT[] DEFAULT '{}';

-- B) AD INSTANCES (Paid)
CREATE TABLE IF NOT EXISTS ad_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id UUID REFERENCES content_variants(id),
    video_id UUID REFERENCES videos(id),
    
    -- Platform info
    platform TEXT NOT NULL,  -- 'meta', 'tiktok', 'google', 'youtube'
    ad_account_id TEXT,
    campaign_id TEXT,
    adset_id TEXT,
    ad_id TEXT,
    
    -- Timeline
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active',  -- 'active', 'paused', 'completed'
    
    -- Spend metrics
    spend NUMERIC(12,2) DEFAULT 0,
    impressions BIGINT DEFAULT 0,
    
    -- Normalized metrics
    cpm NUMERIC(8,2),
    cpc NUMERIC(8,4),
    ctr NUMERIC(8,4),
    cpa NUMERIC(10,2),
    roas NUMERIC(8,2),
    frequency NUMERIC(6,2),
    
    -- Retention (paid)
    hook_rate_3s NUMERIC(5,2),
    avg_view_duration NUMERIC(8,2),
    avg_percent_viewed NUMERIC(5,2),
    cost_per_thruplay NUMERIC(8,4),
    
    -- Conversions
    conversions INTEGER DEFAULT 0,
    conversion_value NUMERIC(12,2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 4. SENTIMENT HYDRATION
-- =============================================================================

CREATE TABLE IF NOT EXISTS content_sentiment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Links (one of these should be set)
    post_instance_id UUID REFERENCES posted_content(id),
    ad_instance_id UUID REFERENCES ad_instances(id),
    video_id UUID REFERENCES videos(id),
    
    -- Sentiment metrics
    sentiment_score NUMERIC(3,2),  -- -1 to +1
    positive_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    
    -- Theme extraction
    themes TEXT[] DEFAULT '{}',  -- ['objection', 'confusion', 'praise', 'feature_request', 'price_question']
    top_questions TEXT[] DEFAULT '{}',
    
    -- High-intent tracking
    high_intent_comments INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    high_intent_rate NUMERIC(5,2),
    
    -- Timestamps
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT one_source CHECK (
        (post_instance_id IS NOT NULL)::int + 
        (ad_instance_id IS NOT NULL)::int + 
        (video_id IS NOT NULL)::int = 1
    )
);

-- =============================================================================
-- 5. NARRATIVE BUILDER STATE
-- =============================================================================

CREATE TABLE IF NOT EXISTS narrative_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    
    -- Goal definition
    goal_text TEXT NOT NULL,
    cta_type TEXT,  -- 'subscribe', 'waitlist', 'dm_keyword', 'click', 'purchase'
    
    -- Pillar configuration
    pillar_tags TEXT[] DEFAULT '{}',
    pillar_mix JSONB DEFAULT '{}',  -- {"value": 60, "proof": 20, "cta": 20}
    
    -- Audience
    audience_description TEXT,
    awareness_level TEXT,  -- 'cold', 'warm', 'hot'
    
    -- Constraints
    platforms TEXT[] DEFAULT '{}',
    max_posts_per_day INTEGER DEFAULT 3,
    cooldown_days INTEGER DEFAULT 7,
    banned_topics TEXT[] DEFAULT '{}',
    
    -- Time horizon
    time_horizon TEXT DEFAULT '7days',  -- 'today', '7days', '30days'
    
    -- Mode
    optimization_mode TEXT DEFAULT 'organic',  -- 'organic', 'paid', 'hybrid'
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 6. INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_creative_asset_metrics_video ON creative_asset_metrics(video_id);
CREATE INDEX IF NOT EXISTS idx_variant_metrics_variant ON variant_metrics(variant_id);
CREATE INDEX IF NOT EXISTS idx_posted_content_variant ON posted_content(variant_id);
CREATE INDEX IF NOT EXISTS idx_posted_content_media ON posted_content(media_id);
CREATE INDEX IF NOT EXISTS idx_ad_instances_variant ON ad_instances(variant_id);
CREATE INDEX IF NOT EXISTS idx_ad_instances_video ON ad_instances(video_id);
CREATE INDEX IF NOT EXISTS idx_ad_instances_platform ON ad_instances(platform);
CREATE INDEX IF NOT EXISTS idx_content_sentiment_post ON content_sentiment(post_instance_id);
CREATE INDEX IF NOT EXISTS idx_content_sentiment_video ON content_sentiment(video_id);
CREATE INDEX IF NOT EXISTS idx_narrative_goals_user ON narrative_goals(user_id);

-- =============================================================================
-- 7. VIEWS FOR NARRATIVE BUILDER
-- =============================================================================

CREATE OR REPLACE VIEW narrative_candidates AS
SELECT 
    v.id as video_id,
    v.file_name as title,
    v.duration_sec,
    v.aspect_ratio,
    v.thumbnail_path,
    va.transcript,
    va.hooks,
    va.topics as topic_tags,
    va.pillar_tags,
    va.tone,
    va.pacing,
    va.pre_social_score as base_score,
    va.curation_status,
    COALESCE(cam.total_posts, 0) as total_posts,
    COALESCE(cam.total_views, 0) as total_views,
    cam.last_posted_at,
    cam.avg_sentiment_score,
    cam.performance_decay_rate,
    -- Calculate freshness score (100 = never posted, decays with posts)
    CASE 
        WHEN COALESCE(cam.total_posts, 0) = 0 THEN 100
        WHEN COALESCE(cam.total_posts, 0) = 1 THEN 80
        WHEN COALESCE(cam.total_posts, 0) = 2 THEN 60
        WHEN COALESCE(cam.total_posts, 0) = 3 THEN 40
        ELSE 20
    END as novelty_score,
    -- Days since last post
    EXTRACT(EPOCH FROM (NOW() - cam.last_posted_at)) / 86400 as days_since_posted
FROM videos v
INNER JOIN video_analysis va ON v.id = va.video_id
LEFT JOIN creative_asset_metrics cam ON v.id = cam.video_id
WHERE va.pre_social_score IS NOT NULL;
