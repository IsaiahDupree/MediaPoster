# Provider Failover Strategy

## Overview

This document defines the failover strategy for RapidAPI social media providers, ensuring high availability and graceful degradation.

---

## Provider Priority by Platform

### TikTok
| Priority | Provider | Host | Status | Use Case |
|----------|----------|------|--------|----------|
| 1 (Primary) | TikTok Scraper7 | tiktok-scraper7.p.rapidapi.com | ✅ | User profiles, posts, metrics |
| 2 (Secondary) | TikTok Feature Summary | tiktok-video-feature-summary.p.rapidapi.com | ✅ | Backup for user data |
| 3 (Fallback) | TikTok Scraper TIKWM | tiktok-scraper.p.rapidapi.com | ⚠️ | Last resort |

### Instagram
| Priority | Provider | Host | Status | Use Case |
|----------|----------|------|--------|----------|
| 1 (Primary) | Instagram Looter2 | instagram-looter2.p.rapidapi.com | ✅ | Profile + posts |
| 2 (Secondary) | Instagram Statistics | instagram-statistics-api.p.rapidapi.com | ✅ | Analytics only |

### YouTube
| Priority | Provider | Host | Status | Use Case |
|----------|----------|------|--------|----------|
| 1 (Primary) | YT-API | yt-api.p.rapidapi.com | ✅ | All operations |

### Twitter/X
| Priority | Provider | Host | Status | Use Case |
|----------|----------|------|--------|----------|
| 1 (Primary) | The Old Bird | twitter-api45.p.rapidapi.com | ⚠️ | Rate limited |

### LinkedIn
| Priority | Provider | Host | Status | Use Case |
|----------|----------|------|--------|----------|
| 1 (Primary) | Real-Time LinkedIn | linkedin-data-scraper.p.rapidapi.com | ⚠️ | Profile enrichment |
| 2 (Secondary) | Fresh LinkedIn | fresh-linkedin-scraper-api.p.rapidapi.com | ⚠️ | Backup |

---

## Failover Decision Tree

```
Request comes in
    │
    ▼
┌─────────────────┐
│ Try Primary     │
│ Provider        │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Success │──────────▶ Return Data
    │  200?   │
    └────┬────┘
         │ No
         ▼
┌─────────────────┐
│ Error Type?     │
└────────┬────────┘
         │
    ┌────┼────┬────────┐
    │    │    │        │
   429  5xx  404     401
    │    │    │        │
    ▼    ▼    ▼        ▼
  Wait  Try   Log    Refresh
  +Retry Next Error   Key
         │
         ▼
┌─────────────────┐
│ Try Secondary   │
│ Provider        │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Success │──────────▶ Return Data
    │  200?   │
    └────┬────┘
         │ No
         ▼
┌─────────────────┐
│ Return Cached   │
│ + Queue Refresh │
└─────────────────┘
```

---

## Python Implementation

```python
import httpx
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import os

@dataclass
class ProviderConfig:
    name: str
    host: str
    priority: int
    error_count: int = 0
    last_error: Optional[datetime] = None
    disabled_until: Optional[datetime] = None

class ProviderRegistry:
    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.providers: Dict[str, List[ProviderConfig]] = {
            "tiktok": [
                ProviderConfig("tiktok-scraper7", "tiktok-scraper7.p.rapidapi.com", 1),
                ProviderConfig("tiktok-feature", "tiktok-video-feature-summary.p.rapidapi.com", 2),
            ],
            "instagram": [
                ProviderConfig("instagram-looter2", "instagram-looter2.p.rapidapi.com", 1),
                ProviderConfig("instagram-stats", "instagram-statistics-api.p.rapidapi.com", 2),
            ],
            "youtube": [
                ProviderConfig("yt-api", "yt-api.p.rapidapi.com", 1),
            ],
            "twitter": [
                ProviderConfig("the-old-bird", "twitter-api45.p.rapidapi.com", 1),
            ],
            "linkedin": [
                ProviderConfig("linkedin-realtime", "linkedin-data-scraper.p.rapidapi.com", 1),
                ProviderConfig("linkedin-fresh", "fresh-linkedin-scraper-api.p.rapidapi.com", 2),
            ],
        }
    
    def get_available_providers(self, platform: str) -> List[ProviderConfig]:
        """Get providers sorted by priority, excluding disabled ones."""
        now = datetime.now()
        providers = self.providers.get(platform, [])
        available = [
            p for p in providers 
            if p.disabled_until is None or p.disabled_until < now
        ]
        return sorted(available, key=lambda p: p.priority)
    
    def mark_error(self, platform: str, provider_name: str):
        """Mark a provider as having an error, potentially disabling it."""
        for p in self.providers.get(platform, []):
            if p.name == provider_name:
                p.error_count += 1
                p.last_error = datetime.now()
                # Disable for increasing durations based on error count
                if p.error_count >= 3:
                    p.disabled_until = datetime.now() + timedelta(minutes=5 * p.error_count)
                break
    
    def mark_success(self, platform: str, provider_name: str):
        """Reset error count on success."""
        for p in self.providers.get(platform, []):
            if p.name == provider_name:
                p.error_count = 0
                p.disabled_until = None
                break

registry = ProviderRegistry()

async def call_with_failover(
    platform: str,
    endpoint: str,
    params: Dict[str, Any],
    timeout: float = 15.0
) -> Optional[Dict]:
    """
    Call API with automatic failover to secondary providers.
    """
    providers = registry.get_available_providers(platform)
    
    if not providers:
        raise Exception(f"No available providers for {platform}")
    
    last_error = None
    
    for provider in providers:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{provider.host}{endpoint}",
                    headers={
                        "X-RapidAPI-Key": registry.api_key,
                        "X-RapidAPI-Host": provider.host,
                    },
                    params=params,
                    timeout=timeout,
                )
                
                if response.status_code == 200:
                    registry.mark_success(platform, provider.name)
                    return response.json()
                
                elif response.status_code == 429:
                    # Rate limited - wait and try next
                    registry.mark_error(platform, provider.name)
                    await asyncio.sleep(1)
                    continue
                
                elif response.status_code in (500, 502, 503, 504):
                    # Server error - try next
                    registry.mark_error(platform, provider.name)
                    continue
                
                elif response.status_code == 404:
                    # Endpoint not found - log and continue
                    last_error = f"404 from {provider.name}"
                    continue
                
                elif response.status_code == 401:
                    # Auth error - critical, don't try others
                    raise Exception(f"Authentication failed for {provider.name}")
                
        except httpx.TimeoutException:
            registry.mark_error(platform, provider.name)
            last_error = f"Timeout from {provider.name}"
            continue
        except Exception as e:
            registry.mark_error(platform, provider.name)
            last_error = str(e)
            continue
    
    # All providers failed
    raise Exception(f"All providers failed for {platform}: {last_error}")


# Example usage
async def get_tiktok_user(username: str) -> Dict:
    return await call_with_failover(
        platform="tiktok",
        endpoint="/user/info",
        params={"unique_id": username}
    )

async def get_instagram_profile(username: str) -> Dict:
    return await call_with_failover(
        platform="instagram",
        endpoint="/profile",
        params={"username": username}
    )

async def get_youtube_video(video_id: str) -> Dict:
    return await call_with_failover(
        platform="youtube",
        endpoint="/video/info",
        params={"id": video_id}
    )
```

---

## Health Monitoring

```python
async def check_provider_health():
    """Periodic health check for all providers."""
    results = {}
    
    test_params = {
        "tiktok": {"endpoint": "/user/info", "params": {"unique_id": "tiktok"}},
        "instagram": {"endpoint": "/profile", "params": {"username": "instagram"}},
        "youtube": {"endpoint": "/video/info", "params": {"id": "dQw4w9WgXcQ"}},
    }
    
    for platform, config in test_params.items():
        providers = registry.get_available_providers(platform)
        results[platform] = {}
        
        for provider in providers:
            try:
                start = datetime.now()
                response = await call_single_provider(
                    provider, config["endpoint"], config["params"]
                )
                latency = (datetime.now() - start).total_seconds() * 1000
                
                results[platform][provider.name] = {
                    "status": "healthy",
                    "latency_ms": round(latency, 2),
                }
            except Exception as e:
                results[platform][provider.name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
    
    return results
```

---

## Error Handling Matrix

| Error Code | Action | Retry? | Switch Provider? |
|------------|--------|--------|------------------|
| 200 | Success | No | No |
| 400 | Bad Request | No | No (fix params) |
| 401 | Auth Failed | No | No (fix key) |
| 403 | Forbidden | No | Yes |
| 404 | Not Found | No | Yes |
| 429 | Rate Limited | Yes (delay) | Yes |
| 500 | Server Error | Yes | Yes |
| 502 | Bad Gateway | Yes | Yes |
| 503 | Unavailable | Yes | Yes |
| 504 | Timeout | Yes | Yes |

---

## Recommendations

### KEEP (Primary Providers)
- ✅ `tiktok-scraper7` - Best coverage, stable
- ✅ `instagram-looter2` - Reliable profile data
- ✅ `yt-api` - Comprehensive YouTube data
- ✅ `instagram-statistics-api` - Analytics

### KEEP (Secondary/Fallback)
- 🟡 `tiktok-video-feature-summary` - Backup
- 🟡 `linkedin-data-scraper` - Rate limited but works

### REPLACE/UPGRADE
- ⚠️ `twitter-api45` - Consider PRO tier
- ⚠️ `threads-api4` - Need to subscribe
- ⚠️ LinkedIn APIs - Need higher tier for reliable access

### REMOVE
- ❌ Duplicate YouTube MP3 converters
- ❌ Low-rated TikTok scrapers (< 9.0 rating)
- ❌ Deprecated Instagram APIs

---

*Last Updated: December 20, 2024*
