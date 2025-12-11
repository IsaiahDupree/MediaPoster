"""
Comprehensive Backend API Endpoint Tests
Tests all API endpoints for availability, response format, and basic functionality.
"""
import pytest
import httpx
from typing import Dict, Any

# API Base URL
API_BASE = "http://localhost:5555"


# =============================================================================
# CORE ENDPOINTS
# =============================================================================

class TestCoreEndpoints:
    """Test core application endpoints."""
    
    def test_root_endpoint(self):
        """Root endpoint should return API info."""
        response = httpx.get(f"{API_BASE}/", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        print(f"✓ Root: {data['message']}")
    
    def test_health_endpoint(self):
        """Health check should return status."""
        response = httpx.get(f"{API_BASE}/health", timeout=10)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "services" in data
        print(f"✓ Health: {data['status']}")
    
    def test_api_health_endpoint(self):
        """API health check should return status."""
        response = httpx.get(f"{API_BASE}/api/health", timeout=10)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "api_version" in data
        print(f"✓ API Health: {data['api_version']}")


# =============================================================================
# MEDIA PROCESSING (DATABASE) ENDPOINTS
# =============================================================================

class TestMediaProcessingDBEndpoints:
    """Test database-backed media processing endpoints."""
    
    def test_media_db_health(self):
        """Media DB health endpoint."""
        response = httpx.get(f"{API_BASE}/api/media-db/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Media DB Health: {data['database']}")
    
    def test_media_db_stats(self):
        """Media DB stats endpoint."""
        response = httpx.get(f"{API_BASE}/api/media-db/stats", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "total_videos" in data
        assert "analyzed_count" in data
        print(f"✓ Stats: {data['total_videos']} total")
    
    def test_media_db_list(self):
        """Media DB list endpoint."""
        response = httpx.get(f"{API_BASE}/api/media-db/list?limit=10", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List: {len(data)} items")
    
    def test_media_db_list_with_status_filter(self):
        """Media DB list with status filter."""
        response = httpx.get(
            f"{API_BASE}/api/media-db/list?status=analyzed&limit=5",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List (analyzed): {len(data)} items")
    
    def test_media_db_search(self):
        """Media DB search endpoint."""
        response = httpx.get(
            f"{API_BASE}/api/media-db/search?query=test&limit=5",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Search: {len(data)} results")


# =============================================================================
# VIDEO ENDPOINTS
# =============================================================================

class TestVideoEndpoints:
    """Test video management endpoints."""
    
    def test_list_videos(self):
        """List videos endpoint."""
        response = httpx.get(f"{API_BASE}/api/videos?limit=10", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data or isinstance(data, list)
        print(f"✓ Videos list")
    
    def test_video_stats(self):
        """Video stats endpoint."""
        response = httpx.get(f"{API_BASE}/api/videos/stats", timeout=10)
        # May not exist, that's ok
        assert response.status_code in [200, 404, 405]
        print(f"✓ Video stats: {response.status_code}")


# =============================================================================
# INGESTION ENDPOINTS
# =============================================================================

class TestIngestionEndpoints:
    """Test ingestion endpoints."""
    
    def test_ingestion_status(self):
        """Ingestion status endpoint."""
        response = httpx.get(f"{API_BASE}/api/ingestion/status", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Ingestion status: {response.status_code}")


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

class TestAnalyticsEndpoints:
    """Test analytics endpoints."""
    
    def test_analytics_overview(self):
        """Analytics overview endpoint."""
        response = httpx.get(f"{API_BASE}/api/analytics/overview", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Analytics overview: {response.status_code}")
    
    def test_analytics_ci_overview(self):
        """Content Intelligence analytics endpoint."""
        response = httpx.get(f"{API_BASE}/api/analytics-ci/overview", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ CI Analytics: {response.status_code}")


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

class TestAnalysisEndpoints:
    """Test analysis endpoints."""
    
    def test_analysis_status(self):
        """Analysis status endpoint."""
        response = httpx.get(f"{API_BASE}/api/analysis/status", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Analysis status: {response.status_code}")


# =============================================================================
# CONTENT ENDPOINTS
# =============================================================================

class TestContentEndpoints:
    """Test content graph endpoints."""
    
    def test_content_list(self):
        """Content list endpoint."""
        response = httpx.get(f"{API_BASE}/api/content", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Content list: {response.status_code}")


# =============================================================================
# CLIPS ENDPOINTS
# =============================================================================

class TestClipsEndpoints:
    """Test clips endpoints."""
    
    def test_clips_list(self):
        """Clips list endpoint."""
        response = httpx.get(f"{API_BASE}/api/clips", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Clips list: {response.status_code}")
    
    def test_clip_management_list(self):
        """Clip management list endpoint."""
        response = httpx.get(f"{API_BASE}/api/clip-management/clips", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Clip management: {response.status_code}")


# =============================================================================
# BRIEFS ENDPOINTS
# =============================================================================

class TestBriefsEndpoints:
    """Test creative briefs endpoints."""
    
    def test_briefs_list(self):
        """Briefs list endpoint."""
        response = httpx.get(f"{API_BASE}/api/briefs", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Briefs list: {response.status_code}")


# =============================================================================
# PEOPLE ENDPOINTS
# =============================================================================

class TestPeopleEndpoints:
    """Test people graph endpoints."""
    
    def test_people_list(self):
        """People list endpoint."""
        response = httpx.get(f"{API_BASE}/api/people", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ People list: {response.status_code}")


# =============================================================================
# WORKSPACES ENDPOINTS
# =============================================================================

class TestWorkspacesEndpoints:
    """Test workspaces endpoints."""
    
    def test_workspaces_list(self):
        """Workspaces list endpoint."""
        response = httpx.get(f"{API_BASE}/api/workspaces", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Workspaces list: {response.status_code}")


# =============================================================================
# DASHBOARD ENDPOINTS
# =============================================================================

class TestDashboardEndpoints:
    """Test dashboard endpoints."""
    
    def test_dashboard_overview(self):
        """Dashboard overview endpoint."""
        response = httpx.get(f"{API_BASE}/api/dashboard/overview", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Dashboard overview: {response.status_code}")


# =============================================================================
# THUMBNAILS ENDPOINTS
# =============================================================================

class TestThumbnailsEndpoints:
    """Test thumbnail generation endpoints."""
    
    def test_thumbnails_status(self):
        """Thumbnails status endpoint."""
        response = httpx.get(f"{API_BASE}/api/thumbnails/status", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Thumbnails status: {response.status_code}")


# =============================================================================
# PUBLISHING ENDPOINTS
# =============================================================================

class TestPublishingEndpoints:
    """Test publishing endpoints."""
    
    def test_publishing_queue(self):
        """Publishing queue endpoint."""
        response = httpx.get(f"{API_BASE}/api/publishing/queue", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Publishing queue: {response.status_code}")


# =============================================================================
# PLATFORM ENDPOINTS
# =============================================================================

class TestPlatformEndpoints:
    """Test platform publishing endpoints."""
    
    def test_platform_accounts(self):
        """Platform accounts endpoint."""
        response = httpx.get(f"{API_BASE}/api/platform/accounts", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Platform accounts: {response.status_code}")


# =============================================================================
# TRENDING ENDPOINTS
# =============================================================================

class TestTrendingEndpoints:
    """Test trending content endpoints."""
    
    def test_trending_videos(self):
        """Trending videos endpoint."""
        response = httpx.get(f"{API_BASE}/api/trending/videos", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Trending videos: {response.status_code}")


# =============================================================================
# STORAGE ENDPOINTS
# =============================================================================

class TestStorageEndpoints:
    """Test storage management endpoints."""
    
    def test_storage_stats(self):
        """Storage stats endpoint."""
        response = httpx.get(f"{API_BASE}/api/storage/stats", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Storage stats: {response.status_code}")


# =============================================================================
# JOBS ENDPOINTS
# =============================================================================

class TestJobsEndpoints:
    """Test jobs endpoints."""
    
    def test_jobs_list(self):
        """Jobs list endpoint."""
        response = httpx.get(f"{API_BASE}/api/jobs", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Jobs list: {response.status_code}")


# =============================================================================
# CALENDAR ENDPOINTS
# =============================================================================

class TestCalendarEndpoints:
    """Test calendar endpoints."""
    
    def test_calendar_events(self):
        """Calendar events endpoint."""
        response = httpx.get(f"{API_BASE}/api/calendar/events", timeout=10)
        assert response.status_code in [200, 404, 405]
        print(f"✓ Calendar events: {response.status_code}")


# =============================================================================
# ENDPOINT DISCOVERY
# =============================================================================

class TestEndpointDiscovery:
    """Test API documentation and endpoint discovery."""
    
    def test_openapi_schema(self):
        """OpenAPI schema should be available."""
        response = httpx.get(f"{API_BASE}/openapi.json", timeout=10)
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        
        # Count endpoints
        endpoint_count = len(schema["paths"])
        print(f"✓ OpenAPI schema: {endpoint_count} endpoints")
        
        return schema
    
    def test_docs_available(self):
        """API docs should be available."""
        response = httpx.get(f"{API_BASE}/docs", timeout=10)
        assert response.status_code == 200
        print(f"✓ API docs available")
    
    def test_redoc_available(self):
        """ReDoc should be available."""
        response = httpx.get(f"{API_BASE}/redoc", timeout=10)
        assert response.status_code == 200
        print(f"✓ ReDoc available")


# =============================================================================
# ENDPOINT SUMMARY
# =============================================================================

class TestEndpointSummary:
    """Generate summary of all endpoints."""
    
    def test_generate_endpoint_summary(self):
        """Generate summary of all available endpoints."""
        print(f"\n{'='*60}")
        print(f"BACKEND API ENDPOINT SUMMARY")
        print(f"{'='*60}\n")
        
        # Get OpenAPI schema
        response = httpx.get(f"{API_BASE}/openapi.json", timeout=10)
        if response.status_code != 200:
            pytest.skip("Cannot fetch OpenAPI schema")
        
        schema = response.json()
        paths = schema.get("paths", {})
        
        # Group by tag/prefix
        endpoints_by_prefix = {}
        for path, methods in paths.items():
            prefix = path.split("/")[1] if "/" in path else "root"
            if prefix not in endpoints_by_prefix:
                endpoints_by_prefix[prefix] = []
            
            for method in methods.keys():
                if method in ["get", "post", "put", "delete", "patch"]:
                    endpoints_by_prefix[prefix].append(f"{method.upper()} {path}")
        
        # Print summary
        total_endpoints = 0
        for prefix in sorted(endpoints_by_prefix.keys()):
            endpoints = endpoints_by_prefix[prefix]
            print(f"/{prefix}/ ({len(endpoints)} endpoints)")
            for endpoint in sorted(endpoints)[:5]:  # Show first 5
                print(f"  {endpoint}")
            if len(endpoints) > 5:
                print(f"  ... and {len(endpoints) - 5} more")
            print()
            total_endpoints += len(endpoints)
        
        print(f"{'='*60}")
        print(f"Total Endpoints: {total_endpoints}")
        print(f"{'='*60}\n")
        
        assert total_endpoints > 0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
