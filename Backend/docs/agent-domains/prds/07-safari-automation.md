# PRD 07 — Safari Automation Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `automation/safari_app_controller.py` — Core Safari AppleScript controller (singleton)
- `automation/safari_session_manager.py` — Login detection + session keeper (all platforms)
- `automation/safari_extension_bridge.py` — JS injection bridge
- `automation/safari_twitter_poster.py` — Twitter/X posting automation
- `automation/safari_instagram_poster.py` — Instagram posting automation
- `automation/safari_instagram_scraper.py` — Instagram URL scraper (scroll+collect)
- `automation/safari_threads_poster.py` — Threads posting
- `automation/safari_reddit_poster.py` — Reddit posting
- `automation/tiktok_engagement.py` — TikTok FYP engagement (like/comment/follow)
- `automation/tiktok_dm_controller.py` — TikTok DM automation
- `automation/instagram_dm_controller.py` — Instagram DM automation
- `automation/instagram_comment_automation.py` — Instagram comment automation
- `automation/tiktok_comment_agentic.py` — Agentic TikTok commenting
- `automation/threads_auto_commenter.py` — Threads auto-commenter
- `automation/sora_full_automation.py` — Sora video generation via browser
- `services/safari_automation_orchestrator.py` — Orchestrates multi-platform Safari tasks
- `services/safari_queue_manager.py` — Queue for Safari automation tasks

## Platform Login Codes
- Twitter/X: encryption code 7911 if prompted
- All platforms: Safari must have "Allow Remote Automation" enabled (Develop menu)

## Supported Platforms
Twitter (x.com, 25min refresh), TikTok (20min), Instagram (25min), Sora (30min), YouTube (45min), Threads (25min)

## Features to Build

### F1 — Unified Safari Task Queue API
Currently `safari_queue_manager.py` exists but isn't fully wired to a REST API.
Add `POST /api/safari/tasks` accepting: `{ platform, action, params, priority }`.
Actions: `post`, `comment`, `dm`, `scrape`, `engage`.
Queue is FIFO with priority override. Return `task_id`.
Add `GET /api/safari/tasks/{task_id}` for status.
Add `GET /api/safari/tasks/queue` for full queue view.

### F2 — Session Health Dashboard
Expand `safari_session_manager.py` to expose per-platform session health.
Add `GET /api/safari/sessions` returning: `{ platform, logged_in, last_checked, last_refreshed, next_refresh }`.
If any platform shows `logged_in: false`, emit `agent_event` type `safari_session_expired`.

### F3 — Rate Limit Tracking Per Platform
Track how many actions (posts, comments, DMs) have been performed per platform per hour/day.
Store in Redis or a simple DB table. Block automation if platform-specific limits are hit:
- TikTok: max 50 comments/day, 20 DMs/day
- Instagram: max 30 comments/day, 10 DMs/day
- Twitter: max 500 tweets/day, 400 DMs/day
Add `GET /api/safari/rate-limits` showing current usage vs limits.

### F4 — Screenshot Audit Trail
After every automation action, capture a screenshot and store it at
`automation/screenshots/{platform}/{action}/{timestamp}.png`.
Add `GET /api/safari/audit/{platform}?action=post&date=2026-03-04` returning screenshot paths.
This provides a visual audit trail for debugging and compliance.

### F5 — Agentic Comment Quality Filter
Before posting any auto-generated comment, run it through `FATEScorer`.
Require minimum T (Tribe) score of 0.3 — comments must feel human/community-relevant.
Block and regenerate up to 3 times if score is too low.
Log rejection reasons to `agent_events`.

## Success Criteria
- Task queue API functional with priority ordering
- Session health checked every 20min, alerts on expiry
- Rate limits enforced — no platform bans from over-automation
- Screenshot audit trail captures every action
- Comment quality filter uses real FATE scores
