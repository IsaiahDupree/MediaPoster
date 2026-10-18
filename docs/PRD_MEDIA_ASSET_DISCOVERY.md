# PRD: Media Asset Discovery

**Version:** 1.0  
**Date:** January 19, 2026  
**Status:** Proposed  
**Priority:** Medium  
**Estimated Effort:** 2-3 weeks

---

## Executive Summary

Build an integrated media discovery system that allows creators to find and use GIFs, stock videos, and images directly within MediaPoster. This eliminates context-switching to external sites and streamlines the content creation workflow.

---

## Problem Statement

### Current State
- Creators manually search Giphy, Pexels, Unsplash separately
- Copy/paste URLs or download/re-upload assets
- No integration with video editor or post composer
- Time wasted switching between tools

### User Pain Points
1. Breaking workflow to find assets
2. Managing downloads and re-uploads
3. No search history or favorites
4. License confusion (commercial use?)
5. No AI-powered suggestions based on content

---

## Goals & Success Metrics

### Goals
1. Unified search across GIF, video, and image providers
2. One-click insert into posts/videos
3. AI-suggested assets based on content context
4. License-safe commercial use assets
5. Personal media library with favorites

### Success Metrics

| Metric | Target |
|--------|--------|
| Asset searches/user/week | 10+ |
| Insert rate (search → use) | > 30% |
| Time saved per post | 2-3 minutes |
| AI suggestion acceptance | > 25% |

---

## Features

### Phase 1: Multi-Provider Search (Week 1)

#### 1.1 Supported Providers

| Provider | Asset Type | License | API |
|----------|-----------|---------|-----|
| **Giphy** | GIFs, Stickers | Free for all use | ✅ Free tier |
| **Tenor** | GIFs | Free for all use | ✅ Free tier |
| **Pexels** | Videos, Photos | Free commercial | ✅ Free |
| **Pixabay** | Videos, Photos, Vectors | Free commercial | ✅ Free |
| **Unsplash** | Photos | Free commercial | ✅ Free |
| **Coverr** | Videos | Free commercial | ✅ Free |
| **Mixkit** | Videos, Music | Free commercial | Scraping |

#### 1.2 Unified Search Interface
- Single search box, all providers
- Filter by asset type (GIF, Video, Photo)
- Filter by provider
- Filter by orientation (landscape, portrait, square)
- Filter by duration (for videos)
- Color search (dominant color filter)
- Safe search toggle

#### 1.3 Search Results
- Thumbnail grid view
- Hover preview (animated for GIFs/videos)
- Quick info: resolution, duration, provider
- License badge
- One-click copy URL
- One-click insert to editor

### Phase 2: AI-Powered Suggestions (Week 2)

#### 2.1 Context-Aware Suggestions
- **Post composer:** Suggest based on caption text
- **Video editor:** Suggest B-roll based on transcript
- **Content repurposing:** Auto-suggest overlays for clips

#### 2.2 AI Analysis
```
Input: "Just finished my morning workout routine 💪"
Output suggestions:
- GIFs: workout, fitness, exercise, gym, strong
- Videos: gym footage, running, weights
- Images: fitness motivation, healthy lifestyle
```

#### 2.3 Trending Assets
- Platform-specific trending (TikTok trends, meme formats)
- Seasonal/event-based suggestions
- Niche-specific recommendations

### Phase 3: Media Library & Integration (Week 2-3)

#### 3.1 Personal Media Library
- **Favorites:** Save assets for later
- **Collections:** Organize by project/theme
- **Recent:** Quick access to recently used
- **Uploads:** User's own assets
- **Brand assets:** Logos, watermarks, templates

#### 3.2 Integration Points

| Integration | Functionality |
|-------------|--------------|
| Post Composer | Insert GIF/image into post |
| Video Editor | Add B-roll, overlays, stickers |
| Content Repurposing | Auto-suggest B-roll for clips |
| Story Creator | Stickers, backgrounds |
| Thumbnail Generator | Background images |

#### 3.3 Asset Processing
- Auto-resize for platform requirements
- Format conversion (WebP → PNG, etc.)
- Compression optimization
- Watermark removal detection

---

## Technical Architecture

### Database Schema

```sql
-- Media assets (cached from providers)
CREATE TABLE media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Provider info
    provider VARCHAR(20) NOT NULL, -- giphy, pexels, unsplash, etc
    provider_id VARCHAR(255) NOT NULL,
    
    -- Asset info
    asset_type VARCHAR(20) NOT NULL, -- gif, video, photo, sticker
    title VARCHAR(255),
    description TEXT,
    tags JSONB DEFAULT '[]',
    
    -- URLs
    thumbnail_url TEXT NOT NULL,
    preview_url TEXT,
    download_url TEXT NOT NULL,
    
    -- Metadata
    width INTEGER,
    height INTEGER,
    duration_seconds FLOAT, -- for videos/gifs
    file_size_bytes BIGINT,
    format VARCHAR(20),
    
    -- License
    license_type VARCHAR(50),
    attribution_required BOOLEAN DEFAULT false,
    attribution_text TEXT,
    
    -- Search optimization
    search_vector tsvector,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(provider, provider_id)
);

-- User favorites
CREATE TABLE media_favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    asset_id UUID REFERENCES media_assets(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES media_collections(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, asset_id)
);

-- User collections
CREATE TABLE media_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Search history
CREATE TABLE media_search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    query VARCHAR(255) NOT NULL,
    filters JSONB,
    results_count INTEGER,
    selected_asset_id UUID REFERENCES media_assets(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Asset usage tracking
CREATE TABLE media_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    asset_id UUID REFERENCES media_assets(id),
    
    used_in_type VARCHAR(20), -- post, video, story
    used_in_id UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_media_assets_search ON media_assets USING gin(search_vector);
CREATE INDEX idx_media_assets_type ON media_assets(asset_type);
CREATE INDEX idx_media_favorites_user ON media_favorites(user_id);
CREATE INDEX idx_media_search_user ON media_search_history(user_id, created_at DESC);
```

### API Endpoints

```
# Search
GET    /api/media/search                     # Unified search
GET    /api/media/search/gifs                # GIFs only
GET    /api/media/search/videos              # Videos only  
GET    /api/media/search/photos              # Photos only
GET    /api/media/trending                   # Trending assets
GET    /api/media/suggestions                # AI suggestions

# Asset Details
GET    /api/media/assets/{id}                # Get asset details
GET    /api/media/assets/{id}/download       # Proxy download

# Favorites & Collections
GET    /api/media/favorites                  # List favorites
POST   /api/media/favorites                  # Add favorite
DELETE /api/media/favorites/{id}             # Remove favorite
GET    /api/media/collections                # List collections
POST   /api/media/collections                # Create collection
PUT    /api/media/collections/{id}           # Update collection
DELETE /api/media/collections/{id}           # Delete collection

# History
GET    /api/media/history                    # Search history
GET    /api/media/recent                     # Recently used

# User uploads
POST   /api/media/upload                     # Upload own asset
GET    /api/media/uploads                    # List uploads
DELETE /api/media/uploads/{id}               # Delete upload
```

### Provider Integration

```python
# Backend/services/media/providers/base.py

from abc import ABC, abstractmethod
from typing import List, Optional

class MediaProvider(ABC):
    """Base class for media providers"""
    
    @abstractmethod
    async def search(
        self,
        query: str,
        asset_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[MediaAsset]:
        pass
    
    @abstractmethod
    async def get_trending(
        self,
        asset_type: Optional[str] = None,
        limit: int = 20
    ) -> List[MediaAsset]:
        pass
    
    @abstractmethod
    async def get_asset(self, provider_id: str) -> MediaAsset:
        pass
```

```python
# Backend/services/media/providers/giphy.py

import httpx

class GiphyProvider(MediaProvider):
    BASE_URL = "https://api.giphy.com/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def search(
        self,
        query: str,
        asset_type: str = "gifs",
        limit: int = 20,
        offset: int = 0
    ) -> List[MediaAsset]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/{asset_type}/search",
                params={
                    "api_key": self.api_key,
                    "q": query,
                    "limit": limit,
                    "offset": offset,
                    "rating": "g"
                }
            )
            data = response.json()
            return [self._to_media_asset(item) for item in data["data"]]
    
    def _to_media_asset(self, item: dict) -> MediaAsset:
        return MediaAsset(
            provider="giphy",
            provider_id=item["id"],
            asset_type="gif",
            title=item.get("title"),
            thumbnail_url=item["images"]["fixed_height_small"]["url"],
            preview_url=item["images"]["fixed_height"]["url"],
            download_url=item["images"]["original"]["url"],
            width=int(item["images"]["original"]["width"]),
            height=int(item["images"]["original"]["height"])
        )
```

### File Structure

```
Backend/
├── services/
│   └── media/
│       ├── __init__.py
│       ├── media_service.py          # Unified search orchestrator
│       ├── ai_suggestions.py         # AI-powered suggestions
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py               # Abstract base class
│       │   ├── giphy.py              # Giphy API
│       │   ├── tenor.py              # Tenor API
│       │   ├── pexels.py             # Pexels API
│       │   ├── pixabay.py            # Pixabay API
│       │   ├── unsplash.py           # Unsplash API
│       │   └── coverr.py             # Coverr API
│       └── cache/
│           └── asset_cache.py        # Redis caching for results
├── api/
│   └── endpoints/
│       └── media_api.py

dashboard/
├── app/
│   └── (dashboard)/
│       └── media/
│           ├── page.tsx              # Media browser
│           ├── favorites/
│           │   └── page.tsx          # Favorites view
│           └── collections/
│               └── page.tsx          # Collections manager
├── components/
│   └── media/
│       ├── MediaBrowser.tsx          # Main browser component
│       ├── SearchBar.tsx             # Search input with filters
│       ├── AssetGrid.tsx             # Results grid
│       ├── AssetCard.tsx             # Single asset preview
│       ├── AssetPreview.tsx          # Full preview modal
│       ├── CollectionPicker.tsx      # Save to collection
│       └── MediaPicker.tsx           # Embeddable picker component
```

---

## User Interface

### Media Browser
```
┌─────────────────────────────────────────────────────────────────┐
│  Media Library                           [Upload] [Collections] │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🔍 [Search GIFs, videos, photos...                    ] [🔍]   │
│                                                                   │
│  Filters: [All Types ▼] [All Providers ▼] [Any Orientation ▼]   │
│                                                                   │
│  Tabs: [All] [GIFs] [Videos] [Photos] [Favorites] [Recent]      │
│                                                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │  🎬     │ │  📷     │ │  🎭     │ │  🎬     │ │  📷     │   │
│  │ [GIF]   │ │ [Photo] │ │ [GIF]   │ │ [Video] │ │ [Photo] │   │
│  │ Giphy   │ │ Pexels  │ │ Tenor   │ │ Pixabay │ │Unsplash │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │         │ │         │ │         │ │         │ │         │   │
│  │         │ │         │ │         │ │         │ │         │   │
│  │         │ │         │ │         │ │         │ │         │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                                   │
│  [Load More...]                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Asset Preview Modal
```
┌─────────────────────────────────────────────────────────────────┐
│  Preview                                              [×]        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                          │    │
│  │                    [Asset Preview]                       │    │
│  │                     (Animated/Video)                     │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  "Happy celebration dance"                                       │
│  Provider: Giphy • Type: GIF • 480×360 • 2.4 MB                 │
│  License: ✅ Free for all use                                    │
│                                                                   │
│  Tags: happy, dance, celebration, excited, party                 │
│                                                                   │
│  [♡ Favorite] [📁 Add to Collection] [📋 Copy URL]              │
│                                                                   │
│  [Insert to Post] [Insert to Video] [Download]                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Embedded Picker (in Post Composer)
```
┌─────────────────────────────────────────────────────────────────┐
│  New Post                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Just finished my morning workout routine 💪              │    │
│  │ Feeling strong and ready to take on the day!            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  [📷 Photo] [🎬 Video] [🎭 GIF] [📍 Location] [#️⃣ Tags]        │
│                                                                   │
│  ┌─ AI Suggested GIFs ────────────────────────────────────┐     │
│  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ [See More →] │     │
│  │ │💪   │ │🏋️   │ │🏃   │ │💯   │ │🎉   │               │     │
│  │ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘               │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  [Schedule] [Post Now]                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Keys Required

| Provider | API Key | Rate Limit | Link |
|----------|---------|------------|------|
| Giphy | Required | 42 req/hr (free) | https://developers.giphy.com |
| Tenor | Required | 50 req/min | https://tenor.com/developer |
| Pexels | Required | 200 req/hr | https://www.pexels.com/api |
| Pixabay | Required | 5000 req/hr | https://pixabay.com/api/docs |
| Unsplash | Required | 50 req/hr | https://unsplash.com/developers |

---

## Implementation Timeline

| Day | Task |
|-----|------|
| 1-2 | Provider base class, Giphy + Tenor integration |
| 3-4 | Pexels, Pixabay, Unsplash integration |
| 5 | Unified search API, caching layer |
| 6-7 | Frontend: Media browser, search, filters |
| 8-9 | Favorites, collections, history |
| 10 | AI suggestions integration |
| 11-12 | Embeddable picker, editor integrations |
| 13-14 | Testing, performance optimization |

---

## Dependencies

- **Redis:** Search result caching
- **OpenAI:** AI-powered suggestions
- **FFmpeg:** Video/GIF processing
- **Sharp:** Image resizing/optimization

---

## Future Enhancements

1. **Audio search:** Find music/sound effects (Freesound, Epidemic Sound)
2. **AI image generation:** DALL-E/Midjourney integration
3. **Brand asset management:** Logo library, templates
4. **Team shared libraries:** Organization-wide collections
5. **Usage analytics:** Track which assets perform best

---

**Document Owner:** Product Team  
**Last Updated:** January 19, 2026
