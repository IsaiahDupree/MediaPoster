"""
Narrative Scheduler API Endpoints
=================================
Endpoints for viewing reasoning chains and AI decision-making process.
"""

import json
from fastapi import APIRouter, HTTPException
from services.narrative_scheduler import NarrativeScheduler

router = APIRouter(prefix="/api/narrative", tags=["Narrative Scheduler"])


@router.get("/reasoning/{goal_id}")
async def get_reasoning_chain(goal_id: str):
    """
    Get the current reasoning chain and thoughts for a goal.
    Returns real-time AI decision-making process.
    """
    scheduler = NarrativeScheduler()
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        
        # Get the latest plan for this goal
        plan_result = conn.execute(text("""
            SELECT id, reasoning_chain, justification_summary, status, updated_at
            FROM weekly_schedules
            WHERE goal_id = :goal_id
            ORDER BY created_at DESC
            LIMIT 1
        """), {"goal_id": goal_id})
        
        plan_row = plan_result.fetchone()
        
        if plan_row:
            reasoning_chain = json.loads(plan_row[1]) if plan_row[1] else []
            return {
                "goal_id": goal_id,
                "plan_id": str(plan_row[0]),
                "reasoning_chain": reasoning_chain,
                "justification_summary": plan_row[2],
                "status": plan_row[3],
                "last_updated": str(plan_row[4]) if plan_row[4] else None,
                "current_thought": reasoning_chain[-1] if reasoning_chain else None,
            }
        
        # If no plan exists, check if there's an active planning process
        # This could be enhanced to track real-time planning state
        return {
            "goal_id": goal_id,
            "plan_id": None,
            "reasoning_chain": [],
            "justification_summary": None,
            "status": "no_plan",
            "last_updated": None,
            "current_thought": {
                "step": 0,
                "thought": "No plan generated yet. Click 'Generate 7-Day Plan' to start.",
                "decision": "Waiting for plan generation",
                "confidence": 0.0
            }
        }


@router.get("/reasoning/live/{goal_id}")
async def get_live_reasoning(goal_id: str):
    """
    Get live reasoning updates during plan generation.
    This endpoint can be polled to get real-time thoughts.
    """
    # Check if there's an active plan generation in progress
    # This would ideally be stored in Redis or similar for real-time updates
    scheduler = NarrativeScheduler()
    
    # For now, return the latest reasoning chain
    # In production, this could be enhanced with Redis pub/sub or WebSocket
    return await get_reasoning_chain(goal_id)
