# Ad Creative Testing Pipeline (ACTP)

## Overview

An automated system that generates video ad creatives, tests them organically on social platforms, identifies winners, allocates small ad budgets to top performers, and iterates — continuously finding winning angles through data-driven creative testing.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ACTP Orchestrator                         │
│  (Pipeline Controller - manages rounds, state, decisions)   │
└──────────┬──────────┬──────────┬──────────┬─────────────────┘
           │          │          │          │
    ┌──────▼──┐ ┌─────▼────┐ ┌──▼─────┐ ┌─▼──────────┐
    │ Creative │ │ Organic  │ │ Winner │ │ Ad Spend   │
    │ Engine   │ │ Publisher│ │ Picker │ │ Deployer   │
    └──────────┘ └──────────┘ └────────┘ └────────────┘
         │            │           │            │
    ┌────▼────┐  ┌────▼────┐ ┌───▼───┐  ┌────▼─────┐
    │Remotion │  │MediaPost│ │Analyt │  │Meta Ads  │
    │Sora/Veo3│  │YouTube  │ │ics    │  │TikTok Ads│
    │Nano Ban │  │TikTok   │ │Engine │  │YouTube   │
    └─────────┘  │Instagram│ └───────┘  └──────────┘
                 │Safari   │
                 └─────────┘
```

## Core Loop

### Round 1: Generate & Test Organically
1. **Input**: Offer/product from WaitlistLab, angle hypotheses
2. **Generate**: Create 5-10 video variations using Remotion + Sora/Veo3/Nano Banana
3. **Publish**: Post organically to YouTube Shorts + TikTok
4. **Wait**: 24-48 hours for organic signal
5. **Measure**: Views, engagement rate, watch time, comments sentiment
6. **Select**: Top 2-3 organic performers

### Round 2: Small Budget Ad Test ($5 each)
1. **Deploy**: Winners from Round 1 get $5 ad spend on Meta/TikTok Ads
2. **Target**: Aligned to offer audience from WaitlistLab
3. **Wait**: 24-48 hours for ad metrics
4. **Measure**: CTR, CPC, hook rate, hold rate, conversion
5. **Select**: Top 1-2 ad performers

### Round 3+: Iterate & Scale
1. **Analyze**: What angles/hooks/CTAs won and why
2. **Generate**: New variations based on winning elements (hook_swap, cta_swap, ai_remix)
3. **Test**: Repeat Round 1-2 with new variations
4. **Scale**: Gradually increase budget on proven winners ($5 → $20 → $50 → $100)
5. **Learn**: AI learner builds pattern database of what works

## Existing Infrastructure (Already Built)

### Remotion (Video Generation)
- `python/services/video_generation/full_pipeline.py` — End-to-end video pipeline
- `python/services/video_generation/orchestrator.py` — Video generation orchestrator
- `python/services/video_generation/sora_runner.py` — Sora job execution with caching
- `python/services/video_providers/sora_provider.py` — Sora API adapter
- `python/services/sora_video_pipeline.py` — Multi-clip Sora+Remotion composition
- `src/service/server.ts` — Remotion render queue (render-brief handler)

### MediaPoster (Publishing & Ad Testing)
- `connectors/youtube/connector.py` — YouTube upload + metrics
- `connectors/tiktok/connector.py` — TikTok publish + analytics
- `connectors/twitter/connector.py` — Twitter publish via Blotato
- `automation/safari_tiktok_cli.py` — Safari TikTok automation
- `automation/safari_instagram_poster.py` — Safari Instagram automation
- `services/ad_testing/variation_generator.py` (AD-002) — Ad variation generation
- `services/ad_testing/campaign_deployer.py` (AD-004) — Meta Ads deployment
- `services/ad_testing/performance_tracker.py` (AD-005) — Ad performance tracking
- `services/ad_testing/campaign_manager.py` (AD-007) — Pause/scale campaigns
- `services/ad_testing/ai_learner.py` (AD-006) — AI learning from performance
- `services/ad_testing/dco_optimizer.py` — Dynamic creative optimization
- `services/ad_testing/batch_renderer.py` — Batch render creatives

### WaitlistLab (Offers & Campaigns)
- `dashboard/amd/campaigns/` — Campaign management
- `dashboard/landings/` — Landing pages for offers

## New Components to Build

### 1. Pipeline Orchestrator (`orchestrator.py`)
Central controller managing the full test loop lifecycle:
- Create test rounds
- Track state across generate → publish → measure → select → iterate
- Schedule actions with proper wait times
- Persist state to database (Supabase)

### 2. Creative Engine (`creative_engine.py`)
Bridges to Remotion's video generation:
- Accept offer/angle/hook inputs
- Generate video briefs for Remotion pipeline
- Support multiple video providers: Sora, Veo3, Nano Banana
- Create variations from winning elements
- Manage video asset storage

### 3. Organic Publisher (`organic_publisher.py`)
Manages organic posting via MediaPoster connectors:
- Post to YouTube Shorts (via YouTube connector or Safari)
- Post to TikTok (via TikTok connector or Safari automation)
- Post to Instagram Reels (via Safari automation)
- Track post IDs for analytics collection
- Handle rate limiting and scheduling

### 4. Analytics Collector (`analytics_collector.py`)
Gathers and normalizes metrics from all platforms:
- YouTube: views, likes, comments, watch time, CTR
- TikTok: views, likes, comments, shares, completion rate
- Instagram: views, likes, comments, saves, reach
- Normalize to comparable scores across platforms
- Calculate composite "organic quality score"

### 5. Winner Selector (`winner_selector.py`)
Algorithm to pick winners from each round:
- Organic round: score by engagement rate + view velocity + completion rate
- Ad round: score by CTR + CPC + hook rate + hold rate
- Statistical significance checks (minimum sample sizes)
- Confidence intervals for decisions

### 6. Ad Budget Deployer (`ad_deployer.py`)
Manages ad spend allocation:
- Create campaigns aligned to WaitlistLab offers
- Start with $5 micro-budgets
- Scale winners: $5 → $20 → $50 → $100
- Auto-pause underperformers
- Support Meta Ads + TikTok Ads

### 7. Iteration Engine (`iteration_engine.py`)
Generates next-round variations from winners:
- Extract winning elements (hooks, CTAs, angles, visuals)
- Use AdVariationGenerator strategies (hook_swap, cta_swap, ai_remix)
- Mutate winning videos with new hooks/CTAs
- Track genealogy (which variations came from which winners)

### 8. Offer Connector (`offer_connector.py`)
Bridges to WaitlistLab for offer alignment:
- Fetch active offers/products
- Get target audience definitions
- Get landing page URLs for ad destinations
- Report performance back to WaitlistLab

## Data Model

### TestCampaign
```
id, name, offer_id, status (draft|generating|organic_testing|
ad_testing|iterating|scaling|completed), created_at, config
```

### TestRound
```
id, campaign_id, round_number, round_type (organic|ad|scale),
status, budget_per_creative, started_at, completed_at
```

### Creative
```
id, campaign_id, round_id, parent_creative_id, video_url,
thumbnail_url, hook, cta, angle, target_audience,
generation_source (sora|veo3|nano_banana|remix), metadata
```

### OrganicPost
```
id, creative_id, platform (youtube|tiktok|instagram),
post_id, post_url, posted_at, metrics_json, organic_score
```

### AdDeployment
```
id, creative_id, platform (meta|tiktok_ads|youtube_ads),
campaign_id_external, ad_set_id, ad_id, budget_cents,
spend_cents, metrics_json, ad_score, status
```

### PerformanceLog
```
id, creative_id, round_id, metric_type, value,
measured_at, platform, raw_data
```

### WinnerSelection
```
id, round_id, creative_id, rank, score,
selection_reason, promoted_to_round_id
```

## API Endpoints

```
POST   /api/actp/campaigns                    — Create new test campaign
GET    /api/actp/campaigns                    — List campaigns
GET    /api/actp/campaigns/:id                — Get campaign detail
POST   /api/actp/campaigns/:id/start          — Start testing
POST   /api/actp/campaigns/:id/pause          — Pause campaign

POST   /api/actp/rounds/:id/generate          — Generate creatives for round
POST   /api/actp/rounds/:id/publish           — Publish to organic channels
POST   /api/actp/rounds/:id/collect-metrics   — Collect analytics
POST   /api/actp/rounds/:id/select-winners    — Run winner selection
POST   /api/actp/rounds/:id/deploy-ads        — Deploy ad spend

GET    /api/actp/creatives/:id                — Creative detail with metrics
GET    /api/actp/creatives/:id/lineage        — Creative genealogy tree

GET    /api/actp/analytics/dashboard          — Overall pipeline dashboard
GET    /api/actp/analytics/winning-patterns   — AI-identified winning patterns
```

## Configuration

```python
ACTP_CONFIG = {
    "organic_test": {
        "platforms": ["youtube_shorts", "tiktok"],
        "creatives_per_round": 5,
        "wait_hours": 24,
        "min_views_for_decision": 100,
    },
    "ad_test": {
        "platforms": ["meta", "tiktok_ads"],
        "budget_per_creative_cents": 500,  # $5
        "wait_hours": 48,
        "min_impressions_for_decision": 1000,
    },
    "scaling": {
        "budget_tiers_cents": [500, 2000, 5000, 10000],  # $5, $20, $50, $100
        "scale_threshold_ctr": 1.5,  # % CTR to scale up
        "pause_threshold_ctr": 0.5,  # % CTR to pause
    },
    "video_generation": {
        "providers": ["sora", "veo3", "nano_banana"],
        "default_duration_seconds": 15,
        "aspect_ratio": "9:16",  # Portrait for social
        "variations_per_angle": 3,
    },
    "iteration": {
        "max_rounds": 10,
        "strategies": ["hook_swap", "cta_swap", "ai_remix"],
        "winner_count": 3,
    },
}
```

## Tech Stack
- **Backend**: Python (FastAPI) — extends MediaPoster Backend
- **Video Gen**: Remotion + OpenAI Sora + Veo3 + Nano Banana
- **Publishing**: MediaPoster connectors + Safari automation
- **Ad Platforms**: Meta Marketing API + TikTok Ads API
- **Database**: Supabase (PostgreSQL)
- **Analytics**: MediaPoster analytics engine
- **AI**: OpenAI GPT-4o for brief generation, pattern analysis

## Success Metrics
- Time from offer → first organic test < 2 hours
- Time from organic results → ad deployment < 1 hour
- Find winning angle within 3-5 rounds
- CPA reduction of 30%+ vs manual creative testing
- 10x more creative variations tested per week
