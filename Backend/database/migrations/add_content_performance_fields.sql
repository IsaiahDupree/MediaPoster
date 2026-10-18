-- Migration: Add content performance tracking fields
-- Created: 2025-12-20
-- Purpose: Support ideal Content Performance page spec (YouTube Studio + Instagram Insights style)

-- ============================================================================
-- ORGANIC METRICS
-- ============================================================================

-- Video/Content metrics
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS watch_time_seconds INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS avg_view_duration FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS avg_percent_viewed FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS completion_rate FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS hook_rate FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS video_duration_seconds INTEGER DEFAULT 0;

-- Distribution metrics
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS reach INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS impressions INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS follows_from_post INTEGER DEFAULT 0;

-- Content metadata
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS creative_tags TEXT[];
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS content_type TEXT; -- 'video', 'image', 'carousel', 'reel', 'short', 'story'
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS length_bucket TEXT; -- 'short' (<15s), 'medium' (15-60s), 'long' (>60s)

-- ============================================================================
-- PAID METRICS
-- ============================================================================

ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT FALSE;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS ad_id TEXT;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS ad_set_id TEXT;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS campaign_id TEXT;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS campaign_objective TEXT; -- 'awareness', 'traffic', 'leads', 'purchases'

-- Spend and efficiency
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS spend DECIMAL(10,2) DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS clicks INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS link_clicks INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS cpm DECIMAL(10,4) DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS cpc DECIMAL(10,4) DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS ctr FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS frequency FLOAT DEFAULT 0;

-- Conversion tracking
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS conversions INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS conversion_value DECIMAL(10,2) DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS cpa DECIMAL(10,4) DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS roas FLOAT DEFAULT 0;

-- Video ad metrics
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS thruplays INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS cost_per_thruplay DECIMAL(10,4) DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS three_second_views INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS thumbstop_rate FLOAT DEFAULT 0;

-- ============================================================================
-- CREATIVE ASSET LINKING (for "One Creative → Many Distributions")
-- ============================================================================

-- Link to the original creative asset (media file)
-- media_id already exists, but add creative_asset_id for grouping
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS creative_asset_id UUID;

-- Create creative_assets table for the "one creative" concept
CREATE TABLE IF NOT EXISTS creative_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source file
    media_id UUID,
    file_path TEXT,
    thumbnail_url TEXT,
    
    -- Creative metadata
    title TEXT,
    hook_text TEXT, -- First line or hook
    creative_tags TEXT[],
    content_type TEXT, -- 'video', 'image', 'carousel'
    duration_seconds INTEGER,
    length_bucket TEXT,
    
    -- Aggregated organic metrics (rollup from posts)
    total_organic_views INTEGER DEFAULT 0,
    total_organic_likes INTEGER DEFAULT 0,
    total_organic_shares INTEGER DEFAULT 0,
    total_organic_saves INTEGER DEFAULT 0,
    avg_organic_completion_rate FLOAT DEFAULT 0,
    avg_organic_hook_rate FLOAT DEFAULT 0,
    
    -- Aggregated paid metrics (rollup from ad instances)
    total_paid_spend DECIMAL(10,2) DEFAULT 0,
    total_paid_impressions INTEGER DEFAULT 0,
    total_paid_clicks INTEGER DEFAULT 0,
    total_paid_conversions INTEGER DEFAULT 0,
    avg_paid_cpm DECIMAL(10,4) DEFAULT 0,
    avg_paid_cpa DECIMAL(10,4) DEFAULT 0,
    avg_paid_roas FLOAT DEFAULT 0,
    
    -- Scoring
    creative_quality_score FLOAT DEFAULT 0,
    paid_efficiency_score FLOAT DEFAULT 0,
    decision_label TEXT, -- 'scale', 'iterate', 'retarget', 'pause'
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for creative grouping
CREATE INDEX IF NOT EXISTS idx_posted_content_creative_asset_id ON posted_content(creative_asset_id);
CREATE INDEX IF NOT EXISTS idx_creative_assets_media_id ON creative_assets(media_id);
CREATE INDEX IF NOT EXISTS idx_posted_content_is_paid ON posted_content(is_paid);
CREATE INDEX IF NOT EXISTS idx_posted_content_campaign_id ON posted_content(campaign_id);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON COLUMN posted_content.hook_rate IS 'Percentage of viewers who watched past first 1-3 seconds';
COMMENT ON COLUMN posted_content.avg_percent_viewed IS 'Average percentage of video watched';
COMMENT ON COLUMN posted_content.completion_rate IS 'Percentage of viewers who watched to the end';
COMMENT ON COLUMN posted_content.thumbstop_rate IS 'Percentage who stopped scrolling (3-sec view rate for ads)';
COMMENT ON COLUMN posted_content.creative_asset_id IS 'Links to creative_assets for "one creative → many distributions" rollup';
COMMENT ON TABLE creative_assets IS 'Aggregates metrics across all organic posts and paid ads using the same creative';
