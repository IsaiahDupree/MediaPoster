"""
API Endpoints for Relationship-First CRM
Implements the Relationship-First DM Automation System.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

router = APIRouter(prefix="/relationships", tags=["Relationship CRM"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateContactRequest(BaseModel):
    """Request to create a new contact."""
    platform: str = Field(..., description="Platform: instagram, tiktok, twitter, threads")
    username: str = Field(..., description="Username on the platform")
    name: str = Field(default="", description="Display name")
    how_we_met: str = Field(default="", description="How you first connected")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Initial context")


class UpdateContextRequest(BaseModel):
    """Request to update contact context."""
    building: Optional[str] = Field(default=None, description="What they're working on")
    struggles: Optional[str] = Field(default=None, description="What's hard for them")
    values: Optional[str] = Field(default=None, description="What they care about")
    win_30d: Optional[str] = Field(default=None, description="30-day win goal")
    preferred_cadence: Optional[str] = Field(default=None, description="daily|weekly|monthly")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class LogValueRequest(BaseModel):
    """Request to log value delivered."""
    action_type: str = Field(..., description="Type: resource, intro, quick_audit, etc.")
    description: str = Field(..., description="What value was delivered")
    lane: str = Field(default="B", description="Message lane: A, B, or C")
    impact_score: int = Field(default=1, ge=1, le=5, description="Impact 1-5")


class RecordInteractionRequest(BaseModel):
    """Request to record an interaction."""
    direction: str = Field(..., description="inbound or outbound")
    message_text: str = Field(default="", description="Message content")
    lane: str = Field(default="A", description="Message lane: A, B, or C")
    sentiment: str = Field(default="neutral", description="Message sentiment")


class SuggestReplyRequest(BaseModel):
    """Request to suggest a reply."""
    their_message: str = Field(..., description="The message to reply to")
    conversation_history: Optional[List[Dict]] = Field(default=None)


# =============================================================================
# CONTACT MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/contacts")
async def create_contact(request: CreateContactRequest):
    """Create a new relationship contact."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        
        # Check if contact already exists
        existing = crm.get_contact_by_username(request.platform, request.username)
        if existing:
            return {"success": True, "contact": existing.to_dict(), "created": False}
        
        contact = crm.create_contact(
            platform=request.platform,
            username=request.username,
            name=request.name,
            how_we_met=request.how_we_met,
            context=request.context
        )
        
        return {"success": True, "contact": contact.to_dict(), "created": True}
        
    except Exception as e:
        logger.error(f"Failed to create contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str):
    """Get contact by ID."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        contact = crm.get_contact(contact_id)
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return contact.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/by-username/{platform}/{username}")
async def get_contact_by_username(platform: str, username: str):
    """Get contact by platform and username."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        contact = crm.get_contact_by_username(platform, username)
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return contact.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/contacts/{contact_id}/context")
async def update_contact_context(contact_id: str, request: UpdateContextRequest):
    """Update contact context (what they're working on, struggles, etc.)."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        
        updates = {k: v for k, v in request.dict().items() if v is not None}
        contact = crm.update_context(contact_id, updates)
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return {"success": True, "contact": contact.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# VALUE TRACKING ENDPOINTS
# =============================================================================

@router.post("/contacts/{contact_id}/value")
async def log_value_delivered(contact_id: str, request: LogValueRequest):
    """Log value delivered to a contact."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        
        success = crm.log_value_delivered(
            contact_id=contact_id,
            action_type=request.action_type,
            description=request.description,
            lane=request.lane,
            impact_score=request.impact_score
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact = crm.get_contact(contact_id)
        return {"success": True, "contact": contact.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to log value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/{contact_id}/value-log")
async def get_value_log(contact_id: str, limit: int = 20):
    """Get value log for a contact."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        log = crm.get_value_log(contact_id, limit)
        
        return {"value_log": log}
        
    except Exception as e:
        logger.error(f"Failed to get value log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PIPELINE MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/contacts/{contact_id}/advance")
async def advance_pipeline(contact_id: str, to_stage: Optional[str] = None):
    """Advance contact to next pipeline stage."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        contact = crm.advance_pipeline(contact_id, to_stage)
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return {"success": True, "contact": contact.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to advance pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contacts/{contact_id}/trust-signal")
async def record_trust_signal(contact_id: str, signal: str):
    """Record a trust signal from the contact."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        contact = crm.record_trust_signal(contact_id, signal)
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return {"success": True, "contact": contact.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record trust signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# INTERACTION TRACKING ENDPOINTS
# =============================================================================

@router.post("/contacts/{contact_id}/interaction")
async def record_interaction(contact_id: str, request: RecordInteractionRequest):
    """Record an interaction with a contact."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        
        contact = crm.record_interaction(
            contact_id=contact_id,
            direction=request.direction,
            message_text=request.message_text,
            lane=request.lane,
            sentiment=request.sentiment
        )
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return {"success": True, "contact": contact.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RELATIONSHIP HEALTH QUERIES
# =============================================================================

@router.get("/needs-care")
async def get_needs_care(limit: int = 20):
    """Get contacts who need care (health 40-59)."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        contacts = crm.get_needs_care(limit)
        
        return {
            "contacts": [c.to_dict() for c in contacts if c],
            "count": len(contacts)
        }
        
    except Exception as e:
        logger.error(f"Failed to get needs care: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/healthy")
async def get_healthy_relationships(limit: int = 20):
    """Get contacts with healthy relationships (health 80+)."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        contacts = crm.get_healthy_relationships(limit)
        
        return {
            "contacts": [c.to_dict() for c in contacts if c],
            "count": len(contacts)
        }
        
    except Exception as e:
        logger.error(f"Failed to get healthy relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/due-actions")
async def get_due_actions():
    """Get contacts with actions due today or overdue."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        contacts = crm.get_due_for_action()
        
        return {
            "contacts": [c.to_dict() for c in contacts if c],
            "count": len(contacts)
        }
        
    except Exception as e:
        logger.error(f"Failed to get due actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline-summary")
async def get_pipeline_summary():
    """Get count of contacts by pipeline stage."""
    try:
        from services.relationship_crm import get_relationship_crm
        
        crm = get_relationship_crm()
        summary = crm.get_pipeline_summary()
        
        return {"pipeline": summary}
        
    except Exception as e:
        logger.error(f"Failed to get pipeline summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AI SUGGESTIONS ENDPOINTS
# =============================================================================

@router.get("/contacts/{contact_id}/next-action")
async def get_next_action(contact_id: str):
    """Get AI-suggested next best action for a contact."""
    try:
        from services.relationship_crm import get_relationship_crm
        from services.relationship_ai import get_relationship_ai
        
        crm = get_relationship_crm()
        ai = get_relationship_ai()
        
        contact = crm.get_contact(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        action = ai.get_next_best_action(contact.to_dict())
        
        return {
            "contact_id": contact_id,
            "username": contact.username,
            "health": contact.relationship_health,
            "action": {
                "type": action.action_type,
                "lane": action.lane,
                "template_id": action.template_id,
                "message": action.message,
                "reasoning": action.reasoning,
                "priority": action.priority,
                "timing": action.timing
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get next action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contacts/{contact_id}/suggest-reply")
async def suggest_reply(contact_id: str, request: SuggestReplyRequest):
    """Get AI-suggested reply to an incoming message."""
    try:
        from services.relationship_crm import get_relationship_crm
        from services.relationship_ai import get_relationship_ai
        
        crm = get_relationship_crm()
        ai = get_relationship_ai()
        
        contact = crm.get_contact(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        suggestion = await ai.suggest_reply(
            contact=contact.to_dict(),
            their_message=request.their_message,
            conversation_history=request.conversation_history
        )
        
        return {
            "contact_id": contact_id,
            "their_message": request.their_message,
            **suggestion
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to suggest reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-actions")
async def get_batch_actions(limit: int = 10):
    """Get prioritized actions for multiple contacts."""
    try:
        from services.relationship_crm import get_relationship_crm
        from services.relationship_ai import get_relationship_ai
        
        crm = get_relationship_crm()
        ai = get_relationship_ai()
        
        # Get contacts that need attention
        needs_care = crm.get_needs_care(limit=limit)
        due_actions = crm.get_due_for_action()
        
        # Combine and dedupe
        all_contacts = {c.id: c for c in needs_care + due_actions if c}
        contacts_data = [c.to_dict() for c in all_contacts.values()]
        
        actions = ai.get_batch_actions(contacts_data, limit=limit)
        
        return {"actions": actions, "count": len(actions)}
        
    except Exception as e:
        logger.error(f"Failed to get batch actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-message")
async def analyze_message(message: str):
    """Analyze sentiment and intent of a message."""
    try:
        from services.relationship_ai import get_relationship_ai
        
        ai = get_relationship_ai()
        analysis = await ai.analyze_message_sentiment(message)
        
        return {"message": message, "analysis": analysis}
        
    except Exception as e:
        logger.error(f"Failed to analyze message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RF-006: FIT SIGNAL DETECTION
# =============================================================================

@router.post("/contacts/{contact_id}/detect-fit")
async def detect_fit_signals(contact_id: str, messages: List[str]):
    """Detect fit signals in conversation to identify offer opportunities."""
    try:
        from services.relationship_crm import get_relationship_crm
        from services.relationship_fit_signals import FitSignalDetector
        
        crm = get_relationship_crm()
        detector = FitSignalDetector()
        
        contact = crm.get_contact(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        context = {
            "building": contact.context.building if contact.context else "",
            "struggles": contact.context.struggles if contact.context else "",
            "values": contact.context.values if contact.context else ""
        }
        
        matches = await detector.detect_signals_ai(messages, context)
        golden_ready, best_match = detector.check_golden_trigger(contact.to_dict(), matches)
        
        return {
            "contact_id": contact_id,
            "fit_signals": [
                {
                    "offer_type": m.offer_type,
                    "offer_name": m.offer_name,
                    "confidence": m.confidence,
                    "matched_signals": m.matched_signals,
                    "offer_line": m.offer_line
                }
                for m in matches
            ],
            "golden_trigger_ready": golden_ready,
            "recommended_offer": {
                "offer_type": best_match.offer_type,
                "offer_line": best_match.offer_line
            } if best_match else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect fit signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/{contact_id}/offer-timing")
async def get_offer_timing(contact_id: str):
    """Get recommendation on when/how to make an offer."""
    try:
        from services.relationship_crm import get_relationship_crm
        from services.relationship_fit_signals import FitSignalDetector, FitSignalMatch
        
        crm = get_relationship_crm()
        detector = FitSignalDetector()
        
        contact = crm.get_contact(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Create a placeholder fit match for timing check
        fit_match = FitSignalMatch(
            offer_type="general",
            offer_name="General Offer",
            matched_signals=[],
            confidence=0.5,
            offer_line="",
            context="",
            detected_at=None
        )
        
        timing = detector.get_offer_timing_recommendation(contact.to_dict(), fit_match)
        
        return {
            "contact_id": contact_id,
            "health_score": contact.scores.relationship_health if contact.scores else 50,
            "pipeline_stage": contact.pipeline_stage,
            **timing
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get offer timing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RF-007: TOUCH CADENCES
# =============================================================================

@router.get("/cadence/today")
async def get_today_cadence(user_id: str = "default"):
    """Get today's touch cadence summary."""
    try:
        from services.relationship_cadence import TouchCadenceManager
        
        manager = TouchCadenceManager()
        summary = manager.get_today_summary(user_id)
        
        return {"success": True, **summary}
        
    except Exception as e:
        logger.error(f"Failed to get today's cadence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cadence/daily")
async def get_daily_cadence(user_id: str = "default"):
    """Get detailed daily cadence tasks."""
    try:
        from services.relationship_cadence import TouchCadenceManager
        
        manager = TouchCadenceManager()
        cadence = manager.generate_daily_cadence(user_id)
        
        return {
            "date": str(cadence.date),
            "story_replies": [
                {"contact": t.contact_name, "platform": t.platform, "health": t.health_score}
                for t in cadence.story_replies
            ],
            "hot_check_ins": [
                {"contact": t.contact_name, "platform": t.platform, "health": t.health_score, "message": t.suggested_message}
                for t in cadence.hot_check_ins
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get daily cadence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cadence/weekly")
async def get_weekly_cadence(user_id: str = "default"):
    """Get detailed weekly cadence tasks."""
    try:
        from services.relationship_cadence import TouchCadenceManager
        
        manager = TouchCadenceManager()
        cadence = manager.generate_weekly_cadence(user_id)
        
        return {
            "week_start": str(cadence.week_start),
            "micro_wins": [
                {"contact": t.contact_name, "platform": t.platform, "context": t.context, "message": t.suggested_message}
                for t in cadence.micro_wins
            ],
            "curiosity_questions": [
                {"contact": t.contact_name, "platform": t.platform, "message": t.suggested_message}
                for t in cadence.curiosity_questions
            ],
            "permissioned_offers": [
                {"contact": t.contact_name, "platform": t.platform, "context": t.context, "message": t.suggested_message}
                for t in cadence.permissioned_offers
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get weekly cadence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cadence/complete")
async def complete_cadence_task(user_id: str, contact_id: str, task_type: str):
    """Mark a cadence task as complete."""
    try:
        from services.relationship_cadence import TouchCadenceManager
        
        manager = TouchCadenceManager()
        success = manager.mark_task_complete(user_id, contact_id, task_type)
        
        return {"success": success, "message": "Task marked complete" if success else "Failed to mark complete"}
        
    except Exception as e:
        logger.error(f"Failed to complete cadence task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RF-008: SUCCESS METRICS
# =============================================================================

@router.get("/metrics/dashboard")
async def get_metrics_dashboard(user_id: str = "default"):
    """Get full relationship metrics dashboard."""
    try:
        from services.relationship_metrics import RelationshipMetricsService
        
        service = RelationshipMetricsService()
        dashboard = service.get_full_dashboard(user_id)
        
        return {"success": True, **dashboard}
        
    except Exception as e:
        logger.error(f"Failed to get metrics dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/pipeline")
async def get_pipeline_funnel(user_id: str = "default"):
    """Get pipeline stage distribution."""
    try:
        from services.relationship_metrics import RelationshipMetricsService
        
        service = RelationshipMetricsService()
        funnel = service.get_pipeline_funnel(user_id)
        
        return {
            "success": True,
            "funnel": {
                "first_touch": funnel.first_touch,
                "context_captured": funnel.context_captured,
                "micro_win": funnel.micro_win,
                "cadence": funnel.cadence,
                "trust_signals": funnel.trust_signals,
                "fit_identified": funnel.fit_identified,
                "offer": funnel.offer,
                "post_win": funnel.post_win
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get pipeline funnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/health-distribution")
async def get_health_distribution(user_id: str = "default"):
    """Get relationship health score distribution."""
    try:
        from services.relationship_metrics import RelationshipMetricsService
        
        service = RelationshipMetricsService()
        dist = service.get_health_distribution(user_id)
        
        return {
            "success": True,
            "distribution": {
                "excellent_80_100": dist.excellent,
                "good_60_79": dist.good,
                "needs_attention_40_59": dist.needs_attention,
                "cold_below_40": dist.cold
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get health distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/{contact_id}/3-1-rule")
async def check_3_1_rule(contact_id: str, user_id: str = "default"):
    """Check 3:1 rule compliance for a contact."""
    try:
        from services.relationship_metrics import RelationshipMetricsService
        
        service = RelationshipMetricsService()
        result = service.check_3_1_rule_compliance(user_id, contact_id)
        
        return {"success": True, "contact_id": contact_id, **result}
        
    except Exception as e:
        logger.error(f"Failed to check 3:1 rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
