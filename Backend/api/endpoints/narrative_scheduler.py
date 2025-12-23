"""
AI Narrative Scheduler API Endpoints

Provides endpoints for:
- Managing narrative goals, pillars, and constraints
- Generating AI-powered 7-day content plans
- Viewing AI reasoning chains
- Approving and scheduling plans
- Reflection and learning system
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date
import logging
import json

from services.narrative_scheduler.scheduler import NarrativeScheduler
from services.narrative_scheduler.models import (
    NarrativeGoal,
    NarrativePillar,
    SchedulingConstraints,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/narrative", tags=["Narrative Scheduler"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class NarrativeGoalCreate(BaseModel):
    goal_statement: str = Field(..., description="The narrative goal statement")
    primary_cta: str = Field(default="follow", description="Primary call-to-action")
    target_audience: str = Field(default="", description="Target audience description")
    time_horizon: str = Field(default="next_7_days")
    target_followers: Optional[int] = None
    target_engagement_rate: Optional[float] = None
    target_conversions: Optional[int] = None


class NarrativePillarCreate(BaseModel):
    name: str
    description: str = ""
    pillar_type: str = "value"  # value, proof, cta
    color: str = "#3b82f6"
    keywords: List[str] = []
    target_percentage: float = 20.0
    min_posts_per_week: int = 1
    max_posts_per_week: int = 5


class SchedulingConstraintsCreate(BaseModel):
    enabled_platforms: List[str] = ["tiktok", "instagram"]
    max_posts_per_day: int = 3
    min_posts_per_day: int = 1
    posting_windows: Dict[str, List[str]] = {}
    timezone: str = "America/New_York"
    min_pre_social_score: int = 60
    max_same_pillar_consecutive: int = 2


class GeneratePlanRequest(BaseModel):
    goal_id: Optional[str] = None
    use_defaults: bool = True


class PlanResponse(BaseModel):
    id: str
    goal_id: str
    week_start: str
    week_end: str
    total_posts: int
    pillar_distribution: Dict[str, int]
    platform_distribution: Dict[str, int]
    status: str
    reasoning_chain: List[Dict[str, Any]]
    justification_summary: str
    scheduled_slots: List[Dict[str, Any]]


# =============================================================================
# NARRATIVE GOALS ENDPOINTS
# =============================================================================

@router.get("/goals")
async def list_narrative_goals():
    """List all narrative goals"""
    scheduler = NarrativeScheduler()
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("""
            SELECT id, goal_text, cta_type, audience_description, time_horizon,
                   platforms, max_posts_per_day, is_active, created_at
            FROM narrative_goals ORDER BY created_at DESC
        """))
        
        goals = []
        for row in result:
            goals.append({
                "id": str(row[0]),
                "goal_statement": row[1],
                "primary_cta": row[2],
                "target_audience": row[3],
                "time_horizon": row[4],
                "platforms": row[5],
                "max_posts_per_day": row[6],
                "status": "active" if row[7] else "inactive",
                "created_at": str(row[8]) if row[8] else None
            })
        
        return {"goals": goals, "total": len(goals)}


@router.post("/goals")
async def create_narrative_goal(goal: NarrativeGoalCreate):
    """Create a new narrative goal"""
    scheduler = NarrativeScheduler()
    
    import uuid
    goal_id = str(uuid.uuid4())
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("""
            INSERT INTO narrative_goals (id, goal_text, cta_type, audience_description,
                time_horizon, platforms, max_posts_per_day, is_active)
            VALUES (:id, :goal_text, :cta_type, :audience_description,
                :time_horizon, :platforms, 3, TRUE)
        """), {
            "id": goal_id,
            "goal_text": goal.goal_statement,
            "cta_type": goal.primary_cta,
            "audience_description": goal.target_audience,
            "time_horizon": goal.time_horizon,
            "platforms": ["tiktok", "instagram"]
        })
        conn.commit()
    
    return {"id": goal_id, "message": "Goal created successfully"}


@router.get("/goals/{goal_id}")
async def get_narrative_goal(goal_id: str):
    """Get a specific narrative goal"""
    scheduler = NarrativeScheduler()
    goal = await scheduler._load_goal(goal_id)
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return goal.to_dict()


# =============================================================================
# NARRATIVE PILLARS ENDPOINTS
# =============================================================================

@router.get("/goals/{goal_id}/pillars")
async def list_goal_pillars(goal_id: str):
    """List pillars for a goal"""
    scheduler = NarrativeScheduler()
    pillars = await scheduler._load_pillars(goal_id)
    
    return {"pillars": [p.to_dict() for p in pillars], "total": len(pillars)}


@router.post("/goals/{goal_id}/pillars")
async def create_pillar(goal_id: str, pillar: NarrativePillarCreate):
    """Create a pillar for a goal"""
    scheduler = NarrativeScheduler()
    
    import uuid
    pillar_id = str(uuid.uuid4())
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("""
            INSERT INTO narrative_pillars (id, goal_id, name, description, pillar_type, color,
                keywords, target_percentage, min_posts_per_week, max_posts_per_week, is_active)
            VALUES (:id, :goal_id, :name, :description, :pillar_type, :color,
                :keywords, :target_percentage, :min_posts, :max_posts, TRUE)
        """), {
            "id": pillar_id,
            "goal_id": goal_id,
            "name": pillar.name,
            "description": pillar.description,
            "pillar_type": pillar.pillar_type,
            "color": pillar.color,
            "keywords": pillar.keywords,
            "target_percentage": pillar.target_percentage,
            "min_posts": pillar.min_posts_per_week,
            "max_posts": pillar.max_posts_per_week
        })
        conn.commit()
    
    return {"id": pillar_id, "message": "Pillar created successfully"}


# =============================================================================
# SCHEDULING CONSTRAINTS ENDPOINTS
# =============================================================================

@router.get("/goals/{goal_id}/constraints")
async def get_goal_constraints(goal_id: str):
    """Get scheduling constraints for a goal"""
    scheduler = NarrativeScheduler()
    constraints = await scheduler._load_constraints(goal_id)
    
    if constraints:
        return constraints.to_dict()
    
    # Return defaults
    return scheduler._get_default_constraints().to_dict()


@router.post("/goals/{goal_id}/constraints")
async def set_goal_constraints(goal_id: str, constraints: SchedulingConstraintsCreate):
    """Set scheduling constraints for a goal"""
    scheduler = NarrativeScheduler()
    
    import uuid
    constraint_id = str(uuid.uuid4())
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        # Delete existing constraints
        conn.execute(text("DELETE FROM scheduling_constraints WHERE goal_id = :goal_id"), {"goal_id": goal_id})
        
        # Insert new constraints
        conn.execute(text("""
            INSERT INTO scheduling_constraints (id, goal_id, enabled_platforms, max_posts_per_day,
                min_posts_per_day, posting_windows, timezone, min_pre_social_score, max_same_pillar_consecutive)
            VALUES (:id, :goal_id, :platforms, :max_posts, :min_posts, :windows, :timezone, :min_score, :max_consecutive)
        """), {
            "id": constraint_id,
            "goal_id": goal_id,
            "platforms": constraints.enabled_platforms,
            "max_posts": constraints.max_posts_per_day,
            "min_posts": constraints.min_posts_per_day,
            "windows": json.dumps(constraints.posting_windows),
            "timezone": constraints.timezone,
            "min_score": constraints.min_pre_social_score,
            "max_consecutive": constraints.max_same_pillar_consecutive
        })
        conn.commit()
    
    return {"id": constraint_id, "message": "Constraints saved successfully"}


# =============================================================================
# AI PLAN GENERATION ENDPOINTS
# =============================================================================

@router.post("/generate-plan")
async def generate_7_day_plan(request: GeneratePlanRequest, background_tasks: BackgroundTasks):
    """
    Generate a 7-day content plan with AI reasoning.
    
    This is the main endpoint that:
    1. Loads goals, pillars, constraints
    2. Analyzes available content
    3. Generates schedule with full reasoning chain
    4. Returns plan for review
    """
    logger.info("[API] Generate plan request received")
    
    scheduler = NarrativeScheduler()
    
    try:
        plan = await scheduler.generate_7_day_plan(
            goal_id=request.goal_id,
            use_defaults=request.use_defaults
        )
        
        return {
            "success": True,
            "plan": plan.to_dict()
        }
    except Exception as e:
        logger.error(f"[API] Plan generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def list_plans(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, le=50)
):
    """List generated plans"""
    scheduler = NarrativeScheduler()
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        
        query = """
            SELECT id, goal_id, week_start, week_end, total_posts, 
                   pillar_distribution, platform_distribution, status, created_at
            FROM weekly_schedules
        """
        params = {}
        
        if status:
            query += " WHERE status = :status"
            params["status"] = status
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit
        
        result = conn.execute(text(query), params)
        
        plans = []
        for row in result:
            plans.append({
                "id": str(row[0]),
                "goal_id": str(row[1]) if row[1] else None,
                "week_start": str(row[2]) if row[2] else None,
                "week_end": str(row[3]) if row[3] else None,
                "total_posts": row[4],
                "pillar_distribution": json.loads(row[5]) if row[5] else {},
                "platform_distribution": json.loads(row[6]) if row[6] else {},
                "status": row[7],
                "created_at": str(row[8]) if row[8] else None
            })
        
        return {"plans": plans, "total": len(plans)}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get a specific plan with full details"""
    scheduler = NarrativeScheduler()
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        
        # Get plan
        result = conn.execute(text("""
            SELECT id, goal_id, week_start, week_end, total_posts, 
                   pillar_distribution, platform_distribution, reasoning_chain,
                   justification, status, created_at
            FROM weekly_schedules WHERE id = :plan_id
        """), {"plan_id": plan_id})
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Get slots
        slots_result = conn.execute(text("""
            SELECT id, video_id, video_title, platform, scheduled_date, 
                   scheduled_time, pillar, selection_reason
            FROM schedule_slots WHERE schedule_id = :plan_id
            ORDER BY scheduled_date, scheduled_time
        """), {"plan_id": plan_id})
        
        slots = []
        for slot_row in slots_result:
            slots.append({
                "id": str(slot_row[0]),
                "video_id": str(slot_row[1]),
                "video_title": slot_row[2],
                "platform": slot_row[3],
                "scheduled_date": str(slot_row[4]) if slot_row[4] else None,
                "scheduled_time": slot_row[5],
                "pillar": slot_row[6],
                "selection_reason": slot_row[7]
            })
        
        return {
            "id": str(row[0]),
            "goal_id": str(row[1]) if row[1] else None,
            "week_start": str(row[2]) if row[2] else None,
            "week_end": str(row[3]) if row[3] else None,
            "total_posts": row[4],
            "pillar_distribution": json.loads(row[5]) if row[5] else {},
            "platform_distribution": json.loads(row[6]) if row[6] else {},
            "reasoning_chain": json.loads(row[7]) if row[7] else [],
            "justification": row[8],
            "status": row[9],
            "created_at": str(row[10]) if row[10] else None,
            "scheduled_slots": slots
        }


@router.get("/plans/{plan_id}/reasoning")
async def get_plan_reasoning(plan_id: str):
    """Get the AI reasoning chain for a plan"""
    scheduler = NarrativeScheduler()
    reasoning = await scheduler.get_plan_reasoning(plan_id)
    
    if not reasoning:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return reasoning


@router.post("/plans/{plan_id}/approve")
async def approve_plan(plan_id: str):
    """Approve a plan and create scheduled posts"""
    scheduler = NarrativeScheduler()
    
    try:
        result = await scheduler.approve_and_schedule(plan_id)
        return result
    except Exception as e:
        logger.error(f"[API] Plan approval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans/{plan_id}/regenerate")
async def regenerate_plan(plan_id: str, adjustments: Optional[Dict[str, Any]] = None):
    """Regenerate a plan with optional adjustments"""
    scheduler = NarrativeScheduler()
    
    # Get existing plan's goal
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT goal_id FROM weekly_schedules WHERE id = :plan_id"), {"plan_id": plan_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        goal_id = str(row[0]) if row[0] else None
    
    # Generate new plan
    plan = await scheduler.generate_7_day_plan(goal_id=goal_id, use_defaults=True)
    
    return {
        "success": True,
        "new_plan": plan.to_dict(),
        "old_plan_id": plan_id
    }


# =============================================================================
# REFLECTION & LEARNING ENDPOINTS
# =============================================================================

@router.get("/performance/{week_start}")
async def get_week_performance(week_start: str):
    """Get performance metrics for a specific week"""
    scheduler = NarrativeScheduler()
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        
        result = conn.execute(text("""
            SELECT id, schedule_id, total_posts, total_views, total_likes, 
                   total_comments, avg_engagement_rate, followers_gained, conversions,
                   goal_progress_pct, pillar_performance
            FROM schedule_performance WHERE week_start = :week_start
        """), {"week_start": week_start})
        
        row = result.fetchone()
        
        if not row:
            return {"message": "No performance data for this week", "week_start": week_start}
        
        return {
            "id": str(row[0]),
            "schedule_id": str(row[1]),
            "total_posts": row[2],
            "total_views": row[3],
            "total_likes": row[4],
            "total_comments": row[5],
            "avg_engagement_rate": row[6],
            "followers_gained": row[7],
            "conversions": row[8],
            "goal_progress_pct": row[9],
            "pillar_performance": json.loads(row[10]) if row[10] else {}
        }


@router.get("/learnings")
async def get_learnings(
    goal_id: Optional[str] = None,
    applied: Optional[bool] = None,
    limit: int = Query(20, le=100)
):
    """Get accumulated learnings"""
    scheduler = NarrativeScheduler()
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        
        query = "SELECT id, learning_type, insight, confidence, action, source_schedule_id, applied, created_at FROM learnings WHERE 1=1"
        params = {"limit": limit}
        
        if goal_id:
            query += " AND goal_id = :goal_id"
            params["goal_id"] = goal_id
        
        if applied is not None:
            query += " AND applied = :applied"
            params["applied"] = applied
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        
        result = conn.execute(text(query), params)
        
        learnings = []
        for row in result:
            learnings.append({
                "id": str(row[0]),
                "learning_type": row[1],
                "insight": row[2],
                "confidence": row[3],
                "action": row[4],
                "source_schedule_id": str(row[5]) if row[5] else None,
                "applied": row[6],
                "created_at": str(row[7]) if row[7] else None
            })
        
        return {"learnings": learnings, "total": len(learnings)}


@router.post("/reflect")
async def trigger_reflection(schedule_id: str):
    """Trigger reflection analysis for a completed schedule"""
    from services.narrative_scheduler.reflection_system import ReflectionSystem
    
    reflection_system = ReflectionSystem()
    
    try:
        reflection = await reflection_system.generate_weekly_reflection(schedule_id)
        return {
            "success": True,
            "reflection": reflection.to_dict()
        }
    except Exception as e:
        logger.error(f"[API] Reflection failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "schedule_id": schedule_id
        }


# =============================================================================
# WEEKLY AUTOMATION ENDPOINTS
# =============================================================================

@router.post("/automation/weekly-cycle")
async def trigger_full_weekly_cycle(goal_id: Optional[str] = None):
    """
    Trigger a full weekly automation cycle:
    1. Reflect on past week's performance
    2. Generate learnings
    3. Create new 7-day plan with learnings applied
    """
    from services.narrative_scheduler.weekly_automation import WeeklyAutomation
    
    automation = WeeklyAutomation()
    
    try:
        result = await automation.run_full_weekly_cycle(goal_id)
        return result
    except Exception as e:
        logger.error(f"[API] Weekly cycle failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/automation/reflect")
async def trigger_reflection_only():
    """Trigger weekly reflection without generating a new plan."""
    from services.narrative_scheduler.weekly_automation import WeeklyAutomation
    
    automation = WeeklyAutomation()
    
    try:
        result = await automation.run_weekly_reflection()
        return result
    except Exception as e:
        logger.error(f"[API] Reflection trigger failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/automation/generate-plan")
async def trigger_plan_generation(
    goal_id: Optional[str] = None,
    apply_learnings: bool = True
):
    """Generate next week's plan with optional learning application."""
    from services.narrative_scheduler.weekly_automation import WeeklyAutomation
    
    automation = WeeklyAutomation()
    
    try:
        result = await automation.generate_next_week_plan(
            goal_id=goal_id,
            apply_learnings=apply_learnings
        )
        return result
    except Exception as e:
        logger.error(f"[API] Plan generation trigger failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# CLIP SCHEDULING ENDPOINTS
# =============================================================================

@router.post("/clips/auto-schedule")
async def auto_schedule_clips(goal_id: Optional[str] = None):
    """
    Automatically schedule extracted clips based on narrative goals.
    
    1. Loads unscheduled extracted clips
    2. Classifies into narrative pillars
    3. Ranks by goal alignment
    4. Generates and saves schedule
    """
    from services.narrative_scheduler.clip_integration import ClipSchedulingIntegration
    
    integration = ClipSchedulingIntegration()
    
    try:
        result = await integration.auto_schedule_clips(goal_id)
        return result
    except Exception as e:
        logger.error(f"[API] Clip auto-scheduling failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/clips/unscheduled")
async def get_unscheduled_clips(limit: int = Query(20, le=50)):
    """Get extracted clips that haven't been scheduled yet."""
    from services.narrative_scheduler.clip_integration import ClipSchedulingIntegration
    
    integration = ClipSchedulingIntegration()
    
    try:
        clips = await integration.load_unscheduled_clips(min_relevance=0.3, limit=limit)
        return {
            "clips": [c.to_dict() for c in clips],
            "count": len(clips)
        }
    except Exception as e:
        logger.error(f"[API] Failed to load unscheduled clips: {e}")
        return {"clips": [], "count": 0, "error": str(e)}


@router.post("/clips/classify")
async def classify_clips(clip_ids: List[str] = None):
    """Classify clips into narrative pillars."""
    from services.narrative_scheduler.clip_integration import ClipSchedulingIntegration
    
    integration = ClipSchedulingIntegration()
    scheduler = NarrativeScheduler()
    
    try:
        # Load clips
        clips = await integration.load_unscheduled_clips(limit=50)
        
        if clip_ids:
            clips = [c for c in clips if c.id in clip_ids]
        
        # Load pillars
        pillars = scheduler._get_default_pillars()
        
        # Classify
        classified = await integration.classify_clips_into_pillars(clips, pillars)
        
        return {
            "classified": len(classified),
            "clips": [
                {
                    "id": c.id,
                    "pillar": c.pillar,
                    "confidence": c.pillar_confidence,
                    "text": c.text[:100]
                } for c in classified
            ]
        }
    except Exception as e:
        logger.error(f"[API] Clip classification failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# CONTENT ORCHESTRATION ENDPOINTS
# =============================================================================

@router.post("/orchestrate")
async def orchestrate_content(
    goal_id: Optional[str] = None,
    count: int = Query(7, le=14, description="Number of content pieces to generate")
):
    """
    Orchestrate content creation from narrative goals.
    
    Generates briefs, scripts, and clip plans based on narrative goals and pillars.
    """
    from services.narrative_scheduler.content_orchestration import NarrativeContentOrchestrator
    
    scheduler = NarrativeScheduler()
    orchestrator = NarrativeContentOrchestrator()
    
    try:
        # Load goal and pillars
        goal = await scheduler._load_goal(goal_id)
        if not goal:
            goal = scheduler._get_default_goal()
        
        pillars = await scheduler._load_pillars(goal.id) if goal_id else []
        if not pillars:
            pillars = scheduler._get_default_pillars()
        
        # Generate briefs
        briefs = await orchestrator.generate_content_briefs_from_goal(
            goal=goal,
            pillars=pillars,
            count=count
        )
        
        return {
            "success": True,
            "briefs_count": len(briefs),
            "briefs": [b.to_dict() for b in briefs],
            "goal": goal.goal_statement,
            "pillars": [p.name for p in pillars]
        }
    except Exception as e:
        logger.error(f"[API] Content orchestration failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/orchestrate/script")
async def generate_script_from_brief(brief_data: Dict[str, Any]):
    """Generate a video script from a content brief."""
    from services.narrative_scheduler.content_orchestration import (
        NarrativeContentOrchestrator, 
        ContentBriefFromNarrative
    )
    
    orchestrator = NarrativeContentOrchestrator()
    
    # Convert dict to brief
    brief = ContentBriefFromNarrative(
        narrative_goal_id=brief_data.get("narrative_goal_id", ""),
        pillar=brief_data.get("pillar", ""),
        topic=brief_data.get("topic", ""),
        hook=brief_data.get("hook", ""),
        key_points=brief_data.get("key_points", []),
        call_to_action=brief_data.get("call_to_action", ""),
        target_duration_seconds=brief_data.get("target_duration_seconds", 30),
        target_platforms=brief_data.get("target_platforms", ["tiktok"]),
        tone=brief_data.get("tone", "engaging"),
    )
    
    try:
        script = await orchestrator.convert_brief_to_script(brief)
        return {
            "success": True,
            "script": script,
            "brief_id": brief.id
        }
    except Exception as e:
        logger.error(f"[API] Script generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# VIDEO GENERATION BRIDGE ENDPOINTS
# =============================================================================

@router.post("/video/generate")
async def generate_video_content(
    goal_statement: str = "Build engagement and grow following",
    pillar: str = "Process/How-To",
    primary_cta: str = "follow",
    target_audience: str = "general",
    target_duration: int = 30
):
    """
    Generate video content from narrative goal.
    
    Full pipeline: goal → brief → script → clip plan → provider payloads
    """
    try:
        from services.video_orchestrator.narrative_bridge import NarrativeVideoBridge
        
        bridge = NarrativeVideoBridge()
        
        result = await bridge.full_generation_pipeline(
            goal_statement=goal_statement,
            pillar=pillar,
            primary_cta=primary_cta,
            target_audience=target_audience,
            target_duration=target_duration
        )
        
        return {
            "success": True,
            "content": result.to_dict(),
            "script": result.script,
            "clips_count": len(result.clips),
            "total_duration": result.total_duration_seconds
        }
    except Exception as e:
        logger.error(f"[API] Video generation failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/video/script")
async def generate_video_script(
    topic: str,
    hook: str = "",
    key_points: List[str] = None,
    call_to_action: str = "Follow for more!",
    tone: str = "engaging",
    target_duration: int = 30
):
    """Generate a video script from topic and key points."""
    try:
        from services.video_orchestrator.narrative_bridge import (
            NarrativeVideoBridge, 
            NarrativeVideoBrief
        )
        
        bridge = NarrativeVideoBridge()
        
        brief = NarrativeVideoBrief(
            topic=topic,
            hook=hook or f"Here's something about {topic}...",
            key_points=key_points or ["Key insight 1", "Key insight 2"],
            call_to_action=call_to_action,
            tone=tone,
            target_duration_seconds=target_duration
        )
        
        script = await bridge.generate_script_from_brief(brief)
        
        return {
            "success": True,
            "script": script,
            "brief": brief.to_dict()
        }
    except Exception as e:
        logger.error(f"[API] Script generation failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# TEMPLATE ENDPOINTS
# =============================================================================

@router.get("/templates")
async def get_templates():
    """Get available templates for goals, pillars, and constraints"""
    import os
    import json
    
    template_path = os.path.join(
        os.path.dirname(__file__), 
        "../../docs/narrative_scheduler_test_templates.json"
    )
    
    # Try alternative path
    if not os.path.exists(template_path):
        template_path = "/Users/isaiahdupree/Documents/Software/MediaPoster/docs/narrative_scheduler_test_templates.json"
    
    try:
        with open(template_path, 'r') as f:
            templates = json.load(f)
        return templates
    except FileNotFoundError:
        return {"error": "Templates file not found"}


@router.post("/templates/apply/{template_id}")
async def apply_template(template_id: str):
    """Apply a template to create goal, pillars, and constraints"""
    # Load template and create goal/pillars/constraints
    return {
        "message": f"Template {template_id} applied",
        "status": "success"
    }


# =============================================================================
# AUTONOMOUS NARRATIVE PLANNER ENDPOINTS
# =============================================================================

@router.get("/autonomous/status")
async def get_autonomous_planner_status():
    """
    Get status of the autonomous narrative planner.
    Shows readiness, current draft, and reasoning chain.
    """
    from services.narrative_scheduler.autonomous_planner import get_planner
    
    planner = get_planner()
    
    try:
        status = await planner.get_status()
        return {"success": True, **status}
    except Exception as e:
        logger.error(f"[API] Autonomous status error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/autonomous/run-cycle")
async def run_autonomous_cycle():
    """
    Manually trigger one autonomous planning cycle.
    The planner will analyze content and generate a draft plan if ready.
    """
    from services.narrative_scheduler.autonomous_planner import get_planner
    
    planner = get_planner()
    
    try:
        status = await planner.run_once()
        return {"success": True, "message": "Cycle completed", **status}
    except Exception as e:
        logger.error(f"[API] Autonomous cycle error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/autonomous/draft")
async def get_draft_plan():
    """
    Get the current draft plan awaiting human approval.
    Returns full plan details including days, posts, and reasoning.
    """
    from services.narrative_scheduler.autonomous_planner import get_planner
    
    planner = get_planner()
    
    try:
        draft = await planner.get_draft_plan()
        if draft:
            return {"success": True, "draft": draft}
        return {"success": True, "draft": None, "message": "No draft plan available"}
    except Exception as e:
        logger.error(f"[API] Get draft error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/autonomous/approve")
async def approve_draft_plan(plan_id: Optional[str] = None):
    """
    HUMAN APPROVAL: Approve the current draft plan.
    Only after approval will the plan be eligible for scheduling.
    """
    from services.narrative_scheduler.autonomous_planner import get_planner
    
    planner = get_planner()
    
    try:
        result = await planner.approve_plan(plan_id)
        return result
    except Exception as e:
        logger.error(f"[API] Approve plan error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/autonomous/reject")
async def reject_draft_plan(plan_id: Optional[str] = None, reason: str = ""):
    """
    HUMAN REJECTION: Reject the current draft plan.
    Planner will generate a new plan on next cycle.
    """
    from services.narrative_scheduler.autonomous_planner import get_planner
    
    planner = get_planner()
    
    try:
        result = await planner.reject_plan(plan_id, reason)
        return result
    except Exception as e:
        logger.error(f"[API] Reject plan error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/autonomous/schedule-approved")
async def schedule_approved_plan():
    """
    Schedule the approved plan.
    This ONLY works after human approval - posts are created in scheduled_posts table.
    """
    from services.narrative_scheduler.autonomous_planner import get_planner
    
    planner = get_planner()
    
    try:
        result = await planner.schedule_approved_plan()
        return result
    except Exception as e:
        logger.error(f"[API] Schedule approved error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/autonomous/readiness")
async def check_plan_readiness():
    """
    Check if there's enough content to generate a 7-day plan.
    Returns detailed readiness metrics and missing requirements.
    """
    from services.narrative_scheduler.autonomous_planner import get_planner
    
    planner = get_planner()
    
    try:
        readiness = await planner.check_readiness()
        return {
            "success": True,
            "is_ready": readiness.is_ready,
            "readiness_score": readiness.readiness_score,
            "metrics": {
                "analyzed_videos": readiness.analyzed_videos,
                "high_performers": readiness.high_performers,
                "active_pillars": readiness.active_pillars,
                "candidates_available": readiness.candidates_available
            },
            "missing_requirements": readiness.missing_requirements
        }
    except Exception as e:
        logger.error(f"[API] Readiness check error: {e}")
        return {"success": False, "error": str(e)}
