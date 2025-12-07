# Cross-Platform Content Strategy & Implementation Guide

**Date**: November 22, 2025, 9:37 PM  
**Status**: 🎯 **READY FOR IMPLEMENTATION**

---

## Executive Summary

This document defines how to display social media analytics across multiple dimensions (account, platform, content) and how to tie posts from different platforms to a single canonical `content_id` for unified cross-platform analytics.

---

## What to Display

### Overview (All Platforms)
- ✅ Total followers, views, likes, comments, engagement
- ✅ Platform distribution (donut) + platform leaderboard
- 📊 Posts vs Engaged Reach over time (are we publishing more or just more noise?)
- 📊 Content-type performance by tags: `hook_type`, `visual_type`, `cta_type`
- 📊 Posting cadence heatmap (day x hour)

### Accounts Directory
- 📱 Account cards with platform badge, follower sparkline, 7/30/90d growth
- 📊 KPIs: views, engagement rate, posts this period, last sync status
- 📈 Scatter: Followers vs Engagement (size = views) to spot under/overperformers

### Platform Detail (e.g., TikTok)
- ✅ Trends: followers, views, likes, engagement rate (multi-axis)
- ✅ Top posts table with CTR/retention summary
- 📊 Posting cadence heatmap for this platform
- 📊 Hashtag/topic tiles by lift

### Post Performance (Single Post)
- 📊 Retention curve with annotated timeline (hook/body/CTA)
- 📊 Word-level snippet + key frame at hover-time
- ✅ CTA response rate (keyword counts), comments sentiment/themes
- 📊 Variant metadata used (title/caption/hashtags)

### Content Catalog (Cross-Platform) 🆕
- 📋 Grid/table of canonical content items (one row per `content_id`)
- 🏷️ Badges for platforms posted to, totals (views/likes/comments), "best platform"
- 🔲 Matrix view: rows = `content_id`, columns = platform, cells show views/posted status
- 🏆 Leaderboard: "Best content this month" by engaged reach or leverage score

### Content Detail (Cross-Platform View) 🆕
- 📄 Header: content title/thumbnail, owner video/clip
- 📱 Per-platform cards (views/likes/ER, posted_at, permalink, top comments)
- 📊 Cross-platform totals + "best performing platform" + "best posting time"
- ⏱️ Cohorts (first 1h/6h/24h): platform-to-platform timing effects

---

## Tie Everything to One content_id Across Platforms

### Data Model (Minimal)

#### content_items
```sql
CREATE TABLE content_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID REFERENCES workspaces(id),
  title           TEXT NOT NULL,
  description     TEXT,
  source_video_id UUID,  -- optional link to original video
  source_clip_id  UUID,  -- optional link to clip
  slug            TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### content_posts (Bridge Table)
```sql
CREATE TABLE content_posts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id      UUID REFERENCES content_items(id) NOT NULL,
  post_id         UUID,  -- link to your posts table if exists
  platform        TEXT NOT NULL,
  external_post_id TEXT,
  permalink_url   TEXT,
  posted_at       TIMESTAMPTZ,
  variant_label   TEXT,  -- "Hook A", "Version B", etc.
  is_primary      BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_posts_content_id ON content_posts(content_id);
CREATE INDEX idx_content_posts_platform ON content_posts(platform);
```

### Mapping Strategies (Robust)

#### 1. Deterministic at Publish Time (Best ⭐)
- When we schedule/publish a clip, we set `posts.content_id = <uuid>` and write `content_posts(content_id, post_id)`
- This is the most reliable method

#### 2. Identifier in Caption
- Add a short token (e.g., "CID:abc123") to captions
- Scrapers link back to `content_id` via this token

#### 3. Source Fingerprint
- Hash original video or store `source_url`/`video_hash` in `posts.extra`
- Match scraped posts by MD5 of media or embedded canonical URL

#### 4. Manual Reconciliation
- Admin UI: pick a scraped post and "Link to content …" → writes to `content_posts`

---

## Helpful DB Views

### content_platform_rollup
Per `content_id` x platform: totals (views/likes/comments), first/last posted_at

```sql
CREATE VIEW content_platform_rollup AS
SELECT 
  cp.content_id,
  cp.platform,
  COUNT(DISTINCT cp.id) as post_count,
  MIN(cp.posted_at) as first_posted_at,
  MAX(cp.posted_at) as last_posted_at,
  SUM(COALESCE(pcb.views, 0)) as total_views,
  SUM(COALESCE(pcb.likes, 0)) as total_likes,
  SUM(COALESCE(pcb.comments, 0)) as total_comments,
  AVG(COALESCE(pcb.avg_watch_pct, 0)) as avg_watch_pct,
  AVG(COALESCE(pcb.engagement_rate, 0)) as avg_engagement_rate
FROM content_posts cp
LEFT JOIN post_checkbacks pcb ON pcb.post_id = cp.post_id
WHERE pcb.checkback_h = 24 OR pcb.checkback_h IS NULL
GROUP BY cp.content_id, cp.platform;
```

### content_cross_platform_summary
Per `content_id`: totals across platforms, posted_platforms[], best_platform

```sql
CREATE VIEW content_cross_platform_summary AS
SELECT 
  ci.id as content_id,
  ci.title,
  ci.slug,
  ci.created_at,
  COUNT(DISTINCT cp.platform) as platform_count,
  ARRAY_AGG(DISTINCT cp.platform) as platforms,
  SUM(cpr.total_views) as total_views,
  SUM(cpr.total_likes) as total_likes,
  SUM(cpr.total_comments) as total_comments,
  AVG(cpr.avg_engagement_rate) as avg_engagement_rate,
  (
    SELECT platform 
    FROM content_platform_rollup 
    WHERE content_id = ci.id 
    ORDER BY total_views DESC 
    LIMIT 1
  ) as best_platform
FROM content_items ci
LEFT JOIN content_posts cp ON cp.content_id = ci.id
LEFT JOIN content_platform_rollup cpr ON cpr.content_id = ci.id
GROUP BY ci.id, ci.title, ci.slug, ci.created_at;
```

### content_leaderboard_period
Rank `content_id` by engaged reach or leverage score for a time window

```sql
CREATE VIEW content_leaderboard_period AS
SELECT 
  ci.id as content_id,
  ci.title,
  SUM(cpr.total_views) as total_views,
  SUM(cpr.total_likes + cpr.total_comments) as engaged_reach,
  (SUM(cpr.total_likes + cpr.total_comments)::numeric / NULLIF(COUNT(cp.id), 0)) as leverage_score,
  ARRAY_AGG(DISTINCT cp.platform) as platforms
FROM content_items ci
JOIN content_posts cp ON cp.content_id = ci.id
JOIN content_platform_rollup cpr ON cpr.content_id = ci.id
WHERE cp.posted_at >= NOW() - INTERVAL '30 days'
GROUP BY ci.id, ci.title
ORDER BY engaged_reach DESC;
```

---

## API Additions

### GET /api/social-analytics/content
Returns `content_cross_platform_summary` (paginate, filter by tag/platform/period)

**Response**:
```json
{
  "items": [
    {
      "content_id": "uuid",
      "title": "How to automate TikTok",
      "platform_count": 3,
      "platforms": ["tiktok", "instagram", "youtube"],
      "total_views": 45000,
      "total_likes": 5200,
      "best_platform": "tiktok",
      "avg_engagement_rate": 11.5
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### GET /api/social-analytics/content/{content_id}
Returns header + `content_platform_rollup` + per-post details

**Response**:
```json
{
  "content_id": "uuid",
  "title": "How to automate TikTok",
  "created_at": "2025-11-22T...",
  "platforms": [
    {
      "platform": "tiktok",
      "post_count": 1,
      "total_views": 32092,
      "total_likes": 4043,
      "avg_engagement_rate": 12.6,
      "posts": [
        {
          "external_post_id": "...",
          "permalink_url": "https://...",
          "posted_at": "...",
          "views": 32092,
          "likes": 4043
        }
      ]
    }
  ],
  "totals": {
    "views": 45000,
    "likes": 5200,
    "comments": 142
  },
  "best_platform": "tiktok"
}
```

### GET /api/social-analytics/content/leaderboard
Rank by "engaged reach" or "content leverage score"

**Query Params**:
- `metric`: "engaged_reach" | "leverage_score" | "views"
- `period`: "7d" | "30d" | "90d"
- `limit`: 10

### GET /api/social-analytics/content/matrix (Optional)
Sparse matrix for UI (content x platforms)

---

## Frontend Pages

### /analytics/content (Content Catalog) 🆕
Table with platform badges, totals, best platform; matrix view toggle

**Features**:
- Grid/table view toggle
- Sort by: views, engagement, platform count, date
- Filter by: platform, date range, performance tier
- Click row → navigate to `/analytics/content/:id`

### /analytics/content/:id (Content Detail) 🆕
Cross-platform cards, totals, trend mini-charts, links to original posts

**Sections**:
1. Header with title, thumbnail, source info
2. Cross-platform summary stats
3. Per-platform cards with metrics
4. Timeline showing when posted to each platform
5. Link to original posts on each platform

---

## Displays You Can Add Quickly

### Matrix (content x platforms)
Shows at-a-glance cross-post coverage and metrics; click cell to open the platform post.

### Treemap by platform
Area = views; color = engagement rate

### Cohort chart
Time-to-first-1k-views grouped by platform

### Funnel
impressions → views → watch_50% → likes → comments → profile taps (per platform)

### Calendar heatmap
Posts/day and engaged reach/day

---

## How This Ties Into Your Current System

### You Already Have ✅
- `/api/social-analytics/overview`
- `/api/social-analytics/platform/{platform}`
- `/api/social-analytics/content-mapping`
- Frontend `/analytics` tabs (Overview + TikTok)

### Next Steps 📋
1. Add `content_items`, `content_posts` tables
2. Backfill via publish flow
3. Create rollup views
4. Add API endpoints: `/content`, `/content/{id}`, `/content/leaderboard`
5. Build Content Catalog + Content Detail pages
6. Show "best platform" and "coverage" inline on Overview

---

## North Star Metrics Tie-In

### Weekly Engaged Reach
Sum unique engaged across all `content_id` for the week

### Content Leverage Score
(comments + saves + shares + profile_taps) / posts

### Warm Lead Flow
link_clicks + DM_starts + email signups

**Surface these**:
- Per `content_id`
- Per platform
- Overall

To guide scheduling and regeneration decisions.

---

## Implementation Priority

### Phase 1: Foundation ⭐
1. Create `content_items` and `content_posts` tables
2. Create DB views: `content_platform_rollup`, `content_cross_platform_summary`
3. Add API endpoint: `GET /content`

### Phase 2: Content Catalog 📋
4. Build `/analytics/content` page (table view)
5. Add sorting, filtering, platform badges

### Phase 3: Content Detail 📊
6. Add API endpoint: `GET /content/{id}`
7. Build `/analytics/content/:id` page
8. Show per-platform cards and totals

### Phase 4: Leaderboard & Advanced 🏆
9. Add API endpoint: `GET /content/leaderboard`
10. Add leaderboard widget to Overview
11. Add matrix view to Content Catalog
12. Implement publisher integration (auto-set `content_id`)

---

## Example Rollup Logic

```sql
-- Best platform = max by views or engagement rate
SELECT 
  content_id,
  platform,
  total_views,
  avg_engagement_rate,
  RANK() OVER (PARTITION BY content_id ORDER BY total_views DESC) as rank
FROM content_platform_rollup;

-- Content with best cross-platform coverage
SELECT 
  content_id,
  title,
  platform_count,
  total_views,
  CASE 
    WHEN platform_count >= 5 THEN 'excellent'
    WHEN platform_count >= 3 THEN 'good'
    ELSE 'limited'
  END as coverage_tier
FROM content_cross_platform_summary
ORDER BY platform_count DESC, total_views DESC;
```

---

## Benefits

### For Creators
- **See what works where**: Same content, different platforms, different results
- **Optimize posting strategy**: Post where content performs best
- **Reduce waste**: Don't post everywhere if one platform dominates

### For Analytics
- **Unified view**: One content item, all performance data
- **Cross-platform comparison**: Apples-to-apples comparison
- **Better ROI tracking**: Content leverage score shows efficiency

### For Publishing
- **Variant testing**: Test different hooks/captions per platform
- **Timing optimization**: Learn best posting times per platform
- **Resource allocation**: Focus on platforms that deliver

---

## Success Metrics

- ✅ All scraped posts linked to `content_id`
- ✅ Content Catalog shows 100% of content
- ✅ Best platform identified for top 20 pieces
- ✅ Content Leverage Score improves by 15% in 30 days
- ✅ Cross-platform posting reduces by 20% (focus on winners)

---

## Notes & Considerations

### Data Quality
- Manual reconciliation UI needed for edge cases
- Content fingerprinting helps with orphaned posts
- Regular audits to ensure all posts are mapped

### Performance
- Views may need caching for large catalogs
- Consider materialized views for expensive rollups
- Paginate content lists

### Privacy & Compliance
- Ensure `content_id` doesn't leak in public URLs
- Respect platform terms of service for data retention
- Allow content deletion across all platforms

---

## Questions to Answer

1. Should `content_id` be auto-generated or user-defined slugs?
2. How to handle content that's posted to new platforms later?
3. What to do with scraped posts that can't be matched?
4. Should we support multiple variants per platform (A/B tests)?

---

## Resources

- **DB Schema**: See `CROSS_PLATFORM_CONTENT_SCHEMA.sql`
- **API Spec**: See `CONTENT_API_SPEC.md`
- **Frontend Mockups**: See `designs/content-catalog/`

---

**Status**: 📝 Document complete, ready for implementation  
**Next Action**: Create database migration for `content_items` and `content_posts`
