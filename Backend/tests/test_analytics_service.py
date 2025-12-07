import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import date, timedelta
from services.analytics_service import AnalyticsService
from database.models import WeeklyMetric, PlatformPost, PlatformCheckback

@pytest.mark.asyncio
async def test_calculate_weekly_metrics():
    # Mock Sync Session for AnalyticsService (since it was written as Sync)
    # Wait, if AnalyticsService is Sync, I can't easily test it with pytest-asyncio unless I wrap it or mock it as sync.
    # But the service method `calculate_weekly_metrics` is synchronous (def ...).
    
    mock_db = MagicMock()
    service = AnalyticsService(mock_db)
    
    week_start = date.today()
    user_id = uuid4()
    
    # Mock posts query
    mock_posts = [
        PlatformPost(id=uuid4(), platform="tiktok", platform_post_id="p1"),
        PlatformPost(id=uuid4(), platform="instagram", platform_post_id="p2")
    ]
    
    # Custom MockQuery class to handle fluent interface and formatting
    class MockQuery:
        def __init__(self, items=None, first_results=None):
            self.items = items or []
            self.first_results = first_results or []
            self.first_call_count = 0
            
        def filter(self, *args, **kwargs):
            return self

        def filter_by(self, *args, **kwargs):
            return self
            
        def join(self, *args, **kwargs):
            return self
            
        def order_by(self, *args, **kwargs):
            return self
            
        def all(self):
            return self.items
            
        def first(self):
            if self.first_call_count < len(self.first_results):
                result = self.first_results[self.first_call_count]
                self.first_call_count += 1
                return result
            return None
            
        def scalar(self):
            return 0.5
            
        def __str__(self):
            return "MockQuery"
            
        def __format__(self, format_spec):
            return "MockQuery"

    # Mock checkbacks
    mock_checkback = PlatformCheckback(
        views=100, likes=10, comments=5, shares=2, saves=1,
        profile_taps=1, link_clicks=1, avg_watch_pct=0.5
    )

    # Initialize MockQuery with posts and sequence of first() results
    # 1. checkback query -> returns mock_checkback
    # 2. checkback query (2nd post) -> returns mock_checkback
    # 3. weekly metric query -> returns None
    # Note: The service iterates over posts. We have 2 posts.
    # So first() will be called for checkback for post 1, then post 2.
    # Then first() will be called for WeeklyMetric check.
    mock_query_instance = MockQuery(
        items=mock_posts,
        first_results=[mock_checkback, mock_checkback, None]
    )
    
    mock_db.query.return_value = mock_query_instance
    
    result = service.calculate_weekly_metrics(week_start, user_id)
    
    assert result["total_posts"] == 2
    assert result["total_views"] == 200 # 100 * 2 posts
    assert result["engaged_reach"] == 2 # 2 posts engaged
    
    # Verify db.add was called (for new WeeklyMetric)
    mock_db.add.assert_called()
    mock_db.commit.assert_called()

def test_get_overview_dashboard():
    mock_db = MagicMock()
    service = AnalyticsService(mock_db)
    
    # Mock WeeklyMetric data
    mock_metrics = [
        WeeklyMetric(
            week_start_date=date.today(),
            engaged_reach=100,
            content_leverage_score=5.0,
            warm_lead_flow=10,
            total_posts=5
        ),
        WeeklyMetric(
            week_start_date=date.today() - timedelta(days=7),
            engaged_reach=80,
            content_leverage_score=4.0,
            warm_lead_flow=8,
            total_posts=4
        )
    ]
    
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_metrics
    
    result = service.get_overview_dashboard(weeks=4)
    
    assert result["current_week"]["engaged_reach"] == 100
    assert result["current_week"]["engaged_reach_delta_pct"] == 25.0 # (100-80)/80 * 100
    assert len(result["trend_data"]) == 2
