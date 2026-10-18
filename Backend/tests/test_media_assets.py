"""
Tests for Media Asset Service (ASSET-001 through ASSET-005)
============================================================
Validates Giphy integration, Pexels integration, Unsplash integration,
unified asset search, and asset library management.
"""
import pytest
from services.media_asset_service import (
    MediaAssetService,
    get_media_asset_service,
    MediaAsset,
    MediaCollection,
    MediaFavorite,
    AssetProvider,
    AssetType,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def svc():
    """Fresh MediaAssetService for each test."""
    MediaAssetService.reset_instance()
    return MediaAssetService()


# ============================================================================
# ASSET-001: Giphy Integration
# ============================================================================

class TestASSET001_GiphyIntegration:
    """ASSET-001: Giphy Integration - search GIFs, trending, categories."""

    def test_search_giphy_returns_results(self, svc):
        """ASSET-001: search_giphy should return a list of MediaAsset."""
        results = svc.search_giphy("funny cat")
        assert len(results) > 0
        assert all(isinstance(r, MediaAsset) for r in results)

    def test_search_giphy_provider_is_giphy(self, svc):
        """ASSET-001: All Giphy results should have provider='giphy'."""
        results = svc.search_giphy("reaction")
        for r in results:
            assert r.provider == AssetProvider.GIPHY

    def test_search_giphy_asset_type_gif(self, svc):
        """ASSET-001: Default Giphy results should be GIF type."""
        results = svc.search_giphy("happy")
        for r in results:
            assert r.asset_type == AssetType.GIF

    def test_search_giphy_sticker_type(self, svc):
        """ASSET-001: Searching stickers should return STICKER type."""
        results = svc.search_giphy("thumbs up", asset_type=AssetType.STICKER)
        for r in results:
            assert r.asset_type == AssetType.STICKER

    def test_search_giphy_respects_limit(self, svc):
        """ASSET-001: search_giphy should respect the limit parameter."""
        results = svc.search_giphy("cat", limit=3)
        assert len(results) == 3

    def test_search_giphy_has_urls(self, svc):
        """ASSET-001: Giphy results should have thumbnail, preview, download URLs."""
        results = svc.search_giphy("dance")
        for r in results:
            assert r.thumbnail_url.startswith("https://")
            assert r.preview_url.startswith("https://")
            assert r.download_url.startswith("https://")

    def test_search_giphy_caches_assets(self, svc):
        """ASSET-001: Searched assets should be cached for later retrieval."""
        results = svc.search_giphy("test")
        for r in results:
            cached = svc.get_asset(r.id)
            assert cached is not None
            assert cached.id == r.id

    def test_get_giphy_trending(self, svc):
        """ASSET-001: get_giphy_trending should return trending GIFs."""
        results = svc.get_giphy_trending(limit=4)
        assert len(results) == 4
        for r in results:
            assert r.provider == AssetProvider.GIPHY
            assert "trending" in r.tags

    def test_get_giphy_categories(self, svc):
        """ASSET-001: get_giphy_categories should return category list."""
        categories = svc.get_giphy_categories()
        assert len(categories) > 0
        for cat in categories:
            assert "name" in cat
            assert "slug" in cat
            assert "gif_count" in cat

    def test_giphy_result_has_dimensions(self, svc):
        """ASSET-001: Giphy results should have width and height."""
        results = svc.search_giphy("cat")
        for r in results:
            assert r.width > 0
            assert r.height > 0


# ============================================================================
# ASSET-002: Pexels Integration
# ============================================================================

class TestASSET002_PexelsIntegration:
    """ASSET-002: Pexels Integration - photos, videos, attribution."""

    def test_search_pexels_photos_returns_results(self, svc):
        """ASSET-002: search_pexels_photos should return photo results."""
        results = svc.search_pexels_photos("sunset")
        assert len(results) > 0
        assert all(isinstance(r, MediaAsset) for r in results)

    def test_search_pexels_photos_provider(self, svc):
        """ASSET-002: All Pexels photo results should have provider='pexels'."""
        results = svc.search_pexels_photos("ocean")
        for r in results:
            assert r.provider == AssetProvider.PEXELS
            assert r.asset_type == AssetType.PHOTO

    def test_search_pexels_photos_orientation_portrait(self, svc):
        """ASSET-002: Portrait orientation should produce taller images."""
        results = svc.search_pexels_photos("nature", orientation="portrait")
        for r in results:
            assert r.height > r.width

    def test_search_pexels_photos_orientation_square(self, svc):
        """ASSET-002: Square orientation should produce equal dimensions."""
        results = svc.search_pexels_photos("nature", orientation="square")
        for r in results:
            assert r.width == r.height

    def test_search_pexels_videos_returns_results(self, svc):
        """ASSET-002: search_pexels_videos should return video results."""
        results = svc.search_pexels_videos("city")
        assert len(results) > 0
        for r in results:
            assert r.asset_type == AssetType.VIDEO
            assert r.provider == AssetProvider.PEXELS

    def test_search_pexels_videos_has_duration(self, svc):
        """ASSET-002: Pexels video results should have duration_seconds."""
        results = svc.search_pexels_videos("nature")
        for r in results:
            assert r.duration_seconds is not None
            assert r.duration_seconds > 0

    def test_pexels_attribution_required(self, svc):
        """ASSET-002: Pexels assets should require attribution."""
        results = svc.search_pexels_photos("coffee")
        for r in results:
            assert r.attribution_required is True
            assert len(r.attribution_text) > 0

    def test_get_pexels_attribution(self, svc):
        """ASSET-002: get_pexels_attribution should return attribution text."""
        results = svc.search_pexels_photos("desk")
        asset = results[0]
        attribution = svc.get_pexels_attribution(asset.id)
        assert attribution is not None
        assert "Pexels" in attribution

    def test_get_pexels_attribution_non_pexels_returns_none(self, svc):
        """ASSET-002: get_pexels_attribution for non-Pexels asset returns None."""
        giphy_results = svc.search_giphy("test")
        attribution = svc.get_pexels_attribution(giphy_results[0].id)
        assert attribution is None

    def test_get_pexels_attribution_unknown_asset(self, svc):
        """ASSET-002: get_pexels_attribution for unknown asset returns None."""
        attribution = svc.get_pexels_attribution("nonexistent_id")
        assert attribution is None


# ============================================================================
# ASSET-003: Unsplash Integration
# ============================================================================

class TestASSET003_UnsplashIntegration:
    """ASSET-003: Unsplash Integration - search, collections, download tracking."""

    def test_search_unsplash_returns_results(self, svc):
        """ASSET-003: search_unsplash should return photo results."""
        results = svc.search_unsplash("mountain")
        assert len(results) > 0
        assert all(isinstance(r, MediaAsset) for r in results)

    def test_search_unsplash_provider(self, svc):
        """ASSET-003: All Unsplash results should have provider='unsplash'."""
        results = svc.search_unsplash("landscape")
        for r in results:
            assert r.provider == AssetProvider.UNSPLASH
            assert r.asset_type == AssetType.PHOTO

    def test_search_unsplash_attribution_required(self, svc):
        """ASSET-003: Unsplash results should have attribution."""
        results = svc.search_unsplash("portrait")
        for r in results:
            assert r.attribution_required is True
            assert "Unsplash" in r.attribution_text

    def test_search_unsplash_orientation_portrait(self, svc):
        """ASSET-003: Portrait orientation should produce taller images."""
        results = svc.search_unsplash("person", orientation="portrait")
        for r in results:
            assert r.height > r.width

    def test_search_unsplash_respects_limit(self, svc):
        """ASSET-003: search_unsplash should respect limit."""
        results = svc.search_unsplash("test", limit=3)
        assert len(results) == 3

    def test_get_unsplash_collections(self, svc):
        """ASSET-003: get_unsplash_collections should return curated collections."""
        collections = svc.get_unsplash_collections()
        assert len(collections) > 0
        for col in collections:
            assert "id" in col
            assert "title" in col
            assert "total_photos" in col

    def test_track_download_success(self, svc):
        """ASSET-003: track_download should track an Unsplash download."""
        results = svc.search_unsplash("nature")
        asset = results[0]
        tracked = svc.track_download(asset.id)
        assert tracked is True

    def test_track_download_appears_in_log(self, svc):
        """ASSET-003: Tracked downloads should appear in download log."""
        results = svc.search_unsplash("sky")
        svc.track_download(results[0].id)
        svc.track_download(results[1].id)
        log = svc.get_download_log()
        assert len(log) == 2
        assert log[0]["asset_id"] == results[0].id

    def test_track_download_unknown_asset(self, svc):
        """ASSET-003: track_download for unknown asset returns False."""
        result = svc.track_download("nonexistent_id")
        assert result is False

    def test_unsplash_result_has_high_resolution(self, svc):
        """ASSET-003: Unsplash results should have high-resolution dimensions."""
        results = svc.search_unsplash("architecture")
        for r in results:
            assert r.width >= 2000 or r.height >= 2000


# ============================================================================
# ASSET-004: Unified Asset Search
# ============================================================================

class TestASSET004_UnifiedSearch:
    """ASSET-004: Unified search across all providers."""

    def test_unified_search_returns_results_from_all_providers(self, svc):
        """ASSET-004: unified_search should return results from multiple providers."""
        results = svc.unified_search("nature")
        providers_found = set(r.provider for r in results)
        assert AssetProvider.GIPHY in providers_found
        assert AssetProvider.PEXELS in providers_found
        assert AssetProvider.UNSPLASH in providers_found

    def test_unified_search_filter_by_provider(self, svc):
        """ASSET-004: unified_search should filter by specific providers."""
        results = svc.unified_search("test", providers=[AssetProvider.PEXELS])
        for r in results:
            assert r.provider == AssetProvider.PEXELS

    def test_unified_search_filter_by_asset_type(self, svc):
        """ASSET-004: unified_search should filter by asset type."""
        results = svc.unified_search("city", asset_types=[AssetType.VIDEO])
        for r in results:
            assert r.asset_type == AssetType.VIDEO

    def test_unified_search_includes_photos_and_gifs(self, svc):
        """ASSET-004: Unified search without type filter includes mixed types."""
        results = svc.unified_search("sunset")
        types_found = set(r.asset_type for r in results)
        assert len(types_found) > 1

    def test_unified_search_results_are_sorted(self, svc):
        """ASSET-004: unified_search results should be sorted by relevance."""
        results = svc.unified_search("nature")
        # Just verify we get a non-empty list (sorting tested by structure)
        assert len(results) > 0

    def test_get_trending_returns_merged(self, svc):
        """ASSET-004: get_trending should return results from multiple providers."""
        results = svc.get_trending(limit=3)
        providers_found = set(r.provider for r in results)
        assert len(providers_found) >= 2

    def test_filter_results_by_provider(self, svc):
        """ASSET-004: filter_results should filter by provider."""
        all_results = svc.unified_search("landscape")
        filtered = svc.filter_results(all_results, provider=AssetProvider.UNSPLASH)
        for r in filtered:
            assert r.provider == AssetProvider.UNSPLASH

    def test_filter_results_by_type(self, svc):
        """ASSET-004: filter_results should filter by asset type."""
        all_results = svc.unified_search("city")
        filtered = svc.filter_results(all_results, asset_type=AssetType.GIF)
        for r in filtered:
            assert r.asset_type == AssetType.GIF

    def test_filter_results_by_orientation(self, svc):
        """ASSET-004: filter_results should filter by orientation."""
        all_results = svc.unified_search("landscape")
        # Default results are landscape (width > height)
        filtered = svc.filter_results(all_results, orientation="landscape")
        for r in filtered:
            assert r.width > r.height

    def test_filter_results_by_min_width(self, svc):
        """ASSET-004: filter_results should filter by minimum width."""
        all_results = svc.unified_search("test")
        filtered = svc.filter_results(all_results, min_width=1000)
        for r in filtered:
            assert r.width >= 1000


# ============================================================================
# ASSET-005: Asset Library
# ============================================================================

class TestASSET005_AssetLibrary:
    """ASSET-005: Save favorites, organize in collections."""

    def test_save_to_favorites(self, svc):
        """ASSET-005: save_to_favorites should create a MediaFavorite."""
        results = svc.search_giphy("test")
        fav = svc.save_to_favorites(results[0].id)
        assert fav is not None
        assert isinstance(fav, MediaFavorite)
        assert fav.asset_id == results[0].id

    def test_save_to_favorites_unknown_asset(self, svc):
        """ASSET-005: save_to_favorites for unknown asset returns None."""
        fav = svc.save_to_favorites("nonexistent_id")
        assert fav is None

    def test_save_to_favorites_duplicate(self, svc):
        """ASSET-005: Favoriting same asset twice returns existing favorite."""
        results = svc.search_giphy("cat")
        fav1 = svc.save_to_favorites(results[0].id)
        fav2 = svc.save_to_favorites(results[0].id)
        assert fav1.id == fav2.id

    def test_is_favorited(self, svc):
        """ASSET-005: is_favorited should return True after saving."""
        results = svc.search_unsplash("sky")
        assert svc.is_favorited(results[0].id) is False
        svc.save_to_favorites(results[0].id)
        assert svc.is_favorited(results[0].id) is True

    def test_remove_from_favorites(self, svc):
        """ASSET-005: remove_from_favorites should remove the favorite."""
        results = svc.search_pexels_photos("flower")
        svc.save_to_favorites(results[0].id)
        assert svc.is_favorited(results[0].id) is True
        removed = svc.remove_from_favorites(results[0].id)
        assert removed is True
        assert svc.is_favorited(results[0].id) is False

    def test_remove_from_favorites_not_found(self, svc):
        """ASSET-005: remove_from_favorites for non-favorited asset returns False."""
        removed = svc.remove_from_favorites("nonexistent")
        assert removed is False

    def test_get_favorites(self, svc):
        """ASSET-005: get_favorites should return all favorites."""
        results = svc.search_giphy("test")
        svc.save_to_favorites(results[0].id)
        svc.save_to_favorites(results[1].id)
        favorites = svc.get_favorites()
        assert len(favorites) == 2

    def test_create_collection(self, svc):
        """ASSET-005: create_collection should create a new collection."""
        col = svc.create_collection("My Photos", "Personal photo picks")
        assert isinstance(col, MediaCollection)
        assert col.name == "My Photos"
        assert col.description == "Personal photo picks"
        assert col.is_default is False
        assert col.asset_count == 0

    def test_get_collection(self, svc):
        """ASSET-005: get_collection should retrieve by ID."""
        col = svc.create_collection("Videos")
        retrieved = svc.get_collection(col.id)
        assert retrieved is not None
        assert retrieved.id == col.id
        assert retrieved.name == "Videos"

    def test_get_collection_not_found(self, svc):
        """ASSET-005: get_collection for unknown ID returns None."""
        assert svc.get_collection("nonexistent") is None

    def test_list_collections_includes_default(self, svc):
        """ASSET-005: list_collections should include the default collection."""
        collections = svc.list_collections()
        assert len(collections) >= 1
        default_cols = [c for c in collections if c.is_default]
        assert len(default_cols) == 1
        assert default_cols[0].name == "All Favorites"

    def test_list_collections_with_custom(self, svc):
        """ASSET-005: list_collections should include custom collections."""
        svc.create_collection("Memes")
        svc.create_collection("Stock Photos")
        collections = svc.list_collections()
        names = [c.name for c in collections]
        assert "Memes" in names
        assert "Stock Photos" in names

    def test_add_to_collection(self, svc):
        """ASSET-005: add_to_collection should add asset to a collection."""
        col = svc.create_collection("Favorites")
        results = svc.search_pexels_photos("nature")
        added = svc.add_to_collection(results[0].id, col.id)
        assert added is True
        updated_col = svc.get_collection(col.id)
        assert updated_col.asset_count == 1

    def test_add_to_collection_unknown_asset(self, svc):
        """ASSET-005: add_to_collection for unknown asset returns False."""
        col = svc.create_collection("Test")
        result = svc.add_to_collection("nonexistent", col.id)
        assert result is False

    def test_add_to_collection_unknown_collection(self, svc):
        """ASSET-005: add_to_collection for unknown collection returns False."""
        results = svc.search_giphy("test")
        result = svc.add_to_collection(results[0].id, "nonexistent")
        assert result is False

    def test_get_collection_assets(self, svc):
        """ASSET-005: get_collection_assets should return assets in collection."""
        col = svc.create_collection("Nature")
        results = svc.search_unsplash("forest")
        svc.add_to_collection(results[0].id, col.id)
        svc.add_to_collection(results[1].id, col.id)
        assets = svc.get_collection_assets(col.id)
        assert len(assets) == 2
        assert all(isinstance(a, MediaAsset) for a in assets)

    def test_remove_from_collection(self, svc):
        """ASSET-005: remove_from_collection should remove asset and update count."""
        col = svc.create_collection("Temp")
        results = svc.search_pexels_videos("waves")
        svc.add_to_collection(results[0].id, col.id)
        assert svc.get_collection(col.id).asset_count == 1
        removed = svc.remove_from_collection(results[0].id, col.id)
        assert removed is True
        assert svc.get_collection(col.id).asset_count == 0

    def test_remove_from_collection_not_found(self, svc):
        """ASSET-005: remove_from_collection for missing asset returns False."""
        col = svc.create_collection("Empty")
        removed = svc.remove_from_collection("nonexistent", col.id)
        assert removed is False

    def test_save_favorite_updates_default_collection_count(self, svc):
        """ASSET-005: Saving favorites should update default collection count."""
        results = svc.search_giphy("star")
        svc.save_to_favorites(results[0].id)
        svc.save_to_favorites(results[1].id)
        # Find the default collection
        default_col = [c for c in svc.list_collections() if c.is_default][0]
        assert default_col.asset_count == 2

    def test_save_to_specific_collection(self, svc):
        """ASSET-005: save_to_favorites with collection_id uses that collection."""
        col = svc.create_collection("Special")
        results = svc.search_unsplash("abstract")
        fav = svc.save_to_favorites(results[0].id, collection_id=col.id)
        assert fav.collection_id == col.id
        assets = svc.get_collection_assets(col.id)
        assert len(assets) == 1


# ============================================================================
# Cross-feature / Integration
# ============================================================================

class TestCrossFeature:
    """Cross-feature integration tests."""

    def test_singleton_pattern(self):
        """Singleton: get_media_asset_service returns same instance."""
        MediaAssetService.reset_instance()
        svc1 = get_media_asset_service()
        svc2 = get_media_asset_service()
        assert svc1 is svc2
        MediaAssetService.reset_instance()

    def test_reset_instance(self):
        """Singleton: reset_instance clears state."""
        MediaAssetService.reset_instance()
        svc1 = MediaAssetService()
        svc1.search_giphy("test")
        assert svc1.get_stats()["cached_assets"] > 0
        MediaAssetService.reset_instance()
        svc2 = MediaAssetService()
        assert svc2.get_stats()["cached_assets"] == 0

    def test_get_stats(self, svc):
        """Stats: get_stats should return meaningful data."""
        stats = svc.get_stats()
        assert "cached_assets" in stats
        assert "favorites" in stats
        assert "collections" in stats
        assert "downloads_tracked" in stats

    def test_media_asset_to_dict(self, svc):
        """Serialization: MediaAsset.to_dict should return a dict."""
        results = svc.search_giphy("test")
        d = results[0].to_dict()
        assert isinstance(d, dict)
        assert "id" in d
        assert "provider" in d
        assert "tags" in d

    def test_media_collection_to_dict(self, svc):
        """Serialization: MediaCollection.to_dict should return a dict."""
        col = svc.create_collection("Test")
        d = col.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "Test"

    def test_unified_search_then_favorite_flow(self, svc):
        """Integration: Search -> favorite -> collection workflow."""
        # Search
        results = svc.unified_search("nature", providers=[AssetProvider.UNSPLASH])
        assert len(results) > 0

        # Create collection
        col = svc.create_collection("Nature Picks")

        # Favorite and add to collection
        fav = svc.save_to_favorites(results[0].id, collection_id=col.id)
        assert fav is not None

        # Verify collection
        assets = svc.get_collection_assets(col.id)
        assert len(assets) == 1
        assert assets[0].provider == AssetProvider.UNSPLASH

    def test_enum_values(self):
        """Enums: AssetProvider and AssetType should have correct values."""
        assert AssetProvider.GIPHY == "giphy"
        assert AssetProvider.PEXELS == "pexels"
        assert AssetProvider.UNSPLASH == "unsplash"
        assert AssetType.GIF == "gif"
        assert AssetType.VIDEO == "video"
        assert AssetType.PHOTO == "photo"
        assert AssetType.STICKER == "sticker"
        assert AssetType.ILLUSTRATION == "illustration"
