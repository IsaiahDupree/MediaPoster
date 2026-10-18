"""
Backend API endpoints for Phase 4 & 5: Publishing & Analytics

Phase 4: Publishing & scheduling via scheduled_posts table
Phase 5: Analytics queries against real post data
"""
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, date, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.event_bus import EventBus, Topics

router = APIRouter(prefix="/api", tags=["publishing", "analytics"])


# ============================================================================
# PHASE 4: PUBLISHING & SCHEDULING
# ============================================================================

class SchedulePostRequest(BaseModel):
    """Request to schedule a post"""
    clip_id: str
    platform: str
    scheduled_time: datetime
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None


class RegenerateRequest(BaseModel):
    """Request to regenerate content"""
    type: str  # 'title' | 'caption' | 'hashtags'
    style: Optional[str] = None  # 'punchier' | 'shorter' | 'educational' | etc.


class AutoScheduleRequest(BaseModel):
    """Request to auto-schedule multiple clips"""
    clip_ids: List[str]
    platform: str
    start_date: date
    end_date: date


@router.post("/publishing/schedule")
async def schedule_post(request: SchedulePostRequest, db: AsyncSession = Depends(get_db)):
    """
    Schedule a post for publishing.

    Inserts into the scheduled_posts table and returns the new post record.
    """
    post_id = str(uuid.uuid4())

    await db.execute(text("""
        INSERT INTO scheduled_posts (id, clip_id, platform, scheduled_time, title, caption, hashtags, status)
        VALUES (:id, :clip_id, :platform, :scheduled_time, :title, :caption, :hashtags, 'scheduled')
    """), {
        "id": post_id,
        "clip_id": request.clip_id,
        "platform": request.platform,
        "scheduled_time": request.scheduled_time,
        "title": request.title,
        "caption": request.caption,
        "hashtags": request.hashtags,
    })

    return {
        "post_id": post_id,
        "clip_id": request.clip_id,
        "platform": request.platform,
        "scheduled_time": request.scheduled_time,
        "status": "scheduled",
    }


@router.put("/publishing/posts/{post_id}/reschedule")
async def reschedule_post(post_id: str, new_time: datetime, db: AsyncSession = Depends(get_db)):
    """
    Reschedule an existing post (drag & drop).

    Updates the scheduled_time in the scheduled_posts table.
    """
    result = await db.execute(text("""
        UPDATE scheduled_posts
        SET scheduled_time = :new_time, updated_at = NOW()
        WHERE id = :post_id AND status IN ('scheduled', 'rescheduled')
        RETURNING id
    """), {"post_id": post_id, "new_time": new_time})

    row = result.fetchone()
    if not row:
        raise HTTPException(404, f"Scheduled post {post_id} not found or already published")

    return {
        "post_id": post_id,
        "scheduled_time": new_time,
        "status": "rescheduled",
    }


@router.post("/publishing/posts/{post_id}/regenerate")
async def regenerate_content(post_id: str, request: RegenerateRequest):
    """
    AI regenerate title, caption, or hashtags.

    Uses OpenAI to generate new content variants.
    """
    if request.type not in ("title", "caption", "hashtags"):
        raise HTTPException(400, "Invalid type. Must be 'title', 'caption', or 'hashtags'.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            503,
            "Content regeneration requires OPENAI_API_KEY to be configured",
        )

    style_instruction = ""
    if request.style:
        style_instruction = f" The style should be: {request.style}."

    type_instructions = {
        "title": (
            "Generate 3 alternative short video titles (each under 80 characters). "
            "Make them attention-grabbing and platform-optimized."
            f"{style_instruction} "
            'Respond with JSON: {"variants": ["title1", "title2", "title3"]}'
        ),
        "caption": (
            "Generate 3 alternative social media captions (each under 300 characters). "
            "Include hooks and calls-to-action."
            f"{style_instruction} "
            'Respond with JSON: {"variants": ["caption1", "caption2", "caption3"]}'
        ),
        "hashtags": (
            "Generate 3 alternative hashtag sets (4-6 hashtags each, including the # symbol). "
            "Mix trending and niche hashtags."
            f"{style_instruction} "
            'Respond with JSON: {"variants": [["#tag1","#tag2","#tag3","#tag4"], '
            '["#tag5","#tag6","#tag7","#tag8"], ["#tag9","#tag10","#tag11","#tag12"]]}'
        ),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a social media content strategist. "
                            "Generate creative, engaging content variants. "
                            "Always respond with valid JSON only."
                        ),
                    },
                    {"role": "user", "content": type_instructions[request.type]},
                ],
                "temperature": 0.8,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    result = json.loads(content)
    variants = result.get("variants", [])

    return {
        "type": request.type,
        "variants": variants,
        "selected": 0,
    }


@router.get("/publishing/calendar/{year}/{month}")
async def get_calendar(year: int, month: int, db: AsyncSession = Depends(get_db)):
    """
    Get all posts for a calendar month.

    Queries the scheduled_posts table for the given month and groups by day.
    """
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    result = await db.execute(text("""
        SELECT id, clip_id, platform, title, caption, scheduled_time, status, metadata
        FROM scheduled_posts
        WHERE scheduled_time >= :start_date AND scheduled_time < :end_date
        ORDER BY scheduled_time
    """), {"start_date": start_date, "end_date": end_date})

    posts_by_day: dict = defaultdict(list)
    for row in result:
        day_key = row[5].strftime("%Y-%m-%d") if row[5] else "unknown"
        posts_by_day[day_key].append({
            "post_id": str(row[0]),
            "clip_id": str(row[1]) if row[1] else None,
            "platform": row[2],
            "title": row[3],
            "scheduled_time": row[5].isoformat() if row[5] else None,
            "status": row[6],
        })

    return {
        "year": year,
        "month": month,
        "posts": dict(posts_by_day),
    }


@router.post("/publishing/auto-schedule")
async def auto_schedule_week(request: AutoScheduleRequest, db: AsyncSession = Depends(get_db)):
    """
    Auto-generate posting plan for selected clips.

    Distributes clips evenly across the date range using best-performing
    time slots from historical data.
    """
    if not request.clip_ids:
        raise HTTPException(400, "No clip_ids provided")

    # Query historical best times for this platform
    best_times_result = await db.execute(text("""
        SELECT EXTRACT(DOW FROM scheduled_time) AS dow,
               EXTRACT(HOUR FROM scheduled_time) AS hour,
               COUNT(*) AS post_count
        FROM scheduled_posts
        WHERE platform = :platform AND status = 'published'
        GROUP BY dow, hour
        ORDER BY post_count DESC
        LIMIT 7
    """), {"platform": request.platform})

    best_slots = best_times_result.fetchall()

    # Default posting hours if no history
    default_hours = [10, 14, 18]
    if best_slots:
        preferred_hours = list(set(int(row[1]) for row in best_slots))[:3]
    else:
        preferred_hours = default_hours

    # Distribute clips across date range
    total_days = (request.end_date - request.start_date).days + 1
    if total_days <= 0:
        raise HTTPException(400, "end_date must be after start_date")

    schedule = []
    for i, clip_id in enumerate(request.clip_ids):
        day_offset = i % total_days
        hour = preferred_hours[i % len(preferred_hours)]
        target_date = request.start_date + timedelta(days=day_offset)
        target_time = datetime(target_date.year, target_date.month, target_date.day, hour)

        reason = (
            f"Slot {hour}:00 selected based on "
            + (f"historical performance data" if best_slots else "default schedule")
        )

        schedule.append({
            "clip_id": clip_id,
            "suggested_time": target_time.isoformat(),
            "reason": reason,
        })

    return {"schedule": schedule}


# ============================================================================
# PHASE 5: ANALYTICS
# ============================================================================

@router.get("/analytics/overview")
async def get_analytics_overview(db: AsyncSession = Depends(get_db)):
    """
    Get overview dashboard data from database.

    Queries scheduled_posts and original_videos for aggregate metrics.
    """
    # Total videos
    videos_result = await db.execute(text(
        "SELECT COUNT(*) FROM original_videos"
    ))
    total_videos = videos_result.scalar() or 0

    # Total clips
    clips_result = await db.execute(text(
        "SELECT COUNT(*) FROM analyzed_videos"
    ))
    total_clips = clips_result.scalar() or 0

    # Total posts and processing queue
    posts_result = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status != 'scheduled') AS total_posts,
            COUNT(*) FILTER (WHERE status = 'scheduled') AS processing_queue
        FROM scheduled_posts
    """))
    posts_row = posts_result.fetchone()
    total_posts = posts_row[0] if posts_row else 0
    processing_queue = posts_row[1] if posts_row else 0

    # Platform distribution
    platform_result = await db.execute(text("""
        SELECT platform, COUNT(*) AS cnt
        FROM scheduled_posts
        GROUP BY platform
        ORDER BY cnt DESC
    """))
    platform_distribution = {row[0]: row[1] for row in platform_result}

    # Recent performance (last 14 days of published posts)
    perf_result = await db.execute(text("""
        SELECT DATE(scheduled_time) AS post_date, COUNT(*) AS posts
        FROM scheduled_posts
        WHERE status = 'published'
          AND scheduled_time >= NOW() - INTERVAL '14 days'
        GROUP BY post_date
        ORDER BY post_date
    """))
    performance_over_time = [
        {"date": row[0].isoformat(), "posts": row[1]}
        for row in perf_result
    ]

    return {
        "summary": {
            "total_videos": total_videos,
            "total_clips": total_clips,
            "total_posts": total_posts,
            "processing_queue": processing_queue,
        },
        "performance_over_time": performance_over_time,
        "platform_distribution": platform_distribution,
    }


@router.get("/analytics/posts/{post_id}/performance")
async def get_post_performance(post_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get detailed performance for a single post.

    Retrieves post data and any associated metadata from the database.
    """
    result = await db.execute(text("""
        SELECT id, platform, title, scheduled_time, status, caption, metadata
        FROM scheduled_posts
        WHERE id = :post_id
    """), {"post_id": post_id})

    row = result.fetchone()
    if not row:
        raise HTTPException(404, f"Post {post_id} not found")

    metadata = row[6] or {}

    return {
        "post_id": str(row[0]),
        "platform": row[1],
        "title": row[2],
        "posted_at": row[3].isoformat() if row[3] else None,
        "status": row[4],
        "caption": row[5],
        "metrics": metadata.get("metrics", {}),
        "retention_curve": metadata.get("retention_curve", []),
        "sentiment": metadata.get("sentiment", {}),
        "checkbacks": metadata.get("checkbacks", []),
    }


@router.get("/analytics/posts/{post_id}/retention")
async def get_retention_curve(post_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get retention curve with transcript annotations.

    Retrieves retention data from post metadata. This data is populated
    by the analytics feedback loop (ARCH-006) from platform APIs.
    """
    result = await db.execute(text("""
        SELECT metadata FROM scheduled_posts WHERE id = :post_id
    """), {"post_id": post_id})

    row = result.fetchone()
    if not row:
        raise HTTPException(404, f"Post {post_id} not found")

    metadata = row[0] or {}
    retention_data = metadata.get("retention_curve", [])
    annotations = metadata.get("retention_annotations", {})

    if not retention_data:
        return {
            "retention_curve": [],
            "annotations": {},
            "note": "Retention data not yet available. Data is populated by the analytics feedback loop.",
        }

    return {
        "retention_curve": retention_data,
        "annotations": annotations,
    }


@router.get("/analytics/insights")
async def get_insights(db: AsyncSession = Depends(get_db)):
    """
    Get data-driven insights from post performance.

    Analyzes published posts for patterns in timing, platform, and content.
    """
    # Best platform by post count
    platform_result = await db.execute(text("""
        SELECT platform, COUNT(*) AS cnt
        FROM scheduled_posts
        WHERE status = 'published'
        GROUP BY platform
        ORDER BY cnt DESC
        LIMIT 3
    """))
    top_platforms = platform_result.fetchall()

    # Best day of week
    dow_result = await db.execute(text("""
        SELECT EXTRACT(DOW FROM scheduled_time) AS dow, COUNT(*) AS cnt
        FROM scheduled_posts
        WHERE status = 'published'
        GROUP BY dow
        ORDER BY cnt DESC
        LIMIT 1
    """))
    best_dow_row = dow_result.fetchone()

    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    best_day = day_names[int(best_dow_row[0])] if best_dow_row else None

    # Best hour
    hour_result = await db.execute(text("""
        SELECT EXTRACT(HOUR FROM scheduled_time) AS hr, COUNT(*) AS cnt
        FROM scheduled_posts
        WHERE status = 'published'
        GROUP BY hr
        ORDER BY cnt DESC
        LIMIT 1
    """))
    best_hour_row = hour_result.fetchone()
    best_hour = int(best_hour_row[0]) if best_hour_row else None

    # Build insights
    patterns = []
    recommendations = []

    if best_day and best_hour:
        patterns.append({
            "type": "timing",
            "insight": f"Most posts published on {best_day} around {best_hour}:00",
            "confidence": 0.8,
        })

    if top_platforms:
        top_platform = top_platforms[0]
        patterns.append({
            "type": "platform",
            "insight": f"Most active platform: {top_platform[0]} ({top_platform[1]} posts)",
            "confidence": 0.9,
        })

        if len(top_platforms) > 1:
            least = top_platforms[-1]
            recommendations.append({
                "type": "platform",
                "suggestion": f"Consider posting more on {least[0]}",
                "reason": f"Only {least[1]} posts vs {top_platform[1]} on {top_platform[0]}",
            })

    # Content gap detection
    gap_result = await db.execute(text("""
        SELECT platform, MAX(scheduled_time) AS last_post,
               EXTRACT(DAY FROM NOW() - MAX(scheduled_time)) AS days_ago
        FROM scheduled_posts
        WHERE status = 'published'
        GROUP BY platform
        HAVING MAX(scheduled_time) < NOW() - INTERVAL '7 days'
    """))

    content_gaps = [
        {
            "platform": row[0],
            "last_posted": row[1].isoformat() if row[1] else None,
            "days_ago": int(row[2]) if row[2] else None,
        }
        for row in gap_result
    ]

    if not patterns and not recommendations:
        return {
            "patterns": [],
            "recommendations": [{
                "type": "data",
                "suggestion": "Publish more content to enable pattern detection",
                "reason": "Insufficient published post data for analysis",
            }],
            "content_gaps": content_gaps,
        }

    return {
        "patterns": patterns,
        "recommendations": recommendations,
        "content_gaps": content_gaps,
    }
