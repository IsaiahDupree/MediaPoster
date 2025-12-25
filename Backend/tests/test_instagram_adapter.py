"""
Unit Tests for Instagram Adapter
Tests the RapidAPI Instagram adapter functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.instagram.adapters import RapidApiInstagramAdapter
from services.instagram.adapters.base import MediaType


class TestRapidApiInstagramAdapter:
    """Test suite for RapidAPI Instagram adapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance with mock API key"""
        return RapidApiInstagramAdapter(api_key="test_key_123")
    
    def test_adapter_initialization(self, adapter):
        """Test adapter initializes correctly"""
        assert adapter.api_key == "test_key_123"
        assert adapter.name == "rapidapi-instagram-looter2"
        assert adapter.type == "scraper"
        assert adapter.host == "instagram-looter2.p.rapidapi.com"
    
    def test_get_headers(self, adapter):
        """Test headers are correctly formatted"""
        headers = adapter._get_headers()
        assert headers["X-RapidAPI-Key"] == "test_key_123"
        assert headers["X-RapidAPI-Host"] == "instagram-looter2.p.rapidapi.com"
    
    @pytest.mark.asyncio
    async def test_get_profile_success(self, adapter):
        """Test successful profile fetch"""
        mock_response = {
            "data": {
                "id": "123456",
                "username": "testuser",
                "full_name": "Test User",
                "biography": "Test bio",
                "follower_count": 1000,
                "following_count": 500,
                "media_count": 100,
                "is_verified": True,
                "profile_pic_url": "https://example.com/pic.jpg"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=Mock(
                    status_code=200,
                    json=Mock(return_value=mock_response)
                )
            )
            
            profile = await adapter.get_profile("testuser")
            
            assert profile.id == "123456"
            assert profile.username == "testuser"
            assert profile.followers_count == 1000
            assert profile.is_verified is True
    
    @pytest.mark.asyncio
    async def test_get_profile_http_error(self, adapter):
        """Test profile fetch with HTTP error"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("HTTP 404")
            )
            
            with pytest.raises(Exception):
                await adapter.get_profile("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_media_with_pagination(self, adapter):
        """Test media fetch with pagination"""
        mock_response = {
            "data": {
                "items": [
                    {
                        "id": "post1",
                        "media_type": "REEL",
                        "caption": {"text": "Test caption"},
                        "like_count": 100,
                        "comment_count": 10,
                        "taken_at": 1640000000
                    }
                ],
                "pagination_token": "next_cursor_123",
                "has_more": True
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=Mock(
                    status_code=200,
                    json=Mock(return_value=mock_response)
                )
            )
            
            media_page = await adapter.get_media("testuser", limit=10)
            
            assert len(media_page.items) == 1
            assert media_page.cursor == "next_cursor_123"
            assert media_page.has_more is True
            assert media_page.items[0].id == "post1"
    
    def test_extract_hashtags(self, adapter):
        """Test hashtag extraction from caption"""
        caption = "Check out my #fitness #workout routine! #health"
        hashtags = adapter._extract_hashtags(caption)
        
        assert len(hashtags) == 3
        assert "fitness" in hashtags
        assert "workout" in hashtags
        assert "health" in hashtags
    
    def test_extract_mentions(self, adapter):
        """Test mention extraction from caption"""
        caption = "Thanks @user1 and @user2 for the collaboration!"
        mentions = adapter._extract_mentions(caption)
        
        assert len(mentions) == 2
        assert "user1" in mentions
        assert "user2" in mentions
    
    def test_clean_tag(self, adapter):
        """Test hashtag cleaning"""
        assert adapter._clean_tag("#fitness") == "fitness"
        assert adapter._clean_tag("fitness") == "fitness"
        assert adapter._clean_tag("##fitness") == "fitness"
    
    @pytest.mark.asyncio
    async def test_parse_media_item_reel(self, adapter):
        """Test parsing reel media item"""
        item_data = {
            "id": "reel123",
            "product_type": "clips",
            "caption": {"text": "My reel #viral"},
            "like_count": 500,
            "comment_count": 50,
            "play_count": 10000,
            "taken_at": 1640000000,
            "video_url": "https://example.com/video.mp4",
            "audio": {
                "id": "audio123",
                "title": "Trending Sound",
                "artist": "Artist Name"
            },
            "code": "ABC123"
        }
        
        media_item = adapter._parse_media_item(item_data)
        
        assert media_item.id == "reel123"
        assert media_item.media_type == MediaType.REEL
        assert media_item.caption == "My reel #viral"
        assert media_item.like_count == 500
        assert media_item.play_count == 10000
        assert media_item.audio is not None
        assert media_item.audio.id == "audio123"
        assert len(media_item.hashtags) == 1
        assert "viral" in media_item.hashtags
    
    @pytest.mark.asyncio
    async def test_is_healthy(self, adapter):
        """Test health check"""
        with patch.object(adapter, 'get_profile', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(username="instagram")
            
            is_healthy = await adapter.is_healthy()
            assert is_healthy is True
            mock_get.assert_called_once_with("instagram")
    
    @pytest.mark.asyncio
    async def test_is_healthy_failure(self, adapter):
        """Test health check failure"""
        with patch.object(adapter, 'get_profile', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API Error")
            
            is_healthy = await adapter.is_healthy()
            assert is_healthy is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
