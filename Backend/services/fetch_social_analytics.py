"""
Fetch Social Media Analytics Script
Pulls analytics data for all monitored accounts with rate limiting
"""
import asyncio
import logging
import time
from datetime import date, datetime
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from services.scrapers import Platform, get_factory
from services.social_analytics_service import SocialAnalyticsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Rate Limiting Configuration
RATE_LIMITS = {
    "tiktok": {
        "daily_limit": 600000,  # PRO tier: 600K/month = ~20K/day
        "safety_margin": 0.8,   # Use only 80% to be safe
        "requests_per_account": 100  # Profile + posts
    },
    "instagram": {
        "daily_limit": 10000,
        "safety_margin": 0.8,
        "requests_per_account": 100
    }
}


class SocialAnalyticsFetcher:
    """Fetches and saves social media analytics"""
    
    def __init__(self):
        self.factory = get_factory()
        self.service = SocialAnalyticsService()
        self.stats = {
            "accounts_processed": 0,
            "posts_saved": 0,
            "errors": 0,
            "api_calls_made": 0
        }
    
    async def check_rate_limit(self, platform: str) -> bool:
        """Check if we can make more API calls today"""
        config = RATE_LIMITS.get(platform, {"daily_limit": 1000, "safety_margin": 0.8})
        daily_limit = config["daily_limit"] * config["safety_margin"]
        
        # Get today's usage
        usage = await self.service.get_daily_api_usage(
            provider_name=f"{platform}_provider",
            date_to_check=date.today()
        )
        
        remaining = daily_limit - usage
        logger.info(f"📊 {platform.upper()} API Usage: {usage}/{int(daily_limit)} ({remaining} remaining)")
        
        return remaining > 100  # Need at least 100 requests left
    
    async def fetch_account_analytics(
        self,
        platform: str,
        username: str,
        posts_limit: int = 50
    ) -> Dict:
        """
        Fetch complete analytics for one account
        
        Returns:
            Dict with analytics data and status
        """
        start_time = time.time()
        
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"📊 Fetching analytics for {platform}/@{username}")
            logger.info(f"{'='*80}")
            
            # Check rate limit
            if not await self.check_rate_limit(platform):
                logger.warning(f"⚠️  Rate limit reached for {platform}, skipping...")
                return {
                    "success": False,
                    "error": "Rate limit reached",
                    "username": username
                }
            
            # Fetch analytics
            analytics = await self.factory.execute_with_fallback(
                Platform[platform.upper()],
                "get_analytics",
                username,
                posts_limit
            )
            
            if not analytics:
                logger.error(f"❌ Failed to fetch analytics for @{username}")
                return {
                    "success": False,
                    "error": "Failed to fetch analytics",
                    "username": username
                }
            
            # Track API usage
            elapsed_ms = (time.time() - start_time) * 1000
            await self.service.track_api_usage(
                provider_name=f"{platform}_provider",
                platform=platform,
                endpoint="get_analytics",
                success=True,
                latency_ms=int(elapsed_ms)
            )
            
            self.stats["api_calls_made"] += 2  # Profile + posts
            
            # Save to database
            logger.info(f"💾 Saving data to database...")
            
            # 1. Get or create account
            account_id = await self.service.get_or_create_account(
                platform=platform,
                username=username,
                profile_data={
                    "full_name": analytics.profile.full_name,
                    "bio": analytics.profile.bio,
                    "profile_pic_url": analytics.profile.profile_pic_url,
                    "is_verified": analytics.profile.is_verified,
                    "is_business": analytics.profile.is_business
                }
            )
            
            # 2. Save analytics snapshot
            await self.service.save_analytics_snapshot(
                account_id=account_id,
                analytics_data={
                    "followers_count": analytics.profile.followers_count,
                    "following_count": analytics.profile.following_count,
                    "posts_count": analytics.profile.posts_count,
                    "total_likes": analytics.total_likes,
                    "total_comments": analytics.total_comments,
                    "total_views": analytics.total_views,
                    "total_shares": analytics.total_shares,
                    "engagement_rate": analytics.engagement_rate,
                    "avg_likes_per_post": analytics.avg_likes_per_post,
                    "avg_comments_per_post": analytics.avg_comments_per_post
                }
            )
            
            # 3. Save all posts
            posts_saved = 0
            for post in analytics.posts:
                try:
                    # Save post
                    post_id = await self.service.save_post(
                        account_id=account_id,
                        platform=platform,
                        post_data={
                            "post_id": post.post_id,
                            "url": post.url,
                            "caption": post.caption,
                            "media_type": post.media_type,
                            "thumbnail_url": post.thumbnail_url,
                            "media_url": post.media_url,
                            "duration": post.duration,
                            "posted_at": post.posted_at
                        }
                    )
                    
                    # Save post analytics
                    await self.service.save_post_analytics(
                        post_id=post_id,
                        analytics_data={
                            "likes": post.likes_count,
                            "comments": post.comments_count,
                            "views": post.views_count,
                            "shares": post.shares_count
                        }
                    )
                    
                    posts_saved += 1
                    
                except Exception as e:
                    logger.error(f"Error saving post {post.post_id}: {e}")
                    continue
            
            # 4. Save hashtags
            if analytics.top_hashtags and analytics.best_performing_post:
                best_post_query = f"SELECT id FROM social_media_posts WHERE external_post_id = '{analytics.best_performing_post.post_id}' LIMIT 1"
                # Save hashtags logic here if needed
            
            logger.info(f"✅ Saved {posts_saved} posts for @{username}")
            self.stats["posts_saved"] += posts_saved
            self.stats["accounts_processed"] += 1
            
            return {
                "success": True,
                "username": username,
                "posts_saved": posts_saved,
                "total_views": analytics.total_views,
                "total_likes": analytics.total_likes,
                "engagement_rate": analytics.engagement_rate
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching analytics for @{username}: {e}")
            self.stats["errors"] += 1
            
            # Track failed API call
            await self.service.track_api_usage(
                provider_name=f"{platform}_provider",
                platform=platform,
                endpoint="get_analytics",
                success=False,
                error_message=str(e)
            )
            
            return {
                "success": False,
                "error": str(e),
                "username": username
            }
    
    async def fetch_all_monitored_accounts(self, platform: str = None):
        """Fetch analytics for all active monitored accounts"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 Starting Analytics Fetch Job")
        logger.info(f"{'='*80}\n")
        
        # Get active accounts
        accounts = await self.service.get_active_accounts(platform=platform)
        
        if not accounts:
            logger.info("No active accounts to monitor")
            return
        
        logger.info(f"📋 Found {len(accounts)} active accounts to monitor\n")
        
        results = []
        
        for account in accounts:
            platform_name = account["platform"]
            username = account["username"]
            
            # Create fetch job
            job_id = await self.service.create_fetch_job(
                account_id=account["id"],
                job_type="daily_snapshot"
            )
            
            try:
                # Fetch analytics
                result = await self.fetch_account_analytics(
                    platform=platform_name,
                    username=username,
                    posts_limit=50
                )
                
                results.append(result)
                
                # Complete job
                await self.service.complete_fetch_job(
                    job_id=job_id,
                    posts_fetched=result.get("posts_saved", 0),
                    status="completed" if result["success"] else "failed",
                    error_message=result.get("error")
                )
                
                # Rate limiting delay
                await asyncio.sleep(2)  # 2 second delay between accounts
                
            except Exception as e:
                logger.error(f"Error processing account @{username}: {e}")
                await self.service.complete_fetch_job(
                    job_id=job_id,
                    posts_fetched=0,
                    status="failed",
                    error_message=str(e)
                )
        
        # Print summary
        self.print_summary(results)
    
    def print_summary(self, results: List[Dict]):
        """Print summary of fetch job"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 ANALYTICS FETCH SUMMARY")
        logger.info(f"{'='*80}\n")
        
        logger.info(f"Accounts Processed: {self.stats['accounts_processed']}")
        logger.info(f"Posts Saved: {self.stats['posts_saved']}")
        logger.info(f"API Calls Made: {self.stats['api_calls_made']}")
        logger.info(f"Errors: {self.stats['errors']}")
        
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        if successful:
            logger.info(f"\n✅ Successful ({len(successful)}):")
            for result in successful:
                logger.info(
                    f"  - @{result['username']}: "
                    f"{result.get('posts_saved', 0)} posts, "
                    f"{result.get('total_views', 0):,} views, "
                    f"{result.get('engagement_rate', 0)}% engagement"
                )
        
        if failed:
            logger.info(f"\n❌ Failed ({len(failed)}):")
            for result in failed:
                logger.info(f"  - @{result['username']}: {result.get('error', 'Unknown error')}")
        
        logger.info(f"\n{'='*80}\n")


async def fetch_single_account(platform: str, username: str):
    """Fetch analytics for a single account"""
    fetcher = SocialAnalyticsFetcher()
    result = await fetcher.fetch_account_analytics(platform, username, posts_limit=100)
    fetcher.print_summary([result])
    return result


async def fetch_all_accounts(platform: str = None):
    """Fetch analytics for all monitored accounts"""
    fetcher = SocialAnalyticsFetcher()
    await fetcher.fetch_all_monitored_accounts(platform=platform)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Fetch specific account
        if len(sys.argv) == 3:
            platform = sys.argv[1]
            username = sys.argv[2]
            asyncio.run(fetch_single_account(platform, username))
        else:
            print("Usage: python fetch_social_analytics.py [platform] [username]")
            print("   or: python fetch_social_analytics.py  (to fetch all)")
    else:
        # Fetch all accounts
        asyncio.run(fetch_all_accounts())
