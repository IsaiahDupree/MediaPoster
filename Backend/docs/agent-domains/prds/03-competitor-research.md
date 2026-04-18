# PRD 03 — Competitor Research Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `services/competitor_service.py` — RapidAPI profile/reels/posts fetcher + local storage
- `services/competitor_analysis_service.py` — GPT-4o per-post analysis → AccountLearnings
- `services/competitor_audit/` — Posting time analyzer, hook generator, deep audit
- `services/competitor_sync_scheduler.py` — Background sync scheduler
- `automation/safari_instagram_scraper.py` — Safari scroll + URL collection (525 URLs)
- `scripts/extract_engagement_stats.py` — yt-dlp engagement extraction
- `scripts/download_competitor_videos.py` — RapidAPI video downloader
- `scripts/analyze_competitor_for_prompts.py` — Full GPT-4 analysis pipeline
- `scripts/personalbrand_video_generator.py` — End-to-end: analyze → generate videos
- `scripts/scrape_competitor_tiktok.py` — TikTok competitor scraper
- `api/endpoints/competitor_api.py` — Competitor REST API
- `tasks/competitor_weekly_reports.py` — Celery weekly report tasks

## Data Paths
- Scraped data: `/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/`
- Safari manifest: `safari_manifest.json` (525 URLs for @personalbrandlaunch)
- Engagement stats: `engagement_stats.json`
- Downloaded videos: `posts/` (72 videos, 464.9 MB)
- Analysis output: `analysis/learnings.json` + `analysis/learnings.md`

## Features to Build

### F1 — Cross-Account Pattern Comparison
After analyzing multiple competitors, generate a cross-account insights report comparing:
hooks used, posting frequency, top formats, engagement by content type.
Add `POST /api/competitors/cross-analysis` accepting list of usernames.
Output: shared patterns, unique differentiators per account, content gaps to exploit.

### F2 — Auto-Refresh Stale Analysis
In `competitor_sync_scheduler.py`, check `learnings.json` age. If older than 7 days,
auto-trigger re-scrape (Safari manifest) + re-analysis (GPT-4o). Log result to DB.
Add `GET /api/competitors/accounts/{username}/freshness` returning age + next_refresh timestamp.

### F3 — Engagement Stats → Hook Correlation
After extracting engagement stats, use OpenAI to correlate hook type with view count.
Identify which hook archetypes (from FATE Tribe/Focus patterns) drove top 10% of views.
Save as `hook_performance.json`. Expose via `GET /api/competitors/{username}/hook-performance`.

### F4 — TikTok Competitor Parity
`scrape_competitor_tiktok.py` currently exists but is not wired into the analysis pipeline.
Wire it so TikTok accounts go through the same `analyze_account()` flow as Instagram.
Add `platform` field to `AccountLearnings` model. Store TikTok data under
`CompetitorResearch/accounts/{username}_tiktok/`.

### F5 — Competitor Alert System
Monitor tracked competitor accounts weekly. If a new video gets >100K views within 48h,
emit an `agent_event` of type `competitor_viral_alert` with the video URL, view count,
hook text, and suggested response content idea.

## Success Criteria
- Cross-analysis endpoint works for 2+ accounts simultaneously
- Stale analysis auto-triggers without manual intervention
- Hook correlation report identifies top 3 performing archetypes
- No mock data — all analysis uses real OpenAI GPT-4o calls
