-- Cross-Platform Content Tracking Migration
-- Date: 2025-11-22
-- Purpose: Link posts across multiple platforms to a single content_id

-- =============================================================================
-- TABLES
-- =============================================================================

-- content_items: Canonical content that can be posted to multiple platforms
CREATE TABLE IF NOT EXISTS content_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  title           TEXT NOT NULL,
  description     TEXT,
  source_video_id UUID,  -- optional link to original video
  source_clip_id  UUID,  -- optional link to clip
  slug            TEXT,
  thumbnail_url   TEXT,
  created_by      UUID REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_items_workspace ON content_items(workspace_id);
CREATE INDEX idx_content_items_slug ON content_items(slug);
CREATE INDEX idx_content_items_created_at ON content_items(created_at DESC);

-- content_posts: Bridge table linking content to platform posts
CREATE TABLE IF NOT EXISTS content_posts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id      UUID REFERENCES content_items(id) ON DELETE CASCADE NOT NULL,
  post_id         UUID,  -- link to internal posts table if exists
  platform        TEXT NOT NULL,
  external_post_id TEXT,
  permalink_url   TEXT,
  posted_at       TIMESTAMPTZ,
  variant_label   TEXT,  -- "Hook A", "Version B", etc.
  is_primary      BOOLEAN DEFAULT false,
  metadata        JSONB,  -- any extra platform-specific data
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_posts_content_id ON content_posts(content_id);
CREATE INDEX idx_content_posts_platform ON content_posts(platform);
CREATE INDEX idx_content_posts_posted_at ON content_posts(posted_at DESC);
CREATE INDEX idx_content_posts_external_post_id ON content_posts(external_post_id);

-- content_tags: Optional tagging system
CREATE TABLE IF NOT EXISTS content_tags (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id      UUID REFERENCES content_items(id) ON DELETE CASCADE,
  tag_type        TEXT,  -- 'hook_type', 'visual_type', 'cta_type', 'topic', etc.
  tag_value       TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_tags_content_id ON content_tags(content_id);
CREATE INDEX idx_content_tags_type ON content_tags(tag_type, tag_value);

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
  COALESCE(SUM(sas.total_views), 0) as total_views,
  COALESCE(SUM(sas.total_likes), 0) as total_likes,
  COALESCE(SUM(sas.total_comments), 0) as total_comments,
  COALESCE(SUM(sas.total_shares), 0) as total_shares,
  COALESCE(AVG(sas.engagement_rate), 0) as avg_engagement_rate,
  ARRAY_AGG(cp.permalink_url) FILTER (WHERE cp.permalink_url IS NOT NULL) as post_urls
FROM content_posts cp
LEFT JOIN social_accounts sa ON sa.platform = cp.platform
LEFT JOIN social_analytics_snapshots sas ON sas.social_account_id = sa.id
  AND DATE(sas.snapshot_date) >= DATE(cp.posted_at)
  AND DATE(sas.snapshot_date) <= DATE(cp.posted_at) + INTERVAL '7 days'
GROUP BY cp.content_id, cp.platform;

-- content_cross_platform_summary: Aggregate metrics across all platforms
CREATE OR REPLACE VIEW content_cross_platform_summary AS
WITH platform_stats AS (
  SELECT 
    content_id,
    COUNT(DISTINCT platform) as platform_count,
    ARRAY_AGG(DISTINCT platform) as platforms,
    SUM(total_views) as total_views,
    SUM(total_likes) as total_likes,
    SUM(total_comments) as total_comments,
    SUM(total_shares) as total_shares,
    AVG(avg_engagement_rate) as avg_engagement_rate
  FROM content_platform_rollup
  GROUP BY content_id
),
best_platform AS (
  SELECT DISTINCT ON (content_id)
    content_id,
    platform as best_platform,
    total_views as best_platform_views
  FROM content_platform_rollup
  ORDER BY content_id, total_views DESC
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
  COALESCE(ps.total_views, 0) as total_views,
  COALESCE(ps.total_likes, 0) as total_likes,
  COALESCE(ps.total_comments, 0) as total_comments,
  COALESCE(ps.total_shares, 0) as total_shares,
  COALESCE(ps.avg_engagement_rate, 0) as avg_engagement_rate,
  bp.best_platform,
  bp.best_platform_views
FROM content_items ci
LEFT JOIN platform_stats ps ON ps.content_id = ci.id
LEFT JOIN best_platform bp ON bp.content_id = ci.id;

-- content_leaderboard: Ranked content by performance
CREATE OR REPLACE VIEW content_leaderboard AS
SELECT 
  content_id,
  title,
  platform_count,
  platforms,
  total_views,
  total_likes,
  total_comments,
  (total_likes + total_comments + total_shares) as engaged_reach,
  CASE 
    WHEN platform_count > 0 
    THEN (total_likes + total_comments + total_shares)::numeric / platform_count
    ELSE 0
  END as leverage_score,
  best_platform,
  created_at,
  ROW_NUMBER() OVER (ORDER BY (total_likes + total_comments + total_shares) DESC) as rank_by_reach,
  ROW_NUMBER() OVER (ORDER BY total_views DESC) as rank_by_views
FROM content_cross_platform_summary
WHERE total_views > 0;

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_content_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER content_items_updated_at
BEFORE UPDATE ON content_items
FOR EACH ROW
EXECUTE FUNCTION update_content_updated_at();

-- =============================================================================
-- COMMENTS (Documentation)
-- =============================================================================

COMMENT ON TABLE content_items IS 'Canonical content items that can be posted across multiple platforms';
COMMENT ON TABLE content_posts IS 'Bridge table linking content to specific platform posts';
COMMENT ON TABLE content_tags IS 'Flexible tagging system for content categorization';
COMMENT ON VIEW content_platform_rollup IS 'Aggregate metrics per content item per platform';
COMMENT ON VIEW content_cross_platform_summary IS 'Cross-platform summary with totals and best platform';
COMMENT ON VIEW content_leaderboard IS 'Ranked content by engagement and views';

-- =============================================================================
-- SAMPLE DATA (Optional - for testing)
-- =============================================================================

-- Uncomment to insert sample content item
-- INSERT INTO content_items (id, title, description, slug)
-- VALUES (
--   gen_random_uuid(),
--   'Sample Content: How to Automate Social Media',
--   'A tutorial on automation workflows',
--   'automate-social-media'
-- );
