"""
API Endpoints for DM Outreach System
Manages prospect discovery, DM lists, and outreach sequencing.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from loguru import logger

router = APIRouter(prefix="/dm-outreach", tags=["DM Outreach"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class AddProspectRequest(BaseModel):
    """Request to manually add a prospect."""
    platform: str = Field(..., description="Platform name")
    account_id: int = Field(..., description="Your account ID on that platform")
    username: str = Field(..., description="Prospect's username")
    display_name: str = Field(default="")
    bio: str = Field(default="")
    follower_count: int = Field(default=0)
    source_note: str = Field(default="")


class AddToListRequest(BaseModel):
    """Request to add prospect to DM list."""
    prospect_id: str = Field(..., description="Prospect ID")
    assigned_to: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    """Request to update DM list entry status."""
    status: str = Field(..., description="New status")


class UpdatePhaseRequest(BaseModel):
    """Request to update outreach phase."""
    phase: str = Field(..., description="New phase")


class SendMessageRequest(BaseModel):
    """Request to record a sent message."""
    content: str = Field(..., description="Message content")
    template_id: Optional[str] = None


class AddNoteRequest(BaseModel):
    """Request to add a note."""
    note: str = Field(..., description="Note content")


class CreateOfferRequest(BaseModel):
    """Request to create an offer."""
    name: str = Field(..., description="Offer name")
    description: str = Field(default="")
    price_range: str = Field(default="")
    offer_type: str = Field(default="coaching")
    fit_signals: List[str] = Field(default=[])
    disqualifiers: List[str] = Field(default=[])


class DiscoveryRequest(BaseModel):
    """Request to run discovery."""
    platform: Optional[str] = None
    account_id: Optional[int] = None
    sources: List[str] = Field(default=["comments", "engagement"])


# =============================================================================
# PROSPECT ENDPOINTS
# =============================================================================

@router.get("/prospects")
async def get_prospects(
    platform: Optional[str] = None,
    account_id: Optional[int] = None,
    source: Optional[str] = None,
    qualified: Optional[bool] = None,
    limit: int = 50
):
    """Get discovered prospects with filters."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        prospects = manager.get_prospects(
            platform=platform,
            account_id=account_id,
            source=source,
            qualified=qualified,
            limit=limit
        )
        
        return {
            "prospects": [p.to_dict() for p in prospects],
            "count": len(prospects)
        }
        
    except Exception as e:
        logger.error(f"Failed to get prospects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prospects/{prospect_id}")
async def get_prospect(prospect_id: str):
    """Get a specific prospect."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        prospect = manager.get_prospect(prospect_id)
        
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")
        
        return prospect.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prospect: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prospects")
async def add_prospect(request: AddProspectRequest):
    """Manually add a prospect."""
    try:
        from services.dm_outreach import get_prospect_finder
        
        finder = get_prospect_finder()
        prospect = finder.add_manual_prospect(
            platform=request.platform,
            account_id=request.account_id,
            username=request.username,
            display_name=request.display_name,
            bio=request.bio,
            follower_count=request.follower_count,
            source_note=request.source_note
        )
        
        return {"success": True, "prospect": prospect.to_dict()}
        
    except Exception as e:
        logger.error(f"Failed to add prospect: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover")
async def run_discovery(request: DiscoveryRequest, background_tasks: BackgroundTasks):
    """Run prospect discovery."""
    try:
        from services.dm_outreach import get_prospect_finder
        
        finder = get_prospect_finder()
        
        # Run discovery in background for larger operations
        result = await finder.run_discovery(
            platform=request.platform,
            account_id=request.account_id,
            sources=request.sources
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DM LIST ENDPOINTS
# =============================================================================

@router.get("/list")
async def get_dm_list(
    status: Optional[str] = None,
    phase: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50
):
    """Get DM list entries with filters."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        entries = manager.get_dm_list(
            status=status,
            phase=phase,
            platform=platform,
            limit=limit
        )
        
        return {
            "entries": [e.to_dict() for e in entries],
            "count": len(entries)
        }
        
    except Exception as e:
        logger.error(f"Failed to get DM list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/ready")
async def get_ready_to_contact(limit: int = 20):
    """Get prospects ready to contact today."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        entries = manager.get_ready_to_contact(limit=limit)
        
        return {
            "entries": [e.to_dict() for e in entries],
            "count": len(entries)
        }
        
    except Exception as e:
        logger.error(f"Failed to get ready list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list/add")
async def add_to_list(request: AddToListRequest):
    """Add a prospect to the DM list."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        entry = manager.add_to_dm_list(
            prospect_id=request.prospect_id,
            assigned_to=request.assigned_to
        )
        
        return {"success": True, "entry": entry.to_dict()}
        
    except Exception as e:
        logger.error(f"Failed to add to list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/list/{entry_id}/status")
async def update_status(entry_id: str, request: UpdateStatusRequest):
    """Update DM list entry status."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        success = manager.update_status(entry_id, request.status)
        
        if not success:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        return {"success": True, "status": request.status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/list/{entry_id}/phase")
async def update_phase(entry_id: str, request: UpdatePhaseRequest):
    """Update outreach phase."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        success = manager.update_phase(entry_id, request.phase)
        
        if not success:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        return {"success": True, "phase": request.phase}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update phase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list/{entry_id}/message")
async def record_message(entry_id: str, request: SendMessageRequest):
    """Record a sent message."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        manager.record_interaction(entry_id, direction="sent")
        
        return {"success": True, "message_recorded": True}
        
    except Exception as e:
        logger.error(f"Failed to record message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list/{entry_id}/note")
async def add_note(entry_id: str, request: AddNoteRequest):
    """Add a note to DM list entry."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        manager.add_note(entry_id, request.note)
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to add note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MESSAGING ENDPOINTS
# =============================================================================

@router.get("/list/{entry_id}/suggest")
async def get_message_suggestion(entry_id: str):
    """Get AI-suggested next message for a prospect."""
    try:
        from services.dm_outreach import get_dm_list_manager, get_outreach_sequencer
        
        manager = get_dm_list_manager()
        sequencer = get_outreach_sequencer()
        
        # Get the entry with prospect
        entries = manager.get_dm_list(limit=100)
        entry = next((e for e in entries if e.id == entry_id), None)
        
        if not entry or not entry.prospect:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        # Get message suggestion
        suggestion = sequencer.get_next_message(
            phase=entry.phase,
            prospect_data=entry.prospect.to_dict(),
            conversation_history=[],
            context={}
        )
        
        # Get timing recommendation
        timing = sequencer.get_recommended_timing(
            phase=entry.phase,
            last_interaction=entry.last_interaction_at
        )
        
        return {
            "suggestion": {
                "content": suggestion.content,
                "phase": suggestion.phase,
                "template_type": suggestion.template_type,
                "confidence": suggestion.confidence
            },
            "timing": timing
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{entry_id}/should-advance")
async def check_phase_advancement(entry_id: str):
    """Check if prospect should advance to next phase."""
    try:
        from services.dm_outreach import get_dm_list_manager, get_outreach_sequencer
        
        manager = get_dm_list_manager()
        sequencer = get_outreach_sequencer()
        
        entries = manager.get_dm_list(limit=100)
        entry = next((e for e in entries if e.id == entry_id), None)
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        recommendation = sequencer.should_advance_phase(
            current_phase=entry.phase,
            interaction_count=entry.interaction_count,
            trust_score=entry.trust_score,
            last_interaction=entry.last_interaction_at
        )
        
        return recommendation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check advancement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# OFFER ENDPOINTS
# =============================================================================

@router.get("/offers")
async def get_offers(active_only: bool = True):
    """Get all offers."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        offers = manager.get_offers(active_only=active_only)
        
        return {
            "offers": [o.to_dict() for o in offers],
            "count": len(offers)
        }
        
    except Exception as e:
        logger.error(f"Failed to get offers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/offers")
async def create_offer(request: CreateOfferRequest):
    """Create a new offer."""
    try:
        from services.dm_outreach import get_dm_list_manager, Offer
        
        manager = get_dm_list_manager()
        
        offer = Offer(
            name=request.name,
            description=request.description,
            price_range=request.price_range,
            offer_type=request.offer_type,
            fit_signals=request.fit_signals,
            disqualifiers=request.disqualifiers
        )
        
        created = manager.create_offer(offer)
        
        return {"success": True, "offer": created.to_dict()}
        
    except Exception as e:
        logger.error(f"Failed to create offer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{platform}/{account_id}/offers")
async def get_account_offers(platform: str, account_id: int):
    """Get offers assigned to a specific account."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        offers = manager.get_account_offers(platform, account_id)
        
        return {
            "platform": platform,
            "account_id": account_id,
            "offers": [o.to_dict() for o in offers]
        }
        
    except Exception as e:
        logger.error(f"Failed to get account offers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATS ENDPOINTS
# =============================================================================

@router.get("/stats")
async def get_stats():
    """Get outreach statistics."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        stats = manager.get_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funnel")
async def get_funnel():
    """Get outreach funnel metrics."""
    try:
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        stats = manager.get_stats()
        
        by_status = stats.get("by_status", {})
        
        funnel = {
            "stages": [
                {"name": "Discovered", "count": stats.get("total_prospects", 0)},
                {"name": "In List", "count": stats.get("total_in_list", 0)},
                {"name": "Contacted", "count": by_status.get("contacted", 0) + by_status.get("replied", 0) + by_status.get("nurturing", 0)},
                {"name": "Replied", "count": by_status.get("replied", 0) + by_status.get("nurturing", 0)},
                {"name": "Nurturing", "count": by_status.get("nurturing", 0)},
                {"name": "Offer Ready", "count": by_status.get("offer_ready", 0)},
                {"name": "Converted", "count": by_status.get("converted", 0)}
            ]
        }
        
        return funnel
        
    except Exception as e:
        logger.error(f"Failed to get funnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DM SENDING ENDPOINTS
# =============================================================================

class SendDMRequest(BaseModel):
    """Request to send a DM."""
    message: str = Field(..., description="Message to send")


@router.post("/list/{entry_id}/send")
async def send_dm(entry_id: str, request: SendDMRequest):
    """Send a DM to a prospect via Safari automation."""
    try:
        from services.dm_outreach import get_dm_sender
        
        sender = get_dm_sender()
        result = await sender.send_dm(entry_id, request.message)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to send DM: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota")
async def get_dm_quota():
    """Get remaining DM quota per platform."""
    try:
        from services.dm_outreach import get_dm_sender
        
        sender = get_dm_sender()
        return sender.get_daily_quota()
        
    except Exception as e:
        logger.error(f"Failed to get quota: {e}")
        raise HTTPException(status_code=500, detail=str(e))
