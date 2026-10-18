# PRD 04 — Social Analytics Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `services/analytics_service.py` — Core analytics service
- `services/analytics_dashboard_service.py` — Dashboard aggregation
- `services/multi_platform_analytics_aggregator.py` — Cross-platform aggregation
- `services/platform_data_orchestrator.py` — Platform data sync orchestration
- `services/social_analytics_service.py` — Social-specific analytics
- `services/analytics_feedback_loop.py` — Performance → content feedback
- `services/analytics_aggregator.py` — Metric aggregation
- `services/engagement_scorer.py` — Engagement rate scoring
- `services/auto_engagement_tracker.py` — Automatic engagement collection
- `services/metrics_snapshot_service.py` — Point-in-time metric snapshots
- `services/realtime_metrics.py` — Live metric streaming
- `services/performance_correlator.py` — Content attribute → performance correlation
- `api/endpoints/analytics*.py` — Analytics API endpoints
- `scripts/backfill_instagram_metrics.py` / `backfill_tiktok_metrics.py`

## Current State
- RapidAPI fetches metrics for Instagram (instagram-statistics-api) and TikTok (tiktok-scraper7)
- Metrics stored in Supabase (localhost:54322 in dev, cloud in prod)
- Multi-platform aggregator combines data across platforms
- Backfill scripts exist for historical data

## Features to Build

### F1 — Unified Performance Score
Compute a single `performance_score` (0–100) per piece of content, normalized across platforms.
Formula: weight views (40%), likes (30%), comments (20%), shares/saves (10%).
Normalize against the account's rolling 30-day average so platform differences cancel out.
Store in DB. Expose via `GET /api/analytics/content/{content_id}/score`.

### F2 — Content Attribute Correlations
Use `performance_correlator.py` to surface which content attributes predict high performance:
- Hook type (from FATE Focus score)
- Video duration bucket (0-15s, 15-30s, 30-60s, 60s+)
- Time of day published
- Awareness level
Add `GET /api/analytics/correlations` returning ranked attribute → avg_performance_lift pairs.

### F3 — Weekly Performance Report Endpoint
Add `GET /api/analytics/weekly-report` returning a structured JSON report:
- Top 5 performing posts across all platforms
- Platform-by-platform growth (followers delta, avg engagement rate)
- Best performing content type / hook type
- Recommended actions based on data
Use real OpenAI call to generate the "recommended actions" section from the data.

### F4 — Real-Time Metrics WebSocket
Add a WebSocket endpoint `WS /api/analytics/live` that streams metric updates every 30s.
Push events when: a post crosses 1K/10K/100K views, follower count changes by 1%+.
Use `realtime_metrics.py` as the source.

### F5 — Backfill Gap Detection
Scan DB for media items with missing or stale metrics (>48h old).
Add `GET /api/analytics/gaps` returning list of content IDs needing backfill.
Add `POST /api/analytics/backfill` that triggers backfill for those IDs in background.

## Success Criteria
- Performance score persisted for all analyzed content
- Correlations endpoint returns at least 5 ranked attributes
- Weekly report generates within 10s including OpenAI call
- WebSocket pushes updates without crashing on disconnect
