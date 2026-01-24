# Brand Ops Engagement System

> Closed-loop system for auto-engagement tracking and optimization across platforms.

## Overview

This system implements a **closed-loop Brand Ops workflow**:

```
Instrumentation → Ingestion → Normalization → Scoring → Learning → Prompt Updates → Publishing → Measurement
```

## Quick Start

```bash
# Auto-comment on 3 Instagram posts with full tracking
python -m services.auto_comment_service -p instagram -n 3

# Auto-comment on 3 Threads posts
python -m services.auto_comment_service -p threads -n 3

# View session summary
python -c "from services.auto_comment_service import AutoCommentService; print(AutoCommentService().get_session_summary())"
```

## Architecture

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Auto-Comment Service | `services/auto_comment_service.py` | Unified engagement service |
| Instagram Selectors | `automation/instagram_selectors.py` | Verified CSS selectors |
| Threads Selectors | `automation/threads_selectors.py` | Verified CSS selectors |
| DB Migrations | `database/migrations/013_*.sql`, `014_*.sql` | Schema definitions |

### Database Schema

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   agent_runs    │────▶│  engagement_actions  │────▶│  content_scores │
│                 │     │                      │     │                 │
│ - inputs        │     │ - platform           │     │ - attention     │
│ - outputs       │     │ - target post        │     │ - engagement    │
│ - tool calls    │     │ - context (AI vision)│     │ - traffic       │
│ - tokens/cost   │     │ - comment text       │     │ - conversion    │
│ - trace_id      │     │ - AI prompt/model    │     │ - classification│
└─────────────────┘     │ - verification       │     └─────────────────┘
                        │ - UTM tracking       │
                        └──────────────────────┘
                                  │
                                  ▼
                        ┌──────────────────────┐
                        │ engagement_daily_stats│
                        │                      │
                        │ - volume metrics     │
                        │ - success rates      │
                        │ - costs              │
                        └──────────────────────┘
```

## Data Captured Per Engagement

### Context Extraction
- **Post caption** - Full text content
- **Image description** - AI Vision analysis (GPT-4o)
- **Top comments** - For tone matching
- **Engagement stats** - Likes, comments, shares at time of action
- **Hashtags & mentions** - For relevance

### AI Generation
- **Full prompt** - Exactly what was sent to AI
- **Model & temperature** - For reproducibility
- **Token usage** - Input + output tokens
- **Cost** - USD per action

### Verification
- **Status** - pending, posted, verified, failed
- **Method** - How we verified (page_check, API)
- **Timestamp** - When verified

### Attribution
- **content_id** - Unique ID for tracking
- **UTM parameters** - Full campaign attribution
- **agent_run_id** - Link to full trace

## Content Scoring System

### Score Calculation

```
Total Score = 
    0.35 × attention_score +
    0.25 × engagement_score +
    0.25 × traffic_score +
    0.15 × conversion_score
```

### Classification

| Classification | Percentile | Action |
|---------------|------------|--------|
| **Winner** | Top 20% | Replicate hook/style |
| **Promising** | 60-80% | Test with better CTA |
| **Average** | 40-60% | Monitor |
| **Flop** | Bottom 20% | Stop this approach |

## Weekly Optimization Loop

```
Monday:
1. Pull last week's metrics
2. Update baselines per platform
3. Rank winners/flops
4. Extract winning patterns (hook, CTA, timing)
5. Update prompt versions
6. Generate next week's plan (80% proven, 20% experiments)
```

## Dashboards

### 1. Executive Scorecard (Weekly)
```sql
SELECT * FROM engagement_executive_scorecard;
```
- Total engagement actions
- Verification rate
- New follows from engagement
- Weekly AI cost

### 2. Content Lab
```sql
SELECT * FROM engagement_content_lab;
```
- Winners by prompt version
- Best posting times
- Hook effectiveness

### 3. Agent Health
```sql
SELECT * FROM agent_health_dashboard;
```
- Success/failure rates
- Avg duration
- Token usage
- Retry rates

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/engagement/auto-comment` | POST | Trigger auto-comment run |
| `/api/engagement/stats` | GET | Get engagement statistics |
| `/api/engagement/actions` | GET | List engagement actions |
| `/api/engagement/scores` | GET | Get content scores |
| `/api/agent-runs` | GET | List agent runs with traces |

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY=sk-...          # Required for AI comments
DATABASE_URL=postgres://...     # For tracking
```

### Rate Limits (per hour)
```python
{
    "threads": 20,
    "instagram": 15,
    "tiktok": 10
}
```

## Prompt Versioning

Prompts are versioned like code:

```sql
INSERT INTO prompt_versions (prompt_name, version, system_prompt, user_prompt_template)
VALUES (
    'instagram_comment',
    '1.2.0',
    'You are engaging authentically on Instagram...',
    'Comment on: {caption}\nImage: {image_description}\nTop comments: {comments}'
);
```

A/B test by tagging:
- `hook_family`: contrarian, how-to, story, proof
- `cta_style`: comment_keyword, link_in_bio, dm_me
- `offer_bridge`: pain, aspiration, mechanism

## Metrics Tracked

### North Star
- **Offer conversions** (best)
- **Qualified leads** (DM keywords, signups)
- **Click-through to offers**

### Diagnostic
| Category | Metrics |
|----------|---------|
| Attention | impressions, reach, 3s/5s views, avg watch time |
| Engagement | saves, shares, comments per 1k views |
| Traffic | link clicks, CTR, profile visits |
| Conversion | CVR, CPA, revenue per 1k views |

## File Structure

```
Backend/
├── services/
│   └── auto_comment_service.py      # Main service
├── automation/
│   ├── instagram_selectors.py       # Instagram DOM selectors
│   ├── instagram_feed_auto_commenter.py
│   ├── threads_selectors.py         # Threads DOM selectors
│   └── threads_auto_commenter.py
├── database/migrations/
│   ├── 013_auto_comment_tracking.sql
│   └── 014_brand_ops_engagement.sql # Full schema
└── docs/
    └── BRAND_OPS_ENGAGEMENT_SYSTEM.md  # This file
```

## Next Steps

1. **Run migrations**: Apply `014_brand_ops_engagement.sql`
2. **Configure accounts**: Set up platform accounts in config
3. **Start engaging**: Run auto-comment service
4. **Monitor**: Check dashboards weekly
5. **Optimize**: Update prompts based on winners

---

*Last updated: January 23, 2026*
