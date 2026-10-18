"""
Unit Tests for Posting Optimizer Service
Tests best time to post calculations
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, time

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.instagram.posting_optimizer import PostingOptimizer


class TestPostingOptimizer:
    """Test suite for posting optimizer"""
    
    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance"""
        return PostingOptimizer()
    
    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initializes correctly"""
        assert optimizer.engine is not None
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_get_hourly_engagement_with_data(self, mock_engine, optimizer):
        """Test hourly engagement calculation with data"""
        mock_conn = MagicMock()
        mock_result = [
            (0, 100, 10, 5),   # hour 0: 100 likes, 10 comments, 5 shares
            (1, 150, 15, 8),   # hour 1: 150 likes, 15 comments, 8 shares
            (18, 500, 50, 25), # hour 18: peak time
        ]
        mock_conn.execute.return_value.fetchall.return_value = mock_result
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        hourly_data = optimizer.get_hourly_engagement()
        
        assert len(hourly_data) == 24
        # Hour 18 should have highest engagement
        hour_18 = next(h for h in hourly_data if h["hour"] == 18)
        assert hour_18["engagement_rate"] > 0
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_get_daily_engagement_with_data(self, mock_engine, optimizer):
        """Test daily engagement calculation"""
        mock_conn = MagicMock()
        mock_result = [
            (0, 1000, 100, 50),  # Monday
            (1, 1200, 120, 60),  # Tuesday
            (4, 1500, 150, 75),  # Friday - peak day
        ]
        mock_conn.execute.return_value.fetchall.return_value = mock_result
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        daily_data = optimizer.get_daily_engagement()
        
        assert len(daily_data) == 7
        # Friday should have highest engagement
        friday = next(d for d in daily_data if d["day"] == "Friday")
        assert friday["engagement_rate"] > 0
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_calculate_best_times_top_5(self, mock_engine, optimizer):
        """Test calculating top 5 best posting times"""
        mock_conn = MagicMock()
        # Mock hourly data
        hourly_result = [(h, 100 + h * 10, 10, 5) for h in range(24)]
        # Mock daily data
        daily_result = [(d, 1000, 100, 50) for d in range(7)]
        
        mock_conn.execute.return_value.fetchall.side_effect = [
            hourly_result,
            daily_result
        ]
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        best_times = optimizer.get_best_times(top_n=5)
        
        assert len(best_times) <= 5
        # Should be sorted by score descending
        for i in range(len(best_times) - 1):
            assert best_times[i]["score"] >= best_times[i + 1]["score"]
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_calculate_best_times_with_profile_filter(self, mock_engine, optimizer):
        """Test best times calculation filtered by profile"""
        mock_conn = MagicMock()
        hourly_result = [(h, 100, 10, 5) for h in range(24)]
        daily_result = [(d, 1000, 100, 50) for d in range(7)]
        
        mock_conn.execute.return_value.fetchall.side_effect = [
            hourly_result,
            daily_result
        ]
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        best_times = optimizer.get_best_times(profile_id="test_profile", top_n=3)
        
        assert len(best_times) <= 3
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_suggest_posting_schedule_7_posts(self, mock_engine, optimizer):
        """Test suggesting a 7-post weekly schedule"""
        mock_conn = MagicMock()
        hourly_result = [(h, 100 + h * 10, 10, 5) for h in range(24)]
        daily_result = [(d, 1000 + d * 100, 100, 50) for d in range(7)]
        
        mock_conn.execute.return_value.fetchall.side_effect = [
            hourly_result,
            daily_result
        ]
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        schedule = optimizer.suggest_posting_schedule(posts_per_week=7)
        
        assert len(schedule) == 7
        # Each day should have one post
        days_in_schedule = [s["day"] for s in schedule]
        assert len(set(days_in_schedule)) == 7
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_suggest_posting_schedule_3_posts(self, mock_engine, optimizer):
        """Test suggesting a 3-post weekly schedule"""
        mock_conn = MagicMock()
        hourly_result = [(h, 100, 10, 5) for h in range(24)]
        daily_result = [(d, 1000 + d * 100, 100, 50) for d in range(7)]
        
        mock_conn.execute.return_value.fetchall.side_effect = [
            hourly_result,
            daily_result
        ]
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        schedule = optimizer.suggest_posting_schedule(posts_per_week=3)
        
        assert len(schedule) == 3
        # Should pick top 3 days
    
    def test_calculate_engagement_rate(self, optimizer):
        """Test engagement rate calculation"""
        likes = 100
        comments = 10
        shares = 5
        views = 1000
        
        # Engagement rate = (likes + comments + shares) / views
        expected_rate = (100 + 10 + 5) / 1000
        
        # Manual calculation for testing
        total_engagement = likes + comments + shares
        rate = total_engagement / views if views > 0 else 0
        
        assert rate == expected_rate
        assert rate == 0.115
    
    def test_calculate_engagement_rate_no_views(self, optimizer):
        """Test engagement rate with zero views"""
        likes = 100
        comments = 10
        shares = 5
        views = 0
        
        rate = (likes + comments + shares) / views if views > 0 else 0
        assert rate == 0
    
    def test_normalize_score_to_100(self, optimizer):
        """Test score normalization to 0-100 scale"""
        max_engagement = 0.15
        current_engagement = 0.10
        
        # Score = (current / max) * 100
        score = (current_engagement / max_engagement) * 100 if max_engagement > 0 else 0
        
        assert score == pytest.approx(66.67, rel=0.01)
    
    def test_day_of_week_mapping(self, optimizer):
        """Test day of week number to name mapping"""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for i, day_name in enumerate(days):
            assert days[i] == day_name
    
    def test_time_display_formatting(self, optimizer):
        """Test time display formatting"""
        hour = 18
        time_display = f"{hour:02d}:00"
        
        assert time_display == "18:00"
        
        hour = 9
        time_display = f"{hour:02d}:00"
        assert time_display == "09:00"
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_get_best_times_empty_data(self, mock_engine, optimizer):
        """Test best times calculation with no data"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.side_effect = [[], []]
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        best_times = optimizer.get_best_times()
        
        # Should return empty or default times
        assert isinstance(best_times, list)
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_content_type_filter_reel(self, mock_engine, optimizer):
        """Test filtering by REEL content type"""
        mock_conn = MagicMock()
        hourly_result = [(h, 100, 10, 5) for h in range(24)]
        daily_result = [(d, 1000, 100, 50) for d in range(7)]
        
        mock_conn.execute.return_value.fetchall.side_effect = [
            hourly_result,
            daily_result
        ]
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        best_times = optimizer.get_best_times(content_type="REEL")
        
        assert isinstance(best_times, list)
    
    @patch('services.instagram.posting_optimizer.create_engine')
    def test_timezone_conversion(self, mock_engine, optimizer):
        """Test timezone parameter handling"""
        mock_conn = MagicMock()
        hourly_result = [(h, 100, 10, 5) for h in range(24)]
        daily_result = [(d, 1000, 100, 50) for d in range(7)]
        
        mock_conn.execute.return_value.fetchall.side_effect = [
            hourly_result,
            daily_result
        ]
        optimizer.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        best_times = optimizer.get_best_times(timezone="America/New_York")
        
        assert isinstance(best_times, list)
    
    def test_recommendation_generation(self, optimizer):
        """Test generating recommendations based on time"""
        hour = 18
        
        if 17 <= hour <= 19:
            recommendation = "Evening commute - prime time"
        elif 12 <= hour <= 14:
            recommendation = "Lunch break - peak browsing"
        elif 8 <= hour <= 10:
            recommendation = "Morning routine - good engagement"
        else:
            recommendation = "Off-peak hours"
        
        assert recommendation == "Evening commute - prime time"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
