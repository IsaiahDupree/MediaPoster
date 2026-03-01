-- ACTP Database Schema
-- Ad Creative Testing Pipeline tables

-- Campaign status enum
DO $$ BEGIN
    CREATE TYPE actp_campaign_status AS ENUM (
        'draft', 'generating', 'organic_testing', 'ad_testing',
        'iterating', 'scaling', 'paused', 'completed', 'failed'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Round type enum
DO $$ BEGIN
    CREATE TYPE actp_round_type AS ENUM ('organic', 'ad', 'scale');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Round status enum
DO $$ BEGIN
    CREATE TYPE actp_round_status AS ENUM (
        'pending', 'generating', 'publishing', 'waiting',
        'collecting', 'selecting', 'deploying', 'completed', 'failed'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Generation source enum
DO $$ BEGIN
    CREATE TYPE actp_generation_source AS ENUM (
        'sora', 'veo3', 'nano_banana', 'remotion', 'remix'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Platform enum
DO $$ BEGIN
    CREATE TYPE actp_platform AS ENUM (
        'youtube_shorts', 'tiktok', 'instagram_reels',
        'meta', 'tiktok_ads', 'youtube_ads'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Ad deployment status enum
DO $$ BEGIN
    CREATE TYPE actp_ad_status AS ENUM (
        'pending', 'active', 'paused', 'completed', 'failed'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ─── Test Campaigns ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS actp_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    offer_id TEXT,
    offer_name TEXT,
    offer_url TEXT,
    status actp_campaign_status NOT NULL DEFAULT 'draft',
    config JSONB NOT NULL DEFAULT '{}',
    angles JSONB NOT NULL DEFAULT '[]',
    target_audience JSONB,
    mode TEXT NOT NULL DEFAULT 'offer',
    total_spend_cents INTEGER NOT NULL DEFAULT 0,
    total_creatives INTEGER NOT NULL DEFAULT 0,
    total_rounds INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_actp_campaigns_status ON actp_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_actp_campaigns_created ON actp_campaigns(created_at DESC);

-- ─── Test Rounds ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS actp_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES actp_campaigns(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    round_type actp_round_type NOT NULL,
    status actp_round_status NOT NULL DEFAULT 'pending',
    budget_per_creative_cents INTEGER NOT NULL DEFAULT 0,
    total_budget_cents INTEGER NOT NULL DEFAULT 0,
    total_spend_cents INTEGER NOT NULL DEFAULT 0,
    config JSONB NOT NULL DEFAULT '{}',
    started_at TIMESTAMPTZ,
    wait_until TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(campaign_id, round_number)
);

CREATE INDEX IF NOT EXISTS idx_actp_rounds_campaign ON actp_rounds(campaign_id);
CREATE INDEX IF NOT EXISTS idx_actp_rounds_status ON actp_rounds(status);

-- ─── Creatives ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS actp_creatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES actp_campaigns(id) ON DELETE CASCADE,
    round_id UUID NOT NULL REFERENCES actp_rounds(id) ON DELETE CASCADE,
    parent_creative_id UUID REFERENCES actp_creatives(id) ON DELETE SET NULL,
    video_url TEXT,
    thumbnail_url TEXT,
    hook TEXT,
    cta TEXT,
    angle TEXT,
    script TEXT,
    target_audience TEXT,
    generation_source actp_generation_source NOT NULL DEFAULT 'sora',
    generation_metadata JSONB NOT NULL DEFAULT '{}',
    organic_score FLOAT,
    ad_score FLOAT,
    is_winner BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actp_creatives_campaign ON actp_creatives(campaign_id);
CREATE INDEX IF NOT EXISTS idx_actp_creatives_round ON actp_creatives(round_id);
CREATE INDEX IF NOT EXISTS idx_actp_creatives_parent ON actp_creatives(parent_creative_id);
CREATE INDEX IF NOT EXISTS idx_actp_creatives_winner ON actp_creatives(is_winner) WHERE is_winner = TRUE;

-- ─── Organic Posts ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS actp_organic_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creative_id UUID NOT NULL REFERENCES actp_creatives(id) ON DELETE CASCADE,
    platform actp_platform NOT NULL,
    post_id TEXT,
    post_url TEXT,
    posted_at TIMESTAMPTZ,
    metrics JSONB NOT NULL DEFAULT '{}',
    organic_score FLOAT,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actp_organic_creative ON actp_organic_posts(creative_id);
CREATE INDEX IF NOT EXISTS idx_actp_organic_platform ON actp_organic_posts(platform);

-- ─── Ad Deployments ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS actp_ad_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creative_id UUID NOT NULL REFERENCES actp_creatives(id) ON DELETE CASCADE,
    round_id UUID NOT NULL REFERENCES actp_rounds(id) ON DELETE CASCADE,
    platform actp_platform NOT NULL,
    external_campaign_id TEXT,
    external_ad_set_id TEXT,
    external_ad_id TEXT,
    budget_cents INTEGER NOT NULL DEFAULT 0,
    spend_cents INTEGER NOT NULL DEFAULT 0,
    metrics JSONB NOT NULL DEFAULT '{}',
    ad_score FLOAT,
    status actp_ad_status NOT NULL DEFAULT 'pending',
    landing_page_url TEXT,
    audience_config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actp_ads_creative ON actp_ad_deployments(creative_id);
CREATE INDEX IF NOT EXISTS idx_actp_ads_round ON actp_ad_deployments(round_id);
CREATE INDEX IF NOT EXISTS idx_actp_ads_status ON actp_ad_deployments(status);

-- ─── Performance Logs ────────────────────────────────────

CREATE TABLE IF NOT EXISTS actp_performance_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creative_id UUID NOT NULL REFERENCES actp_creatives(id) ON DELETE CASCADE,
    round_id UUID NOT NULL REFERENCES actp_rounds(id) ON DELETE CASCADE,
    metric_type TEXT NOT NULL,
    value FLOAT NOT NULL,
    platform actp_platform NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_data JSONB
);

CREATE INDEX IF NOT EXISTS idx_actp_perf_creative ON actp_performance_logs(creative_id);
CREATE INDEX IF NOT EXISTS idx_actp_perf_round ON actp_performance_logs(round_id);
CREATE INDEX IF NOT EXISTS idx_actp_perf_measured ON actp_performance_logs(measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_actp_perf_type ON actp_performance_logs(metric_type);

-- ─── Winner Selections ───────────────────────────────────

CREATE TABLE IF NOT EXISTS actp_winner_selections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES actp_rounds(id) ON DELETE CASCADE,
    creative_id UUID NOT NULL REFERENCES actp_creatives(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    score FLOAT NOT NULL,
    selection_reason TEXT NOT NULL,
    promoted_to_round_id UUID REFERENCES actp_rounds(id) ON DELETE SET NULL,
    selected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actp_winners_round ON actp_winner_selections(round_id);
CREATE INDEX IF NOT EXISTS idx_actp_winners_creative ON actp_winner_selections(creative_id);

-- ─── Updated At Trigger ──────────────────────────────────

CREATE OR REPLACE FUNCTION actp_update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS actp_campaigns_updated ON actp_campaigns;
CREATE TRIGGER actp_campaigns_updated
    BEFORE UPDATE ON actp_campaigns
    FOR EACH ROW EXECUTE FUNCTION actp_update_updated_at();

DROP TRIGGER IF EXISTS actp_ads_updated ON actp_ad_deployments;
CREATE TRIGGER actp_ads_updated
    BEFORE UPDATE ON actp_ad_deployments
    FOR EACH ROW EXECUTE FUNCTION actp_update_updated_at();

-- ─── RLS Policies ────────────────────────────────────────

ALTER TABLE actp_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_creatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_organic_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_ad_deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_performance_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_winner_selections ENABLE ROW LEVEL SECURITY;

-- Service role has full access (backend API)
CREATE POLICY IF NOT EXISTS actp_campaigns_service ON actp_campaigns FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS actp_rounds_service ON actp_rounds FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS actp_creatives_service ON actp_creatives FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS actp_organic_service ON actp_organic_posts FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS actp_ads_service ON actp_ad_deployments FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS actp_perf_service ON actp_performance_logs FOR ALL USING (true);
CREATE POLICY IF NOT EXISTS actp_winners_service ON actp_winner_selections FOR ALL USING (true);
