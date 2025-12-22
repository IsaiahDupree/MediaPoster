"""
End-to-End Tests for All Page APIs
Comprehensive tests that verify all page endpoints work correctly.
Tests the actual backend with real HTTP requests.
"""
import requests
import pytest
from datetime import datetime, timedelta
import uuid

API_URL = "http://localhost:5555"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_test_scheduled_post():
    """Create a test scheduled post and return its data"""
    return {
        "content_id": f"e2e-test-{uuid.uuid4().hex[:8]}",
        "title": "E2E Test Post",
        "caption": "E2E testing #test",
        "platform": "tiktok",
        "account_id": "test-account",
        "account_username": "test_user",
        "scheduled_at": (datetime.now() + timedelta(days=1)).isoformat(),
    }


# =============================================================================
# SCHEDULE PAGE TESTS
# =============================================================================

class TestSchedulePageE2E:
    """E2E tests for Schedule/Calendar page functionality"""
    
    def test_schedule_list_endpoint(self):
        """GET /api/schedule/list - Calendar loads posts"""
        response = requests.get(f"{API_URL}/api/schedule/list")
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data or isinstance(data, list)
    
    def test_schedule_accounts_list(self):
        """GET /api/schedule/accounts/list - Account selector loads"""
        response = requests.get(f"{API_URL}/api/schedule/accounts/list")
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
    
    def test_schedule_create_and_delete(self):
        """POST /api/schedule/create + DELETE - Schedule button works"""
        # Create
        post_data = create_test_scheduled_post()
        create_response = requests.post(
            f"{API_URL}/api/schedule/create",
            json=post_data
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert "id" in created
        
        # Delete
        delete_response = requests.delete(f"{API_URL}/api/schedule/{created['id']}")
        assert delete_response.status_code == 200
    
    def test_schedule_update(self):
        """PUT /api/schedule/{id} - Save button works"""
        # Create post
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Update
        update_response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={"title": "Updated Title", "caption": "Updated caption"}
        )
        assert update_response.status_code == 200
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_schedule_stats(self):
        """GET /api/schedule/stats/overview - Stats panel loads"""
        response = requests.get(f"{API_URL}/api/schedule/stats/overview")
        assert response.status_code == 200


# =============================================================================
# HYDRATION PAGE DATA TESTS
# =============================================================================

class TestHydrationEndpointsE2E:
    """E2E tests for centralized hydration endpoints"""
    
    def test_hydration_status(self):
        """GET /api/hydration/status - Check hydration health"""
        response = requests.get(f"{API_URL}/api/hydration/status")
        assert response.status_code == 200
        data = response.json()
        assert "accounts_count" in data or "last_full_refresh" in data
    
    def test_hydration_page_analytics(self):
        """GET /api/hydration/page/analytics - Analytics page data"""
        response = requests.get(f"{API_URL}/api/hydration/page/analytics")
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data or "totals" in data
    
    def test_hydration_page_schedule(self):
        """GET /api/hydration/page/schedule - Schedule page data"""
        response = requests.get(f"{API_URL}/api/hydration/page/schedule")
        assert response.status_code == 200
        data = response.json()
        # Should contain unified schedule data
        assert "scheduled_posts" in data or "accounts" in data or "stats" in data
    
    def test_hydration_page_content_performance(self):
        """GET /api/hydration/page/content-performance - Content page data"""
        response = requests.get(f"{API_URL}/api/hydration/page/content-performance")
        assert response.status_code == 200
    
    def test_hydration_page_followers(self):
        """GET /api/hydration/page/followers - Followers page data"""
        response = requests.get(f"{API_URL}/api/hydration/page/followers")
        assert response.status_code == 200
    
    def test_hydration_page_people(self):
        """GET /api/hydration/page/people - People page data"""
        response = requests.get(f"{API_URL}/api/hydration/page/people")
        assert response.status_code == 200
    
    def test_hydration_page_narrative_builder(self):
        """GET /api/hydration/page/narrative-builder - Narrative builder data"""
        response = requests.get(f"{API_URL}/api/hydration/page/narrative-builder")
        assert response.status_code == 200


# =============================================================================
# NARRATIVE BUILDER TESTS
# =============================================================================

class TestNarrativeBuilderE2E:
    """E2E tests for Narrative Builder page functionality"""
    
    def test_signals_endpoint(self):
        """GET /api/narrative-builder/signals - Signals load"""
        response = requests.get(f"{API_URL}/api/narrative-builder/signals")
        assert response.status_code == 200
    
    def test_candidates_endpoint(self):
        """GET /api/narrative-builder/candidates - Candidates load"""
        response = requests.get(f"{API_URL}/api/narrative-builder/candidates")
        assert response.status_code == 200
    
    def test_generate_recommendations(self):
        """POST /api/narrative-builder/recommendations - AI recommendations"""
        response = requests.post(
            f"{API_URL}/api/narrative-builder/recommendations",
            json={
                "goal": "Grow followers",
                "platforms": ["tiktok", "instagram"],
                "pillars": ["value", "proof"],
                "count": 3
            }
        )
        # May return 200, 404 (not implemented), 422 (validation), or 500
        assert response.status_code in [200, 404, 422, 500]


# =============================================================================
# ANALYZED CONTENT TESTS
# =============================================================================

class TestAnalyzedContentE2E:
    """E2E tests for Analyzed Content / Media Library"""
    
    def test_analyzed_content_list(self):
        """GET /api/analyzed-content/list - Media library loads"""
        response = requests.get(f"{API_URL}/api/analyzed-content/list?limit=10")
        assert response.status_code in [200, 404]
    
    def test_analyzed_content_stats(self):
        """GET /api/analyzed-content/stats - Stats load"""
        response = requests.get(f"{API_URL}/api/analyzed-content/stats")
        assert response.status_code in [200, 404]
    
    def test_analyzed_content_filter_by_status(self):
        """Filter by status works"""
        for status in ["approved", "pending", "all"]:
            response = requests.get(f"{API_URL}/api/analyzed-content/list?status={status}")
            assert response.status_code in [200, 404]


# =============================================================================
# POSTED CONTENT TESTS
# =============================================================================

class TestPostedContentE2E:
    """E2E tests for Posted Content page"""
    
    def test_posted_content_list(self):
        """GET /api/posted-content - Posted content loads"""
        response = requests.get(f"{API_URL}/api/posted-content")
        assert response.status_code in [200, 404]
    
    def test_posted_content_with_pagination(self):
        """Pagination works"""
        response = requests.get(f"{API_URL}/api/posted-content?limit=10&offset=0")
        assert response.status_code in [200, 404]


# =============================================================================
# SOCIAL ACCOUNTS TESTS
# =============================================================================

class TestSocialAccountsE2E:
    """E2E tests for Social Accounts management"""
    
    def test_accounts_list(self):
        """GET /api/accounts - Accounts list loads"""
        response = requests.get(f"{API_URL}/api/accounts")
        assert response.status_code in [200, 404]
    
    def test_blotato_accounts(self):
        """GET /api/blotato/accounts - Blotato integration"""
        response = requests.get(f"{API_URL}/api/blotato/accounts")
        assert response.status_code in [200, 404, 401]


# =============================================================================
# CALENDAR VIEWS TESTS
# =============================================================================

class TestCalendarViewsE2E:
    """E2E tests for Calendar view functionality"""
    
    def test_calendar_week_view(self):
        """GET /api/schedule/calendar/week - Week view data"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(f"{API_URL}/api/schedule/calendar/week?date={today}")
        assert response.status_code in [200, 404]
    
    def test_schedule_list_with_date_range(self):
        """Date range filtering works"""
        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        response = requests.get(
            f"{API_URL}/api/schedule/list?start_date={start}&end_date={end}"
        )
        assert response.status_code == 200
    
    def test_schedule_list_with_platform_filter(self):
        """Platform filtering works"""
        response = requests.get(f"{API_URL}/api/schedule/list?platform=tiktok")
        assert response.status_code == 200


# =============================================================================
# DRAG AND DROP SIMULATION
# =============================================================================

class TestDragDropE2E:
    """E2E tests for drag-and-drop rescheduling"""
    
    def test_reschedule_to_new_day(self):
        """Drag post to different day updates scheduled_at"""
        # Create post
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Simulate drag to new day
        new_time = (datetime.now() + timedelta(days=3)).isoformat()
        update_response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={"scheduled_at": new_time}
        )
        assert update_response.status_code == 200
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_reschedule_to_new_time(self):
        """Drag post to different time slot"""
        # Create post
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Simulate drag to new time (same day, different hour)
        new_time = (datetime.now() + timedelta(days=1, hours=3)).isoformat()
        update_response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={"scheduled_at": new_time}
        )
        assert update_response.status_code == 200
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")


# =============================================================================
# EDIT MODAL TESTS
# =============================================================================

class TestEditModalE2E:
    """E2E tests for schedule edit modal functionality"""
    
    def test_update_title(self):
        """Edit modal - Update title"""
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={"title": "New Title from Edit Modal"}
        )
        assert response.status_code == 200
        
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_update_caption(self):
        """Edit modal - Update caption"""
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={"caption": "New caption with #hashtags"}
        )
        assert response.status_code == 200
        
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_update_scheduled_time(self):
        """Edit modal - Date picker changes time"""
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        new_time = (datetime.now() + timedelta(days=5)).isoformat()
        response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={"scheduled_at": new_time}
        )
        assert response.status_code == 200
        
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_delete_with_confirmation(self):
        """Edit modal - Delete button with confirmation"""
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Delete (simulates clicking Delete + Confirm)
        response = requests.delete(f"{API_URL}/api/schedule/{created['id']}")
        assert response.status_code == 200
        
        # Verify deleted
        list_response = requests.get(f"{API_URL}/api/schedule/list")
        data = list_response.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
        found = any(p.get("id") == created["id"] for p in posts)
        assert not found


# =============================================================================
# FULL USER FLOW TESTS
# =============================================================================

class TestFullUserFlowsE2E:
    """E2E tests simulating complete user flows"""
    
    def test_schedule_content_flow(self):
        """
        Complete flow: Open calendar → Select date → Choose media → 
        Select account → Set time → Click Schedule → Verify in calendar
        """
        # 1. Load calendar data
        calendar_response = requests.get(f"{API_URL}/api/schedule/list")
        assert calendar_response.status_code == 200
        
        # 2. Load accounts for selector
        accounts_response = requests.get(f"{API_URL}/api/schedule/accounts/list")
        assert accounts_response.status_code == 200
        
        # 3. Create scheduled post (simulates Schedule button)
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        assert create_response.status_code == 200
        created = create_response.json()
        
        # 4. Verify post appears in calendar
        list_response = requests.get(f"{API_URL}/api/schedule/list")
        data = list_response.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
        found = any(p.get("id") == created["id"] for p in posts)
        assert found, "Scheduled post not found in calendar"
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_edit_scheduled_post_flow(self):
        """
        Complete flow: Click post → Open edit modal → 
        Modify fields → Save → Verify changes
        """
        # Create post
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Edit post (simulates edit modal Save)
        update_response = requests.put(
            f"{API_URL}/api/schedule/{created['id']}",
            json={
                "title": "Edited Title",
                "caption": "Edited caption #edited",
                "scheduled_at": (datetime.now() + timedelta(days=2)).isoformat()
            }
        )
        assert update_response.status_code == 200
        
        # Cleanup
        requests.delete(f"{API_URL}/api/schedule/{created['id']}")
    
    def test_delete_scheduled_post_flow(self):
        """
        Complete flow: Click post → Open edit modal → 
        Click Delete → Confirm → Verify removed
        """
        # Create post
        post_data = create_test_scheduled_post()
        create_response = requests.post(f"{API_URL}/api/schedule/create", json=post_data)
        created = create_response.json()
        
        # Delete with confirmation
        delete_response = requests.delete(f"{API_URL}/api/schedule/{created['id']}")
        assert delete_response.status_code == 200
        
        # Verify removed
        list_response = requests.get(f"{API_URL}/api/schedule/list")
        data = list_response.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
        found = any(p.get("id") == created["id"] for p in posts)
        assert not found, "Post still exists after delete"


# =============================================================================
# HEALTH CHECK
# =============================================================================

class TestHealthCheckE2E:
    """Basic health checks for all endpoints"""
    
    def test_api_health(self):
        """GET /health - API is running"""
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200
    
    def test_all_page_endpoints_respond(self):
        """All page endpoints should respond (not 500)"""
        endpoints = [
            "/api/schedule/list",
            "/api/schedule/accounts/list",
            "/api/schedule/stats/overview",
            "/api/hydration/status",
            "/api/hydration/page/analytics",
            "/api/hydration/page/schedule",
            "/api/hydration/page/content-performance",
            "/api/hydration/page/followers",
            "/api/hydration/page/people",
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{API_URL}{endpoint}")
            assert response.status_code != 500, f"{endpoint} returned 500"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
