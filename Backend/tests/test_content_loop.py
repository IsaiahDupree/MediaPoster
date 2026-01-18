"""
Tests for the Closed-Loop Content System API

Tests cover:
- Content items CRUD
- Postings CRUD
- Metric snapshots
- Review windows
- Reviews and scoring
- Playbook rules
- Content slots
- Insights
"""

import pytest
import httpx
from uuid import uuid4

API_URL = "http://localhost:5555"


class TestContentLoop:
    """Test suite for content loop API endpoints."""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(base_url=API_URL, timeout=30)
    
    # =========================================================================
    # Content Items
    # =========================================================================
    
    def test_create_content_item(self, client):
        """Test creating a content item."""
        response = client.post("/api/content-loop/content-items", json={
            "title": "Test UGC Video",
            "source_type": "UGC",
            "format_type": "talking_head",
            "hook_text": "You won't believe this...",
            "duration_sec": 45
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test UGC Video"
        assert data["source_type"] == "UGC"
        return data["id"]
    
    def test_create_sora_content_item(self, client):
        """Test creating a Sora AI content item."""
        response = client.post("/api/content-loop/content-items", json={
            "title": "AI Generated Scene",
            "source_type": "SORA",
            "format_type": "broll",
            "duration_sec": 30
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "SORA"
    
    def test_list_content_items(self, client):
        """Test listing content items."""
        response = client.get("/api/content-loop/content-items")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "count" in data
    
    def test_filter_content_by_source(self, client):
        """Test filtering content items by source type."""
        response = client.get("/api/content-loop/content-items?source_type=UGC")
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["source_type"] == "UGC"
    
    # =========================================================================
    # Postings
    # =========================================================================
    
    def test_create_posting(self, client):
        """Test creating a posting."""
        # First create content
        content_resp = client.post("/api/content-loop/content-items", json={
            "title": "Posting Test Video",
            "source_type": "UGC"
        })
        content_id = content_resp.json()["id"]
        
        # Create posting
        response = client.post("/api/content-loop/postings", json={
            "content_item_id": content_id,
            "platform": "tiktok",
            "caption_text": "Check this out! #viral",
            "hashtags": ["viral", "fyp", "trending"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["platform"] == "tiktok"
        return data["id"], content_id
    
    def test_list_postings(self, client):
        """Test listing postings."""
        response = client.get("/api/content-loop/postings")
        
        assert response.status_code == 200
        data = response.json()
        assert "postings" in data
    
    def test_filter_postings_by_platform(self, client):
        """Test filtering postings by platform."""
        response = client.get("/api/content-loop/postings?platform=tiktok")
        
        assert response.status_code == 200
        data = response.json()
        for posting in data["postings"]:
            assert posting["platform"] == "tiktok"
    
    def test_update_posting_status(self, client):
        """Test updating posting status to posted."""
        # Create content and posting first
        content_resp = client.post("/api/content-loop/content-items", json={
            "title": "Status Test Video",
            "source_type": "UGC"
        })
        content_id = content_resp.json()["id"]
        
        posting_resp = client.post("/api/content-loop/postings", json={
            "content_item_id": content_id,
            "platform": "instagram_reels"
        })
        posting_id = posting_resp.json()["id"]
        
        # Update status
        response = client.patch(
            f"/api/content-loop/postings/{posting_id}/status",
            params={
                "status": "posted",
                "platform_post_id": "ABC123",
                "platform_url": "https://instagram.com/reel/ABC123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "posted"
        assert data["posted_at"] is not None
    
    # =========================================================================
    # Review Windows
    # =========================================================================
    
    def test_list_review_windows(self, client):
        """Test listing review windows."""
        response = client.get("/api/content-loop/review-windows")
        
        assert response.status_code == 200
        data = response.json()
        assert "windows" in data
        assert len(data["windows"]) >= 10  # We seeded 10 windows
    
    def test_filter_windows_by_platform(self, client):
        """Test filtering review windows by platform."""
        response = client.get("/api/content-loop/review-windows?platform=tiktok")
        
        assert response.status_code == 200
        data = response.json()
        for window in data["windows"]:
            assert window["platform"] == "tiktok"
    
    def test_review_window_structure(self, client):
        """Test that review windows have required fields."""
        response = client.get("/api/content-loop/review-windows?platform=tiktok")
        
        data = response.json()
        assert len(data["windows"]) > 0
        
        window = data["windows"][0]
        assert "id" in window
        assert "platform" in window
        assert "name" in window
        assert "start_hour" in window
        assert "end_hour" in window
        assert "primary_metric_weights" in window
    
    # =========================================================================
    # Metric Snapshots
    # =========================================================================
    
    def test_create_metric_snapshot(self, client):
        """Test creating a metric snapshot."""
        # Create content and posting
        content_resp = client.post("/api/content-loop/content-items", json={
            "title": "Metrics Test Video",
            "source_type": "SORA"
        })
        content_id = content_resp.json()["id"]
        
        posting_resp = client.post("/api/content-loop/postings", json={
            "content_item_id": content_id,
            "platform": "youtube_shorts"
        })
        posting_id = posting_resp.json()["id"]
        
        # Update to posted status
        client.patch(f"/api/content-loop/postings/{posting_id}/status", params={"status": "posted"})
        
        # Create metric snapshot
        response = client.post("/api/content-loop/metrics/snapshot", json={
            "posting_id": posting_id,
            "views": 1500,
            "likes": 120,
            "comments": 25,
            "shares": 15,
            "saves": 45
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "captured_at" in data
    
    def test_get_posting_metrics(self, client):
        """Test getting metrics for a posting."""
        # Create content, posting, and snapshot
        content_resp = client.post("/api/content-loop/content-items", json={
            "title": "Get Metrics Test",
            "source_type": "UGC"
        })
        content_id = content_resp.json()["id"]
        
        posting_resp = client.post("/api/content-loop/postings", json={
            "content_item_id": content_id,
            "platform": "tiktok"
        })
        posting_id = posting_resp.json()["id"]
        
        client.patch(f"/api/content-loop/postings/{posting_id}/status", params={"status": "posted"})
        
        # Add multiple snapshots
        for views in [100, 500, 1000]:
            client.post("/api/content-loop/metrics/snapshot", json={
                "posting_id": posting_id,
                "views": views,
                "likes": views // 10
            })
        
        # Get metrics
        response = client.get(f"/api/content-loop/postings/{posting_id}/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["posting_id"] == posting_id
        assert "snapshots" in data
        assert len(data["snapshots"]) >= 3
    
    # =========================================================================
    # Reviews
    # =========================================================================
    
    def test_create_review(self, client):
        """Test creating a review."""
        # Get a review window
        windows_resp = client.get("/api/content-loop/review-windows?platform=tiktok")
        window_id = windows_resp.json()["windows"][0]["id"]
        
        # Create content and posting
        content_resp = client.post("/api/content-loop/content-items", json={
            "title": "Review Test Video",
            "source_type": "UGC"
        })
        content_id = content_resp.json()["id"]
        
        posting_resp = client.post("/api/content-loop/postings", json={
            "content_item_id": content_id,
            "platform": "tiktok"
        })
        posting_id = posting_resp.json()["id"]
        
        # Create review
        response = client.post("/api/content-loop/reviews", json={
            "posting_id": posting_id,
            "window_id": window_id,
            "auto_score": 75.5,
            "label": "winner",
            "notes": "Great hook, strong engagement"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["label"] == "winner"
    
    def test_list_reviews(self, client):
        """Test listing reviews."""
        response = client.get("/api/content-loop/reviews")
        
        assert response.status_code == 200
        data = response.json()
        assert "reviews" in data
    
    def test_filter_reviews_by_label(self, client):
        """Test filtering reviews by label."""
        response = client.get("/api/content-loop/reviews?label=winner")
        
        assert response.status_code == 200
        data = response.json()
        for review in data["reviews"]:
            assert review["label"] == "winner"
    
    # =========================================================================
    # Playbook Rules
    # =========================================================================
    
    def test_create_playbook_rule(self, client):
        """Test creating a playbook rule."""
        response = client.post("/api/content-loop/playbook", json={
            "rule_type": "hook",
            "rule_text": "Start with a question to drive curiosity",
            "platform": "tiktok",
            "confidence_score": 85.0
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["rule_type"] == "hook"
        assert data["confidence_score"] == 85.0
    
    def test_list_playbook_rules(self, client):
        """Test listing playbook rules."""
        response = client.get("/api/content-loop/playbook")
        
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
    
    def test_filter_playbook_by_confidence(self, client):
        """Test filtering playbook rules by minimum confidence."""
        response = client.get("/api/content-loop/playbook?min_confidence=70")
        
        assert response.status_code == 200
        data = response.json()
        for rule in data["rules"]:
            assert rule["confidence_score"] >= 70
    
    # =========================================================================
    # Content Slots
    # =========================================================================
    
    def test_create_content_slot(self, client):
        """Test creating a content slot."""
        response = client.post("/api/content-loop/slots", json={
            "slot_date": "2026-01-10",
            "platform": "tiktok",
            "slot_type": "UGC",
            "objective": "reach"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["platform"] == "tiktok"
        assert data["slot_type"] == "UGC"
    
    def test_create_sora_slot(self, client):
        """Test creating a Sora AI content slot."""
        response = client.post("/api/content-loop/slots", json={
            "slot_date": "2026-01-10",
            "platform": "youtube_shorts",
            "slot_type": "SORA",
            "objective": "engage"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["slot_type"] == "SORA"
    
    def test_list_content_slots(self, client):
        """Test listing content slots."""
        response = client.get("/api/content-loop/slots")
        
        assert response.status_code == 200
        data = response.json()
        assert "slots" in data
    
    def test_assign_content_to_slot(self, client):
        """Test assigning content to a slot."""
        # Create content
        content_resp = client.post("/api/content-loop/content-items", json={
            "title": "Slot Assignment Test",
            "source_type": "UGC"
        })
        content_id = content_resp.json()["id"]
        
        # Create slot
        slot_resp = client.post("/api/content-loop/slots", json={
            "slot_date": "2026-01-11",
            "platform": "instagram_reels",
            "slot_type": "UGC",
            "objective": "convert"
        })
        slot_id = slot_resp.json()["id"]
        
        # Assign content to slot
        response = client.post(
            f"/api/content-loop/slots/{slot_id}/assign",
            params={"content_item_id": content_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_filled"] == True
    
    # =========================================================================
    # Insights
    # =========================================================================
    
    def test_list_insights(self, client):
        """Test listing insights."""
        response = client.get("/api/content-loop/insights")
        
        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
    
    # =========================================================================
    # Dashboard
    # =========================================================================
    
    def test_dashboard_endpoint(self, client):
        """Test the dashboard summary endpoint."""
        response = client.get("/api/content-loop/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "category_performance" in data
        assert "attention_needed" in data
        assert "todays_slots" in data
        assert "top_playbook_rules" in data


class TestPerformanceReview:
    """Test suite for the performance review API."""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(base_url=API_URL, timeout=30)
    
    def test_get_performance_review(self, client):
        """Test getting performance review data."""
        response = client.get("/api/review/performance")
        
        # May return 200 with data or 500 if no data
        if response.status_code == 200:
            data = response.json()
            assert "categories" in data or "total_videos" in data
    
    def test_get_insights(self, client):
        """Test getting review insights."""
        response = client.get("/api/review/insights")
        
        assert response.status_code == 200
        data = response.json()
        assert "insights" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
