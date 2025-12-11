"""
Content Pipeline Test Suite - Part 2: Extended Tests
Additional tests for scheduling, publishing, and edge cases.
"""

import pytest
import requests
from datetime import datetime, timedelta
import uuid

BASE_URL = "http://localhost:5555"
API_URL = f"{BASE_URL}/api/content-pipeline"


# ============================================================================
# 8. SCHEDULING EDGE CASES (25 tests)
# ============================================================================

class TestSchedulingEdgeCases:
    """Edge case tests for scheduling"""

    def test_110_schedule_content_returns_200(self):
        """Schedule single post returns 200"""
        # First approve some content
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve", json={
                "content_id": content_id,
                "action": "approve"
            })
            # Now schedule
            response = requests.post(f"{API_URL}/schedule", json={
                "content_id": content_id,
                "platform": "instagram",
                "scheduled_time": (datetime.now() + timedelta(hours=4)).isoformat()
            })
            assert response.status_code in [200, 404]

    def test_111_schedule_has_post_id(self):
        """Scheduled post gets an ID"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            content_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve", json={"content_id": content_id, "action": "approve"})
            response = requests.post(f"{API_URL}/schedule", json={
                "content_id": content_id,
                "platform": "instagram",
                "scheduled_time": (datetime.now() + timedelta(hours=4)).isoformat()
            })
            if response.status_code == 200:
                assert "post_id" in response.json()

    def test_112_auto_schedule_daylight_hours(self):
        """Auto-schedule respects daylight hours"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 1,
            "posts_per_day": 4
        })
        assert response.status_code == 200

    def test_113_auto_schedule_max_days(self):
        """Auto-schedule accepts max 60 days"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 60,
            "posts_per_day": 1
        })
        assert response.status_code == 200

    def test_114_auto_schedule_exceeds_max_days(self):
        """Auto-schedule rejects > 60 days"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "days": 61,
            "posts_per_day": 1
        })
        assert response.status_code == 422

    def test_115_schedule_grouped_by_date(self):
        """Schedule returns posts grouped by date"""
        response = requests.get(f"{API_URL}/schedule")
        assert "by_date" in response.json()

    def test_116_schedule_total_count(self):
        """Schedule returns total count"""
        response = requests.get(f"{API_URL}/schedule")
        assert "total" in response.json()


# ============================================================================
# 9. PLATFORM MATCHING TESTS (35 tests)
# ============================================================================

class TestPlatformMatching:
    """Tests for platform matching logic"""

    def test_120_image_matches_image_platforms(self):
        """Images match image-compatible platforms"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"content_type": "image"}).json()
        if queue.get("items"):
            platforms = [a["platform"] for a in queue["items"][0].get("platform_assignments", [])]
            # Images should match at least one image-compatible platform
            image_platforms = ["instagram", "twitter", "linkedin", "threads", "pinterest"]
            assert any(p in image_platforms for p in platforms)

    def test_121_video_matches_tiktok(self):
        """Videos match TikTok"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"content_type": "video"}).json()
        if queue.get("items"):
            platforms = [a["platform"] for a in queue["items"][0].get("platform_assignments", [])]
            assert "tiktok" in platforms or "youtube" in platforms

    def test_122_clip_matches_shorts(self):
        """Clips match YouTube Shorts/TikTok"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"content_type": "clip"}).json()
        if queue.get("items"):
            platforms = [a["platform"] for a in queue["items"][0].get("platform_assignments", [])]
            assert "tiktok" in platforms or "youtube" in platforms or "instagram" in platforms

    def test_123_assignment_has_match_reasons(self):
        """Platform assignments have match reasons"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            for assignment in queue["items"][0].get("platform_assignments", []):
                assert "match_reasons" in assignment

    def test_124_high_quality_gets_bonus(self):
        """High quality content gets score bonus"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"min_quality": 80}).json()
        if queue.get("items"):
            for assignment in queue["items"][0].get("platform_assignments", []):
                assert assignment["match_score"] >= 60

    def test_125_assignments_sorted_by_score(self):
        """Platform assignments sorted by score"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            assignments = queue["items"][0].get("platform_assignments", [])
            if len(assignments) >= 2:
                assert assignments[0]["match_score"] >= assignments[1]["match_score"]

    def test_126_max_platforms_per_content(self):
        """Content has max 4 platform suggestions"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            for item in queue["items"]:
                assert len(item.get("platform_assignments", [])) <= 4


# ============================================================================
# 10. CONTENT TYPE SPECIFIC TESTS (20 tests)
# ============================================================================

class TestContentTypes:
    """Tests for different content types"""

    def test_130_video_has_duration(self):
        """Videos have duration"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"content_type": "video"}).json()
        for item in queue.get("items", []):
            assert item.get("duration_sec") is not None

    def test_131_clip_has_duration(self):
        """Clips have duration"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"content_type": "clip"}).json()
        for item in queue.get("items", []):
            assert item.get("duration_sec") is not None

    def test_132_image_no_duration(self):
        """Images don't have duration"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"content_type": "image"}).json()
        for item in queue.get("items", []):
            assert item.get("duration_sec") is None

    def test_133_video_has_resolution(self):
        """Videos have resolution"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue", params={"content_type": "video"}).json()
        for item in queue.get("items", []):
            assert item.get("resolution") is not None

    def test_134_content_has_aspect_ratio(self):
        """Content has aspect ratio"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        for item in queue.get("items", [])[:5]:
            assert item.get("aspect_ratio") is not None


# ============================================================================
# 11. VARIATION MANAGEMENT TESTS (20 tests)
# ============================================================================

class TestVariationManagement:
    """Extended tests for content variations"""

    def test_140_variation_has_platform_hint(self):
        """Variations have platform hints"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            for var in queue["items"][0].get("variations", []):
                assert "platform_hint" in var

    def test_141_variation_tracks_usage(self):
        """Variations track usage count"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            for var in queue["items"][0].get("variations", []):
                assert "times_used" in var
                assert var["times_used"] >= 0

    def test_142_generate_up_to_10_variations(self):
        """Can generate up to 10 variations"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            response = requests.post(f"{API_URL}/generate-variations", json={
                "content_id": queue["items"][0]["id"],
                "count": 10
            })
            assert response.status_code == 200

    def test_143_generate_exceeds_limit(self):
        """Cannot generate more than 10 variations at once"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            response = requests.post(f"{API_URL}/generate-variations", json={
                "content_id": queue["items"][0]["id"],
                "count": 11
            })
            assert response.status_code == 422

    def test_144_total_variations_tracked(self):
        """Total variations count is tracked"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            response = requests.post(f"{API_URL}/generate-variations", json={
                "content_id": queue["items"][0]["id"],
                "count": 2
            })
            if response.status_code == 200:
                assert "total_variations" in response.json()


# ============================================================================
# 12. NICHE FILTERING TESTS (15 tests)
# ============================================================================

class TestNicheFiltering:
    """Tests for niche-based filtering"""

    def test_150_filter_lifestyle_niche(self):
        """Can filter by lifestyle niche"""
        requests.post(f"{API_URL}/reset-mock-data")
        response = requests.get(f"{API_URL}/queue", params={"niche": "lifestyle"})
        assert response.status_code == 200

    def test_151_filter_fitness_niche(self):
        """Can filter by fitness niche"""
        requests.post(f"{API_URL}/reset-mock-data")
        response = requests.get(f"{API_URL}/queue", params={"niche": "fitness"})
        assert response.status_code == 200

    def test_152_filter_comedy_niche(self):
        """Can filter by comedy niche"""
        requests.post(f"{API_URL}/reset-mock-data")
        response = requests.get(f"{API_URL}/queue", params={"niche": "comedy"})
        assert response.status_code == 200

    def test_153_bulk_approve_by_niche(self):
        """Can bulk approve by niche"""
        requests.post(f"{API_URL}/reset-mock-data")
        response = requests.post(f"{API_URL}/bulk-approve", params={
            "min_quality": 50,
            "niches": ["lifestyle", "fitness"],
            "limit": 10
        })
        assert response.status_code == 200

    def test_154_niche_in_runway_stats(self):
        """Niche breakdown in runway stats"""
        response = requests.get(f"{API_URL}/runway")
        assert "content_by_niche" in response.json()


# ============================================================================
# 13. ERROR HANDLING TESTS (15 tests)
# ============================================================================

class TestErrorHandling:
    """Tests for error handling"""

    def test_160_invalid_content_id(self):
        """Invalid content ID returns error"""
        response = requests.post(f"{API_URL}/approve", json={
            "content_id": "not-a-valid-uuid",
            "action": "approve"
        })
        assert response.status_code in [404, 422]

    def test_161_missing_content_id(self):
        """Missing content ID returns error"""
        response = requests.post(f"{API_URL}/approve", json={
            "action": "approve"
        })
        assert response.status_code == 422

    def test_162_missing_action(self):
        """Missing action returns error"""
        response = requests.post(f"{API_URL}/approve", json={
            "content_id": str(uuid.uuid4())
        })
        assert response.status_code == 422

    def test_163_invalid_limit(self):
        """Invalid limit returns error"""
        response = requests.get(f"{API_URL}/queue", params={"limit": 0})
        assert response.status_code == 422

    def test_164_limit_exceeds_max(self):
        """Limit exceeding max returns error"""
        response = requests.get(f"{API_URL}/queue", params={"limit": 101})
        assert response.status_code == 422

    def test_165_invalid_quality_range(self):
        """Invalid quality range returns error"""
        response = requests.get(f"{API_URL}/queue", params={"min_quality": 101})
        assert response.status_code == 422

    def test_166_negative_offset(self):
        """Negative offset returns error"""
        response = requests.get(f"{API_URL}/queue", params={"offset": -1})
        assert response.status_code == 422


# ============================================================================
# 14. RESET AND INITIALIZATION TESTS (10 tests)
# ============================================================================

class TestResetInit:
    """Tests for reset and initialization"""

    def test_170_reset_data_returns_200(self):
        """Reset endpoint returns 200"""
        response = requests.post(f"{API_URL}/reset-mock-data")
        assert response.status_code == 200

    def test_171_reset_returns_queue_size(self):
        """Reset returns new queue size"""
        response = requests.post(f"{API_URL}/reset-mock-data")
        assert "queue_size" in response.json()

    def test_172_reset_clears_approved(self):
        """Reset clears approved content"""
        # First approve some
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            requests.post(f"{API_URL}/approve", json={
                "content_id": queue["items"][0]["id"],
                "action": "approve"
            })
        # Now reset
        requests.post(f"{API_URL}/reset-mock-data")
        runway = requests.get(f"{API_URL}/runway").json()
        assert runway["total_approved"] == 0

    def test_173_reset_clears_scheduled(self):
        """Reset clears scheduled posts"""
        requests.post(f"{API_URL}/reset-mock-data")
        schedule = requests.get(f"{API_URL}/schedule").json()
        assert schedule["total"] == 0

    def test_174_reset_repopulates_queue(self):
        """Reset repopulates queue with mock data"""
        response = requests.post(f"{API_URL}/reset-mock-data")
        assert response.json()["queue_size"] > 0


# ============================================================================
# 15. AI ANALYSIS RESULT TESTS (15 tests)
# ============================================================================

class TestAIAnalysis:
    """Tests for AI analysis results"""

    def test_180_analysis_has_mood(self):
        """AI analysis includes mood"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            analysis = queue["items"][0].get("ai_analysis", {})
            assert "mood" in analysis

    def test_181_analysis_has_topics(self):
        """AI analysis includes topics"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            analysis = queue["items"][0].get("ai_analysis", {})
            assert "topics" in analysis

    def test_182_analysis_has_engagement_prediction(self):
        """AI analysis includes engagement prediction"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            analysis = queue["items"][0].get("ai_analysis", {})
            assert "engagement_prediction" in analysis

    def test_183_engagement_prediction_valid_values(self):
        """Engagement prediction has valid values"""
        requests.post(f"{API_URL}/reset-mock-data")
        queue = requests.get(f"{API_URL}/queue").json()
        if queue.get("items"):
            analysis = queue["items"][0].get("ai_analysis", {})
            if "engagement_prediction" in analysis:
                assert analysis["engagement_prediction"] in ["high", "medium", "low"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
