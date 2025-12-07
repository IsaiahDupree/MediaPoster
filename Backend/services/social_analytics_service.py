"""
Social Media Analytics Service
Saves and retrieves analytics data from the database
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
import os

logger = logging.getLogger(__name__)


class SocialAnalyticsService:
    """Service for managing social media analytics in the database"""
    
    def __init__(self):
        # Create synchronous database connection
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        self.engine = create_engine(database_url)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
    
    async def get_or_create_account(
        self,
        platform: str,
        username: str,
        profile_data: Dict[str, Any]
    ) -> int:
        """
        Get existing account or create new one
        Returns account_id
        """
        try:
            # Check if account exists
            query = text("""
                SELECT id FROM social_media_accounts
                WHERE platform = :platform AND username = :username
            """)
            
            result = self.db.execute(query, {
                "platform": platform,
                "username": username
            }).fetchone()
            
            if result:
                account_id = result[0]
                
                # Update account info
                update_query = text("""
                    UPDATE social_media_accounts
                    SET 
                        display_name = :display_name,
                        bio = :bio,
                        profile_pic_url = :profile_pic_url,
                        is_verified = :is_verified,
                        is_business = :is_business,
                        updated_at = NOW(),
                        last_fetched_at = NOW()
                    WHERE id = :account_id
                """)
                
                self.db.execute(update_query, {
                    "account_id": account_id,
                    "display_name": profile_data.get("full_name"),
                    "bio": profile_data.get("bio"),
                    "profile_pic_url": profile_data.get("profile_pic_url"),
                    "is_verified": profile_data.get("is_verified", False),
                    "is_business": profile_data.get("is_business", False)
                })
                self.db.commit()
                
                logger.info(f"Updated account: {platform}/@{username} (ID: {account_id})")
                return account_id
            
            else:
                # Create new account
                insert_query = text("""
                    INSERT INTO social_media_accounts (
                        platform, username, display_name, bio, profile_pic_url,
                        is_verified, is_business, last_fetched_at
                    ) VALUES (
                        :platform, :username, :display_name, :bio, :profile_pic_url,
                        :is_verified, :is_business, NOW()
                    )
                    RETURNING id
                """)
                
                result = self.db.execute(insert_query, {
                    "platform": platform,
                    "username": username,
                    "display_name": profile_data.get("full_name"),
                    "bio": profile_data.get("bio"),
                    "profile_pic_url": profile_data.get("profile_pic_url"),
                    "is_verified": profile_data.get("is_verified", False),
                    "is_business": profile_data.get("is_business", False)
                }).fetchone()
                
                self.db.commit()
                account_id = result[0]
                
                logger.info(f"Created new account: {platform}/@{username} (ID: {account_id})")
                return account_id
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error getting/creating account: {e}")
            raise
    
    async def save_analytics_snapshot(
        self,
        account_id: int,
        analytics_data: Dict[str, Any],
        snapshot_date: date = None
    ) -> int:
        """
        Save daily analytics snapshot
        Returns snapshot_id
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        try:
            # Upsert snapshot
            query = text("""
                INSERT INTO social_media_analytics_snapshots (
                    account_id, snapshot_date, followers_count, following_count,
                    posts_count, total_likes, total_comments, total_views,
                    total_shares, engagement_rate, avg_likes_per_post,
                    avg_comments_per_post
                ) VALUES (
                    :account_id, :snapshot_date, :followers_count, :following_count,
                    :posts_count, :total_likes, :total_comments, :total_views,
                    :total_shares, :engagement_rate, :avg_likes_per_post,
                    :avg_comments_per_post
                )
                ON CONFLICT (account_id, snapshot_date)
                DO UPDATE SET
                    followers_count = EXCLUDED.followers_count,
                    following_count = EXCLUDED.following_count,
                    posts_count = EXCLUDED.posts_count,
                    total_likes = EXCLUDED.total_likes,
                    total_comments = EXCLUDED.total_comments,
                    total_views = EXCLUDED.total_views,
                    total_shares = EXCLUDED.total_shares,
                    engagement_rate = EXCLUDED.engagement_rate,
                    avg_likes_per_post = EXCLUDED.avg_likes_per_post,
                    avg_comments_per_post = EXCLUDED.avg_comments_per_post
                RETURNING id
            """)
            
            result = self.db.execute(query, {
                "account_id": account_id,
                "snapshot_date": snapshot_date,
                "followers_count": analytics_data.get("followers_count", 0),
                "following_count": analytics_data.get("following_count", 0),
                "posts_count": analytics_data.get("posts_count", 0),
                "total_likes": analytics_data.get("total_likes", 0),
                "total_comments": analytics_data.get("total_comments", 0),
                "total_views": analytics_data.get("total_views", 0),
                "total_shares": analytics_data.get("total_shares", 0),
                "engagement_rate": analytics_data.get("engagement_rate", 0),
                "avg_likes_per_post": analytics_data.get("avg_likes_per_post", 0),
                "avg_comments_per_post": analytics_data.get("avg_comments_per_post", 0)
            }).fetchone()
            
            self.db.commit()
            snapshot_id = result[0]
            
            logger.info(f"Saved analytics snapshot for account {account_id} on {snapshot_date}")
            return snapshot_id
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving analytics snapshot: {e}")
            raise
    
    async def save_post(
        self,
        account_id: int,
        platform: str,
        post_data: Dict[str, Any]
    ) -> int:
        """
        Save or update a social media post
        Returns post_id
        """
        try:
            # Upsert post
            query = text("""
                INSERT INTO social_media_posts (
                    account_id, platform, external_post_id, post_url,
                    caption, media_type, thumbnail_url, media_url,
                    duration, posted_at
                ) VALUES (
                    :account_id, :platform, :external_post_id, :post_url,
                    :caption, :media_type, :thumbnail_url, :media_url,
                    :duration, :posted_at
                )
                ON CONFLICT (platform, external_post_id)
                DO UPDATE SET
                    caption = EXCLUDED.caption,
                    thumbnail_url = EXCLUDED.thumbnail_url,
                    media_url = EXCLUDED.media_url,
                    updated_at = NOW()
                RETURNING id
            """)
            
            posted_at = post_data.get("posted_at")
            if isinstance(posted_at, str):
                posted_at = datetime.fromisoformat(posted_at)
            
            result = self.db.execute(query, {
                "account_id": account_id,
                "platform": platform,
                "external_post_id": post_data.get("post_id"),
                "post_url": post_data.get("url"),
                "caption": post_data.get("caption", "")[:5000],  # Limit caption length
                "media_type": post_data.get("media_type"),
                "thumbnail_url": post_data.get("thumbnail_url"),
                "media_url": post_data.get("media_url"),
                "duration": post_data.get("duration"),
                "posted_at": posted_at
            }).fetchone()
            
            self.db.commit()
            post_id = result[0]
            
            return post_id
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving post: {e}")
            raise
    
    async def save_post_analytics(
        self,
        post_id: int,
        analytics_data: Dict[str, Any],
        snapshot_date: date = None
    ) -> int:
        """
        Save post analytics for a specific date
        Returns analytics_id
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        try:
            query = text("""
                INSERT INTO social_media_post_analytics (
                    post_id, snapshot_date, likes_count, comments_count,
                    views_count, shares_count, saves_count
                ) VALUES (
                    :post_id, :snapshot_date, :likes_count, :comments_count,
                    :views_count, :shares_count, :saves_count
                )
                ON CONFLICT (post_id, snapshot_date)
                DO UPDATE SET
                    likes_count = EXCLUDED.likes_count,
                    comments_count = EXCLUDED.comments_count,
                    views_count = EXCLUDED.views_count,
                    shares_count = EXCLUDED.shares_count,
                    saves_count = EXCLUDED.saves_count
                RETURNING id
            """)
            
            result = self.db.execute(query, {
                "post_id": post_id,
                "snapshot_date": snapshot_date,
                "likes_count": analytics_data.get("likes", 0),
                "comments_count": analytics_data.get("comments", 0),
                "views_count": analytics_data.get("views", 0),
                "shares_count": analytics_data.get("shares", 0),
                "saves_count": analytics_data.get("saves", 0)
            }).fetchone()
            
            self.db.commit()
            return result[0]
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving post analytics: {e}")
            raise
    
    async def save_hashtags(self, post_id: int, hashtags: List[str]):
        """Save hashtags for a post"""
        try:
            for hashtag in hashtags:
                # Clean hashtag
                hashtag = hashtag.strip().lower().lstrip('#')
                
                if not hashtag:
                    continue
                
                # Upsert hashtag
                hashtag_query = text("""
                    INSERT INTO social_media_hashtags (hashtag, total_uses)
                    VALUES (:hashtag, 1)
                    ON CONFLICT (hashtag)
                    DO UPDATE SET 
                        total_uses = social_media_hashtags.total_uses + 1,
                        updated_at = NOW()
                    RETURNING id
                """)
                
                result = self.db.execute(hashtag_query, {"hashtag": hashtag}).fetchone()
                hashtag_id = result[0]
                
                # Link to post
                link_query = text("""
                    INSERT INTO social_media_post_hashtags (post_id, hashtag_id)
                    VALUES (:post_id, :hashtag_id)
                    ON CONFLICT DO NOTHING
                """)
                
                self.db.execute(link_query, {
                    "post_id": post_id,
                    "hashtag_id": hashtag_id
                })
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving hashtags: {e}")
            raise
    
    async def track_api_usage(
        self,
        provider_name: str,
        platform: str,
        endpoint: str,
        success: bool,
        latency_ms: int = None,
        error_message: str = None
    ):
        """Track API usage for rate limiting monitoring"""
        try:
            query = text("""
                INSERT INTO api_usage_tracking (
                    provider_name, platform, endpoint, request_count,
                    success, latency_ms, error_message
                ) VALUES (
                    :provider_name, :platform, :endpoint, 1,
                    :success, :latency_ms, :error_message
                )
            """)
            
            self.db.execute(query, {
                "provider_name": provider_name,
                "platform": platform,
                "endpoint": endpoint,
                "success": success,
                "latency_ms": latency_ms,
                "error_message": error_message
            })
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error tracking API usage: {e}")
    
    async def get_daily_api_usage(
        self,
        provider_name: str,
        date_to_check: date = None
    ) -> int:
        """Get total API calls made today for a provider"""
        if date_to_check is None:
            date_to_check = date.today()
        
        try:
            query = text("""
                SELECT SUM(request_count) as total
                FROM api_usage_tracking
                WHERE provider_name = :provider_name
                AND date = :date
            """)
            
            result = self.db.execute(query, {
                "provider_name": provider_name,
                "date": date_to_check
            }).fetchone()
            
            return result[0] if result[0] else 0
            
        except Exception as e:
            logger.error(f"Error getting API usage: {e}")
            return 0
    
    async def create_fetch_job(
        self,
        account_id: int,
        job_type: str = "daily_snapshot"
    ) -> int:
        """Create a new analytics fetch job"""
        try:
            query = text("""
                INSERT INTO analytics_fetch_jobs (
                    account_id, job_type, status, started_at
                ) VALUES (
                    :account_id, :job_type, 'running', NOW()
                )
                RETURNING id
            """)
            
            result = self.db.execute(query, {
                "account_id": account_id,
                "job_type": job_type
            }).fetchone()
            
            self.db.commit()
            return result[0]
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating fetch job: {e}")
            raise
    
    async def complete_fetch_job(
        self,
        job_id: int,
        posts_fetched: int,
        status: str = "completed",
        error_message: str = None
    ):
        """Mark fetch job as completed"""
        try:
            query = text("""
                UPDATE analytics_fetch_jobs
                SET 
                    status = :status,
                    completed_at = NOW(),
                    posts_fetched = :posts_fetched,
                    error_message = :error_message
                WHERE id = :job_id
            """)
            
            self.db.execute(query, {
                "job_id": job_id,
                "status": status,
                "posts_fetched": posts_fetched,
                "error_message": error_message
            })
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error completing fetch job: {e}")
    
    async def get_active_accounts(self, platform: str = None) -> List[Dict]:
        """Get all active accounts to monitor"""
        try:
            if platform:
                query = text("""
                    SELECT * FROM social_media_accounts
                    WHERE is_active = true AND platform = :platform
                    ORDER BY last_fetched_at ASC NULLS FIRST
                """)
                result = self.db.execute(query, {"platform": platform})
            else:
                query = text("""
                    SELECT * FROM social_media_accounts
                    WHERE is_active = true
                    ORDER BY last_fetched_at ASC NULLS FIRST
                """)
                result = self.db.execute(query)
            
            accounts = []
            for row in result:
                accounts.append({
                    "id": row[0],
                    "platform": row[1],
                    "username": row[2],
                    "display_name": row[3],
                    "last_fetched_at": row[11]
                })
            
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting active accounts: {e}")
            return []
