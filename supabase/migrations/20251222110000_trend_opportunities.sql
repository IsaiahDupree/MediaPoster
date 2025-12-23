-- =============================================================================
-- TREND OPPORTUNITIES - Integration with Narrative Builder & Experiments
-- =============================================================================
-- This migration adds trend analysis as an input stream to decision engines.
-- Trends act as "opportunity signals" that trigger:
-- - New narrative slots (what to post)
-- - Experiment hypotheses (what to test)
-- - Scheduling priority changes (when to post)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. TREND RAW DATA (per provider)
-- -----------------------------------------------------------------------------
-- Raw API responses from trend providers (TikTok, Instagram, App Store, etc.)

CREATE TABLE IF NOT EXISTS trend_raw (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Provider info
  provider VARCHAR(50) NOT NULL, -- 'tiktok', 'instagram', 'appstore', 'playstore', 'rapidapi_tiktok', etc.
  endpoint VARCHAR(255), -- API endpoint called
  region VARCHAR(10) DEFAULT 'US',
  
  -- Raw data
  payload JSONB NOT NULL,
  
  -- Metadata
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  processing_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processed', 'failed'
  processed_at TIMESTAMPTZ,
  error_message TEXT,
  
  -- Retention
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days')
);

CREATE INDEX IF NOT EXISTS idx_trend_raw_provider ON trend_raw(provider);
CREATE INDEX IF NOT EXISTS idx_trend_raw_fetched ON trend_raw(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_raw_status ON trend_raw(processing_status);

-- -----------------------------------------------------------------------------
-- 2. TREND ITEMS (Canonical normalized schema)
-- -----------------------------------------------------------------------------
-- Normalized trend data regardless of source

CREATE TABLE IF NOT EXISTS trend_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Identity
  source VARCHAR(50) NOT NULL, -- 'tiktok', 'instagram', 'youtube', 'appstore', 'playstore', 'twitter'
  entity_type VARCHAR(50) NOT NULL, -- 'topic', 'keyword', 'sound', 'hashtag', 'creator', 'app', 'category'
  entity_id VARCHAR(255) NOT NULL, -- Platform-specific ID
  entity_key VARCHAR(255) NOT NULL, -- Normalized key for deduplication
  display_name VARCHAR(500),
  
  -- Location/Context
  region VARCHAR(10) DEFAULT 'US',
  language VARCHAR(10) DEFAULT 'en',
  platform VARCHAR(50), -- May differ from source (e.g., source=rapidapi, platform=tiktok)
  
  -- Time bucket
  timestamp_bucket TIMESTAMPTZ NOT NULL, -- Hour or day bucket
  bucket_type VARCHAR(10) DEFAULT 'hour', -- 'hour', 'day'
  
  -- Metrics (stored as JSONB for flexibility)
  metrics JSONB DEFAULT '{}'::jsonb,
  -- Contains: velocity, acceleration, rank, rank_delta, volume, engagement_proxy
  
  -- Computed scores
  velocity DECIMAL(10,4), -- Slope of growth
  acceleration DECIMAL(10,4), -- Change in slope
  rank INTEGER,
  rank_delta INTEGER, -- Change from previous bucket
  volume BIGINT, -- Views/search volume proxy
  engagement_proxy DECIMAL(10,4),
  
  -- Context (examples, related items)
  context JSONB DEFAULT '{}'::jsonb,
  -- Contains: top_posts, associated_tags, inferred_intent
  
  -- Raw source reference
  raw_id UUID REFERENCES trend_raw(id),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Unique constraint to prevent duplicates
  UNIQUE(source, entity_type, entity_key, timestamp_bucket)
);

CREATE INDEX IF NOT EXISTS idx_trend_items_source ON trend_items(source, entity_type);
CREATE INDEX IF NOT EXISTS idx_trend_items_key ON trend_items(entity_key);
CREATE INDEX IF NOT EXISTS idx_trend_items_bucket ON trend_items(timestamp_bucket DESC);
CREATE INDEX IF NOT EXISTS idx_trend_items_velocity ON trend_items(velocity DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_trend_items_metrics ON trend_items USING gin(metrics);

-- -----------------------------------------------------------------------------
-- 3. TREND CLUSTERS (Grouped similar trends)
-- -----------------------------------------------------------------------------
-- Deduplicated and clustered trends using embeddings

CREATE TABLE IF NOT EXISTS trend_clusters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Cluster info
  label VARCHAR(255), -- Human-readable cluster name
  description TEXT,
  
  -- Embedding for similarity matching
  embedding VECTOR(1536), -- OpenAI ada-002 dimension, adjust as needed
  embedding_model VARCHAR(50) DEFAULT 'text-embedding-ada-002',
  
  -- Member entities
  top_entities JSONB DEFAULT '[]'::jsonb, -- Top trend items in this cluster
  entity_count INTEGER DEFAULT 0,
  
  -- Aggregate metrics
  avg_velocity DECIMAL(10,4),
  max_velocity DECIMAL(10,4),
  total_volume BIGINT,
  
  -- Cross-surface detection
  platforms TEXT[] DEFAULT '{}', -- Which platforms this cluster spans
  is_cross_surface BOOLEAN DEFAULT FALSE, -- True if spans social + app store
  
  -- Timestamps
  first_seen TIMESTAMPTZ DEFAULT NOW(),
  last_updated TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days')
);

CREATE INDEX IF NOT EXISTS idx_trend_clusters_label ON trend_clusters(label);
CREATE INDEX IF NOT EXISTS idx_trend_clusters_velocity ON trend_clusters(max_velocity DESC NULLS LAST);
-- Vector index for similarity search (requires pgvector extension)
-- CREATE INDEX IF NOT EXISTS idx_trend_clusters_embedding ON trend_clusters USING ivfflat (embedding vector_cosine_ops);

-- -----------------------------------------------------------------------------
-- 4. TREND OPPORTUNITIES (Actionable scored opportunities)
-- -----------------------------------------------------------------------------
-- The output of the Trend Engine - scored opportunities for action

CREATE TABLE IF NOT EXISTS trend_opportunities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  
  -- Link to cluster
  cluster_id UUID REFERENCES trend_clusters(id),
  
  -- Opportunity details
  title VARCHAR(500),
  description TEXT,
  
  -- Scoring (OpportunityScore formula)
  opportunity_score DECIMAL(5,2), -- 0-100 composite score
  
  -- Score components
  velocity_score DECIMAL(5,2), -- 0-100
  acceleration_score DECIMAL(5,2), -- 0-100
  relevance_to_brand DECIMAL(5,2), -- 0-100 (embedding similarity to brand pillars)
  content_fit DECIMAL(5,2), -- 0-100 (do you have matching assets?)
  monetization_fit DECIMAL(5,2), -- 0-100 (alignment to offers/keywords)
  
  -- Penalties
  fatigue_penalty DECIMAL(5,2) DEFAULT 0, -- Already posted similar content
  competition_penalty DECIMAL(5,2) DEFAULT 0, -- Many competitors on this
  risk_penalty DECIMAL(5,2) DEFAULT 0, -- Brand safety concerns
  
  -- Why this is an opportunity (JSON explanation)
  why JSONB DEFAULT '{}'::jsonb,
  -- Contains: reasons[], examples[], recommended_hooks[], recommended_formats[]
  
  -- Matching assets from library
  matching_asset_ids UUID[] DEFAULT '{}',
  top_match_score DECIMAL(5,2),
  
  -- Recommended actions
  recommended_actions JSONB DEFAULT '[]'::jsonb,
  -- Contains: [{type: 'post', platform: 'tiktok', priority: 'high'}, {type: 'experiment', hypothesis: '...'}]
  
  -- Status
  status VARCHAR(20) DEFAULT 'new', -- 'new', 'reviewed', 'actioned', 'expired', 'dismissed'
  actioned_at TIMESTAMPTZ,
  actioned_by VARCHAR(50), -- 'narrative_builder', 'experiments', 'user'
  
  -- Time window
  window_start TIMESTAMPTZ DEFAULT NOW(),
  window_end TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '48 hours'),
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
  
  -- Priority for display
  priority VARCHAR(10) DEFAULT 'medium', -- 'critical', 'high', 'medium', 'low'
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trend_opportunities_score ON trend_opportunities(opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_trend_opportunities_status ON trend_opportunities(status);
CREATE INDEX IF NOT EXISTS idx_trend_opportunities_priority ON trend_opportunities(priority);
CREATE INDEX IF NOT EXISTS idx_trend_opportunities_window ON trend_opportunities(window_start, window_end);

-- -----------------------------------------------------------------------------
-- 5. TREND TO ASSET MATCHES
-- -----------------------------------------------------------------------------
-- Links between opportunities and matching library assets

CREATE TABLE IF NOT EXISTS trend_asset_matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- References
  opportunity_id UUID REFERENCES trend_opportunities(id) ON DELETE CASCADE,
  asset_id UUID, -- Reference to content_items or media table
  
  -- Match details
  match_score DECIMAL(5,2), -- 0-100 similarity score
  match_type VARCHAR(50), -- 'transcript', 'tags', 'visual', 'topic'
  match_reason TEXT,
  
  -- Recommended packaging
  recommended_hook TEXT,
  recommended_caption TEXT,
  recommended_hashtags TEXT[],
  
  -- Status
  used BOOLEAN DEFAULT FALSE,
  used_at TIMESTAMPTZ,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trend_asset_matches_opportunity ON trend_asset_matches(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_trend_asset_matches_asset ON trend_asset_matches(asset_id);
CREATE INDEX IF NOT EXISTS idx_trend_asset_matches_score ON trend_asset_matches(match_score DESC);

-- -----------------------------------------------------------------------------
-- 6. TREND BRIEFS (Generated content briefs)
-- -----------------------------------------------------------------------------
-- Auto-generated briefs from trend opportunities

CREATE TABLE IF NOT EXISTS trend_briefs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  
  -- Link to opportunity
  opportunity_id UUID REFERENCES trend_opportunities(id),
  
  -- Brief content
  title VARCHAR(500),
  summary TEXT,
  
  -- What's trending
  trend_context JSONB DEFAULT '{}'::jsonb,
  -- Contains: what, why, examples[], platforms[], time_sensitivity
  
  -- Recommended content
  hook_options JSONB DEFAULT '[]'::jsonb, -- [{text: '...', style: 'question'}]
  caption_options JSONB DEFAULT '[]'::jsonb,
  format_recommendations JSONB DEFAULT '[]'::jsonb, -- [{format: 'vertical', length: '15-22s'}]
  
  -- Matched assets
  recommended_assets JSONB DEFAULT '[]'::jsonb, -- [{asset_id, match_score, why}]
  
  -- Scheduling
  recommended_window JSONB DEFAULT '{}'::jsonb, -- {start, end, best_times[], platforms[]}
  
  -- Experiment suggestions
  experiment_hypotheses JSONB DEFAULT '[]'::jsonb, -- [{hypothesis, variable, expected_lift}]
  
  -- Status
  status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'approved', 'scheduled', 'posted'
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '48 hours')
);

CREATE INDEX IF NOT EXISTS idx_trend_briefs_opportunity ON trend_briefs(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_trend_briefs_status ON trend_briefs(status);

-- -----------------------------------------------------------------------------
-- 7. TREND BUDGET SETTINGS
-- -----------------------------------------------------------------------------
-- Guardrails for trend-chasing behavior

CREATE TABLE IF NOT EXISTS trend_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  
  -- Budget constraints
  max_trend_posts_per_week INTEGER DEFAULT 2, -- Max trend-reactive posts
  trend_budget_percent DECIMAL(5,2) DEFAULT 20.0, -- % of mainline that can be trend-chasing
  
  -- Time windows
  min_opportunity_score DECIMAL(5,2) DEFAULT 60.0, -- Minimum score to surface
  default_window_hours INTEGER DEFAULT 48, -- Default trend window
  
  -- Auto-actions
  auto_generate_briefs BOOLEAN DEFAULT TRUE,
  auto_match_assets BOOLEAN DEFAULT TRUE,
  auto_suggest_experiments BOOLEAN DEFAULT TRUE,
  
  -- Filters
  blocked_topics TEXT[] DEFAULT '{}', -- Topics to never chase
  blocked_keywords TEXT[] DEFAULT '{}', -- Keywords to filter
  required_relevance_score DECIMAL(5,2) DEFAULT 30.0, -- Minimum brand relevance
  
  -- Notification preferences
  notify_on_high_opportunity BOOLEAN DEFAULT TRUE,
  notify_threshold DECIMAL(5,2) DEFAULT 80.0,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 8. UPDATE TRIGGERS
-- -----------------------------------------------------------------------------

-- Auto-update timestamps
DO $$
DECLARE
  t TEXT;
BEGIN
  FOR t IN SELECT unnest(ARRAY['trend_items', 'trend_clusters', 'trend_opportunities', 'trend_briefs', 'trend_settings'])
  LOOP
    EXECUTE format('
      DROP TRIGGER IF EXISTS update_%s_updated_at ON %s;
      CREATE TRIGGER update_%s_updated_at
        BEFORE UPDATE ON %s
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ', t, t, t, t);
  END LOOP;
END $$;

-- -----------------------------------------------------------------------------
-- 9. SEED DEFAULT SETTINGS
-- -----------------------------------------------------------------------------

INSERT INTO trend_settings (
  max_trend_posts_per_week,
  trend_budget_percent,
  min_opportunity_score,
  auto_generate_briefs,
  auto_match_assets,
  auto_suggest_experiments
) VALUES (
  2, 20.0, 60.0, TRUE, TRUE, TRUE
) ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- DONE
-- -----------------------------------------------------------------------------
