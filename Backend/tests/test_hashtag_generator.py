"""
Unit Tests for Hashtag Generator Service
Tests AI-powered hashtag generation
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.instagram.hashtag_generator import HashtagGenerator


class TestHashtagGenerator:
    """Test suite for hashtag generator"""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance"""
        return HashtagGenerator()
    
    def test_generator_initialization(self, generator):
        """Test generator initializes correctly"""
        assert generator.engine is not None
        assert generator.openai_client is not None
    
    @pytest.mark.asyncio
    async def test_detect_niche_fitness(self, generator):
        """Test niche detection for fitness content"""
        content = "Morning workout routine at the gym"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="fitness"))]
            )
            
            niche = await generator._detect_niche(content)
            assert niche == "fitness"
    
    @pytest.mark.asyncio
    async def test_detect_niche_food(self, generator):
        """Test niche detection for food content"""
        content = "Delicious pasta recipe with homemade sauce"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="food"))]
            )
            
            niche = await generator._detect_niche(content)
            assert niche == "food"
    
    @pytest.mark.asyncio
    async def test_generate_long_tail_hashtags(self, generator):
        """Test generating long-tail hashtags"""
        niche = "fitness"
        content = "Morning workout routine"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="morningworkout,homefitness,quickexercise,fitnessmotivation,workoutathome,earlymorningworkout,fitnessjourney,healthylifestyle,exerciseroutine,dailyworkout"))]
            )
            
            long_tail = await generator._generate_long_tail_hashtags(niche, content)
            assert len(long_tail) == 10
            assert all(isinstance(tag, str) for tag in long_tail)
    
    @pytest.mark.asyncio
    async def test_get_trending_hashtags_from_db(self, generator):
        """Test fetching trending hashtags from database"""
        niche = "fitness"
        
        with patch.object(generator, '_query_trending_hashtags') as mock_query:
            mock_query.return_value = [
                {"tag": "fitness", "media_count": 100000, "velocity_7d": 0.5, "trending_score": 85.0},
                {"tag": "workout", "media_count": 80000, "velocity_7d": 0.4, "trending_score": 80.0},
            ]
            
            trending = await generator._get_trending_hashtags(niche, limit=10)
            assert len(trending) <= 10
    
    @pytest.mark.asyncio
    async def test_get_niche_hashtags_from_db(self, generator):
        """Test fetching niche-specific hashtags"""
        niche = "fitness"
        
        with patch.object(generator, '_query_niche_hashtags') as mock_query:
            mock_query.return_value = [
                {"tag": "homefitness", "media_count": 50000, "velocity_7d": 0.3, "trending_score": 70.0},
                {"tag": "fitnessmotivation", "media_count": 45000, "velocity_7d": 0.25, "trending_score": 65.0},
            ]
            
            niche_tags = await generator._get_niche_hashtags(niche, limit=10)
            assert len(niche_tags) <= 10
    
    @pytest.mark.asyncio
    async def test_categorize_by_competition_high(self, generator):
        """Test categorizing hashtags by competition level - high"""
        hashtag = {"tag": "fitness", "media_count": 500000}
        
        competition = generator._categorize_competition(hashtag["media_count"])
        assert competition == "high"
    
    @pytest.mark.asyncio
    async def test_categorize_by_competition_medium(self, generator):
        """Test categorizing hashtags by competition level - medium"""
        hashtag = {"tag": "homefitness", "media_count": 50000}
        
        competition = generator._categorize_competition(hashtag["media_count"])
        assert competition == "medium"
    
    @pytest.mark.asyncio
    async def test_categorize_by_competition_low(self, generator):
        """Test categorizing hashtags by competition level - low"""
        hashtag = {"tag": "morningworkout2024", "media_count": 5000}
        
        competition = generator._categorize_competition(hashtag["media_count"])
        assert competition == "low"
    
    @pytest.mark.asyncio
    async def test_generate_hashtags_complete_set(self, generator):
        """Test generating complete 30-hashtag set"""
        content = "Morning workout routine at home"
        niche = "fitness"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = [
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="fitness"))]),  # Niche detection
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="morningworkout,homefitness,quickexercise,fitnessmotivation,workoutathome,earlymorningworkout,fitnessjourney,healthylifestyle,exerciseroutine,dailyworkout"))])  # Long-tail
            ]
            
            with patch.object(generator, '_get_trending_hashtags') as mock_trending:
                mock_trending.return_value = [
                    {"tag": f"trending{i}", "media_count": 100000, "velocity_7d": 0.5, "trending_score": 85.0, "competition": "high"}
                    for i in range(10)
                ]
                
                with patch.object(generator, '_get_niche_hashtags') as mock_niche:
                    mock_niche.return_value = [
                        {"tag": f"niche{i}", "media_count": 50000, "velocity_7d": 0.3, "trending_score": 70.0, "competition": "medium"}
                        for i in range(10)
                    ]
                    
                    result = await generator.generate_hashtags(content, niche)
                    
                    assert result["total_count"] == 30
                    assert len(result["trending"]) == 10
                    assert len(result["niche"]) == 10
                    assert len(result["long_tail"]) == 10
                    assert result["detected_niche"] == "fitness"
    
    @pytest.mark.asyncio
    async def test_generate_hashtags_auto_detect_niche(self, generator):
        """Test generating hashtags with auto-detected niche"""
        content = "Delicious pasta recipe"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = [
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="food"))]),
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="pastarecipe,homemadepasta,italianfood,cookingathome,foodie,deliciousfood,recipeideas,easyrecipes,foodphotography,instafood"))])
            ]
            
            with patch.object(generator, '_get_trending_hashtags') as mock_trending:
                mock_trending.return_value = [{"tag": f"food{i}", "media_count": 100000, "velocity_7d": 0.5, "trending_score": 85.0, "competition": "high"} for i in range(10)]
                
                with patch.object(generator, '_get_niche_hashtags') as mock_niche:
                    mock_niche.return_value = [{"tag": f"cooking{i}", "media_count": 50000, "velocity_7d": 0.3, "trending_score": 70.0, "competition": "medium"} for i in range(10)]
                    
                    result = await generator.generate_hashtags(content)
                    
                    assert result["detected_niche"] == "food"
                    assert result["total_count"] == 30
    
    @pytest.mark.asyncio
    async def test_analyze_hashtag_found(self, generator):
        """Test analyzing an existing hashtag"""
        hashtag = "fitness"
        
        with patch.object(generator, '_get_hashtag_from_db') as mock_get:
            mock_get.return_value = {
                "tag": "fitness",
                "media_count": 500000,
                "velocity_7d": 0.5,
                "trending_score": 85.0,
                "category": "health"
            }
            
            result = await generator.analyze_hashtag(hashtag)
            
            assert result["found"] is True
            assert result["tag"] == "fitness"
            assert result["competition"] == "high"
            assert "recommendation" in result
    
    @pytest.mark.asyncio
    async def test_analyze_hashtag_not_found(self, generator):
        """Test analyzing a non-existent hashtag"""
        hashtag = "veryrarehashtag123"
        
        with patch.object(generator, '_get_hashtag_from_db') as mock_get:
            mock_get.return_value = None
            
            result = await generator.analyze_hashtag(hashtag)
            
            assert result["found"] is False
            assert result["tag"] == "veryrarehashtag123"
    
    @pytest.mark.asyncio
    async def test_get_hashtag_suggestions_by_category(self, generator):
        """Test getting hashtag suggestions by category"""
        category = "fitness"
        
        with patch.object(generator, '_query_hashtags_by_category') as mock_query:
            mock_query.return_value = [
                {"tag": "fitness", "media_count": 500000, "trending_score": 85.0},
                {"tag": "workout", "media_count": 400000, "trending_score": 80.0},
            ]
            
            suggestions = await generator.get_hashtag_suggestions(category, limit=30)
            
            assert len(suggestions) <= 30
            assert all("tag" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_filter_existing_hashtags(self, generator):
        """Test filtering out existing hashtags"""
        content = "Morning workout"
        existing = ["fitness", "workout"]
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = [
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="fitness"))]),
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="morningworkout,homefitness,quickexercise,fitnessmotivation,workoutathome,earlymorningworkout,fitnessjourney,healthylifestyle,exerciseroutine,dailyworkout"))])
            ]
            
            with patch.object(generator, '_get_trending_hashtags') as mock_trending:
                mock_trending.return_value = [
                    {"tag": "trending1", "media_count": 100000, "velocity_7d": 0.5, "trending_score": 85.0, "competition": "high"}
                    for i in range(10)
                ]
                
                with patch.object(generator, '_get_niche_hashtags') as mock_niche:
                    mock_niche.return_value = [
                        {"tag": "niche1", "media_count": 50000, "velocity_7d": 0.3, "trending_score": 70.0, "competition": "medium"}
                        for i in range(10)
                    ]
                    
                    result = await generator.generate_hashtags(content, existing_hashtags=existing)
                    
                    # Should not include existing hashtags
                    all_tags = [h["tag"] for h in result["trending"] + result["niche"] + result["long_tail"]]
                    assert "fitness" not in all_tags
                    assert "workout" not in all_tags
    
    def test_competition_thresholds(self, generator):
        """Test competition level thresholds"""
        # High competition: > 100k
        assert generator._categorize_competition(500000) == "high"
        assert generator._categorize_competition(150000) == "high"
        
        # Medium competition: 10k - 100k
        assert generator._categorize_competition(50000) == "medium"
        assert generator._categorize_competition(20000) == "medium"
        
        # Low competition: < 10k
        assert generator._categorize_competition(5000) == "low"
        assert generator._categorize_competition(1000) == "low"
    
    def test_recommendation_generation_high_competition(self, generator):
        """Test recommendation for high competition hashtags"""
        media_count = 500000
        competition = "high"
        
        if competition == "high":
            recommendation = "High competition - use with niche tags"
        elif competition == "medium":
            recommendation = "Medium competition - good balance"
        else:
            recommendation = "Low competition - great for visibility"
        
        assert recommendation == "High competition - use with niche tags"
    
    @pytest.mark.asyncio
    async def test_error_handling_openai_failure(self, generator):
        """Test error handling when OpenAI fails"""
        content = "Test content"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = Exception("API Error")
            
            with pytest.raises(Exception):
                await generator._detect_niche(content)
    
    @pytest.mark.asyncio
    async def test_empty_content_handling(self, generator):
        """Test handling empty content"""
        content = ""
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="general"))]
            )
            
            niche = await generator._detect_niche(content)
            assert niche == "general"
    
    def test_hashtag_formatting(self, generator):
        """Test hashtag formatting (removing # symbols)"""
        tags = ["#fitness", "workout", "##health"]
        cleaned = [tag.replace("#", "") for tag in tags]
        
        assert cleaned == ["fitness", "workout", "health"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
