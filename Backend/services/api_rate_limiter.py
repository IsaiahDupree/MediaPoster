"""
API Rate Limiter & Call Tracker
Manages API usage to stay within monthly budgets
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
import json

# Create models in separate module to avoid circular imports
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

logger = logging.getLogger(__name__)


class APICallLog(Base):
    """Track API calls for rate limiting and budget management"""
    __tablename__ = "api_call_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    api_name = Column(String, index=True)  # 'tiktok_scraper', etc.
    endpoint = Column(String)  # Specific endpoint called
    timestamp = Column(DateTime, default=datetime.now, index=True)
    cost = Column(Float, default=1.0)  # API call cost (default 1 call)
    success = Column(Boolean, default=True)
    cache_hit = Column(Boolean, default=False)
    response_time_ms = Column(Float)
    call_metadata = Column(String)  # JSON metadata


class APIRateLimiter:
    """
    Rate limiter with budget tracking and caching
    
    Features:
    - Monthly budget enforcement (e.g., 250 calls/month)
    - Smart caching to reduce redundant calls
    - Call logging and analytics
    - Configurable limits per API
    """
    
    def __init__(self, db: Session, api_name: str = "tiktok_scraper"):
        """
        Initialize rate limiter
        
        Args:
            db: Database session
            api_name: Name of API to track
        """
        self.db = db
        self.api_name = api_name
        self.cache: Dict[str, Any] = {}
        
        # Budget configurations
        self.budgets = {
            "tiktok_scraper": {
                "monthly_limit": 250,
                "safety_margin": 0.9  # Use only 90% of limit (225 calls)
            }
        }
    
    def can_make_call(self, endpoint: str) -> tuple[bool, str]:
        """
        Check if API call is allowed within budget
        
        Args:
            endpoint: Endpoint to call
            
        Returns:
            Tuple of (allowed, reason)
        """
        config = self.budgets.get(self.api_name, {"monthly_limit": 1000, "safety_margin": 0.9})
        monthly_limit = int(config["monthly_limit"] * config["safety_margin"])
        
        # Get call count for current month
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        call_count = self.db.query(APICallLog).filter(
            APICallLog.api_name == self.api_name,
            APICallLog.timestamp >= month_start,
            APICallLog.success == True,
            APICallLog.cache_hit == False  # Only count real API calls
        ).count()
        
        if call_count >= monthly_limit:
            return False, f"Monthly budget exceeded ({call_count}/{monthly_limit} calls used)"
        
        remaining = monthly_limit - call_count
        if remaining <= 10:
            logger.warning(f"API budget running low: {remaining} calls remaining for {self.api_name}")
        
        return True, f"OK ({remaining} calls remaining)"
    
    def get_cached(self, cache_key: str, ttl_hours: int = 24) -> Optional[Any]:
        """
        Get cached result if available and fresh
        
        Args:
            cache_key: Cache key
            ttl_hours: Time-to-live in hours
            
        Returns:
            Cached data or None
        """
        # Check in-memory cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            age = datetime.now() - timestamp
            
            if age < timedelta(hours=ttl_hours):
                logger.info(f"Cache HIT for {cache_key} (age: {age.seconds/3600:.1f}h)")
                return cached_data
            else:
                del self.cache[cache_key]
        
        return None
    
    def set_cache(self, cache_key: str, data: Any):
        """
        Store data in cache
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        self.cache[cache_key] = (data, datetime.now())
        logger.info(f"Cached data for {cache_key}")
    
    def log_call(
        self,
        endpoint: str,
        success: bool = True,
        cache_hit: bool = False,
        response_time_ms: float = 0,
        call_metadata: Optional[Dict] = None
    ):
        """
        Log an API call
        
        Args:
            endpoint: Endpoint called
            success: Whether call succeeded
            cache_hit: Whether result was from cache
            response_time_ms: Response time in milliseconds
            metadata: Additional metadata
        """
        try:
            log_entry = APICallLog(
                api_name=self.api_name,
                endpoint=endpoint,
                success=success,
                cache_hit=cache_hit,
                response_time_ms=response_time_ms,
                call_metadata=json.dumps(call_metadata) if call_metadata else None
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            if not cache_hit:
                logger.info(f"Logged API call: {self.api_name}/{endpoint} (success: {success})")
            
        except Exception as e:
            logger.error(f"Error logging API call: {e}")
            self.db.rollback()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for current month
        
        Returns:
            Dict with usage stats
        """
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        total_calls = self.db.query(APICallLog).filter(
            APICallLog.api_name == self.api_name,
            APICallLog.timestamp >= month_start
        ).count()
        
        api_calls = self.db.query(APICallLog).filter(
            APICallLog.api_name == self.api_name,
            APICallLog.timestamp >= month_start,
            APICallLog.cache_hit == False,
            APICallLog.success == True
        ).count()
        
        cache_hits = self.db.query(APICallLog).filter(
            APICallLog.api_name == self.api_name,
            APICallLog.timestamp >= month_start,
            APICallLog.cache_hit == True
        ).count()
        
        config = self.budgets.get(self.api_name, {"monthly_limit": 1000, "safety_margin": 0.9})
        monthly_limit = int(config["monthly_limit"] * config["safety_margin"])
        
        return {
            "api_name": self.api_name,
            "month": month_start.strftime("%Y-%m"),
            "total_requests": total_calls,
            "api_calls": api_calls,
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hits / total_calls * 100, 1) if total_calls > 0 else 0,
            "monthly_limit": monthly_limit,
            "remaining": monthly_limit - api_calls,
            "usage_percent": round(api_calls / monthly_limit * 100, 1) if monthly_limit > 0 else 0
        }
    
    def clear_old_logs(self, days: int = 90):
        """
        Clear API logs older than specified days
        
        Args:
            days: Number of days to keep
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        deleted = self.db.query(APICallLog).filter(
            APICallLog.timestamp < cutoff
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleared {deleted} old API call logs")


class CachedTikTokScraperAPI:
    """
    Rate-limited wrapper for TikTok Scraper API with intelligent caching
    """
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        """Initialize with rate limiting and caching"""
        from services.tiktok_scraper import TikTokScraperAPI
        
        self.db = db
        self.api = TikTokScraperAPI(api_key=api_key)
        self.rate_limiter = APIRateLimiter(db, "tiktok_scraper")
    
    async def get_trending_feed(
        self,
        region: str = "US",
        count: int = 20,
        force_refresh: bool = False
    ):
        """
        Get trending feed with caching
        
        Cache TTL: 6 hours (trends update frequently but not minute-by-minute)
        """
        cache_key = f"trending_feed_{region}_{count}"
        
        # Check cache first
        if not force_refresh:
            cached = self.rate_limiter.get_cached(cache_key, ttl_hours=6)
            if cached:
                self.rate_limiter.log_call("get_trending_feed", cache_hit=True)
                return cached
        
        # Check rate limit
        allowed, reason = self.rate_limiter.can_make_call("get_trending_feed")
        if not allowed:
            logger.warning(f"API call blocked: {reason}")
            # Return cached data even if stale
            if cache_key in self.rate_limiter.cache:
                return self.rate_limiter.cache[cache_key][0]
            return []
        
        # Make API call
        start_time = datetime.now()
        try:
            result = await self.api.get_trending_feed(region=region, count=count)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.rate_limiter.set_cache(cache_key, result)
            self.rate_limiter.log_call(
                "get_trending_feed",
                success=True,
                cache_hit=False,
                response_time_ms=response_time,
                call_metadata={"region": region, "count": count}
            )
            
            return result
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self.rate_limiter.log_call(
                "get_trending_feed",
                success=False,
                cache_hit=False,
                response_time_ms=response_time
            )
            logger.error(f"API call failed: {e}")
            return []
    
    async def search_hashtag(
        self,
        hashtag: str,
        count: int = 20,
        cursor: Optional[str] = None
    ):
        """
        Search hashtag with caching
        
        Cache TTL: 12 hours (hashtag content is relatively stable)
        """
        cache_key = f"hashtag_{hashtag}_{count}"
        
        # Check cache
        cached = self.rate_limiter.get_cached(cache_key, ttl_hours=12)
        if cached and cursor is None:  # Don't use cache if paginating
            self.rate_limiter.log_call("search_hashtag", cache_hit=True)
            return cached
        
        # Check rate limit
        allowed, reason = self.rate_limiter.can_make_call("search_hashtag")
        if not allowed:
            logger.warning(f"API call blocked: {reason}")
            if cache_key in self.rate_limiter.cache:
                return self.rate_limiter.cache[cache_key][0]
            return {"videos": [], "cursor": None}
        
        # Make API call
        start_time = datetime.now()
        try:
            result = await self.api.search_hashtag(hashtag=hashtag, count=count, cursor=cursor)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if cursor is None:  # Only cache first page
                self.rate_limiter.set_cache(cache_key, result)
            
            self.rate_limiter.log_call(
                "search_hashtag",
                success=True,
                cache_hit=False,
                response_time_ms=response_time,
                call_metadata={"hashtag": hashtag}
            )
            
            return result
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self.rate_limiter.log_call("search_hashtag", success=False, response_time_ms=response_time)
            return {"videos": [], "cursor": None}
    
    async def get_user_posts(
        self,
        username: str,
        count: int = 20,
        cursor: Optional[str] = None
    ):
        """
        Get user posts with caching
        
        Cache TTL: 24 hours (user content updates but for analysis, daily is fine)
        """
        cache_key = f"user_posts_{username}_{count}"
        
        # Check cache
        cached = self.rate_limiter.get_cached(cache_key, ttl_hours=24)
        if cached and cursor is None:
            self.rate_limiter.log_call("get_user_posts", cache_hit=True)
            return cached
        
        # Check rate limit
        allowed, reason = self.rate_limiter.can_make_call("get_user_posts")
        if not allowed:
            logger.warning(f"API call blocked: {reason}")
            if cache_key in self.rate_limiter.cache:
                return self.rate_limiter.cache[cache_key][0]
            return {"videos": [], "user": None}
        
        # Make API call
        start_time = datetime.now()
        try:
            result = await self.api.get_user_posts(username=username, count=count, cursor=cursor)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if cursor is None:
                self.rate_limiter.set_cache(cache_key, result)
            
            self.rate_limiter.log_call(
                "get_user_posts",
                success=True,
                cache_hit=False,
                response_time_ms=response_time,
                call_metadata={"username": username}
            )
            
            return result
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self.rate_limiter.log_call("get_user_posts", success=False, response_time_ms=response_time)
            return {"videos": [], "user": None}
    
    async def analyze_trending_topics(
        self,
        region: str = "US",
        limit: int = 50
    ):
        """
        Analyze trending topics with caching
        
        Cache TTL: 6 hours (trends update frequently but not minute-by-minute)
        """
        cache_key = f"trending_topics_{region}_{limit}"
        
        # Check cache first
        cached = self.rate_limiter.get_cached(cache_key, ttl_hours=6)
        if cached:
            self.rate_limiter.log_call("analyze_trending_topics", cache_hit=True)
            return cached
        
        # Check rate limit
        allowed, reason = self.rate_limiter.can_make_call("analyze_trending_topics")
        if not allowed:
            logger.warning(f"API call blocked: {reason}")
            # Return cached data even if stale
            if cache_key in self.rate_limiter.cache:
                return self.rate_limiter.cache[cache_key][0]
            return []
        
        # Make API call
        start_time = datetime.now()
        try:
            result = await self.api.analyze_trending_topics(region=region, limit=limit)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.rate_limiter.set_cache(cache_key, result)
            self.rate_limiter.log_call(
                "analyze_trending_topics",
                success=True,
                cache_hit=False,
                response_time_ms=response_time,
                call_metadata={"region": region, "limit": limit}
            )
            
            return result
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self.rate_limiter.log_call(
                "analyze_trending_topics",
                success=False,
                cache_hit=False,
                response_time_ms=response_time
            )
            logger.error(f"API call failed: {e}")
            return []