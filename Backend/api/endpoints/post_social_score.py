"""
Post-Social Score API Endpoints
Phase 3: Pre/Post Social Score + Coaching
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from database.connection import get_db
from services.post_social_score import PostSocialScoreCalculator
from loguru import logger

router = APIRouter(prefix="/api/post-social-score", tags=["Post-Social Score"])


class PostSocialScoreResponse(BaseModel):
    """Response model for post-social score"""
    post_id: int
    post_social_score: float
    raw_score: float
    percentile_rank: dict
    normalization_factors: dict
    metrics: dict


@router.get("/post/{post_id}", response_model=PostSocialScoreResponse)
async def get_post_social_score(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate and return post-social score for a specific post
    
    This calculates a normalized performance score (0-100) that accounts for:
    - Follower count
    - Platform behavior
    - Time since posting
    - Percentile ranking vs user's other content
    """
    calculator = PostSocialScoreCalculator(db)
    
    try:
        # Get post data
        post_query = text("""
            SELECT 
                smp.id,
                smp.platform,
                smp.media_type,
                smp.posted_at,
                sa.followers_count
            FROM social_media_posts smp
            JOIN social_media_accounts sa ON smp.account_id = sa.id
            WHERE smp.id = :post_id
        """)
        
        post_result = await db.execute(post_query, {"post_id": post_id})
        post = post_result.first()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Get latest metrics
        metrics_query = text("""
            SELECT 
                views_count,
                likes_count,
                comments_count,
                shares_count,
                saves_count
            FROM social_media_post_analytics
            WHERE post_id = :post_id
            ORDER BY snapshot_date DESC, snapshot_hour DESC NULLS LAST
            LIMIT 1
        """)
        
        metrics_result = await db.execute(metrics_query, {"post_id": post_id})
        metrics_row = metrics_result.first()
        
        if not metrics_row:
            raise HTTPException(status_code=404, detail="No metrics found for this post")
        
        current_metrics = {
            'views': metrics_row.views_count or 0,
            'likes': metrics_row.likes_count or 0,
            'comments': metrics_row.comments_count or 0,
            'shares': metrics_row.shares_count or 0,
            'saves': metrics_row.saves_count or 0
        }
        
        # Calculate score
        score_data = await calculator.calculate_post_social_score(
            db=db,
            post_id=post.id,
            platform=post.platform,
            media_type=post.media_type or 'video',
            follower_count=post.followers_count or 0,
            posted_at=post.posted_at,
            current_metrics=current_metrics
        )
        
        return PostSocialScoreResponse(
            post_id=post_id,
            **score_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating post-social score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/post/{post_id}/calculate")
async def calculate_and_store_post_social_score(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate post-social score and store it in the database
    
    This endpoint calculates the score and updates the post_metrics table
    """
    calculator = PostSocialScoreCalculator(db)
    
    try:
        # Get post data and calculate score (same as GET endpoint)
        post_query = text("""
            SELECT 
                smp.id,
                smp.platform,
                smp.media_type,
                smp.posted_at,
                sa.followers_count
            FROM social_media_posts smp
            JOIN social_media_accounts sa ON smp.account_id = sa.id
            WHERE smp.id = :post_id
        """)
        
        post_result = await db.execute(post_query, {"post_id": post_id})
        post = post_result.first()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Get latest metrics
        metrics_query = text("""
            SELECT 
                views_count,
                likes_count,
                comments_count,
                shares_count,
                saves_count
            FROM social_media_post_analytics
            WHERE post_id = :post_id
            ORDER BY snapshot_date DESC, snapshot_hour DESC NULLS LAST
            LIMIT 1
        """)
        
        metrics_result = await db.execute(metrics_query, {"post_id": post_id})
        metrics_row = metrics_result.first()
        
        if not metrics_row:
            raise HTTPException(status_code=404, detail="No metrics found for this post")
        
        current_metrics = {
            'views': metrics_row.views_count or 0,
            'likes': metrics_row.likes_count or 0,
            'comments': metrics_row.comments_count or 0,
            'shares': metrics_row.shares_count or 0,
            'saves': metrics_row.saves_count or 0
        }
        
        # Calculate score
        score_data = await calculator.calculate_post_social_score(
            db=db,
            post_id=post.id,
            platform=post.platform,
            media_type=post.media_type or 'video',
            follower_count=post.followers_count or 0,
            posted_at=post.posted_at,
            current_metrics=current_metrics
        )
        
        # Store in post_metrics table (if it exists)
        # Note: This assumes post_metrics has a post_social_score column
        try:
            update_query = text("""
                UPDATE social_media_post_analytics
                SET 
                    viral_score = :post_social_score,
                    updated_at = NOW()
                WHERE post_id = :post_id
                AND snapshot_date = (
                    SELECT MAX(snapshot_date)
                    FROM social_media_post_analytics
                    WHERE post_id = :post_id
                )
            """)
            
            await db.execute(update_query, {
                'post_id': post_id,
                'post_social_score': score_data['post_social_score']
            })
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not update post_metrics: {e}")
            # Continue even if update fails
        
        return {
            "message": "Post-social score calculated and stored",
            "post_id": post_id,
            **score_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating and storing post-social score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account/{account_id}/summary")
async def get_account_post_scores_summary(
    account_id: int,
    platform: Optional[str] = None,
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of post-social scores for an account
    
    Returns top performing posts and overall statistics
    """
    calculator = PostSocialScoreCalculator(db)
    
    try:
        # Get all posts for account (with error handling for missing tables)
        try:
            posts_query = text("""
                SELECT 
                    smp.id,
                    smp.platform,
                    smp.media_type,
                    smp.posted_at,
                    sa.followers_count
                FROM social_media_posts smp
                JOIN social_media_accounts sa ON smp.account_id = sa.id
                WHERE smp.account_id = :account_id
            """)
            
            if platform:
                posts_query = text(str(posts_query) + " AND smp.platform = :platform")
            
            posts_result = await db.execute(
                posts_query,
                {"account_id": account_id, "platform": platform} if platform else {"account_id": account_id}
            )
            posts = posts_result.fetchall()
        except Exception as table_error:
            logger.warning(f"Table social_media_posts may not exist: {table_error}")
            return {
                "account_id": account_id,
                "total_posts": 0,
                "average_score": 0,
                "top_posts": []
            }
        
        if not posts:
            return {
                "account_id": account_id,
                "total_posts": 0,
                "average_score": 0,
                "top_posts": []
            }
        
        # Calculate scores for all posts
        scores = []
        for post in posts:
            # Get metrics
            metrics_query = text("""
                SELECT 
                    views_count,
                    likes_count,
                    comments_count,
                    shares_count,
                    saves_count
                FROM social_media_post_analytics
                WHERE post_id = :post_id
                ORDER BY snapshot_date DESC, snapshot_hour DESC NULLS LAST
                LIMIT 1
            """)
            
            metrics_result = await db.execute(metrics_query, {"post_id": post.id})
            metrics_row = metrics_result.first()
            
            if metrics_row:
                current_metrics = {
                    'views': metrics_row.views_count or 0,
                    'likes': metrics_row.likes_count or 0,
                    'comments': metrics_row.comments_count or 0,
                    'shares': metrics_row.shares_count or 0,
                    'saves': metrics_row.saves_count or 0
                }
                
                score_data = await calculator.calculate_post_social_score(
                    db=db,
                    post_id=post.id,
                    platform=post.platform,
                    media_type=post.media_type or 'video',
                    follower_count=post.followers_count or 0,
                    posted_at=post.posted_at,
                    current_metrics=current_metrics
                )
                
                scores.append({
                    'post_id': post.id,
                    'platform': post.platform,
                    'media_type': post.media_type,
                    'score': score_data['post_social_score'],
                    'percentile': score_data['percentile_rank']
                })
        
        # Sort by score
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Calculate average
        avg_score = sum(s['score'] for s in scores) / len(scores) if scores else 0
        
        return {
            "account_id": account_id,
            "total_posts": len(scores),
            "average_score": round(avg_score, 1),
            "top_posts": scores[:limit]
        }
        
    except Exception as e:
        logger.error(f"Error getting account post scores summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

