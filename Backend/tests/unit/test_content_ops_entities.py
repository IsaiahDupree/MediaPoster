"""
Content Ops Entities Tests (ENTITY-001, ENTITY-002, ENTITY-003)
=================================================================
Tests for Brand, Offer, and ICP entities with full CRUD operations
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import uuid

from database.models import Brand, Offer, ICP
from database.connection import init_db
import database.connection as db_conn


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Initialize database connection once for all tests"""
    await init_db()
    yield


@pytest_asyncio.fixture
async def db_session():
    """Create a fresh database session for each test"""
    # Import at runtime to get the initialized global
    if db_conn.async_session_maker is None:
        raise RuntimeError("Database not initialized - async_session_maker is None")

    async with db_conn.async_session_maker() as session:
        # Auto-flush so objects get IDs without explicit commit
        session.expire_on_commit = False
        yield session
        # Always rollback to avoid persisting test data
        await session.rollback()


# =====================================================
# BRAND ENTITY TESTS (ENTITY-001)
# =====================================================

@pytest.mark.asyncio
async def test_create_brand(db_session: AsyncSession):
    """Test creating a brand entity"""
    brand = Brand(
        name="Test Brand",
        description="A test brand for unit testing",
        logo_url="https://example.com/logo.png",
        website_url="https://example.com",
        brand_voice={
            "tone": "professional",
            "keywords": ["quality", "innovation", "excellence"],
            "avoid": ["cheap", "low-cost"]
        },
        core_values=["integrity", "customer-first", "innovation"],
        target_audience="B2B SaaS companies",
        is_active=True
    )

    db_session.add(brand)
    await db_session.commit()
    await db_session.refresh(brand)

    # Verify brand was created
    assert brand.id is not None
    assert brand.name == "Test Brand"
    assert brand.is_active is True
    assert brand.brand_voice["tone"] == "professional"
    assert len(brand.core_values) == 3
    assert "innovation" in brand.core_values


@pytest.mark.asyncio
async def test_read_brand(db_session: AsyncSession):
    """Test reading a brand entity"""
    # Create brand
    brand = Brand(name="Read Test Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()
    brand_id = brand.id

    # Read brand
    result = await db_session.execute(select(Brand).where(Brand.id == brand_id))
    retrieved_brand = result.scalar_one_or_none()

    assert retrieved_brand is not None
    assert retrieved_brand.id == brand_id
    assert retrieved_brand.name == "Read Test Brand"


@pytest.mark.asyncio
async def test_update_brand(db_session: AsyncSession):
    """Test updating a brand entity"""
    # Create brand
    brand = Brand(name="Original Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()

    # Update brand
    brand.name = "Updated Brand"
    brand.description = "Updated description"
    brand.is_active = False
    await db_session.commit()
    await db_session.refresh(brand)

    # Verify updates
    assert brand.name == "Updated Brand"
    assert brand.description == "Updated description"
    assert brand.is_active is False


@pytest.mark.asyncio
async def test_delete_brand(db_session: AsyncSession):
    """Test deleting a brand entity"""
    # Create brand
    brand = Brand(name="Delete Test Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()
    brand_id = brand.id

    # Delete brand
    await db_session.delete(brand)
    await db_session.commit()

    # Verify deletion
    result = await db_session.execute(select(Brand).where(Brand.id == brand_id))
    deleted_brand = result.scalar_one_or_none()
    assert deleted_brand is None


@pytest.mark.asyncio
async def test_brand_filter_by_active(db_session: AsyncSession):
    """Test filtering brands by is_active status"""
    # Create active and inactive brands
    active_brand = Brand(name="Active Brand", is_active=True)
    inactive_brand = Brand(name="Inactive Brand", is_active=False)
    db_session.add_all([active_brand, inactive_brand])
    await db_session.commit()

    # Query only active brands
    result = await db_session.execute(
        select(Brand).where(Brand.is_active == True)
    )
    active_brands = result.scalars().all()

    # Verify only active brands returned
    assert len([b for b in active_brands if b.name == "Active Brand"]) == 1
    assert not any(b.name == "Inactive Brand" for b in active_brands)


# =====================================================
# OFFER ENTITY TESTS (ENTITY-002)
# =====================================================

@pytest.mark.asyncio
async def test_create_offer(db_session: AsyncSession):
    """Test creating an offer entity"""
    # Create brand first (required FK)
    brand = Brand(name="Test Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()

    # Create offer
    offer = Offer(
        brand_id=brand.id,
        title="Test Offer",
        description="A test offer",
        offer_type="product",
        landing_page_url="https://example.com/offer",
        cta_text="Get Started Now",
        terms="Terms and conditions apply",
        price=99.99,
        currency="USD",
        priority=10,
        is_active=True
    )

    db_session.add(offer)
    await db_session.commit()
    await db_session.refresh(offer)

    # Verify offer was created
    assert offer.id is not None
    assert offer.brand_id == brand.id
    assert offer.title == "Test Offer"
    assert offer.offer_type == "product"
    assert float(offer.price) == 99.99
    assert offer.priority == 10


@pytest.mark.asyncio
async def test_offer_brand_relationship(db_session: AsyncSession):
    """Test offer-brand relationship"""
    # Create brand and offer
    brand = Brand(name="Relationship Test Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()

    offer = Offer(brand_id=brand.id, title="Test Offer", is_active=True)
    db_session.add(offer)
    await db_session.commit()

    # Verify relationship
    result = await db_session.execute(
        select(Offer).where(Offer.brand_id == brand.id)
    )
    brand_offers = result.scalars().all()

    assert len(brand_offers) > 0
    assert brand_offers[0].brand_id == brand.id


@pytest.mark.asyncio
async def test_offer_cascade_delete(db_session: AsyncSession):
    """Test cascade delete when brand is deleted"""
    # Create brand and offer
    brand = Brand(name="Cascade Test Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()

    offer = Offer(brand_id=brand.id, title="Cascade Test Offer", is_active=True)
    db_session.add(offer)
    await db_session.commit()
    offer_id = offer.id

    # Delete brand (should cascade to offer)
    await db_session.delete(brand)
    await db_session.commit()

    # Verify offer was deleted
    result = await db_session.execute(select(Offer).where(Offer.id == offer_id))
    deleted_offer = result.scalar_one_or_none()
    assert deleted_offer is None


@pytest.mark.asyncio
async def test_offer_filter_by_type(db_session: AsyncSession):
    """Test filtering offers by offer_type"""
    # Create brand
    brand = Brand(name="Filter Test Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()

    # Create offers with different types
    product_offer = Offer(
        brand_id=brand.id,
        title="Product Offer",
        offer_type="product",
        is_active=True
    )
    service_offer = Offer(
        brand_id=brand.id,
        title="Service Offer",
        offer_type="service",
        is_active=True
    )
    db_session.add_all([product_offer, service_offer])
    await db_session.commit()

    # Query only product offers
    result = await db_session.execute(
        select(Offer).where(Offer.offer_type == "product")
    )
    product_offers = result.scalars().all()

    # Verify only product offers returned
    assert len([o for o in product_offers if o.title == "Product Offer"]) == 1
    assert not any(o.title == "Service Offer" for o in product_offers)


# =====================================================
# ICP ENTITY TESTS (ENTITY-003)
# =====================================================

@pytest.mark.asyncio
async def test_create_icp(db_session: AsyncSession):
    """Test creating an ICP entity"""
    icp = ICP(
        name="Startup Founder",
        description="Early-stage startup founders",
        age_range="25-40",
        location=["United States", "Canada", "United Kingdom"],
        job_titles=["CEO", "Founder", "Co-Founder"],
        company_size="1-10",
        pain_points=["Limited budget", "Time constraints", "Scaling challenges"],
        goals=["Grow revenue", "Build team", "Raise funding"],
        interests=["SaaS", "Startups", "Product Management"],
        objections=["Too expensive", "Not enough features", "Complex onboarding"],
        default_awareness_level="problem_aware",
        is_active=True
    )

    db_session.add(icp)
    await db_session.commit()
    await db_session.refresh(icp)

    # Verify ICP was created
    assert icp.id is not None
    assert icp.name == "Startup Founder"
    assert icp.age_range == "25-40"
    assert len(icp.location) == 3
    assert len(icp.pain_points) == 3
    assert icp.default_awareness_level == "problem_aware"


@pytest.mark.asyncio
async def test_read_icp(db_session: AsyncSession):
    """Test reading an ICP entity"""
    # Create ICP
    icp = ICP(name="Enterprise CMO", default_awareness_level="solution_aware", is_active=True)
    db_session.add(icp)
    await db_session.commit()
    icp_id = icp.id

    # Read ICP
    result = await db_session.execute(select(ICP).where(ICP.id == icp_id))
    retrieved_icp = result.scalar_one_or_none()

    assert retrieved_icp is not None
    assert retrieved_icp.id == icp_id
    assert retrieved_icp.name == "Enterprise CMO"


@pytest.mark.asyncio
async def test_update_icp(db_session: AsyncSession):
    """Test updating an ICP entity"""
    # Create ICP
    icp = ICP(name="Original ICP", default_awareness_level="unaware", is_active=True)
    db_session.add(icp)
    await db_session.commit()

    # Update ICP
    icp.name = "Updated ICP"
    icp.default_awareness_level = "most_aware"
    icp.pain_points = ["New pain point"]
    await db_session.commit()
    await db_session.refresh(icp)

    # Verify updates
    assert icp.name == "Updated ICP"
    assert icp.default_awareness_level == "most_aware"
    assert "New pain point" in icp.pain_points


@pytest.mark.asyncio
async def test_delete_icp(db_session: AsyncSession):
    """Test deleting an ICP entity"""
    # Create ICP
    icp = ICP(name="Delete Test ICP", is_active=True)
    db_session.add(icp)
    await db_session.commit()
    icp_id = icp.id

    # Delete ICP
    await db_session.delete(icp)
    await db_session.commit()

    # Verify deletion
    result = await db_session.execute(select(ICP).where(ICP.id == icp_id))
    deleted_icp = result.scalar_one_or_none()
    assert deleted_icp is None


@pytest.mark.asyncio
async def test_icp_filter_by_awareness_level(db_session: AsyncSession):
    """Test filtering ICPs by awareness level"""
    # Create ICPs with different awareness levels
    unaware_icp = ICP(
        name="Unaware ICP",
        default_awareness_level="unaware",
        is_active=True
    )
    problem_aware_icp = ICP(
        name="Problem Aware ICP",
        default_awareness_level="problem_aware",
        is_active=True
    )
    db_session.add_all([unaware_icp, problem_aware_icp])
    await db_session.commit()

    # Query only problem-aware ICPs
    result = await db_session.execute(
        select(ICP).where(ICP.default_awareness_level == "problem_aware")
    )
    problem_aware_icps = result.scalars().all()

    # Verify only problem-aware ICPs returned
    assert len([i for i in problem_aware_icps if i.name == "Problem Aware ICP"]) == 1
    assert not any(i.name == "Unaware ICP" for i in problem_aware_icps)


# =====================================================
# INTEGRATION TESTS
# =====================================================

@pytest.mark.asyncio
async def test_brand_offer_icp_full_chain(db_session: AsyncSession):
    """Test full entity chain: Brand → Offer → ICP"""
    # Create brand
    brand = Brand(name="Full Chain Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()

    # Create offer linked to brand
    offer = Offer(
        brand_id=brand.id,
        title="Full Chain Offer",
        offer_type="product",
        is_active=True
    )
    db_session.add(offer)
    await db_session.commit()

    # Create ICP
    icp = ICP(
        name="Full Chain ICP",
        default_awareness_level="solution_aware",
        is_active=True
    )
    db_session.add(icp)
    await db_session.commit()

    # Verify all entities exist
    assert brand.id is not None
    assert offer.id is not None
    assert offer.brand_id == brand.id
    assert icp.id is not None


@pytest.mark.asyncio
async def test_multiple_offers_per_brand(db_session: AsyncSession):
    """Test that a brand can have multiple offers"""
    # Create brand
    brand = Brand(name="Multi-Offer Brand", is_active=True)
    db_session.add(brand)
    await db_session.commit()

    # Create multiple offers
    offer1 = Offer(brand_id=brand.id, title="Offer 1", is_active=True)
    offer2 = Offer(brand_id=brand.id, title="Offer 2", is_active=True)
    offer3 = Offer(brand_id=brand.id, title="Offer 3", is_active=True)
    db_session.add_all([offer1, offer2, offer3])
    await db_session.commit()

    # Query all offers for brand
    result = await db_session.execute(
        select(Offer).where(Offer.brand_id == brand.id)
    )
    brand_offers = result.scalars().all()

    # Verify 3 offers exist
    assert len(brand_offers) == 3
