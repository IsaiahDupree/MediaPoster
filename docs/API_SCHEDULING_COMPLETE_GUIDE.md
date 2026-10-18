# Complete API Scheduling Guide

## 🎯 Purpose

This is the **definitive reference** for scheduling and publishing content via API to all supported platforms. Use this document when:
- Setting up new platform integrations
- Debugging publishing issues
- Understanding the data flow
- Building automation scripts

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication](#authentication)
3. [Platform-Specific Guides](#platform-specific-guides)
   - [TikTok](#tiktok)
   - [Instagram](#instagram)
   - [YouTube](#youtube)
   - [Twitter/X](#twitterx)
   - [Threads](#threads)
   - [Pinterest](#pinterest)
   - [LinkedIn](#linkedin)
   - [Facebook](#facebook)
   - [Bluesky](#bluesky)
4. [Blotato Integration](#blotato-integration)
5. [Internal API Reference](#internal-api-reference)
6. [Database Schema](#database-schema)
7. [Error Handling](#error-handling)
8. [Rate Limits](#rate-limits)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PUBLISHING ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐                                                       │
│   │   Frontend   │                                                       │
│   │   (Next.js)  │                                                       │
│   └──────┬───────┘                                                       │
│          │                                                               │
│          │ POST /api/schedule/create                                     │
│          ▼                                                               │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐          │
│   │   Backend    │─────▶│  Post        │─────▶│  Background  │          │
│   │   (FastAPI)  │      │  Scheduler   │      │  Publisher   │          │
│   └──────────────┘      └──────────────┘      └──────┬───────┘          │
│                                                       │                  │
│                                                       ▼                  │
│                                               ┌──────────────┐          │
│                                               │   Publish    │          │
│                                               │   Service    │          │
│                                               └──────┬───────┘          │
│                                                      │                   │
│          ┌───────────────────────────────────────────┼──────────────┐   │
│          │                                           │              │   │
│          ▼                                           ▼              ▼   │
│   ┌──────────────┐                           ┌──────────────┐  ┌──────┐│
│   │ Google Drive │                           │   Blotato    │  │Direct││
│   │  (staging)   │                           │     API      │  │ APIs ││
│   └──────────────┘                           └──────┬───────┘  └──────┘│
│                                                      │                  │
│          ┌───────────────────────────────────────────┴──────────────┐  │
│          ▼              ▼              ▼              ▼              ▼  │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────┐│
│   │  TikTok  │   │Instagram │   │ YouTube  │   │ Twitter  │   │ etc. ││
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Authentication

### Blotato API Key
```bash
# Location: Backend/.env
BLOTATO_API_KEY=your_blotato_api_key_here

# Usage in code
headers = {
    "Authorization": f"Bearer {BLOTATO_API_KEY}",
    "Content-Type": "application/json"
}
```

### Google Drive (for media staging)
```bash
# Service Account JSON
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

### Platform-Specific (for direct API access)
```bash
# YouTube API
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret

# Twitter API
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
```

---

## Platform-Specific Guides

### TikTok

#### Account IDs (Blotato)
| ID | Username |
|----|----------|
| 710 | @isaiah_dupree |
| 243 | @the_isaiah_dupree |
| 4508 | @dupree_isaiah |
| 571 | @soursides_is_sour |

#### Blotato API Request
```python
import httpx

async def post_to_tiktok(
    account_id: str,
    video_url: str,
    caption: str,
    hashtags: list = None
):
    """Post video to TikTok via Blotato."""
    
    full_caption = caption
    if hashtags:
        full_caption += " " + " ".join(hashtags)
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": full_caption,
                "mediaUrls": [video_url],
                "platform": "tiktok"
            },
            "target": {
                "targetType": "tiktok",
                "privacyLevel": "PUBLIC_TO_EVERYONE",  # REQUIRED
                "disabledComments": False,
                "disabledDuet": False,
                "disabledStitch": False,
                "isBrandedContent": False,
                "isYourBrand": False,
                "isAiGenerated": False
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://backend.blotato.com/v2/posts",
            headers={
                "Authorization": f"Bearer {BLOTATO_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        return response.json()
```

#### Response Format
```json
{
  "postSubmissionId": "uuid-here",
  "status": "processing"
}
```

#### URL Format (after publishing)
```
https://www.tiktok.com/@username/video/{video_id}
```

#### Rate Limits
- **Blotato**: ~50 posts/day per account
- **TikTok Native**: 100% URL capture rate ✅

---

### Instagram

#### Account IDs (Blotato)
| ID | Username |
|----|----------|
| 807 | @the_isaiah_dupree |
| 670 | @the_isaiah_dupree_ |
| 1369 | @dupree_isaiah_ |
| 4508 | @dupree_isaiah |

#### Blotato API Request
```python
async def post_to_instagram(
    account_id: str,
    media_url: str,
    caption: str,
    media_type: str = "reel"  # "reel", "post", "story"
):
    """Post to Instagram via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": caption,
                "mediaUrls": [media_url],
                "platform": "instagram"
            },
            "target": {
                "targetType": "instagram",
                "mediaType": media_type  # IMPORTANT: reel for videos
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://backend.blotato.com/v2/posts",
            headers={
                "Authorization": f"Bearer {BLOTATO_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        return response.json()
```

#### Media Type Options
| Type | Use Case |
|------|----------|
| `reel` | Videos (default for video content) |
| `post` | Images or carousel |
| `story` | 24-hour stories |

#### Character Limits
- **Caption**: 2,200 characters max (target 1,760 = 80%)
- **Hashtags**: 30 max (recommended 5-15)

#### URL Format
```
https://www.instagram.com/reel/{shortcode}/
https://www.instagram.com/p/{shortcode}/
```

---

### YouTube

#### Account IDs (Blotato)
| ID | Channel |
|----|---------|
| 228 | UCnDBsELI2OlaEl5yxA77HNA (Isaiah Dupree) |
| 3370 | lofi_creator |

#### Blotato API Request
```python
async def post_to_youtube(
    account_id: str,
    video_url: str,
    title: str,
    description: str,
    tags: list = None,
    privacy: str = "public"
):
    """Upload video to YouTube via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": description,
                "mediaUrls": [video_url],
                "platform": "youtube"
            },
            "target": {
                "targetType": "youtube",
                "title": title,  # REQUIRED for YouTube
                "privacyStatus": privacy,  # "public", "unlisted", "private"
                "shouldNotifySubscribers": True,
                "isMadeForKids": False,
                "tags": tags or []
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://backend.blotato.com/v2/posts",
            headers={
                "Authorization": f"Bearer {BLOTATO_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        return response.json()
```

#### ⚠️ IMPORTANT: YouTube URL Capture

YouTube URLs are NOT immediately available. You must poll for them:

```python
async def get_youtube_url(post_submission_id: str, max_attempts: int = 10):
    """Poll Blotato for YouTube URL after upload."""
    
    for attempt in range(max_attempts):
        await asyncio.sleep(30)  # Wait 30s between checks
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://backend.blotato.com/v2/posts/{post_submission_id}",
                headers={"Authorization": f"Bearer {BLOTATO_API_KEY}"}
            )
            
            data = response.json()
            
            if data.get("status") == "published":
                # Extract YouTube video ID
                video_id = data.get("platformPostId")
                if video_id and len(video_id) == 11:  # YouTube IDs are 11 chars
                    return f"https://www.youtube.com/watch?v={video_id}"
    
    return None  # URL not available yet
```

#### URL Format
```
https://www.youtube.com/watch?v={video_id}
https://youtu.be/{video_id}
```

#### Character Limits
- **Title**: 100 characters max
- **Description**: 5,000 characters max
- **Tags**: 500 characters total

---

### Twitter/X

#### Account IDs (Blotato)
| ID | Username |
|----|----------|
| 4151 | @IsaiahDupree7 |
| 571 | @soursides_is_sour |

#### Blotato API Request (Text Only)
```python
async def post_to_twitter(
    account_id: str,
    text: str
):
    """Post text tweet via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": text,
                "mediaUrls": [],  # Empty for text-only
                "platform": "twitter"
            },
            "target": {
                "targetType": "twitter"
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://backend.blotato.com/v2/posts",
            headers={
                "Authorization": f"Bearer {BLOTATO_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        return response.json()
```

#### Blotato API Request (With Media)
```python
async def post_to_twitter_with_media(
    account_id: str,
    text: str,
    media_url: str
):
    """Post tweet with media via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": text,
                "mediaUrls": [media_url],
                "platform": "twitter"
            },
            "target": {
                "targetType": "twitter"
            }
        }
    }
    
    # Same as above...
```

#### Character Limits
- **Tweet**: 280 characters (4,000 for Premium)
- **With media**: Still 280 chars for text

#### Rate Limits ⚠️
- **30 posts in rapid succession** before rate limit
- **Recommended**: 5+ minutes between posts
- See `docs/TWITTER_POSTING_STRATEGY.md` for details

#### URL Format
```
https://twitter.com/{username}/status/{tweet_id}
https://x.com/{username}/status/{tweet_id}
```

---

### Threads

#### Account IDs (Blotato)
| ID | Username |
|----|----------|
| 173 | @the_isaiah_dupree_ |
| 201 | @the_isaiah_dupree |
| 1369 | @dupree_isaiah_ |
| 4150 | @isaiahdupree75 |

#### Blotato API Request
```python
async def post_to_threads(
    account_id: str,
    text: str,
    media_url: str = None
):
    """Post to Threads via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": text,
                "mediaUrls": [media_url] if media_url else [],
                "platform": "threads"
            },
            "target": {
                "targetType": "threads"
            }
        }
    }
    
    # Same pattern as others...
```

#### Character Limits
- **Post**: 500 characters

---

### Pinterest

#### Account IDs (Blotato)
| ID | Username |
|----|----------|
| 173 | @isaiahdupree33 |
| 243 | @isaiahdupree75 |

#### Blotato API Request
```python
async def post_to_pinterest(
    account_id: str,
    media_url: str,
    title: str,
    description: str,
    link: str = None,
    board_id: str = None
):
    """Create Pinterest pin via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": description,
                "mediaUrls": [media_url],
                "platform": "pinterest"
            },
            "target": {
                "targetType": "pinterest",
                "title": title,
                "link": link,
                "boardId": board_id  # Optional: specific board
            }
        }
    }
    
    # Same pattern...
```

#### Character Limits
- **Title**: 100 characters
- **Description**: 500 characters

---

### LinkedIn

#### Account IDs (Blotato)
| ID | Username |
|----|----------|
| 571 | @IsaiahDupree7 |

#### Blotato API Request
```python
async def post_to_linkedin(
    account_id: str,
    text: str,
    media_url: str = None
):
    """Post to LinkedIn via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": text,
                "mediaUrls": [media_url] if media_url else [],
                "platform": "linkedin"
            },
            "target": {
                "targetType": "linkedin"
            }
        }
    }
    
    # Same pattern...
```

#### Character Limits
- **Post**: 3,000 characters

---

### Facebook

#### Account IDs (Blotato)
| ID | Name |
|----|------|
| 786 | Isaiah Dupree |

#### Blotato API Request
```python
async def post_to_facebook(
    account_id: str,
    text: str,
    media_url: str = None
):
    """Post to Facebook page via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": text,
                "mediaUrls": [media_url] if media_url else [],
                "platform": "facebook"
            },
            "target": {
                "targetType": "facebook"
            }
        }
    }
    
    # Same pattern...
```

---

### Bluesky

#### Account IDs (Blotato)
| ID | Handle |
|----|--------|
| 201 | isaiahdupree.bsky.social |

#### Blotato API Request
```python
async def post_to_bluesky(
    account_id: str,
    text: str,
    media_url: str = None
):
    """Post to Bluesky via Blotato."""
    
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": text,
                "mediaUrls": [media_url] if media_url else [],
                "platform": "bluesky"
            },
            "target": {
                "targetType": "bluesky"
            }
        }
    }
    
    # Same pattern...
```

#### Character Limits
- **Post**: 300 characters

---

## Blotato Integration

### Base URL
```
https://backend.blotato.com/v2
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/posts` | POST | Create new post |
| `/posts/{id}` | GET | Get post status |
| `/media` | POST | Upload media |
| `/accounts` | GET | List connected accounts |

### Complete Post Flow
```python
async def full_publish_flow(
    platform: str,
    account_id: str,
    media_path: str,
    caption: str,
    **platform_options
):
    """Complete publish flow with URL capture."""
    
    # Step 1: Upload media to Google Drive (staging)
    gdrive_url = await upload_to_gdrive(media_path)
    
    # Step 2: Upload to Blotato media storage
    blotato_url = await upload_to_blotato(gdrive_url)
    
    # Step 3: Create post
    result = await create_post(
        platform=platform,
        account_id=account_id,
        media_url=blotato_url,
        caption=caption,
        **platform_options
    )
    
    post_submission_id = result.get("postSubmissionId")
    
    # Step 4: Poll for completion and URL
    platform_url = await poll_for_url(post_submission_id)
    
    # Step 5: Save to database
    await save_post_result(
        post_submission_id=post_submission_id,
        platform_url=platform_url,
        status="posted" if platform_url else "published_no_url"
    )
    
    # Step 6: Cleanup staging
    await delete_from_gdrive(gdrive_url)
    
    return {
        "success": True,
        "post_submission_id": post_submission_id,
        "platform_url": platform_url
    }
```

### Media Upload
```python
async def upload_to_blotato(media_url: str) -> str:
    """Upload media to Blotato storage."""
    
    payload = {
        "mediaUrl": media_url,
        "fileName": "video.mp4"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://backend.blotato.com/v2/media",
            headers={
                "Authorization": f"Bearer {BLOTATO_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        data = response.json()
        return data.get("publicUrl")
```

---

## Internal API Reference

### Create Scheduled Post
```bash
POST http://localhost:5555/api/schedule/create

{
  "clip_id": "uuid-of-video",
  "platform": "tiktok",
  "account_id": "710",
  "scheduled_at": "2026-01-06T12:00:00Z",
  "title": "My Post Title",
  "caption": "Post caption here #hashtag",
  "hashtags": ["#ai", "#automation"],
  "post_type": "reel"
}
```

### List Scheduled Posts
```bash
GET http://localhost:5555/api/schedule/
GET http://localhost:5555/api/schedule/?status=scheduled
GET http://localhost:5555/api/schedule/?platform=tiktok
GET http://localhost:5555/api/schedule/?limit=50
```

### Get Single Post
```bash
GET http://localhost:5555/api/schedule/{post_id}
```

### Update Post
```bash
PUT http://localhost:5555/api/schedule/{post_id}

{
  "caption": "Updated caption",
  "scheduled_at": "2026-01-07T14:00:00Z"
}
```

### Cancel Post
```bash
DELETE http://localhost:5555/api/schedule/{post_id}
```

### Trigger Due Posts
```bash
POST http://localhost:5555/api/schedule/process-due
```

---

## Database Schema

### scheduled_posts Table
```sql
CREATE TABLE scheduled_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Content Reference
    clip_id UUID,                    -- Reference to video in media DB
    content_variant_id UUID,         -- A/B test variant
    
    -- Platform Config
    platform VARCHAR(50) NOT NULL,   -- tiktok, instagram, youtube, etc.
    account_id VARCHAR(50),          -- Internal account ID
    blotato_account_id TEXT,         -- Blotato's account ID
    
    -- Scheduling
    scheduled_at TIMESTAMP WITH TIME ZONE,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Content
    title TEXT,
    caption TEXT,
    hashtags TEXT[],
    thumbnail_url TEXT,
    post_type VARCHAR(50),           -- reel, post, story, shorts
    
    -- Status Tracking
    status VARCHAR(50) DEFAULT 'pending',
    -- Values: pending, scheduled, publishing, posted, failed, retry_scheduled, cancelled
    
    -- Publishing Results
    platform_post_id TEXT,           -- External platform's ID
    platform_url TEXT,               -- ⚠️ URL to published post
    publish_response JSONB,          -- Full API response
    published_at TIMESTAMP WITH TIME ZONE,
    
    -- Error Handling
    error_message TEXT,
    last_error TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Key Fields for URL Tracking

| Field | Purpose | Format |
|-------|---------|--------|
| `platform_post_id` | Platform's unique ID | YouTube: 11 chars, TikTok: numeric |
| `platform_url` | Full URL to post | https://platform.com/... |
| `publish_response` | Full API response | JSON with all details |

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Media not found` | clip_id doesn't exist | Verify video exists in media DB |
| `Account not found` | Invalid Blotato account_id | Check account IDs in config |
| `Rate limited` | Too many posts | Wait 15+ minutes |
| `Invalid media type` | Wrong format for platform | Check platform requirements |

### Retry Logic
```python
MAX_RETRIES = 3
RETRY_DELAYS = [300, 1800, 7200]  # 5min, 30min, 2hr

async def publish_with_retry(post_id: str):
    for attempt in range(MAX_RETRIES):
        try:
            result = await publish(post_id)
            if result.success:
                return result
        except RateLimitError:
            await asyncio.sleep(RETRY_DELAYS[attempt])
        except Exception as e:
            log_error(post_id, str(e))
    
    mark_as_failed(post_id)
```

---

## Rate Limits

### By Platform

| Platform | Limit | Period | Recovery |
|----------|-------|--------|----------|
| Twitter | 30 | Burst | 15 min |
| TikTok | ~50 | Day | 24 hours |
| Instagram | ~25 | Day | 24 hours |
| YouTube | Variable | - | Account-based |
| Threads | ~25 | Day | 24 hours |
| Pinterest | ~50 | Day | 24 hours |
| LinkedIn | ~100 | Day | 24 hours |

### Safe Posting Schedule
```python
SAFE_DELAYS = {
    "twitter": 300,     # 5 minutes
    "tiktok": 600,      # 10 minutes
    "instagram": 600,   # 10 minutes
    "youtube": 1800,    # 30 minutes
    "threads": 300,     # 5 minutes
    "pinterest": 300,   # 5 minutes
    "linkedin": 300,    # 5 minutes
}
```

---

## Troubleshooting

### Check Post Status
```bash
# API
curl http://localhost:5555/api/schedule/{post_id}

# Database
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -c "SELECT id, platform, status, platform_url, error_message 
      FROM scheduled_posts WHERE id = '{post_id}';"
```

### Find Posts Missing URLs
```sql
SELECT id, platform, title, platform_post_id, status
FROM scheduled_posts 
WHERE status = 'posted' AND platform_url IS NULL
ORDER BY published_at DESC;
```

### Reconstruct YouTube URLs
```sql
-- If platform_post_id is a valid YouTube ID (11 chars)
UPDATE scheduled_posts 
SET platform_url = 'https://www.youtube.com/watch?v=' || platform_post_id
WHERE platform = 'youtube' 
  AND platform_url IS NULL 
  AND LENGTH(platform_post_id) = 11;
```

### View Scheduler Logs
```bash
tail -f Backend/logs/app.log | grep -i "scheduler\|publish\|blotato"
```

### Force Reprocess
```bash
# Manually trigger scheduler
curl -X POST http://localhost:5555/api/schedule/process-due

# Reset failed post for retry
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -c "UPDATE scheduled_posts 
      SET status = 'scheduled', retry_count = 0, error_message = NULL
      WHERE id = '{post_id}';"
```

---

## Quick Reference Card

### Blotato Payload Template
```json
{
  "post": {
    "accountId": "ACCOUNT_ID",
    "content": {
      "text": "CAPTION",
      "mediaUrls": ["MEDIA_URL"],
      "platform": "PLATFORM"
    },
    "target": {
      "targetType": "PLATFORM",
      ...platform_specific_options
    }
  }
}
```

### Platform Target Options

| Platform | Required Options |
|----------|-----------------|
| TikTok | `privacyLevel: "PUBLIC_TO_EVERYONE"` |
| Instagram | `mediaType: "reel"` (for videos) |
| YouTube | `title: "..."`, `privacyStatus: "public"` |
| Twitter | (none) |
| Threads | (none) |
| Pinterest | `title: "..."` |

### Account ID Quick Reference
```
TikTok:    710, 243, 4508, 571
Instagram: 807, 670, 1369, 4508
YouTube:   228, 3370
Twitter:   4151, 571
Threads:   173, 201, 1369, 4150
Pinterest: 173, 243
LinkedIn:  571
Facebook:  786
Bluesky:   201
```

---

*Document Version: 1.0*
*Last Updated: January 5, 2026*
*Author: MediaPoster System*
