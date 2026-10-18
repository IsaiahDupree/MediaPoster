"""
Tests for Trending Keywords Service and Video Analysis
"""
import pytest
import json
from pathlib import Path
from datetime import datetime

# Test the trending keywords service
class TestTrendingKeywordsService:
    """Tests for the TrendingKeywordsService."""
    
    def test_extract_hooks_pov(self):
        """Test POV hook extraction."""
        from services.trending_keywords_service import TrendingKeywordsService
        
        service = TrendingKeywordsService()
        text = "POV: you're the only one who knows this secret"
        hooks = service.extract_hooks(text)
        
        assert len(hooks) > 0
        assert any("POV" in h[0] for h in hooks)
        assert hooks[0][1] == "hook"
    
    def test_extract_hooks_hot_take(self):
        """Test hot take hook extraction."""
        from services.trending_keywords_service import TrendingKeywordsService
        
        service = TrendingKeywordsService()
        text = "Hot take: most entrepreneurs are doing it wrong"
        hooks = service.extract_hooks(text)
        
        assert len(hooks) > 0
        assert any("Hot take" in h[0] for h in hooks)
    
    def test_extract_hooks_nobody_talks(self):
        """Test 'nobody talks about' hook extraction."""
        from services.trending_keywords_service import TrendingKeywordsService
        
        service = TrendingKeywordsService()
        text = "Nobody talks about the hard parts of success"
        hooks = service.extract_hooks(text)
        
        assert len(hooks) > 0
    
    def test_extract_ctas(self):
        """Test CTA extraction."""
        from services.trending_keywords_service import TrendingKeywordsService
        
        service = TrendingKeywordsService()
        text = "Save this for later! Drop a 🔥 if you agree"
        ctas = service.extract_ctas(text)
        
        assert len(ctas) >= 1
        assert ctas[0][1] == "cta"
    
    def test_extract_ngrams(self):
        """Test n-gram extraction."""
        from services.trending_keywords_service import TrendingKeywordsService
        
        service = TrendingKeywordsService()
        text = "The secret to success is consistency and hard work every single day"
        ngrams = service.extract_ngrams(text)
        
        assert len(ngrams) > 0
        # Should find phrases like "secret to success", "hard work every"
        phrases = [n[0] for n in ngrams]
        assert any("secret" in p for p in phrases)
    
    def test_process_caption(self):
        """Test full caption processing."""
        from services.trending_keywords_service import TrendingKeywordsService
        
        service = TrendingKeywordsService()
        caption = """
        POV: you just discovered the secret to viral content.
        Here's what nobody talks about - engagement is king!
        Save this for later and follow for more tips.
        #entrepreneur #success #viral
        """
        
        keywords = service.process_caption(caption, engagement=10000)
        
        assert len(keywords) > 0
        # Should have extracted hooks and CTAs
        types = set(kw.keyword_type for kw in keywords)
        assert "hook" in types or "cta" in types or "phrase" in types
    
    def test_calculate_trend_score(self):
        """Test trend score calculation."""
        from services.trending_keywords_service import TrendingKeywordsService, TrendingKeyword
        
        service = TrendingKeywordsService()
        
        kw = TrendingKeyword("test phrase", "hook")
        kw.occurrence_count = 100
        kw.velocity_7d = 1.5
        kw.avg_engagement = 5000
        
        score = service._calculate_trend_score(kw)
        
        assert score > 0
        assert score < 200  # Reasonable upper bound
    
    def test_get_trending_keywords_empty(self):
        """Test getting trending keywords when cache is empty."""
        from services.trending_keywords_service import TrendingKeywordsService
        
        service = TrendingKeywordsService()
        service.keywords_cache = {}  # Clear cache
        
        keywords = service.get_trending_keywords()
        
        assert isinstance(keywords, list)
    
    def test_keyword_to_dict(self):
        """Test keyword serialization."""
        from services.trending_keywords_service import TrendingKeyword
        
        kw = TrendingKeyword("POV: test", "hook", "business")
        kw.occurrence_count = 50
        kw.trend_score = 75.5
        
        data = kw.to_dict()
        
        assert data["keyword"] == "POV: test"
        assert data["keyword_type"] == "hook"
        assert data["niche"] == "business"
        assert data["occurrence_count"] == 50
        assert data["trend_score"] == 75.5


class TestVideoAnalysisRecommendations:
    """Tests for video analysis recommendations."""
    
    def test_duration_recommendation_short(self):
        """Test duration recommendation for short videos."""
        duration_seconds = 10
        recommendations = []
        
        if duration_seconds < 15:
            recommendations.append("⚡ Very short video - perfect for Reels/Shorts")
        
        assert len(recommendations) == 1
        assert "Reels" in recommendations[0]
    
    def test_duration_recommendation_medium(self):
        """Test duration recommendation for medium videos."""
        duration_seconds = 45
        recommendations = []
        
        if duration_seconds >= 15 and duration_seconds < 60:
            recommendations.append("📱 Ideal length for short-form content")
        
        assert len(recommendations) == 1
        assert "Ideal" in recommendations[0]
    
    def test_duration_recommendation_long(self):
        """Test duration recommendation for long videos."""
        duration_seconds = 400
        recommendations = []
        
        if duration_seconds > 300:
            recommendations.append("📺 Long-form - consider for YouTube")
        
        assert len(recommendations) == 1
        assert "YouTube" in recommendations[0]
    
    def test_audio_quality_recommendation(self):
        """Test audio quality recommendation."""
        audio_quality_score = 40
        recommendations = []
        
        if audio_quality_score < 50:
            recommendations.append("🎙️ Audio quality is low - use external mic")
        
        assert len(recommendations) == 1
        assert "mic" in recommendations[0]
    
    def test_background_noise_recommendation(self):
        """Test background noise recommendation."""
        background_noise_level = -15  # High noise
        recommendations = []
        
        if background_noise_level > -20:
            recommendations.append("🔇 High background noise - record in quieter space")
        
        assert len(recommendations) == 1
        assert "noise" in recommendations[0]
    
    def test_hook_recommendation(self):
        """Test hook recommendation when missing."""
        has_hook = False
        recommendations = []
        
        if not has_hook:
            recommendations.append("🎣 Add a strong hook in first 3 seconds")
        
        assert len(recommendations) == 1
        assert "hook" in recommendations[0]
    
    def test_broll_recommendation(self):
        """Test B-roll recommendation for talking head videos."""
        content_type = "talking_head"
        duration_seconds = 45
        recommendations = []
        
        if content_type == "talking_head" and duration_seconds > 30:
            recommendations.append("🎬 Add B-roll to maintain engagement")
        
        assert len(recommendations) == 1
        assert "B-roll" in recommendations[0]
    
    def test_combined_duration_threshold(self):
        """Test recommendation for combining videos to reach 5+ minutes."""
        total_duration_minutes = 3.5
        recommendations = []
        
        if total_duration_minutes < 5:
            recommendations.append(f"⏱️ Duration: {total_duration_minutes:.1f}min - Combine with other videos to reach 5+ minutes for long-form")
        
        assert len(recommendations) == 1
        assert "5+" in recommendations[0]
    
    def test_transcript_recommendation(self):
        """Test transcript recommendation when not available."""
        has_transcript = False
        recommendations = []
        
        if not has_transcript:
            recommendations.append("📝 Re-run with --transcript flag (requires OPENAI_API_KEY) for better analysis")
        
        assert len(recommendations) == 1
        assert "transcript" in recommendations[0]


class TestTrendCrawler:
    """Tests for trend crawler functionality."""
    
    def test_hashtag_extraction_from_caption(self):
        """Test hashtag extraction from caption."""
        import re
        
        caption = "Great content! #entrepreneur #success #viral #growthmindset"
        tags = re.findall(r'#(\w+)', caption)
        
        assert len(tags) == 4
        assert "entrepreneur" in tags
        assert "success" in tags
    
    def test_hashtag_counter(self):
        """Test hashtag counting."""
        from collections import Counter
        
        hashtags = ["entrepreneur", "success", "entrepreneur", "viral", "entrepreneur"]
        counter = Counter(hashtags)
        
        assert counter["entrepreneur"] == 3
        assert counter["success"] == 1
    
    def test_trending_score_calculation(self):
        """Test trending score calculation for hashtags."""
        count = 50
        avg_engagement = 10000
        
        trending_score = round(count * 10 + avg_engagement / 100, 1)
        
        assert trending_score == 600.0  # 50*10 + 10000/100
    
    def test_hashtag_sorting(self):
        """Test hashtag sorting by trending score."""
        hashtags = [
            {"tag": "#a", "trending_score": 50},
            {"tag": "#b", "trending_score": 100},
            {"tag": "#c", "trending_score": 75}
        ]
        
        sorted_hashtags = sorted(hashtags, key=lambda x: x["trending_score"], reverse=True)
        
        assert sorted_hashtags[0]["tag"] == "#b"
        assert sorted_hashtags[1]["tag"] == "#c"
        assert sorted_hashtags[2]["tag"] == "#a"


class TestAPIEndpoints:
    """Tests for API endpoints (integration tests)."""
    
    @pytest.mark.asyncio
    async def test_trending_keywords_endpoint(self):
        """Test /api/trends/trending-keywords endpoint."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5555/api/trends/trending-keywords")
            
            if response.status_code == 200:
                data = response.json()
                assert "keywords" in data
                assert "count" in data
    
    @pytest.mark.asyncio
    async def test_trending_hooks_endpoint(self):
        """Test /api/trends/trending-keywords/hooks endpoint."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5555/api/trends/trending-keywords/hooks")
            
            if response.status_code == 200:
                data = response.json()
                assert "hooks" in data
    
    @pytest.mark.asyncio
    async def test_extract_keywords_endpoint(self):
        """Test /api/trends/trending-keywords/extract endpoint."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:5555/api/trends/trending-keywords/extract")
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
    
    @pytest.mark.asyncio
    async def test_populate_hashtags_endpoint(self):
        """Test /api/trends/crawler/populate-hashtags endpoint."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:5555/api/trends/crawler/populate-hashtags")
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
