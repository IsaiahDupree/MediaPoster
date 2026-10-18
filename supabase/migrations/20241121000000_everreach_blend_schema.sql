-- EverReach/Blend: Comprehensive Database Schema

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- People Graph (EverReach Core)
-- ============================================================================

-- 1. people
CREATE TABLE IF NOT EXISTS people (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  full_name TEXT,
  primary_email TEXT,
  company TEXT,
  role TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. identities
CREATE TABLE IF NOT EXISTS identities (
  id BIGSERIAL PRIMARY KEY,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  channel TEXT CHECK (channel IN ('email','instagram','linkedin','twitter','facebook','tiktok','youtube','threads','bluesky','pinterest')),
  handle TEXT NOT NULL,
  extra JSONB,
  is_verified BOOLEAN DEFAULT FALSE,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(channel, handle)
);

CREATE INDEX IF NOT EXISTS idx_identities_person ON identities(person_id);
CREATE INDEX IF NOT EXISTS idx_identities_channel ON identities(channel);

-- 3. person_events
CREATE TABLE IF NOT EXISTS person_events (
  id BIGSERIAL PRIMARY KEY,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  event_type TEXT NOT NULL,
  platform_id TEXT,
  content_excerpt TEXT,
  sentiment NUMERIC CHECK (sentiment >= -1 AND sentiment <= 1),
  traffic_type TEXT CHECK (traffic_type IN ('organic','paid')) DEFAULT 'organic',
  metadata JSONB,
  occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_person_events_person ON person_events(person_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_person_events_type ON person_events(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_person_events_traffic ON person_events(traffic_type);

-- 4. person_insights
CREATE TABLE IF NOT EXISTS person_insights (
  person_id UUID PRIMARY KEY REFERENCES people(id) ON DELETE CASCADE,
  interests JSONB,
  tone_preferences JSONB,
  channel_preferences JSONB,
  avg_reply_time INTERVAL,
  activity_state TEXT CHECK (activity_state IN ('active','warming','cool','dormant')),
  last_active_at TIMESTAMPTZ,
  seasonality JSONB,
  warmth_score NUMERIC,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. segments
CREATE TABLE IF NOT EXISTS segments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  definition JSONB,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. segment_members
CREATE TABLE IF NOT EXISTS segment_members (
  segment_id UUID REFERENCES segments(id) ON DELETE CASCADE,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (segment_id, person_id)
);

CREATE INDEX IF NOT EXISTS idx_segment_members_person ON segment_members(person_id);

-- 7. segment_insights
CREATE TABLE IF NOT EXISTS segment_insights (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  segment_id UUID REFERENCES segments(id) ON DELETE CASCADE,
  traffic_type TEXT CHECK (traffic_type IN ('organic','paid')),
  top_topics JSONB,
  top_platforms JSONB,
  top_formats JSONB,
  engagement_style JSONB,
  best_times JSONB,
  expected_reach_range INT4RANGE,
  expected_engagement_rate_range NUMRANGE,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(segment_id, traffic_type)
);

-- 8. outbound_messages
CREATE TABLE IF NOT EXISTS outbound_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES segments(id) ON DELETE SET NULL,
  channel TEXT NOT NULL,
  goal_type TEXT,
  variant TEXT,
  subject TEXT,
  body TEXT,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  opened_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  replied_at TIMESTAMPTZ,
  metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_outbound_person ON outbound_messages(person_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outbound_segment ON outbound_messages(segment_id, sent_at DESC);


-- ============================================================================
-- Content Graph (Blend Cross-Platform)
-- ============================================================================

-- 9. content_items
CREATE TABLE IF NOT EXISTS content_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- 10. content_variants
CREATE TABLE IF NOT EXISTS content_variants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- 11. content_metrics
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

-- 12. content_rollups
CREATE TABLE IF NOT EXISTS content_rollups (
  content_id UUID PRIMARY KEY REFERENCES content_items(id) ON DELETE CASCADE,
  total_views BIGINT,
  total_impressions BIGINT,
  total_likes BIGINT,
  total_comments BIGINT,
  total_shares BIGINT,
  total_saves BIGINT,
  total_clicks BIGINT,
  avg_watch_time_seconds NUMERIC,
  global_sentiment NUMERIC,
  best_platform TEXT,
  last_updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. content_experiments
CREATE TABLE IF NOT EXISTS content_experiments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  content_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  hypothesis TEXT,
  primary_metric TEXT,
  status TEXT CHECK (status IN ('draft','running','completed','cancelled')) DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);


-- ============================================================================
-- Platform Connectors
-- ============================================================================

-- 14. ig_connections
CREATE TABLE IF NOT EXISTS ig_connections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  everreach_user_id UUID NOT NULL,
  fb_page_id TEXT NOT NULL,
  ig_business_id TEXT NOT NULL,
  access_token TEXT NOT NULL,
  token_expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_synced_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ig_conn_user ON ig_connections(everreach_user_id);

-- 15. connector_configs
CREATE TABLE IF NOT EXISTS connector_configs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  connector_type TEXT NOT NULL,
  config JSONB NOT NULL,
  is_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, connector_type)
);

-- ============================================================================
-- Indexes for Search & Performance
-- ============================================================================

-- Full-text search on content
CREATE INDEX IF NOT EXISTS idx_content_title_search ON content_items USING GIN (to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_content_desc_search ON content_items USING GIN (to_tsvector('english', description));

-- Partial indexes for active data
CREATE INDEX IF NOT EXISTS idx_active_people ON person_insights(person_id) WHERE activity_state IN ('active','warming');
CREATE INDEX IF NOT EXISTS idx_scheduled_variants ON content_variants(scheduled_at) WHERE published_at IS NULL;

-- ============================================================================
-- Row Level Security (RLS) - Basic Setup
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE people ENABLE ROW LEVEL SECURITY;
ALTER TABLE identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE segment_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE segment_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbound_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_rollups ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ig_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_configs ENABLE ROW LEVEL SECURITY;

-- Create policies (Placeholder: allow all for authenticated users for now, refine later)
-- Note: In a real production app, you'd want stricter policies based on user ownership.

CREATE POLICY "Allow all access for authenticated users" ON people FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON identities FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON person_events FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON person_insights FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON segments FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON segment_members FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON segment_insights FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON outbound_messages FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON content_items FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON content_variants FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON content_metrics FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON content_rollups FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON content_experiments FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON ig_connections FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all access for authenticated users" ON connector_configs FOR ALL TO authenticated USING (true);
