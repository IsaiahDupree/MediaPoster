"""
Tests for Content Metrics Aggregation (Phase 4)
Tests ContentMetricsService and Content Metrics API
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from services.content_metrics import ContentMetricsService
from database.models import ContentItem, ContentVariant, ContentMetric, ContentRollup


@pytest.mark.asyncio
class TestContentMetricsService:
    """Test Content Metrics Service"""
    
    async def test_poll_metrics_for_variant(self, db_session, mock_adapter):
        """Test polling metrics from adapter"""
        service = ContentMetricsService(db_session)
        
        # Create content and variant
        content = ContentItem(
            id=uuid4(),
            type='video',
            title='Test Content'
        )
        db_session.add(content)
        
        variant = ContentVariant(
            id=uuid4(),
            content_id=content.id,
            platform='instagram',
            platform_post_id='ig_post_123',
            published_at=datetime.utcnow()
        )
        db_session.add(variant)
        await db_session.commit()
        
        # Poll metrics
        metric = await service.poll_metrics_for_variant(variant)
        
        assert metric is not None
        assert metric.variant_id == variant.id
        assert metric.views is not None
        assert metric.traffic_type == 'organic'
    
    async def test_recompute_rollup_single_platform(self, db_session):
        """Test rollup computation with single platform"""
        service = ContentMetricsService(db_session)
        
        # Create content and variant
        content = ContentItem(id=uuid4(), type='video', title='Test')
        variant = ContentVariant(
            id=uuid4(),
            content_id=content.id,
            platform='instagram',
            published_at=datetime.utcnow()
        )
        db_session.add_all([content, variant])
        await db_session.flush()
        
        # Add metrics
        metric = ContentMetric(
            variant_id=variant.id,
            views=1000,
            likes=50,
            comments=10,
            shares=5
        )
        db_session.add(metric)
        await db_session.commit()
        
        # Recompute rollup
        rollup = await service.recompute_rollup(content.id)
        
        assert rollup.total_views == 1000
        assert rollup.total_likes == 50
        assert rollup.total_comments == 10
        assert rollup.best_platform == 'instagram'
    
    async def test_recompute_rollup_multi_platform(self, db_session):
        """Test rollup aggregation across multiple platforms"""
        service = ContentMetricsService(db_session)
        
        content = ContentItem(id=uuid4(), type='video', title='Multi-platform Test')
        db_session.add(content)
        await db_session.flush()
        
        # Create variants for different platforms
        platforms = ['instagram', 'tiktok', 'youtube']
        for platform in platforms:
            variant = ContentVariant(
                id=uuid4(),
                content_id=content.id,
                platform=platform,
                published_at=datetime.utcnow()
            )
            db_session.add(variant)
            await db_session.flush()
            
            # Add metrics (Instagram gets more views)
            views = 2000 if platform == 'instagram' else 500
            metric = ContentMetric(
                variant_id=variant.id,
                views=views,
                likes=views // 20
            )
            db_session.add(metric)
        
        await db_session.commit()
        
        # Recompute
        rollup = await service.recompute_rollup(content.id)
        
        # Total views = 2000 + 500 + 500 = 3000
        assert rollup.total_views == 3000
        # Instagram should be best platform
        assert rollup.best_platform == 'instagram'
    
    async def test_organic_vs_paid_separation(self, db_session):
        """Test that organic and paid metrics stay separate"""
        service = ContentMetricsService(db_session)
        
        content = ContentItem(id=uuid4(), type='video', title='Paid Test')
        db_session.add(content)
        await db_session.flush()
        
        # Organic variant
        organic_variant = ContentVariant(
            id=uuid4(),
            content_id=content.id,
            platform='instagram',
            is_paid=False,
            published_at=datetime.utcnow()
        )
        db_session.add(organic_variant)
        await db_session.flush()
        
        organic_metric = ContentMetric(
            variant_id=organic_variant.id,
            views=500,
            traffic_type='organic'
        )
        db_session.add(organic_metric)
        
        # Paid variant
        paid_variant = ContentVariant(
            id=uuid4(),
            content_id=content.id,
            platform='instagram',
            is_paid=True,
            published_at=datetime.utcnow()
        )
        db_session.add(paid_variant)
        await db_session.flush()
        
        paid_metric = ContentMetric(
            variant_id=paid_variant.id,
            views=2000,
            traffic_type='paid'
        )
        db_session.add(paid_metric)
        
        await db_session.commit()
        
        # Verify traffic types
        assert organic_metric.traffic_type == 'organic'
        assert paid_metric.traffic_type == 'paid'
        
        # Rollup aggregates both
        rollup = await service.recompute_rollup(content.id)
        assert rollup.total_views == 2500  # 500 + 2000
    
    async def test_poll_all_recent_content(self, db_session, mock_adapter):
        """Test polling all recent content"""
        service = ContentMetricsService(db_session)
        
        # Create recent content
        for i in range(3):
            content = ContentItem(id=uuid4(), type='video', title=f'Content {i}')
            variant = ContentVariant(
                id=uuid4(),
                content_id=content.id,
                platform='instagram',
                platform_post_id=f'ig_{i}',
                published_at=datetime.utcnow() - timedelta(hours=12)
            )
            db_session.add_all([content, variant])
        
        await db_session.commit()
        
        # Poll recent
        stats = await service.poll_all_recent_content(hours=48)
        
        assert stats['content_items'] >= 3
        assert stats['metrics_collected'] >= 0


@pytest.mark.asyncio  
class TestContentMetricsAPI:
    """Test Content Metrics API Endpoints"""
    
    async def test_poll_content_metrics(self, client, db_session):
        """Test POST /api/content-metrics/poll/{content_id}"""
        # Create content
        content = ContentItem(id=uuid4(), type='video', title='API Test')
        variant = ContentVariant(
            id=uuid4(),
            content_id=content.id,
            platform='instagram',
            platform_post_id='ig_test',
            published_at=datetime.utcnow()
        )
        db_session.add_all([content, variant])
        await db_session.commit()
        
        response = await client.post(f'/api/content-metrics/poll/{content.id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'metrics_collected' in data
    
    async def test_get_content_rollup(self, client, db_session):
        """Test GET /api/content-metrics/{content_id}/rollup"""
        service = ContentMetricsService(db_session)
        
        content = ContentItem(id=uuid4(), type='video', title='Rollup Test')
        variant = ContentVariant(
            id=uuid4(),
            content_id=content.id,
            platform='instagram',
            published_at=datetime.utcnow()
        )
        metric = ContentMetric(
            variant_id=variant.id,
            views=1500,
            likes=75
        )
        db_session.add_all([content, variant, metric])
        await db_session.commit()
        
        # Create rollup
        await service.recompute_rollup(content.id)
        
        response = await client.get(f'/api/content-metrics/{content.id}/rollup')
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_views'] == 1500
        assert data['total_likes'] == 75
    
    async def test_poll_recent_endpoint(self, client):
        """Test POST /api/content-metrics/poll-recent"""
        response = await client.post('/api/content-metrics/poll-recent', params={'hours': 24})
        
        assert response.status_code == 200
        data = response.json()
        assert 'content_items' in data
        assert 'metrics_collected' in data


# Fixtures
@pytest.fixture
def mock_adapter():
    """Mock platform adapter for testing"""
    from connectors.base import SourceAdapter, PlatformMetricSnapshot
    
    class MockAdapter(SourceAdapter):
        @property
        def id(self):
            return 'mock'
        
        @property
        def display_name(self):
            return 'Mock Adapter'
        
        def is_enabled(self):
            return True
        
        def list_supported_platforms(self):
            return ['instagram', 'tiktok', 'youtube']
        
        async def fetch_metrics(self, platform, platform_post_id):
            return PlatformMetricSnapshot(
                platform=platform,
                platform_post_id=platform_post_id,
                views=1000,
                likes=50,
                comments=10
            )
    
    return MockAdapter()


@pytest.fixture
async def db_session():
    """Mock database session"""
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
