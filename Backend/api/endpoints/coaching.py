"""
AI Coaching API Endpoints
Phase 3: Pre/Post Social Score + Coaching
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from services.coaching_service import CoachingService
from services.event_bus import EventBus, Topics
from loguru import logger

router = APIRouter(prefix="/api/coaching", tags=["Coaching"])


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    message: str
    recommendations: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None


@router.get("/recommendations")
async def get_coaching_recommendations(
    goal_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized coaching recommendations
    
    Returns:
    - Content brief recommendations
    - Script suggestions
    - Performance insights
    - Strategy recommendations
    """
    try:
        # Mock user_id for now (would come from auth)
        user_id = "00000000-0000-0000-0000-000000000000"
        
        context = {}
        if goal_id:
            context['goal_id'] = goal_id
        
        service = CoachingService()
        recommendations = await service.get_coaching_recommendations(
            db=db,
            user_id=user_id,
            context=context
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting coaching recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_with_coach(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with AI coach
    
    Provides conversational coaching based on user questions
    """
    try:
        # Mock user_id for now
        user_id = "00000000-0000-0000-0000-000000000000"
        
        service = CoachingService()
        
        # Get recommendations based on context
        recommendations = await service.get_coaching_recommendations(
            db=db,
            user_id=user_id,
            context=request.context or {}
        )
        
        # Simple response generation (would use LLM in production)
        message_lower = request.message.lower()
        
        if 'brief' in message_lower or 'content idea' in message_lower:
            response = "Based on your performance, I recommend creating content similar to your top performers. "
            if recommendations.get('content_briefs'):
                brief = recommendations['content_briefs'][0]
                response += f"Try: {brief['title']} - {brief['description']}"
            else:
                response += "Focus on educational content with strong hooks in the first 3 seconds."
        
        elif 'script' in message_lower or 'what to say' in message_lower:
            response = "Here's an optimal script structure: "
            if recommendations.get('script_suggestions'):
                script = recommendations['script_suggestions'][0]
                if 'structure' in script:
                    response += " ".join(script['structure'])
            else:
                response += "Hook (0-3s) → Problem (3-10s) → Solution (10-45s) → CTA (45-60s)"
        
        elif 'strategy' in message_lower or 'how to improve' in message_lower:
            response = "Based on your analytics: "
            if recommendations.get('strategy_recommendations'):
                strategy = recommendations['strategy_recommendations'][0]
                response += f"{strategy['title']} - {strategy['description']}"
            else:
                response += "Post consistently 3-5 times per week and engage with comments."
        
        elif 'performance' in message_lower or 'how am i doing' in message_lower:
            response = "Your recent performance insights: "
            if recommendations.get('performance_insights'):
                insight = recommendations['performance_insights'][0]
                response += f"{insight['title']} - {insight['description']}"
            else:
                response += "Keep creating content and track your metrics."
        
        else:
            response = "I can help you with content briefs, script suggestions, performance insights, and strategy recommendations. What would you like to know?"
        
        # Emit COACHING_SESSION_STARTED event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.COACH_INSIGHT_GENERATED, {
                "user_id": user_id,
                "message_type": "chat",
                "context": request.context,
            })
            logger.info(f"[PubSub] Emitted COACH_INSIGHT_GENERATED")
        except Exception as e:
            logger.warning(f"[PubSub] Failed to emit coaching event: {e}")
        
        return ChatResponse(
            message=response,
            recommendations=recommendations,
            suggestions=[
                "What content should I create next?",
                "Help me write a script",
                "How can I improve my performance?",
                "What's my best performing content?"
            ]
        )
        
    except Exception as e:
        logger.error(f"Error in coaching chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_coaching_insights(
    db: AsyncSession = Depends(get_db)
):
    """
    Get coaching insights for the coaching page
    
    Returns actionable insights and recommendations
    """
    try:
        # Mock user_id for now
        user_id = "00000000-0000-0000-0000-000000000000"
        
        service = CoachingService()
        
        # Get recommendations
        recommendations = await service.get_coaching_recommendations(
            db=db,
            user_id=user_id,
            context={}
        )
        
        # Format as insights array
        insights = []
        
        # Add content brief recommendations as tips
        if recommendations.get('content_briefs'):
            for brief in recommendations['content_briefs'][:3]:
                insights.append({
                    'type': 'tip',
                    'title': brief.get('title', 'Content Recommendation'),
                    'message': brief.get('description', 'Consider creating this type of content'),
                    'priority': 1,
                    'created_at': datetime.now().isoformat()
                })
        
        # Add script suggestions as tips
        if recommendations.get('script_suggestions'):
            for script in recommendations['script_suggestions'][:2]:
                insights.append({
                    'type': 'tip',
                    'title': 'Script Structure',
                    'message': script.get('description', 'Optimize your script structure for better engagement'),
                    'priority': 2,
                    'created_at': datetime.now().isoformat()
                })
        
        # Add performance insights
        if recommendations.get('performance_insights'):
            for insight in recommendations['performance_insights'][:3]:
                insights.append({
                    'type': 'celebration' if 'good' in insight.get('title', '').lower() or 'great' in insight.get('title', '').lower() else 'tip',
                    'title': insight.get('title', 'Performance Insight'),
                    'message': insight.get('description', 'Keep up the good work'),
                    'priority': 1,
                    'created_at': datetime.now().isoformat()
                })
        
        # Add strategy recommendations as actions
        if recommendations.get('strategy_recommendations'):
            for strategy in recommendations['strategy_recommendations'][:2]:
                insights.append({
                    'type': 'action',
                    'title': strategy.get('title', 'Strategy Recommendation'),
                    'message': strategy.get('description', 'Consider implementing this strategy'),
                    'priority': 1,
                    'created_at': datetime.now().isoformat()
                })
        
        # If no insights, provide default ones
        if not insights:
            insights = [
                {
                    'type': 'tip',
                    'title': 'Get Started',
                    'message': 'Start creating content consistently to build your audience',
                    'priority': 1,
                    'created_at': datetime.now().isoformat()
                },
                {
                    'type': 'tip',
                    'title': 'Engage with Comments',
                    'message': 'Responding to comments helps build community and increases engagement',
                    'priority': 2,
                    'created_at': datetime.now().isoformat()
                }
            ]
        
        return {'insights': insights}
        
    except Exception as e:
        logger.error(f"Error getting coaching insights: {e}")
        # Return default insights instead of 500 error
        from datetime import datetime
        return {
            'insights': [
                {
                    'type': 'tip',
                    'title': 'Welcome',
                    'message': 'Start creating content to see personalized insights',
                    'priority': 1,
                    'created_at': datetime.now().isoformat()
                }
            ]
        }








