"""
Tests for Content Brief Generator (Phase 5)
Tests ContentBriefGenerator service and Briefs API
"""
import pytest
from datetime import datetime
from uuid import uuid4

from services.content_brief import ContentBriefGenerator
from database.models import Segment, SegmentInsight


@pytest.mark.asyncio
class TestContentBriefGenerator:
    """Test Content Brief Generator Service"""
    
    async def test_generate_organic_brief_basic(self, db_session):
        """Test generating basic organic brief"""
        generator = ContentBriefGenerator(db_session)
        
        # Create segment with insights
        segment = Segment(
            id=uuid4(),
            name="Tech Enthusiasts",
            description="Engaged tech audience"
        )
        db_session.add(segment)
        await db_session.flush()
        
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='organic',
            top_topics=["AI", "automation", "productivity"],
            top_platforms={"instagram": 0.6, "linkedin": 0.4},
            top_formats={"reels": 0.5, "carousels": 0.3, "posts": 0.2},
            best_times={"weekday": "9am-11am", "weekend": "2pm-4pm"},
            expected_reach_range="[1000,5000]",
            expected_engagement_rate_range="[0.02,0.05]"
        )
        db_session.add(insights)
        await db_session.commit()
        
        # Generate brief
        brief = await generator.generate_organic_brief(
            segment_id=segment.id,
            campaign_goal='educate',
            time_window_days=30
        )
        
        assert brief is not None
        assert brief['segment_name'] == "Tech Enthusiasts"
        assert brief['traffic_type'] == 'organic'
        assert brief['campaign_goal'] == 'educate'
        assert 'segment_snapshot' in brief
        assert 'content_strategy' in brief
        assert 'hook_templates' in brief
        assert len(brief['hook_templates']) > 0
    
    async def test_generate_paid_brief_basic(self, db_session):
        """Test generating basic paid brief"""
        generator = ContentBriefGenerator(db_session)
        
        segment = Segment(
            id=uuid4(),
            name="SaaS Founders",
            description="B2B SaaS decision makers"
        )
        db_session.add(segment)
        await db_session.flush()
        
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='paid',
            top_topics=["SaaS", "growth", "scaling"],
            top_platforms={"linkedin": 0.7, "facebook": 0.3},
            top_formats={"video": 0.6, "image": 0.4}
        )
        db_session.add(insights)
        await db_session.commit()
        
        # Generate paid brief
        brief = await generator.generate_paid_brief(
            segment_id=segment.id,
            campaign_goal='launch',
            budget_range={"min": 100, "max": 1000}
        )
        
        assert brief is not None
        assert brief['traffic_type'] == 'paid'
        assert 'audience_targeting' in brief
        assert 'creative_strategy' in brief
        assert 'testing_matrix' in brief
        assert 'budget_guidance' in brief
        assert brief['budget_guidance']['suggested_budget']['min'] == 100
    
    async def test_brief_includes_segment_characteristics(self, db_session):
        """Test that brief includes segment characteristics"""
        generator = ContentBriefGenerator(db_session)
        
        segment = Segment(id=uuid4(), name="Test Segment")
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='organic',
            top_topics=["topic1", "topic2"],
            top_platforms={"instagram": 0.8}
        )
        db_session.add_all([segment, insights])
        await db_session.commit()
        
        brief = await generator.generate_organic_brief(segment.id, 'nurture')
        
        snapshot = brief['segment_snapshot']
        assert 'who_they_are' in snapshot
        assert 'what_they_care_about' in snapshot
        assert 'topic1' in snapshot['what_they_care_about']
    
    async def test_brief_matches_campaign_goal(self, db_session):
        """Test brief adapts to campaign goal"""
        generator = ContentBriefGenerator(db_session)
        
        segment = Segment(id=uuid4(), name="Goal Test")
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='organic',
            top_topics=["test"]
        )
        db_session.add_all([segment, insights])
        await db_session.commit()
        
        # Test different goals
        educate_brief = await generator.generate_organic_brief(segment.id, 'educate')
        launch_brief = await generator.generate_organic_brief(segment.id, 'launch')
        
        # Strategies should differ
        educate_angles = educate_brief['content_strategy']['angle_ideas']
        launch_angles = launch_brief['content_strategy']['angle_ideas']
        
        assert educate_angles != launch_angles
        assert any('how-to' in str(angle).lower() for angle in educate_angles)
        assert any('launch' in str(angle).lower() or 'first' in str(angle).lower() for angle in launch_angles)
    
    async def test_platform_recommendations(self, db_session):
        """Test platform recommendations based on insights"""
        generator = ContentBriefGenerator(db_session)
        
        segment = Segment(id=uuid4(), name="Multi-Platform")
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='organic',
            top_platforms={
                "instagram": 0.5,
                "tiktok": 0.3,
                "youtube": 0.2
            },
            top_formats={"reels": 0.7, "videos": 0.3}
        )
        db_session.add_all([segment, insights])
        await db_session.commit()
        
        brief = await generator.generate_organic_brief(segment.id, 'educate')
        
        platform_recs = brief['platform_recommendations']
        assert 'primary_platforms' in platform_recs
        assert 'instagram' in platform_recs['primary_platforms']
        assert len(platform_recs['primary_platforms']) <= 3
    
    async def test_hook_templates_generated(self, db_session):
        """Test hook template generation"""
        generator = ContentBriefGenerator(db_session)
        
        segment = Segment(id=uuid4(), name="Hook Test")
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='organic',
            top_topics=["productivity", "time management"]
        )
        db_session.add_all([segment, insights])
        await db_session.commit()
        
        brief = await generator.generate_organic_brief(segment.id, 'educate')
        
        hooks = brief['hook_templates']
        assert len(hooks) >= 3
        # Should reference segment topics
        hooks_text = ' '.join(hooks).lower()
        assert 'productivity' in hooks_text or 'time' in hooks_text
    
    async def test_paid_brief_includes_testing_matrix(self, db_session):
        """Test paid brief includes A/B testing guidance"""
        generator = ContentBriefGenerator(db_session)
        
        segment = Segment(id=uuid4(), name="Paid Test")
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='paid',
            top_topics=["product"]
        )
        db_session.add_all([segment, insights])
        await db_session.commit()
        
        brief = await generator.generate_paid_brief(segment.id, 'launch')
        
        testing = brief['testing_matrix']
        assert 'variables_to_test' in testing
        assert 'recommended_variants' in testing
        assert testing['recommended_variants'] >= 2
    
    async def test_error_no_insights(self, db_session):
        """Test error when segment has no insights"""
        generator = ContentBriefGenerator(db_session)
        
        segment = Segment(id=uuid4(), name="No Insights")
        db_session.add(segment)
        await db_session.commit()
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="No organic insights"):
            await generator.generate_organic_brief(segment.id, 'educate')


@pytest.mark.asyncio
class TestBriefsAPI:
    """Test Briefs API Endpoints"""
    
    async def test_generate_brief_endpoint(self, client, db_session):
        """Test POST /api/briefs/generate"""
        # Create segment with insights
        segment = Segment(id=uuid4(), name="API Test Segment")
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='organic',
            top_topics=["test"]
        )
        db_session.add_all([segment, insights])
        await db_session.commit()
        
        response = await client.post('/api/briefs/generate', json={
            'segment_id': str(segment.id),
            'campaign_goal': 'educate',
            'traffic_type': 'organic',
            'time_window_days': 30
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'brief' in data
        assert data['brief']['segment_name'] == "API Test Segment"
    
    async def test_list_campaign_goals(self, client):
        """Test GET /api/briefs/goals"""
        response = await client.get('/api/briefs/goals')
        
        assert response.status_code == 200
        data = response.json()
        assert 'goals' in data
        assert len(data['goals']) >= 4
        
        goal_ids = [g['id'] for g in data['goals']]
        assert 'educate' in goal_ids
        assert 'nurture' in goal_ids
        assert 'launch' in goal_ids
    
    async def test_generate_paid_brief_endpoint(self, client, db_session):
        """Test generating paid brief via API"""
        segment = Segment(id=uuid4(), name="Paid API Test")
        insights = SegmentInsight(
            segment_id=segment.id,
            traffic_type='paid',
            top_topics=["ad test"]
        )
        db_session.add_all([segment, insights])
        await db_session.commit()
        
        response = await client.post('/api/briefs/generate', json={
            'segment_id': str(segment.id),
            'campaign_goal': 'launch',
            'traffic_type': 'paid',
            'budget_range': {'min': 200, 'max': 2000}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['brief']['traffic_type'] == 'paid'
    
    async def test_invalid_segment_id(self, client):
        """Test error with non-existent segment"""
        fake_id = str(uuid4())
        
        response = await client.post('/api/briefs/generate', json={
            'segment_id': fake_id,
            'campaign_goal': 'educate',
            'traffic_type': 'organic'
        })
        
        assert response.status_code == 404


# Fixtures
@pytest.fixture
async def db_session():
    """Database session fixture"""
    from database.connection import get_db
    async for session in get_db():
        yield session


@pytest.fixture
async def client():
    """FastAPI test client"""
    from httpx import AsyncClient
    from main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
