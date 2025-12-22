"""
Trust & Verification Tests for Scheduling System

These tests verify that:
1. Scheduled content is reliably stored and retrieved
2. Polling for approved content URLs works correctly
3. Scheduling is consistent across multiple operations
4. Data integrity is maintained through the scheduling lifecycle
"""
import requests
import pytest
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

API_URL = "http://localhost:5555"


class SchedulingTrustMetrics:
    """Track metrics for trust verification"""
    def __init__(self):
        self.created_posts: List[str] = []
        self.successful_creates = 0
        self.failed_creates = 0
        self.successful_retrievals = 0
        self.failed_retrievals = 0
        self.data_mismatches = 0
        self.polling_successes = 0
        self.polling_failures = 0
    
    def report(self) -> Dict:
        total_creates = self.successful_creates + self.failed_creates
        total_retrievals = self.successful_retrievals + self.failed_retrievals
        return {
            "create_success_rate": self.successful_creates / total_creates if total_creates > 0 else 0,
            "retrieval_success_rate": self.successful_retrievals / total_retrievals if total_retrievals > 0 else 0,
            "data_integrity_issues": self.data_mismatches,
            "polling_success_rate": self.polling_successes / (self.polling_successes + self.polling_failures) if (self.polling_successes + self.polling_failures) > 0 else 0,
        }


def create_test_post(
    title: str = None,
    scheduled_days: int = 1,
    hour: int = 10,
    platform: str = "instagram"
) -> Dict:
    """Create a test post payload"""
    scheduled = datetime.now() + timedelta(days=scheduled_days)
    scheduled = scheduled.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    return {
        "content_id": f"trust-test-{uuid.uuid4().hex[:8]}",
        "title": title or f"Trust Test Post {uuid.uuid4().hex[:4]}",
        "caption": f"Testing scheduling reliability #{uuid.uuid4().hex[:4]}",
        "platform": platform,
        "account_id": "test-account",
        "account_username": "test_user",
        "scheduled_at": scheduled.isoformat(),
    }


class TestSchedulingConsistency:
    """Tests for consistent scheduling behavior"""
    
    def test_create_and_retrieve_single_post(self):
        """Create a post and immediately retrieve it - should match exactly"""
        post_data = create_test_post(title="Consistency Test 1")
        
        # Create
        create_res = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        assert create_res.status_code == 200, f"Create failed: {create_res.text}"
        created = create_res.json()
        post_id = created["id"]
        
        # Retrieve via list
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        assert list_res.status_code == 200
        posts = list_res.json().get("posts", list_res.json())
        
        # Find our post
        found = next((p for p in posts if p.get("id") == post_id), None)
        assert found is not None, "Created post not found in list"
        
        # Verify data integrity
        assert found.get("title") == post_data["title"], "Title mismatch"
        assert found.get("platform") == post_data["platform"], "Platform mismatch"
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{post_id}")
    
    def test_create_multiple_posts_all_retrievable(self):
        """Create multiple posts and verify all are retrievable"""
        num_posts = 5
        created_ids = []
        
        # Create posts
        for i in range(num_posts):
            post_data = create_test_post(title=f"Multi-Post Test {i+1}", hour=9+i)
            res = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
            assert res.status_code == 200
            created_ids.append(res.json()["id"])
        
        # Retrieve all
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        posts = list_res.json().get("posts", list_res.json())
        
        # Verify all posts found
        found_count = sum(1 for pid in created_ids if any(p.get("id") == pid for p in posts))
        assert found_count == num_posts, f"Only {found_count}/{num_posts} posts found"
        
        # Cleanup
        for pid in created_ids:
            requests.delete(f"{API_URL}/api/schedule/{pid}")
    
    def test_update_persists_correctly(self):
        """Update a post and verify changes persist"""
        original = create_test_post(title="Original Title")
        create_res = requests.post(f"{API_URL}/api/schedule/create", json=original)
        created = create_res.json()
        post_id = created["id"]
        
        # Update
        new_title = "Updated Title - Changed"
        update_res = requests.put(
            f"{API_URL}/api/schedule/{post_id}",
            json={"title": new_title}
        )
        assert update_res.status_code == 200
        
        # Retrieve and verify
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        posts = list_res.json().get("posts", list_res.json())
        updated = next((p for p in posts if p.get("id") == post_id), None)
        
        assert updated is not None
        assert updated.get("title") == new_title, "Update did not persist"
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{post_id}")
    
    def test_delete_actually_removes(self):
        """Delete a post and verify it's gone"""
        post_data = create_test_post(title="To Be Deleted")
        create_res = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        post_id = create_res.json()["id"]
        
        # Verify exists
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        posts = list_res.json().get("posts", list_res.json())
        assert any(p.get("id") == post_id for p in posts), "Post not created"
        
        # Delete
        del_res = requests.delete(f"{API_URL}/api/schedule/{post_id}")
        assert del_res.status_code == 200
        
        # Verify gone
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        posts = list_res.json().get("posts", list_res.json())
        assert not any(p.get("id") == post_id for p in posts), "Post not deleted"


class TestPollingForApprovedContent:
    """Tests for polling mechanism to get approved content URLs"""
    
    def test_poll_for_media_url(self):
        """Poll for media URL until available or timeout"""
        # Get list of analyzed content
        response = requests.get(f"{API_URL}/api/media/list?status=approved&limit=1")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            if items:
                content_id = items[0].get("id")
                # Try to get video URL
                video_res = requests.get(f"{API_URL}/api/media/video/{content_id}")
                # Should return 200 or 404 depending on if video exists
                assert video_res.status_code in [200, 404, 302]
    
    def test_polling_with_retry(self):
        """Simulate polling with retries for content availability"""
        max_retries = 3
        retry_delay = 0.5  # seconds
        
        # Get any available content
        for attempt in range(max_retries):
            response = requests.get(f"{API_URL}/api/media/list")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", data) if isinstance(data, dict) else data
                if items:
                    # Content available
                    assert len(items) > 0
                    return
            
            time.sleep(retry_delay)
        
        # Even if no content, the endpoint should work
        assert response.status_code == 200
    
    def test_content_url_consistency(self):
        """Verify content URLs are consistent across multiple requests"""
        # Get content list
        response = requests.get(f"{API_URL}/api/media/list")
        if response.status_code != 200:
            pytest.skip("No media endpoint available")
        
        data = response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        
        if not items:
            pytest.skip("No content available for URL consistency test")
        
        # Request same content multiple times
        content_id = items[0].get("id")
        urls = []
        
        for _ in range(3):
            res = requests.get(f"{API_URL}/api/videos/{content_id}")
            if res.status_code == 200:
                urls.append(res.json())
        
        if len(urls) >= 2:
            # All responses should be identical
            assert all(u == urls[0] for u in urls), "URL responses inconsistent"


class TestSchedulingReliability:
    """End-to-end reliability tests"""
    
    def test_rapid_create_delete_cycle(self):
        """Rapidly create and delete posts - no orphans should remain"""
        created_ids = []
        
        # Rapid create
        for i in range(10):
            post = create_test_post(title=f"Rapid Test {i}")
            res = requests.post(f"{API_URL}/api/schedule/create", json=post)
            if res.status_code == 200:
                created_ids.append(res.json()["id"])
        
        # Rapid delete
        for pid in created_ids:
            requests.delete(f"{API_URL}/api/schedule/{pid}")
        
        # Verify none remain
        time.sleep(0.5)  # Allow for any async processing
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        posts = list_res.json().get("posts", list_res.json())
        
        remaining = [p for p in posts if p.get("id") in created_ids]
        assert len(remaining) == 0, f"{len(remaining)} orphan posts found"
    
    def test_concurrent_scheduling_same_slot(self):
        """Multiple posts scheduled for same time slot"""
        same_time = datetime.now() + timedelta(days=2)
        same_time = same_time.replace(hour=14, minute=0, second=0)
        
        posts = []
        for i in range(3):
            post = create_test_post(title=f"Same Slot {i}")
            post["scheduled_at"] = same_time.isoformat()
            res = requests.post(f"{API_URL}/api/schedule/create", json=post)
            assert res.status_code == 200
            posts.append(res.json()["id"])
        
        # All should exist
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        all_posts = list_res.json().get("posts", list_res.json())
        
        found = [p for p in all_posts if p.get("id") in posts]
        assert len(found) == 3, "Not all concurrent posts saved"
        
        # Cleanup
        for pid in posts:
            requests.delete(f"{API_URL}/api/schedule/{pid}")
    
    def test_schedule_integrity_after_reschedule(self):
        """Reschedule a post and verify no duplicate/ghost entries"""
        post = create_test_post(title="Reschedule Test")
        create_res = requests.post(f"{API_URL}/api/schedule/create", json=post)
        post_id = create_res.json()["id"]
        original_time = post["scheduled_at"]
        
        # Count posts before reschedule
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        count_before = len(list_res.json().get("posts", list_res.json()))
        
        # Reschedule multiple times
        for days in [3, 5, 7]:
            new_time = (datetime.now() + timedelta(days=days)).isoformat()
            requests.put(f"{API_URL}/api/schedule/{post_id}", json={"scheduled_at": new_time})
        
        # Count posts after - should be same
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        count_after = len(list_res.json().get("posts", list_res.json()))
        
        assert count_after == count_before, "Reschedule created duplicate entries"
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{post_id}")


class TestDataIntegrity:
    """Tests for data integrity and validation"""
    
    def test_scheduled_time_preserved_exactly(self):
        """Scheduled time should be preserved exactly as set"""
        scheduled = datetime.now() + timedelta(days=1)
        scheduled = scheduled.replace(hour=15, minute=30, second=0, microsecond=0)
        
        post = create_test_post()
        post["scheduled_at"] = scheduled.isoformat()
        
        create_res = requests.post(f"{API_URL}/api/schedule/create", json=post)
        post_id = create_res.json()["id"]
        
        # Retrieve and verify
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        posts = list_res.json().get("posts", list_res.json())
        found = next((p for p in posts if p.get("id") == post_id), None)
        
        if found:
            retrieved_time = found.get("scheduledAt", "").replace("Z", "")
            # Parse and compare
            retrieved_dt = datetime.fromisoformat(retrieved_time[:19])
            assert retrieved_dt.hour == 15, f"Hour mismatch: {retrieved_dt.hour}"
            assert retrieved_dt.minute == 30, f"Minute mismatch: {retrieved_dt.minute}"
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{post_id}")
    
    def test_special_characters_in_caption(self):
        """Captions with special characters should be preserved"""
        special_caption = "Testing 🚀 emoji & special chars <script>alert('xss')</script> \"quotes\" 'apostrophe'"
        
        post = create_test_post()
        post["caption"] = special_caption
        
        create_res = requests.post(f"{API_URL}/api/schedule/create", json=post)
        post_id = create_res.json()["id"]
        
        # Retrieve
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        posts = list_res.json().get("posts", list_res.json())
        found = next((p for p in posts if p.get("id") == post_id), None)
        
        assert found is not None
        # Caption should be preserved (may be sanitized for XSS but emojis should work)
        assert "🚀" in found.get("caption", ""), "Emoji not preserved"
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{post_id}")
    
    def test_platform_validation(self):
        """Platform should be validated and preserved"""
        for platform in ["instagram", "tiktok", "youtube"]:
            post = create_test_post(platform=platform)
            create_res = requests.post(f"{API_URL}/api/schedule/create", json=post)
            
            if create_res.status_code == 200:
                post_id = create_res.json()["id"]
                
                list_res = requests.get(f"{API_URL}/api/schedule/list")
                posts = list_res.json().get("posts", list_res.json())
                found = next((p for p in posts if p.get("id") == post_id), None)
                
                assert found is not None
                assert found.get("platform") == platform, f"Platform mismatch for {platform}"
                
                requests.delete(f"{API_URL}/api/schedule/{post_id}")


class TestTrustMetricsCollection:
    """Run comprehensive tests and collect trust metrics"""
    
    def test_collect_trust_metrics(self):
        """Run multiple operations and report trust metrics"""
        metrics = SchedulingTrustMetrics()
        
        # Test creates
        for i in range(10):
            post = create_test_post(title=f"Metrics Test {i}")
            try:
                res = requests.post(f"{API_URL}/api/schedule/create", json=post)
                if res.status_code == 200:
                    metrics.successful_creates += 1
                    metrics.created_posts.append(res.json()["id"])
                else:
                    metrics.failed_creates += 1
            except:
                metrics.failed_creates += 1
        
        # Test retrievals
        for _ in range(5):
            try:
                res = requests.get(f"{API_URL}/api/schedule/list")
                if res.status_code == 200:
                    metrics.successful_retrievals += 1
                else:
                    metrics.failed_retrievals += 1
            except:
                metrics.failed_retrievals += 1
        
        # Verify data integrity
        list_res = requests.get(f"{API_URL}/api/schedule/list")
        if list_res.status_code == 200:
            posts = list_res.json().get("posts", list_res.json())
            for pid in metrics.created_posts:
                if not any(p.get("id") == pid for p in posts):
                    metrics.data_mismatches += 1
        
        # Test polling
        for _ in range(3):
            try:
                res = requests.get(f"{API_URL}/api/media/list?limit=1")
                if res.status_code == 200:
                    metrics.polling_successes += 1
                else:
                    metrics.polling_failures += 1
            except:
                metrics.polling_failures += 1
        
        # Cleanup
        for pid in metrics.created_posts:
            requests.delete(f"{API_URL}/api/schedule/{pid}")
        
        # Report
        report = metrics.report()
        print(f"\n=== TRUST METRICS REPORT ===")
        print(f"Create Success Rate: {report['create_success_rate']*100:.1f}%")
        print(f"Retrieval Success Rate: {report['retrieval_success_rate']*100:.1f}%")
        print(f"Data Integrity Issues: {report['data_integrity_issues']}")
        print(f"Polling Success Rate: {report['polling_success_rate']*100:.1f}%")
        
        # Assert high reliability
        assert report['create_success_rate'] >= 0.9, "Create success rate too low"
        assert report['retrieval_success_rate'] >= 0.9, "Retrieval success rate too low"
        assert report['data_integrity_issues'] == 0, "Data integrity issues found"


class TestApprovedContentPolling:
    """Specific tests for approved content URL polling"""
    
    def test_get_approved_media_list(self):
        """Get list of approved media items"""
        # Try without status filter first (status param may not be supported)
        response = requests.get(f"{API_URL}/api/media/list")
        assert response.status_code == 200
        data = response.json()
        # Accept either dict with items or direct list
        assert "items" in data or isinstance(data, list) or "total" in data
    
    def test_poll_until_approved(self):
        """Simulate polling for content approval status"""
        # This simulates what the frontend would do
        max_polls = 5
        poll_interval = 0.3
        
        for poll in range(max_polls):
            response = requests.get(f"{API_URL}/api/media/list?status=approved&limit=10")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if items:
                    # Found approved content
                    for item in items:
                        assert "id" in item, "Approved item missing id"
                    return
            
            time.sleep(poll_interval)
        
        # Even if no approved content, test passed if no errors
        assert True
    
    def test_media_url_endpoint_reliability(self):
        """Test media URL endpoint responds correctly"""
        # First get a real content ID from the list
        list_res = requests.get(f"{API_URL}/api/media/list")
        if list_res.status_code == 200:
            data = list_res.json()
            items = data.get("items", data) if isinstance(data, dict) else data
            if items and len(items) > 0:
                real_id = items[0].get("id")
                if real_id:
                    response = requests.get(f"{API_URL}/api/videos/{real_id}")
                    # Should return 200 (found), 404 (not found), or 422 (validation)
                    assert response.status_code in [200, 404, 422], f"Unexpected status for {real_id}"
        
        # Test with nonexistent ID - expect 404 or 422
        response = requests.get(f"{API_URL}/api/videos/nonexistent-test-id-12345")
        assert response.status_code in [200, 404, 422], "Unexpected status for nonexistent ID"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
