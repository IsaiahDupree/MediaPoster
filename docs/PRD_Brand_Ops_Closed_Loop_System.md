# PRD: Brand Ops Closed-Loop System

**Version:** 1.0  
**Date:** January 23, 2026  
**Status:** Draft  

---

## Executive Summary

A closed-loop "Brand Ops" system that ingests all platform metrics + all agent actions, normalizes them, scores performance, then feeds learnings back into prompts/timing/templates for continuous improvement.

**Core Loop:**
```
Instrumentation → Ingestion → Normalization → Scoring → Learning → Prompt/Timing Updates → Publishing → Measurement
```

---

## 1. North-Star & Diagnostic Metrics

### North-Star Metric (Pick 1)
| Priority | Metric | Description |
|----------|--------|-------------|
| 1 | **Offer Conversions** | Best - direct revenue attribution |
| 2 | Qualified Leads | Email signup, DM keyword, booked call |
| 3 | Click-through | Clicks to offer pages |

### Diagnostic Metrics (Explain Why)

| Category | Metrics |
|----------|---------|
| **Attention** | Impressions, reach, 3s/5s views, avg watch time, completion rate |
| **Engagement Quality** | Saves, shares, comments per 1k views, profile visits |
| **Traffic** | Link clicks, CTR, landing page view rate |
| **Conversion** | CVR, CPA/CAC, revenue per 1k views (RPMV) |

> **Key Insight:** Stop judging posts by likes. Judge by "attention → intent → action".

---

## 2. Instrumentation & Attribution

### UTM Taxonomy
Every link must include standardized UTM parameters:

```
https://offer.example.com/page?
  utm_source={platform}
  &utm_medium=social
  &utm_campaign={campaign_name}
  &utm_content={post_id}
  &utm_term={hook_type}
  &content_id={content_id}
  &agent_version={agent_version}
  &offer={offer_slug}
```

### Required Components
- [ ] **Single tracking domain** or link shortener (click logs)
- [ ] **Pixel + server-side events** (Meta CAPI style) on offer pages
- [ ] **PostHog** for product analytics
- [ ] **content_id parameter** mapping conversions to specific post + prompt version

### Attribution Chain
Every conversion traces back to:
```
platform → post → creative → hook → prompt_version → agent_run_id → publish_time
```

---

## 3. Data Ingestion

### Platform APIs

| Platform | API | Documentation |
|----------|-----|---------------|
| **Instagram/Facebook** | Graph API Insights | [Meta for Developers](https://developers.facebook.com/docs/graph-api/reference/insights/) |
| **YouTube** | Analytics API `reports.query` | [YouTube Analytics API](https://developers.google.com/youtube/analytics/reference/reports/query) |
| **TikTok** | TikTok for Developers | [TikTok Developer Docs](https://developers.tiktok.com/doc/overview) |
| **X (Twitter)** | X API v2 | [X Developer Platform](https://developer.twitter.com/en/docs) |
| **LinkedIn** | Marketing API | [LinkedIn Marketing API](https://docs.microsoft.com/en-us/linkedin/marketing/) |

### Ingestion Cadence

| Frequency | Lookback | Purpose |
|-----------|----------|---------|
| **Hourly** | Last 48h | Fast feedback loop |
| **Daily** | Last 30d | Trend analysis |
| **Weekly** | All time | Long-term baselines |

---

## 4. Database Schema

### A) `posts` Table
```sql
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(20) NOT NULL, -- 'instagram', 'tiktok', 'youtube', 'twitter', 'linkedin'
    account_id VARCHAR(100) NOT NULL,
    post_id VARCHAR(100) NOT NULL UNIQUE,
    published_at TIMESTAMPTZ NOT NULL,
    
    -- Content references
    caption_id UUID REFERENCES captions(id),
    creative_id UUID REFERENCES creatives(id),
    hook_id UUID REFERENCES hooks(id),
    cta_id UUID REFERENCES ctas(id),
    offer_id UUID REFERENCES offers(id),
    
    -- Agent tracking
    prompt_version VARCHAR(50),
    agent_run_id UUID REFERENCES agent_runs(id),
    
    -- Metadata
    post_type VARCHAR(20), -- 'reel', 'story', 'post', 'video', 'short'
    duration_seconds INTEGER,
    hashtags TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_posts_platform ON posts(platform);
CREATE INDEX idx_posts_published_at ON posts(published_at);
CREATE INDEX idx_posts_agent_run ON posts(agent_run_id);
```

### B) `post_metrics_daily` Table
```sql
CREATE TABLE post_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES posts(id) NOT NULL,
    date DATE NOT NULL,
    
    -- Attention metrics
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    views_3s INTEGER DEFAULT 0,
    views_5s INTEGER DEFAULT 0,
    watch_time_seconds INTEGER DEFAULT 0,
    avg_view_duration_seconds DECIMAL(10,2),
    completion_rate DECIMAL(5,4),
    
    -- Engagement metrics
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    profile_visits INTEGER DEFAULT 0,
    
    -- Traffic metrics
    link_clicks INTEGER DEFAULT 0,
    ctr DECIMAL(5,4),
    
    -- Calculated
    engagement_rate DECIMAL(5,4),
    saves_per_1k_views DECIMAL(10,2),
    shares_per_1k_views DECIMAL(10,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(post_id, date)
);

CREATE INDEX idx_metrics_post_date ON post_metrics_daily(post_id, date);
CREATE INDEX idx_metrics_date ON post_metrics_daily(date);
```

### C) `traffic_events` Table
```sql
CREATE TABLE traffic_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Attribution
    content_id UUID REFERENCES posts(id),
    session_id VARCHAR(100),
    
    -- UTM parameters
    utm_source VARCHAR(50),
    utm_medium VARCHAR(50),
    utm_campaign VARCHAR(100),
    utm_content VARCHAR(100),
    utm_term VARCHAR(100),
    
    -- Event data
    event_type VARCHAR(50) NOT NULL, -- 'pageview', 'signup', 'purchase', 'lead'
    event_value DECIMAL(10,2),
    event_currency VARCHAR(3),
    
    -- Context
    page_url TEXT,
    referrer_url TEXT,
    device_type VARCHAR(20),
    country VARCHAR(2),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_content ON traffic_events(content_id);
CREATE INDEX idx_events_type ON traffic_events(event_type);
CREATE INDEX idx_events_created ON traffic_events(created_at);
```

### D) `agent_runs` Table
```sql
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Run identification
    agent_name VARCHAR(50) NOT NULL,
    agent_version VARCHAR(20) NOT NULL,
    run_type VARCHAR(50), -- 'content_generation', 'scheduling', 'analysis'
    
    -- Inputs
    prompt_template TEXT,
    prompt_version VARCHAR(50),
    input_constraints JSONB,
    assets_used UUID[],
    audience_target JSONB,
    
    -- Outputs
    generated_captions TEXT[],
    generated_titles TEXT[],
    generated_creatives UUID[],
    scheduled_time TIMESTAMPTZ,
    
    -- Tool calls & observability
    tool_calls JSONB, -- [{tool, params, result, duration_ms, error}]
    llm_calls JSONB, -- [{model, tokens_in, tokens_out, cost, duration_ms}]
    total_cost_usd DECIMAL(10,4),
    
    -- Results
    created_post_ids UUID[],
    status VARCHAR(20) NOT NULL, -- 'pending', 'running', 'success', 'failed'
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_runs_agent ON agent_runs(agent_name, agent_version);
CREATE INDEX idx_runs_status ON agent_runs(status);
CREATE INDEX idx_runs_created ON agent_runs(created_at);
```

### E) Supporting Tables
```sql
-- Hooks library
CREATE TABLE hooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hook_text TEXT NOT NULL,
    hook_family VARCHAR(50), -- 'contrarian', 'how-to', 'story', 'proof', 'curiosity'
    platform VARCHAR(20),
    performance_score DECIMAL(5,2),
    times_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CTAs library
CREATE TABLE ctas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cta_text TEXT NOT NULL,
    cta_style VARCHAR(50), -- 'comment_keyword', 'link_in_bio', 'dm_me', 'swipe_up'
    offer_bridge VARCHAR(50), -- 'pain', 'aspiration', 'mechanism'
    performance_score DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Offers
CREATE TABLE offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL UNIQUE,
    offer_url TEXT,
    product VARCHAR(50), -- 'MatrixLoop', 'KeywordRadar', 'VelloPad', 'services'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Platform baselines (for normalization)
CREATE TABLE platform_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(20) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    
    -- Rolling stats
    median_30d DECIMAL(15,4),
    p25_30d DECIMAL(15,4),
    p75_30d DECIMAL(15,4),
    mean_30d DECIMAL(15,4),
    stddev_30d DECIMAL(15,4),
    
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, account_id, metric_name)
);
```

---

## 5. Content Scoring System

### Score Formula
```
Content Score = 
    0.35 × normalized_watch_quality +
    0.25 × normalized_saves_shares +
    0.25 × normalized_clicks +
    0.15 × normalized_conversions
```

Where `normalized` = value / platform's 30-day median

### SQL Implementation
```sql
CREATE OR REPLACE FUNCTION calculate_content_score(p_post_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    v_platform VARCHAR(20);
    v_watch_quality DECIMAL;
    v_saves_shares DECIMAL;
    v_clicks DECIMAL;
    v_conversions DECIMAL;
    v_score DECIMAL;
BEGIN
    -- Get platform
    SELECT platform INTO v_platform FROM posts WHERE id = p_post_id;
    
    -- Get normalized metrics (vs 30d baseline)
    SELECT 
        COALESCE(m.completion_rate / NULLIF(b1.median_30d, 0), 1),
        COALESCE((m.saves + m.shares) / NULLIF(b2.median_30d, 0), 1),
        COALESCE(m.link_clicks / NULLIF(b3.median_30d, 0), 1),
        COALESCE(
            (SELECT COUNT(*) FROM traffic_events 
             WHERE content_id = p_post_id AND event_type = 'purchase')
            / NULLIF(b4.median_30d, 0), 1
        )
    INTO v_watch_quality, v_saves_shares, v_clicks, v_conversions
    FROM post_metrics_daily m
    LEFT JOIN platform_baselines b1 ON b1.platform = v_platform AND b1.metric_name = 'completion_rate'
    LEFT JOIN platform_baselines b2 ON b2.platform = v_platform AND b2.metric_name = 'saves_shares'
    LEFT JOIN platform_baselines b3 ON b3.platform = v_platform AND b3.metric_name = 'link_clicks'
    LEFT JOIN platform_baselines b4 ON b4.platform = v_platform AND b4.metric_name = 'conversions'
    WHERE m.post_id = p_post_id
    ORDER BY m.date DESC
    LIMIT 1;
    
    -- Calculate score
    v_score := (0.35 * v_watch_quality) + 
               (0.25 * v_saves_shares) + 
               (0.25 * v_clicks) + 
               (0.15 * v_conversions);
    
    RETURN v_score;
END;
$$ LANGUAGE plpgsql;
```

### Classification
| Tier | Criteria | Action |
|------|----------|--------|
| **Winners** | Top 20% score | Replicate hook/template |
| **Promising** | High attention, low conversion | Improve CTA/offer bridge |
| **Flops** | Bottom 20% | Stop using that hook/template |

---

## 6. Agent Observability

### Structured Logging Format
```json
{
    "agent_run_id": "uuid",
    "timestamp": "2026-01-23T10:30:00Z",
    "agent": "content_generator",
    "version": "1.2.0",
    "level": "info",
    "step": "generate_caption",
    "inputs": {
        "prompt_template": "competitor_remix_v3",
        "hook_family": "contrarian",
        "target_platform": "instagram"
    },
    "outputs": {
        "caption": "...",
        "tokens_used": 450
    },
    "duration_ms": 1250,
    "cost_usd": 0.0045
}
```

### Key Metrics to Track
| Metric | Description |
|--------|-------------|
| `run_success_rate` | % of runs completing without error |
| `publish_success_rate` | % of generated content actually published |
| `api_error_rate` | % of external API calls failing |
| `cost_per_asset` | Average USD cost per generated asset |
| `time_to_publish` | Minutes from run start to live post |

### OpenTelemetry Integration
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Trace across steps
tracer = trace.get_tracer("brand_ops.agent")

with tracer.start_as_current_span("content_generation") as span:
    span.set_attribute("agent.version", "1.2.0")
    span.set_attribute("prompt.version", "competitor_remix_v3")
    
    with tracer.start_as_current_span("research"):
        # Research step
        pass
    
    with tracer.start_as_current_span("generate"):
        # Generation step
        pass
    
    with tracer.start_as_current_span("schedule"):
        # Scheduling step
        pass
```

---

## 7. Weekly Optimization Loop

### Automated Routine

```python
# runs every Sunday at midnight
async def weekly_optimization_loop():
    # 1. Pull metrics
    await sync_platform_metrics(lookback_days=7)
    
    # 2. Update baselines
    await update_platform_baselines()
    
    # 3. Rank winners
    winners = await get_top_performers(percentile=80)
    
    # 4. Extract patterns
    patterns = await analyze_winner_patterns(winners)
    # Returns: {hook_types, cta_styles, posting_times, formats}
    
    # 5. Generate next week's plan
    plan = await generate_content_plan(
        winning_patterns=patterns,
        experiment_ratio=0.20  # 20% new experiments
    )
    
    # 6. Version prompts
    await save_prompt_version(
        version=f"v{datetime.now().strftime('%Y%m%d')}",
        patterns=patterns
    )
    
    return plan
```

### A/B Test Tags
```python
EXPERIMENT_TAGS = {
    "hook_family": ["contrarian", "how-to", "story", "proof", "curiosity", "pain"],
    "cta_style": ["comment_keyword", "link_in_bio", "dm_me", "save_for_later"],
    "offer_bridge": ["pain", "aspiration", "mechanism", "social_proof"],
    "post_time": ["morning", "midday", "evening", "night"],
    "format": ["talking_head", "broll", "text_cards", "tutorial", "story"]
}
```

---

## 8. Dashboards

### A) Executive Scorecard (Weekly)
| Metric | This Week | Last Week | Δ |
|--------|-----------|-----------|---|
| Conversions | 47 | 38 | +24% |
| Link Clicks | 1,240 | 980 | +27% |
| New Followers | 890 | 720 | +24% |
| Best Post | [link] | - | - |
| Cost per Conversion | $2.14 | $2.89 | -26% |

### B) Content Lab
- Winners by hook type
- Performance by prompt version
- Best posting times heatmap
- Format effectiveness comparison

### C) Agent Health
- Run success rate (target: >95%)
- Average cost per run
- API error rate by service
- Throughput (posts/day)

---

## 9. Technology Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| **Database** | Supabase/Postgres | Data warehouse |
| **Product Analytics** | PostHog | Offer site events |
| **ETL** | n8n / scheduled workers | Platform API pulls |
| **Dashboards** | Metabase / Looker Studio | Visualization |
| **Agent Observability** | OpenTelemetry + custom | Tracing & metrics |
| **Link Tracking** | Custom shortener / Dub.co | Click attribution |

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Set up database schema in Supabase
- [ ] Implement UTM tracking on all links
- [ ] Add PostHog to offer pages
- [ ] Create `agent_runs` logging

### Phase 2: Ingestion (Week 3-4)
- [ ] Build Instagram API integration
- [ ] Build TikTok API integration
- [ ] Build YouTube API integration
- [ ] Set up hourly/daily sync jobs

### Phase 3: Scoring (Week 5-6)
- [ ] Implement baseline calculation
- [ ] Build content scoring function
- [ ] Create winner/flop classification
- [ ] Build pattern extraction

### Phase 4: Optimization (Week 7-8)
- [ ] Implement weekly optimization loop
- [ ] Build prompt versioning system
- [ ] Create A/B test framework
- [ ] Set up automated reporting

### Phase 5: Dashboards (Week 9-10)
- [ ] Executive scorecard
- [ ] Content lab
- [ ] Agent health dashboard

---

## 11. Success Criteria

| Metric | Target | Timeline |
|--------|--------|----------|
| Attribution coverage | >90% of conversions traced | 30 days |
| Baseline accuracy | Within 10% of manual calc | 30 days |
| Winner identification | 3+ actionable patterns/week | 60 days |
| Cost per conversion | 20% reduction | 90 days |
| Agent success rate | >95% | 30 days |

---

## Appendix A: Platform-Specific Notes

### Instagram
- Use Graph API Insights for business accounts
- Metrics available: impressions, reach, saves, shares, profile_visits
- Rate limits: 200 calls/hour per user

### TikTok
- Business API required for analytics
- Video insights available after 24h
- Limited historical data access

### YouTube
- Analytics API for custom reports
- Reporting API for bulk data
- 2-day data latency

---

## Appendix B: Links & Resources

- [Meta Graph API Insights](https://developers.facebook.com/docs/graph-api/reference/insights/)
- [YouTube Analytics API](https://developers.google.com/youtube/analytics/reference/reports/query)
- [TikTok Developer Docs](https://developers.tiktok.com/doc/overview)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/overview/)
- [PostHog Documentation](https://posthog.com/docs)
