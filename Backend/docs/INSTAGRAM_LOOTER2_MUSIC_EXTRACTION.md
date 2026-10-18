# Instagram Looter2 API - Music Extraction Results

**Date:** 2025-12-26  
**API:** Instagram Looter2 (instagram-looter2.p.rapidapi.com)  
**Status:** ✅ **WORKING**

## ✅ Success Summary

**Test Results:**
- ✅ API endpoint `/profile` works
- ✅ Successfully extracted **11 video/reel tracks** from @instagram
- ✅ Retrieved video URLs (can be used for audio extraction)
- ✅ Retrieved engagement metrics (views, likes, comments)
- ✅ Extracted hashtags and captions

## 📊 Data Retrieved

### What We Got:
1. **Video URLs** - Direct URLs to video files (can extract audio from these)
2. **Engagement Metrics:**
   - View counts (play_count)
   - Like counts
   - Comment counts
3. **Content Data:**
   - Captions
   - Hashtags
   - Shortcodes
   - Timestamps

### What We Didn't Get:
- ❌ Direct audio URLs (not available in this API)
- ❌ Music track titles/artists (not in response structure)
- ❌ Audio metadata (music_id, etc.)

## 🎵 Audio Extraction Strategy

Since Instagram Looter2 doesn't provide direct audio URLs, we can:

### Option 1: Extract Audio from Video URLs
```python
import subprocess

def extract_audio_from_video(video_url: str, output_path: str):
    """Extract audio from video URL using FFmpeg"""
    cmd = [
        'ffmpeg',
        '-i', video_url,
        '-vn',  # No video
        '-acodec', 'libmp3lame',
        '-ab', '192k',
        '-y',
        output_path
    ]
    subprocess.run(cmd, check=True)
```

### Option 2: Use Video URL as Audio Source
- Download video file
- Extract audio track using FFmpeg
- Save as MP3/WAV

## 📋 API Endpoints Used

### ✅ Working Endpoints:

1. **GET /profile**
   ```python
   GET https://instagram-looter2.p.rapidapi.com/profile?username=instagram
   ```
   - Returns: Profile data + 12 most recent posts/reels
   - Includes: Video URLs, engagement metrics, captions

2. **GET /post** (for detailed post info)
   ```python
   GET https://instagram-looter2.p.rapidapi.com/post?shortcode=DSvIp-OkfHI
   ```
   - Returns: Detailed post information
   - May contain additional metadata

## 📊 Example Response Structure

```json
{
  "edge_owner_to_timeline_media": {
    "edges": [
      {
        "node": {
          "id": "3456789012345678901",
          "shortcode": "DSvIp-OkfHI",
          "typename": "GraphVideo",
          "is_video": true,
          "video_view_count": 5926304,
          "display_url": "https://instagram.fbcn2-1.fna.fbcdn.net/...",
          "edge_liked_by": {"count": 124824},
          "edge_media_to_comment": {"count": 2270},
          "edge_media_to_caption": {
            "edges": [{
              "node": {"text": "chef's kiss 🤌\n\n#InTheMoment"}
            }]
          }
        }
      }
    ]
  }
}
```

## 🔧 Usage Example

```python
import httpx
import os

API_KEY = os.getenv("RAPIDAPI_KEY")
API_BASE = "https://instagram-looter2.p.rapidapi.com"

async def get_reels_with_audio(username: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/profile",
            headers={
                "X-RapidAPI-Key": API_KEY,
                "X-RapidAPI-Host": "instagram-looter2.p.rapidapi.com"
            },
            params={"username": username}
        )
        
        data = response.json()
        edges = data.get("edge_owner_to_timeline_media", {}).get("edges", [])
        
        reels = []
        for edge in edges:
            node = edge["node"]
            if node.get("is_video"):
                reels.append({
                    "shortcode": node["shortcode"],
                    "video_url": node.get("display_url"),
                    "views": node.get("video_view_count", 0),
                    "likes": node.get("edge_liked_by", {}).get("count", 0),
                    "caption": node.get("edge_media_to_caption", {})
                        .get("edges", [{}])[0]
                        .get("node", {})
                        .get("text", "")
                })
        
        return reels
```

## 📈 Test Results

**Test Account:** @instagram  
**Posts Found:** 12  
**Video/Reel Tracks:** 11  
**Success Rate:** 91.7%

**Top Track:**
- Shortcode: `DSlBObBCTvK`
- Views: 41,333,907
- Likes: 551,810
- Comments: 6,644

## ✅ Next Steps

1. **Extract Audio from Videos:**
   - Use FFmpeg to extract audio from video URLs
   - Save as MP3/WAV files
   - Store for trend analysis

2. **Build Audio Database:**
   - Store video URLs
   - Extract and store audio files
   - Track usage across accounts

3. **Trend Analysis:**
   - Aggregate audio usage
   - Track trending sounds
   - Calculate velocity metrics

## 📝 Files Created

- **Test Script:** `Backend/scripts/test_instagram_looter_music.py`
- **Results:** `Backend/instagram_looter_music_results.json`
- **Documentation:** This file

## 🎯 Comparison: Looter2 vs Scraper Stable

| Feature | Looter2 | Scraper Stable |
|---------|---------|----------------|
| **Status** | ✅ Working | ❌ 404 errors |
| **Video URLs** | ✅ Yes | ❓ Unknown |
| **Direct Audio URLs** | ❌ No | ❓ Unknown |
| **Engagement Metrics** | ✅ Yes | ❓ Unknown |
| **Music Metadata** | ❌ No | ❓ Unknown |
| **Rate Limits** | 100/month (free) | Varies |

## 💡 Recommendation

**Use Instagram Looter2 API for:**
- ✅ Getting video/reel data
- ✅ Extracting engagement metrics
- ✅ Getting captions and hashtags
- ✅ Building media candidate pool

**For direct audio URLs:**
- Extract audio from video URLs using FFmpeg
- Or try to get Scraper Stable API working (if subscription allows)

