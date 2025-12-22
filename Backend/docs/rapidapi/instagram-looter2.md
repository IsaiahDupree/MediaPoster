# Instagram Looter2 API

## Overview
- **Host**: `instagram-looter2.p.rapidapi.com`
- **Base URL**: `https://instagram-looter2.p.rapidapi.com`
- **Status**: ✅ Working
- **Free Tier**: 100 requests/month
- **Provider**: IRROR Systems
- **RapidAPI Link**: https://rapidapi.com/IRROR-Systems/api/instagram-looter

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: instagram-looter2.p.rapidapi.com
```

## Endpoints

### ✅ GET /profile
Get user profile with recent posts.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Instagram username (without @) |

**Example Request:**
```bash
curl -X GET "https://instagram-looter2.p.rapidapi.com/profile?username=the_isaiah_dupree" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: instagram-looter2.p.rapidapi.com"
```

**Example Response:**
```json
{
  "status": true,
  "username": "the_isaiah_dupree",
  "full_name": "Isaiah Dupree",
  "biography": "Creator | Developer",
  "bio_links": [],
  "external_url": "https://example.com",
  "is_private": false,
  "is_verified": false,
  "is_business_account": true,
  "profile_pic_url": "https://...",
  "profile_pic_url_hd": "https://...",
  "edge_followed_by": {
    "count": 1234
  },
  "edge_follow": {
    "count": 567
  },
  "edge_owner_to_timeline_media": {
    "count": 42,
    "page_info": {
      "has_next_page": true,
      "end_cursor": "..."
    },
    "edges": [
      {
        "node": {
          "id": "3456789012345678901",
          "shortcode": "DOVvhx1AKQr",
          "typename": "GraphVideo",
          "display_url": "https://...",
          "is_video": true,
          "video_view_count": 517,
          "edge_liked_by": {
            "count": 54
          },
          "edge_media_to_comment": {
            "count": 3
          },
          "taken_at_timestamp": 1703001234,
          "edge_media_to_caption": {
            "edges": [
              {
                "node": {
                  "text": "Post caption here"
                }
              }
            ]
          }
        }
      }
    ]
  }
}
```

**Metrics Mapping:**
| API Field | Description |
|-----------|-------------|
| `edge_liked_by.count` | Likes |
| `edge_media_to_comment.count` | Comments |
| `video_view_count` | Video views (for videos/reels) |
| `shortcode` | Post identifier for URLs |

---

### ✅ GET /post
Get single post details by shortcode.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `shortcode` | string | Yes | Post shortcode from URL |

**Example Request:**
```bash
curl -X GET "https://instagram-looter2.p.rapidapi.com/post?shortcode=DOVvhx1AKQr" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: instagram-looter2.p.rapidapi.com"
```

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "instagram-looter2.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# Get user profile with posts
response = httpx.get(
    f"https://{HOST}/profile",
    headers=headers,
    params={"username": "the_isaiah_dupree"}
)

data = response.json()

# Extract posts
posts = data.get("edge_owner_to_timeline_media", {}).get("edges", [])
for edge in posts:
    node = edge["node"]
    print(f"Shortcode: {node['shortcode']}")
    print(f"  Likes: {node.get('edge_liked_by', {}).get('count', 0)}")
    print(f"  Comments: {node.get('edge_media_to_comment', {}).get('count', 0)}")
    print(f"  Views: {node.get('video_view_count', 'N/A')}")
```

---

## Extracting Shortcode from URL

```python
import re

def extract_shortcode(url):
    patterns = [
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
        r'instagram\.com/tv/([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Example
url = "https://www.instagram.com/reel/DOVvhx1AKQr/"
shortcode = extract_shortcode(url)  # Returns: DOVvhx1AKQr
```

---

## Rate Limits

| Plan | Requests/Month |
|------|----------------|
| BASIC | 100 |
| PRO | 10,000 |
| ULTRA | 50,000 |

---

## Notes

1. **Profile endpoint returns 12 most recent posts** - for older posts, pagination may be needed
2. **Shortcodes are case-sensitive** - extract exactly as shown in URLs
3. **Private accounts** will return limited data
4. **video_view_count** only available for video/reel posts, not photos

---

*Last Updated: December 2024*
