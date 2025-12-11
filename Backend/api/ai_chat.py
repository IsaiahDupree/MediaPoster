"""
AI Chat API - Chat with all MediaPoster data
Provides conversational AI interface to query analytics, media, schedules, and insights
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

router = APIRouter(prefix="/api/ai-chat", tags=["AI Chat"])


class DataSource(BaseModel):
    """Reference to data used in response"""
    type: str  # 'media', 'analytics', 'schedule', 'coaching', 'insights'
    title: str
    id: Optional[str] = None
    relevance: int  # 0-100


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: Optional[datetime] = None
    sources: Optional[List[DataSource]] = None


class ChatRequest(BaseModel):
    """Request for chat completion"""
    message: str
    context: str = "all"  # 'all', 'media', 'analytics', 'schedule', 'coaching'
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Response from AI chat"""
    message: str
    sources: List[DataSource]
    suggested_actions: Optional[List[Dict[str, str]]] = None


class DataContext(BaseModel):
    """Available data context for chat"""
    id: str
    label: str
    description: str
    item_count: int


# Data aggregation functions
async def get_media_context() -> Dict[str, Any]:
    """Get summary of media library for AI context"""
    # In production, this would query the actual database
    return {
        "total_items": 47,
        "analyzed": 42,
        "pending": 5,
        "top_scores": [
            {"title": "Arduino Tutorial", "score": 92},
            {"title": "ESP32 Project", "score": 88},
            {"title": "LED Matrix Build", "score": 85},
        ],
        "content_types": {
            "tutorials": 18,
            "behind_scenes": 12,
            "product_shots": 10,
            "lifestyle": 7,
        },
        "avg_score": 78.5,
    }


async def get_analytics_context() -> Dict[str, Any]:
    """Get analytics summary for AI context"""
    return {
        "period": "last_30_days",
        "total_views": 156000,
        "total_engagement": 12400,
        "engagement_rate": 7.9,
        "follower_growth": 2847,
        "growth_rate": 8.3,
        "top_platform": "instagram",
        "best_performing_day": "Tuesday",
        "best_time": "7:00 PM - 9:00 PM",
        "top_content_type": "tutorials",
        "audience": {
            "age_25_34": 45,
            "age_18_24": 30,
            "age_35_44": 15,
            "top_country": "USA",
            "mobile_percent": 78,
        },
    }


async def get_schedule_context() -> Dict[str, Any]:
    """Get schedule summary for AI context"""
    return {
        "scheduled_posts": 12,
        "next_post": "2024-01-20T10:00:00",
        "posts_this_week": 8,
        "platforms": {
            "instagram": 5,
            "tiktok": 4,
            "youtube": 3,
        },
        "optimal_times": [
            {"day": "Tuesday", "time": "7:00 PM", "engagement_boost": 14},
            {"day": "Thursday", "time": "12:00 PM", "engagement_boost": 11},
            {"day": "Saturday", "time": "10:00 AM", "engagement_boost": 9},
        ],
    }


async def get_coaching_context() -> Dict[str, Any]:
    """Get coaching insights for AI context"""
    return {
        "active_recommendations": 5,
        "completed_recommendations": 12,
        "improvement_areas": [
            "posting_frequency",
            "hashtag_strategy",
            "engagement_response",
        ],
        "strengths": [
            "content_quality",
            "visual_consistency",
            "tutorial_format",
        ],
        "current_goals": [
            {"goal": "Increase engagement rate to 10%", "progress": 79},
            {"goal": "Post 5x per week consistently", "progress": 60},
            {"goal": "Grow followers by 5000", "progress": 57},
        ],
    }


async def build_context_prompt(context: str) -> str:
    """Build context-aware system prompt"""
    media_ctx = await get_media_context()
    analytics_ctx = await get_analytics_context()
    schedule_ctx = await get_schedule_context()
    coaching_ctx = await get_coaching_context()
    
    context_data = {
        "media": media_ctx if context in ["all", "media"] else None,
        "analytics": analytics_ctx if context in ["all", "analytics"] else None,
        "schedule": schedule_ctx if context in ["all", "schedule"] else None,
        "coaching": coaching_ctx if context in ["all", "coaching"] else None,
    }
    
    return f"""You are an AI assistant for MediaPoster, a social media management platform.
You have access to the following user data:

MEDIA LIBRARY:
{json.dumps(context_data.get('media'), indent=2) if context_data.get('media') else 'Not available in current context'}

ANALYTICS:
{json.dumps(context_data.get('analytics'), indent=2) if context_data.get('analytics') else 'Not available in current context'}

SCHEDULE:
{json.dumps(context_data.get('schedule'), indent=2) if context_data.get('schedule') else 'Not available in current context'}

COACHING:
{json.dumps(context_data.get('coaching'), indent=2) if context_data.get('coaching') else 'Not available in current context'}

Use this data to provide helpful, specific, and actionable responses.
Always cite which data sources you're using in your response.
Be conversational but professional.
If asked about something outside the available data, acknowledge the limitation.
"""


def determine_sources(message: str, response: str) -> List[DataSource]:
    """Determine which data sources were used for the response"""
    sources = []
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['performance', 'views', 'engagement', 'growth', 'analytics']):
        sources.append(DataSource(
            type="analytics",
            title="Performance Analytics",
            relevance=95
        ))
    
    if any(word in message_lower for word in ['content', 'video', 'media', 'library', 'upload']):
        sources.append(DataSource(
            type="media",
            title="Media Library",
            relevance=90
        ))
    
    if any(word in message_lower for word in ['schedule', 'post', 'when', 'time', 'calendar']):
        sources.append(DataSource(
            type="schedule",
            title="Content Schedule",
            relevance=88
        ))
    
    if any(word in message_lower for word in ['suggest', 'recommend', 'improve', 'tips', 'strategy', 'coach']):
        sources.append(DataSource(
            type="coaching",
            title="AI Coaching Insights",
            relevance=92
        ))
    
    if any(word in message_lower for word in ['audience', 'follower', 'demographic', 'who']):
        sources.append(DataSource(
            type="insights",
            title="Audience Insights",
            relevance=91
        ))
    
    # Default source if none matched
    if not sources:
        sources.append(DataSource(
            type="analytics",
            title="General Data",
            relevance=75
        ))
    
    return sources


@router.get("/contexts")
async def get_available_contexts() -> List[DataContext]:
    """Get list of available data contexts for chat"""
    media_ctx = await get_media_context()
    analytics_ctx = await get_analytics_context()
    schedule_ctx = await get_schedule_context()
    coaching_ctx = await get_coaching_context()
    
    return [
        DataContext(
            id="all",
            label="All Data",
            description="Search across all your data",
            item_count=media_ctx["total_items"] + schedule_ctx["scheduled_posts"]
        ),
        DataContext(
            id="media",
            label="Media Library",
            description="Videos, images, and content",
            item_count=media_ctx["total_items"]
        ),
        DataContext(
            id="analytics",
            label="Analytics",
            description="Performance metrics and insights",
            item_count=30  # Days of data
        ),
        DataContext(
            id="schedule",
            label="Schedule",
            description="Scheduled and past posts",
            item_count=schedule_ctx["scheduled_posts"]
        ),
        DataContext(
            id="coaching",
            label="Coaching",
            description="AI recommendations and tips",
            item_count=coaching_ctx["active_recommendations"]
        ),
    ]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message and return AI response
    
    In production, this would:
    1. Build context from actual database
    2. Send to LLM (OpenAI, Claude, etc.)
    3. Parse and return structured response
    """
    message = request.message.lower()
    
    # Build context-aware response
    # In production, this would call an actual LLM
    
    if "best performing" in message or "top content" in message:
        response_text = """Based on your analytics data, here are your top performing content pieces:

**1. "Arduino Tutorial Series" (Pre-Social Score: 92)**
- 45K views, 12% engagement rate
- Key factors: Clear hook, educational value, trending topic

**2. "Behind the Scenes: Studio Setup" (Pre-Social Score: 88)**
- 32K views, 15% engagement rate  
- Key factors: Authentic content, curiosity gap

**3. "Quick Tips: Soldering Basics" (Pre-Social Score: 85)**
- 28K views, 10% engagement rate
- Key factors: Short format, practical value

💡 **Recommendation:** Your tutorial content consistently outperforms. Consider a weekly tutorial series."""
        
    elif "best time" in message or "when to post" in message:
        response_text = """Based on your audience engagement patterns:

**Instagram:**
- 🌅 Morning: 7-9 AM (14% higher engagement)
- 🌙 Evening: 7-9 PM (Peak engagement)

**TikTok:**
- 📱 Afternoon: 12-3 PM (Best for tutorials)
- 🌃 Night: 9-11 PM (Highest reach)

**Key Insight:** Your audience is most active on weekday evenings (7-9 PM)."""
        
    elif "audience" in message or "follower" in message:
        response_text = """Here's your audience breakdown:

**Demographics:**
- 👤 Age: 25-34 (45%), 18-24 (30%), 35-44 (15%)
- 🌍 Top Countries: USA (42%), UK (18%), Canada (12%)
- 📱 Device: Mobile (78%), Desktop (22%)

**Top Interests:**
1. DIY Electronics & Maker Projects
2. Home Automation
3. Tech Reviews"""
        
    elif "suggest" in message or "content idea" in message or "create" in message:
        response_text = """Based on your performance data, here are content recommendations:

**🔥 High-Potential Ideas:**

1. **"5 Common Arduino Mistakes"** - Predicted Score: 90+
2. **"Smart Mirror Build Challenge"** - Predicted Score: 88
3. **"ESP32 WiFi Guide"** - Predicted Score: 85

**Trending in Your Niche:**
- AI/ML with microcontrollers
- Solar/sustainable tech
- Voice-controlled home automation"""
        
    elif "growth" in message:
        response_text = """Your growth analysis for the past 30 days:

**📊 Follower Growth:** +2,847 (+8.3%)
- Best Day: Tuesday (avg. +156)

**🎯 Growth Drivers:**
1. Tutorial Content: 45% of new followers
2. Cross-Platform: TikTok → Instagram driving 23%

**🚀 Recommendations:**
- Increase tutorial output by 1 post/week
- Add stronger CTAs in video endings
- Consider 2-3 creator collaborations"""
        
    else:
        # Default response
        analytics = await get_analytics_context()
        media = await get_media_context()
        
        response_text = f"""I've analyzed your MediaPoster data:

**Summary:**
- 📹 Content Library: {media['total_items']} items (avg score: {media['avg_score']})
- 📊 Monthly Views: {analytics['total_views']:,}
- 📈 Growth Rate: +{analytics['growth_rate']}%
- 🎯 Engagement Rate: {analytics['engagement_rate']}%

What would you like to know more about?
- Content performance
- Scheduling optimization  
- Audience insights
- Growth strategies"""
    
    sources = determine_sources(request.message, response_text)
    
    return ChatResponse(
        message=response_text,
        sources=sources,
        suggested_actions=[
            {"label": "View Analytics", "url": "/analytics"},
            {"label": "See Schedule", "url": "/schedule"},
            {"label": "Get Coaching", "url": "/coaching"},
        ]
    )


@router.get("/quick-prompts")
async def get_quick_prompts() -> List[Dict[str, str]]:
    """Get suggested quick prompts for the chat"""
    return [
        {"icon": "🏆", "label": "Best performing content", "prompt": "What is my best performing content this month and why?"},
        {"icon": "💡", "label": "Content suggestions", "prompt": "Based on my analytics, what type of content should I create next?"},
        {"icon": "📅", "label": "Schedule optimization", "prompt": "What are the best times to post based on my audience engagement?"},
        {"icon": "🔥", "label": "Trending topics", "prompt": "What topics are trending in my niche that I should cover?"},
        {"icon": "👥", "label": "Audience insights", "prompt": "Tell me about my audience demographics and behavior patterns."},
        {"icon": "📈", "label": "Growth analysis", "prompt": "How has my follower growth been and what can I do to improve?"},
    ]
