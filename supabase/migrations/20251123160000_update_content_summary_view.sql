-- Update content_cross_platform_summary view to include total_views

DROP VIEW IF EXISTS content_cross_platform_summary;

CREATE OR REPLACE VIEW content_cross_platform_summary AS
SELECT
    ci.id AS content_id,
    ci.title,
    ci.description,
    ci.slug,
    ci.created_at,
    ci.updated_at,
    -- Aggregates from rollups
    COALESCE(cr.total_views, 0) AS total_views,
    COALESCE(cr.total_likes, 0) AS total_likes,
    COALESCE(cr.total_comments, 0) AS total_comments,
    COALESCE(cr.total_shares, 0) AS total_shares,
    COALESCE(cr.total_saves, 0) AS total_saves,
    cr.best_platform,
    -- Platform count and list
    (SELECT COUNT(DISTINCT platform) FROM content_variants cv WHERE cv.content_id = ci.id) AS platform_count,
    (SELECT ARRAY_AGG(DISTINCT platform) FROM content_variants cv WHERE cv.content_id = ci.id) AS platforms
FROM content_items ci
LEFT JOIN content_rollups cr ON ci.id = cr.content_id;
