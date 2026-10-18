# SoundCloud API

## Overview
- **Host**: `soundcloud-api3.p.rapidapi.com`
- **Base URL**: `https://soundcloud-api3.p.rapidapi.com`
- **Status**: ⚠️ Requires subscription
- **Rating**: 9.6/10
- **Provider**: Patrick
- **RapidAPI Link**: https://rapidapi.com/Patrick1999/api/soundcloud-api

## Features
- Search artists, tracks, albums, playlists
- Get detailed artist/track info
- Stream URLs for listening/downloading
- Album and playlist data

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: soundcloud-api3.p.rapidapi.com
```

## Expected Endpoints

### GET /search
Search for tracks, artists, or playlists.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `type` | string | No | track, artist, playlist |

---

### GET /track
Get track details.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | SoundCloud track URL |

---

### GET /user
Get artist/user profile.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | SoundCloud user URL |

---

### GET /playlist
Get playlist details.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | SoundCloud playlist URL |

---

## Alternative: SoundCloud Scraper

- **Host**: Various
- **Rating**: 9.9/10
- **Features**: Albums, playlists, profiles, high-quality audio downloads

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "soundcloud-api3.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# Search tracks
response = httpx.get(
    f"https://{HOST}/search",
    headers=headers,
    params={"query": "artist name"}
)

data = response.json()
print(data)
```

---

*Last Updated: December 2024*
