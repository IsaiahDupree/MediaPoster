"""
Shortlink Attribution Service Tests (OPS-006)
==============================================
Tests for shortlink creation, tracking, and attribution
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone

from services.shortlink_service import ShortlinkService, get_shortlink_service


@pytest_asyncio.fixture
async def shortlink_service():
    """Create a fresh shortlink service instance for each test"""
    # Reset singleton
    ShortlinkService._instance = None
    service = ShortlinkService.get_instance()
    yield service


@pytest.mark.asyncio
async def test_shortlink_service_singleton():
    """Test that shortlink service is a singleton"""
    ShortlinkService._instance = None
    service1 = ShortlinkService.get_instance()
    service2 = get_shortlink_service()
    assert service1 is service2


@pytest.mark.asyncio
async def test_create_shortlink_basic(shortlink_service):
    """Test basic shortlink creation"""
    offer_id = uuid4()
    destination = "https://example.com/product"

    shortlink = await shortlink_service.create_shortlink(
        destination_url=destination,
        offer_id=offer_id
    )

    assert shortlink is not None
    assert shortlink.short_code is not None
    assert len(shortlink.short_code) == 8
    assert shortlink.destination_url == destination
    assert shortlink.offer_id == offer_id
    assert shortlink.is_active is True
    assert shortlink.click_count == 0


@pytest.mark.asyncio
async def test_create_shortlink_with_full_attribution(shortlink_service):
    """Test shortlink with complete attribution chain"""
    offer_id = uuid4()
    template_id = uuid4()
    icp_id = uuid4()
    touchpoint_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id,
        template_id=template_id,
        icp_id=icp_id,
        touchpoint_id=touchpoint_id
    )

    # All attribution IDs should be encoded
    assert shortlink.offer_id == offer_id
    assert shortlink.template_id == template_id
    assert shortlink.icp_id == icp_id
    assert shortlink.touchpoint_id == touchpoint_id


@pytest.mark.asyncio
async def test_create_shortlink_with_utm_params(shortlink_service):
    """Test shortlink with UTM parameters"""
    offer_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id,
        utm_source="twitter",
        utm_medium="social",
        utm_campaign="spring_launch",
        utm_content="variant_a",
        utm_term="founders"
    )

    # UTM parameters should be added to destination URL
    assert "utm_source=twitter" in shortlink.destination_url
    assert "utm_medium=social" in shortlink.destination_url
    assert "utm_campaign=spring_launch" in shortlink.destination_url
    assert "utm_content=variant_a" in shortlink.destination_url
    assert "utm_term=founders" in shortlink.destination_url

    # UTM values should be stored in database
    assert shortlink.utm_source == "twitter"
    assert shortlink.utm_medium == "social"
    assert shortlink.utm_campaign == "spring_launch"


@pytest.mark.asyncio
async def test_shortlink_utm_format_validation(shortlink_service):
    """Test that UTM format is valid (OPS-006 acceptance criterion)"""
    offer_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product?existing=param",
        offer_id=offer_id,
        utm_source="twitter",
        utm_campaign="test"
    )

    # Should append UTM params with & (not ?)
    assert "?" in shortlink.destination_url
    assert "utm_source=twitter" in shortlink.destination_url
    assert shortlink.destination_url.count("?") == 1  # Only one question mark


@pytest.mark.asyncio
async def test_invalid_url_rejection(shortlink_service):
    """Test that invalid URLs are rejected"""
    offer_id = uuid4()

    with pytest.raises(ValueError, match="Invalid destination URL"):
        await shortlink_service.create_shortlink(
            destination_url="not-a-valid-url",
            offer_id=offer_id
        )


@pytest.mark.asyncio
async def test_get_shortlink(shortlink_service):
    """Test retrieving shortlink by code"""
    offer_id = uuid4()

    created = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id
    )

    retrieved = await shortlink_service.get_shortlink(created.short_code)

    assert retrieved is not None
    assert retrieved.short_code == created.short_code
    assert retrieved.destination_url == created.destination_url


@pytest.mark.asyncio
async def test_track_click(shortlink_service):
    """Test click tracking"""
    offer_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id
    )

    # Track first click
    destination = await shortlink_service.track_click(shortlink.short_code)
    assert destination == shortlink.destination_url

    # Check click count updated
    updated = await shortlink_service.get_shortlink(shortlink.short_code)
    assert updated.click_count == 1
    assert updated.last_clicked_at is not None


@pytest.mark.asyncio
async def test_multiple_clicks(shortlink_service):
    """Test multiple click tracking"""
    offer_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id
    )

    # Track 5 clicks
    for i in range(5):
        await shortlink_service.track_click(shortlink.short_code)

    updated = await shortlink_service.get_shortlink(shortlink.short_code)
    assert updated.click_count == 5


@pytest.mark.asyncio
async def test_click_nonexistent_shortlink(shortlink_service):
    """Test clicking a non-existent shortlink"""
    destination = await shortlink_service.track_click("invalid123")
    assert destination is None


@pytest.mark.asyncio
async def test_deactivate_shortlink(shortlink_service):
    """Test deactivating a shortlink"""
    offer_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id
    )

    # Deactivate
    deactivated = await shortlink_service.deactivate_shortlink(shortlink.short_code)
    assert deactivated is True

    # Should not track clicks when inactive
    destination = await shortlink_service.track_click(shortlink.short_code)
    assert destination is None


@pytest.mark.asyncio
async def test_get_shortlink_stats(shortlink_service):
    """Test getting shortlink statistics"""
    offer_id = uuid4()
    template_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id,
        template_id=template_id,
        utm_source="twitter"
    )

    # Track a few clicks
    await shortlink_service.track_click(shortlink.short_code)
    await shortlink_service.track_click(shortlink.short_code)

    stats = await shortlink_service.get_shortlink_stats(shortlink.short_code)

    assert stats is not None
    assert stats["short_code"] == shortlink.short_code
    assert stats["click_count"] == 2
    assert stats["attribution"]["offer_id"] == str(offer_id)
    assert stats["attribution"]["template_id"] == str(template_id)
    assert stats["utm"]["source"] == "twitter"


@pytest.mark.asyncio
async def test_shortlink_expiration(shortlink_service):
    """Test shortlink expiration"""
    offer_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id,
        expires_in_days=30
    )

    assert shortlink.expires_at is not None
    assert shortlink.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_get_full_url(shortlink_service):
    """Test getting full shortlink URL"""
    offer_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id
    )

    full_url = shortlink_service.get_full_url(shortlink.short_code)

    assert full_url.startswith("https://")
    assert shortlink.short_code in full_url


@pytest.mark.asyncio
async def test_all_attribution_ids_encoded(shortlink_service):
    """Test OPS-006 acceptance criterion: All IDs encoded"""
    offer_id = uuid4()
    template_id = uuid4()
    icp_id = uuid4()
    touchpoint_id = uuid4()

    shortlink = await shortlink_service.create_shortlink(
        destination_url="https://example.com/product",
        offer_id=offer_id,
        template_id=template_id,
        icp_id=icp_id,
        touchpoint_id=touchpoint_id
    )

    # Verify all IDs are encoded in the shortlink record
    assert shortlink.offer_id is not None
    assert shortlink.template_id is not None
    assert shortlink.icp_id is not None
    assert shortlink.touchpoint_id is not None

    # Verify stats retrieval includes all IDs
    stats = await shortlink_service.get_shortlink_stats(shortlink.short_code)
    assert stats["attribution"]["offer_id"] is not None
    assert stats["attribution"]["template_id"] is not None
    assert stats["attribution"]["icp_id"] is not None
    assert stats["attribution"]["touchpoint_id"] is not None
