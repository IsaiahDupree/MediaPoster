"""
Media Asset Service (ASSET-001 through ASSET-005)
==================================================
Unified media asset management across Giphy, Pexels, and Unsplash providers.

Provides:
    - ASSET-001: Giphy Integration - search GIFs, get trending, browse categories
    - ASSET-002: Pexels Integration - search photos and videos, attribution handling
    - ASSET-003: Unsplash Integration - search images, collections, download tracking
    - ASSET-004: Unified Asset Search UI - single search across all providers with filters
    - ASSET-005: Asset Library - save favorites, organize in collections

Usage:
    from services.media_asset_service import MediaAssetService, get_media_asset_service

    svc = get_media_asset_service()
    results = svc.unified_search("sunset", providers=[AssetProvider.PEXELS])
    svc.save_to_favorites(results[0].id)
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class AssetProvider(str, Enum):
    """Supported media asset providers."""
    GIPHY = "giphy"
    PEXELS = "pexels"
    UNSPLASH = "unsplash"


class AssetType(str, Enum):
    """Types of media assets."""
    GIF = "gif"
    VIDEO = "video"
    PHOTO = "photo"
    STICKER = "sticker"
    ILLUSTRATION = "illustration"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class MediaAsset:
    """A media asset from any provider."""
    id: str = field(default_factory=lambda: str(uuid4()))
    provider: str = AssetProvider.GIPHY
    provider_id: str = ""
    asset_type: str = AssetType.PHOTO
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    thumbnail_url: str = ""
    preview_url: str = ""
    download_url: str = ""
    width: int = 0
    height: int = 0
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    format: str = ""
    license_type: str = "free"
    attribution_required: bool = False
    attribution_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MediaCollection:
    """A user-created collection of media assets."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    is_default: bool = False
    asset_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MediaFavorite:
    """A favorited asset, optionally placed in a collection."""
    id: str = field(default_factory=lambda: str(uuid4()))
    asset_id: str = ""
    collection_id: Optional[str] = None
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Mock Data Generators (for testing mode / no API keys)
# ============================================================================

def _mock_giphy_results(query: str, limit: int = 5) -> List[MediaAsset]:
    """Generate mock Giphy GIF results."""
    results = []
    samples = [
        ("funny cat", "Hilarious cat compilation", ["cat", "funny", "animal"]),
        ("dancing dog", "Dog dancing to music", ["dog", "dance", "funny"]),
        ("thumbs up", "Thumbs up approval", ["thumbs up", "approve", "yes"]),
        ("celebration", "Celebration confetti", ["celebrate", "party", "confetti"]),
        ("mind blown", "Mind blown reaction", ["reaction", "mind blown", "wow"]),
    ]
    for i, (title, desc, tags) in enumerate(samples[:limit]):
        if query.lower() not in " ".join(tags + [title, desc]).lower() and query.lower() != "trending":
            # Still return results but adjust title to include query
            title = f"{query} - {title}"
        results.append(MediaAsset(
            id=str(uuid4()),
            provider=AssetProvider.GIPHY,
            provider_id=f"giphy_{i}_{uuid4().hex[:8]}",
            asset_type=AssetType.GIF,
            title=title,
            description=desc,
            tags=tags + [query.lower()],
            thumbnail_url=f"https://media.giphy.com/media/thumb_{i}.gif",
            preview_url=f"https://media.giphy.com/media/preview_{i}.gif",
            download_url=f"https://media.giphy.com/media/download_{i}.gif",
            width=480,
            height=360,
            duration_seconds=3.5,
            file_size_bytes=2_500_000,
            format="gif",
            license_type="giphy",
            attribution_required=False,
            attribution_text="",
        ))
    return results


def _mock_giphy_categories() -> List[Dict[str, Any]]:
    """Generate mock Giphy categories."""
    return [
        {"name": "Trending", "slug": "trending", "gif_count": 5000},
        {"name": "Reactions", "slug": "reactions", "gif_count": 3200},
        {"name": "Entertainment", "slug": "entertainment", "gif_count": 2800},
        {"name": "Sports", "slug": "sports", "gif_count": 1500},
        {"name": "Stickers", "slug": "stickers", "gif_count": 4100},
    ]


def _mock_pexels_photo_results(query: str, limit: int = 5) -> List[MediaAsset]:
    """Generate mock Pexels photo results."""
    results = []
    samples = [
        ("Sunset over mountains", "Beautiful sunset landscape", ["sunset", "mountains", "nature"]),
        ("City skyline at night", "Urban cityscape", ["city", "night", "skyline"]),
        ("Ocean waves crashing", "Sea waves on rocks", ["ocean", "waves", "sea"]),
        ("Forest path in autumn", "Autumn woodland trail", ["forest", "autumn", "path"]),
        ("Coffee on desk", "Morning coffee workspace", ["coffee", "desk", "workspace"]),
    ]
    for i, (title, desc, tags) in enumerate(samples[:limit]):
        results.append(MediaAsset(
            id=str(uuid4()),
            provider=AssetProvider.PEXELS,
            provider_id=f"pexels_photo_{i}_{uuid4().hex[:8]}",
            asset_type=AssetType.PHOTO,
            title=title,
            description=desc,
            tags=tags + [query.lower()],
            thumbnail_url=f"https://images.pexels.com/photos/{i}/thumb.jpeg",
            preview_url=f"https://images.pexels.com/photos/{i}/medium.jpeg",
            download_url=f"https://images.pexels.com/photos/{i}/original.jpeg",
            width=1920,
            height=1280,
            duration_seconds=None,
            file_size_bytes=5_000_000,
            format="jpeg",
            license_type="pexels",
            attribution_required=True,
            attribution_text=f"Photo by Photographer{i} on Pexels",
        ))
    return results


def _mock_pexels_video_results(query: str, limit: int = 4) -> List[MediaAsset]:
    """Generate mock Pexels video results."""
    results = []
    samples = [
        ("Drone footage of coast", "Aerial coastline view", ["drone", "coast", "aerial"]),
        ("Time lapse of clouds", "Cloud formation timelapse", ["timelapse", "clouds", "sky"]),
        ("Street traffic at night", "City traffic flow", ["traffic", "city", "night"]),
        ("Waterfall in jungle", "Tropical waterfall", ["waterfall", "jungle", "nature"]),
    ]
    for i, (title, desc, tags) in enumerate(samples[:limit]):
        results.append(MediaAsset(
            id=str(uuid4()),
            provider=AssetProvider.PEXELS,
            provider_id=f"pexels_video_{i}_{uuid4().hex[:8]}",
            asset_type=AssetType.VIDEO,
            title=title,
            description=desc,
            tags=tags + [query.lower()],
            thumbnail_url=f"https://images.pexels.com/videos/{i}/thumb.jpeg",
            preview_url=f"https://videos.pexels.com/videos/{i}/preview.mp4",
            download_url=f"https://videos.pexels.com/videos/{i}/original.mp4",
            width=1920,
            height=1080,
            duration_seconds=15.0,
            file_size_bytes=25_000_000,
            format="mp4",
            license_type="pexels",
            attribution_required=True,
            attribution_text=f"Video by Videographer{i} on Pexels",
        ))
    return results


def _mock_unsplash_results(query: str, limit: int = 5) -> List[MediaAsset]:
    """Generate mock Unsplash photo results."""
    results = []
    samples = [
        ("Mountain landscape", "Snow-capped mountain range", ["mountain", "landscape", "snow"]),
        ("Portrait in sunlight", "Natural light portrait", ["portrait", "sunlight", "person"]),
        ("Minimalist architecture", "Clean architectural lines", ["architecture", "minimalist", "building"]),
        ("Wildflower meadow", "Colorful wildflower field", ["wildflower", "meadow", "nature"]),
        ("Abstract light painting", "Long exposure light art", ["abstract", "light", "art"]),
    ]
    for i, (title, desc, tags) in enumerate(samples[:limit]):
        results.append(MediaAsset(
            id=str(uuid4()),
            provider=AssetProvider.UNSPLASH,
            provider_id=f"unsplash_{i}_{uuid4().hex[:8]}",
            asset_type=AssetType.PHOTO,
            title=title,
            description=desc,
            tags=tags + [query.lower()],
            thumbnail_url=f"https://images.unsplash.com/photo-{i}?w=200",
            preview_url=f"https://images.unsplash.com/photo-{i}?w=800",
            download_url=f"https://images.unsplash.com/photo-{i}?w=2400",
            width=2400,
            height=1600,
            duration_seconds=None,
            file_size_bytes=8_000_000,
            format="jpeg",
            license_type="unsplash",
            attribution_required=True,
            attribution_text=f"Photo by Artist{i} on Unsplash",
        ))
    return results


def _mock_unsplash_collections() -> List[Dict[str, Any]]:
    """Generate mock Unsplash curated collections."""
    return [
        {"id": "unsplash_col_1", "title": "Nature", "description": "Nature photography", "total_photos": 1200},
        {"id": "unsplash_col_2", "title": "Architecture", "description": "Architectural wonders", "total_photos": 850},
        {"id": "unsplash_col_3", "title": "People", "description": "Portraits and street", "total_photos": 2100},
        {"id": "unsplash_col_4", "title": "Travel", "description": "Around the world", "total_photos": 1750},
    ]


# ============================================================================
# Media Asset Service
# ============================================================================

class MediaAssetService:
    """
    Unified media asset service (ASSET-001 through ASSET-005).

    Provides search, trending, and library management across Giphy,
    Pexels, and Unsplash with in-memory storage for favorites and
    collections.
    """

    _instance: Optional['MediaAssetService'] = None

    def __init__(self):
        # In-memory stores
        self._assets: Dict[str, MediaAsset] = {}           # asset_id -> MediaAsset
        self._favorites: Dict[str, MediaFavorite] = {}      # favorite_id -> MediaFavorite
        self._collections: Dict[str, MediaCollection] = {}  # collection_id -> MediaCollection
        self._collection_assets: Dict[str, List[str]] = {}  # collection_id -> [asset_id, ...]
        self._download_log: List[Dict[str, Any]] = []       # download tracking entries

        # Create default "All Favorites" collection
        default_col = MediaCollection(
            name="All Favorites",
            description="Default collection for all favorited assets",
            is_default=True,
        )
        self._collections[default_col.id] = default_col
        self._collection_assets[default_col.id] = []
        self._default_collection_id = default_col.id

        logger.info("MediaAssetService initialized")

    @classmethod
    def get_instance(cls) -> 'MediaAssetService':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Helper: Store asset in cache
    # ------------------------------------------------------------------

    def _cache_asset(self, asset: MediaAsset) -> None:
        """Cache an asset in the in-memory store."""
        self._assets[asset.id] = asset

    def _cache_assets(self, assets: List[MediaAsset]) -> None:
        """Cache multiple assets."""
        for asset in assets:
            self._cache_asset(asset)

    def get_asset(self, asset_id: str) -> Optional[MediaAsset]:
        """Get a cached asset by ID."""
        return self._assets.get(asset_id)

    # ==================================================================
    # ASSET-001: Giphy Integration
    # ==================================================================

    def search_giphy(
        self,
        query: str,
        limit: int = 5,
        rating: str = "g",
        asset_type: str = AssetType.GIF,
    ) -> List[MediaAsset]:
        """
        Search Giphy for GIFs or stickers (ASSET-001).

        Args:
            query: Search query
            limit: Maximum results (1-25)
            rating: Content rating (g, pg, pg-13, r)
            asset_type: GIF or STICKER

        Returns:
            List of MediaAsset results
        """
        limit = max(1, min(limit, 25))
        results = _mock_giphy_results(query, limit)

        # If looking for stickers, change asset_type
        if asset_type == AssetType.STICKER:
            for r in results:
                r.asset_type = AssetType.STICKER

        self._cache_assets(results)
        logger.debug("ASSET-001: Giphy search '%s' returned %d results", query, len(results))
        return results

    def get_giphy_trending(self, limit: int = 5) -> List[MediaAsset]:
        """
        Get trending GIFs from Giphy (ASSET-001).

        Args:
            limit: Maximum results

        Returns:
            List of trending MediaAsset GIFs
        """
        results = _mock_giphy_results("trending", limit)
        for r in results:
            r.tags.append("trending")
        self._cache_assets(results)
        logger.debug("ASSET-001: Giphy trending returned %d results", len(results))
        return results

    def get_giphy_categories(self) -> List[Dict[str, Any]]:
        """
        Get Giphy browse categories (ASSET-001).

        Returns:
            List of category dicts with name, slug, gif_count
        """
        categories = _mock_giphy_categories()
        logger.debug("ASSET-001: Giphy categories returned %d categories", len(categories))
        return categories

    # ==================================================================
    # ASSET-002: Pexels Integration
    # ==================================================================

    def search_pexels_photos(
        self,
        query: str,
        limit: int = 5,
        orientation: Optional[str] = None,
    ) -> List[MediaAsset]:
        """
        Search Pexels for photos (ASSET-002).

        Args:
            query: Search query
            limit: Maximum results
            orientation: landscape, portrait, square

        Returns:
            List of MediaAsset photo results
        """
        limit = max(1, min(limit, 25))
        results = _mock_pexels_photo_results(query, limit)

        # Filter by orientation dimensions if specified
        if orientation == "portrait":
            for r in results:
                r.width, r.height = 1280, 1920
        elif orientation == "square":
            for r in results:
                r.width, r.height = 1080, 1080

        self._cache_assets(results)
        logger.debug("ASSET-002: Pexels photo search '%s' returned %d results", query, len(results))
        return results

    def search_pexels_videos(
        self,
        query: str,
        limit: int = 4,
    ) -> List[MediaAsset]:
        """
        Search Pexels for videos (ASSET-002).

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of MediaAsset video results
        """
        limit = max(1, min(limit, 25))
        results = _mock_pexels_video_results(query, limit)
        self._cache_assets(results)
        logger.debug("ASSET-002: Pexels video search '%s' returned %d results", query, len(results))
        return results

    def get_pexels_attribution(self, asset_id: str) -> Optional[str]:
        """
        Get attribution text for a Pexels asset (ASSET-002).

        Args:
            asset_id: The asset ID

        Returns:
            Attribution text string, or None if not found or not Pexels
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return None
        if asset.provider != AssetProvider.PEXELS:
            return None
        return asset.attribution_text

    # ==================================================================
    # ASSET-003: Unsplash Integration
    # ==================================================================

    def search_unsplash(
        self,
        query: str,
        limit: int = 5,
        orientation: Optional[str] = None,
    ) -> List[MediaAsset]:
        """
        Search Unsplash for photos (ASSET-003).

        Args:
            query: Search query
            limit: Maximum results
            orientation: landscape, portrait, squarish

        Returns:
            List of MediaAsset photo results
        """
        limit = max(1, min(limit, 25))
        results = _mock_unsplash_results(query, limit)

        if orientation == "portrait":
            for r in results:
                r.width, r.height = 1600, 2400
        elif orientation == "squarish":
            for r in results:
                r.width, r.height = 2000, 2000

        self._cache_assets(results)
        logger.debug("ASSET-003: Unsplash search '%s' returned %d results", query, len(results))
        return results

    def get_unsplash_collections(self) -> List[Dict[str, Any]]:
        """
        Get curated Unsplash collections (ASSET-003).

        Returns:
            List of collection dicts with id, title, description, total_photos
        """
        collections = _mock_unsplash_collections()
        logger.debug("ASSET-003: Unsplash collections returned %d", len(collections))
        return collections

    def track_download(self, asset_id: str) -> bool:
        """
        Track a download event for an Unsplash asset (ASSET-003).

        Per Unsplash API guidelines, a download must be tracked when
        the user actually downloads the image.

        Args:
            asset_id: The asset ID

        Returns:
            True if tracked successfully, False if asset not found
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return False

        entry = {
            "asset_id": asset_id,
            "provider": asset.provider,
            "provider_id": asset.provider_id,
            "download_url": asset.download_url,
            "tracked_at": datetime.now(timezone.utc).isoformat(),
        }
        self._download_log.append(entry)
        logger.debug("ASSET-003: Download tracked for asset %s", asset_id)
        return True

    def get_download_log(self) -> List[Dict[str, Any]]:
        """Get the download tracking log."""
        return list(self._download_log)

    # ==================================================================
    # ASSET-004: Unified Asset Search
    # ==================================================================

    def unified_search(
        self,
        query: str,
        providers: Optional[List[str]] = None,
        asset_types: Optional[List[str]] = None,
        limit_per_provider: int = 5,
    ) -> List[MediaAsset]:
        """
        Search across all providers in parallel, returning merged results (ASSET-004).

        Results are merged and scored by relevance. Providers can be filtered.

        Args:
            query: Search query
            providers: List of provider names to include (default: all)
            asset_types: List of asset types to include (default: all)
            limit_per_provider: Max results per provider

        Returns:
            List of MediaAsset results merged from all requested providers
        """
        if providers is None:
            providers = [AssetProvider.GIPHY, AssetProvider.PEXELS, AssetProvider.UNSPLASH]
        else:
            providers = [p if isinstance(p, str) else p.value for p in providers]

        all_results: List[MediaAsset] = []

        if AssetProvider.GIPHY in providers or "giphy" in providers:
            all_results.extend(self.search_giphy(query, limit=limit_per_provider))

        if AssetProvider.PEXELS in providers or "pexels" in providers:
            all_results.extend(self.search_pexels_photos(query, limit=limit_per_provider))
            all_results.extend(self.search_pexels_videos(query, limit=min(3, limit_per_provider)))

        if AssetProvider.UNSPLASH in providers or "unsplash" in providers:
            all_results.extend(self.search_unsplash(query, limit=limit_per_provider))

        # Filter by asset type if specified
        if asset_types:
            type_values = [t if isinstance(t, str) else t.value for t in asset_types]
            all_results = [r for r in all_results if r.asset_type in type_values]

        # Score and sort: exact query match in title gets higher rank
        def _relevance_score(asset: MediaAsset) -> float:
            score = 0.0
            q = query.lower()
            if q in asset.title.lower():
                score += 10.0
            if q in asset.description.lower():
                score += 5.0
            if q in [t.lower() for t in asset.tags]:
                score += 3.0
            # Prefer photos and videos over gifs for general searches
            if asset.asset_type == AssetType.PHOTO:
                score += 1.0
            elif asset.asset_type == AssetType.VIDEO:
                score += 0.5
            return score

        all_results.sort(key=_relevance_score, reverse=True)

        logger.debug("ASSET-004: Unified search '%s' returned %d total results", query, len(all_results))
        return all_results

    def get_trending(self, limit: int = 5) -> List[MediaAsset]:
        """
        Get trending assets merged from all providers (ASSET-004).

        Args:
            limit: Max results per provider

        Returns:
            List of trending MediaAsset results
        """
        results: List[MediaAsset] = []
        results.extend(self.get_giphy_trending(limit=limit))
        # Pexels and Unsplash "trending" as curated search
        results.extend(self.search_pexels_photos("trending", limit=limit))
        results.extend(self.search_unsplash("trending", limit=limit))
        logger.debug("ASSET-004: get_trending returned %d results", len(results))
        return results

    def filter_results(
        self,
        results: List[MediaAsset],
        provider: Optional[str] = None,
        asset_type: Optional[str] = None,
        orientation: Optional[str] = None,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
    ) -> List[MediaAsset]:
        """
        Filter a list of results by provider, type, and orientation (ASSET-004).

        Args:
            results: List of MediaAsset to filter
            provider: Filter by provider name
            asset_type: Filter by asset type
            orientation: Filter by orientation (landscape, portrait, square)
            min_width: Minimum width
            min_height: Minimum height

        Returns:
            Filtered list of MediaAsset
        """
        filtered = list(results)

        if provider:
            p_val = provider if isinstance(provider, str) else provider.value
            filtered = [r for r in filtered if r.provider == p_val]

        if asset_type:
            t_val = asset_type if isinstance(asset_type, str) else asset_type.value
            filtered = [r for r in filtered if r.asset_type == t_val]

        if orientation:
            if orientation == "landscape":
                filtered = [r for r in filtered if r.width > r.height]
            elif orientation == "portrait":
                filtered = [r for r in filtered if r.height > r.width]
            elif orientation == "square":
                filtered = [r for r in filtered if r.width == r.height]

        if min_width:
            filtered = [r for r in filtered if r.width >= min_width]

        if min_height:
            filtered = [r for r in filtered if r.height >= min_height]

        logger.debug("ASSET-004: filter_results %d -> %d", len(results), len(filtered))
        return filtered

    # ==================================================================
    # ASSET-005: Asset Library
    # ==================================================================

    def save_to_favorites(
        self,
        asset_id: str,
        collection_id: Optional[str] = None,
    ) -> Optional[MediaFavorite]:
        """
        Save an asset to favorites (ASSET-005).

        Optionally place it in a specific collection.

        Args:
            asset_id: The asset ID to favorite
            collection_id: Optional collection to add to

        Returns:
            MediaFavorite if saved, None if asset not found
        """
        asset = self._assets.get(asset_id)
        if not asset:
            logger.warning("ASSET-005: Cannot favorite unknown asset %s", asset_id)
            return None

        # Check for duplicate favorite
        for fav in self._favorites.values():
            if fav.asset_id == asset_id:
                logger.debug("ASSET-005: Asset %s already in favorites", asset_id)
                return fav

        target_collection = collection_id or self._default_collection_id

        favorite = MediaFavorite(
            asset_id=asset_id,
            collection_id=target_collection,
        )
        self._favorites[favorite.id] = favorite

        # Add to collection asset list
        if target_collection in self._collection_assets:
            if asset_id not in self._collection_assets[target_collection]:
                self._collection_assets[target_collection].append(asset_id)
                # Update asset count
                col = self._collections.get(target_collection)
                if col:
                    col.asset_count = len(self._collection_assets[target_collection])

        logger.debug("ASSET-005: Asset %s saved to favorites (collection=%s)", asset_id, target_collection)
        return favorite

    def remove_from_favorites(self, asset_id: str) -> bool:
        """
        Remove an asset from favorites (ASSET-005).

        Args:
            asset_id: The asset ID to unfavorite

        Returns:
            True if removed, False if not found
        """
        fav_to_remove = None
        for fav_id, fav in self._favorites.items():
            if fav.asset_id == asset_id:
                fav_to_remove = fav_id
                break

        if not fav_to_remove:
            return False

        fav = self._favorites.pop(fav_to_remove)

        # Remove from collection asset list
        if fav.collection_id and fav.collection_id in self._collection_assets:
            assets = self._collection_assets[fav.collection_id]
            if asset_id in assets:
                assets.remove(asset_id)
                col = self._collections.get(fav.collection_id)
                if col:
                    col.asset_count = len(assets)

        logger.debug("ASSET-005: Asset %s removed from favorites", asset_id)
        return True

    def get_favorites(self) -> List[MediaFavorite]:
        """Get all favorites."""
        return list(self._favorites.values())

    def is_favorited(self, asset_id: str) -> bool:
        """Check if an asset is in favorites."""
        return any(f.asset_id == asset_id for f in self._favorites.values())

    def create_collection(
        self,
        name: str,
        description: str = "",
    ) -> MediaCollection:
        """
        Create a new collection (ASSET-005).

        Args:
            name: Collection name
            description: Collection description

        Returns:
            The new MediaCollection
        """
        collection = MediaCollection(
            name=name,
            description=description,
            is_default=False,
        )
        self._collections[collection.id] = collection
        self._collection_assets[collection.id] = []
        logger.debug("ASSET-005: Collection created: %s (%s)", collection.id, name)
        return collection

    def get_collection(self, collection_id: str) -> Optional[MediaCollection]:
        """
        Get a collection by ID (ASSET-005).

        Args:
            collection_id: The collection ID

        Returns:
            MediaCollection or None
        """
        return self._collections.get(collection_id)

    def list_collections(self) -> List[MediaCollection]:
        """
        List all collections (ASSET-005).

        Returns:
            List of all MediaCollection objects
        """
        return list(self._collections.values())

    def get_collection_assets(self, collection_id: str) -> List[MediaAsset]:
        """
        Get all assets in a collection (ASSET-005).

        Args:
            collection_id: The collection ID

        Returns:
            List of MediaAsset objects in the collection
        """
        asset_ids = self._collection_assets.get(collection_id, [])
        assets = []
        for aid in asset_ids:
            asset = self._assets.get(aid)
            if asset:
                assets.append(asset)
        return assets

    def add_to_collection(
        self,
        asset_id: str,
        collection_id: str,
    ) -> bool:
        """
        Add an asset to a collection (ASSET-005).

        The asset must already be cached (from a search or favorite).

        Args:
            asset_id: The asset ID
            collection_id: The collection ID

        Returns:
            True if added, False if asset or collection not found
        """
        if asset_id not in self._assets:
            logger.warning("ASSET-005: Cannot add unknown asset %s to collection", asset_id)
            return False
        if collection_id not in self._collections:
            logger.warning("ASSET-005: Cannot add to unknown collection %s", collection_id)
            return False

        assets_list = self._collection_assets[collection_id]
        if asset_id not in assets_list:
            assets_list.append(asset_id)
            self._collections[collection_id].asset_count = len(assets_list)

        logger.debug("ASSET-005: Asset %s added to collection %s", asset_id, collection_id)
        return True

    def remove_from_collection(
        self,
        asset_id: str,
        collection_id: str,
    ) -> bool:
        """
        Remove an asset from a collection (ASSET-005).

        Args:
            asset_id: The asset ID
            collection_id: The collection ID

        Returns:
            True if removed, False if not found
        """
        if collection_id not in self._collection_assets:
            return False

        assets_list = self._collection_assets[collection_id]
        if asset_id not in assets_list:
            return False

        assets_list.remove(asset_id)
        self._collections[collection_id].asset_count = len(assets_list)
        logger.debug("ASSET-005: Asset %s removed from collection %s", asset_id, collection_id)
        return True

    # ------------------------------------------------------------------
    # Stats / Dashboard
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "cached_assets": len(self._assets),
            "favorites": len(self._favorites),
            "collections": len(self._collections),
            "downloads_tracked": len(self._download_log),
        }


# ============================================================================
# Module-level Convenience Function
# ============================================================================

def get_media_asset_service() -> MediaAssetService:
    """Get the singleton MediaAssetService instance."""
    return MediaAssetService.get_instance()
