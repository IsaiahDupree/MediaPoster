"""
Comments API Endpoints
Fetch and display comments from YouTube videos
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from sqlalchemy import create_engine, text
from pydantic import BaseModel
import os

router = APIRouter(tags=["Comments"])

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
engine = create_engine(DATABASE_URL)


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class CommentResponse(BaseModel):
    comment_id: str
    text: str
    author_name: str
    author_username: Optional[str]
    author_profile_image: Optional[str]
    author_channel_url: Optional[str]
    like_count: int
    published_at: str
    is_reply: bool
    parent_id: Optional[str]
    video_id: Optional[str]
    video_title: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    platform: str


class CommentsListResponse(BaseModel):
    total: int
    comments: List[CommentResponse]
    page: int
    page_size: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/comments", response_model=CommentsListResponse)
async def get_comments(
    platform: Optional[str] = Query(None, description="Filter by platform (youtube, tiktok, etc.)"),
    video_id: Optional[str] = Query(None, description="Filter by video/content ID"),
    author: Optional[str] = Query(None, description="Filter by author username"),
    search: Optional[str] = Query(None, description="Search in comment text"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive, negative, neutral)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    include_replies: bool = Query(True, description="Include reply comments")
):
    """
    Get all comments with filtering and pagination
    """
    conn = engine.connect()
    
    try:
        # Build query
        where_clauses = ["fi.interaction_type = 'comment'"]
        params = {}
        
        if platform:
            where_clauses.append("fi.platform = :platform")
            params['platform'] = platform
        
        if video_id:
            # Find content_id from video_id or external_post_id
            where_clauses.append("""
                (cp.external_post_id = :video_id OR ci.id::text = :video_id)
            """)
            params['video_id'] = video_id
        
        if author:
            where_clauses.append("(f.username ILIKE :author OR f.display_name ILIKE :author)")
            params['author'] = f"%{author}%"
        
        if search:
            where_clauses.append("fi.interaction_value ILIKE :search")
            params['search'] = f"%{search}%"
        
        if sentiment:
            if sentiment == 'positive':
                where_clauses.append("fi.sentiment_score > 0.3")
            elif sentiment == 'negative':
                where_clauses.append("fi.sentiment_score < -0.3")
            elif sentiment == 'neutral':
                where_clauses.append("fi.sentiment_score BETWEEN -0.3 AND 0.3")
        
        if not include_replies:
            where_clauses.append("COALESCE((fi.metadata->>'is_reply')::boolean, false) = false")
        
        where_sql = " AND " + " AND ".join(where_clauses)
        
        # Get total count
        count_query = text(f"""
            SELECT COUNT(DISTINCT fi.id)
            FROM follower_interactions fi
            LEFT JOIN followers f ON fi.follower_id = f.id
            LEFT JOIN content_items ci ON fi.content_id = ci.id
            LEFT JOIN content_posts cp ON ci.id = cp.content_id AND cp.platform = fi.platform
            WHERE 1=1 {where_sql}
        """)
        
        total_result = conn.execute(count_query, params)
        total = total_result.fetchone()[0]
        
        # Get paginated comments
        offset = (page - 1) * page_size
        
        query = text(f"""
            SELECT DISTINCT
                COALESCE(fi.metadata->>'comment_id', fi.id::text) as comment_id,
                fi.interaction_value as text,
                f.display_name as author_name,
                f.username as author_username,
                f.avatar_url as author_profile_image,
                f.profile_url as author_channel_url,
                COALESCE((fi.metadata->>'like_count')::int, 0) as like_count,
                fi.occurred_at as published_at,
                COALESCE((fi.metadata->>'is_reply')::boolean, false) as is_reply,
                fi.metadata->>'parent_id' as parent_id,
                cp.external_post_id as video_id,
                ci.title as video_title,
                fi.sentiment_score,
                fi.sentiment_label,
                fi.platform
            FROM follower_interactions fi
            LEFT JOIN followers f ON fi.follower_id = f.id
            LEFT JOIN content_items ci ON fi.content_id = ci.id
            LEFT JOIN content_posts cp ON ci.id = cp.content_id AND cp.platform = fi.platform
            WHERE 1=1 {where_sql}
            ORDER BY fi.occurred_at DESC
            LIMIT :page_size OFFSET :offset
        """)
        
        params['page_size'] = page_size
        params['offset'] = offset
        
        result = conn.execute(query, params)
        rows = result.fetchall()
        
        comments = []
        for row in rows:
            comments.append(CommentResponse(
                comment_id=row[0] or "",
                text=row[1] or "",
                author_name=row[2] or "Unknown",
                author_username=row[3],
                author_profile_image=row[4],
                author_channel_url=row[5],
                like_count=row[6] or 0,
                published_at=row[7].isoformat() if row[7] else "",
                is_reply=row[8] or False,
                parent_id=row[9],
                video_id=row[10],
                video_title=row[11],
                sentiment_score=float(row[12]) if row[12] is not None else None,
                sentiment_label=row[13],
                platform=row[14] or "unknown"
            ))
        
        return CommentsListResponse(
            total=total,
            comments=comments,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/comments/stats")
async def get_comment_stats(
    platform: Optional[str] = Query(None)
):
    """
    Get comment statistics
    """
    conn = engine.connect()
    
    try:
        where_clause = "WHERE fi.interaction_type = 'comment'"
        params = {}
        
        if platform:
            where_clause += " AND fi.platform = :platform"
            params['platform'] = platform
        
        query = text(f"""
            SELECT 
                COUNT(DISTINCT fi.id) as total_comments,
                COUNT(DISTINCT fi.follower_id) as unique_commenters,
                COUNT(DISTINCT fi.content_id) as videos_with_comments,
                AVG(fi.sentiment_score) as avg_sentiment,
                COUNT(*) FILTER (WHERE fi.sentiment_score > 0.3) as positive_count,
                COUNT(*) FILTER (WHERE fi.sentiment_score < -0.3) as negative_count,
                COUNT(*) FILTER (WHERE fi.sentiment_score BETWEEN -0.3 AND 0.3) as neutral_count
            FROM follower_interactions fi
            {where_clause}
        """)
        
        result = conn.execute(query, params)
        row = result.fetchone()
        
        return {
            "total_comments": row[0] or 0,
            "unique_commenters": row[1] or 0,
            "videos_with_comments": row[2] or 0,
            "avg_sentiment": float(row[3]) if row[3] else None,
            "positive_count": row[4] or 0,
            "negative_count": row[5] or 0,
            "neutral_count": row[6] or 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

