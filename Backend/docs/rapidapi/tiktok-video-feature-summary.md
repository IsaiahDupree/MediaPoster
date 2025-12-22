# TikTok Video Feature Summary API

## Overview
- **Host**: `tiktok-video-feature-summary.p.rapidapi.com`
- **Base URL**: `https://tiktok-video-feature-summary.p.rapidapi.com`
- **Status**: ✅ Working
- **Rating**: 9.9/10
- **Provider**: voyagel
- **RapidAPI Link**: https://rapidapi.com/voyagel/api/tiktok-video-feature-summary

## Features
- HD videos without watermark
- User profile data
- Post metrics
- Music/sound info
- Search functionality
- Feeds and trends

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: tiktok-video-feature-summary.p.rapidapi.com
```

## Endpoints

### ✅ GET /user/info
Get user profile information.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `unique_id` | string | Yes | TikTok username |

**Example Request:**
```bash
curl -X GET "https://tiktok-video-feature-summary.p.rapidapi.com/user/info?unique_id=isaiah_dupree" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: tiktok-video-feature-summary.p.rapidapi.com"
```

---

### ✅ GET /user/posts
Get user's videos with metrics.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `unique_id` | string | Yes | TikTok username |
| `count` | integer | No | Number of posts |

**Example Response:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "videos": [
      {
        "id": "7583730892892392759",
        "desc": "Video description",
        "createTime": 1703001234,
        "video": {
          "cover": "https://...",
          "playAddr": "https://...",
          "downloadAddr": "https://..."
        },
        "stats": {
          "playCount": 1000,
          "diggCount": 50,
          "commentCount": 10,
          "shareCount": 5
        },
        "author": {
          "uniqueId": "isaiah_dupree",
          "nickname": "Isaiah"
        }
      }
    ]
  }
}
```

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "tiktok-video-feature-summary.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

response = httpx.get(
    f"https://{HOST}/user/posts",
    headers=headers,
    params={"unique_id": "isaiah_dupree"}
)

data = response.json()
for video in data.get("data", {}).get("videos", []):
    stats = video.get("stats", {})
    print(f"Video: {video.get('desc', 'N/A')[:50]}")
    print(f"  Views: {stats.get('playCount', 0)}")
    print(f"  Likes: {stats.get('diggCount', 0)}")
```

---

## Rate Limits

| Plan | Requests/Month |
|------|----------------|
| BASIC | 100 |
| PRO | 5,000 |

---

*Last Updated: December 2024*
