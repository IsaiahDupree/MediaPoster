"""
Analytics Scheduler - Background task system for periodic analytics collection
Uses APScheduler for reliable scheduling
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger
import os

from modules.analytics.youtube_analytics import YouTubeAnalytics
from modules.analytics.sentiment_analyzer import SentimentAnalyzer
from database.models.monitoring import PostSubmission, PostAnalytics, PostComment
from database.database import get_db


class AnalyticsScheduler:
    """Schedule and run periodic analytics collection"""
    
    # Check intervals (hours since publication)
    INTERVALS = [1, 6, 24, 168]  # 1h, 6h, 24h, 7days
    
    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = BackgroundScheduler()
        self.youtube = YouTubeAnalytics()
        self.sentiment = SentimentAnalyzer(backend="vader")
        
        logger.info("Analytics Scheduler initialized")
    
    def start(self):
        """Start the background scheduler"""
        # Schedule analytics collection every 15 minutes
        self.scheduler.add_job(
            func=self.collect_pending_analytics,
            trigger=IntervalTrigger(minutes=15),
            id='analytics_collection',
            name='Collect pending analytics',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Analytics scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Analytics scheduler stopped")
    
    def collect_pending_analytics(self):
        """Find and collect analytics for posts needing updates"""
        logger.info("Running analytics collection cycle...")
        
        db = next(get_db())
        
        try:
            # Find published posts
            posts = db.query(PostSubmission).filter(
                PostSubmission.status == 'published',
                PostSubmission.platform_url.isnot(None)
            ).all()
            
            logger.info(f"Found {len(posts)} published posts")
            
            for post in posts:
                if self._needs_analytics_check(post, db):
                    self._collect_post_analytics(post, db)
            
            db.commit()
            logger.success("Analytics collection cycle complete")
            
        except Exception as e:
            logger.error(f"Analytics collection failed: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _needs_analytics_check(self, post: PostSubmission, db) -> bool:
        """Determine if post needs analytics check"""
        if not post.published_at:
            return False
        
        # Hours since publication
        hours_since = (datetime.utcnow() - post.published_at).total_seconds() / 3600
        
        # Check which interval we're in
        for interval in self.INTERVALS:
            if hours_since >= interval:
                # Check if we've collected for this interval
                existing = db.query(PostAnalytics).filter(
                    PostAnalytics.submission_id == post.id,
                    PostAnalytics.hours_since_publish >= interval - 0.5,
                    PostAnalytics.hours_since_publish <= interval + 0.5
                ).first()
                
                if not existing:
                    logger.info(f"Post {post.submission_id[:8]} needs {interval}h check")
                    return True
        
        return False
    
    def _collect_post_analytics(self, post: PostSubmission, db):
        """Collect analytics for a specific post"""
        logger.info(f"Collecting analytics for {post.platform} post {post.submission_id[:8]}")
        
        try:
            hours_since = (datetime.utcnow() - post.published_at).total_seconds() / 3600
            
            # Platform-specific collection
            if post.platform == 'youtube':
                self._collect_youtube_analytics(post, hours_since, db)
            elif post.platform == 'instagram':
                logger.warning(f"Instagram analytics not yet implemented")
            elif post.platform == 'tiktok':
                logger.warning(f"TikTok analytics not yet implemented")
            else:
                logger.warning(f"Analytics not implemented for {post.platform}")
                
        except Exception as e:
            logger.error(f"Failed to collect analytics for {post.submission_id}: {e}")
    
    def _collect_youtube_analytics(self, post: PostSubmission, hours_since: float, db):
        """Collect YouTube-specific analytics"""
        if not post.platform_url:
            return
        
        # Get video stats
        stats = self.youtube.get_video_stats(post.platform_url)
        
        if not stats:
            logger.warning(f"Could not fetch YouTube stats for {post.submission_id[:8]}")
            return
        
        # Calculate engagement rate
        views = stats['views']
        engagement = stats['likes'] + stats['comments_count']
        engagement_rate = (engagement / views * 100) if views > 0 else 0.0
        
        # Get comments for sentiment
        comments = self.youtube.get_comments(post.platform_url, max_results=50)
        
        # Analyze sentiment
        sentiment_data = {'sentiment_score': 0.0, 'positive_pct': 0.0, 'negative_pct': 0.0, 'neutral_pct': 0.0}
        
        if comments:
            comment_texts = [c['text'] for c in comments]
            sentiment_data = self.sentiment.get_overall_sentiment(comment_texts)
            
            # Store individual comments
            for comment in comments[:20]:  # Store top 20
                comment_result = self.sentiment.analyze_comment(comment['text'])
                
                db_comment = PostComment(
                    submission_id=post.id,
                    comment_id=comment['comment_id'],
                    author=comment['author'],
                    text=comment['text'][:500],  # Truncate
                    sentiment=comment_result['sentiment'],
                    sentiment_score=comment_result['score'],
                    posted_at=datetime.fromisoformat(comment['posted_at'].replace('Z', '+00:00')),
                    likes_count=comment['likes_count']
                )
                
                # Check if comment already exists
                existing_comment = db.query(PostComment).filter(
                    PostComment.comment_id == comment['comment_id']
                ).first()
                
                if not existing_comment:
                    db.add(db_comment)
        
        # Create analytics record
        analytics = PostAnalytics(
            submission_id=post.id,
            hours_since_publish=hours_since,
            views=stats['views'],
            likes=stats['likes'],
            comments_count=stats['comments_count'],
            engagement_rate=engagement_rate,
            like_rate=(stats['likes'] / views * 100) if views > 0 else 0.0,
            sentiment_score=sentiment_data['sentiment_score'],
            sentiment_positive=sentiment_data['positive_pct'],
            sentiment_negative=sentiment_data['negative_pct'],
            sentiment_neutral=sentiment_data['neutral_pct'],
            raw_data=stats
        )
        
        db.add(analytics)
        
        logger.success(f"Analytics collected: {views} views, {stats['likes']} likes, "
                      f"{stats['comments_count']} comments, sentiment: {sentiment_data['sentiment_score']:.2f}")
    
    def force_collect(self, submission_id: str):
        """Force immediate analytics collection for a post"""
        logger.info(f"Force collecting analytics for {submission_id}")
        
        db = next(get_db())
        
        try:
            post = db.query(PostSubmission).filter(
                PostSubmission.submission_id == submission_id
            ).first()
            
            if not post:
                logger.error(f"Post not found: {submission_id}")
                return False
            
            self._collect_post_analytics(post, db)
            db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Force collection failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()


# Singleton instance
_scheduler_instance: Optional[AnalyticsScheduler] = None


def get_scheduler() -> AnalyticsScheduler:
    """Get or create scheduler instance"""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = AnalyticsScheduler()
    
    return _scheduler_instance


def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the global scheduler"""
    global _scheduler_instance
    
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None


# Example usage
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    logger.info("Starting analytics scheduler test...")
    
    scheduler = start_scheduler()
    
    logger.info("Scheduler running. Running immediate collection...")
    scheduler.collect_pending_analytics()
    
    logger.info("\nScheduler is now running in background.")
    logger.info("It will check for pending analytics every 15 minutes.")
    logger.info("Press Ctrl+C to stop")
    
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("\nStopping scheduler...")
        stop_scheduler()
        logger.info("Scheduler stopped")
