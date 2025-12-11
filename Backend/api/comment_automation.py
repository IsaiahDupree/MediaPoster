"""
Comment Automation API
Automated comment engagement system for TikTok, YouTube, and Instagram.
Supports AI-generated comments, approval workflows, scheduling, and impact analysis.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import uuid
import random
import hashlib

router = APIRouter(prefix="/api/comment-automation", tags=["Comment Automation"])


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"


class AutomationMode(str, Enum):
    FULL_AUTO = "full_auto"
    SEMI_AUTO = "semi_auto"
    MANUAL = "manual"


class CommentStatus(str, Enum):
    GENERATED = "generated"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    REJECTED = "rejected"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CommentConfig(BaseModel):
    """Global comment automation configuration"""
    daily_limit: int = Field(default=50, ge=1, le=500)
    per_niche_limit: int = Field(default=10, ge=1, le=100)
    per_platform_limit: int = Field(default=20, ge=1, le=200)
    min_interval_minutes: int = Field(default=15, ge=1, le=120)
    max_interval_minutes: int = Field(default=60, ge=5, le=240)
    jitter_percent: int = Field(default=20, ge=0, le=50)
    active_hours_start: int = Field(default=8, ge=0, le=23)
    active_hours_end: int = Field(default=22, ge=0, le=23)
    automation_mode: AutomationMode = AutomationMode.SEMI_AUTO


class NicheConfig(BaseModel):
    """Niche-specific comment configuration"""
    niche: str
    daily_limit: int = Field(default=10, ge=1, le=100)
    priority: Priority = Priority.MEDIUM
    tone: str = Field(default="friendly and engaging")
    keywords: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)
    enabled: bool = True


class PlatformConfig(BaseModel):
    """Platform-specific configuration"""
    platform: Platform
    enabled: bool = True
    daily_limit: int = Field(default=20, ge=1, le=100)
    target_accounts: List[str] = Field(default_factory=list)
    target_hashtags: List[str] = Field(default_factory=list)
    target_playlists: List[str] = Field(default_factory=list)  # YouTube only
    include_fyp: bool = True  # TikTok only
    include_explore: bool = True  # Instagram only


class TargetContent(BaseModel):
    """Content to comment on"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: Platform
    content_id: str
    content_url: str
    content_type: str  # video, post, reel, etc.
    author_username: str
    author_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    niche: str
    discovered_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    top_comments: List[Dict] = Field(default_factory=list)
    engagement_score: float = 0.0


class GeneratedComment(BaseModel):
    """AI-generated comment pending approval/posting"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_content_id: str
    platform: Platform
    niche: str
    comment_text: str
    tone: str
    status: CommentStatus = CommentStatus.GENERATED
    automation_mode: AutomationMode = AutomationMode.SEMI_AUTO
    priority: Priority = Priority.MEDIUM
    scheduled_time: Optional[str] = None
    posted_time: Optional[str] = None
    source_url: str
    comment_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    account_id: Optional[str] = None


class CommentEngagement(BaseModel):
    """Tracking engagement on posted comments"""
    comment_id: str
    likes: int = 0
    replies: int = 0
    profile_clicks: int = 0
    new_followers: int = 0
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class GenerateRequest(BaseModel):
    """Request body for generating comments"""
    target_content_ids: List[str]
    tone: Optional[str] = None


class BulkApproveRequest(BaseModel):
    """Request body for bulk approving comments"""
    comment_ids: List[str]


class ImpactAnalysis(BaseModel):
    """Impact analysis metrics"""
    period: str  # daily, weekly, monthly
    total_comments_posted: int = 0
    total_engagement: int = 0
    avg_likes_per_comment: float = 0.0
    avg_replies_per_comment: float = 0.0
    profile_visits: int = 0
    follower_growth: int = 0
    reach_estimate: int = 0
    best_performing_niche: Optional[str] = None
    best_performing_platform: Optional[Platform] = None
    best_time_of_day: Optional[str] = None
    roi_score: float = 0.0


# ============================================================================
# IN-MEMORY STORAGE (Mock Data)
# ============================================================================

_global_config = CommentConfig()
_niche_configs: Dict[str, NicheConfig] = {}
_platform_configs: Dict[str, PlatformConfig] = {}
_target_content: List[TargetContent] = []
_generated_comments: List[GeneratedComment] = []
_comment_engagements: Dict[str, CommentEngagement] = {}
_posted_comments_today: int = 0
_last_comment_time: Optional[datetime] = None


def _init_mock_data():
    """Initialize with mock data"""
    global _niche_configs, _platform_configs, _target_content, _generated_comments
    
    # Default niche configs
    niches = ["fitness", "tech", "lifestyle", "comedy", "education", "gaming"]
    for niche in niches:
        _niche_configs[niche] = NicheConfig(
            niche=niche,
            daily_limit=10,
            priority=Priority.MEDIUM,
            tone=f"friendly and engaging for {niche} audience",
            keywords=[niche, f"{niche}tips", f"{niche}content"],
        )
    
    # Default platform configs
    for platform in Platform:
        _platform_configs[platform.value] = PlatformConfig(
            platform=platform,
            enabled=True,
            daily_limit=20,
        )
    
    # Mock target content
    mock_targets = [
        {
            "platform": Platform.TIKTOK,
            "content_type": "video",
            "niche": "fitness",
            "title": "5 Minute Morning Workout",
            "author_username": "fitguru123",
        },
        {
            "platform": Platform.YOUTUBE,
            "content_type": "video",
            "niche": "tech",
            "title": "iPhone 16 Review",
            "author_username": "techreviewer",
        },
        {
            "platform": Platform.INSTAGRAM,
            "content_type": "reel",
            "niche": "lifestyle",
            "title": "Day in My Life",
            "author_username": "lifestyle_vibes",
        },
    ]
    
    for i, target in enumerate(mock_targets):
        _target_content.append(TargetContent(
            platform=target["platform"],
            content_id=f"content_{i}_{target['platform'].value}",
            content_url=f"https://{target['platform'].value}.com/content_{i}",
            content_type=target["content_type"],
            author_username=target["author_username"],
            title=target["title"],
            niche=target["niche"],
            top_comments=[
                {"text": "Great content!", "likes": 150},
                {"text": "Love this!", "likes": 89},
                {"text": "So helpful 🙌", "likes": 67},
            ],
            engagement_score=random.uniform(70, 95),
        ))
    
    # Mock generated comments
    tones = ["enthusiastic", "supportive", "curious", "appreciative"]
    for i, target in enumerate(_target_content[:5]):
        tone = random.choice(tones)
        _generated_comments.append(GeneratedComment(
            target_content_id=target.id,
            platform=target.platform,
            niche=target.niche,
            comment_text=_generate_mock_comment(target, tone),
            tone=tone,
            status=CommentStatus.PENDING_REVIEW,
            source_url=target.content_url,
            priority=random.choice(list(Priority)),
        ))


def _generate_mock_comment(target: TargetContent, tone: str) -> str:
    """Generate a mock comment based on target and tone"""
    templates = {
        "enthusiastic": [
            f"This is exactly what I needed today! 🔥 {target.niche} content like this is why I love this platform!",
            f"Incredible! The way you explain {target.niche} topics is so engaging! 💪",
        ],
        "supportive": [
            f"Keep up the amazing work! Your {target.niche} content always inspires me.",
            f"This is so valuable for the {target.niche} community! Thank you for sharing.",
        ],
        "curious": [
            f"Love this approach! Any tips for beginners in {target.niche}?",
            f"This is fascinating! How did you get started in {target.niche}?",
        ],
        "appreciative": [
            f"Thank you for this! Been following your {target.niche} content for a while now.",
            f"Finally someone who gets {target.niche} right! Subscribed! 🎉",
        ],
    }
    return random.choice(templates.get(tone, templates["supportive"]))


_init_mock_data()


# ============================================================================
# CONFIGURATION ENDPOINTS
# ============================================================================

@router.get("/config")
async def get_config() -> CommentConfig:
    """Get global comment automation configuration"""
    return _global_config


@router.put("/config")
async def update_config(config: CommentConfig) -> CommentConfig:
    """Update global configuration"""
    global _global_config
    _global_config = config
    return _global_config


@router.get("/config/niches")
async def get_niche_configs() -> List[NicheConfig]:
    """Get all niche configurations"""
    return list(_niche_configs.values())


@router.get("/config/niche/{niche}")
async def get_niche_config(niche: str) -> NicheConfig:
    """Get specific niche configuration"""
    if niche not in _niche_configs:
        raise HTTPException(status_code=404, detail=f"Niche '{niche}' not found")
    return _niche_configs[niche]


@router.put("/config/niche/{niche}")
async def update_niche_config(niche: str, config: NicheConfig) -> NicheConfig:
    """Update or create niche configuration"""
    _niche_configs[niche] = config
    return config


@router.delete("/config/niche/{niche}")
async def delete_niche_config(niche: str):
    """Delete niche configuration"""
    if niche in _niche_configs:
        del _niche_configs[niche]
    return {"status": "deleted", "niche": niche}


@router.get("/config/platforms")
async def get_platform_configs() -> List[PlatformConfig]:
    """Get all platform configurations"""
    return list(_platform_configs.values())


@router.put("/config/platform/{platform}")
async def update_platform_config(platform: Platform, config: PlatformConfig) -> PlatformConfig:
    """Update platform configuration"""
    _platform_configs[platform.value] = config
    return config


# ============================================================================
# TARGET CONTENT DISCOVERY
# ============================================================================

@router.post("/discover")
async def discover_content(
    platform: Platform,
    niche: str,
    limit: int = Query(default=10, le=50),
) -> Dict:
    """
    Discover target content to comment on.
    Scrapes top content from platform based on niche.
    """
    # Mock discovery - in production would call platform APIs
    discovered = []
    for i in range(limit):
        content = TargetContent(
            platform=platform,
            content_id=f"discovered_{platform.value}_{niche}_{i}_{uuid.uuid4().hex[:8]}",
            content_url=f"https://{platform.value}.com/p/{uuid.uuid4().hex[:10]}",
            content_type="video" if platform in [Platform.TIKTOK, Platform.YOUTUBE] else "post",
            author_username=f"{niche}_creator_{i}",
            title=f"Top {niche.title()} Content #{i+1}",
            niche=niche,
            top_comments=[
                {"text": f"Comment {j}", "likes": random.randint(10, 500)}
                for j in range(5)
            ],
            engagement_score=random.uniform(60, 98),
        )
        discovered.append(content)
        _target_content.append(content)
    
    return {
        "platform": platform,
        "niche": niche,
        "discovered_count": len(discovered),
        "content": [c.dict() for c in discovered],
    }


@router.get("/targets")
async def get_target_content(
    platform: Optional[Platform] = None,
    niche: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> Dict:
    """Get discovered target content"""
    filtered = _target_content
    
    if platform:
        filtered = [t for t in filtered if t.platform == platform]
    if niche:
        filtered = [t for t in filtered if t.niche == niche]
    
    total = len(filtered)
    filtered = filtered[offset:offset + limit]
    
    return {
        "items": [t.dict() for t in filtered],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/targets/{content_id}/top-comments")
async def get_top_comments(content_id: str) -> Dict:
    """Get top comments from target content for analysis"""
    target = next((t for t in _target_content if t.id == content_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target content not found")
    
    return {
        "content_id": content_id,
        "platform": target.platform,
        "top_comments": target.top_comments,
        "summary": _summarize_comments(target.top_comments),
    }


def _summarize_comments(comments: List[Dict]) -> str:
    """Generate summary of top comments (mock AI)"""
    if not comments:
        return "No comments to analyze"
    
    # Mock summary - in production would use AI
    themes = ["enthusiasm", "appreciation", "questions", "support"]
    return f"Top comments show {random.choice(themes)} with an average of {sum(c.get('likes', 0) for c in comments) // len(comments)} likes"


# ============================================================================
# COMMENT GENERATION
# ============================================================================

@router.post("/generate")
async def generate_comments(request: GenerateRequest) -> Dict:
    """
    Generate AI comments for target content.
    Uses configured tone and niche settings.
    """
    generated = []
    
    for content_id in request.target_content_ids:
        target = next((t for t in _target_content if t.id == content_id), None)
        if not target:
            continue
        
        niche_config = _niche_configs.get(target.niche, NicheConfig(niche=target.niche))
        comment_tone = request.tone or niche_config.tone
        
        comment = GeneratedComment(
            target_content_id=content_id,
            platform=target.platform,
            niche=target.niche,
            comment_text=_generate_mock_comment(target, comment_tone),
            tone=comment_tone,
            status=CommentStatus.PENDING_REVIEW if _global_config.automation_mode != AutomationMode.FULL_AUTO else CommentStatus.APPROVED,
            automation_mode=_global_config.automation_mode,
            source_url=target.content_url,
            priority=niche_config.priority,
        )
        
        _generated_comments.append(comment)
        generated.append(comment)
    
    return {
        "generated_count": len(generated),
        "comments": [c.dict() for c in generated],
        "automation_mode": _global_config.automation_mode,
    }


@router.post("/generate-batch")
async def generate_batch_comments(
    platform: Optional[Platform] = None,
    niche: Optional[str] = None,
    count: int = Query(default=10, le=50),
) -> Dict:
    """Generate comments for multiple targets at once"""
    # Filter eligible targets
    targets = _target_content
    if platform:
        targets = [t for t in targets if t.platform == platform]
    if niche:
        targets = [t for t in targets if t.niche == niche]
    
    # Select top targets by engagement
    targets = sorted(targets, key=lambda t: t.engagement_score, reverse=True)[:count]
    
    # Create request object and call generate
    request = GenerateRequest(target_content_ids=[t.id for t in targets])
    return await generate_comments(request)


# ============================================================================
# APPROVAL QUEUE
# ============================================================================

@router.get("/queue")
async def get_approval_queue(
    status: Optional[CommentStatus] = None,
    platform: Optional[Platform] = None,
    niche: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> Dict:
    """Get comments pending approval"""
    filtered = _generated_comments
    
    if status:
        filtered = [c for c in filtered if c.status == status]
    else:
        # Default: show pending review
        filtered = [c for c in filtered if c.status in [CommentStatus.PENDING_REVIEW, CommentStatus.GENERATED]]
    
    if platform:
        filtered = [c for c in filtered if c.platform == platform]
    if niche:
        filtered = [c for c in filtered if c.niche == niche]
    
    # Sort by priority
    priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    filtered = sorted(filtered, key=lambda c: priority_order.get(c.priority, 1))
    
    total = len(filtered)
    filtered = filtered[offset:offset + limit]
    
    return {
        "items": [c.dict() for c in filtered],
        "total": total,
        "limit": limit,
        "offset": offset,
        "stats": {
            "pending": len([c for c in _generated_comments if c.status == CommentStatus.PENDING_REVIEW]),
            "approved": len([c for c in _generated_comments if c.status == CommentStatus.APPROVED]),
            "scheduled": len([c for c in _generated_comments if c.status == CommentStatus.SCHEDULED]),
            "posted": len([c for c in _generated_comments if c.status == CommentStatus.POSTED]),
        },
    }


@router.post("/approve/{comment_id}")
async def approve_comment(
    comment_id: str,
    edited_text: Optional[str] = None,
    schedule_time: Optional[str] = None,
) -> GeneratedComment:
    """Approve a comment for posting"""
    comment = next((c for c in _generated_comments if c.id == comment_id), None)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if edited_text:
        comment.comment_text = edited_text
    
    comment.status = CommentStatus.APPROVED
    comment.approved_at = datetime.now().isoformat()
    
    if schedule_time:
        comment.scheduled_time = schedule_time
        comment.status = CommentStatus.SCHEDULED
    
    return comment


@router.post("/approve-bulk")
async def approve_bulk(request: BulkApproveRequest) -> Dict:
    """Approve multiple comments at once"""
    approved = []
    for comment_id in request.comment_ids:
        comment = next((c for c in _generated_comments if c.id == comment_id), None)
        if comment:
            comment.status = CommentStatus.APPROVED
            comment.approved_at = datetime.now().isoformat()
            approved.append(comment_id)
    
    return {
        "approved_count": len(approved),
        "approved_ids": approved,
    }


@router.post("/reject/{comment_id}")
async def reject_comment(
    comment_id: str,
    reason: Optional[str] = None,
) -> Dict:
    """Reject a comment"""
    comment = next((c for c in _generated_comments if c.id == comment_id), None)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.status = CommentStatus.REJECTED
    return {"status": "rejected", "comment_id": comment_id, "reason": reason}


@router.post("/edit/{comment_id}")
async def edit_comment(
    comment_id: str,
    new_text: str,
) -> GeneratedComment:
    """Edit comment text before posting"""
    comment = next((c for c in _generated_comments if c.id == comment_id), None)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.comment_text = new_text
    return comment


# ============================================================================
# SCHEDULING & POSTING
# ============================================================================

@router.post("/schedule/{comment_id}")
async def schedule_comment(
    comment_id: str,
    scheduled_time: str,
) -> GeneratedComment:
    """Schedule an approved comment for posting"""
    comment = next((c for c in _generated_comments if c.id == comment_id), None)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.status not in [CommentStatus.APPROVED, CommentStatus.PENDING_REVIEW]:
        raise HTTPException(status_code=400, detail="Comment must be approved first")
    
    comment.scheduled_time = scheduled_time
    comment.status = CommentStatus.SCHEDULED
    return comment


@router.post("/auto-schedule")
async def auto_schedule_approved(
    hours_ahead: int = Query(default=24, ge=1, le=168),
) -> Dict:
    """Auto-schedule all approved comments with jitter"""
    approved = [c for c in _generated_comments if c.status == CommentStatus.APPROVED]
    
    if not approved:
        return {"scheduled_count": 0, "message": "No approved comments to schedule"}
    
    # Calculate intervals with jitter
    min_interval = _global_config.min_interval_minutes
    max_interval = _global_config.max_interval_minutes
    jitter = _global_config.jitter_percent / 100
    
    current_time = datetime.now()
    scheduled = []
    
    for comment in approved:
        # Add random interval
        base_interval = random.randint(min_interval, max_interval)
        jitter_amount = int(base_interval * jitter * random.uniform(-1, 1))
        interval = max(min_interval, base_interval + jitter_amount)
        
        current_time += timedelta(minutes=interval)
        
        # Check if within active hours
        if current_time.hour < _global_config.active_hours_start:
            current_time = current_time.replace(hour=_global_config.active_hours_start, minute=0)
        elif current_time.hour >= _global_config.active_hours_end:
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=_global_config.active_hours_start, minute=0)
        
        comment.scheduled_time = current_time.isoformat()
        comment.status = CommentStatus.SCHEDULED
        scheduled.append(comment.id)
    
    return {
        "scheduled_count": len(scheduled),
        "scheduled_ids": scheduled,
        "first_post": scheduled[0] if scheduled else None,
        "last_post": scheduled[-1] if scheduled else None,
    }


@router.get("/schedule")
async def get_schedule(
    days: int = Query(default=7, le=30),
    platform: Optional[Platform] = None,
) -> Dict:
    """Get scheduled comments"""
    scheduled = [c for c in _generated_comments if c.status == CommentStatus.SCHEDULED]
    
    if platform:
        scheduled = [c for c in scheduled if c.platform == platform]
    
    # Sort by scheduled time
    scheduled = sorted(scheduled, key=lambda c: c.scheduled_time or "")
    
    # Group by day
    by_day = {}
    for comment in scheduled:
        if comment.scheduled_time:
            day = comment.scheduled_time[:10]
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(comment.dict())
    
    return {
        "total_scheduled": len(scheduled),
        "by_day": by_day,
        "comments": [c.dict() for c in scheduled],
    }


@router.post("/post/{comment_id}")
async def post_comment(comment_id: str) -> Dict:
    """Post a comment immediately (mock)"""
    comment = next((c for c in _generated_comments if c.id == comment_id), None)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Mock posting - in production would call platform API
    comment.status = CommentStatus.POSTED
    comment.posted_time = datetime.now().isoformat()
    comment.comment_url = f"https://{comment.platform.value}.com/comment/{uuid.uuid4().hex[:10]}"
    
    global _posted_comments_today, _last_comment_time
    _posted_comments_today += 1
    _last_comment_time = datetime.now()
    
    # Initialize engagement tracking
    _comment_engagements[comment_id] = CommentEngagement(comment_id=comment_id)
    
    return {
        "status": "posted",
        "comment_id": comment_id,
        "comment_url": comment.comment_url,
        "posted_at": comment.posted_time,
    }


# ============================================================================
# URL TRACKING & ENGAGEMENT
# ============================================================================

@router.get("/tracking")
async def get_tracking_data(
    platform: Optional[Platform] = None,
    days: int = Query(default=7, le=30),
) -> Dict:
    """Get URL tracking data for posted comments"""
    posted = [c for c in _generated_comments if c.status == CommentStatus.POSTED]
    
    if platform:
        posted = [c for c in posted if c.platform == platform]
    
    tracking_data = []
    for comment in posted:
        engagement = _comment_engagements.get(comment.id, CommentEngagement(comment_id=comment.id))
        tracking_data.append({
            "comment_id": comment.id,
            "source_url": comment.source_url,
            "comment_url": comment.comment_url,
            "platform": comment.platform,
            "niche": comment.niche,
            "posted_at": comment.posted_time,
            "engagement": engagement.dict(),
        })
    
    return {
        "total_tracked": len(tracking_data),
        "tracking_data": tracking_data,
    }


@router.post("/tracking/{comment_id}/update")
async def update_engagement(
    comment_id: str,
    likes: Optional[int] = None,
    replies: Optional[int] = None,
    profile_clicks: Optional[int] = None,
    new_followers: Optional[int] = None,
) -> CommentEngagement:
    """Update engagement metrics for a posted comment"""
    if comment_id not in _comment_engagements:
        _comment_engagements[comment_id] = CommentEngagement(comment_id=comment_id)
    
    engagement = _comment_engagements[comment_id]
    if likes is not None:
        engagement.likes = likes
    if replies is not None:
        engagement.replies = replies
    if profile_clicks is not None:
        engagement.profile_clicks = profile_clicks
    if new_followers is not None:
        engagement.new_followers = new_followers
    engagement.last_updated = datetime.now().isoformat()
    
    return engagement


# ============================================================================
# IMPACT ANALYSIS
# ============================================================================

@router.get("/impact")
async def get_impact_analysis(
    period: str = Query(default="weekly", regex="^(daily|weekly|monthly)$"),
    platform: Optional[Platform] = None,
) -> ImpactAnalysis:
    """Get comment automation impact analysis"""
    posted = [c for c in _generated_comments if c.status == CommentStatus.POSTED]
    
    if platform:
        posted = [c for c in posted if c.platform == platform]
    
    # Calculate metrics
    total_posted = len(posted)
    
    total_likes = sum(
        _comment_engagements.get(c.id, CommentEngagement(comment_id=c.id)).likes
        for c in posted
    )
    total_replies = sum(
        _comment_engagements.get(c.id, CommentEngagement(comment_id=c.id)).replies
        for c in posted
    )
    total_profile_clicks = sum(
        _comment_engagements.get(c.id, CommentEngagement(comment_id=c.id)).profile_clicks
        for c in posted
    )
    total_new_followers = sum(
        _comment_engagements.get(c.id, CommentEngagement(comment_id=c.id)).new_followers
        for c in posted
    )
    
    # Find best performing niche
    niche_engagement = {}
    for comment in posted:
        eng = _comment_engagements.get(comment.id, CommentEngagement(comment_id=comment.id))
        if comment.niche not in niche_engagement:
            niche_engagement[comment.niche] = 0
        niche_engagement[comment.niche] += eng.likes + eng.replies
    
    best_niche = max(niche_engagement, key=niche_engagement.get) if niche_engagement else None
    
    # Find best platform
    platform_engagement = {}
    for comment in posted:
        eng = _comment_engagements.get(comment.id, CommentEngagement(comment_id=comment.id))
        plat = comment.platform.value
        if plat not in platform_engagement:
            platform_engagement[plat] = 0
        platform_engagement[plat] += eng.likes + eng.replies
    
    best_platform = max(platform_engagement, key=platform_engagement.get) if platform_engagement else None
    
    return ImpactAnalysis(
        period=period,
        total_comments_posted=total_posted,
        total_engagement=total_likes + total_replies,
        avg_likes_per_comment=total_likes / total_posted if total_posted > 0 else 0,
        avg_replies_per_comment=total_replies / total_posted if total_posted > 0 else 0,
        profile_visits=total_profile_clicks,
        follower_growth=total_new_followers,
        reach_estimate=total_posted * random.randint(100, 500),  # Mock reach
        best_performing_niche=best_niche,
        best_performing_platform=Platform(best_platform) if best_platform else None,
        best_time_of_day="2:00 PM - 4:00 PM",  # Mock
        roi_score=round(random.uniform(3.5, 8.5), 2),  # Mock ROI
    )


@router.get("/impact/breakdown")
async def get_impact_breakdown() -> Dict:
    """Get detailed impact breakdown by platform and niche"""
    posted = [c for c in _generated_comments if c.status == CommentStatus.POSTED]
    
    # By platform
    by_platform = {}
    for platform in Platform:
        platform_comments = [c for c in posted if c.platform == platform]
        engagement = sum(
            _comment_engagements.get(c.id, CommentEngagement(comment_id=c.id)).likes +
            _comment_engagements.get(c.id, CommentEngagement(comment_id=c.id)).replies
            for c in platform_comments
        )
        by_platform[platform.value] = {
            "count": len(platform_comments),
            "engagement": engagement,
            "avg_engagement": engagement / len(platform_comments) if platform_comments else 0,
        }
    
    # By niche
    by_niche = {}
    niches = set(c.niche for c in posted)
    for niche in niches:
        niche_comments = [c for c in posted if c.niche == niche]
        engagement = sum(
            _comment_engagements.get(c.id, CommentEngagement(comment_id=c.id)).likes +
            _comment_engagements.get(c.id, CommentEngagement(comment_id=c.id)).replies
            for c in niche_comments
        )
        by_niche[niche] = {
            "count": len(niche_comments),
            "engagement": engagement,
            "avg_engagement": engagement / len(niche_comments) if niche_comments else 0,
        }
    
    return {
        "total_posted": len(posted),
        "by_platform": by_platform,
        "by_niche": by_niche,
    }


# ============================================================================
# STATS & MONITORING
# ============================================================================

@router.get("/stats")
async def get_stats() -> Dict:
    """Get current automation stats"""
    return {
        "global_config": _global_config.dict(),
        "comments_posted_today": _posted_comments_today,
        "remaining_today": max(0, _global_config.daily_limit - _posted_comments_today),
        "last_comment_time": _last_comment_time.isoformat() if _last_comment_time else None,
        "queue_stats": {
            "generated": len([c for c in _generated_comments if c.status == CommentStatus.GENERATED]),
            "pending_review": len([c for c in _generated_comments if c.status == CommentStatus.PENDING_REVIEW]),
            "approved": len([c for c in _generated_comments if c.status == CommentStatus.APPROVED]),
            "scheduled": len([c for c in _generated_comments if c.status == CommentStatus.SCHEDULED]),
            "posted": len([c for c in _generated_comments if c.status == CommentStatus.POSTED]),
            "rejected": len([c for c in _generated_comments if c.status == CommentStatus.REJECTED]),
            "failed": len([c for c in _generated_comments if c.status == CommentStatus.FAILED]),
        },
        "target_content_count": len(_target_content),
        "niches_configured": list(_niche_configs.keys()),
        "platforms_enabled": [p for p, c in _platform_configs.items() if c.enabled],
    }


@router.post("/reset")
async def reset_automation():
    """Reset automation data (for testing)"""
    global _posted_comments_today, _last_comment_time
    _generated_comments.clear()
    _target_content.clear()
    _comment_engagements.clear()
    _posted_comments_today = 0
    _last_comment_time = None
    _init_mock_data()
    return {"status": "reset", "message": "Automation data reset"}
