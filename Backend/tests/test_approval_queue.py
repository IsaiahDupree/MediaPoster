"""
Tests for Approval Queue API (Human in the Loop)
Tests content approval workflow, actions, and settings.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import uuid

import sys
sys.path.insert(0, '..')
from main import app

client = TestClient(app)


class TestApprovalQueueItems:
    """Test queue item endpoints"""

    def test_get_queue_items(self):
        """Test getting queue items"""
        response = client.get("/api/approval-queue/items")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

    def test_get_queue_items_with_status_filter(self):
        """Test filtering queue items by status"""
        for status in ["pending", "approved", "rejected", "needs_changes", "scheduled"]:
            response = client.get(f"/api/approval-queue/items?status={status}")
            assert response.status_code == 200
            
            data = response.json()
            for item in data:
                assert item["status"] == status

    def test_get_queue_items_with_platform_filter(self):
        """Test filtering queue items by platform"""
        response = client.get("/api/approval-queue/items?platform=instagram")
        assert response.status_code == 200
        
        data = response.json()
        for item in data:
            assert "instagram" in item["platforms"]

    def test_get_queue_items_with_priority_filter(self):
        """Test filtering queue items by priority"""
        for priority in ["low", "normal", "high", "urgent"]:
            response = client.get(f"/api/approval-queue/items?priority={priority}")
            assert response.status_code == 200

    def test_get_queue_items_sorting(self):
        """Test sorting queue items"""
        for sort_by in ["created_at", "priority", "ai_score"]:
            for order in ["asc", "desc"]:
                response = client.get(f"/api/approval-queue/items?sort_by={sort_by}&order={order}")
                assert response.status_code == 200

    def test_get_queue_items_pagination(self):
        """Test queue items pagination"""
        response = client.get("/api/approval-queue/items?limit=5&offset=0")
        assert response.status_code == 200
        assert len(response.json()) <= 5

    def test_queue_item_structure(self):
        """Test queue item has correct structure"""
        response = client.get("/api/approval-queue/items")
        assert response.status_code == 200
        
        data = response.json()
        if data:
            item = data[0]
            assert "id" in item
            assert "content_id" in item
            assert "title" in item
            assert "platforms" in item
            assert "status" in item
            assert "priority" in item
            assert "created_at" in item


class TestApprovalQueueStats:
    """Test queue statistics endpoint"""

    def test_get_queue_stats(self):
        """Test getting queue statistics"""
        response = client.get("/api/approval-queue/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "pending" in data
        assert "approved" in data
        assert "rejected" in data
        assert "needs_changes" in data
        assert "scheduled" in data
        assert "posted" in data
        assert "by_platform" in data
        assert "by_priority" in data
        assert "avg_review_time_hours" in data

    def test_stats_values_are_valid(self):
        """Test that stats values are valid"""
        response = client.get("/api/approval-queue/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 0
        assert data["pending"] >= 0
        assert data["approved"] >= 0
        assert data["rejected"] >= 0
        assert isinstance(data["by_platform"], dict)
        assert isinstance(data["by_priority"], dict)


class TestApprovalQueueSingleItem:
    """Test single item operations"""

    def test_get_single_item(self):
        """Test getting a single queue item"""
        # First get list to get a valid ID
        list_response = client.get("/api/approval-queue/items")
        assert list_response.status_code == 200
        items = list_response.json()
        
        if items:
            item_id = items[0]["id"]
            response = client.get(f"/api/approval-queue/item/{item_id}")
            assert response.status_code == 200
            assert response.json()["id"] == item_id

    def test_get_nonexistent_item(self):
        """Test getting non-existent item"""
        response = client.get(f"/api/approval-queue/item/{uuid.uuid4()}")
        assert response.status_code == 404


class TestApprovalQueueActions:
    """Test queue item actions"""

    def get_pending_item_id(self):
        """Helper to get a pending item ID"""
        response = client.get("/api/approval-queue/items?status=pending")
        if response.status_code == 200 and response.json():
            return response.json()[0]["id"]
        return None

    def test_approve_item(self):
        """Test approving an item"""
        item_id = self.get_pending_item_id()
        if not item_id:
            pytest.skip("No pending items available")
        
        response = client.post(
            f"/api/approval-queue/item/{item_id}/action",
            json={"action": "approve", "notes": "Looks good"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["new_status"] in ["approved", "scheduled"]

    def test_reject_item(self):
        """Test rejecting an item"""
        item_id = self.get_pending_item_id()
        if not item_id:
            pytest.skip("No pending items available")
        
        response = client.post(
            f"/api/approval-queue/item/{item_id}/action",
            json={
                "action": "reject",
                "rejection_reason": "Content quality too low",
                "notes": "Please improve image quality"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["new_status"] == "rejected"

    def test_request_changes(self):
        """Test requesting changes on an item"""
        item_id = self.get_pending_item_id()
        if not item_id:
            pytest.skip("No pending items available")
        
        response = client.post(
            f"/api/approval-queue/item/{item_id}/action",
            json={
                "action": "request_changes",
                "requested_changes": ["Improve thumbnail", "Add better caption"],
                "notes": "Almost there, needs minor fixes"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["new_status"] == "needs_changes"

    def test_schedule_item(self):
        """Test scheduling an item"""
        item_id = self.get_pending_item_id()
        if not item_id:
            pytest.skip("No pending items available")
        
        future_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
        
        response = client.post(
            f"/api/approval-queue/item/{item_id}/action",
            json={
                "action": "schedule",
                "scheduled_time": future_time,
                "notes": "Scheduling for tomorrow"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["new_status"] == "scheduled"

    def test_invalid_action(self):
        """Test invalid action"""
        item_id = self.get_pending_item_id()
        if not item_id:
            pytest.skip("No pending items available")
        
        response = client.post(
            f"/api/approval-queue/item/{item_id}/action",
            json={"action": "invalid_action"}
        )
        assert response.status_code == 400

    def test_action_on_nonexistent_item(self):
        """Test action on non-existent item"""
        response = client.post(
            f"/api/approval-queue/item/{uuid.uuid4()}/action",
            json={"action": "approve"}
        )
        assert response.status_code == 404


class TestApprovalQueueBulkActions:
    """Test bulk action operations"""

    def test_bulk_approve(self):
        """Test bulk approving items"""
        # Get some items
        response = client.get("/api/approval-queue/items?status=pending&limit=3")
        items = response.json()
        
        if len(items) < 2:
            pytest.skip("Not enough pending items for bulk test")
        
        item_ids = [item["id"] for item in items[:2]]
        
        response = client.post(
            "/api/approval-queue/bulk-action",
            json={
                "item_ids": item_ids,
                "action": "approve",
                "notes": "Bulk approved"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "processed" in data
        assert "successful" in data
        assert data["processed"] == len(item_ids)

    def test_bulk_reject(self):
        """Test bulk rejecting items"""
        response = client.get("/api/approval-queue/items?status=pending&limit=2")
        items = response.json()
        
        if len(items) < 1:
            pytest.skip("No pending items for bulk test")
        
        item_ids = [item["id"] for item in items[:1]]
        
        response = client.post(
            "/api/approval-queue/bulk-action",
            json={
                "item_ids": item_ids,
                "action": "reject"
            }
        )
        assert response.status_code == 200

    def test_bulk_action_empty_list(self):
        """Test bulk action with empty list"""
        response = client.post(
            "/api/approval-queue/bulk-action",
            json={"item_ids": [], "action": "approve"}
        )
        assert response.status_code == 200
        assert response.json()["processed"] == 0


class TestApprovalQueueResubmit:
    """Test item resubmission"""

    def test_resubmit_item(self):
        """Test resubmitting an item after changes"""
        # First get a needs_changes item
        response = client.get("/api/approval-queue/items?status=needs_changes")
        items = response.json()
        
        if not items:
            pytest.skip("No items needing changes")
        
        item_id = items[0]["id"]
        
        response = client.post(f"/api/approval-queue/item/{item_id}/resubmit")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True

    def test_resubmit_nonexistent_item(self):
        """Test resubmitting non-existent item"""
        response = client.post(f"/api/approval-queue/item/{uuid.uuid4()}/resubmit")
        assert response.status_code == 404


class TestApprovalQueueSettings:
    """Test control settings endpoints"""

    def test_get_settings(self):
        """Test getting control settings"""
        response = client.get("/api/approval-queue/settings")
        assert response.status_code == 200
        
        data = response.json()
        assert "require_approval" in data
        assert "auto_approve_high_score" in data
        assert "auto_approve_threshold" in data
        assert "max_posts_per_day" in data

    def test_update_settings(self):
        """Test updating control settings"""
        response = client.put(
            "/api/approval-queue/settings",
            json={
                "require_approval": True,
                "auto_approve_high_score": True,
                "auto_approve_threshold": 90.0,
                "max_posts_per_day": 15,
                "notify_on_new_content": True,
                "notify_on_schedule": True,
                "default_review_priority": "normal",
                "blackout_hours": [],
                "require_caption_review": True,
                "require_hashtag_review": False,
                "platforms_requiring_approval": []
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True

    def test_get_settings_presets(self):
        """Test getting settings presets"""
        response = client.get("/api/approval-queue/settings/presets")
        assert response.status_code == 200
        
        data = response.json()
        assert "presets" in data
        assert isinstance(data["presets"], list)
        
        # Check preset structure
        for preset in data["presets"]:
            assert "id" in preset
            assert "name" in preset
            assert "description" in preset
            assert "settings" in preset


class TestApprovalQueuePlatformControls:
    """Test per-platform control settings"""

    def test_get_platform_controls(self):
        """Test getting platform controls"""
        response = client.get("/api/approval-queue/platforms")
        assert response.status_code == 200
        
        data = response.json()
        assert "platforms" in data
        
        # Check platform structure
        for platform, settings in data["platforms"].items():
            assert "enabled" in settings
            assert "require_approval" in settings
            assert "max_posts_per_day" in settings

    def test_update_platform_control(self):
        """Test updating platform control"""
        response = client.put(
            "/api/approval-queue/platforms/instagram",
            json={
                "enabled": True,
                "require_approval": True,
                "max_posts_per_day": 5
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] == True


class TestApprovalQueueActivity:
    """Test activity log endpoint"""

    def test_get_activity_log(self):
        """Test getting activity log"""
        response = client.get("/api/approval-queue/activity")
        assert response.status_code == 200
        
        data = response.json()
        assert "activities" in data
        assert isinstance(data["activities"], list)

    def test_get_activity_log_with_limit(self):
        """Test getting activity log with limit"""
        response = client.get("/api/approval-queue/activity?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["activities"]) <= 5

    def test_get_activity_log_by_type(self):
        """Test filtering activity by type"""
        response = client.get("/api/approval-queue/activity?action_type=approved")
        assert response.status_code == 200


class TestApprovalQueueDelete:
    """Test item deletion"""

    def test_delete_item(self):
        """Test deleting a queue item"""
        # First get an item
        response = client.get("/api/approval-queue/items?limit=1")
        items = response.json()
        
        if not items:
            pytest.skip("No items to delete")
        
        item_id = items[0]["id"]
        
        response = client.delete(f"/api/approval-queue/item/{item_id}")
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify deletion
        response = client.get(f"/api/approval-queue/item/{item_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_item(self):
        """Test deleting non-existent item"""
        response = client.delete(f"/api/approval-queue/item/{uuid.uuid4()}")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
