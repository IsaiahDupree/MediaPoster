# Content Performance Audit Summary

## Overview

Audit of MediaPoster's Content Performance page against the ideal "One Creative → Many Distributions → One Scoreboard" specification, modeled after YouTube Studio and Instagram Professional Dashboard analytics.

**Audit Date**: December 20, 2024  
**Overall Score**: **~29% of ideal spec with real data**

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `CONTENT_PERFORMANCE_GAP_ANALYSIS.md` | Detailed feature-by-feature gap analysis |
| `add_content_performance_fields.sql` | Database migration for missing fields |
| `YOUTUBE_STUDIO_ANALYTICS.md` | YouTube Studio reference design |
| `INSTAGRAM_PROFESSIONAL_DASHBOARD.md` | Instagram Insights reference design |

---

## Score by Section

| Section | Score | Status | Notes |
|---------|-------|--------|-------|
| Global Controls | 71% | ⚠️ Good | Missing objective filter, tag taxonomy |
| KPI Tiles | 17% | ❌ Needs work | Most metrics simulated |
| Core Graphs | 25% | ❌ Needs work | Missing retention curves, O vs P stacked |
| Organic Metrics | 29% | ❌ Needs work | Only shares/saves are real |
| Paid Metrics | 0% | ❌ Not started | Not implemented |
| Ranking Table | 40% | ⚠️ Partial | Simulated quality scores |
| Organic→Paid Bridge | 0% | ❌ Not started | Not implemented |

---

## Current State

### What's Working ✅

| Feature | Implementation |
|---------|----------------|
| Date range filter | 7d / 30d / 90d / all |
| Platform filter | TikTok, Instagram, YouTube, etc. |
| Traffic type toggle | All / Organic / Paid |
| Viral Engine scatter plot | Avg % Viewed vs Share Rate |
| Decision labels | Scale / Iterate / Retarget / Pause |
| Basic engagement calculation | (likes + comments + shares) / views |
| YouTube Studio-style content table | Thumbnails, titles, metrics |

### What's Simulated ⚠️

These metrics currently use random/estimated values instead of real API data:

| Metric | Current Source | Needed Source |
|--------|----------------|---------------|
| Hook rate | `Math.random() * 30 + 50` | TikTok/IG Analytics API |
| Avg % viewed | `Math.random() * 60 + 20` | TikTok/IG Analytics API |
| Completion rate | `Math.random() * 40 + 10` | TikTok/IG Analytics API |
| Watch time | `views * 15` (estimated) | YouTube Analytics API |
| Avg view duration | `12` (hardcoded) | Platform APIs |
| Impressions | `views * 1.2` (estimated) | Business APIs |
| Reach | `= views` (same) | Business APIs |
| Clicks | `views * 0.02` (estimated) | Business APIs |
| Follows | `views * 0.01` (estimated) | Platform APIs |

### What's Missing ❌

| Feature | Priority | Dependency |
|---------|----------|------------|
| All paid metrics (spend, CPM, CPA, ROAS) | High | Meta/TikTok Ads API |
| Retention curve visualization | Medium | Platform Analytics APIs |
| Organic vs Paid stacked charts | Medium | `is_paid` flag + data |
| Creative asset grouping | High | `creative_assets` table |
| Hook checkpoints (1s/3s/5s/10s) | Low | Detailed retention data |
| Paid lift vs organic baseline | Low | Ads API |

---

## Database Migration

### New Columns Added

The migration script `add_content_performance_fields.sql` adds 30+ columns:

#### Organic Metrics
```sql
watch_time_seconds INTEGER
avg_view_duration FLOAT
avg_percent_viewed FLOAT
completion_rate FLOAT
hook_rate FLOAT
video_duration_seconds INTEGER
reach INTEGER
impressions INTEGER
follows_from_post INTEGER
thumbnail_url TEXT
creative_tags TEXT[]
title TEXT
```

#### Paid Metrics
```sql
is_paid BOOLEAN
ad_id TEXT
campaign_id TEXT
spend DECIMAL(10,2)
clicks INTEGER
cpm DECIMAL(10,4)
cpc DECIMAL(10,4)
ctr FLOAT
cpa DECIMAL(10,4)
roas FLOAT
conversions INTEGER
conversion_value DECIMAL(10,2)
frequency FLOAT
thruplays INTEGER
cost_per_thruplay DECIMAL(10,4)
thumbstop_rate FLOAT
```

#### Creative Linking
```sql
creative_asset_id UUID  -- Links to creative_assets table

-- New table: creative_assets
-- Aggregates metrics across all posts using the same creative
```

### Run Migration

```bash
psql $DATABASE_URL -f database/migrations/add_content_performance_fields.sql
```

---

## API Data Availability

### What We Can Get from RapidAPI (Scrapers)

| Platform | Metrics Available | API |
|----------|-------------------|-----|
| TikTok | play_count, likes, comments, shares, duration | tiktok-scraper7 |
| Instagram | likes, comments, video_view_count | instagram-looter2 |
| YouTube | views, likes, comments | yt-api |

### What Requires Official APIs

| Data | API Required | Notes |
|------|--------------|-------|
| Reach/Impressions | Instagram Graph API | Business account required |
| Watch time metrics | YouTube Analytics API | OAuth required |
| Retention curves | Not available via scraping | Platform-only |
| Paid ad metrics | Meta Ads API, TikTok Ads API | Ad account access |
| Conversion tracking | Pixel/SDK integration | Setup required |

---

## Priority Implementation Roadmap

### Phase 1: Database + Real Metrics (1-2 days)
- [ ] Run migration to add new columns
- [ ] Update TikTok backfill to get `video_duration`, `play_count`
- [ ] Update Instagram backfill to get engagement metrics
- [ ] Store `thumbnail_url` from API responses

### Phase 2: Remove Simulated Data (1 day)
- [ ] Replace random values with real API data or "N/A"
- [ ] Add indicators for "estimated" vs "actual" metrics
- [ ] Update quality score calculation to use real data

### Phase 3: UI Enhancements (2 days)
- [ ] Add objective filter (Awareness/Traffic/Leads/Purchases)
- [ ] Add creative tags taxonomy and filter
- [ ] Add Organic vs Paid stacked area chart
- [ ] Add retention curve visualization (with placeholder data)

### Phase 4: Ads Integration (Future)
- [ ] Integrate Meta Ads API
- [ ] Integrate TikTok Ads API
- [ ] Build Organic→Paid bridge panel
- [ ] Implement creative asset rollup

---

## Files Modified/Created

| File | Type | Purpose |
|------|------|---------|
| `docs/CONTENT_PERFORMANCE_GAP_ANALYSIS.md` | Doc | Detailed gap analysis |
| `docs/CONTENT_PERFORMANCE_AUDIT_SUMMARY.md` | Doc | This summary |
| `docs/YOUTUBE_STUDIO_ANALYTICS.md` | Doc | YouTube reference |
| `docs/INSTAGRAM_PROFESSIONAL_DASHBOARD.md` | Doc | Instagram reference |
| `database/migrations/add_content_performance_fields.sql` | SQL | Schema migration |
| `dashboard/app/(dashboard)/content-performance/page.tsx` | TSX | Updated UI |
| `dashboard/app/(dashboard)/analytics/content/page.tsx` | TSX | Fixed bar chart |

---

## Success Metrics

When fully implemented, the Content Performance page should:

1. **Show real data** for all displayed metrics (no simulated values)
2. **Support organic + paid** in a unified view
3. **Group by creative asset** to see "one creative → many distributions"
4. **Provide actionable decisions** (Scale/Iterate/Retarget/Pause) based on real scores
5. **Match YouTube Studio quality** in terms of insights and visualization

---

*Last Updated: December 20, 2024*
