"""
Shortlink Attribution Service (OPS-006)
========================================
Creates shortlinks with full attribution chain encoding:
- Touchpoint ID
- Offer ID
- Template ID
- ICP ID

Generates UTM-formatted links for tracking content performance across
the Brand → Offer → ICP → Template traceback chain.

Acceptance Criteria:
- All attribution IDs encoded in shortlink
- UTM format validation
- Click tracking
"""

import secrets
import string
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse, parse_qs
from loguru import logger

from database.models import Shortlink, Touchpoint, Offer, ContentTemplate, ICP
from database.connection import async_session_maker
from sqlalchemy import select


class ShortlinkService:
    """
    Service for creating and managing attribution shortlinks

    Usage:
        service = ShortlinkService.get_instance()

        shortlink = await service.create_shortlink(
            destination_url="https://example.com/product",
            offer_id=offer_uuid,
            touchpoint_id=touchpoint_uuid,
            template_id=template_uuid,
            icp_id=icp_uuid,
            utm_source="twitter",
            utm_campaign="spring_launch"
        )

        # shortlink.short_code = "aB3xY9"
        # Full URL: https://yourdomain.com/l/aB3xY9
    """

    _instance: Optional["ShortlinkService"] = None

    def __init__(self):
        """Initialize shortlink service"""
        if ShortlinkService._instance is not None:
            raise RuntimeError("Use ShortlinkService.get_instance()")

        self.base_url = "https://mediaposter.app/l"  # TODO: Configure from settings
        self._code_length = 8
        self._code_chars = string.ascii_letters + string.digits

        logger.info("🔗 Shortlink Attribution Service initialized")

    @classmethod
    def get_instance(cls) -> "ShortlinkService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _generate_short_code(self) -> str:
        """Generate a unique short code"""
        return ''.join(
            secrets.choice(self._code_chars)
            for _ in range(self._code_length)
        )

    def _validate_url(self, url: str) -> bool:
        """Validate destination URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _build_utm_url(
        self,
        destination_url: str,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        utm_term: Optional[str] = None
    ) -> str:
        """Build URL with UTM parameters"""
        utm_params = {}

        if utm_source:
            utm_params['utm_source'] = utm_source
        if utm_medium:
            utm_params['utm_medium'] = utm_medium
        if utm_campaign:
            utm_params['utm_campaign'] = utm_campaign
        if utm_content:
            utm_params['utm_content'] = utm_content
        if utm_term:
            utm_params['utm_term'] = utm_term

        if utm_params:
            # Check if URL already has query params
            separator = '&' if '?' in destination_url else '?'
            return f"{destination_url}{separator}{urlencode(utm_params)}"

        return destination_url

    async def create_shortlink(
        self,
        destination_url: str,
        offer_id: UUID,
        touchpoint_id: Optional[UUID] = None,
        template_id: Optional[UUID] = None,
        icp_id: Optional[UUID] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        utm_term: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> Shortlink:
        """
        Create a shortlink with full attribution

        Args:
            destination_url: Target URL
            offer_id: Offer UUID (required)
            touchpoint_id: Touchpoint UUID (optional)
            template_id: Template UUID (optional)
            icp_id: ICP UUID (optional)
            utm_source: UTM source tag
            utm_medium: UTM medium tag
            utm_campaign: UTM campaign tag
            utm_content: UTM content tag
            utm_term: UTM term tag
            expires_in_days: Expiration days (optional)

        Returns:
            Shortlink object

        Raises:
            ValueError: If URL is invalid
        """
        # Validate destination URL
        if not self._validate_url(destination_url):
            raise ValueError(f"Invalid destination URL: {destination_url}")

        # Build UTM-enhanced destination URL
        final_destination = self._build_utm_url(
            destination_url,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term
        )

        # Generate unique short code
        short_code = self._generate_short_code()

        # Ensure uniqueness (retry if collision)
        async with async_session_maker() as db:
            max_retries = 5
            for attempt in range(max_retries):
                result = await db.execute(
                    select(Shortlink).where(Shortlink.short_code == short_code)
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    break

                short_code = self._generate_short_code()

                if attempt == max_retries - 1:
                    raise RuntimeError("Failed to generate unique short code")

            # Calculate expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

            # Create shortlink record
            shortlink = Shortlink(
                short_code=short_code,
                destination_url=final_destination,
                touchpoint_id=touchpoint_id,
                offer_id=offer_id,
                template_id=template_id,
                icp_id=icp_id,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
                utm_term=utm_term,
                expires_at=expires_at,
                is_active=True,
                click_count=0
            )

            db.add(shortlink)
            await db.commit()
            await db.refresh(shortlink)

            logger.info(
                f"🔗 Shortlink created | Code: {short_code} | "
                f"Offer: {offer_id} | Template: {template_id} | ICP: {icp_id}"
            )

            return shortlink

    async def get_shortlink(self, short_code: str) -> Optional[Shortlink]:
        """Get shortlink by code"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(Shortlink).where(
                    Shortlink.short_code == short_code,
                    Shortlink.is_active == True
                )
            )
            return result.scalar_one_or_none()

    async def track_click(self, short_code: str) -> Optional[str]:
        """
        Track a click and return destination URL

        Args:
            short_code: Short code to resolve

        Returns:
            Destination URL if found and active, None otherwise
        """
        async with async_session_maker() as db:
            result = await db.execute(
                select(Shortlink).where(Shortlink.short_code == short_code)
            )
            shortlink = result.scalar_one_or_none()

            if not shortlink:
                logger.warning(f"Shortlink not found: {short_code}")
                return None

            # Check if expired
            if shortlink.expires_at and shortlink.expires_at < datetime.now(timezone.utc):
                logger.warning(f"Shortlink expired: {short_code}")
                return None

            # Check if active
            if not shortlink.is_active:
                logger.warning(f"Shortlink inactive: {short_code}")
                return None

            # Increment click count
            shortlink.click_count += 1
            shortlink.last_clicked_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"🔗 Click tracked | Code: {short_code} | Count: {shortlink.click_count}")

            return shortlink.destination_url

    async def get_shortlink_stats(self, short_code: str) -> Optional[Dict[str, Any]]:
        """Get click statistics for a shortlink"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(Shortlink).where(Shortlink.short_code == short_code)
            )
            shortlink = result.scalar_one_or_none()

            if not shortlink:
                return None

            return {
                "short_code": shortlink.short_code,
                "destination_url": shortlink.destination_url,
                "click_count": shortlink.click_count,
                "last_clicked_at": shortlink.last_clicked_at.isoformat() if shortlink.last_clicked_at else None,
                "is_active": shortlink.is_active,
                "expires_at": shortlink.expires_at.isoformat() if shortlink.expires_at else None,
                "attribution": {
                    "offer_id": str(shortlink.offer_id) if shortlink.offer_id else None,
                    "template_id": str(shortlink.template_id) if shortlink.template_id else None,
                    "icp_id": str(shortlink.icp_id) if shortlink.icp_id else None,
                    "touchpoint_id": str(shortlink.touchpoint_id) if shortlink.touchpoint_id else None
                },
                "utm": {
                    "source": shortlink.utm_source,
                    "medium": shortlink.utm_medium,
                    "campaign": shortlink.utm_campaign,
                    "content": shortlink.utm_content,
                    "term": shortlink.utm_term
                },
                "created_at": shortlink.created_at.isoformat()
            }

    async def deactivate_shortlink(self, short_code: str) -> bool:
        """Deactivate a shortlink"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(Shortlink).where(Shortlink.short_code == short_code)
            )
            shortlink = result.scalar_one_or_none()

            if not shortlink:
                return False

            shortlink.is_active = False
            await db.commit()

            logger.info(f"🔗 Shortlink deactivated: {short_code}")
            return True

    def get_full_url(self, short_code: str) -> str:
        """Get full shortlink URL"""
        return f"{self.base_url}/{short_code}"


# Singleton getter
def get_shortlink_service() -> ShortlinkService:
    """Get shortlink service instance"""
    return ShortlinkService.get_instance()
