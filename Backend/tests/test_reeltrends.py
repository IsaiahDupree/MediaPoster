"""
ReelTrends API Tests
====================
Tests for all ReelTrends endpoints.
"""
import pytest
import httpx
from typing import Dict, Any

BASE_URL = "http://localhost:5555/api/v1/reeltrends"


class TestReelTrendsPhase1:
    """Phase 1: Content Generation Tests"""

    @pytest.mark.asyncio
    async def test_script_generation(self):
        """Test AI script generation endpoint"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/script",
                json={
                    "topic": "5 productivity hacks for remote workers",
                    "niche": "productivity",
                    "tone": "casual",
                    "length": "short",
                    "format": "reel",
                    "hook_style": "question"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "topic" in data
        assert "beats" in data
        assert "total_duration" in data
        assert "estimated_word_count" in data
        
        # Verify beats
        assert len(data["beats"]) >= 2
        for beat in data["beats"]:
            assert "name" in beat
            assert "script" in beat
            assert "duration_seconds" in beat

    @pytest.mark.asyncio
    async def test_captions_generation(self):
        """Test AI captions generation endpoint"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/captions",
                json={
                    "topic": "Morning routine for success",
                    "niche": "self-improvement",
                    "emoji_level": "moderate"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "topic" in data
        assert "captions" in data
        assert len(data["captions"]) == 3
        
        for caption in data["captions"]:
            assert "style" in caption
            assert "caption" in caption
            assert "character_count" in caption

    @pytest.mark.asyncio
    async def test_carousel_generation(self):
        """Test AI carousel generation endpoint"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/carousel",
                json={
                    "topic": "10 Python tips for beginners",
                    "niche": "programming",
                    "slide_count": 5,
                    "style": "minimal"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "topic" in data
        assert "slides" in data
        assert "style" in data
        assert len(data["slides"]) == 5
        
        for slide in data["slides"]:
            assert "slide_number" in slide
            assert "headline" in slide
            assert "body_text" in slide

    @pytest.mark.asyncio
    async def test_hashtags_generation(self):
        """Test hashtag recommendation endpoint"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/hashtags",
                json={
                    "topic": "Fitness motivation",
                    "niche": "fitness"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "topic" in data
        assert "niche" in data
        assert "format" in data
        assert "discovery" in data
        assert "total_count" in data
        
        # Should have 10 total hashtags
        total = len(data["niche"]) + len(data["format"]) + len(data["discovery"])
        assert total == data["total_count"]

    @pytest.mark.asyncio
    async def test_content_pack_generation(self):
        """Test content pack (all-in-one) generation"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{BASE_URL}/content-pack",
                json={
                    "topic": "How to start a side hustle",
                    "niche": "entrepreneurship",
                    "tone": "casual"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "topic" in data
        assert "script" in data
        assert "captions" in data
        assert "carousel" in data
        assert "hashtags" in data


class TestReelTrendsPhase2:
    """Phase 2: Analytics Tests"""

    @pytest.mark.asyncio
    async def test_best_time_analysis(self):
        """Test best time to post analysis"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/best-time",
                json={
                    "platform": "instagram",
                    "days_to_analyze": 90
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "peak_hour_today" in data
        assert "current_score" in data
        assert "should_wait" in data
        assert "best_days" in data
        assert "worst_days" in data
        assert "optimal_windows" in data
        
        # Verify score is between 0 and 1
        assert 0 <= data["current_score"] <= 1

    @pytest.mark.asyncio
    async def test_post_analysis(self):
        """Test post content analysis"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/analyze",
                json={
                    "transcript": "Hey everyone! Today I'm going to show you 5 ways to boost your productivity. First, wake up early...",
                    "caption": "5 productivity hacks that changed my life 🚀",
                    "content_type": "reel"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all scores present
        assert "overall_score" in data
        assert "hook_score" in data
        assert "body_score" in data
        assert "visual_score" in data
        assert "audio_score" in data
        assert "pacing_score" in data
        assert "cta_score" in data
        assert "viral_score" in data
        
        # Verify scores are in range
        for key in ["overall_score", "hook_score", "body_score", "visual_score"]:
            assert 0 <= data[key] <= 10
        
        # Verify feedback
        assert "top_strengths" in data
        assert "top_improvements" in data
        assert "grade" in data

    @pytest.mark.asyncio
    async def test_viral_forecast(self):
        """Test viral potential forecasting"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/forecast",
                json={
                    "topic": "Why your morning routine is killing your productivity",
                    "hook": "Nobody talks about this...",
                    "format": "reel",
                    "niche": "productivity"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "viral_potential" in data
        assert data["viral_potential"] in ["low", "medium", "high"]
        assert "score" in data
        assert "confidence" in data
        assert "positive_factors" in data
        assert "negative_factors" in data
        assert "suggestions" in data
        assert "estimated_reach" in data


class TestReelTrendsPhase3:
    """Phase 3: Sound Analytics Tests"""

    @pytest.mark.asyncio
    async def test_sound_of_the_day(self):
        """Test sound of the day recommendation"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/sounds/of-the-day",
                json={
                    "niche": "fitness",
                    "content_type": "reel"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sound" in data
        assert "reason" in data
        assert "best_for" in data
        assert "example_hooks" in data
        
        sound = data["sound"]
        assert "title" in sound
        assert "artist" in sound
        assert "trend" in sound

    @pytest.mark.asyncio
    async def test_sound_analysis(self):
        """Test specific sound analysis"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/sounds/analyze",
                json={
                    "sound_name": "Makeba",
                    "artist": "Jain"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sound_name" in data
        assert "trend_analysis" in data
        assert "content_fit" in data
        assert "usage_tips" in data
        assert "recommendation" in data
        
        rec = data["recommendation"]
        assert "should_use" in rec
        assert "reason" in rec
        assert "timing" in rec

    @pytest.mark.asyncio
    async def test_sounds_for_niche(self):
        """Test niche-specific sound recommendations"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/sounds/for-niche",
                json={
                    "niche": "technology",
                    "mood": "energetic",
                    "count": 3
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "niche" in data
        assert "sounds" in data
        assert len(data["sounds"]) <= 3


class TestReelTrendsInfo:
    """Test info endpoint"""

    @pytest.mark.asyncio
    async def test_info_endpoint(self):
        """Test the info endpoint returns all tools"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "tools" in data
        assert len(data["tools"]) >= 8  # At least 8 tools implemented


# Run with: pytest Backend/tests/test_reeltrends.py -v --asyncio-mode=auto
if __name__ == "__main__":
    import asyncio
    
    async def run_quick_tests():
        """Quick smoke tests"""
        print("🧪 Running ReelTrends Quick Tests...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test info endpoint
            print("\n1. Testing /info...")
            r = await client.get(f"{BASE_URL}/info")
            assert r.status_code == 200
            print(f"   ✅ Found {len(r.json()['tools'])} tools")
            
            # Test script generation
            print("\n2. Testing /script...")
            r = await client.post(f"{BASE_URL}/script", json={
                "topic": "Test topic",
                "tone": "casual",
                "length": "short"
            })
            assert r.status_code == 200
            print(f"   ✅ Generated {len(r.json()['beats'])} beats")
            
            # Test best time
            print("\n3. Testing /best-time...")
            r = await client.post(f"{BASE_URL}/best-time", json={
                "platform": "instagram"
            })
            assert r.status_code == 200
            print(f"   ✅ Peak hour: {r.json()['peak_hour_today']}:00")
            
            # Test sound of the day
            print("\n4. Testing /sounds/of-the-day...")
            r = await client.post(f"{BASE_URL}/sounds/of-the-day", json={
                "niche": "general"
            })
            assert r.status_code == 200
            print(f"   ✅ Recommended: {r.json()['sound']['title']}")
        
        print("\n✅ All quick tests passed!")
    
    asyncio.run(run_quick_tests())
