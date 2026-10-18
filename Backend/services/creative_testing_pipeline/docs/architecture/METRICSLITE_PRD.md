# MetricsLite — Analytics Cron Polling Service

## Product Requirements Document

### Problem
ACTP's `AnalyticsCollector` only runs when the local MediaPoster backend is active. When the Mac sleeps, shuts down, or reboots, metrics stop collecting. YouTube/TikTok/Instagram views accumulate but ACTP has no data — winner selection becomes inaccurate, fatigue detection is blind, and round decisions are delayed.

### Solution
A Vercel-deployed service that runs on a cron schedule (every 30 minutes) to poll YouTube Data API, TikTok API, and Instagram (via RapidAPI) for metrics on all active ACTP organic posts and ad deployments. Results are written directly to `actp_performance_logs` in the shared Supabase database.

### Architecture
```
Vercel Cron (every 30min)
        │
        ▼
  MetricsLite serverless function
        │
        ├── Read active posts from actp_organic_posts
        ├── Read active ads from actp_ad_deployments
        │
        ├──→ YouTube Data API (video stats)
        ├──→ TikTok API (video stats)
        ├──→ RapidAPI / Instagram Graph API (reel stats)
        ├──→ Meta Marketing API (ad metrics)
        ├──→ TikTok Business API (ad metrics)
        │
        ▼
  Write to actp_performance_logs
  Update actp_organic_posts.metrics
  Update actp_ad_deployments.metrics
  Detect threshold crossings → write alerts
```

### Tech Stack
- **Framework:** Next.js 16 (App Router)
- **Database:** Supabase (shared ACTP project)
- **Hosting:** Vercel (cron triggers + serverless functions)
- **APIs:** YouTube Data API v3, TikTok Content API, RapidAPI Instagram, Meta Marketing API, TikTok Business API

### Supabase Tables

#### `actp_cron_runs` (new)
```sql
CREATE TABLE actp_cron_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service TEXT NOT NULL DEFAULT 'metricslite',
  job_type TEXT NOT NULL,       -- 'organic_metrics', 'ad_metrics', 'threshold_check'
  status TEXT NOT NULL,         -- 'running', 'completed', 'failed'
  posts_checked INT DEFAULT 0,
  metrics_written INT DEFAULT 0,
  errors JSONB DEFAULT '[]',
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  duration_ms INT
);

CREATE INDEX idx_cron_runs_service ON actp_cron_runs(service, started_at DESC);
```

#### `actp_metric_alerts` (new)
```sql
CREATE TABLE actp_metric_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  creative_id TEXT NOT NULL,
  campaign_id TEXT,
  platform TEXT NOT NULL,
  alert_type TEXT NOT NULL,     -- 'viral_threshold', 'engagement_drop', 'spend_alert', 'fatigue_detected'
  metric_name TEXT NOT NULL,
  current_value FLOAT,
  threshold_value FLOAT,
  message TEXT,
  acknowledged BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_campaign ON actp_metric_alerts(campaign_id, created_at DESC);
```

### API Routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/cron/organic-metrics` | Cron: collect metrics for organic posts |
| POST | `/api/cron/ad-metrics` | Cron: collect metrics for ad deployments |
| POST | `/api/cron/threshold-check` | Cron: detect threshold crossings and generate alerts |
| GET | `/api/health` | Health check |
| GET | `/api/status` | Current collection status and last run times |
| GET | `/api/metrics/:creative_id` | Get all metrics for a creative |
| GET | `/api/metrics/:creative_id/timeseries` | Get metric timeseries for graphing |
| GET | `/api/alerts` | List active metric alerts |
| POST | `/api/alerts/:id/acknowledge` | Acknowledge an alert |
| GET | `/api/runs` | List recent cron runs |
| POST | `/api/collect/:post_id` | Manually trigger collection for a single post |

### Vercel Cron Configuration
```json
// vercel.json
{
  "crons": [
    {
      "path": "/api/cron/organic-metrics",
      "schedule": "*/30 * * * *"
    },
    {
      "path": "/api/cron/ad-metrics",
      "schedule": "*/30 * * * *"
    },
    {
      "path": "/api/cron/threshold-check",
      "schedule": "0 * * * *"
    }
  ]
}
```

### Metric Collection Logic

#### Organic Posts (every 30 min)
1. Query `actp_organic_posts` WHERE `status = 'published'` AND `posted_at > NOW() - INTERVAL '30 days'`
2. Group by platform
3. For each YouTube post → call YouTube Data API `/videos?part=statistics&id=POST_ID`
4. For each TikTok post → call TikTok API video stats endpoint
5. For each Instagram post → call RapidAPI Instagram endpoint
6. Normalize metrics to standard keys: `views`, `likes`, `comments`, `shares`, `watch_time`, `impressions`, `ctr`
7. Write to `actp_performance_logs`
8. Update `actp_organic_posts.metrics` with latest snapshot

#### Ad Deployments (every 30 min)
1. Query `actp_ad_deployments` WHERE `status = 'active'`
2. For Meta ads → call Marketing API `/insights` endpoint
3. For TikTok ads → call Business API `/report/integrated/get/`
4. Normalize to: `impressions`, `clicks`, `spend`, `ctr`, `cpc`, `conversions`, `video_views`
5. Write to `actp_performance_logs`
6. Update `actp_ad_deployments.metrics` and `.spend_cents`

#### Threshold Alerts (every hour)
1. Query latest metrics for all active creatives
2. Check against thresholds:
   - **Viral threshold:** views > 10,000 in first 24h → `viral_threshold` alert
   - **Engagement drop:** engagement rate drops > 50% vs previous check → `engagement_drop` alert
   - **Spend alert:** daily ad spend > configured cap → `spend_alert` alert
   - **Fatigue detected:** CTR drops > 30% over 3 consecutive checks → `fatigue_detected` alert
3. Write alerts to `actp_metric_alerts`

### Dashboard Pages

| Page | Path | Purpose |
|------|------|---------|
| Overview | `/` | Last collection run, posts tracked, alerts count |
| Alerts | `/alerts` | Active alerts with acknowledge controls |
| Runs | `/runs` | Cron run history with success/fail status |
| Creative Metrics | `/metrics/[id]` | Timeseries charts for a specific creative |

### Environment Variables
```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

METRICSLITE_MASTER_KEY=mlk_...
CRON_SECRET=...                    # Vercel cron auth

YOUTUBE_API_KEY=...
TIKTOK_ACCESS_TOKEN=...
RAPIDAPI_KEY=...
META_ACCESS_TOKEN=...
TIKTOK_ADS_ACCESS_TOKEN=...
TIKTOK_ADVERTISER_ID=...
```

### CLI Commands
```bash
metricslite health                   # Health check
metricslite status                   # Last run times and counts
metricslite collect <post_id>        # Manually collect for one post
metricslite alerts                   # List active alerts
metricslite alerts ack <id>          # Acknowledge alert
metricslite runs                     # Recent cron runs
```

### Rate Limit Considerations
- **YouTube Data API:** 10,000 units/day. Each video stats call = 1 unit. ~200 active posts × 48 checks/day = 9,600 units. Tight but workable.
- **TikTok API:** 1,000 requests/day for basic tier. Batch where possible.
- **RapidAPI Instagram:** Depends on plan. Use caching aggressively.
- **Meta Marketing API:** Rate limited per app. Use batch requests for multiple ad IDs.

### Success Criteria
1. Metrics collected every 30 min regardless of local machine state
2. `actp_performance_logs` entries created for all active posts
3. Viral threshold alerts fire within 1 hour of crossing 10K views
4. Fatigue alerts fire within 2 hours of CTR drop
5. Dashboard shows collection health at a glance
6. No stale metrics older than 1 hour for active campaigns
