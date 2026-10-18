# PRD: Meta Ads Autopilot

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** T5.1 Advertising & Revenue  
**Effort:** 8-10 weeks  
**Priority:** 🟢 Medium (Revenue Generation)

---

## Executive Summary

Build a Meta Ads automation system that programmatically tests ad creatives at scale, optimizes campaigns using AI-powered rules, and generates performance insights—inspired by WaitlistLab's Ads Autopilot.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           META ADS AUTOPILOT                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         CREATIVE PIPELINE                                    │   │
│  │                                                                              │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │   │
│  │  │   Content    │───▶│   Script     │───▶│  Variation   │───▶│  Batch   │  │   │
│  │  │   Library    │    │  Extractor   │    │  Generator   │    │  Render  │  │   │
│  │  │              │    │              │    │              │    │          │  │   │
│  │  │  Existing    │    │  Hooks       │    │  50-100      │    │ Remotion │  │   │
│  │  │  Videos      │    │  CTAs        │    │  Variants    │    │          │  │   │
│  │  │              │    │  Pain Points │    │              │    │          │  │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘  │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────┬───────────────────────────────┘   │
│                                                 │                                    │
│                                                 ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         META PUBLISHER                                       │   │
│  │                                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    Marketing API v21.0                              │   │   │
│  │  │                                                                     │   │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │   │
│  │  │  │ Campaign │  │  Ad Set  │  │   Ad     │  │    Video         │   │   │   │
│  │  │  │  Create  │  │  Create  │  │  Create  │  │    Upload        │   │   │   │
│  │  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │   │   │
│  │  │       │             │             │                  │             │   │   │
│  │  │       └─────────────┴─────────────┴──────────────────┘             │   │   │
│  │  │                           │                                        │   │   │
│  │  │                           ▼                                        │   │   │
│  │  │              Campaign Structure:                                   │   │   │
│  │  │              ├── Campaign (Conversions)                           │   │   │
│  │  │              │   ├── Ad Set (Audience A)                          │   │   │
│  │  │              │   │   ├── Ad (Creative V1)                         │   │   │
│  │  │              │   │   ├── Ad (Creative V2)                         │   │   │
│  │  │              │   │   └── Ad (Creative V3)                         │   │   │
│  │  │              │   └── Ad Set (Audience B)                          │   │   │
│  │  │              │       └── ... (DCO variations)                     │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────┬───────────────────────────────┘   │
│                                                 │                                    │
│                          ┌──────────────────────┴──────────────────────┐            │
│                          ▼                                             ▼            │
│  ┌───────────────────────────────────────┐  ┌───────────────────────────────────┐  │
│  │           INSIGHTS FETCHER            │  │         CONVERSION API            │  │
│  │                                       │  │                                   │  │
│  │  Pull every 6 hours:                  │  │  Server-side tracking:            │  │
│  │  • Impressions, Reach                 │  │  • Purchase events                │  │
│  │  • CTR, CPC, CPM                      │  │  • Lead events                    │  │
│  │  • ROAS, Conversions                  │  │  • Add to cart                    │  │
│  │  • Hook Rate (3s views)               │  │  • Custom events                  │  │
│  │  • Video watch %                      │  │                                   │  │
│  │                                       │  │  Pixel ID: {META_PIXEL_ID}        │  │
│  └───────────────────────────────────────┘  └───────────────────────────────────┘  │
│                          │                                                          │
│                          ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         RULES ENGINE                                         │   │
│  │                                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │  Rule: "Pause Low Performers"                                       │   │   │
│  │  │  IF: CTR < 0.5% AND Spend > $20 AND Impressions > 1000              │   │   │
│  │  │  THEN: Pause ad                                                     │   │   │
│  │  │  COOLDOWN: 24 hours                                                 │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │  Rule: "Scale Winners"                                              │   │   │
│  │  │  IF: ROAS > 3.0 AND Spend > $50 AND Conversions > 5                 │   │   │
│  │  │  THEN: Increase budget 20%                                          │   │   │
│  │  │  MAX_BUDGET: $500/day                                               │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │  Rule: "Fatigue Detection"                                          │   │   │
│  │  │  IF: Frequency > 2.5 AND CTR dropped 30% in 3 days                  │   │   │
│  │  │  THEN: Pause ad, suggest refresh                                    │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────┬───────────────────────────────┘   │
│                                                 │                                    │
│                                                 ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         AI INSIGHTS ENGINE                                   │   │
│  │                                                                              │   │
│  │  ┌───────────────────────────────────────────────────────────────────────┐ │   │
│  │  │  Weekly Analysis (GPT-4):                                             │ │   │
│  │  │                                                                       │ │   │
│  │  │  • Top performing hooks: "Question format outperforms statements"    │ │   │
│  │  │  • Best audiences: "25-34 females, interest: entrepreneurship"       │ │   │
│  │  │  • Optimal posting times: "6-9 AM EST, 7-10 PM EST"                  │ │   │
│  │  │  • Creative patterns: "UGC style +45% CTR vs polished"               │ │   │
│  │  │  • Budget recommendations: "Reallocate $X from Campaign A to B"      │ │   │
│  │  │                                                                       │ │   │
│  │  └───────────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         HUMAN REVIEW GATE                                    │   │
│  │                                                                              │   │
│  │   Actions requiring approval:        │  Auto-approved:                      │   │
│  │   • Budget increase > $100           │  • Pause low performers              │   │
│  │   • New campaign creation            │  • Minor budget adjustments          │   │
│  │   • Audience expansion               │  • Ad status changes                 │   │
│  │   • Creative with new messaging      │  • Insights generation               │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Migration: 20260201_meta_ads_autopilot.sql

-- Offers (products/services being advertised)
CREATE TABLE ad_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    landing_page_url TEXT,
    price DECIMAL,
    target_cpa DECIMAL,
    target_roas DECIMAL,
    
    -- Tracking
    pixel_id VARCHAR(50),
    conversion_event VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Meta Objects (synced from Meta API)
CREATE TABLE meta_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meta_id VARCHAR(50) NOT NULL UNIQUE,
    object_type VARCHAR(20) NOT NULL, -- campaign, adset, ad
    parent_meta_id VARCHAR(50),
    
    -- From Meta
    name VARCHAR(255),
    status VARCHAR(20), -- ACTIVE, PAUSED, DELETED
    effective_status VARCHAR(50),
    
    -- Config
    config JSONB,
    -- For campaigns: {objective, buying_type, budget_optimization}
    -- For adsets: {targeting, budget, bid_strategy, placements}
    -- For ads: {creative_id, tracking_specs}
    
    -- Sync
    last_synced_at TIMESTAMPTZ,
    sync_error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Creative Specs
CREATE TABLE creative_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES ad_offers(id),
    
    -- Creative info
    name VARCHAR(255),
    creative_type VARCHAR(20), -- video, image, carousel
    
    -- Source content
    source_content_id UUID, -- Reference to content library
    source_video_path TEXT,
    
    -- Variations
    headline VARCHAR(255),
    body_text TEXT,
    cta VARCHAR(50),
    link_url TEXT,
    
    -- Extracted elements
    hook_text TEXT,
    pain_points TEXT[],
    
    -- Meta upload
    meta_video_id VARCHAR(50),
    thumbnail_url TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft', -- draft, rendering, ready, published
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance Daily (metrics by day)
CREATE TABLE performance_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meta_object_id UUID REFERENCES meta_objects(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Spend
    spend DECIMAL,
    
    -- Reach
    impressions INTEGER,
    reach INTEGER,
    frequency DECIMAL,
    
    -- Engagement
    clicks INTEGER,
    ctr DECIMAL,
    cpc DECIMAL,
    cpm DECIMAL,
    
    -- Video metrics
    video_views INTEGER,
    video_p25 INTEGER,
    video_p50 INTEGER,
    video_p75 INTEGER,
    video_p100 INTEGER,
    hook_rate DECIMAL, -- 3-second views / impressions
    
    -- Conversions
    conversions INTEGER,
    conversion_value DECIMAL,
    cpa DECIMAL,
    roas DECIMAL,
    
    -- Quality
    quality_ranking VARCHAR(20),
    engagement_ranking VARCHAR(20),
    conversion_ranking VARCHAR(20),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(meta_object_id, date)
);

-- Autopilot Rules
CREATE TABLE autopilot_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Scope
    applies_to VARCHAR(20) NOT NULL, -- campaign, adset, ad
    offer_ids UUID[], -- NULL = all offers
    
    -- Conditions (AND logic)
    conditions JSONB NOT NULL,
    -- Example: {
    --   "ctr": {"operator": "lt", "value": 0.5},
    --   "spend": {"operator": "gt", "value": 20},
    --   "impressions": {"operator": "gt", "value": 1000}
    -- }
    
    -- Action
    action_type VARCHAR(50) NOT NULL, -- pause, enable, increase_budget, decrease_budget, notify
    action_config JSONB NOT NULL,
    -- Example: {"percent": 20, "max_budget": 500}
    
    -- Guardrails
    cooldown_hours INTEGER DEFAULT 24,
    requires_approval BOOLEAN DEFAULT FALSE,
    max_daily_executions INTEGER DEFAULT 10,
    
    -- Stats
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Autopilot Actions (pending/executed)
CREATE TABLE autopilot_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES autopilot_rules(id),
    meta_object_id UUID REFERENCES meta_objects(id),
    
    -- Action details
    action_type VARCHAR(50) NOT NULL,
    action_details JSONB NOT NULL,
    reason TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, executed, failed
    requires_approval BOOLEAN DEFAULT FALSE,
    
    -- Approval
    approved_by VARCHAR(255),
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    
    -- Execution
    executed_at TIMESTAMPTZ,
    execution_result JSONB,
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Insights
CREATE TABLE ai_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES ad_offers(id),
    
    insight_type VARCHAR(50), -- weekly_summary, pattern, recommendation, alert
    
    -- Content
    title VARCHAR(255),
    summary TEXT,
    details JSONB,
    
    -- Data range
    date_from DATE,
    date_to DATE,
    
    -- Action items
    recommendations JSONB,
    -- [{action, priority, expected_impact}]
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Experiments (A/B tests)
CREATE TABLE ad_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES ad_offers(id),
    
    name VARCHAR(255),
    hypothesis TEXT,
    
    -- Variants
    control_meta_id VARCHAR(50),
    variant_meta_ids VARCHAR(50)[],
    
    -- Test config
    test_type VARCHAR(50), -- creative, audience, placement, bid
    success_metric VARCHAR(50), -- ctr, cpa, roas
    min_sample_size INTEGER,
    confidence_level DECIMAL DEFAULT 0.95,
    
    -- Status
    status VARCHAR(20) DEFAULT 'running', -- running, completed, stopped
    winner_meta_id VARCHAR(50),
    
    -- Results
    results JSONB,
    
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_meta_objects_type ON meta_objects(object_type);
CREATE INDEX idx_meta_objects_status ON meta_objects(status);
CREATE INDEX idx_performance_date ON performance_daily(date);
CREATE INDEX idx_performance_object ON performance_daily(meta_object_id);
CREATE INDEX idx_actions_status ON autopilot_actions(status);
```

---

## API Endpoints

### Dashboard

```yaml
# GET /api/ads-autopilot/health
# Health check for all integrations
Response:
  supabase: "connected"
  meta: "connected"
  openai: "connected"
  last_sync: "2026-02-01T12:00:00Z"

# GET /api/ads-autopilot/dashboard
# Main dashboard data
Query:
  offer_id: uuid (optional)
  date_from: date
  date_to: date
Response:
  summary:
    total_spend: number
    total_conversions: number
    avg_cpa: number
    avg_roas: number
  campaigns: Campaign[]
  top_performers: Ad[]
  alerts: Alert[]
  pending_actions: Action[]
```

### Campaigns

```yaml
# GET /api/meta-ads/campaigns
# List all campaigns
Response:
  campaigns: Campaign[]

# POST /api/meta-ads/campaigns
# Create new campaign
Request:
  offer_id: uuid
  name: string
  objective: string
  budget: number
  start_date: date
Response:
  campaign: Campaign
  meta_campaign_id: string

# PUT /api/meta-ads/campaigns/{id}/status
# Update campaign status
Request:
  status: "ACTIVE" | "PAUSED"
Response:
  success: boolean
```

### Creatives

```yaml
# GET /api/meta-ads/creatives
# List creatives
Response:
  creatives: CreativeSpec[]

# POST /api/meta-ads/creatives/generate
# Generate creative variations
Request:
  source_content_id: uuid
  variation_count: number
  hooks: string[] (optional)
  ctas: string[] (optional)
Response:
  job_id: string
  variations_queued: number

# POST /api/meta-ads/creatives/render
# Render creative using Remotion
Request:
  creative_id: uuid
Response:
  render_job_id: string

# POST /api/meta-ads/creatives/{id}/publish
# Publish creative to Meta
Request:
  campaign_id: uuid
  adset_id: uuid
Response:
  ad_id: string
  meta_ad_id: string
```

### Rules Engine

```yaml
# GET /api/ads-autopilot/rules
# List automation rules
Response:
  rules: AutopilotRule[]

# POST /api/ads-autopilot/rules
# Create new rule
Request:
  name: string
  applies_to: string
  conditions: object
  action_type: string
  action_config: object
  requires_approval: boolean
Response:
  rule: AutopilotRule

# POST /api/ads-autopilot/rules/evaluate
# Manually trigger rule evaluation
Response:
  rules_evaluated: number
  actions_created: number
  actions_executed: number

# GET /api/ads-autopilot/actions
# List pending actions
Query:
  status: string
Response:
  actions: AutopilotAction[]

# POST /api/ads-autopilot/actions/{id}/approve
# Approve pending action

# POST /api/ads-autopilot/actions/{id}/reject
# Reject pending action
Request:
  reason: string
```

### Insights

```yaml
# GET /api/ads-autopilot/insights
# Get AI insights
Query:
  offer_id: uuid
  type: string
Response:
  insights: AIInsight[]

# POST /api/ads-autopilot/insights/generate
# Generate weekly insights
Request:
  offer_id: uuid
  date_from: date
  date_to: date
Response:
  insight: AIInsight

# POST /api/ads-autopilot/sync
# Sync data from Meta
Response:
  campaigns_synced: number
  performance_records: number
  last_sync: datetime
```

---

## Core Services

### 1. Meta Publisher
```python
# Backend/services/meta_ads/meta_publisher.py

class MetaPublisher:
    """Publish and manage Meta ads."""
    
    def __init__(self):
        self.api = FacebookAdsApi.init(
            access_token=os.environ["META_ACCESS_TOKEN"]
        )
        self.ad_account = AdAccount(os.environ["META_AD_ACCOUNT_ID"])
    
    async def create_campaign(
        self,
        name: str,
        objective: str,
        budget: float,
        budget_type: str = "daily"
    ) -> Campaign:
        """Create Meta campaign."""
        params = {
            "name": name,
            "objective": objective,
            "status": "PAUSED",
            "special_ad_categories": [],
        }
        
        if budget_type == "daily":
            params["daily_budget"] = int(budget * 100)  # Cents
        else:
            params["lifetime_budget"] = int(budget * 100)
        
        campaign = self.ad_account.create_campaign(params=params)
        return campaign
    
    async def create_adset(
        self,
        campaign_id: str,
        name: str,
        targeting: dict,
        budget: float,
        optimization_goal: str = "CONVERSIONS"
    ) -> AdSet:
        """Create ad set with targeting."""
        params = {
            "name": name,
            "campaign_id": campaign_id,
            "daily_budget": int(budget * 100),
            "billing_event": "IMPRESSIONS",
            "optimization_goal": optimization_goal,
            "targeting": targeting,
            "status": "PAUSED",
        }
        
        adset = self.ad_account.create_ad_set(params=params)
        return adset
    
    async def upload_video(self, video_path: str) -> str:
        """Upload video to Meta."""
        video = self.ad_account.create_ad_video(
            params={"file_url": video_path}
        )
        return video["id"]
    
    async def create_ad(
        self,
        adset_id: str,
        creative_spec: CreativeSpec
    ) -> Ad:
        """Create ad with creative."""
        creative_params = {
            "video_data": {
                "video_id": creative_spec.meta_video_id,
                "title": creative_spec.headline,
                "message": creative_spec.body_text,
                "call_to_action": {
                    "type": creative_spec.cta,
                    "value": {"link": creative_spec.link_url}
                }
            }
        }
        
        creative = self.ad_account.create_ad_creative(
            params=creative_params
        )
        
        ad = self.ad_account.create_ad(params={
            "name": creative_spec.name,
            "adset_id": adset_id,
            "creative": {"creative_id": creative["id"]},
            "status": "PAUSED"
        })
        
        return ad
```

### 2. Insights Fetcher
```python
# Backend/services/meta_ads/insights_fetcher.py

class InsightsFetcher:
    """Fetch performance data from Meta."""
    
    METRICS = [
        "spend", "impressions", "reach", "frequency",
        "clicks", "ctr", "cpc", "cpm",
        "video_p25_watched_actions", "video_p50_watched_actions",
        "video_p75_watched_actions", "video_p100_watched_actions",
        "actions", "action_values", "cost_per_action_type"
    ]
    
    async def sync_insights(
        self,
        date_from: date,
        date_to: date
    ) -> int:
        """Sync insights for all objects."""
        
        # Get all campaigns
        campaigns = await self.get_campaigns()
        
        records_synced = 0
        for campaign in campaigns:
            # Sync campaign insights
            insights = await self.fetch_insights(
                campaign["id"], date_from, date_to
            )
            records_synced += await self.store_insights(
                campaign["id"], insights
            )
            
            # Sync adset insights
            for adset in campaign.get("adsets", []):
                insights = await self.fetch_insights(
                    adset["id"], date_from, date_to
                )
                records_synced += await self.store_insights(
                    adset["id"], insights
                )
                
                # Sync ad insights
                for ad in adset.get("ads", []):
                    insights = await self.fetch_insights(
                        ad["id"], date_from, date_to
                    )
                    records_synced += await self.store_insights(
                        ad["id"], insights
                    )
        
        return records_synced
    
    async def fetch_insights(
        self,
        object_id: str,
        date_from: date,
        date_to: date
    ) -> List[dict]:
        """Fetch insights for a single object."""
        obj = AdObject(object_id)
        insights = obj.get_insights(
            fields=self.METRICS,
            params={
                "time_range": {
                    "since": date_from.isoformat(),
                    "until": date_to.isoformat()
                },
                "time_increment": 1  # Daily breakdown
            }
        )
        return list(insights)
```

### 3. Rules Engine
```python
# Backend/services/meta_ads/rules_engine.py

class RulesEngine:
    """Evaluate and execute automation rules."""
    
    OPERATORS = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "gt": lambda a, b: a > b,
        "lt": lambda a, b: a < b,
        "gte": lambda a, b: a >= b,
        "lte": lambda a, b: a <= b,
    }
    
    async def evaluate_all_rules(self) -> List[AutopilotAction]:
        """Evaluate all active rules."""
        
        rules = await self.repo.get_active_rules()
        actions = []
        
        for rule in rules:
            # Get applicable objects
            objects = await self.get_objects_for_rule(rule)
            
            for obj in objects:
                # Check conditions
                if await self.evaluate_conditions(rule.conditions, obj):
                    # Check cooldown
                    if await self.is_in_cooldown(rule, obj):
                        continue
                    
                    # Create action
                    action = await self.create_action(rule, obj)
                    actions.append(action)
                    
                    # Execute if no approval required
                    if not rule.requires_approval:
                        await self.execute_action(action)
        
        return actions
    
    async def evaluate_conditions(
        self,
        conditions: dict,
        obj: MetaObject
    ) -> bool:
        """Evaluate all conditions (AND logic)."""
        
        metrics = await self.get_recent_metrics(obj.meta_id)
        
        for field, condition in conditions.items():
            operator = condition["operator"]
            value = condition["value"]
            actual = metrics.get(field)
            
            if actual is None:
                return False
            
            op_func = self.OPERATORS.get(operator)
            if not op_func(actual, value):
                return False
        
        return True
    
    async def execute_action(self, action: AutopilotAction):
        """Execute an approved action."""
        
        if action.action_type == "pause":
            await self.publisher.update_status(
                action.meta_object_id, "PAUSED"
            )
        elif action.action_type == "enable":
            await self.publisher.update_status(
                action.meta_object_id, "ACTIVE"
            )
        elif action.action_type == "increase_budget":
            percent = action.action_details.get("percent", 20)
            max_budget = action.action_details.get("max_budget")
            await self.publisher.adjust_budget(
                action.meta_object_id, percent, max_budget
            )
        
        action.status = "executed"
        action.executed_at = datetime.now()
        await self.repo.update(action)
```

### 4. Creative Factory
```python
# Backend/services/meta_ads/creative_factory.py

class CreativeFactory:
    """Generate ad creative variations."""
    
    async def generate_variations(
        self,
        source_content_id: UUID,
        count: int = 50
    ) -> List[CreativeSpec]:
        """Generate multiple creative variations."""
        
        # Get source content
        content = await self.content_repo.get(source_content_id)
        
        # Extract key elements
        transcript = await self.get_transcript(content)
        hooks = await self.extract_hooks(transcript)
        ctas = await self.extract_ctas(transcript)
        pain_points = await self.extract_pain_points(transcript)
        
        # Generate variations
        variations = []
        for i in range(count):
            variation = await self.create_variation(
                content=content,
                hook=random.choice(hooks),
                cta=random.choice(ctas),
                pain_point=random.choice(pain_points),
                variation_index=i
            )
            variations.append(variation)
        
        return variations
    
    async def extract_hooks(self, transcript: str) -> List[str]:
        """Extract potential hooks from transcript."""
        
        prompt = f"""
        Extract the top 10 most compelling hooks from this transcript.
        A good hook:
        - Grabs attention in the first 3 seconds
        - Creates curiosity
        - Addresses a pain point or desire
        
        Transcript: {transcript}
        
        Return JSON array of hook strings.
        """
        
        response = await self.openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)["hooks"]
    
    async def render_variation(
        self,
        spec: CreativeSpec
    ) -> str:
        """Render creative using Remotion."""
        
        # Use existing Remotion integration
        result = await self.remotion_service.render({
            "template": "AdCreative",
            "props": {
                "video_url": spec.source_video_path,
                "headline": spec.headline,
                "body_text": spec.body_text,
                "cta": spec.cta,
                "hook_text": spec.hook_text
            }
        })
        
        return result["output_path"]
```

---

## Implementation Phases

### Phase 1: Meta API Integration (Weeks 1-2)
| Task | Effort |
|------|--------|
| Meta API client setup | 8h |
| Campaign CRUD | 12h |
| Ad Set CRUD | 8h |
| Ad CRUD | 8h |
| Video upload | 6h |
| Insights fetcher | 12h |
| Database schema | 6h |

### Phase 2: Creative Pipeline (Weeks 3-4)
| Task | Effort |
|------|--------|
| Script extractor (hooks, CTAs) | 8h |
| Variation generator | 12h |
| Remotion integration for ads | 8h |
| Batch rendering | 8h |
| Creative management UI | 12h |

### Phase 3: Rules Engine (Weeks 5-6)
| Task | Effort |
|------|--------|
| Rules engine core | 12h |
| Condition evaluator | 8h |
| Action executor | 8h |
| Cooldown/guardrails | 4h |
| Approval workflow | 8h |
| Rules UI | 12h |

### Phase 4: AI & Insights (Weeks 7-8)
| Task | Effort |
|------|--------|
| Weekly analysis (GPT-4) | 12h |
| Pattern detection | 8h |
| Recommendations engine | 8h |
| Fatigue detector | 6h |
| Insights dashboard | 12h |

### Phase 5: Polish & Testing (Weeks 9-10)
| Task | Effort |
|------|--------|
| CAPI integration | 8h |
| Experiments/A/B tests | 12h |
| Error handling | 8h |
| Cron jobs | 6h |
| Testing | 16h |

---

## Files to Create

```
Backend/services/meta_ads/
├── __init__.py
├── meta_client.py           # Base Meta API client
├── meta_publisher.py        # Campaign/ad management
├── insights_fetcher.py      # Pull performance data
├── rules_engine.py          # Automation rules
├── creative_factory.py      # Generate variations
├── ai_insights.py           # GPT-4 analysis
├── fatigue_detector.py      # Ad fatigue detection
├── conversion_api.py        # Server-side tracking
└── models.py

Backend/api/endpoints/meta_ads.py
Backend/api/endpoints/ads_autopilot.py

Backend/services/workers/
├── meta_sync_worker.py      # Sync insights
├── rules_worker.py          # Run rules engine
└── creative_render_worker.py

dashboard/app/(dashboard)/ads/
├── page.tsx                 # Ads dashboard
├── campaigns/page.tsx       # Campaign list
├── campaigns/[id]/page.tsx  # Campaign detail
├── creatives/page.tsx       # Creative library
├── rules/page.tsx           # Automation rules
├── insights/page.tsx        # AI insights
├── approval-queue/page.tsx  # Pending actions
└── components/
    ├── CampaignCard.tsx
    ├── PerformanceChart.tsx
    ├── RuleBuilder.tsx
    ├── CreativeGrid.tsx
    ├── InsightCard.tsx
    └── ApprovalItem.tsx
```

---

## Environment Variables

```bash
# Meta API
META_APP_ID=xxx
META_APP_SECRET=xxx
META_ACCESS_TOKEN=xxx
META_AD_ACCOUNT_ID=act_xxx
META_PIXEL_ID=xxx
META_PAGE_ID=xxx

# Optional
META_API_VERSION=v21.0
```

---

## Success Criteria

- [ ] Create/manage campaigns via API
- [ ] Generate 50+ creative variations automatically
- [ ] Rules engine running every 6 hours
- [ ] AI insights generated weekly
- [ ] Fatigue detection working
- [ ] Human approval workflow for major actions
- [ ] ROAS tracking accurate

---

*Document created: February 1, 2026*
