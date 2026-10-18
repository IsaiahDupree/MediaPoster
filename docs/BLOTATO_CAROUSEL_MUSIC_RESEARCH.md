# Blotato Carousel Posts & Music Research

## Summary

**Key Finding:** Blotato API does NOT support specifying a specific music/sound ID when publishing. The only music-related option is `autoAddMusic: true` which lets TikTok automatically recommend music for photo posts.

## Blotato API - Carousel Support

### Instagram Carousels
```json
{
  "post": {
    "accountId": "acc_123",
    "content": {
      "text": "Check out this carousel!",
      "mediaUrls": [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg"
      ],
      "platform": "instagram"
    },
    "target": {
      "targetType": "instagram",
      "altText": "Alt text for images"
    }
  }
}
```

**Notes:**
- Multiple images in `mediaUrls` = carousel post
- Reels are video-only and **cannot** appear in carousel items
- `altText` only supported on single image or image media in carousel

### TikTok Slideshows (Photo Carousel)
```json
{
  "post": {
    "accountId": "acc_123",
    "content": {
      "text": "TikTok slideshow!",
      "mediaUrls": [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg"
      ],
      "platform": "tiktok"
    },
    "target": {
      "targetType": "tiktok",
      "privacyLevel": "PUBLIC_TO_EVERYONE",
      "title": "My Slideshow",
      "autoAddMusic": true,
      "imageCoverIndex": 0
    }
  }
}
```

**TikTok-specific parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `autoAddMusic` | boolean | Auto-add TikTok recommended music (photo posts only) |
| `imageCoverIndex` | number | Which image to use as cover (0-indexed) |
| `title` | string | Title for image posts (max 90 chars, no effect on video) |

## Music ID Limitation

### What Blotato Supports
- `autoAddMusic: true` - TikTok auto-recommends music for photo posts
- **No video music support** - `autoAddMusic` has no effect on video posts

### What Blotato Does NOT Support
- ❌ Specifying a specific music/sound ID
- ❌ Adding music to video posts
- ❌ Instagram Reels music
- ❌ Custom audio tracks

### TikTok API Limitation
The official TikTok Content Posting API does NOT support:
- Posting with a specific sound/music ID
- Adding background music to videos programmatically

TikTok's Research API only allows READING `music_id` from existing videos, not posting with one.

## Workarounds for Background Music

### Option 1: Pre-render with Remotion (Recommended)
Render the video with background music baked in before uploading.

```
Video + Music → Remotion Render → Final Video → Blotato Upload
```

**Pros:**
- Full control over music, volume, timing
- Works on all platforms
- No platform restrictions

**Cons:**
- Requires Remotion rendering infrastructure
- Music must be royalty-free
- Won't use TikTok's trending sounds

### Option 2: Use autoAddMusic for TikTok Photos
Let TikTok automatically add recommended music.

```json
{
  "target": {
    "targetType": "tiktok",
    "autoAddMusic": true
  }
}
```

**Pros:**
- Uses TikTok's music library
- May use trending sounds
- No copyright issues

**Cons:**
- Only works for photo posts (slideshows)
- No control over which music is selected
- Doesn't work for video posts

### Option 3: Manual Addition
Post without music, then manually add music via the platform's app.

**Pros:**
- Access to full music library
- Can use trending sounds

**Cons:**
- Requires manual intervention
- Breaks automation workflow

## Implementation Recommendations

### For MediaPoster
1. **Pre-render music into videos** using Remotion before publishing
2. **Use `autoAddMusic: true`** for TikTok photo slideshows
3. **Document the limitation** - users cannot specify exact TikTok sounds

### Code Changes Needed

#### Update TikTokTarget dataclass
```python
@dataclass
class TikTokTarget:
    target_type: str = "tiktok"
    # ... existing fields ...
    auto_add_music: bool = False  # Already exists
    # NO music_id field - not supported by API
```

#### Schedule Post Flow
```
1. User selects music from our library
2. If video → Remotion renders music into video
3. If photo slideshow + user wants TikTok music → set autoAddMusic=true
4. Upload rendered video to Blotato
5. Publish
```

## Platform Music Support Matrix

| Platform | Carousel Support | Custom Music | Auto Music | Notes |
|----------|-----------------|--------------|------------|-------|
| TikTok | ✅ (photos only) | ❌ API | ✅ Photos only | Pre-render required for video music |
| Instagram | ✅ (images) | ❌ | ❌ | Reels can't be in carousel |
| YouTube | ❌ | ✅ (in video) | ❌ | Pre-render required |
| Twitter | ❌ | ✅ (in video) | ❌ | Pre-render required |
| Threads | ❌ | ✅ (in video) | ❌ | Pre-render required |
| Pinterest | ✅ | ✅ (in video) | ❌ | Pre-render required |
| LinkedIn | ❌ | ✅ (in video) | ❌ | Pre-render required |
| Facebook | ❌ | ✅ (in video) | ❌ | Pre-render required |

## References
- Blotato API: https://help.blotato.com/api/api-reference/publish-post
- TikTok Research API: https://developers.tiktok.com/doc/research-api-specs-query-videos
- TikTok Content Posting API: https://developers.tiktok.com/doc/content-posting-api

## Conclusion

**The only viable way to add specific background music to videos is to pre-render the music into the video using Remotion or FFmpeg before uploading to Blotato.** This is already planned in our Auto Music Matching feature (Phase 4).

For TikTok photo slideshows, we can use `autoAddMusic: true` to let TikTok add recommended music, but we cannot control which specific song is used.
