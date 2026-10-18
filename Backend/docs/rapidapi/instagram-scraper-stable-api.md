# Instagram Scraper Stable API - Complete Documentation

**Provider**: RockSolid APIs (thetechguy32744)  
**Base URL**: `https://instagram-scraper-stable-api.p.rapidapi.com`  
**RapidAPI Hub**: https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api  
**Status**: ✅ Active

---

## Authentication

All requests require RapidAPI headers:

```http
X-RapidAPI-Key: YOUR_RAPIDAPI_KEY
X-RapidAPI-Host: instagram-scraper-stable-api.p.rapidapi.com
Content-Type: application/json
```

---

## Endpoints

### 1. User Profile Information

**Endpoint**: `POST /v1/info`

**Description**: Get detailed user profile information including follower count, bio, profile picture, and account metadata.

**Request Body**:
```json
{
  "username_or_id_or_url": "username"  // Instagram username, user ID, or profile URL
}
```

**Response**:
```json
{
  "data": {
    "id": "123456789",
    "username": "username",
    "full_name": "Full Name",
    "biography": "Bio text",
    "profile_pic_url": "https://...",
    "profile_pic_url_hd": "https://...",
    "follower_count": 12345,
    "following_count": 678,
    "media_count": 234,
    "is_verified": false,
    "is_private": false,
    "is_business_account": true,
    "category_name": "Business Category",
    "external_url": "https://example.com"
  }
}
```

**Response Fields**:
- `id`: User ID
- `username`: Instagram username
- `full_name`: Display name
- `biography`: Bio text
- `profile_pic_url`: Standard profile picture URL
- `profile_pic_url_hd`: High-resolution profile picture URL
- `follower_count`: Number of followers
- `following_count`: Number of accounts following
- `media_count`: Total number of posts/reels
- `is_verified`: Verification status
- `is_private`: Privacy status
- `is_business_account`: Business account flag
- `category_name`: Business category (if business account)
- `external_url`: External website URL

---

### 2. User Reels

**Endpoint**: `POST /v1/reels`

**Description**: Get user reels with video URLs, audio metadata, and engagement metrics.

**Request Body**:
```json
{
  "username_or_id_or_url": "username",
  "count": 12,  // Optional: Number of reels to fetch (default: 12)
  "pagination_token": "token"  // Optional: For pagination
}
```

**Response**:
```json
{
  "data": {
    "items": [
      {
        "id": "reel_id",
        "pk": "primary_key",
        "code": "shortcode",
        "caption": {
          "text": "Caption text"
        },
        "video_versions": [
          {
            "url": "https://video-url.mp4",
            "width": 1080,
            "height": 1920
          }
        ],
        "image_versions2": {
          "candidates": [
            {
              "url": "https://thumbnail-url.jpg",
              "width": 1080,
              "height": 1920
            }
          ]
        },
        "clips_metadata": {
          "music_info": {
            "music_asset_info": {
              "audio_id": "audio_id",
              "title": "Music Title",
              "display_artist": "Artist Name",
              "progressive_download_url": "https://audio-url.mp3",
              "duration_in_ms": 30000
            }
          },
          "original_sound_info": {
            "original_audio_title": "Original Sound",
            "ig_artist": {
              "username": "artist_username"
            },
            "audio_asset_info": {
              "progressive_download_url": "https://audio-url.mp3"
            }
          }
        },
        "play_count": 12345,
        "like_count": 678,
        "comment_count": 90,
        "video_duration": 15.5,
        "taken_at": 1234567890
      }
    ]
  },
  "pagination_token": "next_page_token"  // Optional: For next page
}
```

**Response Fields**:
- `items`: Array of reel objects
  - `id` / `pk`: Reel ID
  - `code`: Shortcode (used in URLs)
  - `caption.text`: Caption text
  - `video_versions[].url`: Video download URL
  - `image_versions2.candidates[].url`: Thumbnail URL
  - `clips_metadata.music_info`: Music/audio information
  - `clips_metadata.original_sound_info`: Original sound information
  - `play_count`: View count
  - `like_count`: Like count
  - `comment_count`: Comment count
  - `video_duration`: Duration in seconds
  - `taken_at`: Unix timestamp

---

### 3. Reel by Shortcode

**Endpoint**: `GET /v1/reel_by_shortcode`

**Description**: Get detailed reel information by shortcode (the code in Instagram URLs).

**Query Parameters**:
- `shortcode` (required): Reel shortcode (e.g., "ABC123" from instagram.com/reel/ABC123/)

**Response**: Same structure as individual reel item in `/v1/reels` response.

**Example**:
```
GET /v1/reel_by_shortcode?shortcode=ABC123
```

---

### 4. Media by Shortcode

**Endpoint**: `GET /v1/media_by_shortcode`

**Description**: Get detailed media information (post or reel) by shortcode. Works for both posts and reels.

**Query Parameters**:
- `shortcode` (required): Media shortcode

**Response**: Full media object with all available fields including play_count for videos.

**Example**:
```
GET /v1/media_by_shortcode?shortcode=ABC123
```

---

### 5. User Posts

**Endpoint**: `POST /v1/posts`

**Description**: Get user posts (photos, videos, carousels) with pagination support.

**Request Body**:
```json
{
  "username_or_id_or_url": "username",
  "count": 12,  // Optional: Number of posts to fetch
  "pagination_token": "token"  // Optional: For pagination
}
```

**Response**:
```json
{
  "data": {
    "items": [
      {
        "id": "media_id",
        "pk": "primary_key",
        "code": "shortcode",
        "media_type": 1,  // 1=photo, 2=video, 8=carousel
        "is_video": false,
        "caption": {
          "text": "Caption text"
        },
        "image_versions2": {
          "candidates": [
            {
              "url": "https://image-url.jpg"
            }
          ]
        },
        "video_versions": [
          {
            "url": "https://video-url.mp4"
          }
        ],
        "like_count": 1234,
        "comment_count": 56,
        "play_count": 7890,  // For videos
        "taken_at": 1234567890
      }
    ]
  },
  "pagination_token": "next_page_token"
}
```

**Media Types**:
- `1`: Photo
- `2`: Video
- `8`: Carousel (multiple images/videos)

---

### 6. Search

**Endpoint**: `POST /v1/search`

**Description**: Search Instagram for users and hashtags.

**Request Body**:
```json
{
  "query": "search term"  // Username or hashtag
}
```

**Response**:
```json
{
  "data": {
    "users": [
      {
        "pk": "user_id",
        "username": "username",
        "full_name": "Full Name",
        "profile_pic_url": "https://...",
        "is_verified": false,
        "follower_count": 12345
      }
    ],
    "hashtags": [
      {
        "name": "hashtag",
        "id": "hashtag_id",
        "media_count": 123456
      }
    ]
  }
}
```

---

## Rate Limits

**Free Tier**:
- Limited requests per month
- Check RapidAPI dashboard for current limits

**Pro Tier**:
- Higher rate limits
- Real-time data
- No caching delays

**Rate Limit Headers**:
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

---

## Error Responses

**400 Bad Request**:
```json
{
  "error": "Invalid username or parameters"
}
```

**404 Not Found**:
```json
{
  "error": "User or media not found"
}
```

**429 Too Many Requests**:
```json
{
  "error": "Rate limit exceeded"
}
```

**500 Internal Server Error**:
```json
{
  "error": "Server error"
}
```

---

## Usage Examples

### Python (httpx)
```python
import httpx

async def get_profile(username: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://instagram-scraper-stable-api.p.rapidapi.com/v1/info",
            headers={
                "X-RapidAPI-Key": "YOUR_KEY",
                "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
                "Content-Type": "application/json"
            },
            json={"username_or_id_or_url": username}
        )
        return response.json()
```

### JavaScript (fetch)
```javascript
async function getProfile(username) {
  const response = await fetch(
    'https://instagram-scraper-stable-api.p.rapidapi.com/v1/info',
    {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': 'YOUR_KEY',
        'X-RapidAPI-Host': 'instagram-scraper-stable-api.p.rapidapi.com',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username_or_id_or_url: username })
    }
  );
  return await response.json();
}
```

---

## Best Practices

1. **Rate Limiting**: Implement rate limiting to avoid exceeding API limits
2. **Error Handling**: Always handle 429 (rate limit) and 404 (not found) errors
3. **Pagination**: Use `pagination_token` for fetching large datasets
4. **Caching**: Cache profile data to reduce API calls
5. **Timeout**: Set appropriate timeouts (30 seconds recommended)
6. **Retry Logic**: Implement exponential backoff for failed requests

---

## Integration Notes

- This API provides real-time data (no caching delays)
- Audio URLs from `clips_metadata` are direct download links
- Video URLs from `video_versions` are direct download links
- Shortcodes can be extracted from Instagram URLs: `instagram.com/p/SHORTCODE/` or `instagram.com/reel/SHORTCODE/`
- User IDs can be used instead of usernames for faster lookups

---

## Changelog

- **2024-12-25**: Initial documentation created
- All endpoints verified working with RapidAPI key

---

## References

- [RapidAPI Hub](https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api)
- [Implementation in Codebase](../services/instagram/adapters/instagram_stable_adapter.py)
- [Audio Service Usage](../services/audio_service.py)

