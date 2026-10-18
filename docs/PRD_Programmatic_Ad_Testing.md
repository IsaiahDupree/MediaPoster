# PRD: Programmatic Meta Ads Testing Based on Transcript

## Overview

Automated system to generate, test, and optimize video ads at scale via **Meta Ads Manager API** by varying transcript-derived elements (hooks, CTAs, pain points, benefits) and measuring performance with Meta's native analytics.

## Problem Statement

Manual ad testing is slow and expensive. Advertisers need to:
- Test 50-100+ ad variations quickly via Meta Ads
- Identify winning hooks, CTAs, and messaging using Meta's A/B testing
- Optimize based on real Meta Ads performance data (CPM, CPC, ROAS)
- Scale winning creatives across Facebook, Instagram, and Audience Network

## Core Concept

```
Transcript → Extract Elements → Generate Variations → Render Videos → Upload to Meta → Create Ad Sets → A/B Test → Measure → Learn
```

## Meta Ads Structure

```
Campaign (Objective: Conversions/Traffic/Engagement)
├── Ad Set 1 (Audience A, Budget $X)
│   ├── Ad Variation 1 (Hook A)
│   ├── Ad Variation 2 (Hook B)
│   └── Ad Variation 3 (Hook C)
├── Ad Set 2 (Audience B, Budget $X)
│   ├── Ad Variation 1 (Hook A)
│   └── Ad Variation 2 (Hook B)
└── [Dynamic Creative Testing]
    └── Meta auto-combines: hooks × CTAs × thumbnails
```

## Meta Ads API Prerequisites

| Requirement | Description |
|-------------|-------------|
| Business Manager | Meta Business Manager account |
| Ad Account | Active ad account with payment method |
| App | Facebook App with `ads_management` permission |
| Access Token | System User token with `ads_management`, `ads_read` |
| Pixel | Meta Pixel installed for conversion tracking |
| Page | Facebook Page for ad delivery |

## Features

### AD-001: Transcript Element Extraction
**Priority:** P0 (Critical)

Extract testable elements from video transcripts using AI.

| Element | Description | Example |
|---------|-------------|---------|
| Hook | First 3 seconds / opening line | "Stop scrolling if you want to 10x your reach" |
| Pain Point | Problem being addressed | "Tired of posting and getting zero engagement?" |
| Benefit | Value proposition | "Get 1000 followers in 30 days" |
| CTA | Call to action | "Link in bio", "Comment 'YES' below" |
| Social Proof | Credibility markers | "I've helped 500+ creators..." |
| Objection Handler | Addresses doubts | "Even if you're just starting out" |

**API:**
```
POST /api/ad-testing/extract
  - transcript: string
  - video_id: string (optional)

Returns:
  - hooks: string[]
  - pain_points: string[]
  - benefits: string[]
  - ctas: string[]
  - social_proofs: string[]
```

### AD-002: Variation Generator
**Priority:** P0 (Critical)

Generate ad variations by combining elements.

| Strategy | Description |
|----------|-------------|
| Hook swap | Same video, different opening text overlay |
| CTA swap | Same content, different call to action |
| Pain-first vs Benefit-first | Reorder messaging structure |
| Length variants | 15s, 30s, 60s cuts of same content |
| Platform optimization | Aspect ratio + pacing for TikTok/Reels/Shorts |

**API:**
```
POST /api/ad-testing/generate-variations
  - base_video_id: string
  - elements: {hooks: [], ctas: [], ...}
  - strategy: "hook_swap" | "cta_swap" | "matrix" | "ai_remix"
  - count: number (max variations to generate)

Returns:
  - variations: [{id, description, elements_used, render_spec}]
```

### AD-003: Batch Video Rendering
**Priority:** P0 (Critical)

Render variations at scale using Remotion or Sora.

| Requirement | Description |
|-------------|-------------|
| Text overlay injection | Add hook/CTA text to video |
| Voiceover swap | Replace audio with AI voice variations |
| B-roll substitution | Swap background footage |
| Parallel rendering | Render 10+ videos concurrently |
| Output formats | MP4 optimized for each platform |

**Integration:** Uses existing Remotion worker + Sora pipeline

### AD-004: Meta Ads Campaign Deployment
**Priority:** P0 (Critical)

Deploy ad variations via Meta Marketing API.

| Step | API Endpoint | Description |
|------|--------------|-------------|
| 1. Upload Video | `POST /{ad-account-id}/advideos` | Upload video creative to Meta |
| 2. Create Campaign | `POST /{ad-account-id}/campaigns` | Set objective (CONVERSIONS, TRAFFIC, etc.) |
| 3. Create Ad Set | `POST /{ad-account-id}/adsets` | Define audience, budget, schedule |
| 4. Create Ad Creative | `POST /{ad-account-id}/adcreatives` | Link video + copy + CTA |
| 5. Create Ad | `POST /{ad-account-id}/ads` | Activate ad in ad set |

**Placements:**
| Placement | Format | Aspect Ratio |
|-----------|--------|--------------|
| Facebook Feed | Video | 1:1, 4:5 |
| Instagram Feed | Video | 1:1, 4:5 |
| Instagram Reels | Video | 9:16 |
| Facebook Reels | Video | 9:16 |
| Stories | Video | 9:16 |
| Audience Network | Video | 16:9, 1:1 |

**Testing Strategies:**
| Strategy | Meta Feature | Use Case |
|----------|--------------|----------|
| A/B Test | Campaign Budget Optimization (CBO) | Test 2-5 variations |
| Dynamic Creative | `asset_feed_spec` | Auto-combine hooks × CTAs × thumbnails |
| Split Test | `adset` level split | Test audiences with same creative |
| Advantage+ Creative | `advantage_creative` | Meta AI optimizes elements |

### AD-005: Meta Ads Performance Tracking
**Priority:** P0 (Critical)

Track metrics for each variation via Meta Insights API.

| Metric | Meta Field | Description |
|--------|------------|-------------|
| Impressions | `impressions` | Total ad views |
| Reach | `reach` | Unique people who saw ad |
| CPM | `cpm` | Cost per 1000 impressions |
| CPC | `cpc` | Cost per click |
| CTR | `ctr` | Click-through rate |
| Video Views | `video_views` | 3-second video views |
| ThruPlays | `video_thruplay_views` | 15s+ or complete views |
| Hook Rate | `video_p25_watched_actions` | % who watched 25% (first 3s) |
| Hold Rate | `video_p75_watched_actions` | % who watched 75% |
| Conversions | `actions` | Purchase, Lead, etc. |
| ROAS | `purchase_roas` | Return on ad spend |
| Cost per Result | `cost_per_action_type` | Cost per conversion |

**Meta Insights API:**
```python
# Fetch ad insights
GET /{ad-id}/insights?fields=impressions,reach,cpm,cpc,ctr,
    video_thruplay_views,video_p25_watched_actions,
    video_p75_watched_actions,actions,purchase_roas
    &date_preset=last_7d
    &breakdowns=publisher_platform
```

**Internal API:**
```
GET /api/meta-ads/results/{campaign_id}

Returns:
  - variations: [{
      ad_id,
      video_id,
      hook_text,
      impressions,
      cpm,
      ctr,
      hook_rate,
      hold_rate,
      conversions,
      roas,
      spend,
      status: "winner" | "loser" | "testing"
    }]
  - winner: ad_id
  - statistical_significance: float (0-1)
  - insights: string[]
```

### AD-006: AI Learning & Recommendations
**Priority:** P1 (High)

Learn from test results to improve future ads.

| Capability | Description |
|------------|-------------|
| Pattern recognition | Identify winning element combinations |
| Audience insights | Which hooks work for which demographics |
| Platform preferences | TikTok likes X, YouTube likes Y |
| Trend alignment | Correlate with trending audio/formats |

**API:**
```
GET /api/ad-testing/insights
  - account_id: string (optional)
  - platform: string (optional)

Returns:
  - top_hooks: [{text, avg_performance, sample_size}]
  - top_ctas: [{text, avg_ctr, sample_size}]
  - recommendations: string[]
  - next_test_suggestions: [{description, expected_lift}]
```

### AD-007: Meta Ads Campaign Management
**Priority:** P1 (High)

Manage ad testing campaigns via Meta API.

| Feature | Meta API | Description |
|---------|----------|-------------|
| Campaign creation | `POST /{ad-account}/campaigns` | Create with objective |
| Pause ad | `POST /{ad-id}?status=PAUSED` | Stop underperformers |
| Scale winner | `POST /{adset-id}?daily_budget=X` | Increase budget |
| Duplicate ad set | `POST /{adset-id}/copies` | Clone winning ad sets |
| Update bid | `POST /{adset-id}?bid_amount=X` | Adjust bidding |

**Campaign Objectives (Meta):**
| Objective | Use Case | Optimization Goal |
|-----------|----------|-------------------|
| `OUTCOME_SALES` | E-commerce | Purchases |
| `OUTCOME_LEADS` | Lead gen | Lead form submissions |
| `OUTCOME_TRAFFIC` | Website visits | Link clicks |
| `OUTCOME_ENGAGEMENT` | Brand awareness | ThruPlays |
| `OUTCOME_APP_PROMOTION` | App installs | Installs |

**Internal API:**
```
POST /api/meta-ads/campaigns
  - name: string
  - ad_account_id: string
  - base_video_id: string (local video to test)
  - objective: "SALES" | "LEADS" | "TRAFFIC" | "ENGAGEMENT"
  - daily_budget: number (USD cents)
  - audience: {age_min, age_max, genders, interests, custom_audiences}
  - placements: ["instagram_reels", "facebook_feed", "stories"]
  - variations_count: number
  - test_duration_days: number
  - use_dynamic_creative: boolean

GET /api/meta-ads/campaigns/{id}
PUT /api/meta-ads/campaigns/{id}/pause
PUT /api/meta-ads/campaigns/{id}/scale-winner
DELETE /api/meta-ads/campaigns/{id}
```

### AD-008: Dynamic Creative Optimization (DCO)
**Priority:** P1 (High)

Use Meta's Dynamic Creative to auto-test combinations.

| Asset Type | Max Count | Description |
|------------|-----------|-------------|
| Videos | 10 | Different hook variations |
| Images | 10 | Thumbnail options |
| Primary Text | 5 | Ad copy variations |
| Headlines | 5 | Short headlines |
| Descriptions | 5 | Link descriptions |
| CTAs | 5 | SHOP_NOW, LEARN_MORE, etc. |

**Meta DCO Request:**
```python
# Create Dynamic Creative Ad
POST /{ad-account-id}/adcreatives
{
  "name": "Hook Test - Dynamic Creative",
  "object_story_spec": {
    "page_id": "<page-id>",
    "video_data": {
      "video_id": "<video-id>",
      "message": "{{primary_text}}",
      "call_to_action": {"type": "{{cta}}"}
    }
  },
  "asset_feed_spec": {
    "videos": [
      {"video_id": "hook_v1"},
      {"video_id": "hook_v2"},
      {"video_id": "hook_v3"}
    ],
    "bodies": [
      {"text": "Stop scrolling - this changes everything"},
      {"text": "I tested 100 hooks and this won"},
      {"text": "POV: You just found your next viral video"}
    ],
    "call_to_action_types": ["SHOP_NOW", "LEARN_MORE", "SIGN_UP"]
  }
}
```

**Result:** Meta automatically tests all combinations (3 videos × 3 texts × 3 CTAs = 27 variations) and allocates budget to winners.

## Database Schema

```sql
-- Meta Ads accounts
CREATE TABLE meta_ad_accounts (
    id UUID PRIMARY KEY,
    meta_account_id TEXT NOT NULL UNIQUE,
    name TEXT,
    business_manager_id TEXT,
    pixel_id TEXT,
    page_id TEXT,
    access_token_encrypted TEXT,
    currency TEXT DEFAULT 'USD',
    timezone TEXT DEFAULT 'America/New_York',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ad test campaigns (linked to Meta)
CREATE TABLE meta_ad_campaigns (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    meta_ad_account_id UUID REFERENCES meta_ad_accounts(id),
    meta_campaign_id TEXT, -- Meta's campaign ID
    base_video_id UUID REFERENCES videos(id),
    objective TEXT DEFAULT 'OUTCOME_TRAFFIC',
    status TEXT DEFAULT 'draft', -- draft, pending, active, paused, completed
    daily_budget_cents INTEGER,
    total_budget_cents INTEGER,
    spend_cents INTEGER DEFAULT 0,
    audience JSONB, -- {age_min, age_max, genders, interests, custom_audiences}
    placements TEXT[], -- ['instagram_reels', 'facebook_feed', 'stories']
    use_dynamic_creative BOOLEAN DEFAULT false,
    test_duration_days INTEGER DEFAULT 7,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    winner_ad_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual ad variations (uploaded to Meta)
CREATE TABLE meta_ad_variations (
    id UUID PRIMARY KEY,
    campaign_id UUID REFERENCES meta_ad_campaigns(id),
    meta_ad_id TEXT, -- Meta's ad ID
    meta_adset_id TEXT, -- Meta's ad set ID
    meta_creative_id TEXT, -- Meta's creative ID
    meta_video_id TEXT, -- Meta's video asset ID
    description TEXT,
    hook_text TEXT,
    cta_text TEXT,
    primary_text TEXT,
    elements JSONB, -- {hook, cta, pain_point, benefit, ...}
    local_video_path TEXT,
    status TEXT DEFAULT 'pending', -- pending, uploading, active, paused, completed
    is_winner BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Meta Ads performance metrics (time-series)
CREATE TABLE meta_ad_metrics (
    id UUID PRIMARY KEY,
    variation_id UUID REFERENCES meta_ad_variations(id),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    date_start DATE,
    date_stop DATE,
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    spend_cents INTEGER DEFAULT 0,
    cpm_cents INTEGER, -- Cost per 1000 impressions
    cpc_cents INTEGER, -- Cost per click
    ctr FLOAT, -- Click-through rate
    clicks INTEGER DEFAULT 0,
    video_views INTEGER DEFAULT 0, -- 3-second views
    video_thruplay INTEGER DEFAULT 0, -- 15s+ views
    video_p25_watched INTEGER DEFAULT 0, -- Hook rate
    video_p50_watched INTEGER DEFAULT 0,
    video_p75_watched INTEGER DEFAULT 0, -- Hold rate
    video_p100_watched INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    conversion_value_cents INTEGER DEFAULT 0,
    roas FLOAT, -- Return on ad spend
    frequency FLOAT
);

-- Learned patterns from Meta Ads
CREATE TABLE meta_ad_insights (
    id UUID PRIMARY KEY,
    ad_account_id UUID REFERENCES meta_ad_accounts(id),
    element_type TEXT, -- hook, cta, primary_text, thumbnail
    element_text TEXT,
    placement TEXT, -- instagram_reels, facebook_feed, etc.
    audience_segment TEXT,
    sample_size INTEGER,
    avg_hook_rate FLOAT, -- video_p25_watched / impressions
    avg_hold_rate FLOAT, -- video_p75_watched / impressions
    avg_ctr FLOAT,
    avg_cpm_cents INTEGER,
    avg_roas FLOAT,
    statistical_confidence FLOAT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audience definitions for testing
CREATE TABLE meta_audiences (
    id UUID PRIMARY KEY,
    ad_account_id UUID REFERENCES meta_ad_accounts(id),
    name TEXT NOT NULL,
    meta_audience_id TEXT, -- Custom/Lookalike audience ID
    audience_type TEXT, -- custom, lookalike, saved, interest
    definition JSONB, -- {age_min, age_max, genders, interests, behaviors, custom_audiences}
    estimated_size INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Pub/Sub Topics

```python
# Meta Ads Testing Topics
META_ADS_CAMPAIGN_CREATED = "meta.ads.campaign.created"
META_ADS_CAMPAIGN_SUBMITTED = "meta.ads.campaign.submitted"  # Sent to Meta
META_ADS_CAMPAIGN_ACTIVE = "meta.ads.campaign.active"
META_ADS_CAMPAIGN_PAUSED = "meta.ads.campaign.paused"
META_ADS_CAMPAIGN_COMPLETED = "meta.ads.campaign.completed"

META_ADS_VIDEO_UPLOADING = "meta.ads.video.uploading"
META_ADS_VIDEO_UPLOADED = "meta.ads.video.uploaded"
META_ADS_VIDEO_FAILED = "meta.ads.video.failed"

META_ADS_VARIATION_CREATED = "meta.ads.variation.created"
META_ADS_VARIATION_ACTIVE = "meta.ads.variation.active"
META_ADS_VARIATION_PAUSED = "meta.ads.variation.paused"
META_ADS_VARIATION_WINNER = "meta.ads.variation.winner"
META_ADS_VARIATION_LOSER = "meta.ads.variation.loser"

META_ADS_METRICS_FETCHED = "meta.ads.metrics.fetched"
META_ADS_INSIGHTS_GENERATED = "meta.ads.insights.generated"
META_ADS_BUDGET_ADJUSTED = "meta.ads.budget.adjusted"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Meta Ads Testing System                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  Transcript  │───▶│  Variation   │───▶│    Batch     │          │
│  │  Extractor   │    │  Generator   │    │   Renderer   │          │
│  │   (OpenAI)   │    │   (AI/Rule)  │    │  (Remotion)  │          │
│  └──────────────┘    └──────────────┘    └──────┬───────┘          │
│                                                  │                   │
│                                                  ▼                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   Insights   │◀───│   Metrics    │◀───│  Meta Ads    │          │
│  │   Engine     │    │   Fetcher    │    │   Deployer   │          │
│  │   (AI/ML)    │    │ (Insights API│    │ (Marketing   │          │
│  │              │    │  + Webhooks) │    │     API)     │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Meta Platform                                │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │  Facebook  │  │ Instagram  │  │  Stories   │  │  Audience  │    │
│  │    Feed    │  │   Reels    │  │            │  │  Network   │    │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Example Workflow

### 1. Create Meta Ads Test Campaign

```bash
curl -X POST http://localhost:5555/api/meta-ads/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hook Test - Product Launch",
    "ad_account_id": "act_123456789",
    "base_video_id": "abc123",
    "objective": "OUTCOME_SALES",
    "daily_budget_cents": 5000,
    "audience": {
      "age_min": 25,
      "age_max": 45,
      "genders": [1, 2],
      "interests": [{"id": "6003139266461", "name": "Entrepreneurship"}],
      "geo_locations": {"countries": ["US"]}
    },
    "placements": ["instagram_reels", "facebook_reels", "stories"],
    "variations_count": 5,
    "test_duration_days": 7,
    "use_dynamic_creative": true
  }'
```

### 2. System Extracts Elements from Transcript

```json
{
  "hooks": [
    "This changed everything for me",
    "Stop what you're doing",
    "I can't believe this actually works",
    "POV: You just discovered this",
    "The secret nobody talks about"
  ],
  "ctas": [
    "Link in bio",
    "Comment YES below",
    "Shop now"
  ],
  "primary_texts": [
    "I tested 100 hooks and this one won...",
    "Most people don't know this trick...",
    "Here's what nobody tells you about..."
  ]
}
```

### 3. Renders 5 Video Variations (Remotion)

| Variation | Hook Text Overlay | Render Status |
|-----------|-------------------|---------------|
| v1 | "This changed everything for me" | ✅ Rendered |
| v2 | "Stop what you're doing" | ✅ Rendered |
| v3 | "I can't believe this actually works" | ✅ Rendered |
| v4 | "POV: You just discovered this" | ✅ Rendered |
| v5 | "The secret nobody talks about" | ✅ Rendered |

### 4. Uploads to Meta & Creates Campaign

```
Campaign: "Hook Test - Product Launch" (OUTCOME_SALES)
├── Ad Set: "Entrepreneurs 25-45 US" ($50/day)
│   ├── Dynamic Creative (enabled)
│   │   ├── Videos: [v1, v2, v3, v4, v5]
│   │   ├── Primary Texts: [3 variations]
│   │   └── CTAs: [SHOP_NOW, LEARN_MORE]
│   └── Placements: IG Reels, FB Reels, Stories
```

Meta auto-tests: 5 videos × 3 texts × 2 CTAs = **30 combinations**

### 5. Tracks Performance (7 days via Meta Insights API)

| Variation | Impressions | Hook Rate | CTR | ROAS | CPM | Winner? |
|-----------|-------------|-----------|-----|------|-----|---------|
| v1 | 45,000 | 32% | 1.2% | 2.1x | $8.50 | |
| v2 | 68,000 | 48% | 2.8% | 4.3x | $6.20 | 🏆 |
| v3 | 52,000 | 38% | 1.8% | 2.8x | $7.80 | |
| v4 | 61,000 | 44% | 2.2% | 3.5x | $7.00 | |
| v5 | 38,000 | 28% | 0.9% | 1.4x | $9.50 | |

**Key Metrics:**
- **Hook Rate** = video_p25_watched / impressions (first 3 seconds)
- **ROAS** = conversion_value / spend

### 6. Auto-Optimization (Meta + MediaPoster)

```json
{
  "actions_taken": [
    "Paused v5 (ROAS below 1.5x threshold)",
    "Increased budget allocation to v2 by 40%",
    "Created lookalike audience from v2 converters"
  ],
  "winner": {
    "variation_id": "v2",
    "hook": "Stop what you're doing",
    "primary_text": "I tested 100 hooks and this one won...",
    "cta": "SHOP_NOW",
    "metrics": {
      "roas": 4.3,
      "ctr": 2.8,
      "hook_rate": 48,
      "cpm": 6.20
    }
  },
  "statistical_significance": 0.96
}
```

### 7. Generates Insights & Next Steps

```json
{
  "insights": [
    "Urgency hooks ('Stop what you're doing') outperform curiosity hooks by 2.1x ROAS",
    "Instagram Reels delivers 35% lower CPM than Facebook Reels",
    "Hook rate (first 3s) is the strongest predictor of ROAS (r=0.87)",
    "SHOP_NOW CTA outperforms LEARN_MORE by 1.4x conversions"
  ],
  "next_test_suggestions": [
    {
      "description": "Test urgency hook with pain-point variations",
      "expected_lift": "+15-25% ROAS"
    },
    {
      "description": "Scale v2 to lookalike audiences",
      "expected_lift": "+20-40% reach at similar ROAS"
    }
  ]
}
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to generate 10 variations | < 5 minutes |
| Render time per variation | < 2 minutes |
| Meta video upload time | < 30 seconds |
| Campaign creation time | < 60 seconds |
| Statistical significance | 95% confidence |
| Winner identification time | < 7 days (Meta minimum) |
| ROAS improvement from testing | > 50% vs baseline |
| CPM reduction from optimization | > 20% |

## Implementation Phases

### Phase 1: Meta Ads Foundation (Week 1-2)
- [ ] AD-001: Transcript element extraction (OpenAI)
- [ ] AD-002: Variation generator (AI + rule-based)
- [ ] Database schema (meta_ad_* tables)
- [ ] Meta API authentication setup

### Phase 2: Video Pipeline (Week 3-4)
- [ ] AD-003: Batch video rendering (Remotion)
- [ ] Text overlay templates for hooks/CTAs
- [ ] Video upload to Meta (`/advideos`)

### Phase 3: Campaign Automation (Week 5-6)
- [ ] AD-004: Meta Ads campaign deployment
- [ ] AD-008: Dynamic Creative Optimization setup
- [ ] Audience targeting configuration

### Phase 4: Metrics & Optimization (Week 7-8)
- [ ] AD-005: Meta Insights API integration
- [ ] AD-006: AI insights engine
- [ ] AD-007: Auto-pause/scale automation

## Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| Meta Business Manager | Ad account access | ✅ Yes |
| Meta Marketing API | Campaign management | ✅ Yes |
| Meta Insights API | Performance metrics | ✅ Yes |
| Facebook App | API access token | ✅ Yes |
| Meta Pixel | Conversion tracking | ✅ Yes |
| Facebook Page | Ad delivery | ✅ Yes |
| OpenAI API | Element extraction, variations | ✅ Yes |
| Remotion | Video rendering | ✅ Yes |
| Supabase | Database storage | ✅ Yes |

## Meta API Rate Limits

| Endpoint | Rate Limit |
|----------|------------|
| Marketing API | 200 calls/hour/ad account |
| Insights API | 60 calls/minute/ad account |
| Video Upload | 1000/day |
| Batch Requests | 50 calls/batch |

## Environment Variables

```bash
# Meta Ads Configuration
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_ACCESS_TOKEN=your_system_user_token
META_AD_ACCOUNT_ID=act_123456789
META_PIXEL_ID=your_pixel_id
META_PAGE_ID=your_page_id
META_BUSINESS_MANAGER_ID=your_bm_id
```

## Status

| Feature | Status |
|---------|--------|
| AD-001: Transcript Extraction | 📋 Planned |
| AD-002: Variation Generator | 📋 Planned |
| AD-003: Batch Rendering | 📋 Planned |
| AD-004: Meta Campaign Deployment | 📋 Planned |
| AD-005: Meta Insights Tracking | 📋 Planned |
| AD-006: AI Insights Engine | 📋 Planned |
| AD-007: Campaign Management | 📋 Planned |
| AD-008: Dynamic Creative | 📋 Planned |

## Files (Planned)

| File | Purpose |
|------|---------|
| `Backend/services/meta_ads/client.py` | Meta Marketing API client |
| `Backend/services/meta_ads/campaign_manager.py` | Campaign CRUD operations |
| `Backend/services/meta_ads/insights_fetcher.py` | Performance metrics |
| `Backend/services/meta_ads/video_uploader.py` | Video asset upload |
| `Backend/services/meta_ads/variation_generator.py` | Hook/CTA variations |
| `Backend/services/meta_ads/optimizer.py` | Auto-pause/scale logic |
| `Backend/api/endpoints/meta_ads.py` | REST API endpoints |
| `Backend/services/workers/meta_ads_worker.py` | Pub/sub worker |
