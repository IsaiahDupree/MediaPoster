# RapidAPI Audio Extraction Guide

**Quick Reference:** How to obtain audio files from Instagram using RapidAPI

## 📚 Main Documentation

**Full API Documentation:** `Backend/docs/rapidapi/instagram-scraper-stable-api.md`

## 🎵 Audio Extraction from Instagram Reels

### Endpoint: `POST /v1/reels`

**Base URL:** `https://instagram-scraper-stable-api.p.rapidapi.com`

### Request

```bash
curl -X POST "https://instagram-scraper-stable-api.p.rapidapi.com/v1/reels" \
  -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
  -H "X-RapidAPI-Host: instagram-scraper-stable-api.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_id_or_url": "username",
    "count": 12
  }'
```

### Response - Audio URLs

The response contains audio URLs in two locations:

#### 1. Music Audio (from music library)
```json
{
  "data": {
    "items": [{
      "clips_metadata": {
        "music_info": {
          "music_asset_info": {
            "progressive_download_url": "https://audio-url.mp3",
            "title": "Music Title",
            "display_artist": "Artist Name",
            "audio_id": "audio_id",
            "duration_in_ms": 30000
          }
        }
      }
    }]
  }
}
```

#### 2. Original Sound (user's original audio)
```json
{
  "data": {
    "items": [{
      "clips_metadata": {
        "original_sound_info": {
          "audio_asset_info": {
            "progressive_download_url": "https://audio-url.mp3"
          },
          "original_audio_title": "Original Sound",
          "ig_artist": {
            "username": "artist_username"
          }
        }
      }
    }]
  }
}
```

## 🔧 Using the Audio Service

### Python Code Example

```python
from services.audio_service import AudioService

# Initialize service
audio_service = AudioService()

# Fetch reels with audio
reels = await audio_service.fetch_reels_with_audio("username")

# Each reel contains audio metadata
for reel in reels:
    print(f"Title: {reel.title}")
    print(f"Artist: {reel.artist}")
    print(f"Audio URL: {reel.audio_url}")
    
    # Download the audio file
    file_path = await audio_service.download_audio(reel)
    print(f"Downloaded to: {file_path}")
```

### API Endpoint

**POST** `/api/audio/fetch`

```bash
curl -X POST "http://localhost:5555/api/audio/fetch" \
  -H "Content-Type: application/json" \
  -d '{
    "reel_url": "username"
  }'
```

**Response:**
```json
{
  "audio_id": "reel_id",
  "title": "Audio Title",
  "artist": "Artist Name",
  "duration_ms": 30000,
  "file_path": "/tmp/mediaposter/audio/audio_id_title.mp3",
  "file_size": 1234567,
  "stream_url": "/api/audio/stream/audio_id",
  "download_url": "/api/audio/download/audio_id",
  "cover_url": "https://thumbnail-url.jpg",
  "source": "instagram-stable"
}
```

## 📋 Audio URL Extraction Steps

1. **Call `/v1/reels` endpoint** with username
2. **Parse response** to get `clips_metadata`
3. **Check for music_info** first (music library audio)
4. **Fallback to original_sound_info** (user's original audio)
5. **Extract `progressive_download_url`** from either source
6. **Download** the audio file from the URL

## 🎯 Key Response Fields for Audio

| Field Path | Description |
|------------|-------------|
| `clips_metadata.music_info.music_asset_info.progressive_download_url` | Music library audio URL |
| `clips_metadata.original_sound_info.audio_asset_info.progressive_download_url` | Original sound audio URL |
| `clips_metadata.music_info.music_asset_info.title` | Music title |
| `clips_metadata.music_info.music_asset_info.display_artist` | Artist name |
| `video_versions[0].url` | Video URL (fallback if no direct audio) |

## 💡 Implementation Details

### Audio Service Location
- **File:** `Backend/services/audio_service.py`
- **Class:** `AudioService`
- **Method:** `fetch_reels_with_audio(username)`

### Storage
- **Directory:** `/tmp/mediaposter/audio`
- **Format:** MP3
- **Naming:** `{audio_id}_{title}.mp3`

### API Endpoints
- **Fetch Audio:** `POST /api/audio/fetch`
- **Stream Audio:** `GET /api/audio/stream/{audio_id}`
- **Download Audio:** `GET /api/audio/download/{audio_id}`

## 🔍 Example: Extract Audio from Reel

```python
import httpx

async def get_audio_from_reel(username: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://instagram-scraper-stable-api.p.rapidapi.com/v1/reels",
            headers={
                "X-RapidAPI-Key": "YOUR_KEY",
                "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
                "Content-Type": "application/json"
            },
            json={"username_or_id_or_url": username, "count": 12}
        )
        
        data = response.json()
        items = data.get("data", {}).get("items", [])
        
        audio_urls = []
        for item in items:
            clips = item.get("clips_metadata", {})
            
            # Try music first
            music_info = clips.get("music_info", {})
            if music_info:
                audio_url = music_info.get("music_asset_info", {}).get("progressive_download_url")
                if audio_url:
                    audio_urls.append({
                        "url": audio_url,
                        "title": music_info.get("music_asset_info", {}).get("title"),
                        "artist": music_info.get("music_asset_info", {}).get("display_artist")
                    })
                    continue
            
            # Fallback to original sound
            original_sound = clips.get("original_sound_info", {})
            if original_sound:
                audio_url = original_sound.get("audio_asset_info", {}).get("progressive_download_url")
                if audio_url:
                    audio_urls.append({
                        "url": audio_url,
                        "title": original_sound.get("original_audio_title", "Original Sound"),
                        "artist": original_sound.get("ig_artist", {}).get("username", "Unknown")
                    })
        
        return audio_urls
```

## 📖 Related Documentation

- **Full API Docs:** `Backend/docs/rapidapi/instagram-scraper-stable-api.md`
- **API Tests:** `Backend/tests/test_instagram_scraper_stable_api.py`
- **Audio Service:** `Backend/services/audio_service.py`
- **API Endpoints:** `Backend/api/endpoints/audio_api.py`

## ⚠️ Important Notes

1. **Rate Limits:** Check your RapidAPI plan limits
2. **Audio Availability:** Not all reels have extractable audio
3. **URL Expiration:** Audio URLs may expire, download promptly
4. **Format:** Audio is typically MP3 format
5. **Storage:** Audio files are stored in `/tmp/mediaposter/audio` by default

