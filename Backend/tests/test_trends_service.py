"""
Unit Tests for Trends Services
Tests trend crawler, velocity engine, and trend cards
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.instagram.trend_crawler import TrendCrawler
from services.instagram.velocity_engine import VelocityEngine
from services.instagram.trend_cards_library import TrendCardsLibrary


class TestTrendCrawler:
    """Test suite for trend crawler"""
    
    @pytest.fixture
    def crawler(self):
        """Create crawler instance"""
        return TrendCrawler(seed_accounts=["test_account"])
    
    def test_crawler_initialization(self, crawler):
        """Test crawler initializes with seed accounts"""
        assert len(crawler.seed_accounts) == 1
        assert "test_account" in crawler.seed_accounts
    
    def test_detect_format_text_hook(self, crawler):
        """Test format detection for text-hook"""
        from services.instagram.adapters import MediaItem, MediaType
        from datetime import datetime
        
        reel = MediaItem(
            id="test1",
            media_type=MediaType.REEL,
            caption="Wait for it... #viral",
            permalink="https://instagram.com/p/test",
            thumbnail_url="https://example.com/thumb.jpg",
            like_count=100,
            comment_count=10,
            timestamp=datetime.now()
        )
        
        format_type = crawler._detect_format(reel)
        assert format_type == "text-hook-short-form"
    
    def test_detect_format_pov(self, crawler):
        """Test format detection for POV"""
        from services.instagram.adapters import MediaItem, MediaType
        from datetime import datetime
        
        reel = MediaItem(
            id="test2",
            media_type=MediaType.REEL,
            caption="POV: You're living your best life",
            permalink="https://instagram.com/p/test",
            thumbnail_url="https://example.com/thumb.jpg",
            like_count=100,
            comment_count=10,
            timestamp=datetime.now()
        )
        
        format_type = crawler._detect_format(reel)
        assert format_type == "pov"
    
    def test_detect_format_tutorial(self, crawler):
        """Test format detection for tutorial"""
        from services.instagram.adapters import MediaItem, MediaType
        from datetime import datetime
        
        reel = MediaItem(
            id="test3",
            media_type=MediaType.REEL,
            caption="How to make the perfect smoothie - step by step guide",
            permalink="https://instagram.com/p/test",
            thumbnail_url="https://example.com/thumb.jpg",
            like_count=100,
            comment_count=10,
            timestamp=datetime.now()
        )
        
        format_type = crawler._detect_format(reel)
        assert format_type == "tutorial"


class TestVelocityEngine:
    """Test suite for velocity engine"""
    
    @pytest.fixture
    def engine(self):
        """Create velocity engine instance"""
        return VelocityEngine()
    
    def test_engine_initialization(self, engine):
        """Test engine initializes correctly"""
        assert engine.engine is not None
    
    @patch('services.instagram.velocity_engine.create_engine')
    def test_calculate_single_velocity_growth(self, mock_engine):
        """Test velocity calculation with growth"""
        engine = VelocityEngine()
        
        # Mock database responses
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = [
            MagicMock(fetchone=lambda: (100,)),  # Current usage
            MagicMock(fetchone=lambda: (50,))    # Previous usage
        ]
        engine.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        velocity = engine._calculate_single_velocity(
            "audio",
            "test_audio",
            date.today(),
            date.today() - timedelta(days=7)
        )
        
        # Velocity = (100 - 50) / 50 = 1.0 (100% growth)
        assert velocity == 1.0
    
    @patch('services.instagram.velocity_engine.create_engine')
    def test_calculate_single_velocity_decline(self, mock_engine):
        """Test velocity calculation with decline"""
        engine = VelocityEngine()
        
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = [
            MagicMock(fetchone=lambda: (50,)),   # Current usage
            MagicMock(fetchone=lambda: (100,))   # Previous usage
        ]
        engine.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        velocity = engine._calculate_single_velocity(
            "audio",
            "test_audio",
            date.today(),
            date.today() - timedelta(days=7)
        )
        
        # Velocity = (50 - 100) / 100 = -0.5 (50% decline)
        assert velocity == -0.5
    
    @patch('services.instagram.velocity_engine.create_engine')
    def test_calculate_single_velocity_no_previous_data(self, mock_engine):
        """Test velocity calculation with no previous data"""
        engine = VelocityEngine()
        
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = [
            MagicMock(fetchone=lambda: (100,)),  # Current usage
            MagicMock(fetchone=lambda: (0,))     # No previous usage
        ]
        engine.engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        
        velocity = engine._calculate_single_velocity(
            "audio",
            "test_audio",
            date.today(),
            date.today() - timedelta(days=7)
        )
        
        # Should return 1.0 for 100% growth from zero
        assert velocity == 1.0


class TestTrendCardsLibrary:
    """Test suite for trend cards library"""
    
    @pytest.fixture
    def library(self):
        """Create trend cards library instance"""
        return TrendCardsLibrary()
    
    def test_library_initialization(self, library):
        """Test library initializes correctly"""
        assert library.engine is not None
    
    def test_match_content_to_cards_pov(self, library):
        """Test content matching for POV format"""
        caption = "POV: You're the main character"
        hashtags = ["pov", "maincharacter"]
        
        with patch.object(library, 'get_card_by_format_type') as mock_get:
            mock_get.return_value = {
                "id": "card1",
                "name": "POV",
                "format_type": "pov",
                "velocity_7d": 0.5,
                "trending_score": 85.0
            }
            
            matches = library.match_content_to_cards(caption, hashtags)
            
            assert len(matches) > 0
            assert matches[0]["format_type"] == "pov"
            assert matches[0]["confidence"] > 0
    
    def test_match_content_to_cards_tutorial(self, library):
        """Test content matching for tutorial format"""
        caption = "How to make the perfect latte - step by step tutorial"
        hashtags = ["tutorial", "howto", "coffee"]
        
        with patch.object(library, 'get_card_by_format_type') as mock_get:
            mock_get.return_value = {
                "id": "card2",
                "name": "Tutorial",
                "format_type": "tutorial",
                "velocity_7d": 0.3,
                "trending_score": 75.0
            }
            
            matches = library.match_content_to_cards(caption, hashtags)
            
            assert len(matches) > 0
            # Should have high confidence due to multiple keyword matches
            tutorial_match = next((m for m in matches if m["format_type"] == "tutorial"), None)
            assert tutorial_match is not None
            assert tutorial_match["confidence"] > 0.3
    
    def test_match_content_no_matches(self, library):
        """Test content matching with no clear format"""
        caption = "Just a regular post"
        hashtags = []
        
        with patch.object(library, 'get_card_by_format_type') as mock_get:
            mock_get.return_value = None
            
            matches = library.match_content_to_cards(caption, hashtags)
            
            # Should return empty or very low confidence matches
            assert len(matches) == 0 or all(m["confidence"] < 0.2 for m in matches)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
