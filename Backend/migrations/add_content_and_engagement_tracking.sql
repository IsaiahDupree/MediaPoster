-- Cross-Platform Content + Follower Engagement Tracking Migration
-- Date: 2025-11-22
-- Purpose: Track content across platforms + identify engaged followers

-- =============================================================================
-- DROP EXISTING TABLES/VIEWS (for clean migration)
-- =============================================================================

-- Drop views first (they depend on tables)
DROP VIEW IF EXISTS follower_cohorts CASCADE;
DROP VIEW IF EXISTS follower_activity_timeline CASCADE;
DROP VIEW IF EXISTS top_engaged_followers CASCADE;
DROP VIEW IF EXISTS content_cross_platform_summary CASCADE;
DROP VIEW IF EXISTS content_platform_rollup CASCADE;

-- Drop tables
DROP TABLE IF EXISTS follower_engagement_scores CASCADE;
DROP TABLE IF EXISTS follower_interactions CASCADE;
DROP TABLE IF EXISTS followers CASCADE;
DROP TABLE IF EXISTS content_tags CASCADE;
DROP TABLE IF EXISTS content_posts CASCADE;
DROP TABLE IF EXISTS content_items CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS determine_engagement_tier(NUMERIC) CASCADE;
DROP FUNCTION IF EXISTS calculate_engagement_score(INT, INT, INT, INT, INT, INT) CASCADE;
DROP FUNCTION IF EXISTS update_followers_updated_at() CASCADE;
DROP FUNCTION IF EXISTS update_content_updated_at() CASCADE;

-- =============================================================================
-- CONTENT TRACKING TABLES
-- =============================================================================

-- content_items: Canonical content that can be posted to multiple platforms
CREATE TABLE IF NOT EXISTS content_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID,  -- nullable for now
  title           TEXT NOT NULL,
  description     TEXT,
  source_video_id UUID,
  source_clip_id  UUID,
  slug            TEXT,
  thumbnail_url   TEXT,
  created_by      UUID,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_items_workspace ON content_items(workspace_id);
CREATE INDEX IF NOT EXISTS idx_content_items_slug ON content_items(slug);
CREATE INDEX IF NOT EXISTS idx_content_items_created_at ON content_items(created_at DESC);

-- content_posts: Bridge table linking content to platform posts
CREATE TABLE IF NOT EXISTS content_posts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id      UUID REFERENCES content_items(id) ON DELETE CASCADE NOT NULL,
  post_id         UUID,
  platform        TEXT NOT NULL,
  external_post_id TEXT,
  permalink_url   TEXT,
  posted_at       TIMESTAMPTZ,
  variant_label   TEXT,
  is_primary      BOOLEAN DEFAULT false,
  metadata        JSONB,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_posts_content_id ON content_posts(content_id);
CREATE INDEX IF NOT EXISTS idx_content_posts_platform ON content_posts(platform);
CREATE INDEX IF NOT EXISTS idx_content_posts_posted_at ON content_posts(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_posts_external_post_id ON content_posts(external_post_id);

-- content_tags: Optional tagging system
CREATE TABLE IF NOT EXISTS content_tags (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id      UUID REFERENCES content_items(id) ON DELETE CASCADE,
  tag_type        TEXT,
  tag_value       TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_tags_content_id ON content_tags(content_id);
CREATE INDEX IF NOT EXISTS idx_content_tags_type ON content_tags(tag_type, tag_value);

-- =============================================================================
-- FOLLOWER ENGAGEMENT TRACKING TABLES
-- =============================================================================

-- followers: Track individual followers across platforms
CREATE TABLE IF NOT EXISTS followers (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id        UUID,  -- nullable for now
  platform            TEXT NOT NULL,
  platform_user_id    TEXT NOT NULL,
  username            TEXT,
  display_name        TEXT,
  profile_url         TEXT,
  avatar_url          TEXT,
  follower_count      BIGINT,
  verified            BOOLEAN DEFAULT false,
  bio                 TEXT,
  first_seen_at       TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at        TIMESTAMPTZ DEFAULT NOW(),
  is_following_us     BOOLEAN DEFAULT TRUE,
  metadata            JSONB,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(platform, platform_user_id)
);

CREATE INDEX IF NOT EXISTS idx_followers_workspace ON followers(workspace_id);
CREATE INDEX IF NOT EXISTS idx_followers_platform ON followers(platform);
CREATE INDEX IF NOT EXISTS idx_followers_username ON followers(username);
CREATE INDEX IF NOT EXISTS idx_followers_last_seen ON followers(last_seen_at DESC);

-- follower_interactions: Every interaction they have with our content
CREATE TABLE IF NOT EXISTS follower_interactions (
  id                  BIGSERIAL PRIMARY KEY,
  follower_id         UUID REFERENCES followers(id) ON DELETE CASCADE,
  post_id             UUID,
  content_id          UUID REFERENCES content_items(id) ON DELETE SET NULL,
  interaction_type    TEXT NOT NULL,  -- 'comment','like','share','save','profile_visit','link_click'
  interaction_value   TEXT,
  sentiment_score     NUMERIC,
  sentiment_label     TEXT,  -- 'positive','neutral','negative'
  occurred_at         TIMESTAMPTZ NOT NULL,
  platform            TEXT NOT NULL,
  metadata            JSONB,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_follower_interactions_follower ON follower_interactions(follower_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_follower_interactions_post ON follower_interactions(post_id);
CREATE INDEX IF NOT EXISTS idx_follower_interactions_content ON follower_interactions(content_id);
CREATE INDEX IF NOT EXISTS idx_follower_interactions_type ON follower_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_follower_interactions_occurred ON follower_interactions(occurred_at DESC);

-- follower_engagement_scores: Computed engagement metrics
CREATE TABLE IF NOT EXISTS follower_engagement_scores (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  follower_id         UUID REFERENCES followers(id) ON DELETE CASCADE UNIQUE,
  total_interactions  INT DEFAULT 0,
  comment_count       INT DEFAULT 0,
  like_count          INT DEFAULT 0,
  share_count         INT DEFAULT 0,
  save_count          INT DEFAULT 0,
  profile_visit_count INT DEFAULT 0,
  link_click_count    INT DEFAULT 0,
  engagement_score    NUMERIC DEFAULT 0,
  engagement_tier     TEXT,
  avg_sentiment       NUMERIC,
  first_interaction   TIMESTAMPTZ,
  last_interaction    TIMESTAMPTZ,
  last_calculated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_follower_engagement_scores_follower ON follower_engagement_scores(follower_id);
CREATE INDEX IF NOT EXISTS idx_follower_engagement_scores_score ON follower_engagement_scores(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_follower_engagement_scores_tier ON follower_engagement_scores(engagement_tier);

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Update content_items updated_at
CREATE OR REPLACE FUNCTION update_content_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS content_items_updated_at ON content_items;
CREATE TRIGGER content_items_updated_at
BEFORE UPDATE ON content_items
FOR EACH ROW
EXECUTE FUNCTION update_content_updated_at();

-- Update followers updated_at
CREATE OR REPLACE FUNCTION update_followers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS followers_updated_at ON followers;
CREATE TRIGGER followers_updated_at
BEFORE UPDATE ON followers
FOR EACH ROW
EXECUTE FUNCTION update_followers_updated_at();

-- Calculate engagement score
CREATE OR REPLACE FUNCTION calculate_engagement_score(
  p_comments INT,
  p_likes INT,
  p_shares INT,
  p_saves INT,
  p_profile_visits INT,
  p_link_clicks INT
) RETURNS NUMERIC AS $$
BEGIN
  RETURN (
    (p_comments * 5) +
    (p_likes * 1) +
    (p_shares * 10) +
    (p_saves * 8) +
    (p_profile_visits * 3) +
    (p_link_clicks * 15)
  )::NUMERIC;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Determine engagement tier
CREATE OR REPLACE FUNCTION determine_engagement_tier(p_score NUMERIC)
RETURNS TEXT AS $$
BEGIN
  RETURN CASE
    WHEN p_score >= 500 THEN 'super_fan'
    WHEN p_score >= 100 THEN 'active'
    WHEN p_score >= 10 THEN 'lurker'
    ELSE 'inactive'
  END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =============================================================================
-- VIEWS
-- =============================================================================

-- content_platform_rollup: Aggregate metrics per content per platform
CREATE OR REPLACE VIEW content_platform_rollup AS
SELECT 
  cp.content_id,
  cp.platform,
  COUNT(DISTINCT cp.id) as post_count,
  MIN(cp.posted_at) as first_posted_at,
  MAX(cp.posted_at) as last_posted_at,
  ARRAY_AGG(cp.permalink_url) FILTER (WHERE cp.permalink_url IS NOT NULL) as post_urls,
  -- Get interaction counts from follower_interactions
  COUNT(DISTINCT fi.id) FILTER (WHERE fi.interaction_type = 'comment') as comment_count,
  COUNT(DISTINCT fi.id) FILTER (WHERE fi.interaction_type = 'like') as like_count,
  COUNT(DISTINCT fi.id) FILTER (WHERE fi.interaction_type = 'share') as share_count,
  COUNT(DISTINCT fi.id) FILTER (WHERE fi.interaction_type = 'save') as save_count
FROM content_posts cp
LEFT JOIN follower_interactions fi ON fi.content_id = cp.content_id AND fi.platform = cp.platform
GROUP BY cp.content_id, cp.platform;

-- content_cross_platform_summary
CREATE OR REPLACE VIEW content_cross_platform_summary AS
WITH platform_stats AS (
  SELECT 
    content_id,
    COUNT(DISTINCT platform) as platform_count,
    ARRAY_AGG(DISTINCT platform) as platforms,
    SUM(comment_count) as total_comments,
    SUM(like_count) as total_likes,
    SUM(share_count) as total_shares,
    SUM(save_count) as total_saves
  FROM content_platform_rollup
  GROUP BY content_id
),
best_platform AS (
  SELECT DISTINCT ON (content_id)
    content_id,
    platform as best_platform,
    (comment_count + like_count + share_count) as engagement
  FROM content_platform_rollup
  ORDER BY content_id, (comment_count + like_count + share_count) DESC
)
SELECT 
  ci.id as content_id,
  ci.workspace_id,
  ci.title,
  ci.description,
  ci.slug,
  ci.thumbnail_url,
  ci.created_at,
  ci.updated_at,
  COALESCE(ps.platform_count, 0) as platform_count,
  COALESCE(ps.platforms, ARRAY[]::TEXT[]) as platforms,
  COALESCE(ps.total_comments, 0) as total_comments,
  COALESCE(ps.total_likes, 0) as total_likes,
  COALESCE(ps.total_shares, 0) as total_shares,
  COALESCE(ps.total_saves, 0) as total_saves,
  bp.best_platform
FROM content_items ci
LEFT JOIN platform_stats ps ON ps.content_id = ci.id
LEFT JOIN best_platform bp ON bp.content_id = ci.id;

-- top_engaged_followers: Leaderboard of most engaged followers
CREATE OR REPLACE VIEW top_engaged_followers AS
SELECT 
  f.id as follower_id,
  f.platform,
  f.username,
  f.display_name,
  f.profile_url,
  f.avatar_url,
  f.follower_count,
  f.verified,
  fes.engagement_score,
  fes.engagement_tier,
  fes.total_interactions,
  fes.comment_count,
  fes.like_count,
  fes.share_count,
  fes.avg_sentiment,
  fes.first_interaction,
  fes.last_interaction,
  ROW_NUMBER() OVER (ORDER BY fes.engagement_score DESC) as rank,
  ROW_NUMBER() OVER (PARTITION BY f.platform ORDER BY fes.engagement_score DESC) as platform_rank
FROM followers f
JOIN follower_engagement_scores fes ON fes.follower_id = f.id
WHERE fes.last_interaction >= NOW() - INTERVAL '90 days'
ORDER BY fes.engagement_score DESC;

-- follower_activity_timeline: Recent follower activity
CREATE OR REPLACE VIEW follower_activity_timeline AS
SELECT 
  fi.id as interaction_id,
  fi.follower_id,
  f.username,
  f.display_name,
  f.platform,
  f.avatar_url,
  fi.interaction_type,
  fi.occurred_at,
  fi.interaction_value,
  fi.sentiment_score,
  fi.sentiment_label,
  ci.title as content_title,
  ci.id as content_id
FROM follower_interactions fi
JOIN followers f ON f.id = fi.follower_id
LEFT JOIN content_items ci ON ci.id = fi.content_id
ORDER BY fi.occurred_at DESC;

-- follower_cohorts: Cohort analysis by first_seen week
CREATE OR REPLACE VIEW follower_cohorts AS
SELECT 
  DATE_TRUNC('week', f.first_seen_at) as cohort_week,
  f.platform,
  COUNT(DISTINCT f.id) as follower_count,
  AVG(fes.engagement_score) as avg_engagement_score,
  COUNT(DISTINCT CASE WHEN fes.last_interaction >= NOW() - INTERVAL '30 days' THEN f.id END) as active_30d,
  COUNT(DISTINCT CASE WHEN fes.engagement_tier = 'super_fan' THEN f.id END) as super_fans,
  COUNT(DISTINCT CASE WHEN fes.engagement_tier = 'active' THEN f.id END) as active,
  COUNT(DISTINCT CASE WHEN fes.engagement_tier = 'lurker' THEN f.id END) as lurkers
FROM followers f
LEFT JOIN follower_engagement_scores fes ON fes.follower_id = f.id
GROUP BY DATE_TRUNC('week', f.first_seen_at), f.platform
ORDER BY cohort_week DESC;

-- =============================================================================
-- COMMENTS (Documentation)
-- =============================================================================

COMMENT ON TABLE content_items IS 'Canonical content items that can be posted across multiple platforms';
COMMENT ON TABLE content_posts IS 'Bridge table linking content to specific platform posts';
COMMENT ON TABLE content_tags IS 'Flexible tagging system for content categorization';
COMMENT ON TABLE followers IS 'Individual followers tracked across platforms with profile data';
COMMENT ON TABLE follower_interactions IS 'Every interaction (comment, like, share, etc.) by followers';
COMMENT ON TABLE follower_engagement_scores IS 'Computed engagement metrics and scores per follower';

COMMENT ON VIEW content_platform_rollup IS 'Aggregate metrics per content item per platform';
COMMENT ON VIEW content_cross_platform_summary IS 'Cross-platform summary with totals and best platform';
COMMENT ON VIEW top_engaged_followers IS 'Leaderboard of most engaged followers ranked by score';
COMMENT ON VIEW follower_activity_timeline IS 'Recent follower activity across all content';
COMMENT ON VIEW follower_cohorts IS 'Cohort analysis showing follower retention and engagement by week';
