"""
Backend Tests with Detailed Logging
Captures all requests, responses, and backend logs for debugging.

Run: pytest tests/test_backend_detailed_logs.py -v -s --log-cli-level=DEBUG
"""
import pytest
import httpx
import json
import logging
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:5555"


def log_request(method: str, url: str, **kwargs):
    """Log HTTP request details."""
    logger.info(f"\n{'='*60}")
    logger.info(f"🔵 REQUEST: {method} {url}")
    if kwargs.get("params"):
        logger.info(f"   Params: {json.dumps(kwargs['params'], indent=2)}")
    if kwargs.get("json"):
        logger.info(f"   Body: {json.dumps(kwargs['json'], indent=2)}")
    if kwargs.get("headers"):
        logger.info(f"   Headers: {json.dumps(dict(kwargs['headers']), indent=2)}")
    logger.info(f"{'='*60}\n")


def log_response(response: httpx.Response):
    """Log HTTP response details."""
    logger.info(f"\n{'='*60}")
    logger.info(f"🟢 RESPONSE: {response.status_code} {response.request.method} {response.request.url}")
    logger.info(f"   Status: {response.status_code} {response.reason_phrase}")
    logger.info(f"   Headers: {json.dumps(dict(response.headers), indent=2)}")
    
    try:
        body = response.json()
        logger.info(f"   Body: {json.dumps(body, indent=2)}")
    except:
        logger.info(f"   Body (text): {response.text[:500]}")
    
    logger.info(f"{'='*60}\n")


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

class TestHealthCheck:
    """Test backend health endpoint with detailed logging."""
    
    def test_health_endpoint(self):
        """Check if backend is running and healthy."""
        url = f"{API_BASE}/health"
        log_request("GET", url)
        
        response = httpx.get(url, timeout=5)
        log_response(response)
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        logger.info(f"✅ Backend is healthy: {data}")


# =============================================================================
# MEDIA LIBRARY TESTS
# =============================================================================

class TestMediaLibrary:
    """Test media library endpoints with detailed logging."""
    
    def test_list_media(self):
        """List all media files."""
        url = f"{API_BASE}/api/media-db/list"
        params = {"limit": 10}
        log_request("GET", url, params=params)
        
        response = httpx.get(url, params=params, timeout=10)
        log_response(response)
        
        assert response.status_code == 200
        data = response.json()
        logger.info(f"📊 Found {len(data)} media files")
        
        if data:
            logger.info(f"   First item: {json.dumps(data[0], indent=2)}")
    
    def test_media_stats(self):
        """Get media library statistics."""
        url = f"{API_BASE}/api/media-db/stats"
        log_request("GET", url)
        
        response = httpx.get(url, timeout=10)
        log_response(response)
        
        assert response.status_code == 200
        data = response.json()
        logger.info(f"📈 Stats: {json.dumps(data, indent=2)}")


# =============================================================================
# THUMBNAIL GENERATION TESTS
# =============================================================================

class TestThumbnailGeneration:
    """Test thumbnail generation with detailed logging."""
    
    def test_regenerate_thumbnails(self):
        """Check thumbnail generation via batch analyze."""
        # First get a video without thumbnail
        url = f"{API_BASE}/api/media-db/list"
        params = {"limit": 50}
        log_request("GET", url, params=params)
        
        response = httpx.get(url, params=params, timeout=10)
        log_response(response)
        
        assert response.status_code == 200
        media = response.json()
        
        videos = [m for m in media if m.get("media_type") == "video"]
        logger.info(f"🎬 Found {len(videos)} videos")
        
        if videos:
            video = videos[0]
            logger.info(f"   Sample video: {video.get('filename')}")
            logger.info(f"   Has thumbnail: {bool(video.get('thumbnail_path'))}")
    
    def test_check_missing_thumbnails(self):
        """Check for media without thumbnails."""
        url = f"{API_BASE}/api/media-db/list"
        params = {"limit": 200}
        log_request("GET", url, params=params)
        
        response = httpx.get(url, params=params, timeout=10)
        log_response(response)
        
        assert response.status_code == 200
        media = response.json()
        
        missing = [m for m in media if not m.get("thumbnail_url")]
        logger.info(f"📊 Media without thumbnails: {len(missing)}/{len(media)}")
        
        if missing:
            logger.warning(f"⚠️  Missing thumbnails for:")
            for m in missing[:5]:
                logger.warning(f"     - {m.get('filename')} (type: {m.get('media_type')})")


# =============================================================================
# VIDEO ANALYSIS TESTS
# =============================================================================

class TestVideoAnalysis:
    """Test video analysis endpoints with detailed logging."""
    
    def test_list_videos_with_analysis(self):
        """List videos and check analysis status."""
        url = f"{API_BASE}/api/media-db/list"
        params = {"limit": 50}
        log_request("GET", url, params=params)
        
        response = httpx.get(url, params=params, timeout=10)
        log_response(response)
        
        assert response.status_code == 200
        media = response.json()
        
        videos = [m for m in media if m.get("media_type") == "video"]
        analyzed = [v for v in videos if v.get("analysis_status") == "completed"]
        
        logger.info(f"🎬 Videos: {len(videos)} total, {len(analyzed)} analyzed")
        
        if analyzed:
            logger.info(f"   Sample analyzed video: {json.dumps(analyzed[0], indent=2)}")


# =============================================================================
# SOCIAL ACCOUNTS TESTS
# =============================================================================

class TestSocialAccounts:
    """Test social accounts endpoints with detailed logging."""
    
    def test_list_social_accounts(self):
        """List all social media accounts."""
        url = f"{API_BASE}/api/social-accounts/accounts"
        log_request("GET", url)
        
        response = httpx.get(url, timeout=10)
        log_response(response)
        
        assert response.status_code == 200
        accounts = response.json()
        logger.info(f"📱 Found {len(accounts)} social accounts")
        
        # Group by platform
        by_platform = {}
        for acc in accounts:
            platform = acc["platform"]
            by_platform[platform] = by_platform.get(platform, 0) + 1
        
        logger.info(f"   By platform: {json.dumps(by_platform, indent=2)}")
    
    def test_analytics_overview(self):
        """Get social media analytics overview."""
        url = f"{API_BASE}/api/social-analytics/overview"
        log_request("GET", url)
        
        response = httpx.get(url, timeout=10)
        log_response(response)
        
        assert response.status_code == 200
        data = response.json()
        logger.info(f"📊 Analytics Overview:")
        logger.info(f"   Platforms: {data['total_platforms']}")
        logger.info(f"   Accounts: {data['total_accounts']}")
        logger.info(f"   Followers: {data['total_followers']:,}")
        logger.info(f"   Posts: {data['total_posts']:,}")
        logger.info(f"   Likes: {data['total_likes']:,}")
    
    def test_sync_accounts_from_env(self):
        """Sync social accounts from environment."""
        url = f"{API_BASE}/api/social-accounts/accounts/sync-from-env"
        log_request("POST", url)
        
        response = httpx.post(url, timeout=10)
        log_response(response)
        
        assert response.status_code == 200
        data = response.json()
        logger.info(f"📥 Sync result: {json.dumps(data, indent=2)}")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error responses with detailed logging."""
    
    def test_404_not_found(self):
        """Test 404 error response."""
        url = f"{API_BASE}/api/nonexistent-endpoint"
        log_request("GET", url)
        
        response = httpx.get(url, timeout=5)
        log_response(response)
        
        assert response.status_code == 404
        logger.info(f"✅ 404 handled correctly")
    
    def test_invalid_media_id(self):
        """Test invalid media ID error."""
        url = f"{API_BASE}/api/media-db/list/invalid-uuid-123"
        log_request("GET", url)
        
        response = httpx.get(url, timeout=5)
        log_response(response)
        
        # Should return 404, 422, or 405
        assert response.status_code in [404, 405, 422]
        logger.info(f"✅ Invalid ID handled correctly")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test endpoint performance with timing."""
    
    def test_list_media_performance(self):
        """Measure list media endpoint performance."""
        url = f"{API_BASE}/api/media-db/list"
        params = {"limit": 100}
        
        start = datetime.now()
        log_request("GET", url, params=params)
        
        response = httpx.get(url, params=params, timeout=10)
        
        duration = (datetime.now() - start).total_seconds()
        log_response(response)
        
        assert response.status_code == 200
        data = response.json()
        
        logger.info(f"⏱️  Performance:")
        logger.info(f"   Duration: {duration:.3f}s")
        logger.info(f"   Items: {len(data)}")
        logger.info(f"   Rate: {len(data)/duration:.1f} items/sec")
        
        # Should be reasonably fast
        assert duration < 5.0, f"Too slow: {duration}s"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Test complete workflows with detailed logging."""
    
    def test_full_media_workflow(self):
        """Test complete media workflow: list -> stats -> thumbnails."""
        logger.info("\n" + "="*60)
        logger.info("🔄 FULL MEDIA WORKFLOW TEST")
        logger.info("="*60 + "\n")
        
        # Step 1: List media
        logger.info("📋 Step 1: List media files")
        response = httpx.get(f"{API_BASE}/api/media-db/list", params={"limit": 10}, timeout=10)
        log_response(response)
        assert response.status_code == 200
        media = response.json()
        logger.info(f"   ✅ Found {len(media)} media files\n")
        
        # Step 2: Get stats
        logger.info("📊 Step 2: Get statistics")
        response = httpx.get(f"{API_BASE}/api/media-db/stats", timeout=10)
        log_response(response)
        assert response.status_code == 200
        stats = response.json()
        logger.info(f"   ✅ Stats retrieved: {json.dumps(stats, indent=2)}\n")
        
        # Step 3: Check thumbnails
        logger.info("🖼️  Step 3: Check thumbnail status")
        missing = [m for m in media if not m.get("thumbnail_url")]
        logger.info(f"   Missing thumbnails: {len(missing)}/{len(media)}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ WORKFLOW COMPLETE")
        logger.info("="*60 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--log-cli-level=DEBUG"])
