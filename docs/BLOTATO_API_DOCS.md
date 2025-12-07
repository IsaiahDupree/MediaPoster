# Blotato API v2 Documentation

## Upload Media `/v2/media`

### Endpoint

**Base URL:** `https://backend.blotato.com/v2`
**URL:** `/media`
**Method:** `POST`

### Description

Upload media by providing a URL. Returns a new media URL hosted on `database.blotato.com` for use in posts.

You can upload:
- Publicly accessible URLs
- Base64 encoded image data

**Limit:** 200MB file size or smaller
**Rate Limit:** 10 requests/minute (user-level)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | `string` | ✅ | The URL of the media to upload |

### Response

**Success (201 Created):**
```json
{
  "url": "https://database.blotato.com/path-to-uploaded-media.jpg"
}
```

**Rate Limit (429):**
```json
{
  "statusCode": 429,
  "message": "Rate limit exceeded, retry in 49 seconds"
}
```

### Google Drive URLs

Convert sharing URLs to download format:

**From:** `https://drive.google.com/file/d/FILE_ID/view?usp=drivesdk`
**To:** `https://drive.google.com/uc?export=download&id=FILE_ID`

**Note:** Large videos (100MB+) may show "can't scan for viruses" error. Use Dropbox, S3, or GCP instead.

---

## Publish Post `/v2/posts`

### Endpoint

**Base URL:** `https://backend.blotato.com/v2`
**URL:** `/posts`
**Method:** `POST`

### Description

Publish posts to supported platforms. Posts are queued for publishing.

**Rate Limit:** 30 requests/minute (user-level)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `post` | `object` | ✅ | Post content and metadata |
| `scheduledTime` | `string` | ❌ | ISO 8601 timestamp for scheduling |
| `useNextFreeSlot` | `boolean` | ❌ | Use next available slot (default: false) |

### Post Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `accountId` | `string` | ✅ | Connected account ID (format: `acc_xxxxx`) |
| `content` | `object` | ✅ | Post content |
| `target` | `object` | ✅ | Target platform configuration |

### Content Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | `string` | ✅ | Post caption/text |
| `mediaUrls` | `Array<string>` | ✅ | Media URLs (must be blotato.com domain) |
| `platform` | `string` | ✅ | Platform: `twitter`, `linkedin`, `facebook`, `instagram`, `pinterest`, `tiktok`, `threads`, `bluesky`, `youtube` |
| `additionalPosts` | `Array<object>` | ❌ | For threads (Twitter, Bluesky, Threads) |

### Platform-Specific Targets

#### Twitter
```json
{
  "targetType": "twitter"
}
```

#### Instagram
```json
{
  "targetType": "instagram",
  "mediaType": "reel" | "story",  // Optional, default: "reel"
  "altText": "string"  // Optional, max 1000 chars
}
```

#### TikTok
```json
{
  "targetType": "tiktok",
  "privacyLevel": "PUBLIC_TO_EVERYONE" | "SELF_ONLY" | "MUTUAL_FOLLOW_FRIENDS" | "FOLLOWER_OF_CREATOR",
  "disabledComments": boolean,
  "disabledDuet": boolean,
  "disabledStitch": boolean,
  "isBrandedContent": boolean,
  "isYourBrand": boolean,
  "isAiGenerated": boolean,
  "title": "string",  // Optional, <90 chars
  "autoAddMusic": boolean,  // Optional
  "isDraft": boolean,  // Optional
  "imageCoverIndex": number,  // Optional
  "videoCoverTimestamp": number  // Optional (ms)
}
```

#### Facebook
```json
{
  "targetType": "facebook",
  "pageId": "string",  // Required
  "mediaType": "video" | "reel"  // Optional
}
```

#### YouTube
```json
{
  "targetType": "youtube",
  "title": "string",  // Required
  "privacyStatus": "private" | "public" | "unlisted",  // Required
  "shouldNotifySubscribers": boolean,  // Required
  "isMadeForKids": boolean,  // Optional
  "containsSyntheticMedia": boolean  // Optional
}
```

#### Pinterest
```json
{
  "targetType": "pinterest",
  "boardId": "string",  // Required
  "title": "string",  // Optional
  "altText": "string",  // Optional
  "link": "string"  // Optional
}
```

#### LinkedIn
```json
{
  "targetType": "linkedin",
  "pageId": "string"  // Optional
}
```

#### Threads
```json
{
  "targetType": "threads",
  "replyControl": "everyone" | "accounts_you_follow" | "mentioned_only"  // Optional
}
```

#### Bluesky
```json
{
  "targetType": "bluesky"
}
```

### Response

**Success (201 Created):**
```json
{
  "postSubmissionId": "UNIQUE_POST_SUBMISSION_ID"
}
```

Failed posts appear at: https://my.blotato.com/failed

### Examples

#### Simple Twitter Post
```json
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

#### Instagram Reel with Media
```json
{
  "post": {
    "accountId": "acc_67890",
    "content": {
      "text": "Check this out! #viral",
      "mediaUrls": ["https://database.blotato.com/video.mp4"],
      "platform": "instagram"
    },
    "target": {
      "targetType": "instagram",
      "mediaType": "reel"
    }
  }
}
```

#### Scheduled Post
```json
{
  "post": {
    "accountId": "acc_12345",
    "content": {
      "text": "Scheduled content",
      "mediaUrls": [],
      "platform": "twitter"
    },
    "target": {
      "targetType": "twitter"
    }
  },
  "scheduledTime": "2025-03-10T15:30:00Z"
}
```

#### Twitter Thread
```json
{
  "post": {
    "accountId": "acc_12345",
    "content": {
      "text": "First tweet",
      "mediaUrls": [],
      "platform": "twitter",
      "additionalPosts": [
        {
          "text": "Second tweet",
          "mediaUrls": []
        },
        {
          "text": "Third tweet",
          "mediaUrls": []
        }
      ]
    },
    "target": {
      "targetType": "twitter"
    }
  }
}
```

## Important Notes

1. **Account ID Format:** Must be `acc_xxxxx` format, not numeric IDs
2. **Media URLs:** Must be from `database.blotato.com` (upload via `/v2/media` first)
3. **Headers:** Use `blotato-api-key: YOUR_KEY`
4. **Rate Limits:**
   - Media uploads: 10/min
   - Post publishing: 30/min
5. **Failed Posts:** Check at https://my.blotato.com/failed
