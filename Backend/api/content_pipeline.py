"""
Content Pipeline API
Handles automated content sourcing, analysis, approval, scheduling, and publishing.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import random

router = APIRouter(prefix="/api/content-pipeline", tags=["Content Pipeline"])


# ============================================================================
# ENUMS & MODELS
# ============================================================================

class ContentStatus(str, Enum):
    PENDING_ANALYSIS = "pending_analysis"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    REJECTED = "rejected"
    SAVED_FOR_LATER = "saved_for_later"


class SwipeAction(str, Enum):
    APPROVE = "approve"  # Right swipe
    REJECT = "reject"    # Left swipe
    PRIORITY = "priority"  # Up swipe - approve with high priority
    SAVE_LATER = "save_later"  # Down swipe


class ContentVariation(BaseModel):
    id: str
    title: str
    description: str
    hashtags: List[str] = []
    call_to_action: Optional[str] = None
    platform_hint: Optional[str] = None
    is_primary: bool = False
    times_used: int = 0


class PlatformAssignment(BaseModel):
    platform: str
    account_id: Optional[int] = None
    account_username: Optional[str] = None
    match_score: float = 0
    match_reasons: List[str] = []
    status: str = "suggested"


class ContentItem(BaseModel):
    id: str
    media_id: Optional[str] = None
    source_type: str = "media_library"
    status: str = ContentStatus.PENDING_APPROVAL
    quality_score: int = 0
    niche: Optional[str] = None
    content_type: str = "image"
    duration_sec: Optional[float] = None
    resolution: Optional[str] = None
    aspect_ratio: Optional[str] = None
    thumbnail_url: Optional[str] = None
    ai_analysis: Dict[str, Any] = {}
    variations: List[ContentVariation] = []
    platform_assignments: List[PlatformAssignment] = []
    priority: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class ApproveRequest(BaseModel):
    content_id: str
    action: SwipeAction
    selected_platforms: Optional[List[str]] = None
    selected_variation_id: Optional[str] = None
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    priority: int = 0


class ScheduleRequest(BaseModel):
    content_id: str
    platform: str
    account_id: Optional[int] = None
    scheduled_time: datetime
    variation_id: Optional[str] = None


class RunwayStats(BaseModel):
    total_approved: int
    total_scheduled: int
    total_pending: int
    total_saved_for_later: int
    days_of_runway: int
    runway_by_platform: Dict[str, int]
    posts_today: int
    posts_this_week: int
    content_by_niche: Dict[str, int]
    low_runway_platforms: List[str]
    

# ============================================================================
# MOCK DATA GENERATORS
# ============================================================================

NICHES = ["lifestyle", "fitness", "comedy", "education", "tech", "travel", "food", "fashion", "gaming", "motivation"]
PLATFORMS = ["instagram", "tiktok", "youtube", "twitter", "linkedin", "threads"]
MOODS = ["happy", "energetic", "calm", "inspiring", "funny", "serious", "casual"]

def generate_mock_variations(niche: str, content_type: str) -> List[ContentVariation]:
    """Generate AI-powered title/description variations"""
    templates = {
        "lifestyle": [
            ("Living my best life ✨", "Every day is a new adventure. What's your vibe today?"),
            ("This is the moment 🌟", "Sometimes you just have to stop and appreciate the little things."),
            ("Vibes only 💫", "Life's too short for anything less than amazing."),
        ],
        "fitness": [
            ("No excuses 💪", "Push yourself because no one else is going to do it for you."),
            ("Workout complete ✅", "Another day, another step closer to my goals."),
            ("Grind time 🏋️", "The only bad workout is the one that didn't happen."),
        ],
        "comedy": [
            ("Wait for it... 😂", "POV: When life gives you lemons..."),
            ("This one got me 💀", "I can't believe this actually happened."),
            ("The accuracy tho 😭", "Tell me why this is so relatable."),
        ],
        "travel": [
            ("Found paradise 🌴", "This place is absolutely unreal. Adding to the bucket list."),
            ("Adventure awaits ✈️", "There's a whole world out there waiting to be explored."),
            ("Wanderlust diaries 🗺️", "Every destination tells a story. What's yours?"),
        ],
    }
    
    variations = []
    base_templates = templates.get(niche, templates["lifestyle"])
    
    for i, (title, desc) in enumerate(base_templates):
        hashtags = [f"#{niche}", "#content", "#viral", f"#{content_type}", "#trending"]
        variations.append(ContentVariation(
            id=str(uuid.uuid4()),
            title=title,
            description=desc,
            hashtags=hashtags,
            is_primary=(i == 0),
            platform_hint=random.choice(PLATFORMS),
            times_used=0,
        ))
    
    return variations


def generate_platform_assignments(content_type: str, quality_score: int, niche: str) -> List[PlatformAssignment]:
    """Generate platform assignments based on content analysis"""
    assignments = []
    
    # Define platform compatibility
    platform_compat = {
        "image": ["instagram", "twitter", "linkedin", "threads", "pinterest"],
        "video": ["tiktok", "youtube", "instagram", "twitter", "linkedin"],
        "clip": ["tiktok", "youtube", "instagram"],
    }
    
    compatible = platform_compat.get(content_type, ["instagram", "tiktok"])
    
    for platform in compatible:
        # Calculate match score
        base_score = random.uniform(60, 95)
        
        # Adjust for quality
        if quality_score >= 80:
            base_score += 5
        elif quality_score < 60:
            base_score -= 10
            
        match_reasons = ["format_compatible"]
        if quality_score >= 70:
            match_reasons.append("quality_threshold_met")
        if niche in ["lifestyle", "fitness", "travel"]:
            match_reasons.append("niche_trending")
            
        assignments.append(PlatformAssignment(
            platform=platform,
            account_username=f"@{niche}_account",
            match_score=min(100, base_score),
            match_reasons=match_reasons,
            status="suggested",
        ))
    
    # Sort by match score
    assignments.sort(key=lambda x: x.match_score, reverse=True)
    return assignments[:4]  # Top 4 platforms


def generate_mock_content(count: int = 10, status: str = "pending_approval") -> List[ContentItem]:
    """Generate mock content items for testing"""
    items = []
    
    for i in range(count):
        content_type = random.choice(["image", "video", "clip"])
        niche = random.choice(NICHES)
        quality_score = random.randint(50, 98)
        
        content = ContentItem(
            id=str(uuid.uuid4()),
            media_id=str(uuid.uuid4()),
            source_type="media_library",
            status=status,
            quality_score=quality_score,
            niche=niche,
            content_type=content_type,
            duration_sec=random.uniform(5, 60) if content_type in ["video", "clip"] else None,
            resolution="1080x1920" if content_type in ["video", "clip"] else "1080x1350",
            aspect_ratio="9:16" if content_type in ["video", "clip"] else "4:5",
            thumbnail_url=f"http://localhost:5555/api/media-db/thumbnail/{uuid.uuid4()}",
            ai_analysis={
                "mood": random.choice(MOODS),
                "topics": [niche, random.choice(NICHES)],
                "engagement_prediction": random.choice(["high", "medium", "low"]),
                "scene_type": random.choice(["indoor", "outdoor", "studio"]),
                "people_count": random.randint(0, 3),
            },
            variations=generate_mock_variations(niche, content_type),
            platform_assignments=generate_platform_assignments(content_type, quality_score, niche),
            priority=random.randint(0, 10),
            created_at=datetime.now() - timedelta(hours=random.randint(1, 72)),
        )
        items.append(content)
    
    return items


# ============================================================================
# IN-MEMORY STORAGE (Replace with DB in production)
# ============================================================================

_content_queue: Dict[str, ContentItem] = {}
_approved_content: Dict[str, ContentItem] = {}
_scheduled_posts: List[Dict] = []
_rejected_content: Dict[str, ContentItem] = {}
_saved_for_later: Dict[str, ContentItem] = {}


def _init_mock_data():
    """Initialize with mock data if empty"""
    global _content_queue
    if not _content_queue:
        for item in generate_mock_content(25, "pending_approval"):
            _content_queue[item.id] = item


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/queue", response_model=Dict[str, Any])
async def get_content_queue(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    niche: Optional[str] = Query(default=None),
    min_quality: Optional[int] = Query(default=None, ge=0, le=100),
    content_type: Optional[str] = Query(default=None),
):
    """
    Get pending content for approval (swipe interface).
    Returns content items sorted by priority and quality.
    """
    _init_mock_data()
    
    items = list(_content_queue.values())
    
    # Apply filters
    if niche:
        items = [i for i in items if i.niche == niche]
    if min_quality:
        items = [i for i in items if i.quality_score >= min_quality]
    if content_type:
        items = [i for i in items if i.content_type == content_type]
    
    # Sort by priority (desc) then quality (desc)
    items.sort(key=lambda x: (x.priority, x.quality_score), reverse=True)
    
    # Paginate
    total = len(items)
    items = items[offset:offset + limit]
    
    return {
        "items": [item.dict() for item in items],
        "total": total,
        "offset": offset,
        "limit": limit,
        "filters": {
            "available_niches": list(set(i.niche for i in _content_queue.values() if i.niche)),
            "available_types": list(set(i.content_type for i in _content_queue.values())),
        }
    }


@router.get("/queue/next", response_model=Optional[ContentItem])
async def get_next_content():
    """Get the next content item to approve (for swipe interface)"""
    _init_mock_data()
    
    if not _content_queue:
        return None
    
    # Get highest priority item
    items = sorted(_content_queue.values(), key=lambda x: (x.priority, x.quality_score), reverse=True)
    return items[0] if items else None


@router.post("/approve", response_model=Dict[str, Any])
async def approve_content(request: ApproveRequest):
    """
    Approve or reject content via swipe action.
    
    Actions:
    - APPROVE (right swipe): Approve for selected platforms
    - REJECT (left swipe): Remove from queue
    - PRIORITY (up swipe): Approve with high priority
    - SAVE_LATER (down swipe): Save for later review
    """
    _init_mock_data()
    
    content_id = request.content_id
    
    if content_id not in _content_queue:
        raise HTTPException(status_code=404, detail="Content not found in queue")
    
    content = _content_queue.pop(content_id)
    
    if request.action == SwipeAction.APPROVE:
        content.status = ContentStatus.APPROVED
        content.priority = request.priority
        
        # Update platform assignments if specified
        if request.selected_platforms:
            for assignment in content.platform_assignments:
                if assignment.platform in request.selected_platforms:
                    assignment.status = "approved"
                else:
                    assignment.status = "rejected"
        
        _approved_content[content_id] = content
        return {"status": "approved", "content_id": content_id, "message": "Content approved for posting"}
    
    elif request.action == SwipeAction.REJECT:
        content.status = ContentStatus.REJECTED
        _rejected_content[content_id] = content
        return {"status": "rejected", "content_id": content_id, "message": "Content rejected"}
    
    elif request.action == SwipeAction.PRIORITY:
        content.status = ContentStatus.APPROVED
        content.priority = 100  # High priority
        _approved_content[content_id] = content
        return {"status": "priority_approved", "content_id": content_id, "message": "Content approved with high priority"}
    
    elif request.action == SwipeAction.SAVE_LATER:
        content.status = ContentStatus.SAVED_FOR_LATER
        _saved_for_later[content_id] = content
        return {"status": "saved", "content_id": content_id, "message": "Content saved for later"}
    
    raise HTTPException(status_code=400, detail="Invalid action")


@router.post("/bulk-approve", response_model=Dict[str, Any])
async def bulk_approve(
    min_quality: int = Query(default=80, ge=0, le=100),
    niches: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Bulk approve content meeting criteria"""
    _init_mock_data()
    
    approved_count = 0
    approved_ids = []
    
    for content_id, content in list(_content_queue.items()):
        if approved_count >= limit:
            break
            
        if content.quality_score >= min_quality:
            if niches is None or content.niche in niches:
                content.status = ContentStatus.APPROVED
                _approved_content[content_id] = _content_queue.pop(content_id)
                approved_count += 1
                approved_ids.append(content_id)
    
    return {
        "approved_count": approved_count,
        "approved_ids": approved_ids,
        "remaining_in_queue": len(_content_queue),
    }


@router.get("/runway", response_model=RunwayStats)
async def get_runway_stats():
    """Get content runway statistics"""
    _init_mock_data()
    
    # Calculate runway
    approved_count = len(_approved_content)
    posts_per_day = 4  # Default: 4 posts per day (every 4 hours during daylight)
    days_of_runway = approved_count // posts_per_day if posts_per_day > 0 else 0
    
    # Count by platform
    runway_by_platform = {}
    for content in _approved_content.values():
        for assignment in content.platform_assignments:
            if assignment.status == "approved":
                platform = assignment.platform
                runway_by_platform[platform] = runway_by_platform.get(platform, 0) + 1
    
    # Convert to days
    for platform in runway_by_platform:
        runway_by_platform[platform] = runway_by_platform[platform] // 2  # Assume 2 posts per platform per day
    
    # Count by niche
    content_by_niche = {}
    for content in list(_approved_content.values()) + list(_content_queue.values()):
        niche = content.niche or "uncategorized"
        content_by_niche[niche] = content_by_niche.get(niche, 0) + 1
    
    # Find low runway platforms
    low_runway_platforms = [p for p, days in runway_by_platform.items() if days < 14]
    
    return RunwayStats(
        total_approved=approved_count,
        total_scheduled=len(_scheduled_posts),
        total_pending=len(_content_queue),
        total_saved_for_later=len(_saved_for_later),
        days_of_runway=days_of_runway,
        runway_by_platform=runway_by_platform,
        posts_today=random.randint(2, 8),  # Mock
        posts_this_week=random.randint(15, 35),  # Mock
        content_by_niche=content_by_niche,
        low_runway_platforms=low_runway_platforms,
    )


@router.post("/schedule", response_model=Dict[str, Any])
async def schedule_post(request: ScheduleRequest):
    """Schedule a post for publishing"""
    content_id = request.content_id
    
    if content_id not in _approved_content:
        raise HTTPException(status_code=404, detail="Content not found in approved list")
    
    content = _approved_content[content_id]
    
    post = {
        "id": str(uuid.uuid4()),
        "content_id": content_id,
        "platform": request.platform,
        "account_id": request.account_id,
        "scheduled_time": request.scheduled_time.isoformat(),
        "variation_id": request.variation_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    
    _scheduled_posts.append(post)
    
    return {
        "status": "scheduled",
        "post_id": post["id"],
        "scheduled_time": post["scheduled_time"],
        "platform": request.platform,
    }


@router.get("/schedule", response_model=Dict[str, Any])
async def get_schedule(
    days: int = Query(default=7, ge=1, le=30),
    platform: Optional[str] = Query(default=None),
):
    """Get scheduled posts"""
    posts = _scheduled_posts.copy()
    
    if platform:
        posts = [p for p in posts if p["platform"] == platform]
    
    # Group by date
    by_date = {}
    for post in posts:
        date = post["scheduled_time"][:10]
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(post)
    
    return {
        "posts": posts,
        "by_date": by_date,
        "total": len(posts),
    }


@router.post("/auto-schedule", response_model=Dict[str, Any])
async def auto_schedule(
    days: int = Query(default=7, ge=1, le=60),
    posts_per_day: int = Query(default=4, ge=1, le=10),
):
    """
    Automatically schedule approved content.
    Posts every 4 hours during daylight hours (6 AM - 10 PM).
    """
    from datetime import time as dt_time
    
    posting_times = [
        dt_time(6, 0),   # 6 AM
        dt_time(10, 0),  # 10 AM
        dt_time(14, 0),  # 2 PM
        dt_time(18, 0),  # 6 PM
        dt_time(22, 0),  # 10 PM (optional)
    ][:posts_per_day]
    
    scheduled_count = 0
    approved_list = list(_approved_content.values())
    
    if not approved_list:
        return {"scheduled_count": 0, "message": "No approved content available"}
    
    content_index = 0
    
    for day_offset in range(days):
        post_date = datetime.now().date() + timedelta(days=day_offset)
        
        for post_time in posting_times:
            if content_index >= len(approved_list):
                break
                
            content = approved_list[content_index]
            
            # Find best platform assignment
            approved_platforms = [a for a in content.platform_assignments if a.status == "approved"]
            if not approved_platforms:
                approved_platforms = content.platform_assignments[:1]
            
            if approved_platforms:
                platform = approved_platforms[0].platform
                scheduled_time = datetime.combine(post_date, post_time)
                
                post = {
                    "id": str(uuid.uuid4()),
                    "content_id": content.id,
                    "platform": platform,
                    "scheduled_time": scheduled_time.isoformat(),
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                }
                _scheduled_posts.append(post)
                scheduled_count += 1
            
            content_index += 1
    
    return {
        "scheduled_count": scheduled_count,
        "days_covered": days,
        "posts_per_day": posts_per_day,
        "message": f"Successfully scheduled {scheduled_count} posts over {days} days",
    }


@router.post("/generate-variations", response_model=Dict[str, Any])
async def generate_new_variations(
    content_id: str = Body(...),
    count: int = Body(default=3, ge=1, le=10),
):
    """Generate new title/description variations for content"""
    content = _approved_content.get(content_id) or _content_queue.get(content_id)
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    new_variations = generate_mock_variations(content.niche or "lifestyle", content.content_type)[:count]
    
    # Add to existing variations
    content.variations.extend(new_variations)
    
    return {
        "content_id": content_id,
        "new_variations": [v.dict() for v in new_variations],
        "total_variations": len(content.variations),
    }


@router.get("/analytics", response_model=Dict[str, Any])
async def get_pipeline_analytics():
    """Get analytics for the content pipeline"""
    _init_mock_data()
    
    return {
        "queue_stats": {
            "pending_analysis": 0,
            "pending_approval": len(_content_queue),
            "approved": len(_approved_content),
            "scheduled": len(_scheduled_posts),
            "rejected": len(_rejected_content),
            "saved_for_later": len(_saved_for_later),
        },
        "quality_distribution": {
            "high_quality": sum(1 for c in _content_queue.values() if c.quality_score >= 80),
            "medium_quality": sum(1 for c in _content_queue.values() if 60 <= c.quality_score < 80),
            "low_quality": sum(1 for c in _content_queue.values() if c.quality_score < 60),
        },
        "platform_distribution": {
            platform: sum(
                1 for c in _approved_content.values() 
                for a in c.platform_assignments if a.platform == platform
            )
            for platform in PLATFORMS
        },
        "niche_distribution": {
            niche: sum(1 for c in _content_queue.values() if c.niche == niche)
            for niche in NICHES
        },
        "approval_rate": round(
            len(_approved_content) / (len(_approved_content) + len(_rejected_content) + 0.001) * 100, 1
        ),
    }


class AnalyzeRequest(BaseModel):
    media_id: str


@router.post("/analyze", response_model=Dict[str, Any])
async def trigger_analysis(request: AnalyzeRequest):
    """Trigger AI analysis on a media item"""
    # In production, this would call the AI analysis service
    niche = random.choice(NICHES)
    content_type = random.choice(["image", "video", "clip"])
    quality_score = random.randint(60, 95)
    
    content = ContentItem(
        id=str(uuid.uuid4()),
        media_id=request.media_id,
        source_type="media_library",
        status=ContentStatus.PENDING_APPROVAL,
        quality_score=quality_score,
        niche=niche,
        content_type=content_type,
        ai_analysis={
            "mood": random.choice(MOODS),
            "topics": [niche],
            "engagement_prediction": "high" if quality_score >= 80 else "medium",
        },
        variations=generate_mock_variations(niche, content_type),
        platform_assignments=generate_platform_assignments(content_type, quality_score, niche),
    )
    
    _content_queue[content.id] = content
    
    return {
        "status": "analyzed",
        "content_id": content.id,
        "quality_score": quality_score,
        "niche": niche,
        "variations_generated": len(content.variations),
        "platforms_suggested": len(content.platform_assignments),
    }


@router.delete("/queue/{content_id}")
async def remove_from_queue(content_id: str):
    """Remove content from queue"""
    if content_id in _content_queue:
        del _content_queue[content_id]
        return {"status": "removed", "content_id": content_id}
    raise HTTPException(status_code=404, detail="Content not found")


@router.post("/reset-mock-data")
async def reset_mock_data():
    """Reset all mock data (for testing)"""
    global _content_queue, _approved_content, _scheduled_posts, _rejected_content, _saved_for_later
    _content_queue = {}
    _approved_content = {}
    _scheduled_posts = []
    _rejected_content = {}
    _saved_for_later = {}
    _init_mock_data()
    return {"status": "reset", "queue_size": len(_content_queue)}
