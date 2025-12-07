# Blotato API – Developer Overview and Usage Guide

## Introduction

Blotato is an AI-driven content engine that enables creators and developers to automate content creation and multi-platform distribution. Through its API, Blotato offers endpoints to upload media, generate AI-driven videos or graphics, and publish/schedule posts across major social media platforms (e.g. Twitter (X), LinkedIn, Facebook, Instagram, TikTok, Threads, Pinterest, Bluesky, YouTube). The API is designed for backend integrations – allowing you to build workflows that automate posting, handle large media pipelines, and track content generation programmatically. Blotato's API is available to paying subscribers (generating an API key immediately activates a paid plan) and is intentionally gated to prevent abuse/spam.

## Official Documentation and Developer Resources

Blotato provides a comprehensive API reference via its Help Center (powered by GitBook) covering all endpoints and usage examples. Key sections of the docs include:

- **API Quickstart** – a guide to obtaining API keys, connecting social accounts, and first-call examples
- **API Reference** – detailed docs for each endpoint (e.g. Publish Post, Upload Media, Create Video, Get Video Status, Delete Video) along with an OpenAPI schema
- **Platform Guidelines** – media requirements and limitations per platform (image/video specs, caption lengths, etc.)
- **Integration Templates** – ready-made automation workflows for n8n/Make, showing how to "Post Everywhere" or build AI content pipelines using the API
- **FAQs & Troubleshooting** – a rich FAQ addressing common developer questions and error solutions (e.g. JSON formatting issues, social account setup, rate limit errors, platform-specific quirks)

In addition to the docs, the **Blotato API Dashboard** (on the Blotato web app) is an invaluable tool for developers. It logs every API request/response, helping debug issues by showing payloads and error messages. There's also a **Failed Posts viewer** to see any social posts that were queued but ultimately rejected by the target platform (e.g. due to format or rate limits).

## Authentication and API Access

Authentication is handled via a simple API key mechanism. You generate a Blotato API key from your account settings (note: doing so ends any free trial), and use it in an HTTP header for every API request. For example, include:

```
blotato-api-key: YOUR_API_KEY
```

in the request headers. All Blotato API endpoints use HTTPS and expect this header; unauthorized requests without a valid key will be rejected with 401 errors.

There is no separate OAuth flow for Blotato's API itself – instead, you connect your social media accounts to Blotato via the Blotato web UI (under "Social Accounts") and copy their account IDs. These account IDs are used in API calls to specify which linked account to post to.

### Rate Limits

To maintain good standing with social platforms, Blotato imposes user-level rate limits on its API:
- **Media uploads**: Limited to **10 requests per minute**
- **Post publishing**: Limited to **30 requests per minute**

Exceeding these yields a `429 Too Many Requests` error with a retry-after message (e.g. "retry in X seconds"). These limits ensure you don't spam social APIs.

Additionally, the social networks themselves often have daily posting caps (for instance, Twitter's API permits ~100 tweets per 24 hours per user) – Blotato will relay platform errors if those are hit.

## Core API Endpoints and Examples

### 1. Publishing Posts (Create Post Endpoint)

**Endpoint**: `POST /v2/posts`

The primary function of Blotato is to publish content to social platforms. Key fields include:

- **post.accountId** – The ID of the connected social account to use (required)
- **post.content** – An object with the post body:
  - `text` (caption/text content)
  - `platform` (name of the platform, e.g. "twitter", "instagram", etc.)
  - `mediaUrls` (array, can be empty if no media)
- **post.target** – An object specifying the target platform details:
  - `targetType` that matches the platform (e.g. "twitter", "facebook", "tiktok", etc.)
  - Platform-specific identifiers (e.g., `pageId` for Facebook, `boardId` for Pinterest)

#### Scheduling Options

- **Immediate**: Post as soon as possible (no scheduling fields)
- **Scheduled**: Include `scheduledTime` timestamp (ISO 8601 format, UTC)
- **Next Slot**: Set `useNextFreeSlot: true` to use Content Calendar

#### Example – Immediate Post to Twitter

```bash
POST https://backend.blotato.com/v2/posts
Content-Type: application/json
blotato-api-key: YOUR_API_KEY

{
  "post": {
    "accountId": "acc_12345",
    "content": {
      "text": "Hello, world!",
      "mediaUrls": [],
      "platform": "twitter"
    },
    "target": {
      "targetType": "twitter"
    }
  }
}
```

#### Example – Scheduled Facebook Post

```bash
POST https://backend.blotato.com/v2/posts
Content-Type: application/json
blotato-api-key: YOUR_API_KEY

{
  "post": {
    "accountId": "acc_67890",
    "content": {
      "text": "Scheduled post example",
      "mediaUrls": [],
      "platform": "facebook"
    },
    "target": {
      "targetType": "facebook",
      "pageId": "987654321"
    }
  },
  "scheduledTime": "2025-03-10T15:30:00Z"
}
```

### 2. Attaching Media (Upload & Use Media URLs)

**Endpoint**: `POST /v2/media`

Before including images or videos in a post, you must upload those media files to Blotato's storage. You have two options:

1. Provide a public `url` to the file (Blotato will download it)
2. Provide base64-encoded file data

#### Example – Upload from URL

```bash
POST https://backend.blotato.com/v2/media
Content-Type: application/json
blotato-api-key: YOUR_API_KEY

{
  "url": "https://example.com/image.jpg"
}
```

**Response**:
```json
{
  "url": "https://database.blotato.com/d1655c49-...fa4.jpg"
}
```

This new URL is what you then put into the `mediaUrls` array of your post request.

#### Important Notes:

- **File Size Limits**: Blotato supports media files up to **200 MB** in size
- **Google Drive**: Convert share URLs to direct download format:
  ```
  https://drive.google.com/uc?export=download&id=<ID>
  ```
- **Rate limiting**: 10 uploads per minute
- **Duplicate uploads**: Wait ~20 seconds between identical URL uploads

### 3. AI Video Creation (Optional)

Blotato can programmatically generate AI-driven videos, slideshows, and talking head videos.

#### Create Video

**Endpoint**: `POST /v2/videos/creations`

```bash
POST https://backend.blotato.com/v2/videos/creations
Content-Type: application/json
blotato-api-key: YOUR_API_KEY

{
  "script": "you wake up as a pharaoh",
  "style": "cinematic",
  "template": { "id": "base/pov/wake-up" }
}
```

**Response** includes a video `id` for tracking.

#### Check Video Status

**Endpoint**: `GET /v2/videos/creations/:id`

```bash
GET https://backend.blotato.com/v2/videos/creations/videogen_123456
blotato-api-key: YOUR_API_KEY
```

**Response**:
```json
{
  "item": {
    "id": "videogen_123456",
    "status": "Done",
    "createdAt": "2025-11-15T01:23:45.678Z",
    "mediaUrl": "https://database.blotato.com/video123.mp4",
    "imageUrls": null
  }
}
```

Status values: `"Queued"`, `"Processing"`, `"Done"`, `"Failed"`

#### Delete Video

**Endpoint**: `DELETE /v2/videos/:id`

```bash
DELETE https://backend.blotato.com/v2/videos/videogen_123456
blotato-api-key: YOUR_API_KEY
```

Returns HTTP 204 No Content on success.

## Platform-Specific Features

### Supported Platforms
- `twitter` (X)
- `linkedin`
- `facebook`
- `instagram`
- `pinterest`
- `tiktok`
- `threads`
- `bluesky`
- `youtube`

### Platform Requirements

#### Twitter (X)
- Max 280 characters
- 4 photos or 1 video per tweet
- No special fields required

#### Facebook
- **REQUIRED**: `pageId` in target object
- Cannot post to personal profiles
- Max 63,206 characters

#### LinkedIn
- Personal profile: No extra fields
- Company page: Include `pageId` in target
- Max 3,000 characters

#### Instagram
- **Reels** (default): Videos only
- **Stories**: Set `mediaType: "story"` in target
- Max 2,200 characters for captions
- Aspect ratio: 1.91:1 to 4:5

#### TikTok
**REQUIRED fields** in target:
- `privacyLevel` (e.g., "PUBLIC_TO_EVERYONE")
- `disabledComments` (boolean)
- `disabledDuet` (boolean)
- `disabledStitch` (boolean)
- `isBrandedContent` (boolean)
- `isDraft` (boolean, optional)

⚠️ **Warning**: TikTok rejects posts with external URLs in description

#### Pinterest
- **REQUIRED**: `boardId` in target
- Optional: `title` and `link` (destination URL)

#### YouTube
- **REQUIRED**: One video in `mediaUrls`
- **REQUIRED**: `title` in content
- **REQUIRED**: `privacyStatus` ("public", "unlisted", "private")
- **REQUIRED**: `shouldNotifySubscribers` (boolean)
- Optional: `isMadeForKids`, `containsSyntheticMedia`

#### Threads
- Linked to Instagram account
- May require "warming up" new accounts
- Error "Threads API feature not available" = account not API-enabled yet

## Developer Tools & Integrations

### n8n Nodes
- Official package: `n8n-nodes-blotato`
- Nodes: Media Upload, Publish Post, Create Video
- Visual workflow builder
- MIT license (open source)

### Make.com (Integromat)
- Official Blotato modules
- Templates for multi-platform posting
- Visual workflow builder

### Pipedream
- Pre-built Blotato actions
- Code + no-code flexibility
- Secure credential storage

### Direct API
- OpenAPI spec available
- Use with any HTTP client (curl, requests, axios, etc.)
- No official SDK, but simple REST API

## Testing & Best Practices

### Validate JSON Structure
- Double-check against API docs examples
- Use JSON linters
- Common error: `Invalid JSON` or HTTP 422

### Use API Dashboard
- Visit `my.blotato.com/api-dashboard`
- View all requests and responses
- See exact error messages
- Check Failed Posts page

### Common Errors & Solutions

**Wrong account/page ID**
- Re-copy IDs from Blotato Settings UI
- Use "Copy Account ID" buttons

**Invalid media format**
- Check aspect ratio requirements
- Resize/crop to platform specs
- Max 200 MB file size

**Rate limit exceeded (429)**
- Implement retry logic with exponential backoff
- Respect retry-after header
- Batch requests over time

**New social accounts**
- "Warm up" accounts before API posting
- Post organically for a few days first
- Gain platform trust

### Performance Tips

1. **Respect rate limits**: 10 media uploads/min, 30 posts/min
2. **Queue posts**: Don't blast all at once
3. **Implement retries**: Handle 429 errors gracefully
4. **Cache media URLs**: Reuse uploaded media
5. **Monitor failures**: Check dashboard regularly

### Google Drive Integration

For large files (100MB+):
- Convert share URL to direct download
- Use alternative hosting (S3, GCP, Dropbox) for very large files
- Avoid virus scan interstitials

Format:
```
https://drive.google.com/uc?export=download&id=<FILE_ID>
```

## Limitations & Roadmap

### Current Limitations
- ❌ No API endpoint to delete published social media posts
- ❌ No API for fetching post metrics/analytics
- ❌ No "get post status" endpoint (coming soon)

### Workarounds
- Delete posts manually via platform
- Use platform APIs directly for analytics
- Check Blotato dashboard for post success/failure

### Future Features (Roadmap)
- Post status retrieval API
- Social analytics via API
- Zapier integration (coming soon)
- Enhanced post management

## Example Workflows

### Simple Post Automation

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://backend.blotato.com"

# 1. Upload media
media_response = requests.post(
    f"{BASE_URL}/v2/media",
    headers={"blotato-api-key": API_KEY},
    json={"url": "https://example.com/image.jpg"}
)
media_url = media_response.json()["url"]

# 2. Publish to Twitter
post_response = requests.post(
    f"{BASE_URL}/v2/posts",
    headers={"blotato-api-key": API_KEY},
    json={
        "post": {
            "accountId": "acc_12345",
            "content": {
                "text": "Check this out! 🔥",
                "mediaUrls": [media_url],
                "platform": "twitter"
            },
            "target": {
                "targetType": "twitter"
            }
        }
    }
)
print(f"Post submitted: {post_response.json()}")
```

### Multi-Platform Posting

```python
platforms = [
    {"type": "twitter", "account": "acc_111"},
    {"type": "instagram", "account": "acc_222"},
    {"type": "tiktok", "account": "acc_333", "privacy": "PUBLIC_TO_EVERYONE"}
]

for platform in platforms:
    target = {"targetType": platform["type"]}
    
    # Add platform-specific fields
    if platform["type"] == "tiktok":
        target.update({
            "privacyLevel": platform["privacy"],
            "disabledComments": False,
            "disabledDuet": False,
            "disabledStitch": False,
            "isBrandedContent": False
        })
    
    response = requests.post(
        f"{BASE_URL}/v2/posts",
        headers={"blotato-api-key": API_KEY},
        json={
            "post": {
                "accountId": platform["account"],
                "content": {
                    "text": "My content here",
                    "mediaUrls": [media_url],
                    "platform": platform["type"]
                },
                "target": target
            }
        }
    )
    print(f"{platform['type']}: {response.status_code}")
```

## Support Resources

- **Documentation**: docs.blotato.com
- **API Dashboard**: my.blotato.com/api-dashboard
- **Support**: Via Intercom chat on Blotato website
- **Community**: Check forums/Discord
- **Office Hours**: Weekly with founder (for strategy)

## Conclusion

Blotato's API transforms multi-platform content management into a unified, programmable workflow. With simple authentication, consistent endpoints, and extensive platform support, you can automate content distribution at scale. Whether building a backend system, using workflow builders (n8n/Make), or integrating AI content generation, Blotato provides a flexible foundation for modern content automation.

---

**Version**: API v2  
**Last Updated**: November 2024  
**Base URL**: `https://backend.blotato.com`  
**Authentication**: `blotato-api-key` header
