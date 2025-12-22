# Content Performance Page - Gap Analysis

## Executive Summary

Comparing current implementation against the ideal "One Creative → Many Distributions → One Scoreboard" spec.

---

## 1. Global Controls

| Feature | Ideal Spec | Current Status | Gap |
|---------|------------|----------------|-----|
| Date range filter | ✅ Required | ✅ **Implemented** (7d/30d/90d/all) | None |
| Platform filter | ✅ Required | ✅ **Implemented** | None |
| Traffic type toggle (All/Organic/Paid) | ✅ Required | ✅ **Implemented** | None |
| Account/Brand filter | ✅ Required | ⚠️ **Partial** - has account_username | Need multi-select |
| Objective filter (Awareness/Traffic/Leads/Purchases) | ✅ Required | ❌ **Missing** | Need field + UI |
| Creative tags filter (hook type, topic, format, length) | ✅ Required | ⚠️ **Partial** - creative_tags array exists | Need tag taxonomy + UI |
| Grouping toggle (Creative/Post/Ad) | ✅ Required | ✅ **Implemented** | None |

**Gap Score: 5/7 (71%)**

---

## 2. Executive Snapshot KPIs

### Row A - Distribution Metrics

| Metric | Ideal Spec | Current Status | Data Source |
|--------|------------|----------------|-------------|
| Impressions | ✅ Required | ⚠️ **Simulated** | Need from API |
| Reach | ✅ Required | ⚠️ **Simulated** (=views) | Need from API |
| Views (plays) | ✅ Required | ✅ **Real data** | posted_content.views |
| View rate (views ÷ impressions) | ✅ Required | ⚠️ **Calculated from simulated** | Need real impressions |
| Frequency (paid) | ✅ Required | ❌ **Missing** | Need ad data |

### Row B - Response + Business Metrics

| Metric | Ideal Spec | Current Status | Data Source |
|--------|------------|----------------|-------------|
| Watch time | ✅ Required | ⚠️ **Simulated** | Need from API |
| Avg view duration (AVD) | ✅ Required | ⚠️ **Simulated** | Need from API |
| Avg % viewed | ✅ Required | ⚠️ **Simulated** | Need from API |
| Completion rate | ✅ Required | ⚠️ **Simulated** | Need from API |
| Engagement rate | ✅ Required | ✅ **Calculated** | (likes+comments+shares)/views |
| Clicks + CTR | ✅ Required | ⚠️ **Simulated** | Need from API |
| Conversions + CPA + ROAS | ✅ Required | ❌ **Missing** | Need ad tracking |

**Gap Score: 2/12 real (17%) - Most metrics simulated**

---

## 3. Core Graphs

### A) Performance Over Time
| Feature | Status |
|---------|--------|
| Line chart with views/impressions/watch time | ✅ **Implemented** (AreaChart) |
| Posting times overlay | ❌ **Missing** |
| Ad start/stop markers | ❌ **Missing** |

### B) Organic vs Paid Contribution
| Feature | Status |
|---------|--------|
| Stacked area by source | ❌ **Missing** |
| Views by Organic vs Paid | ❌ **Missing** - have toggle but not stacked |
| Conversions by source | ❌ **Missing** |

### C) Retention Diagnostics
| Feature | Status |
|---------|--------|
| Retention curve (% remaining vs time) | ❌ **Missing** |
| Hook checkpoints (1s/3s/5s/10s) | ⚠️ **Partial** - have hook_rate |
| Drop-off timestamps | ❌ **Missing** |

### D) Creative Scatter Plots
| Feature | Status |
|---------|--------|
| Avg % Viewed vs Share Rate | ✅ **Implemented** ("Viral Engine") |
| Hook Rate vs CTR/CVR | ❌ **Missing** |

**Gap Score: 2/8 (25%)**

---

## 4. Metrics Coverage

### Organic Metrics

| Metric | DB Field | API Source | Status |
|--------|----------|------------|--------|
| Hook rate | ❌ None | TikTok/IG API | ❌ Not tracked |
| Avg % viewed | ❌ None | TikTok/IG API | ❌ Not tracked |
| Completion rate | ❌ None | TikTok/IG API | ❌ Not tracked |
| Share rate | shares/views | ✅ Calculated | ✅ Working |
| Save rate | saves/views | ✅ Calculated | ✅ Working |
| Follow rate | ❌ None | TikTok/IG API | ❌ Not tracked |
| Search/Explore contribution | ❌ None | Platform API | ❌ Not tracked |

### Paid Metrics

| Metric | DB Field | Status |
|--------|----------|--------|
| CPM | ❌ None | ❌ Not tracked |
| CPC / CTR | ❌ None | ❌ Not tracked |
| CPA / ROAS | ❌ None | ❌ Not tracked |
| Frequency | ❌ None | ❌ Not tracked |
| Thumbstop / 3-sec view rate | ❌ None | ❌ Not tracked |
| Cost per thruplay | ❌ None | ❌ Not tracked |
| CVR | ❌ None | ❌ Not tracked |

**Gap Score: Organic 2/7 (29%), Paid 0/7 (0%)**

---

## 5. Ranking Table

| Feature | Ideal Spec | Status |
|---------|------------|--------|
| Thumbnail | ✅ Required | ✅ **Implemented** |
| Hook text | ✅ Required | ⚠️ **Partial** (caption) |
| Length bucket | ✅ Required | ⚠️ **Partial** (duration) |
| Tags | ✅ Required | ⚠️ **In type, not displayed** |
| Hook rate column | ✅ Required | ⚠️ **Simulated** |
| Avg % viewed | ✅ Required | ⚠️ **Simulated** |
| Completion rate | ✅ Required | ⚠️ **Simulated** |
| Share/Save rate | ✅ Required | ✅ **Calculated** |
| Spend/CPM/CTR/CPC/CPA/ROAS | ✅ Required | ❌ **Missing** |
| Decision column (Scale/Iterate/Retarget/Pause) | ✅ Required | ✅ **Implemented** |

**Gap Score: 4/10 (40%)**

---

## 6. Organic → Paid Bridge

| Feature | Status |
|---------|--------|
| "Which organic posts earned paid spend?" | ❌ **Missing** |
| Paid lift vs organic baseline | ❌ **Missing** |
| Retention deltas | ❌ **Missing** |
| CTR/CVR deltas | ❌ **Missing** |
| Frequency trend (fatigue) | ❌ **Missing** |

**Gap Score: 0/5 (0%)**

---

## 7. Scoring System

| Feature | Status |
|---------|--------|
| Creative Quality Score | ✅ **Implemented** |
| - 40% Avg % viewed | ⚠️ Using simulated data |
| - 25% Hook rate | ⚠️ Using simulated data |
| - 20% Share + Save rate | ✅ Real data |
| - 15% Follow rate | ⚠️ Simulated |
| Paid Efficiency Score | ❌ **Missing** |
| Auto-decision rules | ✅ **Implemented** |

**Gap Score: 1/2 (50%)**

---

## Database Schema Gaps

### Current `posted_content` Table
```sql
-- ✅ Have
id, platform, platform_post_id, platform_url, account_id, account_username,
media_id, caption, hashtags, views, likes, comments, shares, saves,
engagement_rate, status, posted_at

-- ❌ Missing (Organic Metrics)
watch_time_seconds, avg_view_duration, avg_percent_viewed, completion_rate,
hook_rate, follows_from_post, reach, impressions, video_duration_seconds,
thumbnail_url, creative_tags

-- ❌ Missing (Paid Metrics)
is_paid, ad_id, ad_set_id, campaign_id, spend, impressions_paid,
clicks, cpm, cpc, ctr, cpa, roas, frequency, conversions, conversion_value
```

---

## Recommended Schema Additions

```sql
-- Add to posted_content table
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS watch_time_seconds INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS avg_view_duration FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS avg_percent_viewed FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS completion_rate FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS hook_rate FLOAT DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS follows_from_post INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS reach INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS impressions INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS video_duration_seconds INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS creative_tags TEXT[];
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS title TEXT;

-- Paid tracking fields
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT FALSE;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS ad_id TEXT;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS campaign_id TEXT;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS spend DECIMAL(10,2) DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS clicks INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS conversions INTEGER DEFAULT 0;
ALTER TABLE posted_content ADD COLUMN IF NOT EXISTS conversion_value DECIMAL(10,2) DEFAULT 0;
```

---

## API Data Availability

### What We Can Get from RapidAPI

| Platform | Metric | API Availability |
|----------|--------|------------------|
| TikTok | play_count, digg_count, comment_count, share_count | ✅ tiktok-scraper7 |
| TikTok | video_duration | ✅ tiktok-scraper7 |
| TikTok | follower change | ❌ Not available per-post |
| Instagram | likes, comments, video_view_count | ✅ instagram-looter2 |
| Instagram | reach, impressions | ❌ Requires Business API |
| Instagram | saves | ❌ Requires Business API |
| YouTube | views, likes, comments | ✅ yt-api |
| YouTube | watch_time, avg_view_duration | ❌ Requires YouTube Analytics API |
| YouTube | retention curve | ❌ Requires YouTube Analytics API |

### What Requires Official Platform APIs

| Data | Platform | API Required |
|------|----------|--------------|
| Reach/Impressions | All | Official Business APIs |
| Watch time metrics | YT/TikTok | Analytics APIs |
| Retention curves | All | Not available via scraping |
| Paid ad metrics | All | Meta Ads API, TikTok Ads API, etc. |
| Conversion tracking | All | Pixel/SDK integration |

---

## Priority Implementation Roadmap

### Phase 1: Database Schema (1 day)
- Add missing columns to posted_content
- Create migration script

### Phase 2: Backfill Real Metrics (2 days)
- Update TikTok backfill to get video duration, play_count
- Update Instagram backfill to get engagement metrics
- Store thumbnail_url from API responses

### Phase 3: UI Enhancements (2 days)
- Add objective filter
- Add creative tags taxonomy
- Add Organic vs Paid stacked charts
- Remove simulated data indicators

### Phase 4: Paid Tracking (Future)
- Integrate Meta Ads API
- Integrate TikTok Ads API
- Build Organic→Paid bridge panel

---

## Overall Score

| Section | Score | Status |
|---------|-------|--------|
| Global Controls | 71% | ⚠️ Good |
| KPI Tiles | 17% | ❌ Needs real data |
| Core Graphs | 25% | ❌ Missing key charts |
| Organic Metrics | 29% | ❌ Mostly simulated |
| Paid Metrics | 0% | ❌ Not implemented |
| Ranking Table | 40% | ⚠️ Partial |
| Organic→Paid Bridge | 0% | ❌ Not implemented |
| Scoring System | 50% | ⚠️ Partial |

**Overall: ~29% of ideal spec implemented with real data**

---

*Generated: December 20, 2024*
