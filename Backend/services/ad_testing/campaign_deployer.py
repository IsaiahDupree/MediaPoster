"""
Meta Campaign Deployer (AD-004)
================================
Deploys ad creatives to Meta Ads (Facebook/Instagram) via the Marketing API.

Manages the full campaign creation hierarchy:
    Campaign -> Ad Set -> Ad (with creative)

Stores state locally so the service works without real API credentials.
When META_ACCESS_TOKEN is set, it will use the real Marketing API.

Usage:
    deployer = get_campaign_deployer()
    campaign = deployer.create_campaign("Test Q1", "CONVERSIONS", 5000, variations)
    creative_id = deployer.upload_creative("/path/to/video.mp4")
    ad_set = deployer.create_ad_set(campaign["id"], audience, 2500)
    ad = deployer.create_ad(ad_set["id"], creative_id, "Headline", "Body text")
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Meta Marketing API base URL (v18.0)
META_API_BASE = "https://graph.facebook.com/v18.0"

# Campaign objective mappings
VALID_OBJECTIVES = {
    "CONVERSIONS",
    "TRAFFIC",
    "REACH",
    "LEAD_GENERATION",
    "VIDEO_VIEWS",
    "BRAND_AWARENESS",
    "APP_INSTALLS",
    "ENGAGEMENT",
    "MESSAGES",
    "SALES",
}

# Default bid strategy
DEFAULT_BID_STRATEGY = "LOWEST_COST_WITHOUT_CAP"


class MetaCampaignDeployer:
    """
    Deploys ad campaigns to Meta Ads platform (AD-004).

    Uses the Meta Marketing API when credentials are available.
    Falls back to local state management for development/testing.
    """

    _instance: Optional["MetaCampaignDeployer"] = None

    def __init__(self) -> None:
        self._access_token: Optional[str] = os.getenv("META_ACCESS_TOKEN")
        self._ad_account_id: Optional[str] = os.getenv("META_AD_ACCOUNT_ID")
        self._use_api = bool(self._access_token and self._ad_account_id)

        # Local state storage
        self._campaigns: Dict[str, Dict[str, Any]] = {}
        self._ad_sets: Dict[str, Dict[str, Any]] = {}
        self._ads: Dict[str, Dict[str, Any]] = {}
        self._creatives: Dict[str, Dict[str, Any]] = {}

        if self._use_api:
            logger.info(
                f"[AD-004] MetaCampaignDeployer initialized with Meta API "
                f"(account={self._ad_account_id})"
            )
        else:
            logger.info(
                "[AD-004] MetaCampaignDeployer initialized in local mode "
                "(set META_ACCESS_TOKEN and META_AD_ACCOUNT_ID for live API)"
            )

    # ------------------------------------------------------------------
    # Campaign CRUD
    # ------------------------------------------------------------------

    def create_campaign(
        self,
        name: str,
        objective: str,
        budget_cents: int,
        ad_variations: Optional[List[Dict[str, Any]]] = None,
        special_ad_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Meta ad campaign.

        Args:
            name: Campaign name.
            objective: Campaign objective (CONVERSIONS, TRAFFIC, etc.).
            budget_cents: Daily budget in cents.
            ad_variations: Optional list of ad variations to auto-create ad sets.
            special_ad_categories: Required Meta compliance field (e.g., HOUSING, CREDIT).

        Returns:
            Campaign dict with id, name, objective, status, budget, ad_sets.
        """
        objective = objective.upper()
        if objective not in VALID_OBJECTIVES:
            logger.warning(
                f"[AD-004] Objective '{objective}' not in known set, proceeding anyway"
            )

        campaign_id = f"camp-{uuid4().hex[:8]}"

        campaign: Dict[str, Any] = {
            "id": campaign_id,
            "name": name,
            "objective": objective,
            "daily_budget_cents": budget_cents,
            "status": "PAUSED",
            "bid_strategy": DEFAULT_BID_STRATEGY,
            "special_ad_categories": special_ad_categories or [],
            "ad_sets": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._use_api:
            try:
                api_result = self._api_create_campaign(campaign)
                campaign["meta_id"] = api_result.get("id")
                campaign["status"] = "ACTIVE"
                logger.info(
                    f"[AD-004] Campaign created via API: {campaign['meta_id']}"
                )
            except Exception as exc:
                logger.error(f"[AD-004] API campaign creation failed: {exc}")
                campaign["api_error"] = str(exc)

        self._campaigns[campaign_id] = campaign

        # Auto-create ad sets from variations if provided
        if ad_variations:
            self._auto_create_ad_sets(campaign_id, ad_variations, budget_cents)

        logger.info(
            f"[AD-004] Campaign '{name}' created: {campaign_id} "
            f"(objective={objective}, budget=${budget_cents / 100:.2f}/day)"
        )
        return campaign

    def upload_creative(
        self,
        video_path: str,
        thumbnail_path: Optional[str] = None,
        title: Optional[str] = None,
    ) -> str:
        """
        Upload a video creative asset.

        Args:
            video_path: Path to the video file.
            thumbnail_path: Optional custom thumbnail.
            title: Optional creative title.

        Returns:
            creative_id: ID of the uploaded creative.
        """
        creative_id = f"cre-{uuid4().hex[:8]}"

        creative: Dict[str, Any] = {
            "id": creative_id,
            "video_path": video_path,
            "thumbnail_path": thumbnail_path,
            "title": title or os.path.basename(video_path),
            "status": "ready",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._use_api:
            try:
                api_result = self._api_upload_creative(video_path)
                creative["meta_video_id"] = api_result.get("video_id")
                creative["meta_creative_id"] = api_result.get("creative_id")
                logger.info(f"[AD-004] Creative uploaded via API: {creative_id}")
            except Exception as exc:
                logger.error(f"[AD-004] API creative upload failed: {exc}")
                creative["api_error"] = str(exc)

        self._creatives[creative_id] = creative
        logger.info(f"[AD-004] Creative registered: {creative_id} ({video_path})")
        return creative_id

    def create_ad_set(
        self,
        campaign_id: str,
        audience: Dict[str, Any],
        budget_cents: int,
        optimization_goal: str = "CONVERSIONS",
        bid_amount_cents: Optional[int] = None,
        placements: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create an ad set within a campaign.

        Args:
            campaign_id: Parent campaign ID.
            audience: Targeting dict with age_min, age_max, interests, etc.
            budget_cents: Daily budget in cents for this ad set.
            optimization_goal: Optimization event (CONVERSIONS, LINK_CLICKS, etc.).
            bid_amount_cents: Optional manual bid amount.
            placements: Optional list of placements (facebook_feed, instagram_stories, etc.).

        Returns:
            Ad set dict with id, campaign_id, audience, status.
        """
        ad_set_id = f"adset-{uuid4().hex[:8]}"

        ad_set: Dict[str, Any] = {
            "id": ad_set_id,
            "campaign_id": campaign_id,
            "audience": audience,
            "daily_budget_cents": budget_cents,
            "optimization_goal": optimization_goal,
            "bid_amount_cents": bid_amount_cents,
            "placements": placements or ["automatic"],
            "status": "PAUSED",
            "ads": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._use_api:
            try:
                api_result = self._api_create_ad_set(campaign_id, ad_set)
                ad_set["meta_id"] = api_result.get("id")
                ad_set["status"] = "ACTIVE"
            except Exception as exc:
                logger.error(f"[AD-004] API ad set creation failed: {exc}")
                ad_set["api_error"] = str(exc)

        self._ad_sets[ad_set_id] = ad_set

        # Link to campaign
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign["ad_sets"].append(ad_set_id)
            campaign["updated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[AD-004] Ad set created: {ad_set_id} (campaign={campaign_id}, "
            f"budget=${budget_cents / 100:.2f}/day)"
        )
        return ad_set

    def create_ad(
        self,
        ad_set_id: str,
        creative_id: str,
        headline: str,
        body: str,
        cta_type: str = "LEARN_MORE",
        link_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an individual ad within an ad set.

        Args:
            ad_set_id: Parent ad set ID.
            creative_id: ID of the creative to use.
            headline: Ad headline text.
            body: Ad primary text (body copy).
            cta_type: CTA button type (LEARN_MORE, SHOP_NOW, SIGN_UP, etc.).
            link_url: Destination URL.

        Returns:
            Ad dict with id, ad_set_id, creative_id, status.
        """
        ad_id = f"ad-{uuid4().hex[:8]}"

        ad: Dict[str, Any] = {
            "id": ad_id,
            "ad_set_id": ad_set_id,
            "creative_id": creative_id,
            "headline": headline,
            "body": body,
            "cta_type": cta_type,
            "link_url": link_url,
            "status": "PAUSED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._use_api:
            try:
                api_result = self._api_create_ad(ad_set_id, ad)
                ad["meta_id"] = api_result.get("id")
                ad["status"] = "ACTIVE"
            except Exception as exc:
                logger.error(f"[AD-004] API ad creation failed: {exc}")
                ad["api_error"] = str(exc)

        self._ads[ad_id] = ad

        # Link to ad set
        ad_set = self._ad_sets.get(ad_set_id)
        if ad_set:
            ad_set["ads"].append(ad_id)
            ad_set["updated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"[AD-004] Ad created: {ad_id} (ad_set={ad_set_id})")
        return ad

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get a campaign by ID."""
        return self._campaigns.get(campaign_id)

    def get_ad_set(self, ad_set_id: str) -> Optional[Dict[str, Any]]:
        """Get an ad set by ID."""
        return self._ad_sets.get(ad_set_id)

    def get_ad(self, ad_id: str) -> Optional[Dict[str, Any]]:
        """Get an ad by ID."""
        return self._ads.get(ad_id)

    def list_campaigns(self) -> List[Dict[str, Any]]:
        """List all campaigns."""
        return list(self._campaigns.values())

    def update_campaign_status(self, campaign_id: str, status: str) -> bool:
        """Update a campaign's status (ACTIVE, PAUSED, ARCHIVED)."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False
        campaign["status"] = status
        campaign["updated_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[AD-004] Campaign {campaign_id} status -> {status}")
        return True

    def update_ad_status(self, ad_id: str, status: str) -> bool:
        """Update an ad's status (ACTIVE, PAUSED)."""
        ad = self._ads.get(ad_id)
        if not ad:
            return False
        ad["status"] = status
        ad["updated_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[AD-004] Ad {ad_id} status -> {status}")
        return True

    # ------------------------------------------------------------------
    # Auto-create helpers
    # ------------------------------------------------------------------

    def _auto_create_ad_sets(
        self,
        campaign_id: str,
        variations: List[Dict[str, Any]],
        total_budget_cents: int,
    ) -> None:
        """Automatically create ad sets and ads from variations."""
        # Group variations by audience
        audience_groups: Dict[str, List[Dict[str, Any]]] = {}
        for var in variations:
            audience = var.get("target_audience", {})
            audience_key = audience.get("name", "default")
            audience_groups.setdefault(audience_key, []).append(var)

        budget_per_set = max(100, total_budget_cents // max(len(audience_groups), 1))

        for audience_key, group_vars in audience_groups.items():
            audience = group_vars[0].get("target_audience", {"name": audience_key})
            ad_set = self.create_ad_set(campaign_id, audience, budget_per_set)

            for var in group_vars:
                # Register placeholder creative
                creative_id = self.upload_creative(
                    var.get("video_path", f"/pending/{var.get('id', 'unknown')}.mp4"),
                    title=var.get("headline", "Ad Creative"),
                )
                self.create_ad(
                    ad_set["id"],
                    creative_id,
                    headline=var.get("headline", ""),
                    body=var.get("body", ""),
                )

        logger.info(
            f"[AD-004] Auto-created {len(audience_groups)} ad sets with "
            f"{len(variations)} ads for campaign {campaign_id}"
        )

    # ------------------------------------------------------------------
    # Meta Marketing API calls (used when credentials available)
    # ------------------------------------------------------------------

    def _api_create_campaign(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        """Create campaign via Meta Marketing API."""
        import requests

        url = f"{META_API_BASE}/act_{self._ad_account_id}/campaigns"
        payload = {
            "name": campaign["name"],
            "objective": campaign["objective"],
            "daily_budget": campaign["daily_budget_cents"],
            "bid_strategy": campaign["bid_strategy"],
            "status": "PAUSED",
            "special_ad_categories": campaign.get("special_ad_categories", []),
            "access_token": self._access_token,
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _api_upload_creative(self, video_path: str) -> Dict[str, Any]:
        """Upload video and create ad creative via Meta API."""
        import requests

        # Step 1: Upload video
        url = f"{META_API_BASE}/act_{self._ad_account_id}/advideos"
        with open(video_path, "rb") as video_file:
            resp = requests.post(
                url,
                files={"source": video_file},
                data={"access_token": self._access_token},
                timeout=120,
            )
        resp.raise_for_status()
        video_id = resp.json().get("id")

        # Step 2: Create ad creative
        creative_url = f"{META_API_BASE}/act_{self._ad_account_id}/adcreatives"
        creative_payload = {
            "name": f"Creative-{video_id}",
            "object_story_spec": {
                "video_data": {
                    "video_id": video_id,
                    "call_to_action": {"type": "LEARN_MORE"},
                }
            },
            "access_token": self._access_token,
        }
        resp2 = requests.post(creative_url, json=creative_payload, timeout=30)
        resp2.raise_for_status()

        return {"video_id": video_id, "creative_id": resp2.json().get("id")}

    def _api_create_ad_set(
        self, campaign_id: str, ad_set: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create ad set via Meta Marketing API."""
        import requests

        campaign = self._campaigns.get(campaign_id, {})
        meta_campaign_id = campaign.get("meta_id", campaign_id)

        url = f"{META_API_BASE}/act_{self._ad_account_id}/adsets"
        audience = ad_set.get("audience", {})

        targeting = {}
        if audience.get("age_min"):
            targeting["age_min"] = audience["age_min"]
        if audience.get("age_max"):
            targeting["age_max"] = audience["age_max"]
        if audience.get("interests"):
            targeting["flexible_spec"] = [
                {"interests": [{"name": i} for i in audience["interests"]]}
            ]

        payload = {
            "name": f"AdSet-{ad_set['id']}",
            "campaign_id": meta_campaign_id,
            "daily_budget": ad_set["daily_budget_cents"],
            "optimization_goal": ad_set["optimization_goal"],
            "billing_event": "IMPRESSIONS",
            "targeting": targeting,
            "status": "PAUSED",
            "access_token": self._access_token,
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _api_create_ad(
        self, ad_set_id: str, ad: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create ad via Meta Marketing API."""
        import requests

        ad_set = self._ad_sets.get(ad_set_id, {})
        meta_ad_set_id = ad_set.get("meta_id", ad_set_id)

        creative = self._creatives.get(ad.get("creative_id", ""), {})
        meta_creative_id = creative.get("meta_creative_id", ad.get("creative_id"))

        url = f"{META_API_BASE}/act_{self._ad_account_id}/ads"
        payload = {
            "name": f"Ad-{ad['id']}",
            "adset_id": meta_ad_set_id,
            "creative": {"creative_id": meta_creative_id},
            "status": "PAUSED",
            "access_token": self._access_token,
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_campaign_deployer_instance: Optional[MetaCampaignDeployer] = None


def get_campaign_deployer() -> MetaCampaignDeployer:
    """Get or create the singleton MetaCampaignDeployer instance."""
    global _campaign_deployer_instance
    if _campaign_deployer_instance is None:
        _campaign_deployer_instance = MetaCampaignDeployer()
    return _campaign_deployer_instance
