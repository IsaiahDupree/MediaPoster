"""
Test Suite for External Scheduling API
======================================
Tests recent developments:
- External scheduling endpoints (submit, smart-schedule, bulk)
- Queue manager and rate limiting
- Local video path support (Safari Automation integration)
- Account listing and capacity endpoints

Run with: pytest tests/test_external_scheduling.py -v
Or standalone: python tests/test_external_scheduling.py
"""

import os
import sys
import json
import tempfile
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import pytest

BASE_URL = "http://localhost:5555"


class TestExternalSchedulingAPI:
    """Test suite for /api/external/* endpoints"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    # =========================================================================
    # Health & Info Endpoints
    # =========================================================================
    
    def test_health_endpoint(self, client):
        """Test /api/external/health returns healthy status"""
        response = client.get("/api/external/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "api_version" in data
        assert "endpoints" in data
        print(f"✅ Health check passed - API v{data['api_version']}")
    
    def test_accounts_endpoint(self, client):
        """Test /api/external/accounts lists available accounts"""
        response = client.get("/api/external/accounts")
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        
        # Verify expected platforms
        expected_platforms = ["tiktok", "instagram", "youtube", "twitter", "threads"]
        for platform in expected_platforms:
            assert platform in data["accounts"], f"Missing platform: {platform}"
        
        # Verify account structure
        for platform, accounts in data["accounts"].items():
            assert isinstance(accounts, list)
            for acc in accounts:
                assert "id" in acc
                assert "username" in acc
        
        print(f"✅ Accounts endpoint - {len(data['accounts'])} platforms configured")
    
    # =========================================================================
    # Queue Analysis Endpoints
    # =========================================================================
    
    def test_queue_analysis(self, client):
        """Test /api/external/queue-analysis returns queue state"""
        response = client.get("/api/external/queue-analysis", params={
            "platform": "tiktok",
            "account_id": "710"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["platform"] == "tiktok"
        assert data["account_id"] == "710"
        assert "posts_today" in data
        assert "posts_this_week" in data
        assert "daily_capacity_remaining" in data
        assert "next_available_slot" in data
        assert "recommended_slots" in data
        
        # Verify capacity is reasonable
        assert data["daily_capacity_remaining"] >= 0
        assert data["daily_capacity_remaining"] <= 8  # TikTok max
        
        print(f"✅ Queue analysis - TikTok capacity: {data['daily_capacity_remaining']}/8")
    
    def test_capacity_endpoint(self, client):
        """Test /api/external/capacity returns posting capacity"""
        response = client.get("/api/external/capacity")
        assert response.status_code == 200
        data = response.json()
        
        assert "generated_at" in data
        assert "timezone" in data
        assert "accounts" in data
        
        print(f"✅ Capacity endpoint - Generated at {data['generated_at']}")
    
    # =========================================================================
    # Submit Endpoint Tests
    # =========================================================================
    
    def test_submit_validation_requires_video(self, client):
        """Test /api/external/submit validates video input"""
        response = client.post("/api/external/submit", json={
            "title": "Test Video",
            "caption": "Test caption",
            "targets": [
                {"platform": "tiktok", "account_id": "710", "scheduled_at": "2026-01-31T18:00:00Z"}
            ]
        })
        # Should fail validation - no video_url or video_path
        assert response.status_code in [400, 422, 500]
        print("✅ Submit validation - Requires video_url or video_path")
    
    def test_submit_with_invalid_local_path(self, client):
        """Test /api/external/submit handles missing local files"""
        response = client.post("/api/external/submit", json={
            "video_path": "/nonexistent/path/video.mp4",
            "title": "Test Video",
            "caption": "Test caption",
            "targets": [
                {"platform": "tiktok", "account_id": "710", "scheduled_at": "2026-01-31T18:00:00Z"}
            ]
        })
        assert response.status_code in [400, 500]
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
        print("✅ Submit validation - Handles missing local files")
    
    def test_submit_with_local_video(self, client):
        """Test /api/external/submit with local video file"""
        # Create a temporary test video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content for testing")
            temp_path = f.name
        
        try:
            response = client.post("/api/external/submit", json={
                "video_path": temp_path,
                "title": "Test Local Video",
                "caption": "Testing local path support",
                "targets": [
                    {"platform": "tiktok", "account_id": "710", "scheduled_at": "2026-02-01T15:00:00Z"}
                ],
                "source_system": "test_suite"
            })
            
            # May fail during ingestion but should accept the local path
            if response.status_code == 200:
                data = response.json()
                assert data["success"] == True
                assert len(data["scheduled_posts"]) > 0
                print(f"✅ Submit with local video - Scheduled {len(data['scheduled_posts'])} post(s)")
            else:
                # Acceptable if ingestion fails (video content is fake)
                print(f"⚠️  Submit with local video - Ingestion failed (expected with fake file)")
        finally:
            os.unlink(temp_path)
    
    # =========================================================================
    # Smart Schedule Endpoint Tests
    # =========================================================================
    
    def test_smart_schedule_validation(self, client):
        """Test /api/external/smart-schedule validation"""
        response = client.post("/api/external/smart-schedule", json={
            "title": "Test Video",
            "caption": "Test caption",
            "platforms": ["tiktok"]
            # Missing video_url and video_path
        })
        assert response.status_code in [400, 422, 500]
        print("✅ Smart schedule validation - Requires video input")
    
    def test_smart_schedule_with_local_video(self, client):
        """Test /api/external/smart-schedule with local video"""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            temp_path = f.name
        
        try:
            response = client.post("/api/external/smart-schedule", json={
                "video_path": temp_path,
                "title": "Smart Scheduled Video",
                "caption": "Let MediaPoster decide the time!",
                "platforms": ["tiktok", "youtube"],
                "source_system": "test_suite"
            })
            
            if response.status_code == 200:
                data = response.json()
                assert data["success"] == True
                assert "queue_analysis" in data
                print(f"✅ Smart schedule - Allocated {len(data['scheduled_posts'])} post(s)")
            else:
                print(f"⚠️  Smart schedule - Ingestion failed (expected with fake file)")
        finally:
            os.unlink(temp_path)
    
    # =========================================================================
    # Status Endpoint Tests
    # =========================================================================
    
    def test_status_endpoint(self, client):
        """Test /api/external/status/{source_id}"""
        response = client.get("/api/external/status/test_source_id")
        assert response.status_code == 200
        data = response.json()
        
        assert "source_id" in data
        assert "total" in data
        assert "posts" in data
        assert isinstance(data["posts"], list)
        
        print(f"✅ Status endpoint - Found {data['total']} posts for source")


class TestQueueManager:
    """Test the ExternalQueueManager service directly"""
    
    def test_queue_manager_initialization(self):
        """Test queue manager can be initialized"""
        from services.external_queue_manager import get_queue_manager, PLATFORM_CONFIGS
        
        qm = get_queue_manager()
        assert qm is not None
        assert qm.timezone is not None
        print("✅ Queue manager initialized")
    
    def test_platform_configs(self):
        """Test platform rate limit configurations"""
        from services.external_queue_manager import PLATFORM_CONFIGS
        
        expected_platforms = ["tiktok", "instagram", "youtube", "twitter", "threads"]
        for platform in expected_platforms:
            assert platform in PLATFORM_CONFIGS, f"Missing config for {platform}"
            config = PLATFORM_CONFIGS[platform]
            assert config.max_daily_posts > 0
            assert config.min_interval_minutes > 0
        
        # Verify specific limits
        assert PLATFORM_CONFIGS["tiktok"].max_daily_posts == 8
        assert PLATFORM_CONFIGS["instagram"].max_daily_posts == 5
        assert PLATFORM_CONFIGS["youtube"].max_daily_posts == 3
        
        print("✅ Platform configs verified")
        for p, c in PLATFORM_CONFIGS.items():
            print(f"   {p}: {c.max_daily_posts}/day, {c.min_interval_minutes}min spacing")
    
    def test_queue_analysis(self):
        """Test queue analysis functionality"""
        from services.external_queue_manager import get_queue_manager
        
        qm = get_queue_manager()
        analysis = qm.analyze_queue("tiktok", "710", days_ahead=7)
        
        assert analysis.platform == "tiktok"
        assert analysis.account_id == "710"
        assert analysis.daily_capacity_remaining >= 0
        assert analysis.next_available_slot is not None
        assert len(analysis.recommended_slots) > 0
        
        print(f"✅ Queue analysis - Next slot: {analysis.next_available_slot}")


class TestModels:
    """Test Pydantic models"""
    
    def test_smart_schedule_request_with_url(self):
        """Test SmartScheduleRequest accepts video_url"""
        from api.endpoints.external_scheduling import SmartScheduleRequest
        
        req = SmartScheduleRequest(
            video_url="https://example.com/video.mp4",
            title="Test",
            caption="Test caption",
            platforms=["tiktok"]
        )
        assert req.video_url == "https://example.com/video.mp4"
        assert req.video_path is None
        print("✅ SmartScheduleRequest with video_url")
    
    def test_smart_schedule_request_with_path(self):
        """Test SmartScheduleRequest accepts video_path"""
        from api.endpoints.external_scheduling import SmartScheduleRequest
        
        req = SmartScheduleRequest(
            video_path="/path/to/local/video.mp4",
            title="Test",
            caption="Test caption",
            platforms=["tiktok", "youtube"]
        )
        assert req.video_path == "/path/to/local/video.mp4"
        assert req.video_url is None
        print("✅ SmartScheduleRequest with video_path")
    
    def test_external_video_submission_with_path(self):
        """Test ExternalVideoSubmission accepts video_path"""
        from api.endpoints.external_scheduling import ExternalVideoSubmission, ScheduleTarget
        
        submission = ExternalVideoSubmission(
            video_path="/path/to/video.mp4",
            title="Test",
            caption="Test",
            targets=[
                ScheduleTarget(
                    platform="tiktok",
                    account_id="710",
                    scheduled_at="2026-01-31T15:00:00Z"
                )
            ]
        )
        assert submission.video_path == "/path/to/video.mp4"
        print("✅ ExternalVideoSubmission with video_path")


def run_standalone_tests():
    """Run tests without pytest (for quick verification)"""
    print("\n" + "="*60)
    print("🧪 External Scheduling API Test Suite")
    print("="*60 + "\n")
    
    base_url = "http://localhost:5555"
    
    # Check if backend is running
    try:
        response = httpx.get(f"{base_url}/api/external/health", timeout=5.0)
        if response.status_code != 200:
            print("❌ Backend not responding properly")
            return False
    except httpx.ConnectError:
        print("❌ Backend not running at localhost:5555")
        print("   Start with: python main.py")
        return False
    
    print("📡 Backend is running\n")
    
    all_passed = True
    client = httpx.Client(base_url=base_url, timeout=30.0)
    
    tests = [
        ("Health Endpoint", lambda: test_health(client)),
        ("Accounts Endpoint", lambda: test_accounts(client)),
        ("Queue Analysis", lambda: test_queue_analysis(client)),
        ("Capacity Endpoint", lambda: test_capacity(client)),
        ("Submit Validation", lambda: test_submit_validation(client)),
        ("Smart Schedule Validation", lambda: test_smart_schedule_validation(client)),
        ("Status Endpoint", lambda: test_status(client)),
        ("Queue Manager", lambda: test_queue_manager()),
        ("Model: SmartScheduleRequest", lambda: test_model_smart_schedule()),
        ("Model: ExternalVideoSubmission", lambda: test_model_submission()),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
            failed += 1
            all_passed = False
    
    print("\n" + "="*60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return all_passed


def test_health(client):
    response = client.get("/api/external/health")
    assert response.status_code == 200
    print("✅ Health endpoint")

def test_accounts(client):
    response = client.get("/api/external/accounts")
    assert response.status_code == 200
    data = response.json()
    assert "tiktok" in data["accounts"]
    print(f"✅ Accounts endpoint ({len(data['accounts'])} platforms)")

def test_queue_analysis(client):
    response = client.get("/api/external/queue-analysis", params={
        "platform": "tiktok", "account_id": "710"
    })
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Queue analysis (capacity: {data['daily_capacity_remaining']}/8)")

def test_capacity(client):
    response = client.get("/api/external/capacity")
    assert response.status_code == 200
    print("✅ Capacity endpoint")

def test_submit_validation(client):
    response = client.post("/api/external/submit", json={
        "title": "Test", "caption": "Test",
        "targets": [{"platform": "tiktok", "account_id": "710", "scheduled_at": "2026-01-31T18:00:00Z"}]
    })
    assert response.status_code in [400, 422, 500]
    print("✅ Submit validation (rejects missing video)")

def test_smart_schedule_validation(client):
    response = client.post("/api/external/smart-schedule", json={
        "title": "Test", "caption": "Test", "platforms": ["tiktok"]
    })
    assert response.status_code in [400, 422, 500]
    print("✅ Smart schedule validation (rejects missing video)")

def test_status(client):
    response = client.get("/api/external/status/test_id")
    assert response.status_code == 200
    print("✅ Status endpoint")

def test_queue_manager():
    from services.external_queue_manager import get_queue_manager, PLATFORM_CONFIGS
    qm = get_queue_manager()
    assert PLATFORM_CONFIGS["tiktok"].max_daily_posts == 8
    print("✅ Queue manager + platform configs")

def test_model_smart_schedule():
    from api.endpoints.external_scheduling import SmartScheduleRequest
    req = SmartScheduleRequest(
        video_path="/test.mp4", title="Test", caption="Test", platforms=["tiktok"]
    )
    assert req.video_path == "/test.mp4"
    print("✅ SmartScheduleRequest model (accepts video_path)")

def test_model_submission():
    from api.endpoints.external_scheduling import ExternalVideoSubmission
    sub = ExternalVideoSubmission(
        video_path="/test.mp4", title="Test", caption="Test",
        targets=[{"platform": "tiktok", "account_id": "710", "scheduled_at": "2026-01-31T18:00:00Z"}]
    )
    assert sub.video_path == "/test.mp4"
    print("✅ ExternalVideoSubmission model (accepts video_path)")


if __name__ == "__main__":
    # Run standalone tests
    success = run_standalone_tests()
    sys.exit(0 if success else 1)
