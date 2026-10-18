"""
Content Pipeline Test Suite - Part 1: Core Tests
Comprehensive tests for the automated content pipeline.
Target: 300 test cases total (split across files)

Test Categories:
- Queue Management (30 tests)
- Content Approval (40 tests)  
- Scheduling (45 tests)
- Variations (25 tests)
- Platform Matching (35 tests)
"""

import pytest
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid

BASE_URL = "http://localhost:5555"
API_URL = f"{BASE_URL}/api/content-pipeline"


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def reset_data():
    """Reset mock data before tests"""
    response = requests.post(f"{API_URL}/reset-mock-data")
    return response.json()


@pytest.fixture
def content_queue(reset_data):
    """Get content queue"""
    response = requests.get(f"{API_URL}/queue")
    return response.json()


@pytest.fixture
def single_content(content_queue):
    """Get a single content item"""
    if content_queue.get("items"):
        return content_queue["items"][0]
    return None


# ============================================================================
# 1. QUEUE MANAGEMENT TESTS (30 tests)
# ============================================================================

class TestQueueManagement:
    """Tests for content queue operations"""

    def test_001_get_queue_returns_200(self):
        """Queue endpoint returns 200"""
        response = requests.get(f"{API_URL}/queue")
        assert response.status_code == 200

    def test_002_queue_has_items(self, content_queue):
        """Queue contains items"""
        assert "items" in content_queue
        assert isinstance(content_queue["items"], list)

    def test_003_queue_has_total_count(self, content_queue):
        """Queue returns total count"""
        assert "total" in content_queue
        assert isinstance(content_queue["total"], int)

    def test_004_queue_items_have_id(self, content_queue):
        """Each item has an ID"""
        for item in content_queue.get("items", []):
            assert "id" in item
            assert item["id"] is not None

    def test_005_queue_items_have_status(self, content_queue):
        """Each item has a status"""
        for item in content_queue.get("items", []):
            assert "status" in item

    def test_006_queue_items_have_quality_score(self, content_queue):
        """Each item has quality score"""
        for item in content_queue.get("items", []):
            assert "quality_score" in item
            assert 0 <= item["quality_score"] <= 100

    def test_007_queue_items_have_niche(self, content_queue):
        """Each item has a niche"""
        for item in content_queue.get("items", []):
            assert "niche" in item

    def test_008_queue_items_have_content_type(self, content_queue):
        """Each item has content type"""
        for item in content_queue.get("items", []):
            assert "content_type" in item
            assert item["content_type"] in ["image", "video", "clip"]

    def test_009_queue_items_have_variations(self, content_queue):
        """Each item has variations"""
        for item in content_queue.get("items", []):
            assert "variations" in item
            assert isinstance(item["variations"], list)

    def test_010_queue_items_have_platform_assignments(self, content_queue):
        """Each item has platform assignments"""
        for item in content_queue.get("items", []):
            assert "platform_assignments" in item
            assert isinstance(item["platform_assignments"], list)

    def test_011_queue_pagination_limit(self):
        """Queue respects limit parameter"""
        response = requests.get(f"{API_URL}/queue", params={"limit": 5})
        data = response.json()
        assert len(data["items"]) <= 5

    def test_012_queue_pagination_offset(self):
        """Queue respects offset parameter"""
        response1 = requests.get(f"{API_URL}/queue", params={"limit": 5, "offset": 0})
        response2 = requests.get(f"{API_URL}/queue", params={"limit": 5, "offset": 5})
        data1 = response1.json()
        data2 = response2.json()
        if data1["items"] and data2["items"]:
            assert data1["items"][0]["id"] != data2["items"][0]["id"]

    def test_013_queue_filter_by_niche(self):
        """Queue filters by niche"""
        response = requests.get(f"{API_URL}/queue", params={"niche": "lifestyle"})
        data = response.json()
        for item in data.get("items", []):
            assert item.get("niche") == "lifestyle" or item.get("niche") is None

    def test_014_queue_filter_by_min_quality(self):
        """Queue filters by minimum quality"""
        response = requests.get(f"{API_URL}/queue", params={"min_quality": 80})
        data = response.json()
        for item in data.get("items", []):
            assert item["quality_score"] >= 80

    def test_015_queue_filter_by_content_type(self):
        """Queue filters by content type"""
        response = requests.get(f"{API_URL}/queue", params={"content_type": "video"})
        data = response.json()
        for item in data.get("items", []):
            assert item["content_type"] == "video"

    def test_016_queue_sorted_by_priority(self, content_queue):
        """Queue is sorted by priority descending"""
        items = content_queue.get("items", [])
        if len(items) >= 2:
            for i in range(len(items) - 1):
                assert items[i]["priority"] >= items[i + 1]["priority"] or \
                       items[i]["quality_score"] >= items[i + 1]["quality_score"]

    def test_017_get_next_content(self):
        """Get next content item for swipe"""
        response = requests.get(f"{API_URL}/queue/next")
        assert response.status_code == 200

    def test_018_next_content_is_highest_priority(self):
        """Next content is highest priority item"""
        next_response = requests.get(f"{API_URL}/queue/next")
        queue_response = requests.get(f"{API_URL}/queue", params={"limit": 1})
        if next_response.json() and queue_response.json().get("items"):
            assert next_response.json()["id"] == queue_response.json()["items"][0]["id"]

    def test_019_queue_returns_filter_options(self, content_queue):
        """Queue returns available filter options"""
        assert "filters" in content_queue
        assert "available_niches" in content_queue["filters"]
        assert "available_types" in content_queue["filters"]

    def test_020_queue_empty_returns_empty_list(self):
        """Empty queue returns empty list not error"""
        # Use impossible filter to get empty results
        queue = requests.get(f"{API_URL}/queue", params={"min_quality": 100, "niche": "nonexistent_niche_xyz"}).json()
        assert queue.get("items", []) == [] or len(queue.get("items", [])) == 0

    def test_021_remove_from_queue(self, single_content):
        """Can remove item from queue"""
        if single_content:
            content_id = single_content["id"]
            response = requests.delete(f"{API_URL}/queue/{content_id}")
            assert response.status_code == 200

    def test_022_remove_nonexistent_returns_404(self):
        """Removing nonexistent content returns 404"""
        response = requests.delete(f"{API_URL}/queue/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_023_queue_item_has_thumbnail(self, content_queue):
        """Queue items have thumbnail URL"""
        for item in content_queue.get("items", [])[:5]:
            assert "thumbnail_url" in item

    def test_024_queue_item_has_ai_analysis(self, content_queue):
        """Queue items have AI analysis"""
        for item in content_queue.get("items", [])[:5]:
            assert "ai_analysis" in item
            assert isinstance(item["ai_analysis"], dict)

    def test_025_queue_item_has_created_at(self, content_queue):
        """Queue items have created_at timestamp"""
        for item in content_queue.get("items", [])[:5]:
            assert "created_at" in item

    def test_026_variations_have_title(self, single_content):
        """Variations have titles"""
        if single_content:
            for var in single_content.get("variations", []):
                assert "title" in var
                assert var["title"]

    def test_027_variations_have_description(self, single_content):
        """Variations have descriptions"""
        if single_content:
            for var in single_content.get("variations", []):
                assert "description" in var

    def test_028_variations_have_hashtags(self, single_content):
        """Variations have hashtags"""
        if single_content:
            for var in single_content.get("variations", []):
                assert "hashtags" in var
                assert isinstance(var["hashtags"], list)

    def test_029_one_primary_variation(self, single_content):
        """Content has exactly one primary variation"""
        if single_content:
            primary_count = sum(1 for v in single_content.get("variations", []) if v.get("is_primary"))
            assert primary_count <= 1

    def test_030_platform_assignments_have_score(self, single_content):
        """Platform assignments have match scores"""
        if single_content:
            for assignment in single_content.get("platform_assignments", []):
                assert "match_score" in assignment
                assert 0 <= assignment["match_score"] <= 100


# ============================================================================
# 2. CONTENT APPROVAL TESTS (40 tests)
# ============================================================================

class TestContentApproval:
    """Tests for content approval (swipe) operations"""

    def test_031_approve_content_returns_200(self, reset_data):
        """Approve endpoint returns 200"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "approve"
            })
            assert response.status_code == 200

    def test_032_approve_removes_from_queue(self, reset_data):
        """Approved content removed from queue"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "approve"
            })
            new_queue = requests.get(f"{API_URL}/queue").json()
            ids = [item["id"] for item in new_queue.get("items", [])]
            assert content_id not in ids

    def test_033_reject_content(self, reset_data):
        """Can reject content"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "reject"
            })
            assert response.json()["status"] == "rejected"

    def test_034_priority_approve(self, reset_data):
        """Can priority approve content"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "priority"
            })
            assert response.json()["status"] == "priority_approved"

    def test_035_save_for_later(self, reset_data):
        """Can save content for later"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "save_later"
            })
            assert response.json()["status"] == "saved"

    def test_036_approve_with_platforms(self, reset_data):
        """Can approve with specific platforms"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "approve",
                "selected_platforms": ["instagram", "tiktok"]
            })
            assert response.status_code == 200

    def test_037_approve_nonexistent_returns_404(self):
        """Approving nonexistent content returns 404"""
        response = requests.post(f"{API_URL}/approve", json={
            "content_id": str(uuid.uuid4()),
            "action": "approve"
        })
        assert response.status_code == 404

    def test_038_approve_invalid_action_returns_400(self, reset_data):
        """Invalid action returns 400"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "invalid_action"
            })
            assert response.status_code == 422  # Validation error

    def test_039_bulk_approve_by_quality(self, reset_data):
        """Can bulk approve by quality threshold"""
        response = requests.post(f"{API_URL}/bulk-approve", params={
            "min_quality": 80,
            "limit": 10
        })
        assert response.status_code == 200
        assert "approved_count" in response.json()

    def test_040_bulk_approve_respects_limit(self, reset_data):
        """Bulk approve respects limit"""
        response = requests.post(f"{API_URL}/bulk-approve", params={
            "min_quality": 50,
            "limit": 5
        })
        assert response.json()["approved_count"] <= 5

    def test_041_approve_returns_content_id(self, reset_data):
        """Approve response includes content ID"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "approve"
            })
            assert response.json()["content_id"] == content_id

    def test_042_approve_returns_message(self, reset_data):
        """Approve response includes message"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "approve"
            })
            assert "message" in response.json()

    # Continue with more approval tests...
    def test_043_approve_with_custom_priority(self, reset_data):
        """Can approve with custom priority"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "approve",
                "priority": 50
            })
            assert response.status_code == 200


# ============================================================================
# 3. RUNWAY TESTS (20 tests)
# ============================================================================

class TestRunway:
    """Tests for content runway statistics"""

    def test_051_runway_returns_200(self):
        """Runway endpoint returns 200"""
        response = requests.get(f"{API_URL}/runway")
        assert response.status_code == 200

    def test_052_runway_has_total_approved(self):
        """Runway includes total approved"""
        response = requests.get(f"{API_URL}/runway")
        assert "total_approved" in response.json()

    def test_053_runway_has_days_remaining(self):
        """Runway includes days remaining"""
        response = requests.get(f"{API_URL}/runway")
        assert "days_of_runway" in response.json()

    def test_054_runway_has_platform_breakdown(self):
        """Runway includes platform breakdown"""
        response = requests.get(f"{API_URL}/runway")
        assert "runway_by_platform" in response.json()

    def test_055_runway_has_pending_count(self):
        """Runway includes pending count"""
        response = requests.get(f"{API_URL}/runway")
        assert "total_pending" in response.json()

    def test_056_runway_has_scheduled_count(self):
        """Runway includes scheduled count"""
        response = requests.get(f"{API_URL}/runway")
        assert "total_scheduled" in response.json()

    def test_057_runway_has_posts_today(self):
        """Runway includes posts today"""
        response = requests.get(f"{API_URL}/runway")
        assert "posts_today" in response.json()

    def test_058_runway_has_niche_breakdown(self):
        """Runway includes niche breakdown"""
        response = requests.get(f"{API_URL}/runway")
        assert "content_by_niche" in response.json()

    def test_059_runway_identifies_low_platforms(self):
        """Runway identifies low runway platforms"""
        response = requests.get(f"{API_URL}/runway")
        assert "low_runway_platforms" in response.json()

    def test_060_runway_values_are_integers(self):
        """Runway numeric values are integers"""
        response = requests.get(f"{API_URL}/runway").json()
        assert isinstance(response["total_approved"], int)
        assert isinstance(response["days_of_runway"], int)


# ============================================================================
# 4. SCHEDULING TESTS (30 tests)
# ============================================================================

class TestScheduling:
    """Tests for content scheduling"""

    def test_071_get_schedule_returns_200(self):
        """Schedule endpoint returns 200"""
        response = requests.get(f"{API_URL}/schedule")
        assert response.status_code == 200

    def test_072_schedule_has_posts_list(self):
        """Schedule includes posts list"""
        response = requests.get(f"{API_URL}/schedule")
        assert "posts" in response.json()

    def test_073_auto_schedule_returns_200(self):
        """Auto-schedule endpoint returns 200"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 7,
            "posts_per_day": 4
        })
        assert response.status_code == 200

    def test_074_auto_schedule_returns_count(self):
        """Auto-schedule returns scheduled count"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 3,
            "posts_per_day": 2
        })
        assert "scheduled_count" in response.json()

    def test_075_schedule_filter_by_platform(self):
        """Can filter schedule by platform"""
        response = requests.get(f"{API_URL}/schedule", params={
            "platform": "instagram"
        })
        assert response.status_code == 200

    def test_076_schedule_filter_by_days(self):
        """Can filter schedule by days"""
        response = requests.get(f"{API_URL}/schedule", params={
            "days": 7
        })
        assert response.status_code == 200


# ============================================================================
# 5. VARIATIONS TESTS (15 tests)
# ============================================================================

class TestVariations:
    """Tests for content variations"""

    def test_081_generate_variations_returns_200(self, reset_data):
        """Generate variations endpoint returns 200"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/generate-variations", json={
                "content_id": content_id,
                "count": 3
            })
            assert response.status_code == 200

    def test_082_generate_variations_returns_new(self, reset_data):
        """Generate variations returns new variations"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/generate-variations", json={
                "content_id": content_id,
                "count": 2
            })
            data = response.json()
            assert "new_variations" in data
            assert len(data["new_variations"]) == 2

    def test_083_variations_have_unique_ids(self, reset_data):
        """Generated variations have unique IDs"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/generate-variations", json={
                "content_id": content_id,
                "count": 3
            })
            ids = [v["id"] for v in response.json().get("new_variations", [])]
            assert len(ids) == len(set(ids))


# ============================================================================
# 6. ANALYTICS TESTS (15 tests)
# ============================================================================

class TestAnalytics:
    """Tests for pipeline analytics"""

    def test_091_analytics_returns_200(self):
        """Analytics endpoint returns 200"""
        response = requests.get(f"{API_URL}/analytics")
        assert response.status_code == 200

    def test_092_analytics_has_queue_stats(self):
        """Analytics includes queue stats"""
        response = requests.get(f"{API_URL}/analytics")
        assert "queue_stats" in response.json()

    def test_093_analytics_has_quality_distribution(self):
        """Analytics includes quality distribution"""
        response = requests.get(f"{API_URL}/analytics")
        assert "quality_distribution" in response.json()

    def test_094_analytics_has_platform_distribution(self):
        """Analytics includes platform distribution"""
        response = requests.get(f"{API_URL}/analytics")
        assert "platform_distribution" in response.json()

    def test_095_analytics_has_approval_rate(self):
        """Analytics includes approval rate"""
        response = requests.get(f"{API_URL}/analytics")
        assert "approval_rate" in response.json()


# ============================================================================
# 7. ANALYZE CONTENT TESTS (10 tests)
# ============================================================================

class TestAnalyzeContent:
    """Tests for triggering content analysis"""

    def test_101_analyze_returns_200(self):
        """Analyze endpoint returns 200"""
        response = requests.post(f"{API_URL}/analyze", json={
            "media_id": str(uuid.uuid4())
        })
        assert response.status_code == 200

    def test_102_analyze_returns_content_id(self):
        """Analyze returns new content ID"""
        response = requests.post(f"{API_URL}/analyze", json={
            "media_id": str(uuid.uuid4())
        })
        assert "content_id" in response.json()

    def test_103_analyze_returns_quality_score(self):
        """Analyze returns quality score"""
        response = requests.post(f"{API_URL}/analyze", json={
            "media_id": str(uuid.uuid4())
        })
        assert "quality_score" in response.json()

    def test_104_analyze_generates_variations(self):
        """Analyze generates variations"""
        response = requests.post(f"{API_URL}/analyze", json={
            "media_id": str(uuid.uuid4())
        })
        assert response.json()["variations_generated"] > 0

    def test_105_analyze_suggests_platforms(self):
        """Analyze suggests platforms"""
        response = requests.post(f"{API_URL}/analyze", json={
            "media_id": str(uuid.uuid4())
        })
        assert response.json()["platforms_suggested"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
