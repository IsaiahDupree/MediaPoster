# Brand Ops Implementation Roadmap

**Date:** January 23, 2026  
**PRD Reference:** `docs/PRD_Brand_Ops_Closed_Loop_System.md`

---

## Current State Analysis

### ✅ Already Exists (Leverage These)

| Component | File | Status |
|-----------|------|--------|
| **Instagram Analytics** | `services/instagram_analytics.py` | Working - RapidAPI integration |
| **YouTube Analytics** | `services/youtube_analytics_service.py` | Working - YouTube Data API v3 |
| **TikTok Analytics** | `services/tiktok_analytics_service.py` | Working - Safari automation |
| **Social Metrics Ingestion** | `services/ingestion/social_metrics.py` | Scaffolded - needs DB integration |
| **Analytics Service** | `services/analytics_service.py` | Working - URL extraction, external fetcher |
| **Social Analytics DB** | `services/social_analytics_service.py` | Working - accounts, posts, snapshots |
| **Stats Checkback Job** | `services/jobs/stats_checkback.py` | Scaffolded - needs production DB |
| **Platform Connectors** | `connectors/` | Meta, YouTube, TikTok, LinkedIn, Blotato |
| **Publishing Analytics API** | `api/endpoints/publishing_analytics.py` | Mock data - needs real implementation |
| **Competitor Analysis** | `services/competitor_analysis_service.py` | Working - GPT-4 content analysis |

### ❌ Missing (Must Build)

| Component | Priority | Effort | Description |
|-----------|----------|--------|-------------|
| **`agent_runs` table** | P0 | 2h | Track all agent executions, prompts, outputs |
| **Content Scoring Function** | P0 | 4h | `calculate_content_score()` with normalized metrics |
| **Platform Baselines** | P1 | 3h | Rolling 30-day medians per metric per platform |
| **Hooks/CTAs Library** | P1 | 2h | Store winning hooks/CTAs with performance scores |
| **Weekly Optimization Loop** | P1 | 6h | Automated winner extraction + prompt updates |
| **UTM Tracking System** | P1 | 3h | Standardized UTM generator + link shortener |
| **A/B Test Tagging** | P2 | 2h | Tag content by hook_family, cta_style, etc. |
| **OpenTelemetry Integration** | P2 | 4h | Tracing across agent steps |
| **Dashboards** | P2 | 8h | Executive scorecard, Content Lab, Agent Health |

---

## Implementation Phases

### Phase 1: Agent Observability (Week 1)
**Goal:** Track all agent actions for debugging and learning

```
□ Create agent_runs table in Supabase
□ Add logging wrapper for all agent calls
□ Track: prompt_version, inputs, outputs, tool_calls, cost, duration
□ Link agent_runs to created posts
```

**Files to Create/Modify:**
- `database/migrations/xxx_create_agent_runs.sql`
- `services/agent_logger.py` (NEW)
- `automation/sora_full_automation.py` → add run logging
- `services/competitor_analysis_service.py` → add run logging

### Phase 2: Content Scoring (Week 2)
**Goal:** Objectively rank content performance

```
□ Create platform_baselines table
□ Build baseline calculation job (daily)
□ Implement calculate_content_score() function
□ Add score to post_metrics_daily
□ Create winner/flop classification view
```

**SQL Functions Needed:**
```sql
-- Calculate rolling 30-day baselines
CREATE FUNCTION update_platform_baselines(p_platform TEXT)

-- Score individual posts
CREATE FUNCTION calculate_content_score(p_post_id UUID)

-- Classify posts
CREATE VIEW content_classification AS ...
```

### Phase 3: Learning Loop (Week 3-4)
**Goal:** Extract patterns from winners and update prompts

```
□ Create hooks table with performance tracking
□ Create ctas table with performance tracking
□ Build pattern extraction function
□ Create prompt versioning system
□ Build weekly optimization job
```

**Key Functions:**
```python
async def extract_winner_patterns(days: int = 30) -> Dict:
    """Analyze top 20% content, extract common hooks/CTAs/times"""

async def generate_next_week_plan(patterns: Dict, experiment_ratio: float = 0.2):
    """Create content plan using 80% proven + 20% experiments"""

async def version_prompt(name: str, template: str, patterns: Dict):
    """Save new prompt version with changelog"""
```

### Phase 4: Attribution & UTM (Week 5)
**Goal:** Trace every conversion back to content

```
□ Build UTM generator utility
□ Create tracking link table
□ Integrate with PostHog events
□ Build attribution report
```

**UTM Taxonomy:**
```
utm_source = platform (instagram, tiktok, youtube)
utm_medium = social
utm_campaign = campaign_name
utm_content = post_id
utm_term = hook_type
content_id = internal_content_id
agent_version = agent_version
offer = offer_slug
```

### Phase 5: Dashboards (Week 6-7)
**Goal:** Actionable visibility

```
□ Executive Scorecard (weekly summary)
□ Content Lab (winner analysis)
□ Agent Health (success rates, costs)
□ Real-time alerts for anomalies
```

---

## Quick Wins (Can Do Today)

### 1. Add Agent Run Logging to Sora Automation
```python
# In automation/sora_full_automation.py
async def log_agent_run(self, run_data: dict):
    """Log agent run to database"""
    # Insert into agent_runs table
```

### 2. Create Content Score View
```sql
CREATE VIEW content_scores AS
SELECT 
    p.id,
    p.platform,
    p.published_at,
    m.views,
    m.saves,
    m.shares,
    m.link_clicks,
    (0.35 * COALESCE(m.completion_rate, 0) +
     0.25 * COALESCE((m.saves + m.shares) / NULLIF(m.views, 0) * 1000, 0) +
     0.25 * COALESCE(m.link_clicks / NULLIF(m.views, 0) * 1000, 0) +
     0.15 * 0) as raw_score
FROM posts p
JOIN post_metrics_daily m ON m.post_id = p.id
WHERE m.date = (SELECT MAX(date) FROM post_metrics_daily WHERE post_id = p.id);
```

### 3. Start Tracking Hooks Used
Add `hook_text` and `hook_family` columns to posts table to enable future analysis.

---

## Database Migration Plan

### New Tables Needed

```sql
-- 1. Agent runs (observability)
CREATE TABLE agent_runs (...);  -- See PRD for full schema

-- 2. Platform baselines (normalization)
CREATE TABLE platform_baselines (
    id UUID PRIMARY KEY,
    platform VARCHAR(20),
    account_id VARCHAR(100),
    metric_name VARCHAR(50),
    median_30d DECIMAL,
    p25_30d DECIMAL,
    p75_30d DECIMAL,
    calculated_at TIMESTAMPTZ,
    UNIQUE(platform, account_id, metric_name)
);

-- 3. Hooks library
CREATE TABLE hooks (
    id UUID PRIMARY KEY,
    hook_text TEXT,
    hook_family VARCHAR(50),
    platform VARCHAR(20),
    performance_score DECIMAL,
    times_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ
);

-- 4. CTAs library
CREATE TABLE ctas (
    id UUID PRIMARY KEY,
    cta_text TEXT,
    cta_style VARCHAR(50),
    offer_bridge VARCHAR(50),
    performance_score DECIMAL,
    created_at TIMESTAMPTZ
);

-- 5. Prompt versions
CREATE TABLE prompt_versions (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    version VARCHAR(50),
    template TEXT,
    winning_patterns JSONB,
    created_at TIMESTAMPTZ
);
```

---

## Integration Points

### Existing → New

| Existing Component | Integrates With |
|--------------------|-----------------|
| `SoraFullAutomation` | → `agent_runs` logging |
| `CompetitorAnalysisService` | → `agent_runs` + `hooks` extraction |
| `SocialAnalyticsService` | → `platform_baselines` calculation |
| `SocialMetricsIngestionService` | → `content_scores` update |

### New → External

| New Component | External Service |
|---------------|------------------|
| UTM Tracking | PostHog events |
| Agent Tracing | OpenTelemetry Collector |
| Dashboards | Metabase / Custom |

---

## Success Metrics

| Metric | Baseline | Target | Timeline |
|--------|----------|--------|----------|
| Agent runs logged | 0% | 100% | Week 1 |
| Posts with scores | 0% | 100% | Week 2 |
| Hooks tracked | 0 | 50+ | Week 3 |
| Weekly optimization runs | 0 | 1/week | Week 4 |
| Attribution coverage | ~10% | >80% | Week 5 |

---

## Next Actions

1. **Today:** Create `agent_runs` table migration
2. **Today:** Add logging to `SoraFullAutomation`
3. **This Week:** Implement content scoring function
4. **This Week:** Start tracking hooks in posts table

---

## Files Reference

### Existing (to enhance)
- `@/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/services/analytics_service.py`
- `@/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/services/social_analytics_service.py`
- `@/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/services/instagram_analytics.py`
- `@/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/services/youtube_analytics_service.py`
- `@/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/services/tiktok_analytics_service.py`
- `@/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/services/ingestion/social_metrics.py`

### New (to create)
- `Backend/services/agent_logger.py`
- `Backend/services/content_scorer.py`
- `Backend/services/optimization_loop.py`
- `Backend/services/utm_tracker.py`
- `Backend/database/migrations/xxx_brand_ops_tables.sql`
