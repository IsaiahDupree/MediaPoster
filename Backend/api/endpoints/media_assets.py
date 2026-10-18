"""
Media Assets API Endpoints (ASSET-004, ASSET-005)
===================================================
Unified search across Giphy, Pexels, Unsplash with favorites and collections.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import logging

router = APIRouter(prefix="/api/media-assets", tags=["Media Assets"])
logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================

class UnifiedSearchRequest(BaseModel):
    query: str
    providers: Optional[List[str]] = None
    asset_types: Optional[List[str]] = None
    limit_per_provider: int = 5


class FavoriteRequest(BaseModel):
    asset_id: str
    collection_id: Optional[str] = None


class CollectionRequest(BaseModel):
    name: str
    description: str = ""


class CollectionAssetRequest(BaseModel):
    asset_id: str
    collection_id: str


# =============================================================================
# Helper
# =============================================================================

def _get_service():
    from services.media_asset_service import get_media_asset_service, AssetProvider, AssetType
    return get_media_asset_service()


def _parse_providers(providers: Optional[List[str]]):
    if not providers:
        return None
    from services.media_asset_service import AssetProvider
    result = []
    for p in providers:
        try:
            result.append(AssetProvider(p.lower()))
        except ValueError:
            pass
    return result or None


def _parse_asset_types(asset_types: Optional[List[str]]):
    if not asset_types:
        return None
    from services.media_asset_service import AssetType
    result = []
    for t in asset_types:
        try:
            result.append(AssetType(t.lower()))
        except ValueError:
            pass
    return result or None


# =============================================================================
# ASSET-001: Giphy
# =============================================================================

@router.get("/giphy/search")
async def search_giphy(
    query: str,
    limit: int = Query(default=5, le=25),
    asset_type: str = "gif",
):
    """Search Giphy for GIFs or stickers."""
    from services.media_asset_service import AssetType
    svc = _get_service()
    at = AssetType.STICKER if asset_type == "sticker" else AssetType.GIF
    results = svc.search_giphy(query, limit=limit, asset_type=at)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/giphy/trending")
async def giphy_trending(limit: int = Query(default=10, le=25)):
    """Get trending GIFs from Giphy."""
    svc = _get_service()
    results = svc.get_giphy_trending(limit=limit)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/giphy/categories")
async def giphy_categories():
    """Get Giphy categories."""
    svc = _get_service()
    return {"categories": svc.get_giphy_categories()}


# =============================================================================
# ASSET-002: Pexels
# =============================================================================

@router.get("/pexels/photos")
async def search_pexels_photos(
    query: str,
    limit: int = Query(default=5, le=25),
    orientation: Optional[str] = None,
):
    """Search Pexels for photos."""
    svc = _get_service()
    results = svc.search_pexels_photos(query, limit=limit, orientation=orientation)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/pexels/videos")
async def search_pexels_videos(
    query: str,
    limit: int = Query(default=5, le=25),
):
    """Search Pexels for videos."""
    svc = _get_service()
    results = svc.search_pexels_videos(query, limit=limit)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/pexels/attribution/{asset_id}")
async def pexels_attribution(asset_id: str):
    """Get attribution text for a Pexels asset."""
    svc = _get_service()
    attribution = svc.get_pexels_attribution(asset_id)
    if attribution is None:
        raise HTTPException(status_code=404, detail="Asset not found or not a Pexels asset")
    return {"attribution": attribution}


# =============================================================================
# ASSET-003: Unsplash
# =============================================================================

@router.get("/unsplash/search")
async def search_unsplash(
    query: str,
    limit: int = Query(default=5, le=25),
    orientation: Optional[str] = None,
):
    """Search Unsplash for photos."""
    svc = _get_service()
    results = svc.search_unsplash(query, limit=limit, orientation=orientation)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/unsplash/collections")
async def unsplash_collections():
    """Get curated Unsplash collections."""
    svc = _get_service()
    return {"collections": svc.get_unsplash_collections()}


@router.post("/unsplash/track-download/{asset_id}")
async def track_unsplash_download(asset_id: str):
    """Track a download per Unsplash API guidelines."""
    svc = _get_service()
    tracked = svc.track_download(asset_id)
    if not tracked:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"tracked": True}


# =============================================================================
# ASSET-004: Unified Search
# =============================================================================

@router.get("/search")
async def unified_search(
    query: str,
    providers: Optional[str] = Query(default=None, description="Comma-separated: giphy,pexels,unsplash"),
    asset_types: Optional[str] = Query(default=None, description="Comma-separated: gif,video,photo,sticker"),
    limit_per_provider: int = Query(default=5, le=25),
):
    """Unified search across all providers (ASSET-004)."""
    svc = _get_service()
    provider_list = _parse_providers(providers.split(",") if providers else None)
    type_list = _parse_asset_types(asset_types.split(",") if asset_types else None)
    results = svc.unified_search(
        query,
        providers=provider_list,
        asset_types=type_list,
        limit_per_provider=limit_per_provider,
    )
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/trending")
async def trending(limit: int = Query(default=10, le=50)):
    """Get trending assets from all providers (ASSET-004)."""
    svc = _get_service()
    results = svc.get_trending(limit=limit)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/filter")
async def filter_results(
    query: str,
    provider: Optional[str] = None,
    asset_type: Optional[str] = None,
    orientation: Optional[str] = None,
    min_width: Optional[int] = None,
    min_height: Optional[int] = None,
):
    """Search then filter results by criteria (ASSET-004)."""
    from services.media_asset_service import AssetProvider, AssetType
    svc = _get_service()
    all_results = svc.unified_search(query)
    filtered = svc.filter_results(
        all_results,
        provider=AssetProvider(provider) if provider else None,
        asset_type=AssetType(asset_type) if asset_type else None,
        orientation=orientation,
        min_width=min_width,
        min_height=min_height,
    )
    return {"results": [r.to_dict() for r in filtered], "count": len(filtered)}


# =============================================================================
# ASSET-005: Asset Library (Favorites & Collections)
# =============================================================================

@router.post("/favorites")
async def add_favorite(req: FavoriteRequest):
    """Save an asset to favorites (ASSET-005)."""
    svc = _get_service()
    fav = svc.save_to_favorites(req.asset_id, collection_id=req.collection_id)
    if fav is None:
        raise HTTPException(status_code=404, detail="Asset not found in cache. Search first.")
    return {"favorite": fav.to_dict()}


@router.delete("/favorites/{asset_id}")
async def remove_favorite(asset_id: str):
    """Remove an asset from favorites (ASSET-005)."""
    svc = _get_service()
    removed = svc.remove_from_favorites(asset_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"removed": True}


@router.get("/favorites")
async def get_favorites():
    """Get all favorited assets (ASSET-005)."""
    svc = _get_service()
    favorites = svc.get_favorites()
    return {"favorites": [f.to_dict() for f in favorites], "count": len(favorites)}


@router.get("/favorites/{asset_id}/status")
async def check_favorite_status(asset_id: str):
    """Check if an asset is favorited (ASSET-005)."""
    svc = _get_service()
    return {"is_favorited": svc.is_favorited(asset_id)}


@router.post("/collections")
async def create_collection(req: CollectionRequest):
    """Create a new collection (ASSET-005)."""
    svc = _get_service()
    col = svc.create_collection(req.name, req.description)
    return {"collection": col.to_dict()}


@router.get("/collections")
async def list_collections():
    """List all collections (ASSET-005)."""
    svc = _get_service()
    collections = svc.list_collections()
    return {"collections": [c.to_dict() for c in collections], "count": len(collections)}


@router.get("/collections/{collection_id}")
async def get_collection(collection_id: str):
    """Get a specific collection (ASSET-005)."""
    svc = _get_service()
    col = svc.get_collection(collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"collection": col.to_dict()}


@router.get("/collections/{collection_id}/assets")
async def get_collection_assets(collection_id: str):
    """Get all assets in a collection (ASSET-005)."""
    svc = _get_service()
    col = svc.get_collection(collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    assets = svc.get_collection_assets(collection_id)
    return {"assets": [a.to_dict() for a in assets], "count": len(assets)}


@router.post("/collections/{collection_id}/assets")
async def add_to_collection(collection_id: str, req: FavoriteRequest):
    """Add an asset to a collection (ASSET-005)."""
    svc = _get_service()
    added = svc.add_to_collection(req.asset_id, collection_id)
    if not added:
        raise HTTPException(status_code=400, detail="Asset or collection not found")
    return {"added": True}


@router.delete("/collections/{collection_id}/assets/{asset_id}")
async def remove_from_collection(collection_id: str, asset_id: str):
    """Remove an asset from a collection (ASSET-005)."""
    svc = _get_service()
    removed = svc.remove_from_collection(asset_id, collection_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Asset not found in collection")
    return {"removed": True}


# =============================================================================
# Utilities
# =============================================================================

@router.get("/asset/{asset_id}")
async def get_asset(asset_id: str):
    """Get a cached asset by ID."""
    svc = _get_service()
    asset = svc.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found in cache")
    return {"asset": asset.to_dict()}


@router.get("/stats")
async def get_stats():
    """Get service statistics."""
    svc = _get_service()
    return {"stats": svc.get_stats()}


@router.get("/downloads")
async def get_download_log():
    """Get the Unsplash download tracking log."""
    svc = _get_service()
    return {"downloads": svc.get_download_log()}
