"""
Tests for People Graph Ingestion (Phase 3)
Tests PeopleIngestionService, PersonLensComputer, and People API
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from services.people_ingestion import PeopleIngestionService
from services.person_lens import PersonLensComputer
from database.models import Person, Identity, PersonEvent, PersonInsight


@pytest.mark.asyncio
class TestPeopleIngestionService:
    """Test People Ingestion Service"""
    
    async def test_create_person_from_comment(self, db_session):
        """Test creating a new person from a comment"""
        service = PeopleIngestionService(db_session)
        
        event = await service.ingest_comment(
            channel='instagram',
            handle='@testuser',
            platform_post_id='post_123',
            comment_text='This is amazing! Love your content 🔥',
            comment_id='comment_456',
            full_name='Test User',
            profile_pic='https://example.com/pic.jpg'
        )
        
        assert event is not None
        assert event.event_type == 'commented'
        assert event.channel == 'instagram'
        assert event.content_excerpt == 'This is amazing! Love your content 🔥'
        
        # Verify person was created
        person = await service.get_or_create_person_by_identity('instagram', '@testuser')
        assert person.full_name == 'Test User'
    
    async def test_same_person_multiple_events(self, db_session):
        """Test that multiple events link to same person"""
        service = PeopleIngestionService(db_session)
        
        # First comment
        event1 = await service.ingest_comment(
            channel='instagram',
            handle='@testuser',
            platform_post_id='post_123',
            comment_text='First comment',
            comment_id='comment_1'
        )
        
        # Second comment from same user
        event2 = await service.ingest_comment(
            channel='instagram',
            handle='@testuser',
            platform_post_id='post_456',
            comment_text='Second comment',
            comment_id='comment_2'
        )
        
        # Should be same person
        assert event1.person_id == event2.person_id
    
    async def test_ingest_like(self, db_session):
        """Test ingesting a like event"""
        service = PeopleIngestionService(db_session)
        
        event = await service.ingest_like(
            channel='facebook',
            handle='fb_user_789',
            platform_post_id='fb_post_123',
            full_name='FB User'
        )
        
        assert event.event_type == 'liked'
        assert event.channel == 'facebook'
    
    async def test_traffic_type_separation(self, db_session):
        """Test organic vs paid event tracking"""
        service = PeopleIngestionService(db_session)
        
        organic = await service.ingest_comment(
            channel='instagram',
            handle='@organic_user',
            platform_post_id='post_123',
            comment_text='Organic comment',
            comment_id='org_1',
            traffic_type='organic'
        )
        
        paid = await service.ingest_comment(
            channel='instagram',
            handle='@paid_user',
            platform_post_id='ad_post_456',
            comment_text='Paid ad comment',
            comment_id='paid_1',
            traffic_type='paid'
        )
        
        assert organic.traffic_type == 'organic'
        assert paid.traffic_type == 'paid'


@pytest.mark.asyncio
class TestPersonLensComputer:
    """Test Person Lens Computation"""
    
    async def test_compute_lens_new_person(self, db_session):
        """Test computing lens for person with events"""
        service = PeopleIngestionService(db_session)
        computer = PersonLensComputer(db_session)
        
        # Create person with multiple events
        person = await service.get_or_create_person_by_identity('instagram', '@active_user')
        
        # Add various events
        await service.record_event(
            person.id, 'instagram', 'commented',
            content_excerpt='I love AI automation! This is so technical and cool.'
        )
        await service.record_event(
            person.id, 'instagram', 'commented',
            content_excerpt='Great tutorial on API integration!'
        )
        await service.record_event(
            person.id, 'instagram', 'liked',
            platform_id='post_123'
        )
        
        # Compute lens
        insights = await computer.compute_lens_for_person(person.id)
        
        assert insights is not None
        assert insights.activity_state == 'active'
        assert insights.warmth_score > 0
        assert 'instagram' in insights.channel_preferences
        assert len(insights.interests) > 0
    
    async def test_activity_state_classification(self, db_session):
        """Test activity state transitions"""
        service = PeopleIngestionService(db_session)
        computer = PersonLensComputer(db_session)
        
        person = await service.get_or_create_person_by_identity('instagram', '@test_user')
        
        # Recent event = active
        await service.record_event(person.id, 'instagram', 'commented', content_excerpt='Recent')
        insights = await computer.compute_lens_for_person(person.id)
        assert insights.activity_state == 'active'
    
    async def test_warmth_score_calculation(self, db_session):
        """Test warmth score reflects engagement level"""
        service = PeopleIngestionService(db_session)
        computer = PersonLensComputer(db_session)
        
        person = await service.get_or_create_person_by_identity('instagram', '@engaged_user')
        
        # High engagement (multiple comments)
        for i in range(5):
            await service.record_event(
                person.id, 'instagram', 'commented',
                content_excerpt=f'Comment {i}'
            )
        
        insights = await computer.compute_lens_for_person(person.id)
        warmth_high = insights.warmth_score
        
        # Create another person with just one like
        person2 = await service.get_or_create_person_by_identity('instagram', '@casual_user')
        await service.record_event(person2.id, 'instagram', 'liked')
        insights2 = await computer.compute_lens_for_person(person2.id)
        warmth_low = insights2.warmth_score
        
        # Engaged user should have higher warmth
        assert warmth_high > warmth_low
    
    async def test_channel_preferences(self, db_session):
        """Test channel preference calculation"""
        service = PeopleIngestionService(db_session)
        computer = PersonLensComputer(db_session)
        
        person = await service.get_or_create_person_by_identity('instagram', '@multi_channel')
        
        # 3 Instagram events
        for _ in range(3):
            await service.record_event(person.id, 'instagram', 'commented', content_excerpt='IG')
        
        # 1 Facebook event
        await service.record_event(person.id, 'facebook', 'liked')
        
        insights = await computer.compute_lens_for_person(person.id)
        
        # Instagram should be preferred
        assert insights.channel_preferences['instagram'] > insights.channel_preferences.get('facebook', 0)


@pytest.mark.asyncio
class TestPeopleAPI:
    """Test People API Endpoints"""
    
    async def test_ingest_comment_endpoint(self, client, db_session):
        """Test POST /api/people/ingest/comment"""
        response = await client.post('/api/people/ingest/comment', json={
            'channel': 'instagram',
            'handle': '@api_test_user',
            'platform_post_id': 'post_789',
            'comment_text': 'Testing via API!',
            'comment_id': 'api_comment_1',
            'user_data': {
                'full_name': 'API Test User',
                'profile_pic': 'https://example.com/pic.jpg'
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'person_id' in data
        assert 'event_id' in data
    
    async def test_get_person(self, client, db_session):
        """Test GET /api/people/{id}"""
        # Create a person first
        service = PeopleIngestionService(db_session)
        person = await service.get_or_create_person_by_identity(
            'instagram', '@get_test',
            full_name='Get Test User'
        )
        
        response = await client.get(f'/api/people/{person.id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['full_name'] == 'Get Test User'
    
    async def test_get_person_insights(self, client, db_session):
        """Test GET /api/people/{id}/insights"""
        service = PeopleIngestionService(db_session)
        computer = PersonLensComputer(db_session)
        
        person = await service.get_or_create_person_by_identity('instagram', '@insights_test')
        await service.record_event(person.id, 'instagram', 'commented', content_excerpt='Test')
        await computer.compute_lens_for_person(person.id)
        
        response = await client.get(f'/api/people/{person.id}/insights')
        
        assert response.status_code == 200
        data = response.json()
        assert 'warmth_score' in data
        assert 'activity_state' in data
        assert 'interests' in data
    
    async def test_recompute_lens(self, client, db_session):
        """Test POST /api/people/{id}/recompute-lens"""
        service = PeopleIngestionService(db_session)
        person = await service.get_or_create_person_by_identity('instagram', '@recompute_test')
        await service.record_event(person.id, 'instagram', 'commented', content_excerpt='Recompute')
        
        response = await client.post(f'/api/people/{person.id}/recompute-lens')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'


# Pytest fixtures
@pytest.fixture
async def db_session():
    """Mock database session"""
    # TODO: Set up actual test database or use pytest-asyncio with real DB
    from database.connection import get_db
    async for session in get_db():
        yield session


@pytest.fixture
async def client():
    """Mock FastAPI test client"""
    from httpx import AsyncClient
    from main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
