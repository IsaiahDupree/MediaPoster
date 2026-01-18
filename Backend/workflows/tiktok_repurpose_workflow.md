# TikTok Repurposing Workflow

## Overview
Pull TikTok videos from @isaiahdupree, download, analyze, and cross-post to other platforms.

## Pipeline Steps

### Step 1: Fetch TikTok Videos via RapidAPI
- **API**: `tiktok-api6.p.rapidapi.com` or `instagram-looter2.p.rapidapi.com`
- **Endpoint**: `/user/videos` or `/user/posts`
- **Input**: Username `isaiahdupree` (without @)
- **Output**: List of video metadata (id, url, caption, stats)

### Step 2: Download Videos
- Download MP4 files from TikTok CDN URLs
- Save to: `/Volumes/My Passport/MediaPoster/workspace1/tiktok_repurpose/`
- Fallback: `data/tiktok_repurpose/`
- Naming: `{video_id}_{username}.mp4`

### Step 3: Associate as Posted Content
- Insert into `posted_content` table with:
  - `platform`: "tiktok"
  - `platform_post_id`: TikTok video ID
  - `platform_url`: Full TikTok URL
  - `account_id`: 710 (isaiah_dupree TikTok)
  - `caption`: Original caption
  - `status`: "published"
  - `posted_at`: Original post timestamp

### Step 4: Get Stats & Metrics
- Fetch via RapidAPI `/video/details`:
  - Views, likes, comments, shares, saves
- Store in `platform_checkbacks` table
- Calculate engagement rate

### Step 5: Analyze Videos
- **Transcription**: Use Whisper/GPT-4 Audio
- **Topics**: Extract key themes
- **Pre-social Score**: Rate content quality
- Store in `video_analysis` table

### Step 6: Cross-Post to Platforms
Target accounts (Blotato IDs):
| Platform | ID | Username |
|----------|-----|----------|
| Instagram | 807 | @the_isaiah_dupree |
| YouTube | 228 | Isaiah Dupree |
| Threads | 243 | @the_isaiah_dupree |
| Twitter | 571 | @IsaiahDupree7 |

**Scheduling**:
- Stagger posts: 1 hour apart per platform
- Best times: 9 AM, 12 PM, 6 PM EST
- Add to `scheduled_posts` table

---

## API Endpoints

### GET /api/repurpose/tiktok/fetch
Fetch latest videos from TikTok profile.
```json
{
  "username": "isaiahdupree",
  "count": 12
}
```

### POST /api/repurpose/tiktok/download
Download videos and save locally.
```json
{
  "video_ids": ["123...", "456..."]
}
```

### POST /api/repurpose/tiktok/analyze
Analyze downloaded videos.
```json
{
  "video_ids": ["123...", "456..."]
}
```

### POST /api/repurpose/tiktok/crosspost
Schedule cross-posts to other platforms.
```json
{
  "video_ids": ["123...", "456..."],
  "platforms": ["instagram", "youtube", "threads", "twitter"],
  "account_ids": {
    "instagram": 807,
    "youtube": 228,
    "threads": 243,
    "twitter": 571
  }
}
```

### POST /api/repurpose/tiktok/full-pipeline
Run complete pipeline in one call.
```json
{
  "username": "isaiahdupree",
  "count": 12,
  "platforms": ["instagram", "youtube", "threads", "twitter"],
  "analyze": true,
  "schedule_crosspost": true
}
```

---

## Database Tables Used

| Table | Purpose |
|-------|---------|
| `posted_content` | Track TikTok posts as source |
| `platform_checkbacks` | Store metrics snapshots |
| `videos` | Media library reference |
| `video_analysis` | AI analysis results |
| `scheduled_posts` | Cross-post queue |

---

## Implementation Status
- [ ] Fetch TikTok videos
- [ ] Download to local storage
- [ ] Associate as posted content
- [ ] Fetch and store metrics
- [ ] Run video analysis
- [ ] Schedule cross-posts
