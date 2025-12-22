# Instagram Statistics API

## Overview
- **Host**: `instagram-statistics-api.p.rapidapi.com`
- **Base URL**: `https://instagram-statistics-api.p.rapidapi.com`
- **Status**: ✅ Working
- **Free Tier**: 100 requests/month
- **Provider**: Artem Lipko
- **RapidAPI Link**: https://rapidapi.com/Starter-LLP-Starter-LLP-default/api/instagram-statistics-api

## Features
- Follower demographics
- Engagement rates
- Historical data
- Quality scores
- Multi-platform support (Instagram, TikTok, YouTube, Twitter, Facebook, Telegram)

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: instagram-statistics-api.p.rapidapi.com
```

## Endpoints

### ✅ GET /community
Get profile statistics and community info.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | Full Instagram profile URL |

**Example Request:**
```bash
curl -X GET "https://instagram-statistics-api.p.rapidapi.com/community?url=https://www.instagram.com/the_isaiah_dupree/" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: instagram-statistics-api.p.rapidapi.com"
```

**Example Response:**
```json
{
  "meta": {
    "code": 200,
    "message": "OK"
  },
  "data": {
    "cid": "INST:17841400039600391",
    "socialType": "INST",
    "groupID": "17841400039600391",
    "url": "https://instagram.com/the_isaiah_dupree",
    "name": "Isaiah Dupree",
    "image": "https://...",
    "description": "Creator | Developer",
    "followers": 1234,
    "following": 567,
    "postsCount": 42,
    "avgLikes": 150,
    "avgComments": 12,
    "engagementRate": 4.5,
    "qualityScore": 85,
    "isVerified": false,
    "isPrivate": false,
    "category": "Creator"
  }
}
```

---

### GET /posts
Get posts within a date range.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | Full Instagram profile URL |
| `from` | string | Yes | Start date (YYYY-MM-DD) |
| `to` | string | Yes | End date (YYYY-MM-DD) |

**Example Request:**
```bash
curl -X GET "https://instagram-statistics-api.p.rapidapi.com/posts?url=https://www.instagram.com/the_isaiah_dupree/&from=2024-01-01&to=2024-12-31" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: instagram-statistics-api.p.rapidapi.com"
```

**Note:** This endpoint requires `from` and `to` parameters or returns 400 error.

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "instagram-statistics-api.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# Get community statistics
response = httpx.get(
    f"https://{HOST}/community",
    headers=headers,
    params={"url": "https://www.instagram.com/the_isaiah_dupree/"}
)

data = response.json()
stats = data.get("data", {})

print(f"Followers: {stats.get('followers')}")
print(f"Engagement Rate: {stats.get('engagementRate')}%")
print(f"Quality Score: {stats.get('qualityScore')}")
print(f"Avg Likes: {stats.get('avgLikes')}")
```

---

## Supported Platforms

This API supports multiple social platforms:

| Platform | URL Format |
|----------|------------|
| Instagram | `https://instagram.com/username` |
| TikTok | `https://tiktok.com/@username` |
| YouTube | `https://youtube.com/@channel` |
| Twitter/X | `https://twitter.com/username` |
| Facebook | `https://facebook.com/page` |
| Telegram | `https://t.me/channel` |

---

## Data Points Available

- **Follower Count** - Current followers
- **Following Count** - Accounts followed
- **Posts Count** - Total posts
- **Engagement Rate** - Likes + Comments / Followers %
- **Quality Score** - Overall account health (0-100)
- **Demographics** - Audience breakdown (PRO plans)
- **Historical Data** - Follower growth over time

---

## Rate Limits

| Plan | Requests/Month |
|------|----------------|
| BASIC | 100 |
| PRO | 5,000 |
| ULTRA | 25,000 |

---

*Last Updated: December 2024*
