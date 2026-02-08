# PRD: A/B Testing Framework

**Status:** Proposed
**Priority:** P1 — Medium-Term
**Effort:** ~5-7 days
**Impact:** Data-driven content optimization; know exactly which hooks, captions, and thumbnails win

---

## 1. Problem Statement

With 4 TikTok accounts and 4 Instagram accounts, there's a natural A/B testing lab — but it's not being used systematically. Currently, the same content goes to all accounts with the same caption. There's no way to know if a different hook, caption style, or posting time would perform better without structured experimentation.

## 2. Objective

Build a framework that automatically splits content variants across accounts on the same platform, tracks performance, and declares winners — enabling data-driven decisions about hooks, captions, thumbnails, and posting strategies.

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Test throughput | ≥ 5 A/B tests per week |
| Statistical significance | 95% confidence before declaring winner |
| Engagement uplift from learnings | ≥ 20% over 90 days |
| Time to result | < 72 hours per test |

## 4. User Stories

- **As a creator**, I want to test two different captions for the same video and see which one performs better.
- **As a creator**, I want to test different posting times for the same content.
- **As a creator**, I want the system to automatically apply winning strategies to future posts.
- **As a creator**, I want a dashboard showing active tests, results, and historical learnings.

## 5. Technical Design

### 5.1 Test Types

| Test Type | Variants | Measured By |
|-----------|----------|-------------|
| **Caption A/B** | Same video, different captions | Engagement rate |
| **Hook A/B** | Same video, different first line | View-through rate |
| **Time A/B** | Same content, different posting times | Total views in 48hr |
| **Title A/B** | Same video, different titles (YouTube) | CTR, views |
| **Hashtag A/B** | Same caption, different hashtag sets | Reach, discovery views |
| **Account A/B** | Same content, different accounts | Follower growth, engagement |

### 5.2 Architecture

```
┌─────────────────────┐
│  Test Designer       │  ← Define test: type, variants, accounts
│  (API / Dashboard)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Variant Scheduler   │  ← Assigns variants to accounts/times
│  (random assignment) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Existing Publish    │  ← Posts variants via BackgroundPublisher
│  Pipeline            │
└──────────┬──────────┘
           │  After 48-72 hours
           ▼
┌─────────────────────┐
│  Results Analyzer    │  ← Pull metrics, compute significance
│  (stats engine)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Learning Store      │  ← Record what works for future reference
│  (knowledge base)    │
└─────────────────────┘
```

### 5.3 Database Schema

```sql
CREATE TABLE ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    test_type VARCHAR(50) NOT NULL,  -- caption, hook, time, title, hashtag, account
    platform VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',  -- active, completed, cancelled
    media_id UUID REFERENCES media(id),
    hypothesis TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    winner_variant_id UUID
);

CREATE TABLE ab_test_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID REFERENCES ab_tests(id) ON DELETE CASCADE,
    variant_label VARCHAR(10) NOT NULL,  -- 'A', 'B', 'C'
    account_id VARCHAR(50) NOT NULL,
    scheduled_post_id UUID REFERENCES scheduled_posts(id),
    caption TEXT,
    title TEXT,
    hashtags TEXT[],
    scheduled_time TIMESTAMPTZ,
    -- Metrics (filled after collection)
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,
    saves BIGINT,
    engagement_rate FLOAT,
    is_winner BOOLEAN DEFAULT FALSE,
    metrics_collected_at TIMESTAMPTZ
);

CREATE TABLE ab_test_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID REFERENCES ab_tests(id),
    platform VARCHAR(20),
    test_type VARCHAR(50),
    learning TEXT NOT NULL,         -- "Questions as hooks get 2.1x more comments on TikTok"
    confidence FLOAT,
    sample_size INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ab_tests_status ON ab_tests(status, platform);
CREATE INDEX idx_ab_variants_test ON ab_test_variants(test_id);
```

### 5.4 Statistical Engine

```python
class ABTestAnalyzer:
    def compute_significance(self, variant_a: Metrics, variant_b: Metrics) -> TestResult:
        """
        Two-sample z-test for engagement rate proportions.
        Returns: {significant: bool, p_value: float, winner: str, lift: float}
        Requires minimum 1000 views per variant.
        """
    
    def declare_winner(self, test_id: UUID) -> Optional[str]:
        """
        Check if test has reached significance.
        Wait minimum 48 hours before evaluating.
        Returns variant label ('A', 'B') or None if inconclusive.
        """
```

### 5.5 Multi-Account Assignment

```python
# Example: Caption A/B test on TikTok (4 accounts)
# Account 710 (@isaiah_dupree)         → Variant A (question hook)
# Account 243 (@the_isaiah_dupree)     → Variant B (bold claim hook)
# Account 4508 (@dupree_isaiah)        → Variant A (question hook)
# Account 571 (@soursides_is_sour)     → Variant B (bold claim hook)
```

## 6. API Endpoints

```
POST /api/ab-tests                    — Create a new A/B test
GET  /api/ab-tests                    — List all tests (filter by status)
GET  /api/ab-tests/:id               — Get test details + results
POST /api/ab-tests/:id/collect        — Force metrics collection
POST /api/ab-tests/:id/declare        — Force declare winner
GET  /api/ab-tests/learnings          — Browse all learnings
```

## 7. Rollout Plan

1. **Phase 1:** DB schema + test creation API
2. **Phase 2:** Variant scheduler + publish pipeline integration
3. **Phase 3:** Metrics collection + statistical analysis
4. **Phase 4:** Dashboard UI for managing tests and viewing results
5. **Phase 5:** Auto-apply learnings to future posts

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Different accounts have different follower counts | Normalize by engagement rate, not absolute numbers |
| Insufficient sample size | Require minimum 1000 views before evaluation |
| External factors (trending audio, algorithm changes) | Run tests simultaneously; account for time-of-day |
| Too many tests dilute content strategy | Cap at 5 active tests; prioritize high-value tests |

## 9. Out of Scope (v1)

- Multivariate testing (3+ variants)
- Automatic test generation
- Thumbnail A/B testing (requires platform-specific thumbnail upload)
- Statistical power calculation for test planning
