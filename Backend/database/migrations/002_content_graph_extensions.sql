-- Content Graph Extensions  
-- Migration: 002_content_graph_extensions
-- Created: 2025-01-21
-- Note: content_items, content_variants, content_metrics already exist

-- =====================================================
-- CONTENT ROLLUPS: Aggregated cross-platform metrics
-- =====================================================

CREATE TABLE IF NOT EXISTS content_rollups (
  content_id UUID PRIMARY KEY REFERENCES content_items(id) ON DELETE CASCADE,
  total_views BIGINT DEFAULT 0,
  total_impressions BIGINT DEFAULT 0,
  total_likes BIGINT DEFAULT 0,
  total_comments BIGINT DEFAULT 0,
  total_shares BIGINT DEFAULT 0,
  total_saves BIGINT DEFAULT 0,
  total_clicks BIGINT DEFAULT 0,
  avg_watch_time_seconds NUMERIC,
  global_sentiment NUMERIC CHECK (global_sentiment >= -1 AND global_sentiment <= 1),
  best_platform TEXT,
  last_updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rollups_platform ON content_rollups(best_platform);
CREATE INDEX IF NOT EXISTS idx_rollups_updated ON content_rollups(last_updated_at DESC);

-- =====================================================
-- CONTENT EXPERIMENTS: A/B/multivariate testing
-- =====================================================

CREATE TABLE IF NOT EXISTS content_experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  hypothesis TEXT,
  primary_metric TEXT,
  status TEXT CHECK (status IN ('draft','running','completed','cancelled')) DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_experiments_content ON content_experiments(content_id);
CREATE INDEX IF NOT EXISTS idx_experiments_status ON content_experiments(status);

-- =====================================================
-- Update content_metrics if needed (add traffic_type)
-- =====================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name='content_metrics' AND column_name='traffic_type'
  ) THEN
    ALTER TABLE content_metrics 
    ADD COLUMN traffic_type TEXT CHECK (traffic_type IN ('organic','paid')) DEFAULT 'organic';
    
    CREATE INDEX idx_metrics_traffic ON content_metrics(traffic_type);
  END IF;
END $$;

-- =====================================================
-- Enable RLS
-- =====================================================

ALTER TABLE content_rollups ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_experiments ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- Comments
-- =====================================================

COMMENT ON TABLE content_rollups IS 'Nightly aggregated metrics per content ID (cross-platform)';
COMMENT ON TABLE content_experiments IS 'A/B/multivariate testing framework';
