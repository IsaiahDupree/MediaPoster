from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel

from services.segment_engine import SegmentInsightResponse

class ContentBrief(BaseModel):
    id: UUID
    segment_id: UUID
    topic: str
    angle: str
    target_platforms: List[str]
    format_suggestions: Dict[str, str] # e.g. {'tiktok': 'skit', 'linkedin': 'carousel'}
    key_talking_points: List[str]
    estimated_reach: str
    rationale: str
    created_at: datetime

async def generate_briefs_for_segment(
    segment_id: UUID, 
    insights: SegmentInsightResponse
) -> List[ContentBrief]:
    """
    Generate content briefs based on segment insights.
    This simulates an AI analyzing the segment's top topics and platforms
    to suggest high-performing content ideas.
    """
    
    # Mock AI Logic
    # In production, this would use an LLM with the insights as context
    
    briefs = []
    
    # Idea 1: Based on top topic
    if insights.top_topics:
        top_topic = insights.top_topics[0]
        briefs.append(ContentBrief(
            id=uuid4(),
            segment_id=segment_id,
            topic=f"The Future of {top_topic}",
            angle="Contrarian take - why everyone is wrong",
            target_platforms=["linkedin", "twitter"],
            format_suggestions={
                "linkedin": "Text-only post with hook",
                "twitter": "Thread breakdown"
            },
            key_talking_points=[
                "Common misconception 1",
                "Why the data says otherwise",
                "Actionable step for leaders"
            ],
            estimated_reach="High (Top Interest)",
            rationale=f"Leverages high interest in {top_topic} with a strong hook.",
            created_at=datetime.now()
        ))
        
    # Idea 2: Based on best platform
    best_platform = max(insights.top_platforms, key=insights.top_platforms.get) if insights.top_platforms else "instagram"
    
    briefs.append(ContentBrief(
        id=uuid4(),
        segment_id=segment_id,
        topic="Behind the Scenes",
        angle="Authentic / Day in the Life",
        target_platforms=[best_platform, "instagram"],
        format_suggestions={
            best_platform: "Short-form video (Reel/TikTok)",
            "instagram": "Stories + Reel"
        },
        key_talking_points=[
            "Show the messy process",
            "One win from today",
            "One struggle"
        ],
        estimated_reach="Medium (High Engagement)",
        rationale=f"Optimized for {best_platform} where this segment is most active.",
        created_at=datetime.now()
    ))
    
    return briefs
