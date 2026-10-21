# Scheduling & Planning Scripts

Legacy standalone CLI tools for previewing and planning content — **no backend server required**. Direct scheduling and publishing paths are disabled.

Some legacy scripts in this checkout connect to Supabase or the local MediaPoster API. The audited generation and provider-write entrypoints are blocked; this document describes migration context, not an approved path for production scheduling. Airtime owns active scheduling and provider writes.

> **Migration boundary:** This directory is a legacy MediaPoster checkout. Airtime in `content-creation-suite` is the sole social scheduling and provider-write authority. `bulk_scheduler.py` is now preview-only; its non-dry-run path returns `airtime_required`. Legacy caption-generation and direct Blotato commands are blocked. Do not use these scripts to create drafts or queue/provider writes.

---

## Quick Reference

| Script | Purpose | Key Use Case |
|--------|---------|-------------|
| `schedule_videos.py` | Preview a local schedule | Inspect a batch before Airtime handoff |
| `plan_content.py` | Analyze schedule, find gaps, plan strategy | "When should I post next?" |
| `schedule_from_guide.py` | Preview guide-derived metadata | Inspect a guide before Airtime handoff |
| `bulk_scheduler.py` | Local-only schedule preview | Preview legacy rows; provider writes blocked |
| `watch_folder.py` | Disabled legacy auto-ingest daemon | Use Airtime for schedule creation |
| `publish_monitor.py` | Live publish monitoring & notifications | Track publish progress, get alerts |

---

## schedule_videos.py

Preview a local schedule from a folder or file. Direct database writes are disabled.

```bash
# Schedule a folder to YouTube (default: 2/day starting tomorrow 10am EST)
python scripts/schedule_videos.py ~/new-videos --platform youtube

# Cross-post to 3 platforms
python scripts/schedule_videos.py ~/new-videos \
  --platform youtube,tiktok,instagram \
  --account 228,710,807

# With a metadata JSON file (titles, descriptions, hashtags)
python scripts/schedule_videos.py ~/new-videos \
  --metadata ~/new-videos/metadata.json \
  --platform youtube

# Auto-generate titles from filenames + hashtags
python scripts/schedule_videos.py ~/new-videos \
  --platform youtube --titles-from-filenames --auto-hashtags

# Custom start time and 3 posts/day
python scripts/schedule_videos.py ~/new-videos \
  --platform youtube --start "2026-03-01 10:00" --posts-per-day 3

# Single video with custom metadata
python scripts/schedule_videos.py ~/video.mp4 \
  --platform youtube --title "My Title" --caption "Description here"

# Generate thumbnails during scheduling
python scripts/schedule_videos.py ~/new-videos --platform youtube --thumbnails

# Preview only (no DB writes)
python scripts/schedule_videos.py ~/new-videos --platform youtube --dry-run

# Show current schedule
python scripts/schedule_videos.py --show-schedule

# Show available Blotato accounts
python scripts/schedule_videos.py --show-accounts
```

### Metadata JSON Format

```json
{
  "defaults": {
    "caption": "Default caption for all videos",
    "hashtags": ["tag1", "tag2"]
  },
  "videos": {
    "video1.mp4": {
      "title": "Video Title",
      "caption": "Full description...",
      "hashtags": ["specific", "tags"]
    }
  }
}
```

---

## plan_content.py

Strategic planning and schedule analysis.

```bash
# Full schedule overview with gap analysis
python scripts/plan_content.py overview

# Strategic analysis with suggestions
python scripts/plan_content.py analyze

# Find 10 optimal YouTube slots
python scripts/plan_content.py find-slots --count 10 --platform youtube

# What's publishing in the next 3 days?
python scripts/plan_content.py upcoming --days 3

# Shift all YouTube posts 2 hours later
python scripts/plan_content.py shift --platform youtube --hours 2

# Clear all draft posts
python scripts/plan_content.py clear --status draft

# Export schedule to JSON
python scripts/plan_content.py export --output my_schedule.json

# Account posting stats
python scripts/plan_content.py accounts
```

---

## schedule_from_guide.py

Parse a structured markdown publishing guide for preview. Direct scheduling is disabled.

```bash
# Schedule from guide to YouTube
python scripts/schedule_from_guide.py ~/docs/publishing-guide.md \
  --platform youtube

# Cross-post to all platforms
python scripts/schedule_from_guide.py ~/docs/guide.md \
  --platform youtube,tiktok,instagram

# Export parsed metadata (without scheduling)
python scripts/schedule_from_guide.py ~/docs/guide.md \
  --export-metadata metadata.json

# Preview only
python scripts/schedule_from_guide.py ~/docs/guide.md --dry-run
```

### Guide Markdown Format

```markdown
### Video Name
**File:** `~/path/to/video.mp4`
**YouTube Title** (optional): `Full Title Here`
**Description:**
\```
Full description text here...

#Hashtag1 #Hashtag2 #Hashtag3
\```
---
```

---

## bulk_scheduler.py

Dry-run preview only. Direct Blotato scheduling is blocked; submit eligible work through Airtime.

```bash
# Preview a folder schedule to TikTok, 30 min apart
python scripts/bulk_scheduler.py --source ~/videos --platform tiktok \
  --account isaiah_dupree --spacing 30

# Multi-platform
python scripts/bulk_scheduler.py --source ~/videos \
  --platform tiktok,instagram --account 710,807 --spacing 30

# Direct publish is blocked; use Airtime
python scripts/bulk_scheduler.py --source ~/video.mp4 \
  --platform tiktok --account 710 --now

# List accounts
python scripts/bulk_scheduler.py --source . --platform tiktok \
  --account 710 --list-accounts
```

---

## Default Accounts

| Platform | ID | Username |
|----------|-----|----------|
| YouTube | 228 | Isaiah Dupree |
| TikTok | 710 | isaiah_dupree |
| Instagram | 807 | the_isaiah_dupree |
| Threads | 173 | the_isaiah_dupree_ |
| Twitter | 4151 | soursides_is_sour |
| Pinterest | 173 | isaiahdupree33 |
| LinkedIn | 571 | IsaiahDupree7 |
| Facebook | 786 | Isaiah Dupree |
| Bluesky | 201 | isaiahdupree.bsky.social |

---

## watch_folder.py

Disabled legacy auto-ingest daemon. Invocations return `airtime_required` before creating folders, resolving accounts, forking, or writing schedule rows.

```bash
# Watch a folder for new videos → YouTube
python scripts/watch_folder.py ~/sora-videos/incoming --platform youtube

# Watch folder → 3 platforms
python scripts/watch_folder.py ~/incoming --platform youtube,tiktok,instagram

# Process existing files on startup then keep watching
python scripts/watch_folder.py ~/incoming --platform youtube --process-existing

# Custom scheduling (3 posts/day, 6h apart)
python scripts/watch_folder.py ~/incoming --platform youtube --posts-per-day 3 --spacing 6

# Watch multiple folders
python scripts/watch_folder.py ~/folder1 ~/folder2 --platform youtube

# Run as background daemon (logs to Backend/logs/watch_folder.log)
python scripts/watch_folder.py ~/incoming --platform youtube --daemon

# Faster polling (check every 5 seconds)
python scripts/watch_folder.py ~/incoming --platform youtube --interval 5
```

### Sidecar Metadata

Place a `.json` or `.meta.json` file next to a video to provide rich metadata:

```json
{
  "title": "My Video Title",
  "caption": "Full description...",
  "hashtags": ["#tag1", "#tag2"]
}
```

If no sidecar exists, title is auto-generated from the filename.

---

## publish_monitor.py

Live monitoring of post publishing status with optional notifications.

```bash
# One-shot status check
python scripts/publish_monitor.py --status

# Live monitoring with countdown timer
python scripts/publish_monitor.py

# With macOS native notifications
python scripts/publish_monitor.py --notify

# With Slack/Discord webhook
python scripts/publish_monitor.py --webhook https://hooks.slack.com/...

# Show publish history (last 24h)
python scripts/publish_monitor.py --history

# Show failed posts
python scripts/publish_monitor.py --failures

# Only alert on failures
python scripts/publish_monitor.py --failures-only --notify
```

---

## Typical Workflows

### New batch of videos arrives
```bash
# 1. Preview what would be scheduled
python scripts/schedule_videos.py ~/new-batch --platform youtube --dry-run

# 2. Check where they'd fit in the schedule
python scripts/plan_content.py find-slots --count 10 --platform youtube

# 3. Schedule with cross-posting
python scripts/schedule_videos.py ~/new-batch \
  --platform youtube,tiktok,instagram --thumbnails

# 4. Verify
python scripts/plan_content.py overview
```

### Publishing guide ready
```bash
# 1. Parse and preview
python scripts/schedule_from_guide.py ~/guide.md --dry-run

# 2. Schedule to all platforms
python scripts/schedule_from_guide.py ~/guide.md \
  --platform youtube,tiktok,instagram --thumbnails

# 3. Verify timing
python scripts/plan_content.py analyze
```

### Check on publishing progress
```bash
python scripts/plan_content.py upcoming --days 1
python scripts/plan_content.py accounts
```

Legacy entrypoints `publish_approved_videos.py`, `full_workflow_ingest_analyze_publish.py`,
`direct_publish_test.py`, and `test_full_publish_flow.py` now exit with an Airtime authority
message before reading media, calling APIs, saving content, or publishing. They are retained
for migration reference; use ScriptHub for generation/approval and Airtime for schedule and
provider writes.

The additional legacy paths `schedule_test_videos.py`, `schedule_7_day_posts.py`, and
`daily_publisher.py` are also disabled at their CLI and write-helper boundaries. They previously
created local schedule rows, inserted directly into the legacy schedule database, or started
services and triggered due-post processing. Their caption helper no longer returns generic
fallback copy. Schedule and delivery work belongs in Airtime.
`daily_publisher.py` also blocks programmatic `DailyPublisher.run()` and `trigger_publish()` calls,
so importing and invoking the class cannot start services or process due posts.

## Legacy Sora Daily publishing boundary

The recovery checkout's adaptive `POST /api/adaptive/sora-daily` route, Sora daily worker,
`YouTubePublisher` metadata generator, and its direct Blotato upload helpers now fail closed.
The route returns HTTP 409 `script_hub_required`; metadata generation requires ScriptHub,
and YouTube scheduling/provider writes belong to Airtime. This prevents direct Sora pipeline
runs, raw OpenAI metadata calls, and local Blotato uploads through these entrypoints. No active
local scheduler reference was found; external or deployed callers remain unknown.
The legacy `/api/sora-daily` generation routes for start/resume/retry, story/trend prompt
creation, and asynchronous/synchronous script generation also return HTTP 409
`script_hub_required` before queue writes, background work, or model calls. Read-only status,
listing and trend-inspection endpoints remain outside this generation guard.

The legacy `/api/safari` content-writing and video-distribution endpoints are gated as well:
script generation/queueing and Sora requests return `script_hub_required`, while processed-video
distribution returns `airtime_required`. The underlying Sora script generators and orchestrator
Sora/tweet/Blotato helpers fail closed, so importing the classes does not bypass the API guards.

## Legacy Twitter campaign boundary

The legacy `TwitterCampaignService` raw-model generation methods now return a
`script_hub_required` failure, and its local scheduling and due-post methods are blocked with
`airtime_required`. The in-memory `TweetScheduler` cannot create a scheduled campaign or delayed
post tasks, assemble theme copy, or report an in-memory schedule as successful. The
`TwitterOfferScheduler` and `TwitterCampaignScheduler` cannot start or enter their Safari/DB
polling loops. If a worker propagates `script_hub_required`, the orchestrator now fails the owning
pipeline immediately instead of leaving a timed-out step active. The active `/api/twitter-campaign` write endpoints return
HTTP 409 with the matching migration code before generation, DB access, queueing or provider
calls. Read-only campaign product/style/analytics endpoints remain a separate audit surface.
Twitter publishing and scheduling must flow through ScriptHub approval and Airtime. A local
source/LaunchAgent search did not establish whether external or deployed callers still invoke
these legacy paths.

## Legacy Blotato API boundary

The mounted `/api/blotato` router previously exposed direct single, multi-platform, bulk and
full-flow publishing, media upload, paid video generation and video deletion. Those write routes
now return HTTP 409 before constructing provider clients, resolving local media, starting a
BackgroundPublisher, or calling Blotato. Publishing and media writes return
`airtime_required`; generation and deletion return `foundry_required`. Read-only account, health
and video-status routes remain separate. The route/helper tests use a real loopback HTTP server
to assert zero provider requests. Deployed revisions and external callers remain unknown.


## Additional audited migration boundary (2026-10-21)

`youtube_direct_upload.py`, `schedule_videos.py`, `schedule_from_guide.py`, and `watch_folder.py` are migration-only. YouTube direct upload and schedule database-write helpers raise `airtime_required`; CLI write paths exit with status 2 before DB/provider access. `schedule_videos.py` and `schedule_from_guide.py` support local `--dry-run` previews. Thumbnail extraction is compute work and returns `orion_required` from these CLIs; submit it through the Orion job service. The watch-folder daemon is fully disabled, including direct helper calls.

## Mounted scheduling API migration boundary (2026-10-21)

The active legacy `/api/schedule` mutation routes (create, update, delete, reschedule, record-posted, publish-now, scheduled publish, and process-due) and `/api/external` submit/bulk/smart scheduling routes now return HTTP 409 `airtime_required` before their side effects. The external schedule-row helper is also disabled before database access. GET schedule/calendar/account/status/health discovery remains available. Use Airtime for schedule mutations and provider writes; verify remote callers and deployed revisions separately.
