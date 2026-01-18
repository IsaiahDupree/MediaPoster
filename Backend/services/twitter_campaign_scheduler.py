"""
Twitter Campaign Scheduler
Background service that:
1. Posts due tweets every minute
2. Generates new tweets daily at midnight
3. Runs analytics checkbacks on posted content
"""
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from loguru import logger

from services.twitter_campaign_service import get_campaign_service


class TwitterCampaignScheduler:
    """
    Background scheduler for Twitter campaigns.
    Runs continuously, posting tweets and managing the campaign lifecycle.
    """
    
    def __init__(self):
        self.service = get_campaign_service()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        
        # Configuration
        self.post_check_interval = 60  # Check for due tweets every 60 seconds
        self.daily_generation_hour = 0  # Generate new tweets at midnight
        self.analytics_check_intervals = ['1h', '6h', '24h', '48h', '7d']
        
        self._last_daily_generation = None
        self._check_count = 0
        
    async def start(self):
        """Start the campaign scheduler."""
        if self.is_running:
            logger.warning("Twitter campaign scheduler already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("🐦 Twitter Campaign Scheduler started")
        logger.info(f"   - Post check interval: {self.post_check_interval}s")
        logger.info(f"   - Daily generation hour: {self.daily_generation_hour}:00 UTC")
        
    async def stop(self):
        """Stop the campaign scheduler."""
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("🐦 Twitter Campaign Scheduler stopped")
        
    async def _run_loop(self):
        """Main scheduler loop."""
        while self.is_running:
            self._check_count += 1
            now = datetime.now(timezone.utc)
            
            try:
                # Check if it's time for daily generation
                if self._should_generate_daily(now):
                    logger.info("🌅 Running daily tweet generation...")
                    await self._run_daily_generation()
                    self._last_daily_generation = now.date()
                
                # Process due tweets
                result = await self.service.process_due_tweets()
                
                if result['processed'] > 0:
                    logger.info(f"📤 Processed {result['processed']} tweets: "
                               f"✅ {result['success']} | ❌ {result['failed']}")
                
                # Run analytics checkbacks periodically (every 10 checks)
                if self._check_count % 10 == 0:
                    await self._run_analytics_checkbacks()
                    
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            await asyncio.sleep(self.post_check_interval)
    
    def _should_generate_daily(self, now: datetime) -> bool:
        """Check if we should run daily generation."""
        # Only generate once per day
        if self._last_daily_generation == now.date():
            return False
        
        # Generate at the configured hour
        if now.hour == self.daily_generation_hour and now.minute < 5:
            return True
        
        # Also generate if we've never generated before
        if self._last_daily_generation is None:
            # Check if we have any scheduled tweets for today
            from sqlalchemy import create_engine, text
            engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"))
            
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM scheduled_tweets
                    WHERE status = 'scheduled'
                      AND scheduled_time > NOW()
                      AND scheduled_time < NOW() + INTERVAL '24 hours'
                """))
                count = result.scalar() or 0
                
                if count < 10:  # Less than 10 scheduled, generate more
                    return True
        
        return False
    
    async def _run_daily_generation(self):
        """Run the daily tweet generation."""
        try:
            result = await self.service.run_daily_campaign()
            logger.success(f"✅ Daily generation complete: {result['total_scheduled']} tweets scheduled")
        except Exception as e:
            logger.error(f"Daily generation failed: {e}")
    
    async def _run_analytics_checkbacks(self):
        """Run analytics checkbacks on recent tweets."""
        logger.info("📊 Running analytics checkbacks...")
        
        # Get tweets that need checkbacks
        from sqlalchemy import create_engine, text
        engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"))
        
        checkback_periods = [
            ('1h', timedelta(hours=1)),
            ('6h', timedelta(hours=6)),
            ('24h', timedelta(hours=24)),
            ('48h', timedelta(hours=48)),
            ('7d', timedelta(days=7)),
        ]
        
        for period_name, delta in checkback_periods:
            target_time = datetime.now(timezone.utc) - delta
            
            with engine.connect() as conn:
                # Find tweets posted around target_time that haven't had this checkback
                result = conn.execute(text("""
                    SELECT pt.id, pt.platform_url
                    FROM posted_tweets pt
                    LEFT JOIN analytics_checkbacks ac 
                        ON pt.id = ac.posted_tweet_id AND ac.check_period = :period
                    WHERE pt.posted_at BETWEEN :start AND :end
                      AND ac.id IS NULL
                      AND pt.platform_url IS NOT NULL
                    LIMIT 10
                """), {
                    "period": period_name,
                    "start": target_time - timedelta(minutes=30),
                    "end": target_time + timedelta(minutes=30)
                })
                
                tweets_to_check = result.fetchall()
                
                for row in tweets_to_check:
                    tweet_id, platform_url = str(row[0]), row[1]
                    
                    # In production, fetch actual metrics from Twitter API
                    # For now, record placeholder metrics
                    metrics = {
                        'impressions': 0,
                        'engagements': 0,
                        'likes': 0,
                        'retweets': 0,
                        'replies': 0,
                        'engagement_rate': 0
                    }
                    
                    self.service.record_analytics_checkback(tweet_id, period_name, metrics)
                    logger.debug(f"Recorded {period_name} checkback for tweet {tweet_id}")


# Singleton instance
_scheduler = None

def get_twitter_campaign_scheduler() -> TwitterCampaignScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = TwitterCampaignScheduler()
    return _scheduler


async def start_twitter_campaign_scheduler():
    """Start the Twitter campaign scheduler."""
    scheduler = get_twitter_campaign_scheduler()
    await scheduler.start()
    return scheduler


async def stop_twitter_campaign_scheduler():
    """Stop the Twitter campaign scheduler."""
    scheduler = get_twitter_campaign_scheduler()
    await scheduler.stop()
