# YouTube Posting Strategy

**Last Updated:** January 3, 2026

---

## Overview

This document describes the two methods available for posting videos to YouTube and when to use each.

---

## Method 1: Blotato (Primary)

**Best for:** Normal posting, scheduled content, multi-platform posting

### How It Works
1. Video uploaded to Google Drive (temporary storage)
2. Blotato fetches video from Google Drive
3. Blotato publishes to YouTube via their API

### Limits
| Limit | Value | Notes |
|-------|-------|-------|
| **Posts per session** | ~10-15 | Blotato rate limits kick in |
| **Daily limit** | ~50 | Approximate, varies |
| **Google Drive dependency** | Required | Uploads fail if Drive issues |

### When Blotato Fails
Common error: `Failed to upload to Google Drive`
- Google Drive quota exceeded
- OAuth token expired
- Network issues

### Configuration
```
BLOTATO_API_KEY=<key>
BLOTATO_YOUTUBE_ACCOUNT_ID=228
```

---

## Method 2: YouTube Data API v3 (Direct Upload)

**Best for:** Bulk uploads, bypassing Blotato limits, reliability

### How It Works
1. Video uploaded directly to YouTube via API
2. No intermediary (Google Drive not needed)
3. Full control over upload process

### Limits
| Limit | Value | Notes |
|-------|-------|-------|
| **Daily quota** | 10,000 units | ~6-10 videos/day with defaults |
| **Per-video cost** | 1,600 units | Upload + metadata |
| **Rate limit** | None explicit | But quota applies |

### Setup

#### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable **YouTube Data API v3**

#### 2. Create OAuth Credentials
1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Download JSON file
5. Save as: `Backend/config/youtube_client_secrets.json`

#### 3. First Run Authentication
```bash
python scripts/youtube_direct_upload.py --dry-run
```
- Browser opens for OAuth consent
- Authorize the app
- Token saved to `Backend/config/youtube_token.pickle`

### Usage

#### Dry Run (Preview)
```bash
python scripts/youtube_direct_upload.py --dry-run
```

#### Upload All Pending
```bash
python scripts/youtube_direct_upload.py --limit 30 --delay 30
```

#### Options
| Option | Default | Description |
|--------|---------|-------------|
| `--dry-run` | false | Preview without uploading |
| `--limit N` | 30 | Max videos to upload |
| `--delay N` | 30 | Seconds between uploads |

---

## Recommended Strategy

### For Normal Operations (< 10 videos)
Use **Blotato** via the scheduler:
```bash
curl -X POST http://localhost:5555/api/schedule/scheduler/process-now
```

### For Bulk Uploads (10+ videos)
1. Use Blotato for first 10
2. Switch to **YouTube Direct API** for the rest

### Hybrid Approach
```python
# In post_scheduler.py (future enhancement)
BLOTATO_YOUTUBE_LIMIT = 10

if youtube_posts_today < BLOTATO_YOUTUBE_LIMIT:
    use_blotato()
else:
    use_youtube_direct_api()
```

---

## Quota Management

### YouTube API Quota
- **Daily reset:** Midnight Pacific Time
- **Check quota:** [Google Cloud Console > APIs > YouTube Data API](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas)

### Blotato Limits
- No public documentation
- Empirically: ~10-15 posts before rate limiting
- Wait 1 hour or use direct API

---

## Troubleshooting

### Blotato: "Failed to upload to Google Drive"
1. Check Google Drive storage quota
2. Re-authenticate Blotato connection
3. Switch to direct YouTube API

### YouTube API: "quotaExceeded"
1. Wait until midnight PT
2. Request quota increase (takes days)
3. Use multiple projects (not recommended)

### YouTube API: "Invalid credentials"
```bash
rm Backend/config/youtube_token.pickle
python scripts/youtube_direct_upload.py --dry-run
# Re-authenticate
```

---

## File Locations

| File | Purpose |
|------|---------|
| `scripts/youtube_direct_upload.py` | Direct upload script |
| `config/youtube_client_secrets.json` | OAuth credentials (create this) |
| `config/youtube_token.pickle` | Saved auth token (auto-generated) |
| `services/post_scheduler.py` | Blotato-based scheduler |

---

## Session Log: January 3, 2026

### What Happened
1. Scheduled 73 Sora videos via Blotato
2. First ~43 videos posted successfully
3. Blotato hit rate limit ("Failed to upload to Google Drive")
4. 30 videos remained (5 stuck in "publishing", 25 "scheduled")

### Resolution
1. Created `youtube_direct_upload.py` for direct API uploads
2. Remaining videos can be uploaded via:
   ```bash
   python scripts/youtube_direct_upload.py --limit 30
   ```

### Lesson Learned
- Blotato works well for small batches
- For 50+ videos, use direct YouTube API
- Consider implementing automatic fallback in scheduler
