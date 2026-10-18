"""
Attribution Unit Tests (TEST-005)
===================================
Tests for shortlink attribution system that encodes the full attribution chain:
- Touchpoint ID
- Offer ID
- Template ID
- ICP ID

From PRD_CONTENT_OPS_TESTS.md Section 2.5
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
from unittest.mock import patch, AsyncMock

from services.shortlink_service import ShortlinkService
from database.models import Brand, Offer, ContentTemplate, ICP, Touchpoint


@pytest_asyncio.fixture
async def test_brand(db_session):
    """Create a test brand entity"""
    brand = Brand(
        id=uuid4(),
        name="Test Brand",
        description="Test brand for attribution tests"
    )
    db_session.add(brand)
    await db_session.commit()
    await db_session.refresh(brand)
    return brand


@pytest_asyncio.fixture
async def test_offer(db_session, test_brand):
    """Create a test offer entity"""
    offer = Offer(
        id=uuid4(),
        brand_id=test_brand.id,
        title="Test Offer",
        description="Test offer for attribution tests",
        cta_text="Learn More",
        landing_page_url="https://keywordradar.app"
    )
    db_session.add(offer)
    await db_session.commit()
    await db_session.refresh(offer)
    return offer


@pytest_asyncio.fixture
async def test_template(db_session, test_brand):
    """Create a test content template"""
    template = ContentTemplate(
        id=uuid4(),
        brand_id=test_brand.id,
        name="Test Template",
        awareness_level="problem_aware",
        prompt_text="Test template: {problem}",
        required_variables=["problem"],
        fate_focus=0.25,
        fate_authority=0.25,
        fate_tribe=0.25,
        fate_emotion=0.25
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def test_icp(db_session):
    """Create a test ICP (Ideal Customer Profile)"""
    icp = ICP(
        id=uuid4(),
        name="Test ICP",
        description="Test ICP for attribution tests"
    )
    db_session.add(icp)
    await db_session.commit()
    await db_session.refresh(icp)
    return icp


@pytest_asyncio.fixture
async def test_touchpoint(db_session, test_brand, test_offer):
    """Create a test touchpoint"""
    touchpoint = Touchpoint(
        id=uuid4(),
        brand_id=test_brand.id,
        offer_id=test_offer.id,
        channel="twitter",
        message_type="post"
    )
    db_session.add(touchpoint)
    await db_session.commit()
    await db_session.refresh(touchpoint)
    return touchpoint


@pytest_asyncio.fixture
async def shortlink_service(db_session):
    """Create shortlink service with mocked database session"""
    # Reset singleton
    ShortlinkService._instance = None

    # Patch async_session_maker to return our test session
    with patch('services.shortlink_service.async_session_maker') as mock_maker:
        # Make the mock return a context manager that yields the test session
        mock_maker.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        service = ShortlinkService.get_instance()
        yield service

    # Cleanup
    ShortlinkService._instance = None


class TestShortlinkEncoding:
    """Test that shortlinks encode all attribution IDs"""

    @pytest.mark.asyncio
    async def test_shortlink_encodes_all_ids(self, shortlink_service, test_touchpoint, test_offer, test_template, test_icp):
        """Shortlink stores all attribution IDs (touchpoint, offer, template, icp)"""
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            touchpoint_id=test_touchpoint.id,
            offer_id=test_offer.id,
            template_id=test_template.id,
            icp_id=test_icp.id,
            utm_source="twitter",
            utm_campaign="spring_launch"
        )

        # Verify all IDs are stored
        assert shortlink.touchpoint_id == test_touchpoint.id, "Touchpoint ID must be preserved"
        assert shortlink.offer_id == test_offer.id, "Offer ID must be preserved"
        assert shortlink.template_id == test_template.id, "Template ID must be preserved"
        assert shortlink.icp_id == test_icp.id, "ICP ID must be preserved"

    @pytest.mark.asyncio
    async def test_shortlink_decodes_correctly(self, shortlink_service, test_touchpoint, test_offer, test_template, test_icp):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app/pricing",
            touchpoint_id=test_touchpoint.id,
            offer_id=test_offer.id,
            template_id=test_template.id,
            icp_id=test_icp.id
        )

        # Retrieve and verify IDs
        retrieved = await service.get_shortlink(shortlink.short_code)

        assert retrieved is not None, "Shortlink must be retrievable"
        assert retrieved.touchpoint_id == test_touchpoint.id
        assert retrieved.offer_id == test_offer.id
        assert retrieved.template_id == test_template.id
        assert retrieved.icp_id == test_icp.id

    @pytest.mark.asyncio
    async def test_utm_format_valid(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id,
            utm_source="twitter",
            utm_medium="social",
            utm_campaign="spring_launch",
            utm_content="variant_a",
            utm_term="keyword_research"
        )

        # Parse destination URL
        parsed = urlparse(shortlink.destination_url)
        params = parse_qs(parsed.query)

        # Verify UTM params are present
        assert "utm_source" in params, "utm_source must be in URL"
        assert "utm_medium" in params, "utm_medium must be in URL"
        assert "utm_campaign" in params, "utm_campaign must be in URL"
        assert "utm_content" in params, "utm_content must be in URL"
        assert "utm_term" in params, "utm_term must be in URL"

        # Verify values
        assert params["utm_source"][0] == "twitter"
        assert params["utm_medium"][0] == "social"
        assert params["utm_campaign"][0] == "spring_launch"

    @pytest.mark.asyncio
    async def test_click_maps_to_touchpoint(self, shortlink_service, test_touchpoint, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            touchpoint_id=test_touchpoint.id,
            offer_id=test_offer.id
        )

        # Track a click
        initial_count = shortlink.click_count
        destination = await service.track_click(shortlink.short_code)

        assert destination is not None, "Click must return destination"
        assert destination == shortlink.destination_url

        # Verify click was tracked
        stats = await service.get_shortlink_stats(shortlink.short_code)
        assert stats is not None
        assert stats["click_count"] == initial_count + 1, "Click count must increment"
        assert stats["attribution"]["touchpoint_id"] == str(test_touchpoint.id)


class TestAttributionIntegrity:
    """Test that attribution chain remains intact"""

    @pytest.mark.asyncio
    async def test_all_ids_preserved_in_stats(self, shortlink_service, test_touchpoint, test_offer, test_template, test_icp):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            touchpoint_id=test_touchpoint.id,
            offer_id=test_offer.id,
            template_id=test_template.id,
            icp_id=test_icp.id
        )

        stats = await service.get_shortlink_stats(shortlink.short_code)

        assert stats is not None
        assert stats["attribution"]["touchpoint_id"] == str(test_touchpoint.id)
        assert stats["attribution"]["offer_id"] == str(test_offer.id)
        assert stats["attribution"]["template_id"] == str(test_template.id)
        assert stats["attribution"]["icp_id"] == str(test_icp.id)

    @pytest.mark.asyncio
    async def test_optional_ids_can_be_null(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        # Create shortlink with only offer_id
        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        assert shortlink.offer_id == test_offer.id
        assert shortlink.touchpoint_id is None
        assert shortlink.template_id is None
        assert shortlink.icp_id is None


class TestShortlinkGeneration:
    """Test shortlink code generation"""

    @pytest.mark.asyncio
    async def test_generates_unique_codes(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink1 = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        shortlink2 = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        assert shortlink1.short_code != shortlink2.short_code, "Codes must be unique"

    @pytest.mark.asyncio
    async def test_short_code_format(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        assert len(shortlink.short_code) > 0, "Code must not be empty"
        assert shortlink.short_code.isalnum(), "Code must be alphanumeric"

    @pytest.mark.asyncio
    async def test_full_url_format(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        full_url = service.get_full_url(shortlink.short_code)

        assert full_url.startswith("https://"), "Full URL must use HTTPS"
        assert shortlink.short_code in full_url, "Full URL must contain short code"


class TestClickTracking:
    """Test click tracking functionality"""

    @pytest.mark.asyncio
    async def test_click_increments_count(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        initial_count = shortlink.click_count

        # Track 3 clicks
        for i in range(3):
            await service.track_click(shortlink.short_code)

        stats = await service.get_shortlink_stats(shortlink.short_code)
        assert stats["click_count"] == initial_count + 3

    @pytest.mark.asyncio
    async def test_click_updates_last_clicked_at(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        # Initial state
        assert shortlink.last_clicked_at is None

        # Track click
        await service.track_click(shortlink.short_code)

        stats = await service.get_shortlink_stats(shortlink.short_code)
        assert stats["last_clicked_at"] is not None

    @pytest.mark.asyncio
    async def test_invalid_code_returns_none(self, shortlink_service):
        """
        (docstring preserved)
        """
        service = shortlink_service

        destination = await service.track_click("invalid_code_xyz")

        assert destination is None, "Invalid code must return None"

    @pytest.mark.asyncio
    async def test_expired_link_returns_none(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        # Create shortlink that expires in -1 days (already expired)
        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id,
            expires_in_days=-1  # Already expired
        )

        destination = await service.track_click(shortlink.short_code)

        assert destination is None, "Expired link must return None"

    @pytest.mark.asyncio
    async def test_inactive_link_returns_none(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        # Deactivate
        success = await service.deactivate_shortlink(shortlink.short_code)
        assert success is True

        # Try to click
        destination = await service.track_click(shortlink.short_code)

        assert destination is None, "Inactive link must return None"


class TestURLValidation:
    """Test URL validation"""

    @pytest.mark.asyncio
    async def test_valid_urls_accepted(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        valid_urls = [
            "https://keywordradar.app",
            "https://example.com/path",
            "http://example.com",
            "https://example.com:8080/path?query=value"
        ]

        for url in valid_urls:
            shortlink = await service.create_shortlink(
                destination_url=url,
                offer_id=test_offer.id
            )
            assert shortlink is not None, f"Valid URL should be accepted: {url}"

    @pytest.mark.asyncio
    async def test_invalid_urls_rejected(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Invalid scheme
            "//example.com",  # No scheme
            ""
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError, match="Invalid destination URL"):
                await service.create_shortlink(
                    destination_url=url,
                    offer_id=test_offer.id
                )


class TestUTMParameters:
    """Test UTM parameter handling"""

    @pytest.mark.asyncio
    async def test_utm_params_added_to_url(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id,
            utm_source="twitter",
            utm_campaign="launch"
        )

        assert "utm_source=twitter" in shortlink.destination_url
        assert "utm_campaign=launch" in shortlink.destination_url

    @pytest.mark.asyncio
    async def test_utm_params_preserved_in_existing_query(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app?existing=param",
            offer_id=test_offer.id,
            utm_source="twitter"
        )

        assert "existing=param" in shortlink.destination_url
        assert "utm_source=twitter" in shortlink.destination_url
        assert shortlink.destination_url.count('?') == 1, "Should have only one '?'"

    @pytest.mark.asyncio
    async def test_utm_params_stored_in_record(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id,
            utm_source="twitter",
            utm_medium="social",
            utm_campaign="launch",
            utm_content="variant_a",
            utm_term="keyword"
        )

        assert shortlink.utm_source == "twitter"
        assert shortlink.utm_medium == "social"
        assert shortlink.utm_campaign == "launch"
        assert shortlink.utm_content == "variant_a"
        assert shortlink.utm_term == "keyword"


class TestExpirationHandling:
    """Test link expiration"""

    @pytest.mark.asyncio
    async def test_future_expiration_allowed(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id,
            expires_in_days=30
        )

        assert shortlink.expires_at is not None
        assert shortlink.expires_at > datetime.now(timezone.utc)

        # Should still work
        destination = await service.track_click(shortlink.short_code)
        assert destination is not None

    @pytest.mark.asyncio
    async def test_no_expiration_allowed(self, shortlink_service, test_offer):
        """
        (docstring preserved)
        """
        service = shortlink_service

        shortlink = await service.create_shortlink(
            destination_url="https://keywordradar.app",
            offer_id=test_offer.id
        )

        assert shortlink.expires_at is None


class TestSingletonPattern:
    """Test singleton service pattern"""

    def test_get_instance_returns_same_instance(self):
        """get_instance() returns the same instance"""
        service1 = ShortlinkService.get_instance()
        service2 = ShortlinkService.get_instance()

        assert service1 is service2, "Should return same instance"

    def test_cannot_instantiate_directly(self):
        """Cannot create multiple instances directly"""
        # First instance is created via get_instance()
        ShortlinkService.get_instance()

        # Attempting direct instantiation should raise error
        with pytest.raises(RuntimeError, match="Use ShortlinkService.get_instance"):
            ShortlinkService()
