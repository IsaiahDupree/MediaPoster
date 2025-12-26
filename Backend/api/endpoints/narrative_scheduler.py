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


@router.get("/weekly-schedules")
async def get_weekly_schedules():
    """
    Get all weekly schedules/plans history.
    Returns list of generated plans with their status.
    """
    scheduler = NarrativeScheduler()
    
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        
        # First check if weekly_schedules table exists
        try:
            result = conn.execute(text("""
                SELECT 
                    ws.id,
                    ws.goal_id,
                    ws.status,
                    ws.justification_summary,
                    ws.created_at,
                    ws.updated_at
                FROM weekly_schedules ws
                ORDER BY ws.created_at DESC
                LIMIT 20
            """))
        except Exception:
            # Table doesn't exist yet
            return {"schedules": [], "total": 0}
        
        schedules = []
        for row in result:
            schedules.append({
                "id": str(row[0]),
                "goal_id": str(row[1]) if row[1] else None,
                "status": row[2],
                "justification_summary": row[3],
                "created_at": str(row[4]) if row[4] else None,
                "updated_at": str(row[5]) if row[5] else None,
            })
        
        return {"schedules": schedules, "total": len(schedules)}


@router.post("/suggest-goal")
async def suggest_goal():
    """
    Use AI to suggest a content goal based on current signals and performance.
    Makes a real OpenAI API call to generate personalized suggestions.
    """
    import os
    import openai
    from datetime import datetime
    
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    scheduler = NarrativeScheduler()
    
    # Gather context for AI
    with scheduler.engine.connect() as conn:
        from sqlalchemy import text
        
        # Get recent posting stats
        stats_result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_posts,
                COUNT(CASE WHEN platform = 'tiktok' THEN 1 END) as tiktok_posts,
                COUNT(CASE WHEN platform = 'instagram' THEN 1 END) as ig_posts,
                COUNT(CASE WHEN platform = 'youtube' THEN 1 END) as yt_posts
            FROM scheduled_posts
            WHERE scheduled_time > NOW() - INTERVAL '30 days'
            AND status = 'published'
        """))
        stats = stats_result.fetchone()
        
        # Get top performing topics
        try:
            topics_result = conn.execute(text("""
                SELECT unnest(topics) as topic, COUNT(*) as cnt
                FROM video_analysis
                WHERE analyzed_at > NOW() - INTERVAL '30 days'
                GROUP BY topic
                ORDER BY cnt DESC
                LIMIT 5
            """))
            top_topics = [row[0] for row in topics_result]
        except Exception:
            top_topics = []
        
        # Get content inventory (total analyzed content)
        try:
            inventory_result = conn.execute(text("""
                SELECT COUNT(*) FROM video_analysis
            """))
            unused_content = inventory_result.scalar() or 0
        except Exception:
            unused_content = 0
    
    # Build prompt for OpenAI
    prompt = f"""You are a social media content strategist. Based on the following data, suggest ONE specific, actionable content goal for the next 7 days.

Current Stats (last 30 days):
- Total posts published: {stats[0] if stats else 0}
- TikTok posts: {stats[1] if stats else 0}
- Instagram posts: {stats[2] if stats else 0}
- YouTube posts: {stats[3] if stats else 0}

Top Content Topics: {', '.join(top_topics) if top_topics else 'No data yet'}
Unused Content Available: {unused_content} pieces

Today's Date: {datetime.now().strftime('%B %d, %Y')}

Respond in JSON format with these fields:
{{
    "goal": "A specific, measurable goal statement",
    "rationale": "Why this goal makes sense based on the data",
    "suggested_pillars": ["pillar1", "pillar2", "pillar3"],
    "recommended_platforms": ["platform1", "platform2"],
    "posts_per_day": 2,
    "content_mix": {{"educational": 40, "entertaining": 30, "promotional": 20, "community": 10}}
}}"""

    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a social media strategist. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        suggestion_text = response.choices[0].message.content
        # Parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', suggestion_text)
        if json_match:
            suggestion = json.loads(json_match.group())
        else:
            suggestion = {"goal": suggestion_text, "rationale": "AI-generated suggestion"}
        
        return {
            "success": True,
            "suggestion": suggestion,
            "context": {
                "total_posts_30d": stats[0] if stats else 0,
                "top_topics": top_topics,
                "unused_content": unused_content
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI suggestion failed: {str(e)}")
