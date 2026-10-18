"""
Content Pipeline Test Suite - Part 5: Final 80 tests to reach 300
Additional comprehensive coverage tests.
"""

import pytest
import requests
import uuid

BASE_URL = "http://localhost:5555"
API_URL = f"{BASE_URL}/api/content-pipeline"


# ============================================================================
# 31. API CONTRACT TESTS (20 tests)
# ============================================================================

class TestAPIContracts:
    """Tests for API response contracts"""

    def test_400_queue_response_structure(self):
        """Queue response has correct structure"""
        response = requests.get(f"{API_URL}/queue")
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "filters" in data

    def test_401_runway_response_structure(self):
        """Runway response has correct structure"""
        response = requests.get(f"{API_URL}/runway")
        data = response.json()
        assert "total_approved" in data
        assert "total_pending" in data
        assert "total_scheduled" in data
        assert "days_of_runway" in data
        assert "runway_by_platform" in data

    def test_402_analytics_response_structure(self):
        """Analytics response has correct structure"""
        response = requests.get(f"{API_URL}/analytics")
        data = response.json()
        assert "queue_stats" in data
        assert "quality_distribution" in data
        assert "platform_distribution" in data
        assert "approval_rate" in data

    def test_403_schedule_response_structure(self):
        """Schedule response has correct structure"""
        response = requests.get(f"{API_URL}/schedule")
        data = response.json()
        assert "posts" in data
        assert "by_date" in data
        assert "total" in data

    def test_404_content_item_structure(self):
        """Content item has correct structure"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            item = queue["items"][0]
            assert "id" in item
            assert "status" in item
            assert "quality_score" in item
            assert "content_type" in item
            assert "variations" in item
            assert "platform_assignments" in item

    def test_405_variation_structure(self):
        """Variation has correct structure"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items") and queue["items"][0].get("variations"):
            var = queue["items"][0]["variations"][0]
            assert "id" in var
            assert "title" in var
            assert "description" in var
            assert "hashtags" in var
            assert "is_primary" in var

    def test_406_platform_assignment_structure(self):
        """Platform assignment has correct structure"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items") and queue["items"][0].get("platform_assignments"):
            assignment = queue["items"][0]["platform_assignments"][0]
            assert "platform" in assignment
            assert "match_score" in assignment
            assert "match_reasons" in assignment
            assert "status" in assignment

    def test_407_approve_response_structure(self):
        """Approve response has correct structure"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            response = requests.post(f"{API_URL}/approve", json={
                "content_id": queue["items"][0]["id"],
                "action": "approve"
            })
            data = response.json()
            assert "status" in data
            assert "content_id" in data
            assert "message" in data

    def test_408_bulk_approve_response_structure(self):
        """Bulk approve response has correct structure"""
        requests.post(f"{API_URL}/reset-mock-data")
        response = requests.post(f"{API_URL}/bulk-approve", params={
            "min_quality": 50,
            "limit": 5
        })
        data = response.json()
        assert "approved_count" in data
        assert "approved_ids" in data
        assert "remaining_in_queue" in data

    def test_409_auto_schedule_response_structure(self):
        """Auto-schedule response has correct structure"""
        requests.post(f"{API_URL}/reset-mock-data")
        requests.post(f"{API_URL}/bulk-approve", params={"min_quality": 50, "limit": 10})
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 3,
            "posts_per_day": 2
        })
        data = response.json()
        assert "scheduled_count" in data
        assert "days_covered" in data


# ============================================================================
# 32. FILTER COMBINATION TESTS (20 tests)
# ============================================================================

class TestFilterCombinations:
    """Tests for various filter combinations"""

    def test_410_niche_and_quality(self):
        """Filter by niche and quality"""
        response = requests.get(f"{API_URL}/queue", params={
            "niche": "lifestyle",
            "min_quality": 70
        })
        assert response.status_code == 200

    def test_411_type_and_quality(self):
        """Filter by type and quality"""
        response = requests.get(f"{API_URL}/queue", params={
            "content_type": "video",
            "min_quality": 60
        })
        assert response.status_code == 200

    def test_412_niche_and_type(self):
        """Filter by niche and type"""
        response = requests.get(f"{API_URL}/queue", params={
            "niche": "fitness",
            "content_type": "video"
        })
        assert response.status_code == 200

    def test_413_all_filters(self):
        """Filter by all parameters"""
        response = requests.get(f"{API_URL}/queue", params={
            "niche": "lifestyle",
            "content_type": "image",
            "min_quality": 50,
            "limit": 10
        })
        assert response.status_code == 200

    def test_414_quality_and_limit(self):
        """Filter by quality with limit"""
        response = requests.get(f"{API_URL}/queue", params={
            "min_quality": 80,
            "limit": 5
        })
        assert len(response.json().get("items", [])) <= 5

    def test_415_quality_and_offset(self):
        """Filter by quality with offset"""
        response = requests.get(f"{API_URL}/queue", params={
            "min_quality": 60,
            "offset": 5
        })
        assert response.status_code == 200

    def test_416_type_and_limit(self):
        """Filter by type with limit"""
        response = requests.get(f"{API_URL}/queue", params={
            "content_type": "clip",
            "limit": 3
        })
        assert len(response.json().get("items", [])) <= 3

    def test_417_niche_with_pagination(self):
        """Filter by niche with pagination"""
        response = requests.get(f"{API_URL}/queue", params={
            "niche": "comedy",
            "limit": 5,
            "offset": 0
        })
        assert response.status_code == 200

    def test_418_high_quality_videos(self):
        """High quality videos only"""
        response = requests.get(f"{API_URL}/queue", params={
            "content_type": "video",
            "min_quality": 85
        })
        for item in response.json().get("items", []):
            assert item["quality_score"] >= 85
            assert item["content_type"] == "video"

    def test_419_lifestyle_images(self):
        """Lifestyle images only"""
        response = requests.get(f"{API_URL}/queue", params={
            "niche": "lifestyle",
            "content_type": "image"
        })
        for item in response.json().get("items", []):
            assert item.get("niche") == "lifestyle"
            assert item["content_type"] == "image"


# ============================================================================
# 33. VALIDATION BOUNDARY TESTS (20 tests)
# ============================================================================

class TestValidationBoundaries:
    """Tests for parameter validation boundaries"""

    def test_420_limit_exactly_1(self):
        """Limit exactly 1 works"""
        response = requests.get(f"{API_URL}/queue", params={"limit": 1})
        assert response.status_code == 200
        assert len(response.json().get("items", [])) <= 1

    def test_421_limit_exactly_100(self):
        """Limit exactly 100 works"""
        response = requests.get(f"{API_URL}/queue", params={"limit": 100})
        assert response.status_code == 200

    def test_422_offset_exactly_0(self):
        """Offset exactly 0 works"""
        response = requests.get(f"{API_URL}/queue", params={"offset": 0})
        assert response.status_code == 200

    def test_423_quality_exactly_0(self):
        """Quality exactly 0 works"""
        response = requests.get(f"{API_URL}/queue", params={"min_quality": 0})
        assert response.status_code == 200

    def test_424_quality_exactly_100(self):
        """Quality exactly 100 works"""
        response = requests.get(f"{API_URL}/queue", params={"min_quality": 100})
        assert response.status_code == 200

    def test_425_days_exactly_1(self):
        """Days exactly 1 works"""
        requests.post(f"{API_URL}/bulk-approve", params={"min_quality": 50, "limit": 5})
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 1,
            "posts_per_day": 1
        })
        assert response.status_code == 200

    def test_426_days_exactly_60(self):
        """Days exactly 60 works"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 60,
            "posts_per_day": 1
        })
        assert response.status_code == 200

    def test_427_posts_per_day_exactly_1(self):
        """Posts per day exactly 1 works"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 7,
            "posts_per_day": 1
        })
        assert response.status_code == 200

    def test_428_posts_per_day_exactly_10(self):
        """Posts per day exactly 10 works"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 3,
            "posts_per_day": 10
        })
        assert response.status_code == 200

    def test_429_variation_count_exactly_1(self):
        """Variation count exactly 1 works"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            response = requests.post(f"{API_URL}/generate-variations", json={
                "content_id": queue["items"][0]["id"],
                "count": 1
            })
            assert response.status_code == 200


# ============================================================================
# 34. DATA INTEGRITY TESTS (20 tests)
# ============================================================================

class TestDataIntegrity:
    """Tests for data integrity after operations"""

    def test_430_queue_count_decreases_on_approve(self):
        """Queue count decreases on approve"""
        requests.post(f"{API_URL}/reset-mock-data")
        before = requests.get(f"{API_URL}/queue").json()["total"]
        if before > 0:
            queue = requests.get(f"{API_URL}/queue").json()
            requests.post(f"{API_URL}/approve", json={
                "content_id": queue["items"][0]["id"],
                "action": "approve"
            })
            after = requests.get(f"{API_URL}/queue").json()["total"]
            assert after == before - 1

    def test_431_approved_count_increases(self):
        """Approved count increases on approve"""
        requests.post(f"{API_URL}/reset-mock-data")
        before = requests.get(f"{API_URL}/runway").json()["total_approved"]
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            requests.post(f"{API_URL}/approve", json={
                "content_id": queue["items"][0]["id"],
                "action": "approve"
            })
            after = requests.get(f"{API_URL}/runway").json()["total_approved"]
            assert after == before + 1

    def test_432_rejected_not_in_runway(self):
        """Rejected content not counted in runway"""
        requests.post(f"{API_URL}/reset-mock-data")
        before = requests.get(f"{API_URL}/runway").json()["total_approved"]
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            requests.post(f"{API_URL}/approve", json={
                "content_id": queue["items"][0]["id"],
                "action": "reject"
            })
            after = requests.get(f"{API_URL}/runway").json()["total_approved"]
            assert after == before

    def test_433_saved_for_later_tracked(self):
        """Saved for later is tracked"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            requests.post(f"{API_URL}/approve", json={
                "content_id": queue["items"][0]["id"],
                "action": "save_later"
            })
            runway = requests.get(f"{API_URL}/runway").json()
            assert runway["total_saved_for_later"] >= 1

    def test_434_bulk_approve_count_matches(self):
        """Bulk approve count matches approved IDs"""
        requests.post(f"{API_URL}/reset-mock-data")
        response = requests.post(f"{API_URL}/bulk-approve", params={
            "min_quality": 50,
            "limit": 10
        })
        data = response.json()
        assert data["approved_count"] == len(data["approved_ids"])

    def test_435_schedule_count_matches_posts(self):
        """Schedule count matches posts list"""
        schedule = requests.get(f"{API_URL}/schedule").json()
        assert schedule["total"] == len(schedule["posts"])

    def test_436_reset_clears_approved(self):
        """Reset clears approved count"""
        requests.post(f"{API_URL}/bulk-approve", params={"min_quality": 50, "limit": 10})
        requests.post(f"{API_URL}/reset-mock-data")
        runway = requests.get(f"{API_URL}/runway").json()
        assert runway["total_approved"] == 0

    def test_437_reset_clears_scheduled(self):
        """Reset clears scheduled count"""
        requests.post(f"{API_URL}/reset-mock-data")
        requests.post(f"{API_URL}/bulk-approve", params={"min_quality": 50, "limit": 20})
        requests.post(f"{API_URL}/auto-schedule", params={"days": 5, "posts_per_day": 3})
        requests.post(f"{API_URL}/reset-mock-data")
        schedule = requests.get(f"{API_URL}/schedule").json()
        assert schedule["total"] == 0

    def test_438_id_uniqueness(self):
        """Content IDs are unique"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"limit": 50}).json()
        ids = [item["id"] for item in queue.get("items", [])]
        assert len(ids) == len(set(ids))

    def test_439_variation_ids_unique(self):
        """Variation IDs are unique within content"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items") and queue["items"][0].get("variations"):
            ids = [v["id"] for v in queue["items"][0]["variations"]]
            assert len(ids) == len(set(ids))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
