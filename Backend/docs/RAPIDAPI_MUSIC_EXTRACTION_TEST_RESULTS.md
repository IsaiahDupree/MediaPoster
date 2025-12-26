# RapidAPI Music Extraction - Test Results

**Date:** 2025-12-26  
**API:** Instagram Scraper Stable API (RockSolid APIs)  
**Base URL:** `https://instagram-scraper-stable-api.p.rapidapi.com`

## ⚠️ Current Status

**All endpoints tested returned 404 Not Found**

This suggests:
1. **Subscription/Plan Issue:** The API key may not have access to these endpoints (requires PRO plan)
2. **Endpoint Path Changes:** The actual endpoint paths may differ from documentation
3. **API Changes:** The API structure may have changed

## 🔍 Endpoints Tested

All of the following endpoints returned **404**:

### User Reels Endpoints
- `POST /v1/reels`
- `POST /v1/user_reels`
- `POST /user_reels`
- `POST /User Reels`
- `POST /UserReels`
- `POST /user/reels`
- `POST /api/v1/user_reels`

### Search Endpoints
- `POST /v1/search`
- `POST /search`
- `POST /Search`

### User Info Endpoints
- `POST /v1/info`
- `POST /Account Data`
- `POST /account_data`

### Media Endpoints
- `GET /v1/reel_by_shortcode`
- `GET /v1/media_by_shortcode`
- `GET /Detailed Reel Data`

## 📋 Expected Music Data Structure

Once endpoints are working, music data should be in this structure:

```json
{
  "data": {
    "items": [
      {
        "id": "reel_id",
        "code": "shortcode",
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
        "comment_count": 90
      }
    ]
  }
}
```

## 🎯 Music Extraction Code (Ready to Use)

Once endpoints are confirmed, use this code:

```python
import httpx
import os

API_BASE = "https://instagram-scraper-stable-api.p.rapidapi.com"
API_KEY = os.getenv("RAPIDAPI_KEY")

headers = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
    "Content-Type": "application/json"
}

async def extract_music_from_reels(username: str):
    """Extract music/audio from user reels"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # TODO: Replace with correct endpoint once confirmed
        response = await client.post(
            f"{API_BASE}/CORRECT_ENDPOINT_HERE",
            headers=headers,
            json={
                "username_or_id_or_url": username,
                "count": 12
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", {}).get("items", [])
            
            music_tracks = []
            
            for item in items:
                clips_metadata = item.get("clips_metadata", {})
                
                # Extract music library audio
                music_info = clips_metadata.get("music_info", {})
                if music_info:
                    music_asset = music_info.get("music_asset_info", {})
                    audio_url = music_asset.get("progressive_download_url")
                    
                    if audio_url:
                        music_tracks.append({
                            "type": "music",
                            "audio_id": music_asset.get("audio_id"),
                            "title": music_asset.get("title"),
                            "artist": music_asset.get("display_artist"),
                            "audio_url": audio_url,
                            "duration_ms": music_asset.get("duration_in_ms"),
                            "reel_id": item.get("id"),
                            "reel_shortcode": item.get("code"),
                            "play_count": item.get("play_count", 0)
                        })
                
                # Extract original sound
                original_sound = clips_metadata.get("original_sound_info", {})
                if original_sound:
                    audio_asset = original_sound.get("audio_asset_info", {})
                    audio_url = audio_asset.get("progressive_download_url")
                    
                    if audio_url:
                        music_tracks.append({
                            "type": "original_sound",
                            "title": original_sound.get("original_audio_title", "Original Sound"),
                            "artist": original_sound.get("ig_artist", {}).get("username", "Unknown"),
                            "audio_url": audio_url,
                            "reel_id": item.get("id"),
                            "reel_shortcode": item.get("code"),
                            "play_count": item.get("play_count", 0)
                        })
            
            return music_tracks
        
        return []
```

## 🔧 Next Steps

1. **Verify API Subscription:**
   - Check RapidAPI dashboard for plan level
   - Ensure PRO plan is active if required
   - Verify API key has access to Instagram Scraper Stable API

2. **Get Correct Endpoint Names:**
   - Use RapidAPI playground to test endpoints
   - Copy exact endpoint paths from successful requests
   - Update test scripts with correct paths

3. **Test with Known Working Account:**
   - Use an account that definitely has reels with music
   - Test with a verified account (e.g., @instagram)

4. **Update Documentation:**
   - Once endpoints are confirmed, update:
     - `Backend/docs/rapidapi/instagram-scraper-stable-api.md`
     - `Backend/tests/test_rapidapi_music_extraction.py`
     - `Backend/services/audio_service.py`

## 📝 Test Script Location

**Test Script:** `Backend/tests/test_rapidapi_music_extraction.py`  
**Discovery Script:** `Backend/scripts/discover_rapidapi_endpoints.py`

Both scripts are ready to use once correct endpoints are identified.

## 🎵 Expected Music Data Fields

When extraction works, you should get:

- **audio_id** / **music_id**: Unique identifier for the track
- **title**: Music track title
- **artist** / **display_artist**: Artist name
- **progressive_download_url**: Direct download URL for audio file
- **duration_ms**: Track duration in milliseconds
- **reel_id**: ID of reel using this audio
- **play_count**: Views/plays of the reel
- **type**: "music" or "original_sound"

## ✅ Verification Checklist

- [ ] API subscription verified (PRO plan if required)
- [ ] Correct endpoint paths identified
- [ ] Test script runs successfully
- [ ] Music URLs are accessible
- [ ] Audio files can be downloaded
- [ ] Documentation updated with working endpoints

