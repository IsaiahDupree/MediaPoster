"""
Unit Tests for Content Analyzer Service
Tests AI-powered video analysis functionality
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.instagram.content_analyzer import ContentAnalyzer


class TestContentAnalyzer:
    """Test suite for content analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return ContentAnalyzer()
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initializes correctly"""
        assert analyzer.engine is not None
        assert analyzer.openai_client is not None
    
    @pytest.mark.asyncio
    async def test_detect_hook_type_curiosity(self, analyzer):
        """Test hook type detection for curiosity hooks"""
        transcript = "Wait until you see what happens next! You won't believe this..."
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="curiosity"))]
            )
            
            hook_type = await analyzer._detect_hook_type(transcript)
            assert hook_type == "curiosity"
    
    @pytest.mark.asyncio
    async def test_detect_hook_type_text_based(self, analyzer):
        """Test hook type detection for text-based hooks"""
        transcript = "3 ways to improve your morning routine"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="text-based"))]
            )
            
            hook_type = await analyzer._detect_hook_type(transcript)
            assert hook_type == "text-based"
    
    @pytest.mark.asyncio
    async def test_analyze_pacing_fast(self, analyzer):
        """Test pacing analysis for fast-paced content"""
        transcript = "Quick! Fast! Now! Hurry! Rapid fire content here!"
        duration_sec = 15
        
        pacing = await analyzer._analyze_pacing(transcript, duration_sec)
        assert pacing in ["fast", "medium", "slow"]
    
    @pytest.mark.asyncio
    async def test_analyze_pacing_slow(self, analyzer):
        """Test pacing analysis for slow-paced content"""
        transcript = "Let's take our time and really think about this deeply."
        duration_sec = 60
        
        pacing = await analyzer._analyze_pacing(transcript, duration_sec)
        assert pacing in ["fast", "medium", "slow"]
    
    @pytest.mark.asyncio
    async def test_calculate_text_density_high(self, analyzer):
        """Test text density calculation for high density"""
        transcript = "Word " * 100  # 100 words
        duration_sec = 30
        
        density = await analyzer._calculate_text_density(transcript, duration_sec)
        assert density > 2.0  # More than 2 words per second
    
    @pytest.mark.asyncio
    async def test_calculate_text_density_low(self, analyzer):
        """Test text density calculation for low density"""
        transcript = "Just a few words here"
        duration_sec = 30
        
        density = await analyzer._calculate_text_density(transcript, duration_sec)
        assert density < 1.0  # Less than 1 word per second
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_positive(self, analyzer):
        """Test sentiment analysis for positive content"""
        transcript = "This is amazing! I love it! So happy and excited!"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="positive"))]
            )
            
            sentiment = await analyzer._analyze_sentiment(transcript)
            assert sentiment == "positive"
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_negative(self, analyzer):
        """Test sentiment analysis for negative content"""
        transcript = "This is terrible. I hate it. So disappointing."
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="negative"))]
            )
            
            sentiment = await analyzer._analyze_sentiment(transcript)
            assert sentiment == "negative"
    
    @pytest.mark.asyncio
    async def test_match_to_trend_cards(self, analyzer):
        """Test matching content to trend cards"""
        caption = "POV: You're the main character"
        hashtags = ["pov", "maincharacter", "trending"]
        
        with patch.object(analyzer, '_query_trend_cards') as mock_query:
            mock_query.return_value = [
                {"format_type": "pov", "name": "POV", "trending_score": 85.0}
            ]
            
            matches = await analyzer._match_to_trend_cards(caption, hashtags)
            assert len(matches) > 0
            assert matches[0] == "pov"
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_high_priority(self, analyzer):
        """Test generating high priority recommendations"""
        analysis_data = {
            "hook_type": "weak",
            "pacing": "slow",
            "text_density": 0.5,
            "sentiment": "neutral"
        }
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content='[{"title":"Improve Hook","description":"Add curiosity","priority":"high","category":"hook"}]'))]
            )
            
            recommendations = await analyzer._generate_recommendations(analysis_data)
            assert len(recommendations) > 0
            assert recommendations[0]["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_analyze_content_complete_workflow(self, analyzer):
        """Test complete content analysis workflow"""
        video_id = "test_video_123"
        transcript = "Check out this amazing workout routine!"
        caption = "Morning fitness"
        hashtags = ["fitness", "workout"]
        duration_sec = 30
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = [
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="text-based"))]),  # Hook
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="positive"))]),    # Sentiment
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content='[{"title":"Test","description":"Test rec","priority":"medium","category":"pacing"}]'))])  # Recommendations
            ]
            
            with patch.object(analyzer, '_match_to_trend_cards') as mock_match:
                mock_match.return_value = ["tutorial"]
                
                with patch.object(analyzer, '_save_analysis_job') as mock_save:
                    mock_save.return_value = "job_123"
                    
                    job_id = await analyzer.analyze_content(
                        video_id, transcript, caption, hashtags, duration_sec
                    )
                    
                    assert job_id == "job_123"
    
    @pytest.mark.asyncio
    async def test_get_analysis_result_completed(self, analyzer):
        """Test retrieving completed analysis result"""
        job_id = "job_123"
        
        with patch.object(analyzer, '_get_job_from_db') as mock_get:
            mock_get.return_value = {
                "id": job_id,
                "status": "completed",
                "hook_type": "curiosity",
                "pacing": "fast",
                "text_density": 2.5,
                "sentiment": "positive",
                "matched_trend_cards": ["pov"],
                "recommendations": [{"title": "Great job", "priority": "low"}]
            }
            
            result = await analyzer.get_analysis_result(job_id)
            assert result["status"] == "completed"
            assert result["hook_type"] == "curiosity"
    
    @pytest.mark.asyncio
    async def test_get_analysis_result_not_found(self, analyzer):
        """Test retrieving non-existent analysis result"""
        job_id = "nonexistent"
        
        with patch.object(analyzer, '_get_job_from_db') as mock_get:
            mock_get.return_value = None
            
            result = await analyzer.get_analysis_result(job_id)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_quick_analyze_no_database(self, analyzer):
        """Test quick analysis without saving to database"""
        transcript = "Quick test content"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = [
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="text-based"))]),
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content="neutral"))]),
                AsyncMock(choices=[AsyncMock(message=AsyncMock(content='[]'))])
            ]
            
            with patch.object(analyzer, '_match_to_trend_cards') as mock_match:
                mock_match.return_value = []
                
                result = await analyzer.quick_analyze(transcript, duration_sec=15)
                
                assert result["hook_type"] == "text-based"
                assert result["sentiment"] == "neutral"
                assert "pacing" in result
                assert "text_density" in result
    
    @pytest.mark.asyncio
    async def test_error_handling_openai_failure(self, analyzer):
        """Test error handling when OpenAI API fails"""
        transcript = "Test content"
        
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = Exception("API Error")
            
            with pytest.raises(Exception):
                await analyzer._detect_hook_type(transcript)
    
    def test_word_count(self, analyzer):
        """Test word counting utility"""
        text = "This is a test sentence with seven words"
        word_count = len(text.split())
        assert word_count == 8
    
    @pytest.mark.asyncio
    async def test_batch_analysis(self, analyzer):
        """Test batch analysis of multiple videos"""
        video_ids = ["video1", "video2", "video3"]
        
        with patch.object(analyzer, 'analyze_content') as mock_analyze:
            mock_analyze.side_effect = ["job1", "job2", "job3"]
            
            job_ids = []
            for video_id in video_ids:
                job_id = await analyzer.analyze_content(
                    video_id, "Test transcript", "Test caption", [], 30
                )
                job_ids.append(job_id)
            
            assert len(job_ids) == 3
            assert job_ids == ["job1", "job2", "job3"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
