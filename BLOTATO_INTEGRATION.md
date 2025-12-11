# Blotato API Integration

**Complete integration with Blotato's social media publishing and AI video creation APIs.**

**Documentation Source:** https://help.blotato.com/api/api-reference

---

## 📋 Overview

Blotato is a powerful social media automation platform that allows you to:
- **Publish posts** to 9+ social media platforms
- **Schedule content** for future publishing
- **Create AI videos** with various templates and styles
- **Generate narrated content** with AI voices

---

## 🚀 Quick Start

### 1. Get Your API Key

1. Go to [my.blotato.com](https://my.blotato.com)
2. Navigate to Settings > API
3. Click "Generate API Key"

> ⚠️ **Note:** This will end your free trial and start your paid subscription.

### 2. Configure Environment

Add to your `.env` file:

```bash
BLOTATO_API_KEY=your_api_key_here
```

### 3. Connect Social Accounts

Go to Settings in Blotato and connect your social media accounts.

---

## 📡 API Endpoints

### Base URL
```
https://backend.blotato.com/v2
```

### Authentication
```
Header: blotato-api-key: YOUR_API_KEY
```

---

## 📤 Publishing Posts

### Endpoint: `POST /v2/posts`

Publish or schedule posts to social media platforms.

**Rate Limit:** 30 requests/minute

### Supported Platforms

| Platform | ID | Requirements |
|----------|-----|--------------|
| Twitter/X | `twitter` | None |
| LinkedIn | `linkedin` | Optional `pageId` |
| Facebook | `facebook` | Required `pageId` |
| Instagram | `instagram` | Optional `mediaType` (reel/story) |
| TikTok | `tiktok` | Required privacy settings |
| Pinterest | `pinterest` | Required `boardId` |
| Threads | `threads` | Optional `replyControl` |
| Bluesky | `bluesky` | None |
| YouTube | `youtube` | Required `title`, `privacyStatus` |

### Example: Simple Tweet

```python
from services.blotato_api import BlotatoAPI, PostContent, TwitterTarget, Platform

client = BlotatoAPI()

result = await client.publish_post(
    account_id="acc_12345",
    content=PostContent(
        text="Hello, world!",
        platform=Platform.TWITTER,
        media_urls=[]
    ),
    target=TwitterTarget()
)
```

### Example: Instagram Reel with Media

```python
result = await client.publish_post(
    account_id="acc_12345",
    content=PostContent(
        text="Check out this amazing content!",
        platform=Platform.INSTAGRAM,
        media_urls=["https://example.com/video.mp4"]
    ),
    target=InstagramTarget(media_type="reel")
)
```

### Example: Twitter Thread

```python
result = await client.publish_post(
    account_id="acc_12345",
    content=PostContent(
        text="First tweet in the thread",
        platform=Platform.TWITTER,
        additional_posts=[
            {"text": "Second tweet", "mediaUrls": []},
            {"text": "Third tweet", "mediaUrls": []}
        ]
    ),
    target=TwitterTarget()
)
```

### Example: Scheduled Post

```python
from datetime import datetime

result = await client.publish_post(
    account_id="acc_12345",
    content=PostContent(
        text="This will be posted later!",
        platform=Platform.LINKEDIN
    ),
    target=LinkedInTarget(),
    scheduled_time=datetime(2025, 3, 15, 10, 0, 0)
)
```

---

## 📁 Media Upload

### Endpoint: `POST /v2/media`

Upload media to Blotato's servers.

**Rate Limit:** 10 requests/minute  
**Max File Size:** 200 MB

> 💡 **Note:** Upload is optional! You can pass any publicly accessible URL directly into `mediaUrls` when publishing.

### Example

```python
result = await client.upload_media("https://example.com/image.jpg")
# Returns: {"url": "https://database.blotato.com/...jpg"}
```

---

## 🎬 AI Video Creation

### Endpoint: `POST /v2/videos/creations`

Create AI-generated videos.

**Rate Limit:** 1 request/minute

### Available Templates

| Template | ID | Description |
|----------|-----|-------------|
| Empty | `empty` | Custom video with optional narration |
| POV Wakeup | `base/pov/wakeup` | "You wake up as..." style videos |
| Quote Slideshow | `base/slides/quotecard` | Quote cards with AI backgrounds |

### Available Styles

- `cinematic`, `apocalyptic`, `baroque`, `comicbook`
- `cyberpunk`, `dystopian`, `fantasy`, `futuristic`
- `gothic`, `grunge`, `horror`, `kawaii`
- `mystical`, `noir`, `painterly`, `realistic`
- `retro`, `surreal`, `whimsical`

### Example: POV Video

```python
from services.blotato_api import BlotatoAPI, VideoStyle, VideoTemplate

client = BlotatoAPI()

result = await client.create_pov_video(
    script="you wake up as a pharaoh",
    style=VideoStyle.CINEMATIC,
    caption_position="bottom",
    animate_first_image=True
)
# Returns: {"item": {"id": "video_123", "status": "Queued"}}
```

### Example: Quote Slideshow

```python
result = await client.create_quote_slideshow(
    scenes=[
        {"prompt": "inspiring quote about success"},
        {"prompt": "motivational quote about perseverance", "text": "Never give up!"}
    ],
    style=VideoStyle.CINEMATIC,
    caption_position="middle"
)
```

### Example: Narrated Video

```python
result = await client.create_narrated_video(
    script="The history of ancient Egypt is fascinating...",
    style=VideoStyle.CINEMATIC,
    voice_name="brian",  # or use voice_id
    caption_position="bottom"
)
```

### Polling for Video Status

```python
# Get status
status = await client.get_video_status("video_123")

# Or wait for completion
final_status = await client.wait_for_video(
    video_id="video_123",
    timeout_seconds=300,
    poll_interval=10
)
# Returns mediaUrl when complete
```

---

## 🎙️ Available AI Voices

| Name | Gender | Accent | Best For |
|------|--------|--------|----------|
| Alice | Female | British | News, Confident |
| Aria | Female | American | Social Media |
| Bill | Male | American | Narration, Trustworthy |
| Brian | Male | American | Deep, Narration |
| Charlie | Male | Australian | Conversational |
| Daniel | Male | British | News, Authoritative |
| Jessica | Female | American | Conversational |
| Laura | Female | American | Social Media, Upbeat |
| Sarah | Female | American | News, Soft |
| Will | Male | American | Social Media, Friendly |

**Full list:** 20 voices available

---

## 🔧 Backend Integration

### Files Created

1. **`Backend/services/blotato_api.py`** - Complete API client
2. **`Backend/api/blotato_router.py`** - FastAPI endpoints

### API Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/blotato/health` | Check API status |
| POST | `/api/blotato/posts` | Publish a post |
| POST | `/api/blotato/posts/multi-platform` | Post to multiple platforms |
| POST | `/api/blotato/media/upload` | Upload media |
| POST | `/api/blotato/videos/create` | Create AI video |
| POST | `/api/blotato/videos/pov` | Create POV video |
| POST | `/api/blotato/videos/slideshow` | Create slideshow |
| POST | `/api/blotato/videos/narrated` | Create narrated video |
| GET | `/api/blotato/videos/{id}` | Get video status |
| DELETE | `/api/blotato/videos/{id}` | Delete video |
| GET | `/api/blotato/videos/{id}/wait` | Wait for video completion |
| GET | `/api/blotato/voices` | List AI voices |
| GET | `/api/blotato/platforms` | List platforms |
| GET | `/api/blotato/video-styles` | List video styles |
| GET | `/api/blotato/video-templates` | List templates |

---

## 💻 Frontend UI

### File Created

**`dashboard/app/(dashboard)/blotato/page.tsx`**

### Features

1. **Publish Tab**
   - Post content editor
   - Platform selection (9 platforms)
   - Media URL management
   - Scheduling
   - Multi-platform publishing

2. **Video Tab**
   - Script editor
   - Template selection
   - Style selection
   - Voice selection (20 voices)
   - Caption position
   - Video status polling
   - Quick templates

3. **Settings Tab**
   - API status
   - Rate limits
   - Voice browser
   - Setup instructions

---

## 📊 Platform-Specific Requirements

### Twitter/X
- Max 280 characters (25,000 for Premium)
- Up to 4 photos or 1 video
- Supports threads

### Instagram (Reels, Stories, Posts)
- **Caption Length:** Max 2,200 characters
- **Media Types:**
  - `post` - Regular feed post (image or video)
  - `reel` - Instagram Reel (video only, max 15 minutes)
  - `story` - Instagram Story (video only, max 60 seconds)
- **Image Specs:** JPEG/PNG, max 8 MB, aspect ratio 4:5 to 1.91:1
- **Video Specs:** MP4/MOV, max 100 MB
- **Carousel:** 2-10 items, all cropped to first image aspect ratio
- **Alt Text:** Up to 1,000 characters for accessibility
- **Collaborators:** Tag other Instagram handles (without @)

### TikTok
- **Description:** Max 2,200 characters
- **Privacy Levels:**
  - `PUBLIC_TO_EVERYONE` - Anyone can view
  - `MUTUAL_FOLLOW_FRIENDS` - Friends only
  - `FOLLOWER_OF_CREATOR` - Followers only
  - `SELF_ONLY` - Private/Draft
- **Video Specs:** MP4/WebM/MOV, max 4 GB, up to 10 minutes
- **Image Specs:** WebP/JPEG, max 20 MB per image, max 1080px
- **Disclosure Options:** Branded content, AI-generated flags
- **Draft Mode:** Save to drafts without publishing
- **Title:** Max 90 characters (for photo posts)

### YouTube
- **Title:** Required, max 100 characters
- **Description:** Max 5,000 characters
- **Privacy Status:** `private`, `public`, `unlisted`
- **Video Specs:** MP4/MOV/AVI/WMV, up to 256 GB or 12 hours
- **Recommended Resolution:** 1080p (1920x1080) or higher
- **Options:** Notify subscribers, Made for Kids, Synthetic media flag

### Pinterest
- Board ID required
- Title max 100 chars
- Description max 800 chars

### Threads
- Max 500 characters
- Supports carousels (2-20 items)

### Bluesky
- Max 300 characters
- Up to 4 images

---

## ⚡ Rate Limits

| Endpoint | Limit |
|----------|-------|
| Post Publishing | 30/min |
| Media Upload | 10/min |
| Video Creation | 1/min |

---

## 🎨 AI Models

### Text-to-Image Models
- Flux Schnell/Dev/Pro/Ultra
- Recraft V3
- Ideogram V2
- Luma Photon
- GPT Image

### Image-to-Video Models
- Framepack
- Runway Gen3 Turbo
- Luma Dream Machine
- Kling 1.5/1.6 Pro
- MiniMax
- Hunyuan
- Veo2

---

## 🔗 Resources

- **API Documentation:** https://help.blotato.com/api/api-reference
- **API Dashboard:** https://my.blotato.com/api-dashboard
- **n8n Integration:** https://help.blotato.com/api/n8n
- **Make.com Integration:** https://help.blotato.com/api/make.com

---

## ✅ Implementation Checklist

- [x] Blotato API client (`services/blotato_api.py`)
- [x] FastAPI router (`api/blotato_router.py`)
- [x] Router registered in `main.py`
- [x] Frontend UI (`dashboard/app/(dashboard)/blotato/page.tsx`)
- [x] Documentation (`BLOTATO_INTEGRATION.md`)
- [ ] Add BLOTATO_API_KEY to environment
- [ ] Connect social accounts in Blotato
- [ ] Test publishing workflow
- [ ] Test video creation workflow

---

## 📝 Usage Examples

### Quick Post

```bash
curl -X POST http://localhost:5555/api/blotato/posts \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "acc_123",
    "text": "Hello from MediaPoster!",
    "platform": "twitter"
  }'
```

### Create POV Video

```bash
curl -X POST http://localhost:5555/api/blotato/videos/pov \
  -H "Content-Type: application/json" \
  -d '{
    "script": "you wake up as a roman emperor",
    "style": "cinematic"
  }'
```

---

**Last Updated:** December 8, 2025
