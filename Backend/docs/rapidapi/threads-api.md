# Threads API

## Overview
- **Host**: `threads-api4.p.rapidapi.com`
- **Base URL**: `https://threads-api4.p.rapidapi.com`
- **Status**: ⚠️ Not subscribed (404 errors)
- **Rating**: 9.9/10
- **Provider**: apibox
- **RapidAPI Link**: https://rapidapi.com/apibox/api/threads-api

## Features
- Fast and stable Threads API
- User profiles
- User posts/threads
- Post details
- Search functionality

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: threads-api4.p.rapidapi.com
```

## Expected Endpoints

### GET /user/info
Get Threads user profile.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Threads username |

---

### GET /user/posts
Get user's threads/posts.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Threads username |
| `count` | integer | No | Number of posts |

---

### GET /post/info
Get single post details.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `post_id` | string | Yes | Thread post ID |

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "threads-api4.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# Get user profile
response = httpx.get(
    f"https://{HOST}/user/info",
    headers=headers,
    params={"username": "zuck"}
)

data = response.json()
print(data)
```

---

## Notes

⚠️ **Subscription Required**: You need to subscribe to this API on RapidAPI to use it.

Subscribe at: https://rapidapi.com/apibox/api/threads-api

---

*Last Updated: December 2024*
