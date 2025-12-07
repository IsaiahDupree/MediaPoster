"""
Test Suite for Publishing Queue API Endpoints
Tests all publishing queue API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import uuid

from main import app


client = TestClient(app)


@pytest.fixture
def mock_queue_service():
    """Mock PublishingQueueService"""
    with patch('api.endpoints.publishing_queue.PublishingQueueService') as MockService:
        yield MockService


class TestAddToQueue:
    """Test adding items to queue via API"""
    
    def test_add_single_item(self, mock_queue_service):
        """Test POST /add endpoint"""
        mock_service = mock_queue_service.return_value
        mock_item = Mock()
        mock_item.id = uuid.uuid4()
        mock_item.scheduled_for = datetime.now() + timedelta(hours=1)
        mock_service.add_to_queue.return_value = mock_item
        
        response = client.post(
            "/api/publishing-queue/add",
            json={
                "platform": "tiktok",
                "scheduled_for": (datetime.now() + timedelta(hours=1)).isoformat(),
                "caption": "Test post",
                "priority": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "queued"
    
    def test_add_with_invalid_platform(self, mock_queue_service):
        """Test adding with invalid platform"""
        mock_service = mock_queue_service.return_value
        mock_service.add_to_queue.side_effect = ValueError("Invalid platform")
        
        response = client.post(
            "/api/publishing-queue/add",
            json={
                "platform": "invalid_platform",
                "scheduled_for": datetime.now().isoformat()
            }
        )
        
        assert response.status_code == 400


class TestBulkSchedule:
    """Test bulk scheduling endpoint"""
    
    def test_bulk_schedule_multiple(self, mock_queue_service):
        """Test POST /bulk endpoint"""
        mock_service = mock_queue_service.return_value
        mock_items = [Mock(id=uuid.uuid4(), scheduled_for=datetime.now()) for _ in range(3)]
        mock_service.bulk_schedule.return_value = mock_items
        
        response = client.post(
            "/api/publishing-queue/bulk",
            json={
                "items": [
                    {
                        "platform": "tiktok",
                        "scheduled_for": (datetime.now() + timedelta(hours=i)).isoformat()
                    }
                    for i in range(3)
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["scheduled"] == 3


class TestGetQueueItems:
    """Test retrieving queue items"""
    
    def test_get_all_items(self, mock_queue_service):
        """Test GET /items without filters"""
        mock_service = mock_queue_service.return_value
        mock_items = [
            Mock(
                id=uuid.uuid4(),
                platform='tiktok',
                status='queued',
                scheduled_for=datetime.now(),
                priority=0,
                caption='test',
                retry_count=0,
                platform_url=None
            )
        ]
        mock_service.get_next_items.return_value = mock_items
        
        response = client.get("/api/publishing-queue/items")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["count"] >= 0
    
    def test_get_items_by_status(self, mock_queue_service):
        """Test GET /items with status filter"""
        mock_service = mock_queue_service.return_value
        mock_service.get_items_by_status.return_value = []
        
        response = client.get("/api/publishing-queue/items?status=failed")
        
        assert response.status_code == 200


class TestQueueStatistics:
    """Test queue statistics endpoint"""
    
    def test_get_status(self, mock_queue_service):
        """Test GET /status endpoint"""
        mock_service = mock_queue_service.return_value
        mock_service.get_queue_statistics.return_value = {
            'by_status': {'queued': 5, 'published': 10},
            'by_platform': {'tiktok': 8, 'instagram': 7},
            'total': 15
        }
        
        response = client.get("/api/publishing-queue/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data
        assert data["statistics"]["total"] == 15


class TestRetryItem:
    """Test retry endpoint"""
    
    def test_retry_success(self, mock_queue_service):
        """Test PUT /{id}/retry success"""
        mock_service = mock_queue_service.return_value
        mock_service.retry_failed_item.return_value = True
        
        item_id = str(uuid.uuid4())
        response = client.put(f"/api/publishing-queue/{item_id}/retry")
        
        assert response.status_code == 200
        assert "retry" in response.json()["message"].lower()
    
    def test_retry_max_retries_reached(self, mock_queue_service):
        """Test retry when max retries exceeded"""
        mock_service = mock_queue_service.return_value
        mock_service.retry_failed_item.return_value = False
        
        item_id = str(uuid.uuid4())
        response = client.put(f"/api/publishing-queue/{item_id}/retry")
        
        assert response.status_code == 400


class TestRescheduleItem:
    """Test reschedule endpoint"""
    
    def test_reschedule_success(self, mock_queue_service):
        """Test PUT /{id}/reschedule"""
        mock_service = mock_queue_service.return_value
        mock_service.reschedule_item.return_value = True
        
        item_id = str(uuid.uuid4())
        new_time = datetime.now() + timedelta(days=1)
        
        response = client.put(
            f"/api/publishing-queue/{item_id}/reschedule",
            params={"new_time": new_time.isoformat()}
        )
        
        assert response.status_code == 200


class TestCancelItem:
    """Test cancel endpoint"""
    
    def test_cancel_success(self, mock_queue_service):
        """Test DELETE /{id}/cancel"""
        mock_service = mock_queue_service.return_value
        mock_service.cancel_item.return_value = True
        
        item_id = str(uuid.uuid4())
        response = client.delete(f"/api/publishing-queue/{item_id}/cancel")
        
        assert response.status_code == 200
        assert "cancelled" in response.json()["message"].lower()


class TestProcessQueue:
    """Test queue processing endpoint"""
    
    def test_process_queue(self, mock_queue_service):
        """Test POST /process endpoint"""
        mock_service = mock_queue_service.return_value
        mock_items = [Mock(id=uuid.uuid4()) for _ in range(5)]
        mock_service.get_next_items.return_value = mock_items
        mock_service.update_status.return_value = True
        
        response = client.post("/api/publishing-queue/process")
        
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 5
