# PRD: Multi-Account Cascade Strategy

**Status:** Proposed
**Priority:** P2 — Game-Changer
**Effort:** ~4-5 days
**Impact:** Maximize algorithmic reach across all accounts; turn 1 post into 4 platform impressions

---

## 1. Problem Statement

With 4 TikTok accounts, 4 Instagram accounts, 4 Threads accounts, and multiple accounts on other platforms, content is either posted to one account or blasted to all simultaneously. Neither approach is optimal:
- **Single account:** Leaves 3 other audiences untouched
- **Simultaneous posting:** Platforms may detect duplicate content and suppress reach

The optimal strategy is **staggered cascade**: post to the primary account first, then drip to secondary accounts over hours/days with variant captions.

## 2. Objective

Automate a cascade publishing strategy that posts content to the primary account first, monitors early performance, then automatically distributes to secondary accounts with staggered timing and refreshed captions — maximizing total reach while avoiding duplicate-content suppression.

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Total reach per piece of content | ≥ 3x vs single-account posting |
| No duplicate-content suppression | 0 flagged/suppressed posts |
| Automation rate | 100% hands-off after initial publish |
| Cross-account follower growth | ≥ 15% increase across secondary accounts |

## 4. User Stories

- **As a creator**, I want my best content to automatically spread to all my accounts without me manually reposting.
- **As a creator**, I want staggered timing so platforms don't flag it as spam.
- **As a creator**, I want each account to have a slightly different caption to feel authentic.
- **As a creator**, I want to choose which account is "primary" per platform and control the cascade delay.
- **As a creator**, I want the option to only cascade content that performs well on the primary account.

## 5. Technical Design

### 5.1 Account Hierarchy

```python
ACCOUNT_HIERARCHY = {
    "tiktok": {
        "primary":   "710",   # @isaiah_dupree (main)
        "secondary": ["243", "4508", "571"],
        # @the_isaiah_dupree, @dupree_isaiah, @soursides_is_sour
    },
    "instagram": {
        "primary":   "807",   # @the_isaiah_dupree (main)
        "secondary": ["670", "1369", "4508"],
        # @the_isaiah_dupree_, @dupree_isaiah_, @dupree_isaiah
    },
    "threads": {
        "primary":   "201",   # @the_isaiah_dupree
        "secondary": ["173", "1369", "4150"],
    },
}
```

### 5.2 Cascade Modes

| Mode | Description | Trigger |
|------|-------------|---------|
| **Always** | Cascade every post to all accounts | Default |
| **Performance-gated** | Only cascade if primary post exceeds threshold | views > 1000 in 2hrs |
| **Manual** | Queue cascade but require approval | Dashboard button |
| **Disabled** | Single-account only | Per-post override |

### 5.3 Architecture

```
Primary Post Published
       │
       ▼
┌──────────────────────┐
│  Cascade Scheduler    │  ← Monitors primary post; queues secondary posts
│  (delay: 2-6 hours)  │
└──────────┬───────────┘
           │  (if performance gate passes)
           ▼
┌──────────────────────┐
│  Caption Variant      │  ← Refresh caption per account (AI Caption Variants PRD)
│  Engine               │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Staggered Publish    │  ← Account 2 at +2hrs, Account 3 at +4hrs, Account 4 at +6hrs
│  (existing pipeline)  │
└──────────────────────┘
```

### 5.4 Database Schema

```sql
CREATE TABLE cascade_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(20) NOT NULL,
    primary_account_id VARCHAR(50) NOT NULL,
    secondary_account_ids TEXT[] NOT NULL,
    mode VARCHAR(20) DEFAULT 'always',  -- always, performance_gated, manual, disabled
    delay_minutes_min INT DEFAULT 120,   -- 2 hours minimum gap
    delay_minutes_max INT DEFAULT 360,   -- 6 hours maximum gap
    performance_gate_metric VARCHAR(20) DEFAULT 'views',
    performance_gate_threshold INT DEFAULT 1000,
    performance_gate_window_hours INT DEFAULT 2,
    refresh_caption BOOLEAN DEFAULT TRUE,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, primary_account_id)
);

CREATE TABLE cascade_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_post_id UUID REFERENCES scheduled_posts(id),
    cascade_rule_id UUID REFERENCES cascade_rules(id),
    target_account_id VARCHAR(50) NOT NULL,
    scheduled_post_id UUID REFERENCES scheduled_posts(id),  -- the created secondary post
    delay_minutes INT,
    refreshed_caption TEXT,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, gated, scheduled, posted, skipped
    gate_check_at TIMESTAMPTZ,
    gate_result JSONB,  -- {views: 1500, threshold: 1000, passed: true}
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cascade_pending ON cascade_posts(status, created_at);
```

### 5.5 Core Component (`services/cascade_publisher.py`)

```python
class CascadePublisher:
    async def on_post_published(self, original_post_id: UUID, platform: str, account_id: str):
        """
        Called after primary post publishes successfully.
        Creates cascade entries for all secondary accounts.
        """
    
    async def check_performance_gates(self):
        """
        Cron: Check if gated cascade posts should proceed.
        Pull metrics for original post; compare to threshold.
        """
    
    async def schedule_cascade_post(self, cascade: CascadePost):
        """
        Create a new scheduled_post for the secondary account.
        Stagger time = original_time + random(delay_min, delay_max).
        Refresh caption via CaptionVariantEngine.
        """
    
    async def run_cascade_cycle(self):
        """
        Cron: Process all pending cascade posts.
        For 'always' mode: schedule immediately with stagger.
        For 'performance_gated': check metrics first.
        For 'manual': skip (wait for dashboard approval).
        """
```

### 5.6 Stagger Strategy

```python
def compute_stagger_times(self, base_time: datetime, num_accounts: int, rule: CascadeRule) -> List[datetime]:
    """
    Distribute secondary posts with randomized delays.
    Account 2: base + random(2hr, 3hr)
    Account 3: base + random(4hr, 5hr)
    Account 4: base + random(6hr, 8hr)
    
    Avoids posting multiple cascade posts in the same hourly window.
    Respects Smart Posting Times if available.
    """
```

## 6. Integration Points

- **PostScheduler:** Hook into `_mark_post_published` to trigger cascade
- **CaptionVariantEngine:** Refresh captions for each secondary account
- **SmartScheduler:** Use optimal times instead of fixed delays when available
- **ContentRecycler:** Cascade posts count toward recycle history (avoid re-recycling cascaded content)

## 7. API Endpoints

```
GET  /api/cascade/rules                   — List all cascade rules
POST /api/cascade/rules                   — Create/update a cascade rule
GET  /api/cascade/posts?status=pending    — List pending cascade posts
POST /api/cascade/posts/:id/approve       — Manually approve a gated cascade
POST /api/cascade/posts/:id/skip          — Skip a cascade post
GET  /api/cascade/stats                   — Cascade performance stats
```

## 8. Rollout Plan

1. **Phase 1:** Cascade rules + DB schema + "always" mode
2. **Phase 2:** Staggered scheduling + caption refresh integration
3. **Phase 3:** Performance-gated mode + metrics checking
4. **Phase 4:** Dashboard UI for managing cascades
5. **Phase 5:** Smart time integration (cascade to optimal slots)

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Platform detects duplicate content | Different captions; 2-6hr delays; vary first frame if possible |
| Cascade of low-quality content | Performance gate mode; manual override |
| Over-posting to followers who follow multiple accounts | Audience overlap analysis (future); stagger by days not hours |
| Account-level rate limits | Respect platform posting limits; max 3 posts/day/account |

## 10. Out of Scope (v1)

- Cross-platform cascade (TikTok → Instagram Reels)
- Video re-editing per account (different intros/outros)
- Audience overlap detection
- Dynamic delay based on real-time engagement velocity
