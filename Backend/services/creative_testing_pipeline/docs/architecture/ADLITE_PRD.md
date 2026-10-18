# AdLite — Ad Deployment & Budget Management Queue

## Product Requirements Document

### Problem
ACTP's `AdBudgetDeployer` creates ad campaigns on Meta and TikTok, adjusts budgets, detects fatigue, and monitors spend — but only while the local Mac is running. Ad platforms operate 24/7: a winning creative at 2am should get its budget scaled immediately, and a fatigued ad bleeding money at 4am should be paused before morning. The local-only architecture means budget decisions are delayed by hours.

### Solution
A Vercel-deployed ad management service that:
1. Receives ad deployment requests from ACTP (create campaign, scale budget, pause ad)
2. Executes them against Meta Marketing API and TikTok Business API
3. Runs hourly cron jobs for budget pacing, fatigue detection, and spend alerts
4. Auto-scales winners and auto-kills underperformers based on configurable rules

### Architecture
```
ACTP / ACTPDash
      │
      ▼ POST /api/actions (deploy, scale, pause, kill)
  AdLite (Vercel)
      │
      ├── Meta Marketing API (create campaigns, ad sets, ads)
      ├── TikTok Business API (create campaigns, ads)
      │
      ├── Cron: budget pacing check (every hour)
      ├── Cron: fatigue detection (every 2 hours)
      ├── Cron: spend cap enforcement (every hour)
      │
      ▼
  actp_ad_actions + actp_ad_deployments (Supabase)
```

### Tech Stack
- **Framework:** Next.js 16 (App Router)
- **Database:** Supabase (shared ACTP project)
- **Hosting:** Vercel (serverless functions + cron)
- **APIs:** Meta Marketing API v21, TikTok Business API v1.3

### Supabase Tables

#### `actp_ad_actions` (new)
```sql
CREATE TABLE actp_ad_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id TEXT,
  creative_id TEXT,
  deployment_id TEXT REFERENCES actp_ad_deployments(id),

  action_type TEXT NOT NULL,       -- 'deploy', 'scale_up', 'scale_down', 'pause', 'resume', 'kill', 'adjust_audience'
  platform TEXT NOT NULL,          -- 'meta_ads', 'tiktok_ads'
  params JSONB NOT NULL,           -- action-specific parameters

  status TEXT NOT NULL DEFAULT 'pending',  -- pending, executing, completed, failed, cancelled
  result JSONB,
  error TEXT,
  attempts INT DEFAULT 0,
  max_attempts INT DEFAULT 3,

  priority INT DEFAULT 5,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  executed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_ad_actions_status ON actp_ad_actions(status, priority, created_at);
CREATE INDEX idx_ad_actions_campaign ON actp_ad_actions(campaign_id);
```

#### `actp_budget_rules` (new)
```sql
CREATE TABLE actp_budget_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id TEXT,                -- NULL = global rule
  rule_type TEXT NOT NULL,         -- 'auto_scale', 'spend_cap', 'fatigue_kill', 'time_limit'
  conditions JSONB NOT NULL,       -- e.g. {"metric": "ctr", "operator": ">", "value": 0.02}
  action JSONB NOT NULL,           -- e.g. {"type": "scale_up", "factor": 1.5, "max_budget_cents": 5000}
  enabled BOOLEAN DEFAULT TRUE,
  last_triggered_at TIMESTAMPTZ,
  trigger_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### API Routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/actions` | Submit an ad action (deploy, scale, pause, kill) |
| GET | `/api/actions` | List actions (filterable by status, campaign, platform) |
| GET | `/api/actions/:id` | Get action details and result |
| POST | `/api/actions/:id/cancel` | Cancel a pending action |
| POST | `/api/actions/:id/retry` | Retry a failed action |
| POST | `/api/deploy` | High-level: deploy a creative as an ad (creates full campaign structure) |
| POST | `/api/scale` | High-level: scale budget for a deployment |
| POST | `/api/pause/:deployment_id` | Pause a live ad deployment |
| POST | `/api/kill/:deployment_id` | Kill (permanently stop) a deployment |
| GET | `/api/deployments` | List active ad deployments with latest metrics |
| GET | `/api/deployments/:id` | Deployment details + spend history |
| GET | `/api/rules` | List budget rules |
| POST | `/api/rules` | Create a budget rule |
| PUT | `/api/rules/:id` | Update a budget rule |
| DELETE | `/api/rules/:id` | Delete a budget rule |
| POST | `/api/cron/budget-pacing` | Cron: check budget pacing |
| POST | `/api/cron/fatigue-check` | Cron: detect ad fatigue |
| POST | `/api/cron/spend-caps` | Cron: enforce spend caps |
| POST | `/api/cron/execute-actions` | Cron: process pending action queue |
| GET | `/api/health` | Health check |
| GET | `/api/stats` | Spend summary, active deployments, action stats |

### Vercel Cron Configuration
```json
{
  "crons": [
    {
      "path": "/api/cron/execute-actions",
      "schedule": "*/5 * * * *"
    },
    {
      "path": "/api/cron/budget-pacing",
      "schedule": "0 * * * *"
    },
    {
      "path": "/api/cron/fatigue-check",
      "schedule": "0 */2 * * *"
    },
    {
      "path": "/api/cron/spend-caps",
      "schedule": "0 * * * *"
    }
  ]
}
```

### Ad Deployment Flow

#### Deploy a Creative
1. `POST /api/deploy` with `{ creative_id, platform, budget_cents, audience, offer_url }`
2. AdLite creates a full campaign structure on the platform:
   - **Meta:** Campaign → Ad Set (with audience + budget) → Ad (with creative)
   - **TikTok:** Campaign → Ad Group → Ad
3. Stores external IDs in `actp_ad_deployments`
4. Sets initial budget rule: kill if spend > 2× budget with no conversions

#### Auto-Scale Winners
Budget rules evaluate hourly:
```json
{
  "rule_type": "auto_scale",
  "conditions": { "metric": "ctr", "operator": ">", "value": 0.02, "min_impressions": 500 },
  "action": { "type": "scale_up", "factor": 2.0, "max_budget_cents": 10000 }
}
```
If CTR > 2% after 500 impressions → double the budget (up to $100).

#### Fatigue Detection
Cron checks every 2 hours:
- CTR dropped > 30% over 3 consecutive checks → `fatigue_detected`
- Frequency > 3.0 → `audience_saturated`
- CPA increased > 50% from baseline → `cpa_inflated`
- Action: pause ad, mark deployment as `fatigued`, create alert

#### Spend Cap Enforcement
Hourly check:
- Sum today's spend across all deployments for a campaign
- If total > campaign daily cap → pause all active ads for that campaign
- If single ad > per-ad daily cap → pause that ad

### Dashboard Pages

| Page | Path | Purpose |
|------|------|---------|
| Deployments | `/` | Active ads with spend, CTR, CPA, status badges |
| Deployment Detail | `/deployments/[id]` | Full metrics timeline, budget history, actions taken |
| Actions | `/actions` | Action queue with status tracking |
| Rules | `/rules` | Budget rule editor with condition builder |
| Spend | `/spend` | Daily/weekly spend charts by campaign and platform |
| Settings | `/settings` | API key management, default rules |

### Environment Variables
```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

ADLITE_MASTER_KEY=alk_...
CRON_SECRET=...

META_ACCESS_TOKEN=...
META_AD_ACCOUNT_ID=act_...
META_APP_SECRET=...

TIKTOK_ADS_ACCESS_TOKEN=...
TIKTOK_ADVERTISER_ID=...
```

### CLI Commands
```bash
adlite health                        # Health check
adlite deployments                   # List active deployments
adlite deployments <id>              # Deployment details
adlite deploy --creative <id> --platform meta --budget 500
adlite scale <deployment_id> --factor 2.0
adlite pause <deployment_id>
adlite kill <deployment_id>
adlite actions                       # List action queue
adlite rules                         # List budget rules
adlite stats                         # Spend summary
```

### Success Criteria
1. Ad campaigns created on Meta/TikTok without local machine
2. Budget auto-scaled for winners within 1 hour of threshold crossing
3. Fatigued ads paused within 2 hours of detection
4. Spend caps enforced — no campaign exceeds daily limit by more than 10%
5. Action queue processes pending items within 5 minutes
6. Dashboard shows real-time spend and ROI metrics
