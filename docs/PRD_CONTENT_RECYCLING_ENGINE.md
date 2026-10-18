# PRD: Content Recycling Engine

**Status:** Proposed
**Priority:** P0 — Immediate Impact
**Effort:** ~3-4 days
**Impact:** 2-3x content output without creating new videos; evergreen content keeps earning views

---

## 1. Problem Statement

High-performing content has a short shelf life on social media. A TikTok that got 50K views 60 days ago is buried — but the content is still great. Creators manually track and repost old content, which is tedious and inconsistent. Meanwhile, mediocre content never gets recycled (correctly so).

## 2. Objective

Build an automated recycling engine that identifies top-performing posts, waits for a cooldown period, then re-queues them with fresh captions/hashtags. Only evergreen content gets recycled — time-sensitive posts (e.g., Valentine's Day tips after Feb 14) are excluded.

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Content output increase | ≥ 2x without new video creation |
| Recycled post engagement | ≥ 60% of original post performance |
| False positive rate | < 5% (non-evergreen content incorrectly recycled) |
| Creator time saved | ≥ 3 hrs/week on content planning |

## 4. User Stories

- **As a creator**, I want my best-performing content to automatically get reposted so it reaches new followers.
- **As a creator**, I want recycled posts to have fresh captions so they don't look like reposts.
- **As a creator**, I want to exclude specific posts or categories from recycling (e.g., event-specific content).
- **As a creator**, I want to control how often content gets recycled and the minimum cooldown period.
- **As a creator**, I want recycled posts spread across my secondary accounts, not just the original account.

## 5. Technical Design

### 5.1 Architecture

```
┌─────────────────────────┐
│  Performance Analyzer    │  ← Scores all posted content
│  (engagement percentile) │
└───────────┬─────────────┘
            │  Top 20% posts
            ▼
┌─────────────────────────┐
│  Evergreen Classifier    │  ← GPT classifies: evergreen vs time-sensitive
│  (AI + rules)            │
└───────────┬─────────────┘
            │  Evergreen posts only
            ▼
┌─────────────────────────┐
│  Cooldown Manager        │  ← Enforces min 30-60 day gap
│  (per post × platform)   │
└───────────┬─────────────┘
            │  Eligible posts
            ▼
┌─────────────────────────┐
│  Caption Refresher       │  ← GPT rewrites caption with new hook/hashtags
│  (optional: new title)   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  PostScheduler           │  ← Queues recycled post at smart time
│  (existing pipeline)     │
└─────────────────────────┘
```

### 5.2 Components

#### A. Performance Analyzer (`services/content_recycler.py`)

```python
class PerformanceAnalyzer:
    def score_post(self, post: PostMetrics) -> float:
        """
        Composite score: views×0.3 + likes×0.2 + comments×0.25 + shares×0.25
        Normalized to percentile within platform + account
        """
    
    def get_recyclable_posts(
        self,
        min_percentile: float = 0.80,   # Top 20%
        min_age_days: int = 30,          # Cooldown
        max_recycles: int = 3,           # Max times a post can be recycled
        exclude_tags: List[str] = None,  # e.g., ["valentines", "event"]
    ) -> List[RecyclablePost]:
        """Return posts eligible for recycling"""
```

#### B. Evergreen Classifier

```python
class EvergreenClassifier:
    async def classify(self, post: PostData) -> EvergreenResult:
        """
        Uses GPT to classify content as evergreen vs time-sensitive.
        
        Rules-based pre-filter:
        - Contains date references → time-sensitive
        - Contains "today", "this week", "happening now" → time-sensitive
        - Holiday-specific after the holiday → time-sensitive
        
        GPT classification for ambiguous cases:
        - Prompt: "Is this social media post evergreen or time-sensitive?"
        - Returns: {is_evergreen: bool, confidence: float, reason: str}
        """
    
    ALWAYS_EXCLUDE_KEYWORDS = [
        "valentine", "christmas", "new year", "black friday",
        "today only", "this week", "happening now", "live at",
        "breaking", "just announced"
    ]
```

#### C. Caption Refresher

```python
class CaptionRefresher:
    async def refresh(self, original_caption: str, platform: str) -> str:
        """
        GPT rewrites the caption with:
        - New hook (first line)
        - Same core message
        - Updated hashtags (trending ones)
        - Platform-appropriate tone
        
        Prompt: "Rewrite this {platform} caption with a fresh hook.
                 Keep the same message but make it feel new.
                 Original: {caption}"
        """
```

#### D. Recycling Scheduler (`services/recycling_scheduler.py`)

```python
class RecyclingScheduler:
    async def run_recycling_cycle(self):
        """
        Daily cron job:
        1. Get recyclable posts (top 20%, past cooldown)
        2. Filter through evergreen classifier
        3. Refresh captions
        4. Schedule via PostScheduler at smart times
        5. Record recycle event
        """
    
    def select_target_account(self, original_account_id: str, platform: str) -> str:
        """
        Strategy for multi-account recycling:
        - First recycle: same account
        - Second recycle: secondary account on same platform
        - Third recycle: tertiary account
        """
```

### 5.3 Database Schema

```sql
CREATE TABLE content_recycle_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_post_id UUID REFERENCES scheduled_posts(id),
    media_id UUID REFERENCES media(id),
    platform VARCHAR(20) NOT NULL,
    original_account_id VARCHAR(50),
    original_caption TEXT,
    engagement_score FLOAT,
    engagement_percentile FLOAT,
    is_evergreen BOOLEAN DEFAULT TRUE,
    evergreen_confidence FLOAT,
    evergreen_reason TEXT,
    recycle_count INT DEFAULT 0,
    max_recycles INT DEFAULT 3,
    last_recycled_at TIMESTAMPTZ,
    cooldown_days INT DEFAULT 45,
    excluded BOOLEAN DEFAULT FALSE,
    exclude_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE recycle_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id UUID REFERENCES content_recycle_pool(id),
    recycled_post_id UUID REFERENCES scheduled_posts(id),
    target_account_id VARCHAR(50),
    refreshed_caption TEXT,
    scheduled_time TIMESTAMPTZ,
    performance_vs_original FLOAT,  -- e.g., 0.75 = 75% of original engagement
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recycle_eligible ON content_recycle_pool(
    platform, is_evergreen, excluded, recycle_count, last_recycled_at
);
```

### 5.4 Configuration

```python
RECYCLE_CONFIG = {
    "min_percentile": 0.80,          # Top 20% of posts
    "cooldown_days": 45,             # Minimum days between recycles
    "max_recycles_per_post": 3,      # Max times a post can be recycled
    "max_recycles_per_day": 2,       # Don't flood with recycled content
    "recycle_ratio": 0.3,            # Max 30% of scheduled posts can be recycled
    "cross_account_after": 1,        # Cross-post to other accounts after 1st recycle
    "refresh_caption": True,         # AI-rewrite captions
    "auto_exclude_after_days": 180,  # Stop recycling after 6 months
}
```

## 6. API Endpoints

```
GET  /api/recycle/pool                — View all recyclable content
GET  /api/recycle/pool/:id            — View single recyclable post details
POST /api/recycle/pool/:id/exclude    — Manually exclude a post from recycling
POST /api/recycle/pool/:id/force      — Force-recycle a specific post now
POST /api/recycle/run                 — Trigger a recycling cycle manually
GET  /api/recycle/history             — View recycle history with performance comparison
GET  /api/recycle/settings            — Get current recycle configuration
PUT  /api/recycle/settings            — Update recycle configuration
```

## 7. Cron Jobs

| Job | Frequency | Description |
|-----|-----------|-------------|
| `score_posted_content` | Every 12 hours | Update engagement scores for all posted content |
| `classify_evergreen` | Daily at 2am | Run evergreen classifier on new posts |
| `run_recycling_cycle` | Daily at 4am | Select and schedule recycled posts |

## 8. Multi-Account Strategy

With 4 TikTok + 4 Instagram accounts, recycling across accounts maximizes reach:

```
Recycle #1 (Day 45):  Same account, refreshed caption
Recycle #2 (Day 90):  Secondary account (e.g., @the_isaiah_dupree → @dupree_isaiah)
Recycle #3 (Day 135): Tertiary account, different caption angle
```

## 9. Rollout Plan

1. **Phase 1:** Performance scoring + DB schema + recyclable pool
2. **Phase 2:** Evergreen classifier (rules-based + GPT)
3. **Phase 3:** Caption refresher + scheduling integration
4. **Phase 4:** Multi-account cross-posting
5. **Phase 5:** Dashboard UI for managing recycle pool

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Platform penalizes reposts | Refresh captions; vary posting times; minimum 45-day cooldown |
| AI misclassifies time-sensitive as evergreen | Keyword pre-filter + manual exclude option |
| Recycled content underperforms | Track performance_vs_original; auto-exclude if < 30% of original |
| Content fatigue on followers | Cap at 30% recycled content; spread across accounts |

## 11. Out of Scope (v1)

- Video re-editing (different cuts, intros)
- A/B testing recycled vs original captions
- Audience overlap detection between accounts
