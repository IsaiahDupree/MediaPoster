# PRD: Cross-Platform Analytics Dashboard

**Status:** Proposed
**Priority:** P1 — Medium-Term
**Effort:** ~5-7 days
**Impact:** Unified visibility into what's working across all 22 accounts and 9 platforms

---

## 1. Problem Statement

With 22 accounts across 9 platforms, there's no single view of performance. Checking each platform's native analytics is time-consuming and makes it impossible to compare cross-platform performance. Questions like "which content type performs best?" or "which account is growing fastest?" require manual data aggregation.

## 2. Objective

Build a unified analytics dashboard that pulls metrics from all connected accounts, normalizes them, and surfaces actionable insights — best-performing content, fastest-growing accounts, optimal content types, and trend lines.

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Data freshness | Metrics updated every 6 hours |
| Coverage | All 22 accounts reporting |
| Time saved | Replace 2+ hrs/week of manual analytics checking |
| Insight quality | Surface at least 3 actionable insights per week |

## 4. User Stories

- **As a creator**, I want a single dashboard showing all my accounts' performance so I don't have to check each platform individually.
- **As a creator**, I want to see which videos performed best across ALL platforms, not just one.
- **As a creator**, I want growth trend lines (followers, views, engagement rate) over time.
- **As a creator**, I want to compare performance between accounts on the same platform (e.g., which TikTok account is growing fastest).

## 5. Technical Design

### 5.1 Architecture

```
┌────────────────────────┐
│  Metrics Collector      │  ← Blotato API + Platform APIs (cron)
│  (per account/platform) │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Normalization Layer    │  ← Unified schema: views, likes, comments,
│  (cross-platform)       │     shares, saves, engagement_rate
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Analytics Engine       │  ← Aggregations, rankings, trends
│  (time-series + rank)   │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Dashboard UI           │  ← React + Charts (Recharts / Chart.js)
│  (Next.js pages)        │
└────────────────────────┘
```

### 5.2 Data Model

```sql
CREATE TABLE platform_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    post_id VARCHAR(255),
    metric_date DATE NOT NULL,
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    shares BIGINT DEFAULT 0,
    saves BIGINT DEFAULT 0,
    followers_gained INT DEFAULT 0,
    watch_time_seconds BIGINT DEFAULT 0,
    engagement_rate FLOAT,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, platform, post_id, metric_date)
);

CREATE TABLE account_daily_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    stat_date DATE NOT NULL,
    total_followers BIGINT,
    followers_delta INT,
    total_views BIGINT,
    total_engagement BIGINT,
    avg_engagement_rate FLOAT,
    posts_published INT,
    top_post_id VARCHAR(255),
    UNIQUE(account_id, platform, stat_date)
);

CREATE INDEX idx_metrics_date ON platform_metrics(metric_date DESC);
CREATE INDEX idx_daily_stats ON account_daily_stats(stat_date DESC, platform);
```

### 5.3 Dashboard Pages

#### A. Overview (`/analytics`)
- **Scorecard row:** Total views (7d), total engagement (7d), follower growth (7d), posts published (7d)
- **Platform breakdown:** Bar chart comparing views/engagement by platform
- **Top 10 posts this week:** Ranked by engagement score across all platforms
- **Growth sparklines:** Per-account follower trend (30 days)

#### B. Per-Platform Deep Dive (`/analytics/:platform`)
- **Account comparison:** Side-by-side metrics for all accounts on that platform
- **Time-series charts:** Views, likes, comments, shares over time
- **Best posting times heatmap:** (ties into Smart Posting Times PRD)
- **Content type breakdown:** Which formats (video, image, carousel) perform best

#### C. Content Performance (`/analytics/content`)
- **Cross-platform comparison:** Same video's performance on YouTube vs TikTok vs Instagram
- **Content leaderboard:** All-time top performers
- **Engagement decay curve:** How quickly engagement drops after posting

### 5.4 API Endpoints

```
GET /api/analytics/overview?period=7d
GET /api/analytics/platform/:platform?account_id=710&period=30d
GET /api/analytics/content/:media_id     — Cross-platform performance for one video
GET /api/analytics/top-posts?period=7d&limit=10
GET /api/analytics/growth?account_id=710&platform=tiktok&period=90d
GET /api/analytics/compare?accounts=710,243&platform=tiktok&period=30d
```

## 6. Rollout Plan

1. **Phase 1:** Metrics collector cron + DB schema
2. **Phase 2:** API endpoints for aggregated data
3. **Phase 3:** Overview dashboard page with Recharts
4. **Phase 4:** Per-platform deep dive + content comparison
5. **Phase 5:** Automated weekly insight emails

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| API rate limits | Stagger collection; cache aggressively; 6hr refresh cycle |
| Inconsistent metrics across platforms | Normalize to common schema; note platform-specific caveats |
| Data gaps from API downtime | Track fetch status; show "last updated" timestamps |
| Dashboard performance with large datasets | Aggregate daily; use materialized views for common queries |

## 8. Out of Scope (v1)

- Competitor analytics comparison
- Revenue/monetization tracking
- Automated report generation (PDF)
- Audience demographics analysis
