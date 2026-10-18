# External Server API Reference

> **MediaPoster Backend** — `http://<host>:5555`
>
> All endpoints are REST JSON. No auth required on local network (add API key middleware for production).
>
> Updated: 2026-02-17

---

## Table of Contents

1. [UGC Content Generation](#1-ugc-content-generation)
2. [Publishing Controls](#2-publishing-controls)
3. [Offer Management](#3-offer-management)
4. [Offer Tracking](#4-offer-tracking)
5. [Sora Script Generation](#5-sora-script-generation)
6. [End-to-End Workflow](#6-end-to-end-workflow)

---

## 1. UGC Content Generation

Generate offer-aware UGC video scripts (talking-head + Sora AI) driven by live trends.

**Base:** `/api/ugc-content`

### Generate Scripts for an Offer

```http
POST /api/ugc-content/generate
```

```json
{
  "offer_id": "550e8400-e29b-41d4-a716-446655440000",
  "count": 5,
  "formats": ["talking_head", "sora_ai"],
  "platforms": ["tiktok", "instagram", "youtube_shorts"],
  "duration": 30,
  "trend_descriptions": null
}
```

**What it does:**
1. Loads offer details (title, description, CTA, landing page, brand) from DB
2. Fetches live social media trends (TikTok, Instagram, web sources)
3. Generates UGC scripts via GPT-4o tailored to @isaiahdupree character
4. Creates tracked UTM link for the offer URL
5. Persists scripts to `ugc_generated_scripts` table

**Response:**
```json
{
  "generated": 5,
  "offer_id": "550e8400-...",
  "scripts": [
    {
      "id": "abc-123",
      "offer_id": "550e8400-...",
      "title": "The Productivity Hack Nobody Talks About",
      "hook": "Want to 10x your output with one tool?",
      "body": "[0:03-0:25] Hey it's Isaiah. I used to spend hours on...",
      "cta": "[0:25-0:30] Link in bio — try it free for 7 days!",
      "caption": "This changed everything for me 🔥\n\nLink in bio 👆",
      "hashtags": ["#productivity", "#techcreator", "#automation"],
      "format_type": "talking_head",
      "duration_seconds": 30,
      "sora_prompt": null,
      "tracked_url": "https://example.com/offer?utm_source=ugc_generator&utm_medium=social&utm_campaign=ugc_productivity_hack",
      "trend_name": "Day in the Life",
      "awareness_level": "problem_aware",
      "status": "generated"
    }
  ]
}
```

### Generate for ALL Active Offers

```http
POST /api/ugc-content/generate/all-offers
```

```json
{
  "count_per_offer": 3,
  "formats": ["talking_head", "sora_ai"]
}
```

### Generate with Manual Trends

Pass your own trend descriptions instead of fetching live:

```json
{
  "offer_id": "550e8400-...",
  "count": 3,
  "trend_descriptions": [
    "POV: you just discovered the tool that does X",
    "Get ready with me while I show you my workflow",
    "Things I wish I knew before starting content creation"
  ]
}
```

### List Scripts

```http
GET /api/ugc-content/scripts?offer_id=...&status=generated&format_type=talking_head&limit=50
```

### Get Single Script

```http
GET /api/ugc-content/scripts/{script_id}
```

### Update Script (edit caption, hook, etc.)

```http
PATCH /api/ugc-content/scripts/{script_id}
```

```json
{
  "caption": "Updated caption with better hooks 🔥",
  "hook": "Stop scrolling — this changed my life",
  "status": "approved"
}
```

### Update Script Status

```http
PATCH /api/ugc-content/scripts/{script_id}/status?status=approved
```

Valid statuses: `generated` → `approved` → `queued` → `published` | `archived`

### Delete Script

```http
DELETE /api/ugc-content/scripts/{script_id}
```

### Queue Script for Publishing

After recording/rendering the video, push it to the publish queue:

```http
POST /api/ugc-content/scripts/{script_id}/queue
```

```json
{
  "platform": "tiktok",
  "account_id": "710",
  "account_username": "isaiah_dupree",
  "video_url": "/path/to/recorded_video.mp4",
  "scheduled_for": "2026-02-18T14:00:00Z"
}
```

This automatically:
- Uses the script's caption, hashtags, and tracked URL
- Adds the video to the `video_publish_queue` table
- Marks the script status as `queued`
- Respects rate limits from Publishing Controls

### Bulk Queue

```http
POST /api/ugc-content/scripts/bulk-queue
```

```json
{
  "items": [
    {"script_id": "abc-123", "platform": "tiktok", "account_id": "710", "video_url": "/path/video1.mp4"},
    {"script_id": "def-456", "platform": "instagram", "account_id": "715", "video_url": "/path/video2.mp4"}
  ]
}
```

### UGC Stats

```http
GET /api/ugc-content/stats
```

Returns: total scripts, counts by status, offers covered, format types.

### List Offers Available for UGC

```http
GET /api/ugc-content/offers
```

---

## 2. Publishing Controls

Runtime management of the Blotato video publishing queue — rate limits, pause/resume, queue CRUD.

**Base:** `/api/publish-controls`

### Get Config

```http
GET /api/publish-controls/config
```

Returns: global limits, per-platform limits, posting windows, interval settings.

### Update Config

```http
PATCH /api/publish-controls/config
```

```json
{
  "global_videos_per_day": 10,
  "platform_limits": {"tiktok": 6, "instagram": 4, "youtube": 2},
  "min_interval_minutes": 20
}
```

### Pause / Resume All Publishing

```http
POST /api/publish-controls/config/pause
POST /api/publish-controls/config/resume
```

### Check Rate Limit (before publishing)

```http
GET /api/publish-controls/can-publish/tiktok
```

```json
{
  "platform": "tiktok",
  "can_publish": true,
  "global_enabled": true,
  "platform_published_today": 2,
  "platform_daily_limit": 6,
  "platform_remaining": 4,
  "global_remaining": 8
}
```

### Queue Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/queue?platform=tiktok&status=queued` | List queue items |
| `GET` | `/queue/stats` | Counts by status/platform |
| `POST` | `/queue` | Add video to queue |
| `POST` | `/queue/bulk` | Bulk enqueue |
| `GET` | `/queue/{id}` | Get single item |
| `PATCH` | `/queue/{id}` | Update caption/title/priority |
| `PATCH` | `/queue/{id}/priority` | Change priority (1-10) |
| `POST` | `/queue/{id}/reschedule` | Move to new time |
| `POST` | `/queue/{id}/pause` | Pause single item |
| `POST` | `/queue/{id}/resume` | Resume paused item |
| `POST` | `/queue/{id}/cancel` | Cancel item |
| `POST` | `/queue/{id}/retry` | Retry failed item |
| `DELETE` | `/queue/{id}` | Delete from queue |

### Add Video to Queue Directly

```http
POST /api/publish-controls/queue
```

```json
{
  "video_url": "https://drive.google.com/file/d/.../view",
  "caption": "Check out this tool 🔥\n\nLink in bio",
  "platform": "tiktok",
  "account_id": "710",
  "title": "Productivity Hack",
  "account_username": "isaiah_dupree",
  "hashtags": ["#automation", "#tech"],
  "priority": 3,
  "scheduled_for": "2026-02-18T14:00:00Z"
}
```

### Full Status Dashboard

```http
GET /api/publish-controls/status
```

Returns config + daily summary + queue stats in one call.

### Daily Summary

```http
GET /api/publish-controls/daily-summary
```

### Publishing History

```http
GET /api/publish-controls/history?days=7&platform=tiktok&limit=100
```

---

## 3. Offer Management

CRUD for offers (products/services linked to brands).

**Base:** `/api/offers`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/` | Create offer |
| `GET` | `/` | List offers (`?brand_id=...&is_active=true&offer_type=product`) |
| `GET` | `/{offer_id}` | Get single offer |
| `PATCH` | `/{offer_id}` | Update offer |
| `DELETE` | `/{offer_id}` | Delete offer |

### Create Offer

```json
{
  "brand_id": "brand-uuid",
  "title": "AI Productivity Suite",
  "description": "All-in-one AI tools for content creators",
  "offer_type": "product",
  "landing_page_url": "https://example.com/ai-suite",
  "cta_text": "Try free for 7 days",
  "price": 29.99,
  "currency": "USD",
  "priority": 1
}
```

---

## 4. Offer Tracking

UTM link creation, click/conversion tracking, campaign reports.

**Base:** `/api/offer-tracking`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/create-link` | Create tracked URL with UTM params |
| `POST` | `/click` | Record click event |
| `POST` | `/conversion` | Record conversion event |
| `GET` | `/campaign/{campaign}` | Campaign performance report |
| `GET` | `/campaigns` | List all campaigns |

### Create Tracked Link

```json
{
  "offer_url": "https://example.com/ai-suite",
  "campaign": "ugc_tiktok_feb",
  "source": "tiktok",
  "metadata": {"post_id": "123"}
}
```

---

## 5. Sora Script Generation

AI video script generation from trends (character-branded).

**Base:** `/api/sora-daily`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/scripts/generate` | Generate from live trends |
| `POST` | `/scripts/generate/manual` | Generate from manual descriptions |
| `POST` | `/scripts/generate/internal` | Generate from internal trend data |
| `GET` | `/scripts` | List saved scripts |
| `GET` | `/scripts/{id}` | Get single script |
| `PATCH` | `/scripts/{id}` | Update script status |
| `DELETE` | `/scripts/{id}` | Delete script |

---

## 6. End-to-End Workflow

### Flow: External Server → Generate UGC → Queue → Publish

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Safari Server /  │    │   MediaPoster    │    │    Blotato       │
│  Dashboard /      │───▶│   Backend        │───▶│  (Social Media)  │
│  Mobile App       │    │   :5555          │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

**Step 1: Discover offers**
```bash
curl http://mediaposter:5555/api/ugc-content/offers
```

**Step 2: Generate UGC scripts for an offer**
```bash
curl -X POST http://mediaposter:5555/api/ugc-content/generate \
  -H "Content-Type: application/json" \
  -d '{
    "offer_id": "550e8400-...",
    "count": 5,
    "formats": ["talking_head", "sora_ai"],
    "duration": 30
  }'
```

**Step 3: Review and approve scripts**
```bash
# List generated scripts
curl http://mediaposter:5555/api/ugc-content/scripts?offer_id=550e8400-...&status=generated

# Approve a script (optionally edit first)
curl -X PATCH "http://mediaposter:5555/api/ugc-content/scripts/abc-123/status?status=approved"
```

**Step 4: Record the video (external — your camera/editor/Sora)**

**Step 5: Check rate limits before queueing**
```bash
curl http://mediaposter:5555/api/publish-controls/can-publish/tiktok
```

**Step 6: Queue the recorded video for publishing**
```bash
curl -X POST http://mediaposter:5555/api/ugc-content/scripts/abc-123/queue \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "tiktok",
    "account_id": "710",
    "account_username": "isaiah_dupree",
    "video_url": "/Users/isaiahdupree/Videos/ugc_take_3.mp4",
    "scheduled_for": "2026-02-18T14:00:00Z"
  }'
```

**Step 7: Monitor the queue**
```bash
curl http://mediaposter:5555/api/publish-controls/queue?platform=tiktok
curl http://mediaposter:5555/api/publish-controls/status
```

**Step 8: Track conversions**
```bash
curl http://mediaposter:5555/api/offer-tracking/campaign/ugc_productivity_hack
```

### Quick Commands Reference

```bash
BASE=http://mediaposter:5555

# === UGC Generation ===
curl $BASE/api/ugc-content/offers                                    # List offers
curl -X POST $BASE/api/ugc-content/generate -d '...'                 # Generate scripts
curl $BASE/api/ugc-content/scripts                                   # List scripts
curl $BASE/api/ugc-content/scripts/{id}                              # Get script
curl -X PATCH $BASE/api/ugc-content/scripts/{id}/status?status=approved  # Approve
curl -X POST $BASE/api/ugc-content/scripts/{id}/queue -d '...'       # Queue for publish
curl $BASE/api/ugc-content/stats                                     # Stats

# === Publishing Controls ===
curl $BASE/api/publish-controls/config                               # Get config
curl -X PATCH $BASE/api/publish-controls/config -d '...'             # Update limits
curl -X POST $BASE/api/publish-controls/config/pause                 # Pause all
curl -X POST $BASE/api/publish-controls/config/resume                # Resume
curl $BASE/api/publish-controls/can-publish/tiktok                   # Rate check
curl $BASE/api/publish-controls/queue                                # View queue
curl $BASE/api/publish-controls/status                               # Full dashboard
curl $BASE/api/publish-controls/daily-summary                        # Today's usage

# === Offers ===
curl $BASE/api/offers                                                # List offers
curl -X POST $BASE/api/offers -d '...'                               # Create offer

# === Offer Tracking ===
curl $BASE/api/offer-tracking/campaigns                              # All campaigns
curl $BASE/api/offer-tracking/campaign/{name}                        # Campaign report
```

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `offers` | Offer entities (title, CTA, landing page, brand) |
| `brands` | Brand entities |
| `ugc_generated_scripts` | Generated UGC scripts (offer-aware, trend-driven) |
| `sora_generated_scripts` | Sora AI video scripts (character-branded) |
| `publishing_config` | Runtime publishing config (limits, windows, intervals) |
| `video_publish_queue` | Unified video queue for Blotato publishing |
| `scheduled_posts` | Individual scheduled posts (legacy + new) |
| `offer_traffic_tracking` | UTM link tracking, clicks, conversions |

---

## Error Handling

All endpoints return standard error format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

HTTP status codes:
- `200` — Success
- `201` — Created
- `400` — Bad request (validation error)
- `404` — Not found
- `429` — Rate limit exceeded
- `500` — Internal server error
