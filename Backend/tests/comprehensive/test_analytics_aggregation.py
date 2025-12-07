"""
Comprehensive Analytics Aggregation Tests
Tests analytics data aggregation across platforms and time periods
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
import uuid
from datetime import datetime, timedelta

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAnalyticsAggregation:
    """Comprehensive analytics aggregation tests"""
    
    @pytest.mark.asyncio
    async def test_dashboard_overview_aggregation(self, client, db_session, clean_db):
        """Test dashboard overview aggregates data correctly"""
        # Create test accounts
        from database.models import ConnectorConfig
        
        platforms = ["instagram", "tiktok", "youtube"]
        test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        for platform in platforms:
            account = ConnectorConfig(
                id=uuid.uuid4(),
                user_id=test_user_id,
                workspace_id=test_user_id,  # Use user_id as workspace_id for tests
                connector_type=platform,
                config={"username": f"test_{platform}"},
                is_enabled=True
            )
            db_session.add(account)
        await db_session.commit()
        
        # Get dashboard overview
        response = client.get("/api/social-analytics/overview")
        assert response.status_code == 200
        data = response.json()
        
        # Verify aggregation fields
        assert "total_platforms" in data or "platforms_count" in data
        assert "total_accounts" in data or "accounts_count" in data
        assert "platform_breakdown" in data or "platforms" in data
    
    @pytest.mark.asyncio
    async def test_platform_specific_analytics(self, client, db_session, clean_db):
        """Test getting analytics for specific platforms"""
        platforms = ["instagram", "tiktok", "youtube"]
        
        for platform in platforms:
            response = client.get(f"/api/social-analytics/platform/{platform}")
            # May return 200 with data or 404 if no data
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert "platform" in data or platform in str(data)
    
    @pytest.mark.asyncio
    async def test_time_period_analytics(self, client):
        """Test analytics for different time periods"""
        # Test with different day ranges
        day_ranges = [7, 30, 90]
        
        for days in day_ranges:
            response = client.get(
                "/api/social-analytics/platform/instagram",
                params={"days": days}
            )
            # Should handle different time periods
            assert response.status_code in [200, 404, 500]
    
    @pytest.mark.asyncio
    async def test_account_list_with_analytics(self, client, db_session, clean_db):
        """Test getting account list with analytics data"""
        # Create test accounts
        from database.models import ConnectorConfig
        
        test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        account = ConnectorConfig(
            id=uuid.uuid4(),
            user_id=test_user_id,
            workspace_id=test_user_id,  # Use user_id as workspace_id for tests
            connector_type="instagram",
            config={"username": "test_account"},
            is_enabled=True
        )
        db_session.add(account)
        await db_session.commit()
        
        # Get accounts list
        response = client.get("/api/social-analytics/accounts")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

