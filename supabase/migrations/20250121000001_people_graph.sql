-- EverReach People Graph Tables
-- Migration: 001_people_graph
-- Created: 2025-01-21

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- PEOPLE GRAPH: Core person entities
-- =====================================================

CREATE TABLE IF NOT EXISTS people (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT,
  primary_email TEXT,
  company TEXT,
  role TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_people_email ON people(primary_email);
CREATE INDEX IF NOT EXISTS idx_people_created ON people(created_at DESC);

-- =====================================================
-- IDENTITIES: Cross-platform identity mapping
-- =====================================================

CREATE TABLE IF NOT EXISTS identities (
  id BIGSERIAL PRIMARY KEY,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  channel TEXT CHECK (channel IN (
    'email','instagram','linkedin','twitter','facebook',
    'tiktok','youtube','threads','bluesky','pinterest'
  )),
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
CREATE INDEX IF NOT EXISTS idx_identities_handle ON identities(handle);

-- =====================================================
-- PERSON EVENTS: Unified interaction stream
-- =====================================================

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
CREATE INDEX IF NOT EXISTS idx_person_events_channel ON person_events(channel, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_person_events_person_channel ON person_events(person_id, channel, occurred_at DESC);

-- =====================================================
-- PERSON INSIGHTS: Computed "lens" for each person
-- =====================================================

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

CREATE INDEX IF NOT EXISTS idx_active_people ON person_insights(person_id) 
  WHERE activity_state IN ('active','warming');

-- =====================================================
-- SEGMENTS: Dynamic people grouping
-- =====================================================

CREATE TABLE IF NOT EXISTS segments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  definition JSONB,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS segment_members (
  segment_id UUID REFERENCES segments(id) ON DELETE CASCADE,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (segment_id, person_id)
);

CREATE INDEX IF NOT EXISTS idx_segment_members_person ON segment_members(person_id);
CREATE INDEX IF NOT EXISTS idx_segment_members_segment ON segment_members(segment_id);

-- =====================================================
-- SEGMENT INSIGHTS: Per-segment analytics
-- =====================================================

CREATE TABLE IF NOT EXISTS segment_insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

CREATE INDEX IF NOT EXISTS idx_segment_insights_segment ON segment_insights(segment_id);

-- =====================================================
-- OUTBOUND MESSAGES: Email/DM tracking
-- =====================================================

CREATE TABLE IF NOT EXISTS outbound_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
CREATE INDEX IF NOT EXISTS idx_outbound_channel ON outbound_messages(channel, sent_at DESC);

-- =====================================================
-- Enable Row Level Security (RLS)
-- =====================================================

ALTER TABLE people ENABLE ROW LEVEL SECURITY;
ALTER TABLE identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE segment_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE segment_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbound_messages ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- Comments for documentation
-- =====================================================

COMMENT ON TABLE people IS 'Core person entities - one row per unique human';
COMMENT ON TABLE identities IS 'Cross-platform identity mapping (email, social handles)';
COMMENT ON TABLE person_events IS 'Unified event stream of all interactions';
COMMENT ON TABLE person_insights IS 'Computed person lens (interests, preferences, warmth)';
COMMENT ON TABLE segments IS 'Dynamic groups of people';
COMMENT ON TABLE segment_insights IS 'Per-segment analytics (organic vs paid separated)';
COMMENT ON TABLE outbound_messages IS 'Log of all emails/DMs sent';
