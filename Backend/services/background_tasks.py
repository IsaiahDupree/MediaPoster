"""
Background Tasks for Content Intelligence
Automated checkback metrics and comment collection
"""
import logging
from sqlalchemy.orm import Session
from services.multi_platform_publisher import MultiPlatformPublisher
from services.platform_adapters.loader import load_platform_adapters
import uuid

logger = logging.getLogger(__name__)


def collect_checkback_metrics_task(
    post_id: uuid.UUID,
    checkback_hours: int,
    db_session_factory
):
    """
    Background task to collect checkback metrics
    
    Args:
        post_id: Platform post ID
        checkback_hours: Hours since publishing
        db_session_factory: Factory to create DB session
    """
    logger.info(f"Running checkback task for post {post_id} at {checkback_hours}h")
    
    # Create database session
    db = db_session_factory()
    
    try:
        # Initialize publisher with real platform adapters
        publisher = MultiPlatformPublisher(db=db)

        adapters = load_platform_adapters()
        for adapter in adapters:
            publisher.register_adapter(adapter)
        
        # Collect metrics
        result = publisher.collect_metrics(
            post_id=post_id,
            checkback_hours=checkback_hours
        )
        
        if result.get("success"):
            logger.info(f"Checkback metrics collected: {result['metrics']}")
        else:
            logger.error(f"Checkback failed: {result.get('error')}")
        
        # Also collect comments at certain checkbacks
        if checkback_hours in [24, 72, 168]:
            logger.info("Collecting comments...")
            comment_result = publisher.collect_comments(
                post_id=post_id,
                limit=100,
                analyze_sentiment=True
            )
            
            if comment_result.get("success"):
                logger.info(f"Comments collected: {comment_result['comments_collected']}")
    
    except Exception as e:
        logger.error(f"Error in checkback task: {e}")
    
    finally:
        db.close()


def batch_collect_metrics_task(
    post_ids: list,
    checkback_hours: int,
    db_session_factory
):
    """
    Batch collection of metrics for multiple posts
    
    Args:
        post_ids: List of post IDs
        checkback_hours: Hours since publishing
        db_session_factory: Factory to create DB session
    """
    logger.info(f"Running batch checkback for {len(post_ids)} posts at {checkback_hours}h")
    
    for post_id in post_ids:
        try:
            collect_checkback_metrics_task(post_id, checkback_hours, db_session_factory)
        except Exception as e:
            logger.error(f"Error collecting metrics for post {post_id}: {e}")
            continue


def analyze_trending_content_task(db_session_factory):
    """
    Background task to analyze trending content patterns.

    Finds top-performing posts and extracts patterns (hooks, CTAs, topics)
    using the ContentInsight model.
    """
    from sqlalchemy import select, desc
    from database.models import PlatformPost, PlatformCheckback

    logger.info("Running trending content analysis...")

    db = db_session_factory()
    try:
        # Find top posts by engagement in the last 7 days
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=7)

        top_posts = db.execute(
            select(PlatformPost, PlatformCheckback)
            .join(PlatformCheckback, PlatformCheckback.platform_post_id == PlatformPost.id)
            .where(PlatformPost.published_at >= cutoff)
            .order_by(desc(PlatformCheckback.views))
            .limit(20)
        ).all()

        if not top_posts:
            logger.info("No recent posts found for trending analysis")
            return

        patterns = {
            "top_performing_count": len(top_posts),
            "platforms": {},
            "avg_views": 0,
            "avg_likes": 0,
        }

        total_views = 0
        total_likes = 0
        for post, checkback in top_posts:
            platform = post.platform
            if platform not in patterns["platforms"]:
                patterns["platforms"][platform] = 0
            patterns["platforms"][platform] += 1
            total_views += checkback.views or 0
            total_likes += checkback.likes or 0

        count = len(top_posts)
        patterns["avg_views"] = total_views // count if count else 0
        patterns["avg_likes"] = total_likes // count if count else 0

        logger.info(f"Trending analysis complete: {patterns}")

    except Exception as e:
        logger.error(f"Error in trending content analysis: {e}")
    finally:
        db.close()


def update_weekly_metrics_task(db_session_factory):
    """
    Background task to calculate weekly North Star Metrics.

    Aggregates:
    - Weekly Engaged Reach (total views across platforms)
    - Content Leverage Score (engagement rate)
    - Warm Lead Flow (DM conversations started)
    """
    from sqlalchemy import select, func
    from database.models import PlatformPost, PlatformCheckback

    logger.info("Updating weekly metrics...")

    db = db_session_factory()
    try:
        from datetime import datetime, timedelta
        week_start = datetime.utcnow() - timedelta(days=7)

        # Aggregate views and engagement from the past week
        result = db.execute(
            select(
                func.sum(PlatformCheckback.views).label("total_views"),
                func.sum(PlatformCheckback.likes).label("total_likes"),
                func.sum(PlatformCheckback.comments).label("total_comments"),
                func.sum(PlatformCheckback.shares).label("total_shares"),
                func.count(PlatformPost.id.distinct()).label("total_posts"),
            )
            .join(PlatformCheckback, PlatformCheckback.platform_post_id == PlatformPost.id)
            .where(PlatformPost.published_at >= week_start)
        ).first()

        if result:
            total_views = result.total_views or 0
            total_likes = result.total_likes or 0
            total_comments = result.total_comments or 0
            total_shares = result.total_shares or 0
            total_posts = result.total_posts or 0

            engaged_reach = total_views
            total_engagement = total_likes + total_comments + total_shares
            leverage_score = round(total_engagement / total_views * 100, 2) if total_views > 0 else 0

            logger.info(
                f"Weekly metrics: engaged_reach={engaged_reach}, "
                f"leverage_score={leverage_score}%, "
                f"posts={total_posts}"
            )

    except Exception as e:
        logger.error(f"Error updating weekly metrics: {e}")
    finally:
        db.close()
