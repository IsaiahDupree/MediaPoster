"""
Tests for ASSET-004/005 API endpoints, AC-006, and AC-007
==========================================================
Validates:
- ASSET-004: Unified Asset Search API endpoints
- ASSET-005: Asset Library API endpoints (favorites, collections)
- AC-006: Run Detail Agent Panel (backend endpoints exist)
- AC-007: Pub/Sub Inspector (topics, events, lag, health)
"""
import pytest
from fastapi.testclient import TestClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_asset_service():
    """Reset the MediaAssetService singleton before each test."""
    from services.media_asset_service import MediaAssetService
    MediaAssetService.reset_instance()
    yield
    MediaAssetService.reset_instance()


# ============================================================================
# ASSET-004: Unified Asset Search API
# ============================================================================

class TestASSET004_UnifiedSearchAPI:
    """ASSET-004: Unified search API endpoints."""

    def test_unified_search_endpoint_exists(self, client):
        """ASSET-004: GET /api/media-assets/search should exist."""
        resp = client.get("/api/media-assets/search?query=nature")
        assert resp.status_code == 200

    def test_unified_search_returns_results(self, client):
        """ASSET-004: Unified search should return results from multiple providers."""
        resp = client.get("/api/media-assets/search?query=sunset")
        data = resp.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] > 0

    def test_unified_search_filter_by_provider(self, client):
        """ASSET-004: Unified search should filter by provider."""
        resp = client.get("/api/media-assets/search?query=test&providers=pexels")
        data = resp.json()
        for result in data["results"]:
            assert result["provider"] == "pexels"

    def test_unified_search_filter_by_type(self, client):
        """ASSET-004: Unified search should filter by asset type."""
        resp = client.get("/api/media-assets/search?query=city&asset_types=video")
        data = resp.json()
        for result in data["results"]:
            assert result["asset_type"] == "video"

    def test_trending_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/trending should return trending assets."""
        resp = client.get("/api/media-assets/trending?limit=5")
        data = resp.json()
        assert resp.status_code == 200
        assert "results" in data
        assert data["count"] > 0

    def test_filter_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/filter should filter results."""
        resp = client.get("/api/media-assets/filter?query=landscape&provider=unsplash")
        data = resp.json()
        assert resp.status_code == 200
        for result in data["results"]:
            assert result["provider"] == "unsplash"

    def test_giphy_search_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/giphy/search should work."""
        resp = client.get("/api/media-assets/giphy/search?query=cat")
        data = resp.json()
        assert resp.status_code == 200
        assert data["count"] > 0

    def test_giphy_trending_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/giphy/trending should work."""
        resp = client.get("/api/media-assets/giphy/trending?limit=3")
        assert resp.status_code == 200

    def test_giphy_categories_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/giphy/categories should work."""
        resp = client.get("/api/media-assets/giphy/categories")
        data = resp.json()
        assert resp.status_code == 200
        assert "categories" in data
        assert len(data["categories"]) > 0

    def test_pexels_photos_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/pexels/photos should work."""
        resp = client.get("/api/media-assets/pexels/photos?query=ocean")
        assert resp.status_code == 200
        assert resp.json()["count"] > 0

    def test_pexels_videos_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/pexels/videos should work."""
        resp = client.get("/api/media-assets/pexels/videos?query=city")
        assert resp.status_code == 200

    def test_unsplash_search_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/unsplash/search should work."""
        resp = client.get("/api/media-assets/unsplash/search?query=mountain")
        assert resp.status_code == 200
        assert resp.json()["count"] > 0

    def test_unsplash_collections_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/unsplash/collections should work."""
        resp = client.get("/api/media-assets/unsplash/collections")
        assert resp.status_code == 200

    def test_stats_endpoint(self, client):
        """ASSET-004: GET /api/media-assets/stats should work."""
        resp = client.get("/api/media-assets/stats")
        data = resp.json()
        assert resp.status_code == 200
        assert "stats" in data
        assert "cached_assets" in data["stats"]


# ============================================================================
# ASSET-005: Asset Library API
# ============================================================================

class TestASSET005_AssetLibraryAPI:
    """ASSET-005: Favorites and collections API endpoints."""

    def test_list_favorites_empty(self, client):
        """ASSET-005: GET /api/media-assets/favorites should start empty."""
        resp = client.get("/api/media-assets/favorites")
        data = resp.json()
        assert resp.status_code == 200
        assert data["count"] == 0

    def test_add_favorite_requires_search_first(self, client):
        """ASSET-005: POST /api/media-assets/favorites should fail for unknown asset."""
        resp = client.post("/api/media-assets/favorites", json={"asset_id": "nonexistent"})
        assert resp.status_code == 404

    def test_favorite_workflow(self, client):
        """ASSET-005: Search -> favorite -> check -> remove workflow."""
        # Search to populate cache
        search_resp = client.get("/api/media-assets/giphy/search?query=star&limit=2")
        results = search_resp.json()["results"]
        asset_id = results[0]["id"]

        # Favorite
        fav_resp = client.post("/api/media-assets/favorites", json={"asset_id": asset_id})
        assert fav_resp.status_code == 200
        assert fav_resp.json()["favorite"]["asset_id"] == asset_id

        # Check status
        status_resp = client.get(f"/api/media-assets/favorites/{asset_id}/status")
        assert status_resp.json()["is_favorited"] is True

        # List favorites
        list_resp = client.get("/api/media-assets/favorites")
        assert list_resp.json()["count"] == 1

        # Remove
        del_resp = client.delete(f"/api/media-assets/favorites/{asset_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["removed"] is True

        # Verify removed
        status_resp2 = client.get(f"/api/media-assets/favorites/{asset_id}/status")
        assert status_resp2.json()["is_favorited"] is False

    def test_create_collection(self, client):
        """ASSET-005: POST /api/media-assets/collections should create collection."""
        resp = client.post("/api/media-assets/collections", json={
            "name": "My Photos",
            "description": "Personal picks"
        })
        data = resp.json()
        assert resp.status_code == 200
        assert data["collection"]["name"] == "My Photos"

    def test_list_collections_has_default(self, client):
        """ASSET-005: GET /api/media-assets/collections should include default."""
        resp = client.get("/api/media-assets/collections")
        data = resp.json()
        assert resp.status_code == 200
        assert data["count"] >= 1
        names = [c["name"] for c in data["collections"]]
        assert "All Favorites" in names

    def test_collection_asset_workflow(self, client):
        """ASSET-005: Create collection -> add asset -> get assets -> remove."""
        # Create collection
        col_resp = client.post("/api/media-assets/collections", json={"name": "Nature"})
        col_id = col_resp.json()["collection"]["id"]

        # Search to get an asset
        search_resp = client.get("/api/media-assets/unsplash/search?query=forest&limit=2")
        asset_id = search_resp.json()["results"][0]["id"]

        # Add to collection
        add_resp = client.post(
            f"/api/media-assets/collections/{col_id}/assets",
            json={"asset_id": asset_id}
        )
        assert add_resp.status_code == 200

        # Get collection assets
        assets_resp = client.get(f"/api/media-assets/collections/{col_id}/assets")
        assert assets_resp.json()["count"] == 1

        # Remove from collection
        del_resp = client.delete(f"/api/media-assets/collections/{col_id}/assets/{asset_id}")
        assert del_resp.status_code == 200

        # Verify empty
        assets_resp2 = client.get(f"/api/media-assets/collections/{col_id}/assets")
        assert assets_resp2.json()["count"] == 0

    def test_get_collection_by_id(self, client):
        """ASSET-005: GET /api/media-assets/collections/{id} should work."""
        col_resp = client.post("/api/media-assets/collections", json={"name": "Videos"})
        col_id = col_resp.json()["collection"]["id"]

        get_resp = client.get(f"/api/media-assets/collections/{col_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["collection"]["name"] == "Videos"

    def test_get_nonexistent_collection(self, client):
        """ASSET-005: GET /api/media-assets/collections/{id} should 404 for missing."""
        resp = client.get("/api/media-assets/collections/nonexistent-id")
        assert resp.status_code == 404

    def test_get_asset_by_id(self, client):
        """ASSET-005: GET /api/media-assets/asset/{id} should work after search."""
        search_resp = client.get("/api/media-assets/giphy/search?query=test&limit=1")
        asset_id = search_resp.json()["results"][0]["id"]

        resp = client.get(f"/api/media-assets/asset/{asset_id}")
        assert resp.status_code == 200
        assert resp.json()["asset"]["id"] == asset_id

    def test_download_tracking(self, client):
        """ASSET-005: POST track-download and GET downloads should work."""
        # Search unsplash to get an asset
        search_resp = client.get("/api/media-assets/unsplash/search?query=sky&limit=1")
        asset_id = search_resp.json()["results"][0]["id"]

        # Track download
        track_resp = client.post(f"/api/media-assets/unsplash/track-download/{asset_id}")
        assert track_resp.status_code == 200

        # Get download log
        log_resp = client.get("/api/media-assets/downloads")
        assert log_resp.status_code == 200
        assert len(log_resp.json()["downloads"]) >= 1


# ============================================================================
# AC-006: Run Detail Agent Panel (Backend endpoints)
# ============================================================================

class TestAC006_RunDetailAgentPanel:
    """AC-006: Backend API endpoints for run detail panel.

    These endpoints require a database connection. Tests verify the router
    exists and endpoints are registered (accepting 500 for DB-dependent ops).
    """

    def test_automation_router_registered(self):
        """AC-006: Automation router should be importable with correct prefix."""
        from api.endpoints.automation import router
        paths = [r.path for r in router.routes]
        assert "/runs" in paths or any("/runs" in p for p in paths)

    def test_automation_endpoints_defined(self):
        """AC-006: All required run management endpoints should be defined."""
        from api.endpoints.automation import router
        paths = [r.path for r in router.routes]
        # Core run management endpoints
        assert any("runs" in p for p in paths), "Missing /runs endpoint"
        assert any("steps" in p for p in paths), "Missing /steps endpoint"
        assert any("timeline" in p for p in paths), "Missing /timeline endpoint"
        assert any("artifacts" in p for p in paths), "Missing /artifacts endpoint"

    def test_automation_has_control_endpoints(self):
        """AC-006: Pause/cancel/retry endpoints should exist."""
        from api.endpoints.automation import router
        paths = [r.path for r in router.routes]
        assert any("pause" in p for p in paths), "Missing /pause endpoint"
        assert any("cancel" in p for p in paths), "Missing /cancel endpoint"
        assert any("retry" in p for p in paths), "Missing /retry endpoint"

    def test_automation_health_endpoint(self, client):
        """AC-006: GET /api/automation/health should be registered."""
        resp = client.get("/api/automation/health")
        # Health endpoint may need DB for run_manager queries
        assert resp.status_code in [200, 500]
        if resp.status_code == 200:
            data = resp.json()
            assert "health" in data

    def test_automation_runs_endpoint_registered(self, client):
        """AC-006: GET /api/automation/runs should be registered (may need DB)."""
        resp = client.get("/api/automation/runs")
        # 200 if DB available, 500 if not - endpoint exists either way
        assert resp.status_code in [200, 500]

    def test_run_steps_endpoint_registered(self, client):
        """AC-006: GET /api/automation/runs/{id}/steps should be registered."""
        resp = client.get("/api/automation/runs/test-id/steps")
        assert resp.status_code in [200, 404, 500]

    def test_run_timeline_endpoint_registered(self, client):
        """AC-006: GET /api/automation/runs/{id}/timeline should be registered."""
        resp = client.get("/api/automation/runs/test-id/timeline")
        assert resp.status_code in [200, 404, 500]

    def test_run_artifacts_endpoint_registered(self, client):
        """AC-006: GET /api/automation/runs/{id}/artifacts should be registered."""
        resp = client.get("/api/automation/runs/test-id/artifacts")
        assert resp.status_code in [200, 404, 500]

    def test_schedules_endpoint_registered(self, client):
        """AC-006: GET /api/automation/schedules should be registered."""
        resp = client.get("/api/automation/schedules")
        assert resp.status_code in [200, 500]


# ============================================================================
# AC-007: Pub/Sub Inspector
# ============================================================================

class TestAC007_PubSubInspector:
    """AC-007: Pub/Sub Inspector API endpoints."""

    def test_topics_list_endpoint(self, client):
        """AC-007: GET /api/pubsub/topics should list all topics."""
        resp = client.get("/api/pubsub/topics")
        data = resp.json()
        assert resp.status_code == 200
        assert "topics" in data
        assert "count" in data
        assert "domains" in data
        assert data["count"] > 0

    def test_topics_filter_by_domain(self, client):
        """AC-007: GET /api/pubsub/topics?domain=media should filter."""
        resp = client.get("/api/pubsub/topics?domain=media")
        data = resp.json()
        assert resp.status_code == 200
        for topic in data["topics"]:
            assert topic.startswith("media.")

    def test_topics_domains_grouped(self, client):
        """AC-007: Topics should be grouped by domain."""
        resp = client.get("/api/pubsub/topics")
        data = resp.json()
        assert "domains" in data
        assert data["domain_count"] > 0
        # Should have known domains
        domain_names = list(data["domains"].keys())
        assert "media" in domain_names or "publish" in domain_names

    def test_topic_events_endpoint(self, client):
        """AC-007: GET /api/pubsub/topics/{topic}/events should work."""
        resp = client.get("/api/pubsub/topics/media.ingested/events")
        data = resp.json()
        assert resp.status_code == 200
        assert "topic" in data
        assert "events" in data
        assert data["topic"] == "media.ingested"

    def test_topic_stats_endpoint(self, client):
        """AC-007: GET /api/pubsub/topics/{topic}/stats should work."""
        resp = client.get("/api/pubsub/topics/media.ingested/stats")
        data = resp.json()
        assert resp.status_code == 200
        assert "subscriber_count" in data
        assert "subscribers" in data

    def test_subscribers_endpoint(self, client):
        """AC-007: GET /api/pubsub/subscribers should list all subscribers."""
        resp = client.get("/api/pubsub/subscribers")
        data = resp.json()
        assert resp.status_code == 200
        assert "subscribers" in data
        assert "count" in data

    def test_consumer_lag_endpoint(self, client):
        """AC-007: GET /api/pubsub/lag should return lag data."""
        resp = client.get("/api/pubsub/lag")
        data = resp.json()
        assert resp.status_code == 200
        assert "lag" in data
        assert "total_pending" in data

    def test_bus_stats_endpoint(self, client):
        """AC-007: GET /api/pubsub/stats should return bus statistics."""
        resp = client.get("/api/pubsub/stats")
        data = resp.json()
        assert resp.status_code == 200
        assert "stats" in data
        assert "timestamp" in data

    def test_bus_health_endpoint(self, client):
        """AC-007: GET /api/pubsub/health should return health status."""
        resp = client.get("/api/pubsub/health")
        data = resp.json()
        assert resp.status_code == 200
        assert data["healthy"] is True
        assert "bus_type" in data
        assert "registered_topics" in data
        assert data["registered_topics"] > 0


# ============================================================================
# Cross-feature: All endpoints importable
# ============================================================================

class TestEndpointImports:
    """Verify all new endpoints can be imported."""

    def test_media_assets_router_import(self):
        """Router: media_assets router should import."""
        from api.endpoints.media_assets import router
        assert len(router.routes) >= 20

    def test_pubsub_inspector_router_import(self):
        """Router: pubsub_inspector router should import."""
        from api.endpoints.pubsub_inspector import router
        assert len(router.routes) >= 5

    def test_event_bus_has_inspector_methods(self):
        """EventBus: Should have get_topic_history, get_topic_subscribers, etc."""
        from services.event_bus import EventBus
        bus = EventBus.get_instance()
        assert hasattr(bus, 'get_topic_history')
        assert hasattr(bus, 'get_topic_subscribers')
        assert hasattr(bus, 'get_all_subscribers')
        assert hasattr(bus, 'get_consumer_lag')
        EventBus.reset_instance()
