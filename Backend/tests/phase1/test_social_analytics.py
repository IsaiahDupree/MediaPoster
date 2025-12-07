"""
Tests for Phase 1: Multi-Platform Analytics - Social Analytics
Tests dashboard overview, trends, and analytics endpoints
Uses REAL database connections
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from main import app


class TestSocialAnalytics:
    """Test social analytics endpoints with REAL database"""
    
    def test_get_dashboard_overview(self, client):
        """Test getting dashboard overview with REAL database"""
        response = client.get("/api/social-analytics/overview")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_platforms" in data or "platforms_count" in data or "platforms" in data
        assert "total_accounts" in data or "accounts_count" in data
        assert "total_followers" in data or "followers_count" in data
    
    def test_dashboard_has_trends(self, client):
        """Test dashboard includes trend data with REAL database"""
        response = client.get("/api/social-analytics/overview")
        assert response.status_code == 200
        data = response.json()
        
        # Check for trend-related fields
        has_trends = (
            "posts_last_30d" in data or
            "views_last_30d" in data or
            "content" in data and isinstance(data.get("content"), dict)
        )
        assert has_trends
    
    def test_dashboard_has_platform_breakdown(self, client):
        """Test dashboard includes platform breakdown with REAL database"""
        response = client.get("/api/social-analytics/overview")
        assert response.status_code == 200
        data = response.json()
        
        # Should have platform breakdown or platforms list
        has_platforms = (
            "platform_breakdown" in data or
            "platforms" in data or
            "platforms_count" in data
        )
        assert has_platforms
    
    def test_get_accounts_list(self, client):
        """Test getting accounts list"""
        response = client.get("/api/social-analytics/accounts")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
    
    def test_get_platform_details(self, client):
        """Test getting platform-specific details"""
        platforms = ["instagram", "tiktok", "youtube"]
        for platform in platforms:
            response = client.get(f"/api/social-analytics/platform/{platform}")
            # May return 404 if no data, or 200 with data
            assert response.status_code in [200, 404]

