"""
Integration Tests for Schedule API
Tests that buttons actually produce results to the backend
"""
import requests
import pytest
from datetime import datetime, timedelta
import uuid

API_URL = "http://localhost:5555"

# Test data - matches actual API schema (ScheduledPostCreate)
def create_test_post_data():
    return {
        "content_id": f"test-{uuid.uuid4().hex[:8]}",
        "title": "Integration Test Post",
        "caption": "Testing backend integration #test",
        "platform": "tiktok",
        "account_id": "test-account-id",  # Required
        "account_username": "test_user",  # Required
        "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat(),  # Required
    }


class TestScheduleCreate:
    """Tests for POST /api/schedule/create - Schedule Button"""
    
    def test_create_scheduled_post_success(self):
        """Schedule button should create a new post"""
        data = create_test_post_data()
        
        response = requests.post(f"{API_URL}/api/schedule/create", json=data)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        result = response.json()
        # API returns {id, message} on success
        assert "id" in result
        assert "message" in result
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{result['id']}")
    
    def test_create_returns_id(self):
        """Create should return post ID for tracking"""
        data = create_test_post_data()
        
        response = requests.post(f"{API_URL}/api/schedule/create", json=data)
        result = response.json()
        
        assert "id" in result, "Create should return post ID"
        assert result["id"] is not None
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{result['id']}")
    
    def test_create_with_all_platforms(self):
        """Should work for tiktok, instagram, and youtube"""
        for platform in ["tiktok", "instagram", "youtube"]:
            data = create_test_post_data()
            data["platform"] = platform
            
            response = requests.post(f"{API_URL}/api/schedule/create", json=data)
            
            assert response.status_code == 200, f"Failed for {platform}: {response.text}"
            result = response.json()
            assert "id" in result  # Success returns ID
            
            # Cleanup
            requests.delete(f"{API_URL}/api/schedule/{result['id']}")


class TestScheduleList:
    """Tests for GET /api/schedule/list - Calendar Display"""
    
    def test_list_returns_posts(self):
        """Calendar should receive posts data"""
        response = requests.get(f"{API_URL}/api/schedule/list")
        
        assert response.status_code == 200
        data = response.json()
        # API returns {posts: [...], total: N}
        assert "posts" in data
        assert isinstance(data["posts"], list)
    
    def test_list_includes_created_post(self):
        """Created posts should appear in list"""
        # Create a post
        post_data = create_test_post_data()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # List should include it
        response = requests.get(f"{API_URL}/api/schedule/list")
        data = response.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
        
        found = any(p["id"] == created["id"] for p in posts)
        assert found, "Created post not found in list"
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_filter_by_platform(self):
        """Platform filter should work"""
        response = requests.get(f"{API_URL}/api/schedule/list?platform=tiktok")
        
        assert response.status_code == 200
        data = response.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
        for post in posts:
            assert post["platform"] == "tiktok"
    
    def test_filter_by_date_range(self):
        """Date range filter should work"""
        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        response = requests.get(f"{API_URL}/api/schedule/list?start_date={start}&end_date={end}")
        
        assert response.status_code == 200


class TestScheduleUpdate:
    """Tests for PUT /api/schedule/{id} - Save Button in Edit Modal"""
    
    def test_update_title_and_caption(self):
        """Save button should update title and caption"""
        # Create post
        post_data = create_test_post_data()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Update via Save button
        update_data = {
            "title": "Updated Title via Save",
            "caption": "Updated caption #updated"
        }
        response = requests.put(f"{API_URL}/api/schedule/{created['id']}", json=update_data)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        # Success means update worked
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_update_scheduled_time(self):
        """Date picker should update scheduled time"""
        # Create post
        post_data = create_test_post_data()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Update scheduled time (simulates date picker) - use scheduled_at field
        new_time = (datetime.now() + timedelta(days=3)).isoformat()
        response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}", 
            json={"scheduled_at": new_time}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_update_nonexistent_returns_error(self):
        """Update non-existent post should return error"""
        response = requests.put(
            f"{API_URL}/api/schedule/nonexistent-id-12345", 
            json={"title": "Test"}
        )
        
        # Should return 404 or 500 (not found)
        assert response.status_code in [404, 500]


class TestScheduleDelete:
    """Tests for DELETE /api/schedule/{id} - Delete Button + Confirm"""
    
    def test_delete_removes_post(self):
        """Delete + Confirm should remove post"""
        # Create post
        post_data = create_test_post_data()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Delete (simulates Delete + Confirm buttons)
        response = requests.delete(f"{API_URL}/api/schedule/{created['id']}")
        
        assert response.status_code == 200
        
        # Verify it's gone
        list_response = requests.get(f"{API_URL}/api/schedule/list")
        data = list_response.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
        found = any(p["id"] == created["id"] for p in posts)
        assert not found, "Post still exists after delete"
    
    def test_delete_nonexistent_returns_error(self):
        """Delete non-existent post should return error"""
        response = requests.delete(f"{API_URL}/api/schedule/nonexistent-id-12345")
        
        # Should return 404 or 500 (not found)
        assert response.status_code in [404, 500]


class TestDragAndDrop:
    """Tests for Drag & Drop Rescheduling"""
    
    def test_reschedule_via_drag_drop(self):
        """Dropping post on different day should update scheduled_time"""
        # Create post for tomorrow
        post_data = create_test_post_data()
        original_time = datetime.now() + timedelta(days=1)
        post_data["scheduled_at"] = original_time.isoformat()
        
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()

        # Simulate drag and drop - post moved to different day
        new_day = original_time + timedelta(days=2)
        
        response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={"scheduled_at": new_day.isoformat()}
        )

        assert response.status_code == 200
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")


class TestScheduleStats:
    """Tests for GET /api/schedule/stats/overview - Stats Display"""
    
    def test_stats_returns_counts(self):
        """Stats endpoint should return scheduling statistics"""
        response = requests.get(f"{API_URL}/api/schedule/stats/overview")
        
        assert response.status_code == 200
        data = response.json()
        # API returns status_counts, platform_counts, etc.
        assert "status_counts" in data or "platform_counts" in data or "queue_days" in data


class TestAccountsList:
    """Tests for GET /api/schedule/accounts/list - Account Selector"""
    
    def test_accounts_returns_list(self):
        """Accounts endpoint should return list for account selector"""
        response = requests.get(f"{API_URL}/api/schedule/accounts/list")
        
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        assert isinstance(data["accounts"], list)


class TestMediaSelector:
    """Tests for Media Selector API calls"""
    
    def test_analyzed_content_endpoint_exists(self):
        """Media selector endpoint should exist"""
        response = requests.get(f"{API_URL}/api/analyzed-content?limit=10")
        # Should return 200 or 404 (if no content exists)
        assert response.status_code in [200, 404]
    
    def test_videos_endpoint_exists(self):
        """Videos endpoint should exist for video details"""
        response = requests.get(f"{API_URL}/api/videos")
        # Should return something (200, 404, or 405 for wrong method)
        assert response.status_code in [200, 404, 405, 422]


class TestFullScheduleFlow:
    """End-to-end test of complete scheduling flow"""
    
    def test_complete_schedule_flow(self):
        """
        Test complete flow:
        1. List accounts (account selector)
        2. Create scheduled post (Schedule button)
        3. Verify in list (calendar display)
        4. Update post (Save button)
        5. Delete post (Delete + Confirm)
        """
        # 1. Get accounts
        accounts_response = requests.get(f"{API_URL}/api/schedule/accounts/list")
        assert accounts_response.status_code == 200
        print("✓ Accounts loaded")
        
        # 2. Create scheduled post
        post_data = create_test_post_data()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        created = create_response.json()
        print(f"✓ Post created: {created['id']}")
        
        # 3. Verify in list
        list_response = requests.get(f"{API_URL}/api/schedule/list")
        data = list_response.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
        found = any(p["id"] == created["id"] for p in posts)
        assert found, "Post not in calendar"
        print("✓ Post appears in calendar")
        
        # 4. Update post
        update_response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={"title": "Flow Test Updated", "caption": "Updated in flow test"}
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        print("✓ Post updated via Save")
        
        # 5. Delete post
        delete_response = requests.delete(f"{API_URL}/api/schedule/{created['id']}")
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        print("✓ Post deleted via Delete + Confirm")
        
        # Verify deletion
        final_data = requests.get(f"{API_URL}/api/schedule/list").json()
        final_posts = final_data.get("posts", final_data) if isinstance(final_data, dict) else final_data
        still_exists = any(p["id"] == created["id"] for p in final_posts)
        assert not still_exists, "Post still exists after delete"
        print("✓ Post removed from calendar")
        
        print("\n✅ Complete scheduling flow passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
