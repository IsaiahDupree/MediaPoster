"""
E2E Test: Cross-Platform Publishing (TEST-012)

This test verifies content can be generated once and adapted for multiple platforms:
1. Generate base content from a template
2. Adapt content for each platform (X, Instagram, TikTok, LinkedIn)
3. Verify platform-specific constraints (character limits, format requirements)
4. Publish to multiple platforms
5. Track separate touchpoints for each platform
6. Collect metrics independently per platform

Platform Specifications:
- X (Twitter): 280 characters max, supports threads
- Instagram: Caption up to 2,200 characters, requires visual media
- TikTok: Caption up to 2,200 characters, video required
- LinkedIn: 3,000 characters max, professional tone
- Threads: 500 characters max, similar to X
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from loguru import logger

from database.connection import get_db_session_factory, init_db
from database.models import (
    Brand, Offer, ICP, ContentTemplate, Touchpoint, PromptRun, PlatformPost
)


# Platform specifications
PLATFORM_SPECS = {
    "x": {
        "max_length": 280,
        "supports_threads": True,
        "requires_media": False,
        "tone": "casual"
    },
    "instagram": {
        "max_length": 2200,
        "supports_threads": False,
        "requires_media": True,
        "tone": "visual"
    },
    "tiktok": {
        "max_length": 2200,
        "supports_threads": False,
        "requires_media": True,
        "tone": "energetic"
    },
    "linkedin": {
        "max_length": 3000,
        "supports_threads": False,
        "requires_media": False,
        "tone": "professional"
    },
    "threads": {
        "max_length": 500,
        "supports_threads": True,
        "requires_media": False,
        "tone": "casual"
    }
}


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create database session for testing"""
    # Initialize database connection
    await init_db()

    session_factory = get_db_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture(scope="function")
async def test_brand(db_session):
    """Create test brand"""
    brand = Brand(
        id=uuid.uuid4(),
        name="MultiPlatform Test Brand",
        description="Test brand for cross-platform publishing",
        brand_voice={"tone": "adaptable", "keywords": ["innovation", "growth"], "avoid": []},
        core_values=["flexibility", "innovation"],
        target_audience="Multi-platform content creators"
    )
    db_session.add(brand)
    await db_session.commit()
    await db_session.refresh(brand)
    return brand


@pytest_asyncio.fixture(scope="function")
async def test_offer(db_session, test_brand):
    """Create test offer"""
    offer = Offer(
        id=uuid.uuid4(),
        brand_id=test_brand.id,
        name="Cross-Platform Product",
        promise="Works everywhere you need it",
        landing_url="https://test.com/product",
        cta_text="Learn more",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(offer)
    await db_session.commit()
    await db_session.refresh(offer)
    return offer


@pytest_asyncio.fixture(scope="function")
async def test_icp(db_session, test_offer):
    """Create test ICP"""
    icp = ICP(
        id=uuid.uuid4(),
        offer_id=test_offer.id,
        name="Multi-Platform Users",
        pains=["scattered content", "manual posting", "inconsistent messaging"],
        desired_outcomes=["unified content", "automated publishing", "consistent brand"],
        demographics={"role": "content manager", "company_size": "10-50"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(icp)
    await db_session.commit()
    await db_session.refresh(icp)
    return icp


@pytest_asyncio.fixture(scope="function")
async def test_template(db_session, test_brand):
    """Create test template for multi-platform content"""
    template = ContentTemplate(
        id=uuid.uuid4(),
        brand_id=test_brand.id,
        name="Multi-Platform Template",
        awareness_level="solution_aware",
        fate_weights={"F": 0.30, "A": 0.30, "T": 0.20, "E": 0.20},
        prompt_text="""Write a solution-aware post about {product} for {platform}.

Core message: {core_message}

Platform: {platform}
Max length: {max_length} characters
Tone: {tone}

Include:
- Problem statement
- Solution overview
- {cta_text}: {landing_url}

Adapt the tone and format for {platform}.""",
        variable_schema={
            "product": "string",
            "platform": "string",
            "core_message": "string",
            "max_length": "number",
            "tone": "string",
            "cta_text": "string",
            "landing_url": "string"
        },
        cta_strength="soft",
        performance_label="neutral",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


class TestCrossPlatform:
    """E2E test suite for cross-platform publishing"""

    @pytest.mark.asyncio
    async def test_01_generate_base_content(self, db_session, test_template, test_offer, test_icp):
        """
        Step 1: Generate base content with core message

        This creates a platform-agnostic version that will be adapted
        """
        logger.info("📝 Step 1: Generating base content")

        core_message = "Manual content distribution is draining your time. Our tool publishes to all platforms in one click."

        # Store base content for adaptation
        self.base_content = {
            "core_message": core_message,
            "product": test_offer.name,
            "cta_text": test_offer.cta_text,
            "landing_url": test_offer.landing_url
        }

        logger.success(f"✅ Base content prepared: {core_message[:50]}...")

    @pytest.mark.asyncio
    async def test_02_adapt_for_x_twitter(self, db_session, test_template, test_offer, test_icp):
        """
        Step 2a: Adapt content for X (Twitter)

        Constraints:
        - 280 characters max
        - Casual tone
        - Can use threads if needed
        """
        logger.info("🐦 Step 2a: Adapting for X (Twitter)")

        platform = "x"
        specs = PLATFORM_SPECS[platform]

        # Prepare variables
        variables = {
            **self.base_content,
            "platform": platform,
            "max_length": specs["max_length"],
            "tone": specs["tone"]
        }

        # Create PromptRun
        prompt_run = PromptRun(
            id=uuid.uuid4(),
            template_id=test_template.id,
            offer_id=test_offer.id,
            icp_id=test_icp.id,
            prompt_text=test_template.prompt_text,
            variables=variables,
            model="gpt-4o-mini",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(prompt_run)
        await db_session.commit()
        await db_session.refresh(prompt_run)

        # Mock adapted content (in production, would call OpenAI)
        adapted_text = f"Tired of manual posting?\n\n{self.base_content['core_message'][:150]}\n\n{self.base_content['cta_text']}: {self.base_content['landing_url']}"

        # Trim to 280 chars if needed
        if len(adapted_text) > 280:
            adapted_text = adapted_text[:270] + "..."

        prompt_run.response_text = adapted_text
        prompt_run.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Create Post
        post = PlatformPost(
            id=uuid.uuid4(),
            prompt_run_id=prompt_run.id,
            text=adapted_text,
            platform=platform,
            status="published",
            published_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        # Create Touchpoint
        touchpoint = Touchpoint(
            id=uuid.uuid4(),
            prompt_run_id=prompt_run.id,
            offer_id=test_offer.id,
            platform=platform,
            platform_object_id=f"x_post_{uuid.uuid4()}",
            touchpoint_type="post",
            awareness_level="solution_aware",
            published_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(touchpoint)
        await db_session.commit()
        await db_session.refresh(touchpoint)

        # Verify constraints
        assert len(adapted_text) <= 280, f"X post exceeds 280 chars: {len(adapted_text)}"
        assert post.platform == "x"
        assert touchpoint.platform == "x"

        logger.info(f"X Content ({len(adapted_text)} chars): {adapted_text[:100]}...")
        logger.success(f"✅ Published to X (Touchpoint: {touchpoint.id})")

        # Store for comparison
        if not hasattr(self, 'touchpoints'):
            self.touchpoints = {}
        self.touchpoints['x'] = touchpoint

    @pytest.mark.asyncio
    async def test_03_adapt_for_instagram(self, db_session, test_template, test_offer, test_icp):
        """
        Step 2b: Adapt content for Instagram

        Constraints:
        - 2,200 characters max
        - Visual/lifestyle tone
        - Requires media
        """
        logger.info("📸 Step 2b: Adapting for Instagram")

        platform = "instagram"
        specs = PLATFORM_SPECS[platform]

        variables = {
            **self.base_content,
            "platform": platform,
            "max_length": specs["max_length"],
            "tone": specs["tone"]
        }

        # Create PromptRun
        prompt_run = PromptRun(
            id=uuid.uuid4(),
            template_id=test_template.id,
            offer_id=test_offer.id,
            icp_id=test_icp.id,
            prompt_text=test_template.prompt_text,
            variables=variables,
            model="gpt-4o-mini",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(prompt_run)
        await db_session.commit()
        await db_session.refresh(prompt_run)

        # Mock adapted content (longer, more visual)
        adapted_text = f"""✨ {self.base_content['core_message']}

Are you still copying and pasting to every platform? 😓

There's a better way. 💡

With {self.base_content['product']}, you can:
• Create once
• Publish everywhere
• Save hours every week

Stop the manual grind. ⚡

{self.base_content['cta_text']}: {self.base_content['landing_url']}

#ContentCreator #Automation #ProductivityHacks"""

        assert len(adapted_text) <= 2200

        prompt_run.response_text = adapted_text
        prompt_run.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Create Post
        post = PlatformPost(
            id=uuid.uuid4(),
            prompt_run_id=prompt_run.id,
            text=adapted_text,
            platform=platform,
            status="published",
            media_attachments=["https://placeholder.com/image.jpg"],  # Mock media
            published_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        # Create Touchpoint
        touchpoint = Touchpoint(
            id=uuid.uuid4(),
            prompt_run_id=prompt_run.id,
            offer_id=test_offer.id,
            platform=platform,
            platform_object_id=f"ig_post_{uuid.uuid4()}",
            touchpoint_type="post",
            awareness_level="solution_aware",
            published_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(touchpoint)
        await db_session.commit()
        await db_session.refresh(touchpoint)

        # Verify constraints
        assert len(adapted_text) <= 2200
        assert post.platform == "instagram"
        assert post.media_attachments is not None and len(post.media_attachments) > 0

        logger.info(f"Instagram Content ({len(adapted_text)} chars): {adapted_text[:100]}...")
        logger.success(f"✅ Published to Instagram (Touchpoint: {touchpoint.id})")

        self.touchpoints['instagram'] = touchpoint

    @pytest.mark.asyncio
    async def test_04_adapt_for_linkedin(self, db_session, test_template, test_offer, test_icp):
        """
        Step 2c: Adapt content for LinkedIn

        Constraints:
        - 3,000 characters max
        - Professional tone
        - More detailed, business-focused
        """
        logger.info("💼 Step 2c: Adapting for LinkedIn")

        platform = "linkedin"
        specs = PLATFORM_SPECS[platform]

        variables = {
            **self.base_content,
            "platform": platform,
            "max_length": specs["max_length"],
            "tone": specs["tone"]
        }

        # Create PromptRun
        prompt_run = PromptRun(
            id=uuid.uuid4(),
            template_id=test_template.id,
            offer_id=test_offer.id,
            icp_id=test_icp.id,
            prompt_text=test_template.prompt_text,
            variables=variables,
            model="gpt-4o-mini",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(prompt_run)
        await db_session.commit()
        await db_session.refresh(prompt_run)

        # Mock adapted content (professional, detailed)
        adapted_text = f"""The Hidden Cost of Manual Content Distribution

{self.base_content['core_message']}

As content managers, we understand the challenge: creating quality content is hard enough. But then you have to:

→ Reformat for each platform
→ Manually post to 5+ channels
→ Track engagement separately
→ Repeat this process daily

The average content manager spends 10+ hours per week just on distribution.

That's 520 hours per year. Over 13 weeks of full-time work.

There's a better approach.

{self.base_content['product']} enables content teams to:

• Create once, publish everywhere
• Maintain brand consistency across platforms
• Schedule and automate distribution
• Track unified analytics

This isn't about shortcuts. It's about focusing your time on what matters: creating great content.

{self.base_content['cta_text']}: {self.base_content['landing_url']}

#ContentStrategy #MarketingAutomation #Productivity"""

        assert len(adapted_text) <= 3000

        prompt_run.response_text = adapted_text
        prompt_run.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Create Post
        post = PlatformPost(
            id=uuid.uuid4(),
            prompt_run_id=prompt_run.id,
            text=adapted_text,
            platform=platform,
            status="published",
            published_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        # Create Touchpoint
        touchpoint = Touchpoint(
            id=uuid.uuid4(),
            prompt_run_id=prompt_run.id,
            offer_id=test_offer.id,
            platform=platform,
            platform_object_id=f"li_post_{uuid.uuid4()}",
            touchpoint_type="post",
            awareness_level="solution_aware",
            published_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(touchpoint)
        await db_session.commit()
        await db_session.refresh(touchpoint)

        # Verify constraints
        assert len(adapted_text) <= 3000
        assert post.platform == "linkedin"

        logger.info(f"LinkedIn Content ({len(adapted_text)} chars): {adapted_text[:100]}...")
        logger.success(f"✅ Published to LinkedIn (Touchpoint: {touchpoint.id})")

        self.touchpoints['linkedin'] = touchpoint

    @pytest.mark.asyncio
    async def test_05_adapt_for_threads(self, db_session, test_template, test_offer, test_icp):
        """
        Step 2d: Adapt content for Threads

        Constraints:
        - 500 characters max
        - Casual tone (similar to X)
        """
        logger.info("🧵 Step 2d: Adapting for Threads")

        platform = "threads"
        specs = PLATFORM_SPECS[platform]

        variables = {
            **self.base_content,
            "platform": platform,
            "max_length": specs["max_length"],
            "tone": specs["tone"]
        }

        # Create PromptRun
        prompt_run = PromptRun(
            id=uuid.uuid4(),
            template_id=test_template.id,
            offer_id=test_offer.id,
            icp_id=test_icp.id,
            prompt_text=test_template.prompt_text,
            variables=variables,
            model="gpt-4o-mini",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(prompt_run)
        await db_session.commit()
        await db_session.refresh(prompt_run)

        # Mock adapted content
        adapted_text = f"""Still manually posting to every platform?

{self.base_content['core_message'][:200]}

Automate it. Save 10+ hours/week.

{self.base_content['cta_text']}: {self.base_content['landing_url']}"""

        if len(adapted_text) > 500:
            adapted_text = adapted_text[:490] + "..."

        prompt_run.response_text = adapted_text
        prompt_run.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Create Post
        post = PlatformPost(
            id=uuid.uuid4(),
            prompt_run_id=prompt_run.id,
            text=adapted_text,
            platform=platform,
            status="published",
            published_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        # Create Touchpoint
        touchpoint = Touchpoint(
            id=uuid.uuid4(),
            prompt_run_id=prompt_run.id,
            offer_id=test_offer.id,
            platform=platform,
            platform_object_id=f"threads_post_{uuid.uuid4()}",
            touchpoint_type="post",
            awareness_level="solution_aware",
            published_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(touchpoint)
        await db_session.commit()
        await db_session.refresh(touchpoint)

        # Verify constraints
        assert len(adapted_text) <= 500
        assert post.platform == "threads"

        logger.info(f"Threads Content ({len(adapted_text)} chars): {adapted_text[:100]}...")
        logger.success(f"✅ Published to Threads (Touchpoint: {touchpoint.id})")

        self.touchpoints['threads'] = touchpoint

    @pytest.mark.asyncio
    async def test_06_verify_separate_attribution(self, db_session, test_offer):
        """
        Step 3: Verify each platform has separate touchpoint for attribution
        """
        logger.info("🔗 Step 3: Verifying separate attribution chains")

        platforms = ['x', 'instagram', 'linkedin', 'threads']

        for platform in platforms:
            touchpoint = self.touchpoints.get(platform)
            assert touchpoint is not None, f"Missing touchpoint for {platform}"
            assert touchpoint.platform == platform
            assert touchpoint.offer_id == test_offer.id
            assert touchpoint.platform_object_id.startswith(platform.replace('x', 'x_'))

            logger.info(f"  {platform}: Touchpoint {touchpoint.id}")

        logger.success(f"✅ All {len(platforms)} platforms have separate touchpoints")

    @pytest.mark.asyncio
    async def test_07_compare_adaptations(self, db_session):
        """
        Step 4: Compare content adaptations across platforms
        """
        logger.info("📊 Step 4: Comparing platform adaptations")

        # Fetch all posts
        posts_by_platform = {}

        for platform, touchpoint in self.touchpoints.items():
            # Query post by prompt_run_id
            result = await db_session.execute(
                select(PlatformPost).where(PlatformPost.prompt_run_id == touchpoint.prompt_run_id)
            )
            post = result.scalar_one_or_none()

            if post:
                posts_by_platform[platform] = {
                    "text": post.text,
                    "length": len(post.text),
                    "has_media": bool(post.media_attachments)
                }

        # Compare
        logger.info("\n📏 Platform Comparison:")
        for platform, data in posts_by_platform.items():
            logger.info(f"  {platform.upper()}: {data['length']} chars, Media: {data['has_media']}")

        # Verify all contain core message elements
        for platform, data in posts_by_platform.items():
            # Check for key concepts (platform may vary wording)
            text_lower = data["text"].lower()
            assert any(keyword in text_lower for keyword in ["manual", "publish", "platform"]), \
                f"{platform} missing core message"

        logger.success("✅ All adaptations contain core message")

    @pytest.mark.asyncio
    async def test_08_cleanup(self, db_session, test_brand, test_offer, test_icp, test_template):
        """
        Cleanup: Remove test data
        """
        logger.info("🧹 Cleanup: Removing test data")

        try:
            # Delete touchpoints
            for platform, touchpoint in self.touchpoints.items():
                db_session.delete(touchpoint)

            # Delete posts
            for platform, touchpoint in self.touchpoints.items():
                result = await db_session.execute(
                    select(PlatformPost).where(PlatformPost.prompt_run_id == touchpoint.prompt_run_id)
                )
                post = result.scalar_one_or_none()
                if post:
                    db_session.delete(post)

            # Delete prompt runs
            for platform, touchpoint in self.touchpoints.items():
                result = await db_session.execute(
                    select(PromptRun).where(PromptRun.id == touchpoint.prompt_run_id)
                )
                prompt_run = result.scalar_one_or_none()
                if prompt_run:
                    db_session.delete(prompt_run)

            # Delete template
            db_session.delete(test_template)

            # Delete ICP
            db_session.delete(test_icp)

            # Delete offer
            db_session.delete(test_offer)

            # Delete brand
            db_session.delete(test_brand)

            await db_session.commit()

            logger.success("✅ Test data cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            await db_session.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
