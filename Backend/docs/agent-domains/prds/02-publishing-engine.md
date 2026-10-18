# PRD 02 — Publishing Engine Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `services/blotato_api.py` — Blotato API client (22 accounts across 8 platforms)
- `services/blotato_service.py` — Blotato service layer
- `services/multi_platform_publisher.py` — Cross-platform publish coordinator
- `services/post_scheduler.py` — Queue-based post scheduling
- `services/cascade_publisher.py` — Cascaded publish with retry/fallback
- `services/publish_service.py` — Core publish logic
- `services/publisher_service.py` — Platform-specific publisher adapters
- `services/publishing_queue.py` — Queue management
- `services/approval_workflow.py` — Human-in-the-loop approval gates
- `api/blotato_router.py` — Blotato API routes
- `config/blotato_accounts.py` — Account ID → username mapping (22 accounts)

## Account Map (22 Blotato accounts)
TikTok: 710, 243, 4508, 571 | Instagram: 807, 670, 1369, 4508
YouTube: 228, 3370 | Twitter: 4151 | Threads: 173, 201, 1369, 4150
Pinterest: 173, 243 | LinkedIn: 571 | Facebook: 786 | Bluesky: 201

## Features to Build

### F1 — Awareness-to-Platform Auto-Routing
Use the awareness level from `ContentAnalyzer` output to auto-select which accounts to publish to.
- Level 1-2 (cold/story): TikTok + Instagram Reels (accounts 710, 807)
- Level 3 (solution-aware): YouTube + Twitter threads
- Level 4-5 (product/offer): LinkedIn + Email (DM fallback)
Wire into `CascadePublisher.build_publish_plan()` — add `awareness_routing: bool` flag to publish request.

### F2 — Per-Account Daily Cap Enforcement
Add a `DailyCapTracker` that reads from DB and blocks publishing if an account has hit its daily limit.
- TikTok: max 3/day, Instagram: max 5/day, Twitter: max 15/day, LinkedIn: max 2/day
- Store caps in `config/blotato_accounts.py` per account ID
- `POST /api/publishing/check-caps` returns remaining quota per account

### F3 — Publish Result Webhook Receiver
Add `POST /api/publishing/webhook` endpoint that receives Blotato delivery confirmations.
Parse status (`published`, `failed`, `pending`) and update `post_tracker` DB record.
Retry failed posts up to 3 times with exponential backoff via `BackgroundTasks`.

### F4 — Approval Queue Dashboard API
Expose `GET /api/approval/queue` with pagination, filter by platform/status.
Add `POST /api/approval/{item_id}/approve` and `POST /api/approval/{item_id}/reject` with optional note.

### F5 — Schedule Optimization Integration
After every publish, record actual engagement at T+24h. Feed back into `smart_posting_times.py`
to refine per-account optimal posting windows. Expose `GET /api/publishing/optimal-times/{account_id}`.

## Success Criteria
- Daily cap enforcement prevents over-posting
- Awareness routing correctly selects accounts based on content level
- Webhook receiver updates DB within 500ms of receiving payload
- All Blotato API calls include proper error handling and retry logic
