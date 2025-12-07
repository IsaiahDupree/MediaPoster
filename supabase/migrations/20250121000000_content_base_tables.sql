-- Content Base Tables
-- Migration: 000_content_base_tables
-- Created: 2025-01-21
-- Creates the base content tables that other migrations depend on

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- content_items
CREATE TABLE IF NOT EXISTS content_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE,
  type TEXT CHECK (type IN ('video','article','audio','image','carousel')),
  source_url TEXT,
  title TEXT,
  description TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_items_created ON content_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_items_creator ON content_items(created_by);

-- content_variants
CREATE TABLE IF NOT EXISTS content_variants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
  platform TEXT CHECK (platform IN (
    'instagram','tiktok','youtube','linkedin','twitter','facebook',
    'pinterest','threads','bluesky','other'
  )),
  platform_post_id TEXT,
  platform_post_url TEXT,
  title TEXT,
  description TEXT,
  thumbnail_url TEXT,
  scheduled_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  is_paid BOOLEAN DEFAULT FALSE,
  experiment_id UUID,
  variant_label TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_variants_content ON content_variants(content_id);
CREATE INDEX IF NOT EXISTS idx_variants_platform ON content_variants(platform, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_variants_experiment ON content_variants(experiment_id);

-- content_metrics
CREATE TABLE IF NOT EXISTS content_metrics (
  id BIGSERIAL PRIMARY KEY,
  variant_id UUID REFERENCES content_variants(id) ON DELETE CASCADE,
  snapshot_at TIMESTAMPTZ DEFAULT NOW(),
  views BIGINT,
  impressions BIGINT,
  reach BIGINT,
  likes BIGINT,
  comments BIGINT,
  shares BIGINT,
  saves BIGINT,
  clicks BIGINT,
  watch_time_seconds BIGINT,
  sentiment_score NUMERIC CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
  traffic_type TEXT CHECK (traffic_type IN ('organic','paid')) DEFAULT 'organic',
  metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_metrics_variant ON content_metrics(variant_id, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_traffic ON content_metrics(traffic_type);

-- Enable RLS
ALTER TABLE content_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_metrics ENABLE ROW LEVEL SECURITY;

-- Comments
COMMENT ON TABLE content_items IS 'Canonical content assets (Video, Article) with a global ID';
COMMENT ON TABLE content_variants IS 'Platform-specific executions of a content item';
COMMENT ON TABLE content_metrics IS 'Time-series snapshots of performance';

