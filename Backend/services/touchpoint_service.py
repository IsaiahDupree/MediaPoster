"""
Touchpoint Attribution Service (OPS-011)
=========================================
Ensures every touchpoint traces to prompt/template/offer/ICP.
No orphaned touchpoints allowed.

Touchpoint Attribution Chain:
    Touchpoint → Template → Offer → ICP → Brand

Features:
- Create touchpoints with full attribution
- Validate attribution chain completeness
- Update metrics from posted content
- Query touchpoints by attribution chain
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from loguru import logger
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Touchpoint, Offer, ICP, ContentTemplate, PostedContent
from database.connection import async_session_maker
from services.event_bus import EventBus, Topics


class TouchpointAttributionError(Exception):
    """Raised when touchpoint attribution chain is incomplete"""
    pass


class TouchpointService:
    """
    Touchpoint Attribution Service

    Manages touchpoint creation with full attribution chain validation.
    Ensures every touchpoint can be traced back through:
    Template → Offer → ICP → Brand

    Usage:
        service = TouchpointService.get_instance()

        touchpoint = await service.create_touchpoint(
            channel="twitter",
            message_type="post",
            offer_id=offer_id,
            icp_id=icp_id,
            template_id=template_id,
            posted_content_id=posted_content_id,
            shortlink="https://link.co/abc123"
        )
    """

    _instance: Optional["TouchpointService"] = None

    def __init__(self):
        """Initialize touchpoint service"""
        if TouchpointService._instance is not None:
            raise RuntimeError("Use TouchpointService.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("touchpoint-service")

        # Metrics
        self.touchpoints_created = 0
        self.orphaned_detected = 0
        self.attribution_failures = 0

        logger.info("🔗 Touchpoint Attribution Service initialized")

    @classmethod
    def get_instance(cls) -> "TouchpointService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def create_touchpoint(
        self,
        channel: str,
        message_type: str,
        offer_id: UUID,
        icp_id: Optional[UUID] = None,
        template_id: Optional[UUID] = None,
        brand_id: Optional[UUID] = None,
        posted_content_id: Optional[UUID] = None,
        shortlink: Optional[str] = None,
        published_at: Optional[datetime] = None
    ) -> Touchpoint:
        """
        Create touchpoint with full attribution chain validation

        Args:
            channel: Channel name (twitter, instagram, etc.)
            message_type: Type of message (post, comment, dm, etc.)
            offer_id: Required - which offer is this promoting
            icp_id: Optional - which ICP is this targeting
            template_id: Optional - which template generated this
            brand_id: Optional - which brand this belongs to
            posted_content_id: Optional - link to posted content record
            shortlink: Optional - attribution shortlink
            published_at: Optional - when it was published

        Returns:
            Created Touchpoint object

        Raises:
            TouchpointAttributionError: If attribution chain is incomplete or invalid
        """
        # Validate attribution chain
        await self._validate_attribution_chain(
            offer_id=offer_id,
            icp_id=icp_id,
            template_id=template_id,
            brand_id=brand_id
        )

        async with async_session_maker() as session:
            # Create touchpoint
            touchpoint = Touchpoint(
                id=uuid4(),
                channel=channel,
                message_type=message_type,
                offer_id=offer_id,
                icp_id=icp_id,
                template_id=template_id,
                brand_id=brand_id,
                posted_content_id=posted_content_id,
                shortlink=shortlink,
                published_at=published_at or datetime.now(timezone.utc)
            )

            session.add(touchpoint)
            await session.commit()
            await session.refresh(touchpoint)

            self.touchpoints_created += 1

            logger.info(
                f"✓ Touchpoint created | Channel: {channel} | "
                f"Type: {message_type} | Offer: {offer_id}"
            )

            # Emit event
            await self.event_bus.publish(
                Topics.TOUCHPOINT_CREATED,
                {
                    "touchpoint_id": str(touchpoint.id),
                    "channel": channel,
                    "message_type": message_type,
                    "offer_id": str(offer_id),
                    "icp_id": str(icp_id) if icp_id else None,
                    "template_id": str(template_id) if template_id else None,
                    "published_at": touchpoint.published_at.isoformat()
                }
            )

            return touchpoint

    async def _validate_attribution_chain(
        self,
        offer_id: UUID,
        icp_id: Optional[UUID],
        template_id: Optional[UUID],
        brand_id: Optional[UUID]
    ) -> None:
        """
        Validate that attribution chain is complete and valid

        Checks:
        1. Offer exists
        2. If ICP provided, it exists and matches offer's brand
        3. If template provided, it exists
        4. If brand provided, it matches offer's brand

        Args:
            offer_id: Offer ID (required)
            icp_id: ICP ID (optional)
            template_id: Template ID (optional)
            brand_id: Brand ID (optional)

        Raises:
            TouchpointAttributionError: If chain is incomplete or invalid
        """
        async with async_session_maker() as session:
            # 1. Validate offer exists
            offer = await session.get(Offer, offer_id)
            if not offer:
                self.attribution_failures += 1
                raise TouchpointAttributionError(f"Offer not found: {offer_id}")

            # 2. Validate ICP if provided
            if icp_id:
                icp = await session.get(ICP, icp_id)
                if not icp:
                    self.attribution_failures += 1
                    raise TouchpointAttributionError(f"ICP not found: {icp_id}")

                # Check ICP's brand matches offer's brand
                if icp.brand_id != offer.brand_id:
                    self.attribution_failures += 1
                    raise TouchpointAttributionError(
                        f"ICP brand ({icp.brand_id}) doesn't match "
                        f"Offer brand ({offer.brand_id})"
                    )

            # 3. Validate template if provided
            if template_id:
                template = await session.get(ContentTemplate, template_id)
                if not template:
                    self.attribution_failures += 1
                    raise TouchpointAttributionError(
                        f"Template not found: {template_id}"
                    )

            # 4. Validate brand if provided
            if brand_id and brand_id != offer.brand_id:
                self.attribution_failures += 1
                raise TouchpointAttributionError(
                    f"Brand ({brand_id}) doesn't match Offer brand ({offer.brand_id})"
                )

    async def update_touchpoint_metrics(
        self,
        touchpoint_id: UUID,
        impressions: Optional[int] = None,
        clicks: Optional[int] = None,
        likes: Optional[int] = None,
        replies: Optional[int] = None,
        reposts: Optional[int] = None
    ) -> Touchpoint:
        """
        Update touchpoint metrics from posted content checkbacks

        Args:
            touchpoint_id: Touchpoint ID
            impressions: Impression count
            clicks: Click count
            likes: Like count
            replies: Reply count
            reposts: Repost count

        Returns:
            Updated Touchpoint
        """
        async with async_session_maker() as session:
            touchpoint = await session.get(Touchpoint, touchpoint_id)
            if not touchpoint:
                raise TouchpointAttributionError(
                    f"Touchpoint not found: {touchpoint_id}"
                )

            # Update metrics
            if impressions is not None:
                touchpoint.impressions = impressions
            if clicks is not None:
                touchpoint.clicks = clicks
            if likes is not None:
                touchpoint.likes = likes
            if replies is not None:
                touchpoint.replies = replies
            if reposts is not None:
                touchpoint.reposts = reposts

            # Calculate rates
            if touchpoint.impressions > 0:
                touchpoint.engagement_rate = (
                    (touchpoint.likes + touchpoint.replies + touchpoint.reposts) /
                    touchpoint.impressions
                )
                touchpoint.click_rate = touchpoint.clicks / touchpoint.impressions

                # Reward score (same as OPS-005)
                like_rate = touchpoint.likes / touchpoint.impressions
                reply_rate = touchpoint.replies / touchpoint.impressions
                repost_rate = touchpoint.reposts / touchpoint.impressions
                click_rate = touchpoint.click_rate

                # Weighted reward function
                touchpoint.reward_score = (
                    1.0 * click_rate +
                    0.8 * reply_rate +
                    0.6 * repost_rate +
                    0.4 * like_rate
                )

            await session.commit()
            await session.refresh(touchpoint)

            logger.debug(
                f"Updated touchpoint metrics | ID: {touchpoint_id} | "
                f"Impressions: {touchpoint.impressions} | "
                f"Engagement: {touchpoint.engagement_rate:.3f}"
            )

            return touchpoint

    async def sync_metrics_from_posted_content(
        self,
        posted_content_id: UUID
    ) -> List[Touchpoint]:
        """
        Sync metrics from posted content to all linked touchpoints

        Args:
            posted_content_id: Posted content ID

        Returns:
            List of updated touchpoints
        """
        async with async_session_maker() as session:
            # Get posted content
            posted_content = await session.get(PostedContent, posted_content_id)
            if not posted_content:
                logger.warning(f"Posted content not found: {posted_content_id}")
                return []

            # Find all touchpoints linked to this posted content
            result = await session.execute(
                select(Touchpoint).where(
                    Touchpoint.posted_content_id == posted_content_id
                )
            )
            touchpoints = result.scalars().all()

            if not touchpoints:
                logger.debug(f"No touchpoints found for posted content: {posted_content_id}")
                return []

            # Update each touchpoint's metrics
            updated = []
            for touchpoint in touchpoints:
                await self.update_touchpoint_metrics(
                    touchpoint_id=touchpoint.id,
                    impressions=posted_content.impressions,
                    clicks=posted_content.clicks,
                    likes=posted_content.likes,
                    replies=posted_content.replies,
                    reposts=posted_content.reposts
                )
                updated.append(touchpoint)

            logger.info(
                f"✓ Synced metrics to {len(updated)} touchpoint(s) from "
                f"posted content {posted_content_id}"
            )

            return updated

    async def get_touchpoints_by_offer(
        self,
        offer_id: UUID,
        limit: int = 100
    ) -> List[Touchpoint]:
        """Get all touchpoints for an offer"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Touchpoint)
                .where(Touchpoint.offer_id == offer_id)
                .order_by(desc(Touchpoint.published_at))
                .limit(limit)
            )
            return result.scalars().all()

    async def get_touchpoints_by_template(
        self,
        template_id: UUID,
        limit: int = 100
    ) -> List[Touchpoint]:
        """Get all touchpoints for a template"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Touchpoint)
                .where(Touchpoint.template_id == template_id)
                .order_by(desc(Touchpoint.published_at))
                .limit(limit)
            )
            return result.scalars().all()

    async def get_touchpoints_by_icp(
        self,
        icp_id: UUID,
        limit: int = 100
    ) -> List[Touchpoint]:
        """Get all touchpoints for an ICP"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Touchpoint)
                .where(Touchpoint.icp_id == icp_id)
                .order_by(desc(Touchpoint.published_at))
                .limit(limit)
            )
            return result.scalars().all()

    async def detect_orphaned_touchpoints(self) -> List[Touchpoint]:
        """
        Detect orphaned touchpoints (missing attribution chain)

        Returns:
            List of touchpoints with incomplete attribution
        """
        async with async_session_maker() as session:
            # Find touchpoints with missing offer (should never happen)
            result = await session.execute(
                select(Touchpoint)
                .where(Touchpoint.offer_id.is_(None))
            )
            orphaned = result.scalars().all()

            if orphaned:
                self.orphaned_detected = len(orphaned)
                logger.error(
                    f"🚨 Found {len(orphaned)} orphaned touchpoint(s) "
                    f"with missing offer_id"
                )

            return orphaned

    def get_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        return {
            "touchpoints_created": self.touchpoints_created,
            "orphaned_detected": self.orphaned_detected,
            "attribution_failures": self.attribution_failures,
            "health": "healthy" if self.orphaned_detected == 0 else "degraded"
        }
