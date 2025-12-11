"""
Comment Automation Test Suite
Tests for automated comment engagement across TikTok, YouTube, and Instagram.
"""

import pytest
import requests
from datetime import datetime

BASE_URL = "http://localhost:5555"
API_URL = f"{BASE_URL}/api/comment-automation"


# ============================================================================
# 1. CONFIGURATION TESTS (25 tests)
# ============================================================================

class TestConfiguration:
    """Tests for configuration endpoints"""

    def test_001_get_config_returns_200(self):
        """Get config returns 200"""
        response = requests.get(f"{API_URL}/config")
        assert response.status_code == 200

    def test_002_config_has_daily_limit(self):
        """Config has daily_limit field"""
        response = requests.get(f"{API_URL}/config")
        assert "daily_limit" in response.json()

    def test_003_config_has_per_niche_limit(self):
        """Config has per_niche_limit"""
        response = requests.get(f"{API_URL}/config")
        assert "per_niche_limit" in response.json()

    def test_004_config_has_automation_mode(self):
        """Config has automation_mode"""
        response = requests.get(f"{API_URL}/config")
        assert "automation_mode" in response.json()

    def test_005_config_has_interval_settings(self):
        """Config has interval settings"""
        data = requests.get(f"{API_URL}/config").json()
        assert "min_interval_minutes" in data
        assert "max_interval_minutes" in data

    def test_006_config_has_jitter(self):
        """Config has jitter_percent"""
        data = requests.get(f"{API_URL}/config").json()
        assert "jitter_percent" in data

    def test_007_config_has_active_hours(self):
        """Config has active hours"""
        data = requests.get(f"{API_URL}/config").json()
        assert "active_hours_start" in data
        assert "active_hours_end" in data

    def test_008_update_config(self):
        """Can update config"""
        response = requests.put(f"{API_URL}/config", json={
            "daily_limit": 100,
            "per_niche_limit": 20,
            "per_platform_limit": 40,
            "min_interval_minutes": 20,
            "max_interval_minutes": 90,
            "jitter_percent": 25,
            "active_hours_start": 9,
            "active_hours_end": 21,
            "automation_mode": "semi_auto"
        })
        assert response.status_code == 200
        assert response.json()["daily_limit"] == 100

    def test_009_get_niche_configs(self):
        """Get niche configs returns list"""
        response = requests.get(f"{API_URL}/config/niches")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_010_niche_config_has_fields(self):
        """Niche config has required fields"""
        response = requests.get(f"{API_URL}/config/niches")
        if response.json():
            config = response.json()[0]
            assert "niche" in config
            assert "daily_limit" in config
            assert "priority" in config
            assert "tone" in config

    def test_011_get_specific_niche(self):
        """Get specific niche config"""
        response = requests.get(f"{API_URL}/config/niche/fitness")
        assert response.status_code in [200, 404]

    def test_012_update_niche_config(self):
        """Update niche config"""
        response = requests.put(f"{API_URL}/config/niche/gaming", json={
            "niche": "gaming",
            "daily_limit": 15,
            "priority": "high",
            "tone": "casual gamer",
            "keywords": ["gaming", "videogames"],
            "exclude_keywords": ["gambling"],
            "enabled": True
        })
        assert response.status_code == 200

    def test_013_delete_niche_config(self):
        """Delete niche config"""
        # Create first
        requests.put(f"{API_URL}/config/niche/test_delete", json={
            "niche": "test_delete",
            "daily_limit": 5,
            "priority": "low",
            "tone": "test"
        })
        response = requests.delete(f"{API_URL}/config/niche/test_delete")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_014_get_platform_configs(self):
        """Get platform configs"""
        response = requests.get(f"{API_URL}/config/platforms")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_015_platform_config_has_fields(self):
        """Platform config has required fields"""
        response = requests.get(f"{API_URL}/config/platforms")
        if response.json():
            config = response.json()[0]
            assert "platform" in config
            assert "enabled" in config
            assert "daily_limit" in config

    def test_016_update_platform_config(self):
        """Update platform config"""
        response = requests.put(f"{API_URL}/config/platform/tiktok", json={
            "platform": "tiktok",
            "enabled": True,
            "daily_limit": 30,
            "target_accounts": ["@creator1", "@creator2"],
            "target_hashtags": ["fyp", "viral"],
            "include_fyp": True
        })
        assert response.status_code == 200

    def test_017_automation_mode_full_auto(self):
        """Can set full auto mode"""
        response = requests.put(f"{API_URL}/config", json={
            "daily_limit": 50,
            "automation_mode": "full_auto"
        })
        assert response.status_code == 200

    def test_018_automation_mode_semi_auto(self):
        """Can set semi auto mode"""
        response = requests.put(f"{API_URL}/config", json={
            "daily_limit": 50,
            "automation_mode": "semi_auto"
        })
        assert response.status_code == 200

    def test_019_automation_mode_manual(self):
        """Can set manual mode"""
        response = requests.put(f"{API_URL}/config", json={
            "daily_limit": 50,
            "automation_mode": "manual"
        })
        assert response.status_code == 200

    def test_020_invalid_daily_limit_rejected(self):
        """Invalid daily limit is rejected"""
        response = requests.put(f"{API_URL}/config", json={
            "daily_limit": -1
        })
        assert response.status_code == 422

    def test_021_invalid_jitter_rejected(self):
        """Invalid jitter is rejected"""
        response = requests.put(f"{API_URL}/config", json={
            "daily_limit": 50,
            "jitter_percent": 100
        })
        assert response.status_code == 422

    def test_022_niche_keywords_saved(self):
        """Niche keywords are saved"""
        requests.put(f"{API_URL}/config/niche/tech", json={
            "niche": "tech",
            "daily_limit": 10,
            "keywords": ["AI", "coding", "software"],
        })
        response = requests.get(f"{API_URL}/config/niche/tech")
        if response.status_code == 200:
            assert "AI" in response.json().get("keywords", [])

    def test_023_niche_exclude_keywords(self):
        """Niche exclude keywords saved"""
        requests.put(f"{API_URL}/config/niche/finance", json={
            "niche": "finance",
            "daily_limit": 10,
            "exclude_keywords": ["scam", "getrichquick"],
        })
        response = requests.get(f"{API_URL}/config/niche/finance")
        if response.status_code == 200:
            assert "scam" in response.json().get("exclude_keywords", [])

    def test_024_platform_target_accounts(self):
        """Platform target accounts saved"""
        requests.put(f"{API_URL}/config/platform/youtube", json={
            "platform": "youtube",
            "enabled": True,
            "target_accounts": ["@mkbhd", "@linustechtips"],
        })
        response = requests.get(f"{API_URL}/config/platforms")
        assert response.status_code == 200

    def test_025_platform_playlists_youtube(self):
        """YouTube platform supports playlists"""
        response = requests.put(f"{API_URL}/config/platform/youtube", json={
            "platform": "youtube",
            "enabled": True,
            "target_playlists": ["PLxxx123", "PLyyy456"],
        })
        assert response.status_code == 200


# ============================================================================
# 2. CONTENT DISCOVERY TESTS (15 tests)
# ============================================================================

class TestContentDiscovery:
    """Tests for target content discovery"""

    def test_030_discover_endpoint_exists(self):
        """Discover endpoint exists"""
        response = requests.post(f"{API_URL}/discover", params={
            "platform": "tiktok",
            "niche": "fitness"
        })
        assert response.status_code == 200

    def test_031_discover_returns_content(self):
        """Discover returns content list"""
        response = requests.post(f"{API_URL}/discover", params={
            "platform": "tiktok",
            "niche": "fitness",
            "limit": 5
        })
        assert "content" in response.json()
        assert len(response.json()["content"]) <= 5

    def test_032_discover_tiktok(self):
        """Discover TikTok content"""
        response = requests.post(f"{API_URL}/discover", params={
            "platform": "tiktok",
            "niche": "comedy"
        })
        assert response.json()["platform"] == "tiktok"

    def test_033_discover_youtube(self):
        """Discover YouTube content"""
        response = requests.post(f"{API_URL}/discover", params={
            "platform": "youtube",
            "niche": "tech"
        })
        assert response.json()["platform"] == "youtube"

    def test_034_discover_instagram(self):
        """Discover Instagram content"""
        response = requests.post(f"{API_URL}/discover", params={
            "platform": "instagram",
            "niche": "lifestyle"
        })
        assert response.json()["platform"] == "instagram"

    def test_035_get_targets_list(self):
        """Get targets list"""
        response = requests.get(f"{API_URL}/targets")
        assert response.status_code == 200
        assert "items" in response.json()

    def test_036_targets_filter_by_platform(self):
        """Filter targets by platform"""
        response = requests.get(f"{API_URL}/targets", params={
            "platform": "tiktok"
        })
        assert response.status_code == 200

    def test_037_targets_filter_by_niche(self):
        """Filter targets by niche"""
        response = requests.get(f"{API_URL}/targets", params={
            "niche": "fitness"
        })
        assert response.status_code == 200

    def test_038_targets_pagination(self):
        """Targets support pagination"""
        response = requests.get(f"{API_URL}/targets", params={
            "limit": 5,
            "offset": 0
        })
        assert response.json()["limit"] == 5

    def test_039_target_has_content_url(self):
        """Target content has URL"""
        response = requests.get(f"{API_URL}/targets")
        if response.json()["items"]:
            assert "content_url" in response.json()["items"][0]

    def test_040_target_has_author(self):
        """Target content has author"""
        response = requests.get(f"{API_URL}/targets")
        if response.json()["items"]:
            assert "author_username" in response.json()["items"][0]

    def test_041_target_has_engagement_score(self):
        """Target has engagement score"""
        response = requests.get(f"{API_URL}/targets")
        if response.json()["items"]:
            assert "engagement_score" in response.json()["items"][0]

    def test_042_get_top_comments(self):
        """Get top comments from target"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            content_id = targets["items"][0]["id"]
            response = requests.get(f"{API_URL}/targets/{content_id}/top-comments")
            assert response.status_code == 200

    def test_043_top_comments_has_summary(self):
        """Top comments includes summary"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            content_id = targets["items"][0]["id"]
            response = requests.get(f"{API_URL}/targets/{content_id}/top-comments")
            if response.status_code == 200:
                assert "summary" in response.json()

    def test_044_discover_limit_respected(self):
        """Discover limit is respected"""
        response = requests.post(f"{API_URL}/discover", params={
            "platform": "tiktok",
            "niche": "fitness",
            "limit": 3
        })
        assert response.json()["discovered_count"] <= 3


# ============================================================================
# 3. COMMENT GENERATION TESTS (20 tests)
# ============================================================================

class TestCommentGeneration:
    """Tests for AI comment generation"""

    def test_050_generate_endpoint_exists(self):
        """Generate endpoint exists"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]]
            })
            assert response.status_code == 200

    def test_051_generate_returns_comments(self):
        """Generate returns comments"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]]
            })
            assert "comments" in response.json()

    def test_052_generated_comment_has_text(self):
        """Generated comment has text"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]]
            })
            if response.json()["comments"]:
                assert "comment_text" in response.json()["comments"][0]

    def test_053_generate_with_custom_tone(self):
        """Generate with custom tone"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]],
                "tone": "enthusiastic"
            })
            assert response.status_code == 200

    def test_054_generate_batch(self):
        """Generate batch comments"""
        response = requests.post(f"{API_URL}/generate-batch", params={
            "count": 5
        })
        assert response.status_code == 200

    def test_055_generate_batch_by_platform(self):
        """Generate batch by platform"""
        response = requests.post(f"{API_URL}/generate-batch", params={
            "platform": "tiktok",
            "count": 3
        })
        assert response.status_code == 200

    def test_056_generate_batch_by_niche(self):
        """Generate batch by niche"""
        response = requests.post(f"{API_URL}/generate-batch", params={
            "niche": "fitness",
            "count": 3
        })
        assert response.status_code == 200

    def test_057_comment_has_status(self):
        """Generated comment has status"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]]
            })
            if response.json()["comments"]:
                assert "status" in response.json()["comments"][0]

    def test_058_comment_has_source_url(self):
        """Comment has source URL"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]]
            })
            if response.json()["comments"]:
                assert "source_url" in response.json()["comments"][0]

    def test_059_comment_has_platform(self):
        """Comment has platform"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]]
            })
            if response.json()["comments"]:
                assert "platform" in response.json()["comments"][0]

    def test_060_comment_has_niche(self):
        """Comment has niche"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]]
            })
            if response.json()["comments"]:
                assert "niche" in response.json()["comments"][0]

    def test_061_comment_has_priority(self):
        """Comment has priority"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            assert "priority" in queue["items"][0]

    def test_062_generate_multiple_targets(self):
        """Generate for multiple targets"""
        targets = requests.get(f"{API_URL}/targets", params={"limit": 3}).json()
        if len(targets["items"]) >= 2:
            ids = [t["id"] for t in targets["items"][:2]]
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": ids
            })
            assert response.json()["generated_count"] >= 1

    def test_063_automation_mode_returned(self):
        """Automation mode returned in generate"""
        targets = requests.get(f"{API_URL}/targets").json()
        if targets["items"]:
            response = requests.post(f"{API_URL}/generate", json={
                "target_content_ids": [targets["items"][0]["id"]]
            })
            assert "automation_mode" in response.json()

    def test_064_comment_text_not_empty(self):
        """Comment text is not empty"""
        queue = requests.get(f"{API_URL}/queue").json()
        for comment in queue.get("items", []):
            assert len(comment.get("comment_text", "")) > 0


# ============================================================================
# 4. APPROVAL QUEUE TESTS (25 tests)
# ============================================================================

class TestApprovalQueue:
    """Tests for approval queue"""

    def test_070_get_queue(self):
        """Get approval queue"""
        response = requests.get(f"{API_URL}/queue")
        assert response.status_code == 200

    def test_071_queue_has_items(self):
        """Queue has items list"""
        response = requests.get(f"{API_URL}/queue")
        assert "items" in response.json()

    def test_072_queue_has_stats(self):
        """Queue has stats"""
        response = requests.get(f"{API_URL}/queue")
        assert "stats" in response.json()

    def test_073_queue_filter_by_status(self):
        """Filter queue by status"""
        response = requests.get(f"{API_URL}/queue", params={
            "status": "pending_review"
        })
        assert response.status_code == 200

    def test_074_queue_filter_by_platform(self):
        """Filter queue by platform"""
        response = requests.get(f"{API_URL}/queue", params={
            "platform": "tiktok"
        })
        assert response.status_code == 200

    def test_075_queue_filter_by_niche(self):
        """Filter queue by niche"""
        response = requests.get(f"{API_URL}/queue", params={
            "niche": "fitness"
        })
        assert response.status_code == 200

    def test_076_approve_comment(self):
        """Approve a comment"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve/{comment_id}")
            assert response.status_code == 200

    def test_077_approve_with_edit(self):
        """Approve with edited text"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve/{comment_id}", params={
                "edited_text": "This is my edited comment!"
            })
            if response.status_code == 200:
                assert response.json()["comment_text"] == "This is my edited comment!"

    def test_078_approve_with_schedule(self):
        """Approve with schedule time"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/approve/{comment_id}", params={
                "schedule_time": "2025-12-15T14:00:00"
            })
            if response.status_code == 200:
                assert response.json()["status"] == "scheduled"

    def test_079_bulk_approve(self):
        """Bulk approve comments"""
        queue = requests.get(f"{API_URL}/queue").json()
        if len(queue["items"]) >= 2:
            ids = [c["id"] for c in queue["items"][:2]]
            response = requests.post(f"{API_URL}/approve-bulk", json={
                "comment_ids": ids
            })
            assert response.status_code == 200
            assert response.json()["approved_count"] >= 1

    def test_080_reject_comment(self):
        """Reject a comment"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/reject/{comment_id}")
            assert response.status_code == 200
            assert response.json()["status"] == "rejected"

    def test_081_reject_with_reason(self):
        """Reject with reason"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/reject/{comment_id}", params={
                "reason": "Too generic"
            })
            assert response.status_code == 200

    def test_082_edit_comment(self):
        """Edit comment text"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/edit/{comment_id}", params={
                "new_text": "Edited comment text here"
            })
            if response.status_code == 200:
                assert response.json()["comment_text"] == "Edited comment text here"

    def test_083_queue_pagination(self):
        """Queue supports pagination"""
        response = requests.get(f"{API_URL}/queue", params={
            "limit": 5,
            "offset": 0
        })
        assert response.json()["limit"] == 5

    def test_084_approve_nonexistent_404(self):
        """Approve nonexistent returns 404"""
        response = requests.post(f"{API_URL}/approve/nonexistent-id-12345")
        assert response.status_code == 404

    def test_085_reject_nonexistent_404(self):
        """Reject nonexistent returns 404"""
        response = requests.post(f"{API_URL}/reject/nonexistent-id-12345")
        assert response.status_code == 404

    def test_086_edit_nonexistent_404(self):
        """Edit nonexistent returns 404"""
        response = requests.post(f"{API_URL}/edit/nonexistent-id-12345", params={
            "new_text": "test"
        })
        assert response.status_code == 404

    def test_087_queue_stats_counts(self):
        """Queue stats has counts"""
        stats = requests.get(f"{API_URL}/queue").json()["stats"]
        assert "pending" in stats
        assert "approved" in stats
        assert "scheduled" in stats
        assert "posted" in stats


# ============================================================================
# 5. SCHEDULING TESTS (20 tests)
# ============================================================================

class TestScheduling:
    """Tests for comment scheduling"""

    def test_090_schedule_comment(self):
        """Schedule a comment"""
        # First approve a comment
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve/{comment_id}")
            response = requests.post(f"{API_URL}/schedule/{comment_id}", params={
                "scheduled_time": "2025-12-15T14:00:00"
            })
            assert response.status_code in [200, 400]

    def test_091_auto_schedule(self):
        """Auto schedule approved comments"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "hours_ahead": 24
        })
        assert response.status_code == 200

    def test_092_auto_schedule_returns_count(self):
        """Auto schedule returns scheduled count"""
        response = requests.post(f"{API_URL}/auto-schedule", params={
            "hours_ahead": 24
        })
        assert "scheduled_count" in response.json()

    def test_093_get_schedule(self):
        """Get schedule"""
        response = requests.get(f"{API_URL}/schedule")
        assert response.status_code == 200

    def test_094_schedule_has_comments(self):
        """Schedule has comments list"""
        response = requests.get(f"{API_URL}/schedule")
        assert "comments" in response.json()

    def test_095_schedule_filter_by_platform(self):
        """Filter schedule by platform"""
        response = requests.get(f"{API_URL}/schedule", params={
            "platform": "tiktok"
        })
        assert response.status_code == 200

    def test_096_schedule_by_day(self):
        """Schedule grouped by day"""
        response = requests.get(f"{API_URL}/schedule")
        assert "by_day" in response.json()

    def test_097_schedule_total(self):
        """Schedule has total count"""
        response = requests.get(f"{API_URL}/schedule")
        assert "total_scheduled" in response.json()

    def test_098_post_comment(self):
        """Post a comment"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve/{comment_id}")
            response = requests.post(f"{API_URL}/post/{comment_id}")
            assert response.status_code == 200

    def test_099_post_returns_url(self):
        """Post returns comment URL"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve/{comment_id}")
            response = requests.post(f"{API_URL}/post/{comment_id}")
            if response.status_code == 200:
                assert "comment_url" in response.json()

    def test_100_post_updates_status(self):
        """Post updates status to posted"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve/{comment_id}")
            response = requests.post(f"{API_URL}/post/{comment_id}")
            if response.status_code == 200:
                assert response.json()["status"] == "posted"


# ============================================================================
# 6. TRACKING & ENGAGEMENT TESTS (15 tests)
# ============================================================================

class TestTracking:
    """Tests for URL tracking and engagement"""

    def test_110_get_tracking(self):
        """Get tracking data"""
        response = requests.get(f"{API_URL}/tracking")
        assert response.status_code == 200

    def test_111_tracking_has_data(self):
        """Tracking has data list"""
        response = requests.get(f"{API_URL}/tracking")
        assert "tracking_data" in response.json()

    def test_112_tracking_filter_platform(self):
        """Filter tracking by platform"""
        response = requests.get(f"{API_URL}/tracking", params={
            "platform": "tiktok"
        })
        assert response.status_code == 200

    def test_113_update_engagement(self):
        """Update engagement metrics"""
        # First post a comment
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve/{comment_id}")
            requests.post(f"{API_URL}/post/{comment_id}")
            response = requests.post(f"{API_URL}/tracking/{comment_id}/update", params={
                "likes": 10,
                "replies": 2
            })
            assert response.status_code == 200

    def test_114_engagement_has_likes(self):
        """Engagement has likes"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve/{comment_id}")
            requests.post(f"{API_URL}/post/{comment_id}")
            response = requests.post(f"{API_URL}/tracking/{comment_id}/update", params={
                "likes": 15
            })
            if response.status_code == 200:
                assert response.json()["likes"] == 15

    def test_115_engagement_has_replies(self):
        """Engagement has replies"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            requests.post(f"{API_URL}/approve/{comment_id}")
            requests.post(f"{API_URL}/post/{comment_id}")
            response = requests.post(f"{API_URL}/tracking/{comment_id}/update", params={
                "replies": 5
            })
            if response.status_code == 200:
                assert response.json()["replies"] == 5

    def test_116_engagement_profile_clicks(self):
        """Engagement has profile clicks"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/tracking/{comment_id}/update", params={
                "profile_clicks": 25
            })
            if response.status_code == 200:
                assert response.json()["profile_clicks"] == 25

    def test_117_engagement_new_followers(self):
        """Engagement has new followers"""
        queue = requests.get(f"{API_URL}/queue").json()
        if queue["items"]:
            comment_id = queue["items"][0]["id"]
            response = requests.post(f"{API_URL}/tracking/{comment_id}/update", params={
                "new_followers": 3
            })
            if response.status_code == 200:
                assert response.json()["new_followers"] == 3

    def test_118_tracking_has_source_url(self):
        """Tracking data has source URL"""
        response = requests.get(f"{API_URL}/tracking")
        for item in response.json().get("tracking_data", []):
            assert "source_url" in item

    def test_119_tracking_has_comment_url(self):
        """Tracking data has comment URL"""
        response = requests.get(f"{API_URL}/tracking")
        # Comment URL may be None if not posted
        for item in response.json().get("tracking_data", []):
            assert "comment_url" in item


# ============================================================================
# 7. IMPACT ANALYSIS TESTS (20 tests)
# ============================================================================

class TestImpactAnalysis:
    """Tests for impact analysis"""

    def test_120_get_impact(self):
        """Get impact analysis"""
        response = requests.get(f"{API_URL}/impact")
        assert response.status_code == 200

    def test_121_impact_has_total_posted(self):
        """Impact has total posted"""
        response = requests.get(f"{API_URL}/impact")
        assert "total_comments_posted" in response.json()

    def test_122_impact_has_engagement(self):
        """Impact has total engagement"""
        response = requests.get(f"{API_URL}/impact")
        assert "total_engagement" in response.json()

    def test_123_impact_has_avg_likes(self):
        """Impact has avg likes"""
        response = requests.get(f"{API_URL}/impact")
        assert "avg_likes_per_comment" in response.json()

    def test_124_impact_has_avg_replies(self):
        """Impact has avg replies"""
        response = requests.get(f"{API_URL}/impact")
        assert "avg_replies_per_comment" in response.json()

    def test_125_impact_has_profile_visits(self):
        """Impact has profile visits"""
        response = requests.get(f"{API_URL}/impact")
        assert "profile_visits" in response.json()

    def test_126_impact_has_follower_growth(self):
        """Impact has follower growth"""
        response = requests.get(f"{API_URL}/impact")
        assert "follower_growth" in response.json()

    def test_127_impact_has_reach(self):
        """Impact has reach estimate"""
        response = requests.get(f"{API_URL}/impact")
        assert "reach_estimate" in response.json()

    def test_128_impact_has_best_niche(self):
        """Impact has best performing niche"""
        response = requests.get(f"{API_URL}/impact")
        assert "best_performing_niche" in response.json()

    def test_129_impact_has_best_platform(self):
        """Impact has best performing platform"""
        response = requests.get(f"{API_URL}/impact")
        assert "best_performing_platform" in response.json()

    def test_130_impact_has_best_time(self):
        """Impact has best time of day"""
        response = requests.get(f"{API_URL}/impact")
        assert "best_time_of_day" in response.json()

    def test_131_impact_has_roi(self):
        """Impact has ROI score"""
        response = requests.get(f"{API_URL}/impact")
        assert "roi_score" in response.json()

    def test_132_impact_period_daily(self):
        """Impact supports daily period"""
        response = requests.get(f"{API_URL}/impact", params={
            "period": "daily"
        })
        assert response.json()["period"] == "daily"

    def test_133_impact_period_weekly(self):
        """Impact supports weekly period"""
        response = requests.get(f"{API_URL}/impact", params={
            "period": "weekly"
        })
        assert response.json()["period"] == "weekly"

    def test_134_impact_period_monthly(self):
        """Impact supports monthly period"""
        response = requests.get(f"{API_URL}/impact", params={
            "period": "monthly"
        })
        assert response.json()["period"] == "monthly"

    def test_135_impact_filter_platform(self):
        """Impact filter by platform"""
        response = requests.get(f"{API_URL}/impact", params={
            "platform": "tiktok"
        })
        assert response.status_code == 200

    def test_136_get_impact_breakdown(self):
        """Get impact breakdown"""
        response = requests.get(f"{API_URL}/impact/breakdown")
        assert response.status_code == 200

    def test_137_breakdown_by_platform(self):
        """Breakdown has by_platform"""
        response = requests.get(f"{API_URL}/impact/breakdown")
        assert "by_platform" in response.json()

    def test_138_breakdown_by_niche(self):
        """Breakdown has by_niche"""
        response = requests.get(f"{API_URL}/impact/breakdown")
        assert "by_niche" in response.json()

    def test_139_breakdown_total_posted(self):
        """Breakdown has total posted"""
        response = requests.get(f"{API_URL}/impact/breakdown")
        assert "total_posted" in response.json()


# ============================================================================
# 8. STATS & MONITORING TESTS (10 tests)
# ============================================================================

class TestStatsMonitoring:
    """Tests for stats and monitoring"""

    def test_140_get_stats(self):
        """Get stats"""
        response = requests.get(f"{API_URL}/stats")
        assert response.status_code == 200

    def test_141_stats_has_global_config(self):
        """Stats has global config"""
        response = requests.get(f"{API_URL}/stats")
        assert "global_config" in response.json()

    def test_142_stats_has_posted_today(self):
        """Stats has comments posted today"""
        response = requests.get(f"{API_URL}/stats")
        assert "comments_posted_today" in response.json()

    def test_143_stats_has_remaining(self):
        """Stats has remaining today"""
        response = requests.get(f"{API_URL}/stats")
        assert "remaining_today" in response.json()

    def test_144_stats_has_queue_stats(self):
        """Stats has queue stats"""
        response = requests.get(f"{API_URL}/stats")
        assert "queue_stats" in response.json()

    def test_145_stats_has_niches(self):
        """Stats has niches configured"""
        response = requests.get(f"{API_URL}/stats")
        assert "niches_configured" in response.json()

    def test_146_stats_has_platforms(self):
        """Stats has platforms enabled"""
        response = requests.get(f"{API_URL}/stats")
        assert "platforms_enabled" in response.json()

    def test_147_reset_automation(self):
        """Reset automation data"""
        response = requests.post(f"{API_URL}/reset")
        assert response.status_code == 200
        assert response.json()["status"] == "reset"

    def test_148_stats_target_count(self):
        """Stats has target content count"""
        response = requests.get(f"{API_URL}/stats")
        assert "target_content_count" in response.json()

    def test_149_last_comment_time(self):
        """Stats has last comment time"""
        response = requests.get(f"{API_URL}/stats")
        assert "last_comment_time" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
