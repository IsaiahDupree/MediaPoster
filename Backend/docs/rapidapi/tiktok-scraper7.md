# TikTok Scraper7 API

## Overview
- **Host**: `tiktok-scraper7.p.rapidapi.com`
- **Base URL**: `https://tiktok-scraper7.p.rapidapi.com`
- **Status**: ✅ Working
- **Free Tier**: 100 requests/month
- **RapidAPI Link**: https://rapidapi.com/JoTucker/api/tiktok-scraper7

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: tiktok-scraper7.p.rapidapi.com
```

## Endpoints

### ✅ GET /user/info
Get user profile information.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `unique_id` | string | Yes | TikTok username (without @) |

**Example Request:**
```bash
curl -X GET "https://tiktok-scraper7.p.rapidapi.com/user/info?unique_id=tiktok" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: tiktok-scraper7.p.rapidapi.com"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "success",
  "processed_time": 0.7285,
  "data": {
    "user": {
      "id": "107955",
      "uniqueId": "tiktok",
      "nickname": "TikTok",
      "avatarThumb": "https://...",
      "signature": "Make Your Day",
      "verified": true,
      "secUid": "...",
      "privateAccount": false
    },
    "stats": {
      "followerCount": 87000000,
      "followingCount": 500,
      "heart": 1500000000,
      "heartCount": 1500000000,
      "videoCount": 300,
      "diggCount": 5000
    }
  }
}
```

---

### ✅ GET /user/posts
Get user's videos with metrics.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `unique_id` | string | Yes | TikTok username |
| `count` | integer | No | Number of posts (default: 30) |
| `cursor` | string | No | Pagination cursor |

**Example Request:**
```bash
curl -X GET "https://tiktok-scraper7.p.rapidapi.com/user/posts?unique_id=isaiah_dupree" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: tiktok-scraper7.p.rapidapi.com"
```

**Example Response:**
```json
{
  "code": 0,
  "msg": "success",
  "processed_time": 0.4321,
  "data": {
    "videos": [
      {
        "aweme_id": "v12300gd0001d4vd6e7og65iopcq7m30",
        "video_id": "7583730892892392759",
        "region": "US",
        "title": "Posted via MediaPoster",
        "cover": "https://...",
        "play_count": 93,
        "digg_count": 3,
        "comment_count": 1,
        "share_count": 0,
        "download_count": 0,
        "create_time": 1703001234,
        "duration": 15
      }
    ],
    "cursor": "1703001234000",
    "hasMore": true
  }
}
```

**Metrics Mapping:**
| API Field | Description |
|-----------|-------------|
| `play_count` | Video views |
| `digg_count` | Likes |
| `comment_count` | Comments |
| `share_count` | Shares |
| `download_count` | Downloads |

---

### ✅ GET /user/followers
Get user's followers list.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `unique_id` | string | Yes | TikTok username |
| `count` | integer | No | Number of followers |
| `cursor` | string | No | Pagination cursor |

---

### ✅ GET /user/following
Get user's following list.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `unique_id` | string | Yes | TikTok username |
| `count` | integer | No | Number to return |
| `cursor` | string | No | Pagination cursor |

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "tiktok-scraper7.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# Get user posts
response = httpx.get(
    f"https://{HOST}/user/posts",
    headers=headers,
    params={"unique_id": "isaiah_dupree"}
)

data = response.json()
for video in data["data"]["videos"]:
    print(f"Video: {video['title']}")
    print(f"  Views: {video['play_count']}")
    print(f"  Likes: {video['digg_count']}")
```

---

## Rate Limits

| Plan | Requests/Month | Rate |
|------|----------------|------|
| BASIC | 100 | 1/sec |
| PRO | 10,000 | 5/sec |
| ULTRA | 100,000 | 10/sec |

---

## Error Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | User not found |
| 2 | Rate limit exceeded |
| 401 | Invalid API key |
| 403 | Subscription required |

---

*Last Updated: December 2024*
