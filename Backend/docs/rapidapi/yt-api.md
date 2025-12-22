# YT-API (YouTube API)

## Overview
- **Host**: `yt-api.p.rapidapi.com`
- **Base URL**: `https://yt-api.p.rapidapi.com`
- **Status**: ✅ Working
- **Free Tier**: 100 requests/month
- **Rating**: 9.9/10
- **Provider**: ytjar
- **RapidAPI Link**: https://rapidapi.com/ytjar/api/yt-api

## Features
- Video data and stream info
- Channel information
- Search functionality
- Playlist data
- Comments
- Trending videos
- Shorts support

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: yt-api.p.rapidapi.com
```

## Endpoints

### ✅ GET /video/info
Get video details and statistics.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | YouTube video ID |

**Example Request:**
```bash
curl -X GET "https://yt-api.p.rapidapi.com/video/info?id=dQw4w9WgXcQ" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: yt-api.p.rapidapi.com"
```

**Example Response:**
```json
{
  "id": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "description": "...",
  "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
  "channelTitle": "Rick Astley",
  "publishedAt": "2009-10-25T06:57:33Z",
  "duration": 213,
  "viewCount": 1500000000,
  "likeCount": 15000000,
  "commentCount": 3000000,
  "thumbnail": {
    "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "width": 1280,
    "height": 720
  },
  "keywords": ["rick astley", "never gonna give you up"],
  "category": "Music"
}
```

---

### ✅ GET /search
Search for videos, channels, or playlists.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `type` | string | No | video, channel, playlist |
| `sort` | string | No | relevance, date, views |

**Example Request:**
```bash
curl -X GET "https://yt-api.p.rapidapi.com/search?query=coding+tutorial" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: yt-api.p.rapidapi.com"
```

---

### ✅ GET /playlist
Get playlist details and videos.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Playlist ID |

---

### ✅ GET /comments
Get video comments.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Video ID |
| `sort` | string | No | top, new |

---

### ✅ GET /trending
Get trending videos.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `geo` | string | No | Country code (US, GB, etc) |
| `type` | string | No | now, music, gaming, movies |

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "yt-api.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# Get video info
def get_video_metrics(video_id):
    response = httpx.get(
        f"https://{HOST}/video/info",
        headers=headers,
        params={"id": video_id}
    )
    data = response.json()
    return {
        "views": data.get("viewCount", 0),
        "likes": data.get("likeCount", 0),
        "comments": data.get("commentCount", 0),
    }

# Extract video ID from URL
def extract_video_id(url):
    import re
    patterns = [
        r'youtube\.com/watch\?v=([^&]+)',
        r'youtu\.be/([^?]+)',
        r'youtube\.com/shorts/([^?]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Example
video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
video_id = extract_video_id(video_url)
metrics = get_video_metrics(video_id)
print(f"Views: {metrics['views']:,}")
```

---

## Rate Limits

| Plan | Requests/Month |
|------|----------------|
| BASIC | 100 |
| PRO | 10,000 |
| ULTRA | 100,000 |

---

## Notes

1. **Video IDs** are 11 characters (e.g., `dQw4w9WgXcQ`)
2. **Shorts** have the same video ID format
3. **Age-restricted** content may return limited data
4. **Deleted videos** will return error

---

*Last Updated: December 2024*
