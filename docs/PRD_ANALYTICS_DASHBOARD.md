# PRD: Analytics Dashboard

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Effort:** 2-3 weeks  
**Priority:** 🟡 High

---

## Executive Summary

Unified analytics dashboard aggregating performance data from all platforms into actionable insights.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS DASHBOARD                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   DATA SOURCES                                                   │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐             │
│   │Instagram│ │ TikTok  │ │ YouTube │ │ Twitter │ ...         │
│   │(Blotato)│ │(Blotato)│ │(Blotato)│ │(Blotato)│             │
│   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘             │
│        └───────────┴───────────┴───────────┘                    │
│                         │                                        │
│                         ▼                                        │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              AGGREGATION ENGINE                          │  │
│   │  • Normalize metrics across platforms                    │  │
│   │  • Calculate engagement rates                            │  │
│   │  • Track growth trends                                   │  │
│   └─────────────────────────────────────────────────────────┘  │
│                         │                                        │
│                         ▼                                        │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              DASHBOARD VIEWS                             │  │
│   │  • Overview (KPIs)      • Content Performance           │  │
│   │  • Platform Breakdown   • Best Posting Times            │  │
│   │  • AI Insights          • Custom Reports                │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Overview Dashboard** | Total reach, engagement, followers, posts |
| **Platform Breakdown** | Per-platform metrics comparison |
| **Content Performance** | Top posts sorted by engagement |
| **Best Times** | Optimal posting times by platform |
| **AI Insights** | GPT-4 generated recommendations |
| **Reports** | Weekly/monthly PDF exports |

---

## Database Schema

```sql
-- Daily aggregated metrics
CREATE TABLE analytics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    scope_type VARCHAR(20) NOT NULL, -- 'account', 'platform', 'all'
    scope_id VARCHAR(100),
    platform VARCHAR(20),
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    video_views INTEGER DEFAULT 0,
    follower_count INTEGER DEFAULT 0,
    posts_published INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2),
    UNIQUE(date, scope_type, scope_id, platform)
);

-- Content performance
CREATE TABLE content_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID,
    platform VARCHAR(20) NOT NULL,
    platform_post_id VARCHAR(255),
    posted_at TIMESTAMPTZ,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2),
    UNIQUE(platform, platform_post_id)
);

-- AI insights
CREATE TABLE analytics_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_type VARCHAR(50),
    severity VARCHAR(20) DEFAULT 'info',
    title VARCHAR(255),
    description TEXT,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

```yaml
GET /api/analytics/overview
  → Summary metrics with period comparison

GET /api/analytics/daily
  → Daily time series data

GET /api/analytics/content
  → Content performance list

GET /api/analytics/content/top
  → Top performing content

GET /api/analytics/best-times
  → Optimal posting times

GET /api/analytics/insights
  → AI-generated insights

POST /api/analytics/reports
  → Create scheduled report

GET /api/analytics/reports/{id}/download
  → Download report PDF
```

---

## Implementation: 2-3 Weeks

| Phase | Tasks | Effort |
|-------|-------|--------|
| **Week 1** | Database, aggregation service, Blotato sync | 20h |
| **Week 2** | Dashboard UI, charts, content performance | 24h |
| **Week 3** | AI insights, reports, best times | 16h |

---

## Files to Create

```
Backend/services/analytics/
├── aggregation_service.py
├── insights_generator.py
├── report_service.py
└── models.py

Backend/api/endpoints/analytics.py

dashboard/app/(dashboard)/analytics/
├── page.tsx
├── content/page.tsx
├── insights/page.tsx
└── components/
    ├── MetricCard.tsx
    ├── EngagementChart.tsx
    ├── PlatformBreakdown.tsx
    ├── BestTimesHeatmap.tsx
    └── InsightCard.tsx
```

---

*Document created: February 1, 2026*
