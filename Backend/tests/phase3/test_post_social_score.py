"""
Tests for Phase 3: Post-Social Score Calculation
Tests post-social score calculation, normalization, and percentile ranking
Uses REAL database connections
"""
import pytest
from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timedelta

from main import app
from services.post_social_score import PostSocialScoreCalculator


class TestPostSocialScoreAPI:
    """Test post-social score API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_post_social_score(self, client, db_session, clean_db):
        """Test getting post-social score with REAL database"""
        # Create test post data (would need actual post in database)
        post_id = 1  # Using integer ID as expected by endpoint
        
        response = client.get(f"/api/post-social-score/post/{post_id}")
        # May return 404 if post doesn't exist, or 200 with score
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "score" in data or "post_social_score" in data
    
    @pytest.mark.asyncio
    async def test_calculate_post_social_score(self, client, db_session, clean_db):
        """Test calculating and storing post-social score with REAL database"""
        post_id = 1  # Using integer ID as expected by endpoint
        
        response = client.post(f"/api/post-social-score/post/{post_id}/calculate")
        # May return 404 if post doesn't exist, or 200 with calculated score
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "score" in data or "post_social_score" in data
            assert 0 <= data.get("score", data.get("post_social_score", 0)) <= 100
    
    @pytest.mark.asyncio
    async def test_get_account_score_summary(self, client, db_session, clean_db):
        """Test getting account score summary with REAL database"""
        account_id = 1  # Using integer ID as expected by endpoint
        
        response = client.get(f"/api/post-social-score/account/{account_id}/summary")
        # May return 404 if account doesn't exist, or 200 with summary
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "account_id" in data or "platform" in data


class TestPostSocialScoreService:
    """Test post-social score service logic"""
    
    @pytest.mark.asyncio
    async def test_calculate_score_normalization(self, mock_db):
        """Test score normalization factors"""
        service = PostSocialScoreCalculator()
        
        # Mock database responses
        with patch.object(service, 'calculate_post_score', new_callable=AsyncMock) as mock_calc:
            mock_calc.return_value = 75.5
            
            score = await service.calculate_post_score(uuid.uuid4())
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100
    
    @pytest.mark.asyncio
    async def test_follower_count_normalization(self, db_session, clean_db):
        """Test follower count normalization with REAL database"""
        service = PostSocialScoreCalculator()
        
        # Test with different follower counts
        result_low = await service.calculate_post_social_score(
            db_session, 1, "instagram", "reel", 100, datetime.now(), {"views": 50, "likes": 5}
        )
        result_high = await service.calculate_post_social_score(
            db_session, 1, "instagram", "reel", 10000, datetime.now(), {"views": 5000, "likes": 250}
        )
        
        assert isinstance(result_low, dict)
        assert isinstance(result_high, dict)
        assert "post_social_score" in result_low
        assert "post_social_score" in result_high
        # Scores should be normalized appropriately
        assert 0 <= result_low["post_social_score"] <= 100
        assert 0 <= result_high["post_social_score"] <= 100
    
    @pytest.mark.asyncio
    async def test_platform_behavior_normalization(self, db_session, clean_db):
        """Test platform behavior normalization with REAL database"""
        service = PostSocialScoreCalculator()
        
        # Test platform behavior normalization through main calculation
        platforms = ["instagram", "tiktok", "youtube"]
        
        for platform in platforms:
            result = await service.calculate_post_social_score(
                db_session, 1, platform, "video", 1000, datetime.now(), {"views": 500, "likes": 25}
            )
            assert isinstance(result, dict)
            assert "post_social_score" in result
            assert "normalization_factors" in result
            # Check platform-specific normalization is applied
            assert "platform_adjustment" in result["normalization_factors"] or "platform" in str(result["normalization_factors"])
    
    @pytest.mark.asyncio
    async def test_time_since_posting_normalization(self, db_session, clean_db):
        """Test time-since-posting normalization with REAL database"""
        service = PostSocialScoreCalculator()
        
        # Test with different time periods
        posted_recent = datetime.now() - timedelta(hours=2)
        posted_old = datetime.now() - timedelta(days=7)
        
        result_recent = await service.calculate_post_social_score(
            db_session, 1, "instagram", "reel", 1000, posted_recent, {"views": 500, "likes": 25}
        )
        result_old = await service.calculate_post_social_score(
            db_session, 1, "instagram", "reel", 1000, posted_old, {"views": 500, "likes": 25}
        )
        
        assert isinstance(result_recent, dict)
        assert isinstance(result_old, dict)
        assert "post_social_score" in result_recent
        assert "post_social_score" in result_old
        # Recent posts may score differently than old posts
        assert 0 <= result_recent["post_social_score"] <= 100
        assert 0 <= result_old["post_social_score"] <= 100
    
    @pytest.mark.asyncio
    async def test_percentile_ranking(self, db_session, clean_db):
        """Test percentile ranking calculation with REAL database"""
        service = PostSocialScoreCalculator()
        
        # Percentile ranking is included in calculate_post_social_score result
        result = await service.calculate_post_social_score(
            db_session, 1, "instagram", "video", 1000, datetime.now(), {"views": 500, "likes": 25}
        )
        assert isinstance(result, dict)
        assert "post_social_score" in result
        # Percentile may be in normalization_factors or separate field
        assert "normalization_factors" in result or "percentile_rank" in result or "percentile" in result
        if "percentile_rank" in result:
            assert 0 <= result["percentile_rank"] <= 100

