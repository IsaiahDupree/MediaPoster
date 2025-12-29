"""
Tests for Narrative Builder API
================================

Tests the narrative builder endpoints for content planning and scheduling.
"""
import pytest
import httpx
from datetime import datetime, timedelta

API_BASE = "http://localhost:5555"


class TestNarrativeBuilderGoals:
    """Test narrative goal management"""
    
    @pytest.mark.asyncio
    async def test_create_goal(self):
        """Test creating a new narrative goal"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            response = await client.post("/api/narrative-builder/goals", json={
                "goal_statement": "Position myself as the go-to automation architect who turns trends + content into scalable systems",
                "primary_cta": "follow",
                "target_audience": "creators and businesses seeking AI automation",
                "time_horizon": "next_7_days",
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "goal_statement" in data or "message" in data
    
    @pytest.mark.asyncio
    async def test_list_goals(self):
        """Test listing narrative goals"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            response = await client.get("/api/narrative-builder/goals")
            
            assert response.status_code == 200
            data = response.json()
            assert "goals" in data
            assert isinstance(data["goals"], list)


class TestNarrativeBuilderCandidates:
    """Test content candidate selection"""
    
    @pytest.mark.asyncio
    async def test_get_candidates(self):
        """Test getting content candidates"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            response = await client.get("/api/narrative-builder/candidates?limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert "candidates" in data or "total" in data
    
    @pytest.mark.asyncio
    async def test_get_content_stats(self):
        """Test getting content statistics"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            response = await client.get("/api/narrative-builder/content-stats")
            
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert "scheduling" in data


class TestNarrativeBuilderPlan:
    """Test 7-day plan generation"""
    
    @pytest.mark.asyncio
    async def test_get_seven_day_plan(self):
        """Test getting 7-day plan"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            response = await client.get("/api/narrative-builder/plan/7-day")
            
            assert response.status_code == 200
            data = response.json()
            # Should return plan structure
            assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self):
        """Test generating AI recommendations"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=60) as client:
            response = await client.post("/api/narrative-builder/generate-recommendations", json={
                "goal": "Build engagement and grow following as automation architect",
                "cta_type": "follow",
                "pillars": ["AI automation", "content systems", "building in public"]
            })
            
            assert response.status_code == 200
            data = response.json()
            # Should return recommendations or status
            assert isinstance(data, dict)


class TestNarrativeBuilderSignals:
    """Test signal metrics"""
    
    @pytest.mark.asyncio
    async def test_get_signals(self):
        """Test getting narrative signals"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            response = await client.get("/api/narrative-builder/signals")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)


class TestNarrativeBuilderRules:
    """Test KB rules integration"""
    
    @pytest.mark.asyncio
    async def test_get_applicable_rules(self):
        """Test getting applicable rules"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            response = await client.get("/api/narrative-builder/applicable-rules")
            
            assert response.status_code == 200
            data = response.json()
            assert "rules" in data or isinstance(data, dict)


class TestNarrativeBuilderTrends:
    """Test trend opportunities"""
    
    @pytest.mark.asyncio
    async def test_get_trend_opportunities(self):
        """Test getting trend opportunities"""
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            response = await client.get("/api/narrative-builder/trend-opportunities")
            
            assert response.status_code == 200
            data = response.json()
            assert "opportunities" in data or isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
