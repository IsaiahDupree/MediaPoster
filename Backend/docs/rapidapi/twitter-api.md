# Twitter/X API (The Old Bird)

## Overview
- **Host**: `twitter-api45.p.rapidapi.com`
- **Base URL**: `https://twitter-api45.p.rapidapi.com`
- **Status**: ⚠️ Rate limited (429 errors on free tier)
- **Rating**: 9.9/10
- **Provider**: Data Hungry Beast
- **RapidAPI Link**: https://rapidapi.com/Data-Hungry-Beast-Data-Hungry-Beast-default/api/the-old-bird

## Features
- Tweet details and engagement
- User profiles and followers
- Post engagements
- Search (top, latest, videos, photos, people)
- User tweets, replies, media, likes

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: twitter-api45.p.rapidapi.com
```

## Endpoints

### GET /user.php
Get user profile by username or ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes* | Twitter username |
| `user_id` | string | Yes* | Twitter user ID |

*One of username or user_id required

**Example Response:**
```json
{
  "id": "12345678",
  "name": "Display Name",
  "username": "handle",
  "description": "Bio text",
  "verified": false,
  "followers_count": 1000,
  "following_count": 500,
  "tweet_count": 250,
  "profile_image_url": "https://...",
  "created_at": "2020-01-01T00:00:00.000Z"
}
```

---

### GET /tweet.php
Get tweet details by ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tweet_id` | string | Yes | Tweet ID |

---

### GET /search.php
Search tweets.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `type` | string | No | top, latest, photos, videos |

---

### GET /timeline.php
Get user's tweets.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Twitter username |
| `count` | integer | No | Number of tweets |

---

### GET /followers.php
Get user's followers.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Twitter username |

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "twitter-api45.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# Get user profile
response = httpx.get(
    f"https://{HOST}/user.php",
    headers=headers,
    params={"username": "elonmusk"}
)

data = response.json()
print(f"Followers: {data.get('followers_count')}")
```

---

## Rate Limits

| Plan | Requests/Month |
|------|----------------|
| BASIC | 50 |
| PRO | 5,000 |
| ULTRA | 50,000 |

⚠️ **Note**: Free tier has strict rate limiting. You may see 429 errors frequently.

---

## Extract Tweet ID from URL

```python
import re

def extract_tweet_id(url):
    patterns = [
        r'twitter\.com/\w+/status/(\d+)',
        r'x\.com/\w+/status/(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Example
url = "https://x.com/elonmusk/status/1234567890123456789"
tweet_id = extract_tweet_id(url)  # Returns: 1234567890123456789
```

---

*Last Updated: December 2024*
