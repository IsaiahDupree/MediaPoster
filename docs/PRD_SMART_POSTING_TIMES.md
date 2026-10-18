# PRD: Smart Posting Times

**Status:** Proposed
**Priority:** P0 — Immediate Impact
**Effort:** ~3-4 days
**Impact:** 15-30% engagement boost by posting when YOUR audience is online

---

## 1. Problem Statement

MediaPoster currently uses fixed posting times chosen manually. Every audience has unique activity patterns — posting at the wrong time means the algorithm buries content before peak followers see it. Optimal posting windows vary by platform, account, content type, and day of week.

## 2. Objective

Build an ML-driven scheduling engine that analyzes historical engagement data per account and automatically selects the highest-engagement time slots. Replace guesswork with data.

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Engagement rate improvement | ≥ 15% within 30 days |
| Average reach per post | ≥ 20% increase |
| Scheduling accuracy | Predictions within ±1hr of actual optimal window |
| Adoption | 100% of new scheduled posts use smart times by default |

## 4. User Stories

- **As a creator**, I want the system to automatically pick the best time to post so I don't have to guess.
- **As a creator**, I want to see why a specific time was recommended (data-driven explanation).
- **As a creator**, I want to override smart times when I have a reason (e.g., trending moment, event tie-in).
- **As a creator**, I want per-platform optimization since my TikTok and YouTube audiences behave differently.

## 5. Technical Design

### 5.1 Architecture

```
┌──────────────────────┐
│  Engagement Collector │  ← Blotato API / Platform APIs (hourly cron)
│  (views, likes, etc.) │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Time-Series Analysis │  ← Per account × platform × day_of_week
│  (engagement heatmap) │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Slot Optimizer       │  ← Picks top N slots avoiding conflicts
│  (greedy + decay)     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  PostScheduler        │  ← Existing scheduler uses smart times
│  (auto-assign slots)  │
└──────────────────────┘
```

### 5.2 Components

#### A. Engagement Data Collector (`services/engagement_collector.py`)

```python
class EngagementCollector:
    async def fetch_post_metrics(self, account_id: str, platform: str, since_days: int = 90) -> List[PostMetric]:
        """Pull engagement metrics for all posts in the window"""
    
    async def build_hourly_heatmap(self, account_id: str, platform: str) -> Dict[int, Dict[int, float]]:
        """
        Returns: {day_of_week: {hour: avg_engagement_score}}
        engagement_score = weighted(views, likes, comments, shares, saves)
        """
    
    async def collect_all_accounts(self):
        """Cron job: refresh metrics for all 22 accounts"""
```

#### B. Time Optimizer (`services/smart_scheduler.py`)

```python
class SmartScheduler:
    # Engagement score weights per platform
    WEIGHTS = {
        "tiktok":    {"views": 0.3, "likes": 0.2, "comments": 0.25, "shares": 0.25},
        "instagram": {"views": 0.2, "likes": 0.2, "comments": 0.3, "shares": 0.15, "saves": 0.15},
        "youtube":   {"views": 0.4, "likes": 0.15, "comments": 0.2, "watch_time": 0.25},
        "twitter":   {"views": 0.2, "likes": 0.2, "retweets": 0.3, "replies": 0.3},
    }
    
    def get_optimal_slots(
        self,
        account_id: str,
        platform: str,
        num_slots: int = 7,
        date_range: Tuple[date, date] = None,
        min_gap_hours: int = 4,
    ) -> List[datetime]:
        """
        Return the top N posting slots within the date range.
        Ensures minimum gap between posts on the same platform.
        Falls back to industry defaults if insufficient data (<20 posts).
        """
    
    def explain_slot(self, slot: datetime, account_id: str, platform: str) -> str:
        """Human-readable explanation: 'Tue 5pm — your TikTok posts at this time average 2.3x more views'"""
```

#### C. Industry Defaults (cold-start fallback)

```python
# When insufficient historical data, use researched defaults
INDUSTRY_DEFAULTS = {
    "tiktok": {
        # Best times: Tue 9am, Thu 12pm, Fri 5pm (2025-2026 data)
        0: [10, 19],      # Monday: 10am, 7pm
        1: [9, 12, 19],   # Tuesday: 9am, 12pm, 7pm
        2: [10, 19],      # Wednesday
        3: [9, 12, 19],   # Thursday
        4: [10, 17],      # Friday
        5: [11, 15],      # Saturday
        6: [11, 15],      # Sunday
    },
    "instagram": { ... },
    "youtube":   { ... },
    "twitter":   { ... },
}
```

### 5.3 Database Schema

```sql
CREATE TABLE post_engagement_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    platform_post_id VARCHAR(255),
    posted_at TIMESTAMPTZ NOT NULL,
    hour_of_day INT,       -- 0-23
    day_of_week INT,       -- 0=Mon, 6=Sun
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    shares BIGINT DEFAULT 0,
    saves BIGINT DEFAULT 0,
    watch_time_seconds BIGINT DEFAULT 0,
    engagement_score FLOAT,  -- weighted composite
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, platform, platform_post_id)
);

CREATE TABLE optimal_posting_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    day_of_week INT NOT NULL,
    hour INT NOT NULL,
    score FLOAT NOT NULL,
    sample_size INT,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, platform, day_of_week, hour)
);

CREATE INDEX idx_engagement_account_platform ON post_engagement_metrics(account_id, platform);
CREATE INDEX idx_optimal_slots ON optimal_posting_slots(account_id, platform, score DESC);
```

### 5.4 Integration with PostScheduler

```python
# In post_scheduler.py or schedule_videos.py:
smart = SmartScheduler()
slots = smart.get_optimal_slots(
    account_id="710",
    platform="tiktok",
    num_slots=14,  # 2 weeks of daily posts
    date_range=(date.today(), date.today() + timedelta(days=14)),
)

for video, slot in zip(videos, slots):
    schedule_post(video, platform="tiktok", scheduled_time=slot)
```

### 5.5 Cron Jobs

| Job | Frequency | Description |
|-----|-----------|-------------|
| `collect_metrics` | Every 6 hours | Pull engagement data from all accounts |
| `recompute_slots` | Daily at 3am | Rebuild optimal slot heatmaps |

## 6. API Endpoints

```
GET  /api/smart-schedule/heatmap?account_id=710&platform=tiktok
     → Returns 7×24 engagement heatmap

GET  /api/smart-schedule/recommend?platform=tiktok&count=7&start=2026-02-10&end=2026-02-17
     → Returns recommended posting times

POST /api/smart-schedule/apply
     → Auto-assign smart times to all unscheduled posts

GET  /api/smart-schedule/explain?slot=2026-02-10T17:00:00Z&account_id=710&platform=tiktok
     → Returns human-readable explanation
```

## 7. Dashboard Integration

- **Heatmap widget** on the schedule page showing best times per platform
- **"Use Smart Time" toggle** when creating/editing a scheduled post
- **Confidence indicator** (green/yellow/red) based on sample size

## 8. Rollout Plan

1. **Phase 1:** Engagement data collector + DB schema
2. **Phase 2:** Heatmap computation + industry defaults fallback
3. **Phase 3:** Slot optimizer integration with PostScheduler
4. **Phase 4:** Dashboard heatmap widget + API endpoints
5. **Phase 5:** Continuous learning (re-weight as data accumulates)

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Insufficient historical data | Fall back to industry defaults; minimum 20 posts before using ML |
| API rate limits on metrics fetch | Stagger requests; cache aggressively |
| Optimal time changes over time | Recompute daily; exponential decay on older data |
| Multiple posts at same "best" time | Enforce minimum 4hr gap; spread across top slots |

## 10. Out of Scope (v1)

- Real-time trend-aware scheduling (see PRD_AUTOMATED_TREND_DETECTION)
- Timezone-aware multi-region optimization
- Audience overlap analysis between accounts
