# Scheduling & Planning Scripts

Standalone CLI tools for scheduling and planning content — **no backend server required**.

All scripts connect directly to the Supabase PostgreSQL database. The `PostScheduler` background worker handles actual publishing when posts become due.

---

## Quick Reference

| Script | Purpose | Key Use Case |
|--------|---------|-------------|
| `schedule_videos.py` | Schedule new videos from a folder | New batch of videos ready to post |
| `plan_content.py` | Analyze schedule, find gaps, plan strategy | "When should I post next?" |
| `schedule_from_guide.py` | Parse a publishing guide markdown | Bulk schedule with rich metadata |
| `bulk_scheduler.py` | Direct Blotato API scheduling | Immediate publish, bypass DB |
| `watch_folder.py` | Auto-ingest daemon for new videos | Drop video in folder → auto-scheduled |
| `publish_monitor.py` | Live publish monitoring & notifications | Track publish progress, get alerts |

---

## schedule_videos.py

Schedule videos from a folder or file into the PostScheduler DB.

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

Parse a structured markdown publishing guide and schedule everything.

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

Direct Blotato API scheduling (bypasses DB — posts are not tracked by PostScheduler).

```bash
# Schedule folder to TikTok, 30 min apart
python scripts/bulk_scheduler.py --source ~/videos --platform tiktok \
  --account isaiah_dupree --spacing 30

# Multi-platform
python scripts/bulk_scheduler.py --source ~/videos \
  --platform tiktok,instagram --account 710,807 --spacing 30

# Immediate publish
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

Auto-ingest daemon — watches folders for new video files and auto-schedules them.

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
