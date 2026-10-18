-- Trend Intelligence System v1 Schema
-- Migration: trend_intelligence_v1
-- Date: 2025-12-29

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1) WORKSPACES (if not exists)
-- ============================================
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    plan TEXT DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2) WORKSPACE_SOURCES
-- What to track per workspace
-- ============================================
CREATE TABLE IF NOT EXISTS workspace_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('tiktok', 'instagram', 'youtube', 'threads', 'twitter')),
    niche TEXT,
    seed_accounts JSONB DEFAULT '[]',
    seed_keywords JSONB DEFAULT '[]',
    seed_hashtags JSONB DEFAULT '[]',
    is_enabled BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMPTZ,
    sync_frequency_hours INTEGER DEFAULT 24,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspace_sources_workspace ON workspace_sources(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_sources_platform ON workspace_sources(platform);

-- ============================================
-- 3) POSTS_RAW
-- Normalized content across all platforms
-- ============================================
CREATE TABLE IF NOT EXISTS posts_raw (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    platform_post_id TEXT NOT NULL,
    author_handle TEXT,
    author_id TEXT,
    author_followers INTEGER,
    author_verified BOOLEAN DEFAULT false,
    posted_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    caption_text TEXT,
    hashtags JSONB DEFAULT '[]',
    mentions JSONB DEFAULT '[]',
    metrics JSONB DEFAULT '{}',  -- views, likes, comments, shares, saves
    audio_ref JSONB,  -- sound_id, title, creator
    media_type TEXT,  -- video, image, carousel
    media_urls JSONB DEFAULT '[]',
    permalink TEXT,
    language TEXT,
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, platform_post_id)
);

CREATE INDEX IF NOT EXISTS idx_posts_raw_workspace ON posts_raw(workspace_id);
CREATE INDEX IF NOT EXISTS idx_posts_raw_platform ON posts_raw(platform);
CREATE INDEX IF NOT EXISTS idx_posts_raw_posted_at ON posts_raw(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_raw_author ON posts_raw(author_handle);
CREATE INDEX IF NOT EXISTS idx_posts_raw_hashtags ON posts_raw USING GIN(hashtags);

-- ============================================
-- 4) POST_ENRICHMENT
-- Heavy add-ons (transcripts, OCR, comments)
-- ============================================
CREATE TABLE IF NOT EXISTS post_enrichment (
    post_id UUID PRIMARY KEY REFERENCES posts_raw(id) ON DELETE CASCADE,
    top_comments JSONB DEFAULT '[]',
    transcript TEXT,
    transcript_segments JSONB,  -- timestamped segments
    ocr_text TEXT,
    ocr_segments JSONB,  -- text + position + timestamp
    sentiment_score FLOAT,
    topics JSONB DEFAULT '[]',
    entities JSONB DEFAULT '[]',
    enriched_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5) TEXT_EMBEDDINGS
-- Vector embeddings for semantic search
-- ============================================
CREATE TABLE IF NOT EXISTS text_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL CHECK (source_type IN ('post', 'caption', 'comment', 'transcript', 'ocr', 'hook', 'trend')),
    source_id UUID NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 dimension
    model TEXT DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_text_embeddings_workspace ON text_embeddings(workspace_id);
CREATE INDEX IF NOT EXISTS idx_text_embeddings_source ON text_embeddings(source_type, source_id);
-- Vector similarity index (requires pgvector)
CREATE INDEX IF NOT EXISTS idx_text_embeddings_vector ON text_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================
-- 6) TREND_CLUSTERS
-- Each cluster = one emerging trend
-- ============================================
CREATE TABLE IF NOT EXISTS trend_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    cluster_type TEXT NOT NULL CHECK (cluster_type IN ('phrase', 'topic', 'sound', 'format', 'hashtag', 'hook')),
    title TEXT NOT NULL,
    description TEXT,
    centroid_embedding vector(1536),
    platform TEXT,
    niche TEXT,
    status TEXT DEFAULT 'emerging' CHECK (status IN ('emerging', 'rising', 'peak', 'declining', 'dead')),
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trend_clusters_workspace ON trend_clusters(workspace_id);
CREATE INDEX IF NOT EXISTS idx_trend_clusters_status ON trend_clusters(status);
CREATE INDEX IF NOT EXISTS idx_trend_clusters_type ON trend_clusters(cluster_type);

-- ============================================
-- 7) CLUSTER_MEMBERS
-- Posts that belong to a cluster
-- ============================================
CREATE TABLE IF NOT EXISTS cluster_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID REFERENCES trend_clusters(id) ON DELETE CASCADE,
    post_id UUID REFERENCES posts_raw(id) ON DELETE CASCADE,
    weight FLOAT DEFAULT 1.0,
    similarity_score FLOAT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(cluster_id, post_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_members_cluster ON cluster_members(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_members_post ON cluster_members(post_id);

-- ============================================
-- 8) TREND_SCORES
-- Time series velocity/engagement scores
-- ============================================
CREATE TABLE IF NOT EXISTS trend_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID REFERENCES trend_clusters(id) ON DELETE CASCADE,
    window TEXT NOT NULL CHECK (window IN ('1h', '6h', '24h', '3d', '7d', '30d')),
    mentions INTEGER DEFAULT 0,
    velocity FLOAT DEFAULT 0,  -- rate of change
    velocity_delta FLOAT DEFAULT 0,  -- acceleration
    engagement_sum BIGINT DEFAULT 0,
    engagement_p50 FLOAT DEFAULT 0,
    engagement_p90 FLOAT DEFAULT 0,
    creator_count INTEGER DEFAULT 0,
    creator_diversity FLOAT DEFAULT 0,  -- unique creators / total posts
    saturation FLOAT DEFAULT 0,  -- how crowded
    score FLOAT DEFAULT 0,  -- combined ranking score
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trend_scores_cluster ON trend_scores(cluster_id);
CREATE INDEX IF NOT EXISTS idx_trend_scores_window ON trend_scores(window);
CREATE INDEX IF NOT EXISTS idx_trend_scores_computed ON trend_scores(computed_at DESC);

-- ============================================
-- 9) CLUSTER_LINGO
-- Language patterns + meaning
-- ============================================
CREATE TABLE IF NOT EXISTS cluster_lingo (
    cluster_id UUID PRIMARY KEY REFERENCES trend_clusters(id) ON DELETE CASCADE,
    key_phrases JSONB DEFAULT '[]',  -- rising phrases
    hook_patterns JSONB DEFAULT '[]',  -- common openings
    usage_notes TEXT,  -- how to use this trend
    meaning TEXT,  -- what it means culturally
    structure JSONB,  -- setup→pivot→punchline
    tone TEXT,  -- edgy, wholesome, professional
    brand_safety_score FLOAT DEFAULT 0.5,
    brand_safety_flags JSONB DEFAULT '[]',
    example_captions JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 10) BRIEFS
-- Content-ready packs
-- ============================================
CREATE TABLE IF NOT EXISTS briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES trend_clusters(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    platform_target TEXT NOT NULL CHECK (platform_target IN ('tiktok', 'instagram', 'youtube', 'threads', 'twitter', 'all')),
    format_type TEXT,  -- reel, carousel, story, post
    tone JSONB DEFAULT '{}',  -- based, clean, professional
    hooks JSONB DEFAULT '[]',  -- 3+ hook options
    script_outline JSONB,  -- structured script
    caption_templates JSONB DEFAULT '[]',
    angles JSONB DEFAULT '[]',  -- different content angles
    shotlist JSONB DEFAULT '[]',  -- b-roll slots, on-screen text
    cta JSONB DEFAULT '{}',  -- call to action options
    must_include JSONB DEFAULT '[]',  -- required elements
    differentiation TEXT,  -- how to stand out
    brand_voice_id UUID,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'ready', 'used', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_briefs_workspace ON briefs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_briefs_cluster ON briefs(cluster_id);
CREATE INDEX IF NOT EXISTS idx_briefs_status ON briefs(status);

-- ============================================
-- 11) FORMAT_TEMPLATES
-- Remotion/Motion Canvas templates
-- ============================================
CREATE TABLE IF NOT EXISTS format_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    engine TEXT NOT NULL CHECK (engine IN ('remotion', 'motion_canvas', 'ffmpeg')),
    category TEXT,  -- explainer, listicle, hook, transition
    schema JSONB NOT NULL DEFAULT '{}',  -- expected inputs
    default_settings JSONB DEFAULT '{}',  -- fps, resolution, duration
    preview_url TEXT,
    is_public BOOLEAN DEFAULT false,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_format_templates_engine ON format_templates(engine);
CREATE INDEX IF NOT EXISTS idx_format_templates_category ON format_templates(category);

-- ============================================
-- 12) RENDER_JOBS
-- Video generation queue
-- ============================================
CREATE TABLE IF NOT EXISTS render_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    brief_id UUID REFERENCES briefs(id) ON DELETE SET NULL,
    format_template_id UUID REFERENCES format_templates(id) ON DELETE SET NULL,
    engine TEXT NOT NULL,
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    priority INTEGER DEFAULT 0,
    input_payload JSONB NOT NULL DEFAULT '{}',
    output JSONB,  -- video_url, duration, resolution, size_bytes
    error TEXT,
    progress FLOAT DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_render_jobs_workspace ON render_jobs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_render_jobs_status ON render_jobs(status);
CREATE INDEX IF NOT EXISTS idx_render_jobs_created ON render_jobs(created_at DESC);

-- ============================================
-- 13) WEBHOOK_SUBSCRIPTIONS
-- Event notifications
-- ============================================
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    event TEXT NOT NULL CHECK (event IN ('trend.emerging', 'trend.peak', 'brief.ready', 'render.done', 'render.failed')),
    target_url TEXT NOT NULL,
    secret TEXT,
    headers JSONB DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_subs_workspace ON webhook_subscriptions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subs_event ON webhook_subscriptions(event);

-- ============================================
-- 14) PIPELINE_RUNS
-- Track worker executions
-- ============================================
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    pipeline_type TEXT NOT NULL,  -- ingest, enrich, embed, cluster, score, lingo, brief
    source_id UUID,  -- workspace_source_id or cluster_id
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'succeeded', 'failed')),
    items_processed INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_workspace ON pipeline_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_type ON pipeline_runs(pipeline_type);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON pipeline_runs(started_at DESC);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to relevant tables
DROP TRIGGER IF EXISTS update_workspaces_updated_at ON workspaces;
CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_workspace_sources_updated_at ON workspace_sources;
CREATE TRIGGER update_workspace_sources_updated_at BEFORE UPDATE ON workspace_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_trend_clusters_updated_at ON trend_clusters;
CREATE TRIGGER update_trend_clusters_updated_at BEFORE UPDATE ON trend_clusters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_briefs_updated_at ON briefs;
CREATE TRIGGER update_briefs_updated_at BEFORE UPDATE ON briefs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_format_templates_updated_at ON format_templates;
CREATE TRIGGER update_format_templates_updated_at BEFORE UPDATE ON format_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- SEED DATA
-- ============================================

-- Default workspace
INSERT INTO workspaces (id, name, plan) 
VALUES ('00000000-0000-0000-0000-000000000001', 'Default Workspace', 'pro')
ON CONFLICT DO NOTHING;

-- Sample format templates
INSERT INTO format_templates (id, name, engine, category, schema, default_settings) VALUES
('00000000-0000-0000-0000-000000000101', 'Explainer v1', 'remotion', 'explainer', 
 '{"title": "string", "bullets": "array", "on_screen_text": "array", "voiceover_script": "string", "broll": "array", "music": "object"}',
 '{"duration_sec": 22, "fps": 30, "resolution": "1080x1920"}'),
('00000000-0000-0000-0000-000000000102', 'Hook + List', 'remotion', 'listicle',
 '{"hook": "string", "items": "array", "cta": "string"}',
 '{"duration_sec": 15, "fps": 30, "resolution": "1080x1920"}'),
('00000000-0000-0000-0000-000000000103', 'B-Roll + Text Overlay', 'ffmpeg', 'broll',
 '{"video_id": "string", "text_overlays": "array", "music": "object"}',
 '{"duration_sec": 30, "fps": 30, "resolution": "1080x1920"}'
)
ON CONFLICT DO NOTHING;

COMMIT;
