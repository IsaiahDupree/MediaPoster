"""
Offer Tracking API Endpoints (ARCH-005)
========================================

REST API for offer traffic tracking and attribution.

Endpoints:
    POST   /api/offer-tracking/create-link       - Create tracked URL
    POST   /api/offer-tracking/click              - Record click event
    POST   /api/offer-tracking/conversion         - Record conversion
    GET    /api/offer-tracking/campaign/:campaign - Get campaign report
    GET    /api/offer-tracking/campaigns          - List all campaigns
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from services.offer_tracker import get_offer_tracker

router = APIRouter(prefix="/api/offer-tracking", tags=["offer-tracking"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateTrackedLinkRequest(BaseModel):
    """Request to create a tracked URL."""

    offer_url: str = Field(..., description="Base offer URL to track")
    campaign: str = Field(..., description="Campaign identifier")
    source: str = Field(..., description="Source platform (twitter, tiktok, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class TrackedLinkResponse(BaseModel):
    """Response with tracked URL."""

    offer_url: str
    tracked_url: str
    campaign: str
    source: str
    created_at: datetime = Field(default_factory=datetime.now)


class ClickEventRequest(BaseModel):
    """Request to record a click event."""

    offer_url: str
    campaign: str
    platform: str
    metadata: Optional[Dict[str, Any]] = None


class ConversionEventRequest(BaseModel):
    """Request to record a conversion event."""

    offer_url: str
    campaign: str
    platform: str
    conversion_type: str = "purchase"
    revenue: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class CampaignReportResponse(BaseModel):
    """Campaign performance report."""

    campaign: str
    platforms: int
    total_clicks: int
    total_conversions: int
    total_revenue: float
    conversion_rate: float
    avg_revenue_per_conversion: float
    first_tracked: Optional[str] = None
    last_click: Optional[str] = None


class PlatformReportResponse(BaseModel):
    """Platform-specific report within a campaign."""

    campaign: str
    platform: str
    urls: int
    clicks: int
    conversions: int
    revenue: float
    conversion_rate: float
    first_tracked: Optional[str] = None
    last_click: Optional[str] = None


class CampaignSummary(BaseModel):
    """Summary of a campaign."""

    campaign: str
    platforms: int
    clicks: int
    conversions: int
    revenue: float
    conversion_rate: float
    last_activity: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/create-link", response_model=TrackedLinkResponse)
async def create_tracked_link(request: CreateTrackedLinkRequest) -> Dict[str, Any]:
    """
    Create a tracked URL with UTM parameters (ARCH-005).

    Args:
        request: CreateTrackedLinkRequest with offer_url, campaign, source

    Returns:
        Tracked URL with UTM parameters
    """
    tracker = get_offer_tracker()

    tracked_url = await tracker.create_tracked_link(
        offer_url=request.offer_url,
        campaign=request.campaign,
        source=request.source,
        metadata=request.metadata,
    )

    return {
        "offer_url": request.offer_url,
        "tracked_url": tracked_url,
        "campaign": request.campaign,
        "source": request.source,
    }


@router.post("/click")
async def record_click(request: ClickEventRequest) -> Dict[str, Any]:
    """
    Record a click event for a tracked link.

    Args:
        request: ClickEventRequest with link details

    Returns:
        Success status
    """
    tracker = get_offer_tracker()

    success = await tracker.track_click(
        offer_url=request.offer_url,
        campaign=request.campaign,
        platform=request.platform,
        metadata=request.metadata,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to track click")

    return {"success": True, "message": "Click recorded"}


@router.post("/conversion")
async def record_conversion(request: ConversionEventRequest) -> Dict[str, Any]:
    """
    Record a conversion event.

    Args:
        request: ConversionEventRequest with conversion details

    Returns:
        Success status
    """
    tracker = get_offer_tracker()

    success = await tracker.track_conversion(
        offer_url=request.offer_url,
        campaign=request.campaign,
        platform=request.platform,
        conversion_type=request.conversion_type,
        revenue=request.revenue,
        metadata=request.metadata,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to track conversion")

    return {"success": True, "message": "Conversion recorded"}


@router.get("/campaign/{campaign}", response_model=CampaignReportResponse)
async def get_campaign_report(
    campaign: str,
    limit_days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get aggregated report for a campaign (ARCH-005).

    Args:
        campaign: Campaign identifier
        limit_days: Optional limit to last N days

    Returns:
        Campaign metrics
    """
    tracker = get_offer_tracker()

    report = await tracker.get_campaign_report(campaign, limit_days)

    if "error" in report:
        raise HTTPException(status_code=500, detail=report["error"])

    return report


@router.get("/campaign/{campaign}/platform/{platform}", response_model=PlatformReportResponse)
async def get_platform_report(campaign: str, platform: str) -> Dict[str, Any]:
    """
    Get report for a specific platform within a campaign.

    Args:
        campaign: Campaign identifier
        platform: Platform name

    Returns:
        Platform metrics
    """
    tracker = get_offer_tracker()

    report = await tracker.get_platform_report(campaign, platform)

    if "error" in report:
        raise HTTPException(status_code=500, detail=report["error"])

    return report


@router.get("/campaigns", response_model=List[CampaignSummary])
async def list_all_campaigns() -> List[Dict[str, Any]]:
    """
    Get summary metrics for all campaigns.

    Returns:
        List of campaign summaries
    """
    tracker = get_offer_tracker()

    campaigns = await tracker.get_all_campaigns()

    return campaigns
