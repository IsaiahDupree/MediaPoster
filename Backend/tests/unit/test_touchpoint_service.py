"""
Touchpoint Attribution Service Tests (OPS-011)
==============================================
Tests for TouchpointService ensuring full attribution chain validation.

Test Coverage:
- OPS-011: Touchpoint attribution logging
- Full attribution chain validation
- No orphaned touchpoints allowed
- Metrics syncing from posted content
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from services.touchpoint_service import (
    TouchpointService,
    TouchpointAttributionError
)
from database.models import Touchpoint, Offer, ICP, ContentTemplate, Brand


@pytest_asyncio.fixture
async def touchpoint_service():
    """Create fresh touchpoint service instance"""
    TouchpointService._instance = None
    service = TouchpointService.get_instance()
    yield service
    TouchpointService._instance = None


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing"""
    with patch('services.touchpoint_service.EventBus') as mock:
        mock_instance = Mock()
        mock_instance.publish = AsyncMock()
        mock_instance.set_source = Mock()
        mock.get_instance.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_brand_id():
    """Sample brand ID"""
    return uuid4()


@pytest.fixture
def sample_offer_id():
    """Sample offer ID"""
    return uuid4()


@pytest.fixture
def sample_icp_id():
    """Sample ICP ID"""
    return uuid4()


@pytest.fixture
def sample_template_id():
    """Sample template ID"""
    return uuid4()


class TestTouchpointServiceCore:
    """Test core touchpoint service functionality"""

    @pytest.mark.asyncio
    async def test_service_singleton(self, touchpoint_service):
        """Test service uses singleton pattern"""
        another_service = TouchpointService.get_instance()
        assert another_service is touchpoint_service

    @pytest.mark.asyncio
    async def test_service_initialization(self, touchpoint_service):
        """Test service initializes correctly"""
        assert touchpoint_service.touchpoints_created == 0
        assert touchpoint_service.orphaned_detected == 0
        assert touchpoint_service.attribution_failures == 0


class TestTouchpointCreation:
    """Test touchpoint creation with attribution validation"""

    @pytest.mark.asyncio
    async def test_create_touchpoint_validates_offer(
        self,
        touchpoint_service,
        sample_offer_id
    ):
        """Test creating touchpoint validates offer exists"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            # Mock session context manager
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock offer not found
            mock_session_instance.get = AsyncMock(return_value=None)

            # Should raise error for missing offer
            with pytest.raises(TouchpointAttributionError, match="Offer not found"):
                await touchpoint_service.create_touchpoint(
                    channel="twitter",
                    message_type="post",
                    offer_id=sample_offer_id
                )

    @pytest.mark.asyncio
    async def test_create_touchpoint_validates_icp_brand_match(
        self,
        touchpoint_service,
        sample_brand_id,
        sample_offer_id,
        sample_icp_id
    ):
        """Test ICP brand must match offer brand"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock offer and ICP with different brands
            mock_offer = Mock(spec=Offer)
            mock_offer.brand_id = sample_brand_id

            mock_icp = Mock(spec=ICP)
            mock_icp.brand_id = uuid4()  # Different brand

            async def mock_get(model_class, id):
                if model_class == Offer:
                    return mock_offer
                elif model_class == ICP:
                    return mock_icp
                return None

            mock_session_instance.get = mock_get

            # Should raise error for brand mismatch
            with pytest.raises(
                TouchpointAttributionError,
                match="ICP brand .* doesn't match Offer brand"
            ):
                await touchpoint_service.create_touchpoint(
                    channel="twitter",
                    message_type="post",
                    offer_id=sample_offer_id,
                    icp_id=sample_icp_id
                )

    @pytest.mark.asyncio
    async def test_create_touchpoint_success(
        self,
        touchpoint_service,
        sample_brand_id,
        sample_offer_id,
        sample_icp_id,
        sample_template_id
    ):
        """Test successful touchpoint creation with full attribution"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock offer, ICP, and template
            mock_offer = Mock(spec=Offer)
            mock_offer.brand_id = sample_brand_id

            mock_icp = Mock(spec=ICP)
            mock_icp.brand_id = sample_brand_id

            mock_template = Mock(spec=ContentTemplate)

            async def mock_get(model_class, id):
                if model_class == Offer:
                    return mock_offer
                elif model_class == ICP:
                    return mock_icp
                elif model_class == ContentTemplate:
                    return mock_template
                return None

            mock_session_instance.get = mock_get
            mock_session_instance.add = Mock()
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()

            # Create touchpoint
            touchpoint = await touchpoint_service.create_touchpoint(
                channel="twitter",
                message_type="post",
                offer_id=sample_offer_id,
                icp_id=sample_icp_id,
                template_id=sample_template_id,
                brand_id=sample_brand_id,
                shortlink="https://link.co/abc123"
            )

            # Verify touchpoint was created
            assert mock_session_instance.add.called
            assert touchpoint_service.touchpoints_created == 1


class TestTouchpointMetrics:
    """Test touchpoint metrics updates"""

    @pytest.mark.asyncio
    async def test_update_touchpoint_metrics(
        self,
        touchpoint_service
    ):
        """Test updating touchpoint metrics"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock touchpoint
            touchpoint_id = uuid4()
            mock_touchpoint = Mock(spec=Touchpoint)
            mock_touchpoint.id = touchpoint_id
            mock_touchpoint.impressions = 0
            mock_touchpoint.clicks = 0
            mock_touchpoint.likes = 0
            mock_touchpoint.replies = 0
            mock_touchpoint.reposts = 0

            mock_session_instance.get = AsyncMock(return_value=mock_touchpoint)
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()

            # Update metrics
            await touchpoint_service.update_touchpoint_metrics(
                touchpoint_id=touchpoint_id,
                impressions=1000,
                clicks=50,
                likes=100,
                replies=20,
                reposts=10
            )

            # Verify metrics were updated
            assert mock_touchpoint.impressions == 1000
            assert mock_touchpoint.clicks == 50
            assert mock_touchpoint.likes == 100
            assert mock_touchpoint.replies == 20
            assert mock_touchpoint.reposts == 10

            # Verify rates were calculated
            assert mock_touchpoint.click_rate == 0.05  # 50/1000
            assert mock_touchpoint.engagement_rate == 0.13  # (100+20+10)/1000

    @pytest.mark.asyncio
    async def test_update_metrics_calculates_reward_score(
        self,
        touchpoint_service
    ):
        """Test reward score is calculated from metrics"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock touchpoint
            touchpoint_id = uuid4()
            mock_touchpoint = Mock(spec=Touchpoint)
            mock_touchpoint.id = touchpoint_id
            mock_touchpoint.impressions = 1000
            mock_touchpoint.clicks = 50
            mock_touchpoint.likes = 100
            mock_touchpoint.replies = 20
            mock_touchpoint.reposts = 10

            mock_session_instance.get = AsyncMock(return_value=mock_touchpoint)
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()

            # Update metrics (trigger calculation)
            await touchpoint_service.update_touchpoint_metrics(
                touchpoint_id=touchpoint_id,
                impressions=1000
            )

            # Reward score should be calculated
            # Formula: 1.0*click + 0.8*reply + 0.6*repost + 0.4*like
            # = 1.0*0.05 + 0.8*0.02 + 0.6*0.01 + 0.4*0.1
            # = 0.05 + 0.016 + 0.006 + 0.04 = 0.112
            assert mock_touchpoint.reward_score == pytest.approx(0.112, rel=0.01)


class TestTouchpointQueries:
    """Test touchpoint query methods"""

    @pytest.mark.asyncio
    async def test_get_touchpoints_by_offer(
        self,
        touchpoint_service,
        sample_offer_id
    ):
        """Test querying touchpoints by offer"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock result
            mock_result = Mock()
            mock_result.scalars().all.return_value = [
                Mock(spec=Touchpoint),
                Mock(spec=Touchpoint)
            ]
            mock_session_instance.execute = AsyncMock(return_value=mock_result)

            # Query touchpoints
            touchpoints = await touchpoint_service.get_touchpoints_by_offer(
                sample_offer_id
            )

            assert len(touchpoints) == 2

    @pytest.mark.asyncio
    async def test_get_touchpoints_by_template(
        self,
        touchpoint_service,
        sample_template_id
    ):
        """Test querying touchpoints by template"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock result
            mock_result = Mock()
            mock_result.scalars().all.return_value = [Mock(spec=Touchpoint)]
            mock_session_instance.execute = AsyncMock(return_value=mock_result)

            # Query touchpoints
            touchpoints = await touchpoint_service.get_touchpoints_by_template(
                sample_template_id
            )

            assert len(touchpoints) == 1


class TestOrphanDetection:
    """Test orphaned touchpoint detection (OPS-011 requirement)"""

    @pytest.mark.asyncio
    async def test_detect_orphaned_touchpoints(self, touchpoint_service):
        """Test detection of touchpoints with missing offer_id"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock orphaned touchpoints
            orphaned = [
                Mock(spec=Touchpoint, id=uuid4(), offer_id=None),
                Mock(spec=Touchpoint, id=uuid4(), offer_id=None)
            ]

            mock_result = Mock()
            mock_result.scalars().all.return_value = orphaned
            mock_session_instance.execute = AsyncMock(return_value=mock_result)

            # Detect orphans
            found = await touchpoint_service.detect_orphaned_touchpoints()

            assert len(found) == 2
            assert touchpoint_service.orphaned_detected == 2

    @pytest.mark.asyncio
    async def test_no_orphaned_touchpoints(self, touchpoint_service):
        """Test when no orphaned touchpoints exist"""
        with patch('services.touchpoint_service.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            # Mock no orphans
            mock_result = Mock()
            mock_result.scalars().all.return_value = []
            mock_session_instance.execute = AsyncMock(return_value=mock_result)

            # Detect orphans
            found = await touchpoint_service.detect_orphaned_touchpoints()

            assert len(found) == 0
            assert touchpoint_service.orphaned_detected == 0


class TestServiceStatus:
    """Test service status reporting"""

    @pytest.mark.asyncio
    async def test_get_status_healthy(self, touchpoint_service):
        """Test status when no orphans detected"""
        status = touchpoint_service.get_status()

        assert status["health"] == "healthy"
        assert status["orphaned_detected"] == 0

    @pytest.mark.asyncio
    async def test_get_status_degraded(self, touchpoint_service):
        """Test status when orphans detected"""
        # Simulate orphans detected
        touchpoint_service.orphaned_detected = 5

        status = touchpoint_service.get_status()

        assert status["health"] == "degraded"
        assert status["orphaned_detected"] == 5
