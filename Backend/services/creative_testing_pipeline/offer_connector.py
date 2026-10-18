"""
ACTP Offer Connector
=====================
Bridges to WaitlistLab for offer alignment and audience targeting.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .models import TestCampaign

logger = logging.getLogger(__name__)

WAITLISTLAB_API_URL = os.getenv(
    "WAITLISTLAB_API_URL",
    "http://localhost:3000/api",
)
WAITLISTLAB_API_KEY = os.getenv("WAITLISTLAB_API_KEY")


class OfferConnector:
    """
    Connects to WaitlistLab for offer data, audiences, and landing pages.

    Supports two modes:
    - offer: Align ads to a specific offer/product with landing page
    - growth: Optimize for social media account growth
    """

    def __init__(self, db_client=None):
        self.db = db_client
        logger.info("[ACTP:Offer] Connector initialized")

    async def get_active_offers(self) -> List[Dict[str, Any]]:
        """Fetch active offers from WaitlistLab."""
        import httpx

        if not WAITLISTLAB_API_KEY:
            logger.warning("[ACTP:Offer] WAITLISTLAB_API_KEY not set, returning empty")
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{WAITLISTLAB_API_URL}/campaigns",
                    headers={"Authorization": f"Bearer {WAITLISTLAB_API_KEY}"},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("campaigns", data) if isinstance(data, dict) else data
        except Exception as e:
            logger.error(f"[ACTP:Offer] Failed to fetch offers: {e}")
            return []

    async def get_offer_detail(self, offer_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific offer's details including landing page URL."""
        import httpx

        if not WAITLISTLAB_API_KEY:
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{WAITLISTLAB_API_URL}/campaigns/{offer_id}",
                    headers={"Authorization": f"Bearer {WAITLISTLAB_API_KEY}"},
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"[ACTP:Offer] Failed to fetch offer {offer_id}: {e}")
            return None

    async def get_landing_page_url(self, offer_id: str) -> Optional[str]:
        """Get the landing page URL for an offer."""
        offer = await self.get_offer_detail(offer_id)
        if offer:
            return offer.get("landing_page_url") or offer.get("url")
        return None

    async def get_target_audience(self, offer_id: str) -> Dict[str, Any]:
        """Get the target audience definition for an offer."""
        offer = await self.get_offer_detail(offer_id)
        if offer:
            return offer.get("target_audience", {})
        return {}

    async def report_performance(
        self,
        offer_id: str,
        metrics: Dict[str, Any],
    ) -> bool:
        """Report ad performance back to WaitlistLab for the offer."""
        import httpx

        if not WAITLISTLAB_API_KEY:
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{WAITLISTLAB_API_URL}/campaigns/{offer_id}/performance",
                    headers={"Authorization": f"Bearer {WAITLISTLAB_API_KEY}"},
                    json=metrics,
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"[ACTP:Offer] Failed to report performance: {e}")
            return False

    def build_campaign_from_offer(
        self, offer: Dict[str, Any], angles: List[str], mode: str = "offer"
    ) -> Dict[str, Any]:
        """
        Build a CreateCampaignRequest dict from a WaitlistLab offer.
        """
        return {
            "name": f"ACTP - {offer.get('name', 'Unknown Offer')}",
            "offer_id": offer.get("id"),
            "offer_name": offer.get("name"),
            "offer_url": offer.get("landing_page_url") or offer.get("url"),
            "angles": angles,
            "target_audience": offer.get("target_audience"),
            "mode": mode,
        }
