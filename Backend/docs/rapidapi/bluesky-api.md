# Bluesky API Integration

## Overview

Bluesky uses the **AT Protocol** (Authenticated Transfer Protocol) and provides a **FREE public API** - no API key required for public data!

**Base URL**: `https://public.api.bsky.app`

---

## ✅ Verified Working Endpoints (No Auth Required)

### Get User Profile Stats
```
GET https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor={handle}
```

**Parameters**:
- `actor`: Username handle (e.g., `bsky.app`) or DID

**Response**:
```json
{
  "did": "did:plc:xxx",
  "handle": "username.bsky.social",
  "displayName": "Display Name",
  "description": "Bio text",
  "avatar": "https://cdn.bsky.app/...",
  "banner": "https://cdn.bsky.app/...",
  "followersCount": 1250,
  "followsCount": 890,
  "postsCount": 325,
  "createdAt": "2023-04-12T04:53:57.057Z"
}
```

---

### Get User's Posts (Feed)
```
GET https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={handle}&limit={limit}
```

**Parameters**:
- `actor`: Username handle or DID
- `limit`: Number of posts (1-100, default 50)
- `cursor`: Pagination cursor

**Response** (per post):
```json
{
  "post": {
    "uri": "at://did:xxx/app.bsky.feed.post/xxx",
    "cid": "bafyreicxxx",
    "author": { ... },
    "record": {
      "text": "Post content here",
      "createdAt": "2024-12-20T..."
    },
    "likeCount": 42,
    "repostCount": 15,
    "replyCount": 8,
    "quoteCount": 2
  }
}
```

---

### Get Single Post Thread
```
GET https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri={post_uri}
```

**Parameters**:
- `uri`: AT-URI of the post (e.g., `at://did:plc:xxx/app.bsky.feed.post/xxx`)

---

### Search Posts
```
GET https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={query}&limit={limit}
```

**Parameters**:
- `q`: Search query
- `limit`: Number of results (1-100)

---

### Resolve Handle to DID
```
GET https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle={handle}
```

---

## 📊 Available Metrics

| Metric | Endpoint | Field |
|--------|----------|-------|
| Followers | getProfile | `followersCount` |
| Following | getProfile | `followsCount` |
| Total Posts | getProfile | `postsCount` |
| Likes (per post) | getAuthorFeed | `likeCount` |
| Reposts (per post) | getAuthorFeed | `repostCount` |
| Replies (per post) | getAuthorFeed | `replyCount` |
| Quotes (per post) | getAuthorFeed | `quoteCount` |

---

## 🔐 Authentication (For Private Actions)

For posting, liking, following, etc., you need authentication:

1. **Create App Password** at: https://bsky.app/settings/app-passwords
2. **Create Session**:
```bash
curl -X POST https://bsky.social/xrpc/com.atproto.server.createSession \
  -H "Content-Type: application/json" \
  -d '{"identifier": "your.handle", "password": "your-app-password"}'
```

Returns:
```json
{
  "did": "did:plc:xxx",
  "handle": "your.handle",
  "accessJwt": "eyJ...",
  "refreshJwt": "eyJ..."
}
```

Use `accessJwt` in Authorization header for authenticated requests.

---

## Python Example

```python
import httpx

BLUESKY_PUBLIC_API = "https://public.api.bsky.app"

async def get_bluesky_profile(handle: str) -> dict:
    """Get Bluesky user profile stats (no auth required)"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BLUESKY_PUBLIC_API}/xrpc/app.bsky.actor.getProfile",
            params={"actor": handle}
        )
        resp.raise_for_status()
        return resp.json()

async def get_bluesky_posts(handle: str, limit: int = 25) -> list:
    """Get user's posts with engagement metrics"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BLUESKY_PUBLIC_API}/xrpc/app.bsky.feed.getAuthorFeed",
            params={"actor": handle, "limit": limit}
        )
        resp.raise_for_status()
        data = resp.json()
        
        posts = []
        for item in data.get("feed", []):
            post = item["post"]
            posts.append({
                "uri": post["uri"],
                "text": post["record"]["text"],
                "created_at": post["record"]["createdAt"],
                "likes": post.get("likeCount", 0),
                "reposts": post.get("repostCount", 0),
                "replies": post.get("replyCount", 0),
                "quotes": post.get("quoteCount", 0),
            })
        return posts

# Usage
profile = await get_bluesky_profile("your-handle.bsky.social")
print(f"Followers: {profile['followersCount']}")
print(f"Posts: {profile['postsCount']}")

posts = await get_bluesky_posts("your-handle.bsky.social")
for post in posts:
    print(f"Post: {post['text'][:50]}... | Likes: {post['likes']}")
```

---

## Rate Limits

Bluesky's public API has reasonable rate limits:
- ~3000 requests per 5 minutes for unauthenticated
- Higher limits for authenticated requests

---

## Integration Notes

### Advantages
- ✅ **FREE** - No paid API required
- ✅ **No API Key** for public data
- ✅ **Real-time metrics** (likes, reposts, replies, quotes)
- ✅ **Well-documented** official API
- ✅ **Open protocol** (AT Protocol)

### Considerations
- ⚠️ Need app password for posting/actions
- ⚠️ Handle format: `username.bsky.social` or custom domain
- ⚠️ Posts use AT-URI format: `at://did:plc:xxx/app.bsky.feed.post/xxx`

---

## Official Documentation

- **API Docs**: https://docs.bsky.app/docs/api/
- **AT Protocol**: https://atproto.com/
- **GitHub**: https://github.com/bluesky-social/atproto

---

*Last Updated: December 20, 2024*
*Status: ✅ Verified Working (No Auth Required for Public Data)*
