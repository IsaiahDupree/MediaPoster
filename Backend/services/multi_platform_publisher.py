"""
Multi-Platform Publishing Service
Orchestrates publishing across all platforms with metrics tracking
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session
from database.models import PlatformPost, PlatformCheckback, PostComment
from services.platform_adapters.base import (
    PlatformAdapter, PlatformType, PublishRequest,
    PublishResult, MetricsSnapshot, CommentData
)
from services.psychology_tagger import PsychologyTagger

logger = logging.getLogger(__name__)


class MultiPlatformPublisher:
    """Manages publishing and tracking across multiple platforms"""
    
    def __init__(self, db: Session):
        """
        Initialize multi-platform publisher
        
        Args:
            db: Database session
        """
        self.db = db
        self.adapters: Dict[str, PlatformAdapter] = {}
        self.sentiment_analyzer = PsychologyTagger()
    
    def register_adapter(self, adapter: PlatformAdapter):
        """
        Register a platform adapter
        
        Args:
            adapter: Platform adapter instance
        """
        platform = adapter.platform_type.value
        self.adapters[platform] = adapter
        logger.info(f"Registered adapter for {platform}")
    
    def get_available_platforms(self) -> List[str]:
        """Get list of registered platforms"""
        return list(self.adapters.keys())
    
    def publish_to_platform(
        self,
        platform: str,
        request: PublishRequest,
        content_variant_id: Optional[uuid.UUID] = None,
        clip_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Publish content to a single platform
        
        Args:
            platform: Platform name
            request: Publishing request
            content_variant_id: Reference to content_variant
            clip_id: Reference to clip
            
        Returns:
            Publishing result with database record
        """
        if platform not in self.adapters:
            return {
                "success": False,
                "error": f"Platform {platform} not registered"
            }
        
        adapter = self.adapters[platform]
        
        try:
            # Check authentication
            if not adapter.is_authenticated():
                return {
                    "success": False,
                    "error": f"Not authenticated with {platform}"
                }
            
            # Publish
            logger.info(f"Publishing to {platform}: {request.title}")
            result: PublishResult = adapter.publish_video(request)
            
            if not result.success:
                logger.error(f"Publishing failed: {result.error_message}")
                return {
                    "success": False,
                    "error": result.error_message
                }
            
            # Create database record
            platform_post = PlatformPost(
                content_variant_id=content_variant_id,
                clip_id=clip_id,
                platform=platform,
                platform_post_id=result.platform_post_id,
                platform_url=result.post_url,
                published_at=result.published_at or datetime.now(),
                status="published",
                title=request.title,
                caption=request.caption,
                hashtags=request.hashtags
            )
            
            self.db.add(platform_post)
            self.db.commit()
            self.db.refresh(platform_post)
            
            logger.info(f"Successfully published to {platform}: {result.post_url}")
            
            return {
                "success": True,
                "platform": platform,
                "post_id": str(platform_post.id),
                "platform_post_id": result.platform_post_id,
                "post_url": result.post_url,
                "published_at": result.published_at
            }
            
        except Exception as e:
            logger.error(f"Error publishing to {platform}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def publish_to_multiple_platforms(
        self,
        platforms: List[str],
        request: PublishRequest,
        content_variant_id: Optional[uuid.UUID] = None,
        clip_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Publish content to multiple platforms
        
        Args:
            platforms: List of platform names
            request: Publishing request
            content_variant_id: Reference to content_variant
            clip_id: Reference to clip
            
        Returns:
            Results for each platform
        """
        results = {}
        
        for platform in platforms:
            result = self.publish_to_platform(
                platform=platform,
                request=request,
                content_variant_id=content_variant_id,
                clip_id=clip_id
            )
            results[platform] = result
        
        # Summary
        successful = sum(1 for r in results.values() if r.get("success"))
        
        return {
            "total_platforms": len(platforms),
            "successful": successful,
            "failed": len(platforms) - successful,
            "results": results
        }
    
    def collect_metrics(
        self,
        post_id: uuid.UUID,
        checkback_hours: int
    ) -> Dict[str, Any]:
        """
        Collect performance metrics for a post
        
        Args:
            post_id: PlatformPost ID
            checkback_hours: Hours since publishing (1, 6, 24, 72, 168)
            
        Returns:
            Collected metrics
        """
        # Get post record
        post = self.db.query(PlatformPost).filter_by(id=post_id).first()
        
        if not post:
            return {"error": "Post not found"}
        
        if post.platform not in self.adapters:
            return {"error": f"Platform {post.platform} not registered"}
        
        adapter = self.adapters[post.platform]
        
        try:
            # Fetch metrics from platform
            logger.info(f"Collecting {checkback_hours}h metrics for post {post.platform_post_id}")
            snapshot = adapter.fetch_metrics(post.platform_post_id)
            
            if not snapshot:
                return {"error": "Failed to fetch metrics"}
            
            # Calculate rates
            like_rate = snapshot.likes / snapshot.views if snapshot.views > 0 else 0
            comment_rate = snapshot.comments / snapshot.views if snapshot.views > 0 else 0
            share_rate = snapshot.shares / snapshot.views if snapshot.views > 0 else 0
            save_rate = snapshot.saves / snapshot.views if snapshot.views > 0 else 0
            
            # Create checkback record
            checkback = PlatformCheckback(
                platform_post_id=post.id,
                checkback_h=checkback_hours,
                views=snapshot.views,
                unique_viewers=snapshot.unique_viewers,
                impressions=snapshot.impressions,
                avg_watch_time_s=snapshot.avg_watch_time_s,
                avg_watch_pct=snapshot.avg_watch_pct,
                retention_curve=snapshot.retention_curve,
                likes=snapshot.likes,
                comments=snapshot.comments,
                shares=snapshot.shares,
                saves=snapshot.saves,
                profile_taps=snapshot.profile_taps,
                link_clicks=snapshot.link_clicks,
                like_rate=like_rate,
                comment_rate=comment_rate,
                share_rate=share_rate,
                save_rate=save_rate
            )
            
            self.db.add(checkback)
            self.db.commit()
            
            logger.info(f"Stored checkback metrics: {snapshot.views} views, {snapshot.likes} likes")
            
            return {
                "success": True,
                "checkback_hours": checkback_hours,
                "metrics": {
                    "views": snapshot.views,
                    "likes": snapshot.likes,
                    "comments": snapshot.comments,
                    "shares": snapshot.shares,
                    "saves": snapshot.saves,
                    "engagement_rate": like_rate + comment_rate + share_rate
                }
            }
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {"error": str(e)}
    
    def collect_comments(
        self,
        post_id: uuid.UUID,
        limit: int = 100,
        analyze_sentiment: bool = True
    ) -> Dict[str, Any]:
        """
        Collect and analyze comments on a post
        
        Args:
            post_id: PlatformPost ID
            limit: Max comments to collect
            analyze_sentiment: Whether to run sentiment analysis
            
        Returns:
            Collected comments with sentiment
        """
        # Get post record
        post = self.db.query(PlatformPost).filter_by(id=post_id).first()
        
        if not post:
            return {"error": "Post not found"}
        
        if post.platform not in self.adapters:
            return {"error": f"Platform {post.platform} not registered"}
        
        adapter = self.adapters[post.platform]
        
        try:
            # Fetch comments
            logger.info(f"Collecting comments for post {post.platform_post_id}")
            comments = adapter.fetch_comments(post.platform_post_id, limit=limit)
            
            stored_count = 0
            sentiment_results = []
            
            for comment_data in comments:
                # Check if comment already exists
                existing = self.db.query(PostComment).filter_by(
                    platform_post_id=post.id,
                    platform_comment_id=comment_data.platform_comment_id
                ).first()
                
                if existing:
                    continue
                
                # Analyze sentiment
                sentiment_score = None
                emotion_tags = []
                intent = None
                
                if analyze_sentiment and self.sentiment_analyzer.is_enabled():
                    sentiment = self.sentiment_analyzer.analyze_sentiment_emotion(
                        comment_data.text
                    )
                    
                    if sentiment and "error" not in sentiment:
                        sentiment_score = sentiment.get("sentiment_score")
                        emotion = sentiment.get("primary_emotion")
                        if emotion:
                            emotion_tags = [emotion]
                        
                        # Determine intent
                        if "?" in comment_data.text:
                            intent = "question"
                        elif sentiment_score and sentiment_score > 0.5:
                            intent = "praise"
                        elif sentiment_score and sentiment_score < -0.3:
                            intent = "critique"
                        else:
                            intent = "engagement"
                    
                    sentiment_results.append({
                        "text": comment_data.text[:50],
                        "sentiment": sentiment_score,
                        "emotion": emotion_tags
                    })
                
                # Store comment
                post_comment = PostComment(
                    platform_post_id=post.id,
                    platform_comment_id=comment_data.platform_comment_id,
                    author_handle=comment_data.author_handle,
                    author_name=comment_data.author_name,
                    text=comment_data.text,
                    created_at_platform=comment_data.created_at,
                    sentiment_score=sentiment_score,
                    emotion_tags=emotion_tags,
                    intent=intent
                )
                
                self.db.add(post_comment)
                stored_count += 1
            
            self.db.commit()
            
            logger.info(f"Stored {stored_count} new comments")
            
            return {
                "success": True,
                "comments_collected": len(comments),
                "comments_stored": stored_count,
                "sentiment_analyzed": len(sentiment_results),
                "sample_sentiments": sentiment_results[:5]
            }
            
        except Exception as e:
            logger.error(f"Error collecting comments: {e}")
            return {"error": str(e)}
    
    def schedule_checkbacks(
        self,
        post_id: uuid.UUID,
        checkback_hours: List[int] = [1, 6, 24, 72, 168]
    ):
        """
        Schedule metric checkbacks for a post
        (In production, this would schedule background jobs)
        
        Args:
            post_id: PlatformPost ID
            checkback_hours: List of hours to check back at
        """
        # This is a placeholder - in production you'd use Celery/RQ/APScheduler
        logger.info(f"Scheduled checkbacks for post {post_id}: {checkback_hours}h")
        
        # For now, just log what would be scheduled
        post = self.db.query(PlatformPost).filter_by(id=post_id).first()
        if post:
            for hours in checkback_hours:
                scheduled_time = post.published_at + timedelta(hours=hours)
                logger.info(f"  - {hours}h checkback at {scheduled_time}")
