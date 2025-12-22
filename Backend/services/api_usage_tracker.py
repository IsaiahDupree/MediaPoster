"""
API Usage Tracker - Strategic API Call Management
Tracks API calls, manages budgets, and optimizes usage to stay within limits.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class APIProvider(Enum):
    """Supported API providers - Blotato social media platforms only"""
    RAPIDAPI_TIKTOK = "rapidapi_tiktok"
    RAPIDAPI_TIKTOK_SCRAPER7 = "rapidapi_tiktok_scraper7"
    RAPIDAPI_INSTAGRAM = "rapidapi_instagram"
    RAPIDAPI_INSTAGRAM_STATS = "rapidapi_instagram_stats"
    RAPIDAPI_YOUTUBE = "rapidapi_youtube"
    RAPIDAPI_TWITTER = "rapidapi_twitter"
    BLOTATO = "blotato"


@dataclass
class APITier:
    """Represents an API pricing tier"""
    name: str
    monthly_limit: int
    cost_usd: float
    overage_cost_per_call: float = 0.0  # Cost per call over limit
    
    @property
    def cost_per_call(self) -> float:
        if self.monthly_limit == 0:
            return 0.0
        return self.cost_usd / self.monthly_limit


@dataclass
class UsageRecord:
    """Record of a single API call"""
    provider: str
    endpoint: str
    timestamp: str
    success: bool
    response_size_bytes: int = 0
    cached: bool = False
    video_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DailyUsage:
    """Daily usage summary"""
    date: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    cached_responses: int = 0
    estimated_cost: float = 0.0
    calls_by_endpoint: Dict[str, int] = field(default_factory=dict)


@dataclass
class MonthlyBudget:
    """Monthly budget configuration"""
    provider: str
    tier_name: str
    monthly_limit: int
    monthly_cost: float
    warning_threshold_pct: float = 80.0  # Warn at 80% usage
    hard_limit_pct: float = 95.0  # Stop at 95% to leave buffer
    current_usage: int = 0
    period_start: str = ""
    period_end: str = ""


# RapidAPI TikTok API (tiktok-api6) pricing tiers - from https://rapidapi.com/omarmhaimdat/api/tiktok-api6
# Last updated: Dec 2024
RAPIDAPI_TIKTOK_TIERS = {
    "basic": APITier("BASIC", monthly_limit=50, cost_usd=0.0),  # Free tier, hard limit
    "pro": APITier("PRO", monthly_limit=10000, cost_usd=9.99, overage_cost_per_call=0.002),
    "ultra": APITier("ULTRA", monthly_limit=100000, cost_usd=49.99, overage_cost_per_call=0.001),
    "mega": APITier("MEGA", monthly_limit=300000, cost_usd=99.99, overage_cost_per_call=0.0008),
}

# RapidAPI TikTok API endpoints
RAPIDAPI_TIKTOK_ENDPOINTS = {
    "video_details": "/video/details",      # GET/POST - Get video analytics by video_id
    "user_details": "/user/details",        # GET/POST - Get user profile by username
    "user_videos": "/user/videos",          # GET/POST - Get user's videos by username  
    "user_videos_cont": "/user/videos/continuation",  # GET - Paginated videos
    "search_videos": "/search/general/query",  # GET/POST - Search videos by query
    "search_accounts": "/search/accounts/query",  # GET/POST - Search users by query
    "collection": "/collection/",           # GET - Collection details
}

# Rate limits by tier (requests per second)
RAPIDAPI_TIKTOK_RATE_LIMITS = {
    "basic": 0,    # No rate limit (but 50/month hard cap)
    "pro": 1,      # 1 request/second
    "ultra": 5,    # 5 requests/second
    "mega": 5,     # 5 requests/second
}

# =============================================================================
# RapidAPI Twitter/X API (twitter-x) - from https://rapidapi.com/datarise-datarise-default/api/twitter-x
# Host: twitter-x.p.rapidapi.com
# Last updated: Dec 2024
# =============================================================================
RAPIDAPI_TWITTER_HOST = "twitter-x.p.rapidapi.com"

RAPIDAPI_TWITTER_TIERS = {
    "basic": APITier("BASIC", monthly_limit=200, cost_usd=0.0),  # Free tier
    "pro": APITier("PRO", monthly_limit=10000, cost_usd=10.0, overage_cost_per_call=0.004),
    "ultra": APITier("ULTRA", monthly_limit=100000, cost_usd=40.0, overage_cost_per_call=0.003),
    "mega": APITier("MEGA", monthly_limit=500000, cost_usd=100.0, overage_cost_per_call=0.001),
}

RAPIDAPI_TWITTER_ENDPOINTS = {
    "tweet_details": "/tweet/details",       # GET - Tweet detail & conversation
    "tweet_retweeters": "/tweet/retweeters", # GET - Tweet retweeters
    "tweet_favoriters": "/tweet/favoriters", # GET - Tweet favoriters (likers)
    "user_details": "/user/details",         # GET - User by screen name or rest ID
    "user_tweets": "/user/tweets",           # GET - User tweets
    "user_replies": "/user/tweetsandreplies", # GET - User tweets & replies
    "user_followers": "/user/followers",     # GET - User followers
    "user_following": "/user/following",     # GET - User following
    "user_likes": "/user/likes",             # GET - User likes
    "user_media": "/user/media",             # GET - User media
    "search": "/search/",                    # GET - Search results
    "lists_details": "/lists/details",       # GET - Lists details
    "lists_tweets": "/lists/tweets",         # GET - Lists tweets
    "trends": "/trends/",                    # GET - Trends near location
    "community_details": "/community/details", # GET - Community details
    "community_tweets": "/community/tweets",   # GET - Community tweets
}

RAPIDAPI_TWITTER_RATE_LIMITS = {
    "basic": 0,     # No rate limit
    "pro": 5,       # 5 requests/second
    "ultra": 10,    # 10 requests/second
    "mega": 30,     # 30 requests/second
}

# =============================================================================
# RapidAPI Instagram Looter2 (PRIMARY) - WORKING
# Host: instagram-looter2.p.rapidapi.com
# Last updated: Dec 2024
# Note: instagram-scraper-api2 returns 401 "Blocked User" - DO NOT USE
# =============================================================================
RAPIDAPI_INSTAGRAM_HOST = "instagram-looter2.p.rapidapi.com"

RAPIDAPI_INSTAGRAM_TIERS = {
    "basic": APITier("BASIC", monthly_limit=100, cost_usd=0.0),  # Free tier
    "pro": APITier("PRO", monthly_limit=10000, cost_usd=30.0, overage_cost_per_call=0.005),
    "ultra": APITier("ULTRA", monthly_limit=100000, cost_usd=100.0, overage_cost_per_call=0.002),
    "mega": APITier("MEGA", monthly_limit=500000, cost_usd=250.0, overage_cost_per_call=0.001),
}

RAPIDAPI_INSTAGRAM_ENDPOINTS = {
    "profile": "/profile",                    # GET - User profile with posts (VERIFIED WORKING)
}

# Instagram Statistics API (Secondary) - instagram-statistics-api.p.rapidapi.com
RAPIDAPI_INSTAGRAM_STATS_HOST = "instagram-statistics-api.p.rapidapi.com"
RAPIDAPI_INSTAGRAM_STATS_ENDPOINTS = {
    "community": "/community",                # GET - Profile stats & engagement (VERIFIED WORKING)
}

# =============================================================================
# RapidAPI TikTok Scraper7 (PRIMARY) - VERIFIED WORKING
# Host: tiktok-scraper7.p.rapidapi.com
# Last updated: Dec 2024
# =============================================================================
RAPIDAPI_TIKTOK_SCRAPER7_HOST = "tiktok-scraper7.p.rapidapi.com"

RAPIDAPI_TIKTOK_SCRAPER7_TIERS = {
    "basic": APITier("BASIC", monthly_limit=100, cost_usd=0.0),
    "pro": APITier("PRO", monthly_limit=10000, cost_usd=15.0, overage_cost_per_call=0.002),
    "ultra": APITier("ULTRA", monthly_limit=100000, cost_usd=50.0, overage_cost_per_call=0.001),
}

RAPIDAPI_TIKTOK_SCRAPER7_ENDPOINTS = {
    "user_info": "/user/info",                # GET - User profile (VERIFIED WORKING)
    "user_posts": "/user/posts",              # GET - User videos with metrics (VERIFIED WORKING)
    "user_followers": "/user/followers",      # GET - Followers list (VERIFIED WORKING)
    "user_following": "/user/following",      # GET - Following list (VERIFIED WORKING)
    "music_info": "/music/info",              # GET - Music/sound info (VERIFIED WORKING)
}

RAPIDAPI_TIKTOK_SCRAPER7_RATE_LIMITS = {
    "basic": 1,
    "pro": 5,
    "ultra": 10,
}

# =============================================================================
# RapidAPI Google Maps Places - VERIFIED WORKING
# Host: google-map-places.p.rapidapi.com
# =============================================================================
RAPIDAPI_GOOGLE_MAPS_HOST = "google-map-places.p.rapidapi.com"

RAPIDAPI_GOOGLE_MAPS_TIERS = {
    "basic": APITier("BASIC", monthly_limit=500, cost_usd=0.0),
    "pro": APITier("PRO", monthly_limit=10000, cost_usd=10.0),
}

RAPIDAPI_GOOGLE_MAPS_ENDPOINTS = {
    "textsearch": "/maps/api/place/textsearch/json",  # GET - Place search (VERIFIED WORKING)
}

RAPIDAPI_GOOGLE_MAPS_RATE_LIMITS = {
    "basic": 1,
    "pro": 5,
}

# =============================================================================
# RapidAPI Amazon Data - VERIFIED WORKING
# Host: real-time-amazon-data.p.rapidapi.com
# =============================================================================
RAPIDAPI_AMAZON_HOST = "real-time-amazon-data.p.rapidapi.com"

RAPIDAPI_AMAZON_TIERS = {
    "basic": APITier("BASIC", monthly_limit=100, cost_usd=0.0),
    "pro": APITier("PRO", monthly_limit=10000, cost_usd=20.0),
}

RAPIDAPI_AMAZON_ENDPOINTS = {
    "search": "/search",                      # GET - Product search (VERIFIED WORKING)
}

RAPIDAPI_AMAZON_RATE_LIMITS = {
    "basic": 1,
    "pro": 5,
}

RAPIDAPI_INSTAGRAM_RATE_LIMITS = {
    "basic": 1,     # 1 request/second
    "pro": 5,       # 5 requests/second
    "ultra": 10,    # 10 requests/second
    "mega": 20,     # 20 requests/second
}

# =============================================================================
# RapidAPI YouTube (YT-API) - from https://rapidapi.com/ytjar/api/yt-api
# Host: yt-api.p.rapidapi.com
# Last updated: Dec 2024
# =============================================================================
RAPIDAPI_YOUTUBE_HOST = "yt-api.p.rapidapi.com"

RAPIDAPI_YOUTUBE_TIERS = {
    "basic": APITier("BASIC", monthly_limit=100, cost_usd=0.0),  # Free tier
    "pro": APITier("PRO", monthly_limit=50000, cost_usd=10.0, overage_cost_per_call=0.0003),
    "ultra": APITier("ULTRA", monthly_limit=500000, cost_usd=50.0, overage_cost_per_call=0.0002),
    "mega": APITier("MEGA", monthly_limit=2000000, cost_usd=100.0, overage_cost_per_call=0.0001),
}

RAPIDAPI_YOUTUBE_ENDPOINTS = {
    "video_info": "/video/info",              # GET - Video details
    "video_comments": "/video/comments",      # GET - Video comments
    "channel_info": "/channel/info",          # GET - Channel details
    "channel_videos": "/channel/videos",      # GET - Channel videos
    "channel_shorts": "/channel/shorts",      # GET - Channel shorts
    "search": "/search",                      # GET - Search videos/channels
    "playlist": "/playlist",                  # GET - Playlist videos
    "trending": "/trending",                  # GET - Trending videos
    "hashtag": "/hashtag",                    # GET - Hashtag videos
}

RAPIDAPI_YOUTUBE_RATE_LIMITS = {
    "basic": 1,     # 1 request/second
    "pro": 5,       # 5 requests/second
    "ultra": 10,    # 10 requests/second
    "mega": 20,     # 20 requests/second
}

# =============================================================================
# ALL PROVIDERS CONFIGURATION
# =============================================================================
ALL_API_PROVIDERS = {
    # TikTok APIs
    APIProvider.RAPIDAPI_TIKTOK: {
        "host": "tiktok-api6.p.rapidapi.com",
        "display_name": "RapidAPI TikTok (API6)",
        "tiers": RAPIDAPI_TIKTOK_TIERS,
        "endpoints": RAPIDAPI_TIKTOK_ENDPOINTS,
        "rate_limits": RAPIDAPI_TIKTOK_RATE_LIMITS,
    },
    APIProvider.RAPIDAPI_TIKTOK_SCRAPER7: {
        "host": RAPIDAPI_TIKTOK_SCRAPER7_HOST,
        "display_name": "TikTok Scraper7 (PRIMARY ✓)",
        "tiers": RAPIDAPI_TIKTOK_SCRAPER7_TIERS,
        "endpoints": RAPIDAPI_TIKTOK_SCRAPER7_ENDPOINTS,
        "rate_limits": RAPIDAPI_TIKTOK_SCRAPER7_RATE_LIMITS,
    },
    # Instagram APIs
    APIProvider.RAPIDAPI_INSTAGRAM: {
        "host": RAPIDAPI_INSTAGRAM_HOST,
        "display_name": "Instagram Looter2 (PRIMARY ✓)",
        "tiers": RAPIDAPI_INSTAGRAM_TIERS,
        "endpoints": RAPIDAPI_INSTAGRAM_ENDPOINTS,
        "rate_limits": RAPIDAPI_INSTAGRAM_RATE_LIMITS,
    },
    APIProvider.RAPIDAPI_INSTAGRAM_STATS: {
        "host": RAPIDAPI_INSTAGRAM_STATS_HOST,
        "display_name": "Instagram Statistics",
        "tiers": RAPIDAPI_INSTAGRAM_TIERS,
        "endpoints": RAPIDAPI_INSTAGRAM_STATS_ENDPOINTS,
        "rate_limits": RAPIDAPI_INSTAGRAM_RATE_LIMITS,
    },
    # YouTube API
    APIProvider.RAPIDAPI_YOUTUBE: {
        "host": RAPIDAPI_YOUTUBE_HOST,
        "display_name": "YT-API (PRIMARY ✓)",
        "tiers": RAPIDAPI_YOUTUBE_TIERS,
        "endpoints": RAPIDAPI_YOUTUBE_ENDPOINTS,
        "rate_limits": RAPIDAPI_YOUTUBE_RATE_LIMITS,
    },
    # Twitter API
    APIProvider.RAPIDAPI_TWITTER: {
        "host": RAPIDAPI_TWITTER_HOST,
        "display_name": "Twitter/X API",
        "tiers": RAPIDAPI_TWITTER_TIERS,
        "endpoints": RAPIDAPI_TWITTER_ENDPOINTS,
        "rate_limits": RAPIDAPI_TWITTER_RATE_LIMITS,
    },
}


class APIUsageTracker:
    """
    Tracks API usage, manages budgets, and provides strategic call optimization.
    
    Features:
    - Real-time usage tracking per provider
    - Monthly budget management with warnings
    - Call caching to avoid duplicate requests
    - Priority-based refresh scheduling
    - Usage analytics and cost estimation
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the tracker with persistent storage"""
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "api_usage")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.usage_file = self.data_dir / "usage_log.json"
        self.budget_file = self.data_dir / "budgets.json"
        self.cache_file = self.data_dir / "response_cache.json"
        
        # In-memory caches
        self._usage_records: List[UsageRecord] = []
        self._budgets: Dict[str, MonthlyBudget] = {}
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        
        # Load persisted data
        self._load_data()
        
        # Initialize default budgets if not set
        self._init_default_budgets()
    
    def _load_data(self):
        """Load persisted data from files"""
        # Load usage records
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    self._usage_records = [UsageRecord(**r) for r in data.get('records', [])]
            except Exception as e:
                logger.warning(f"Failed to load usage records: {e}")
        
        # Load budgets
        if self.budget_file.exists():
            try:
                with open(self.budget_file, 'r') as f:
                    data = json.load(f)
                    self._budgets = {k: MonthlyBudget(**v) for k, v in data.items()}
            except Exception as e:
                logger.warning(f"Failed to load budgets: {e}")
        
        # Load cache
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self._response_cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
    
    def _save_data(self):
        """Persist data to files"""
        try:
            # Save usage records (keep last 1000)
            records_to_save = self._usage_records[-1000:]
            with open(self.usage_file, 'w') as f:
                json.dump({'records': [asdict(r) for r in records_to_save]}, f, indent=2)
            
            # Save budgets
            with open(self.budget_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self._budgets.items()}, f, indent=2)
            
            # Save cache (only recent entries)
            self._prune_cache()
            with open(self.cache_file, 'w') as f:
                json.dump(self._response_cache, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save API usage data: {e}")
    
    def _init_default_budgets(self):
        """Initialize default budget configurations"""
        now = datetime.now()
        period_start = now.replace(day=1).strftime("%Y-%m-%d")
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Default to basic (free) tier if not configured
        if APIProvider.RAPIDAPI_TIKTOK.value not in self._budgets:
            tier = RAPIDAPI_TIKTOK_TIERS.get(
                os.getenv("RAPIDAPI_TIKTOK_TIER", "basic").lower(),
                RAPIDAPI_TIKTOK_TIERS["basic"]
            )
            self._budgets[APIProvider.RAPIDAPI_TIKTOK.value] = MonthlyBudget(
                provider=APIProvider.RAPIDAPI_TIKTOK.value,
                tier_name=tier.name,
                monthly_limit=tier.monthly_limit,
                monthly_cost=tier.cost_usd,
                period_start=period_start,
                period_end=period_end,
                current_usage=self._count_current_month_usage(APIProvider.RAPIDAPI_TIKTOK.value)
            )
        
        # Initialize Twitter budget
        if APIProvider.RAPIDAPI_TWITTER.value not in self._budgets:
            tier = RAPIDAPI_TWITTER_TIERS.get("basic")
            self._budgets[APIProvider.RAPIDAPI_TWITTER.value] = MonthlyBudget(
                provider=APIProvider.RAPIDAPI_TWITTER.value,
                tier_name=tier.name,
                monthly_limit=tier.monthly_limit,
                monthly_cost=tier.cost_usd,
                period_start=period_start,
                period_end=period_end,
                current_usage=0
            )
        
        # Initialize Instagram budget
        if APIProvider.RAPIDAPI_INSTAGRAM.value not in self._budgets:
            tier = RAPIDAPI_INSTAGRAM_TIERS.get("basic")
            self._budgets[APIProvider.RAPIDAPI_INSTAGRAM.value] = MonthlyBudget(
                provider=APIProvider.RAPIDAPI_INSTAGRAM.value,
                tier_name=tier.name,
                monthly_limit=tier.monthly_limit,
                monthly_cost=tier.cost_usd,
                period_start=period_start,
                period_end=period_end,
                current_usage=0
            )
        
        # RapidAPI YouTube removed - using Google YouTube API directly
        
        self._save_data()
    
    def _count_current_month_usage(self, provider: str) -> int:
        """Count API calls for current month"""
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        count = 0
        for record in self._usage_records:
            if record.provider != provider:
                continue
            try:
                record_time = datetime.fromisoformat(record.timestamp)
                if record_time >= month_start and not record.cached:
                    count += 1
            except:
                pass
        
        return count
    
    def _prune_cache(self, max_age_hours: int = 24):
        """Remove old cache entries"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        cutoff_str = cutoff.isoformat()
        
        keys_to_remove = []
        for key, value in self._response_cache.items():
            if value.get('cached_at', '') < cutoff_str:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._response_cache[key]
    
    def set_tier(self, provider: APIProvider, tier_name: str):
        """
        Set the pricing tier for a provider.
        
        Args:
            provider: API provider
            tier_name: Name of the tier (free, basic, pro, ultra, mega)
        """
        tier_name_lower = tier_name.lower()
        
        if provider == APIProvider.RAPIDAPI_TIKTOK:
            if tier_name_lower not in RAPIDAPI_TIKTOK_TIERS:
                raise ValueError(f"Unknown tier: {tier_name}. Available: {list(RAPIDAPI_TIKTOK_TIERS.keys())}")
            tier = RAPIDAPI_TIKTOK_TIERS[tier_name_lower]
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        now = datetime.now()
        period_start = now.replace(day=1).strftime("%Y-%m-%d")
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
        
        self._budgets[provider.value] = MonthlyBudget(
            provider=provider.value,
            tier_name=tier.name,
            monthly_limit=tier.monthly_limit,
            monthly_cost=tier.cost_usd,
            period_start=period_start,
            period_end=period_end,
            current_usage=self._count_current_month_usage(provider.value)
        )
        
        self._save_data()
        logger.info(f"Set {provider.value} tier to {tier.name} ({tier.monthly_limit} calls/month)")
    
    def can_make_call(self, provider: APIProvider) -> Dict[str, Any]:
        """
        Check if we can make an API call within budget.
        
        Returns:
            Dict with 'allowed', 'reason', 'usage_pct', 'remaining_calls'
        """
        budget = self._budgets.get(provider.value)
        
        if not budget:
            return {
                "allowed": False,
                "reason": f"No budget configured for {provider.value}",
                "usage_pct": 0,
                "remaining_calls": 0
            }
        
        # Refresh current usage count
        budget.current_usage = self._count_current_month_usage(provider.value)
        
        usage_pct = (budget.current_usage / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 100
        remaining = max(0, budget.monthly_limit - budget.current_usage)
        
        # Check hard limit
        if usage_pct >= budget.hard_limit_pct:
            return {
                "allowed": False,
                "reason": f"Hard limit reached ({usage_pct:.1f}% of {budget.monthly_limit} calls)",
                "usage_pct": usage_pct,
                "remaining_calls": remaining,
                "warning": True
            }
        
        # Check warning threshold
        warning = usage_pct >= budget.warning_threshold_pct
        
        return {
            "allowed": True,
            "reason": "OK",
            "usage_pct": usage_pct,
            "remaining_calls": remaining,
            "warning": warning,
            "warning_message": f"Approaching limit: {usage_pct:.1f}% used" if warning else None
        }
    
    def record_call(
        self,
        provider: APIProvider,
        endpoint: str,
        success: bool,
        video_id: Optional[str] = None,
        response_size: int = 0,
        cached: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record an API call"""
        record = UsageRecord(
            provider=provider.value,
            endpoint=endpoint,
            timestamp=datetime.now().isoformat(),
            success=success,
            response_size_bytes=response_size,
            cached=cached,
            video_id=video_id,
            metadata=metadata or {}
        )
        
        self._usage_records.append(record)
        
        # Update budget usage if not cached
        if not cached and provider.value in self._budgets:
            self._budgets[provider.value].current_usage += 1
        
        self._save_data()
        
        logger.debug(f"Recorded API call: {provider.value}/{endpoint} (success={success}, cached={cached})")
    
    def get_cached_response(self, cache_key: str, max_age_hours: int = 6) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired.
        
        Args:
            cache_key: Unique key for this request (e.g., "tiktok:video:12345")
            max_age_hours: Maximum age of cache in hours
            
        Returns:
            Cached response or None
        """
        cached = self._response_cache.get(cache_key)
        
        if not cached:
            return None
        
        cached_at = cached.get('cached_at', '')
        try:
            cache_time = datetime.fromisoformat(cached_at)
            if datetime.now() - cache_time > timedelta(hours=max_age_hours):
                # Cache expired
                del self._response_cache[cache_key]
                return None
        except:
            return None
        
        return cached.get('data')
    
    def cache_response(self, cache_key: str, data: Dict[str, Any]):
        """Cache an API response"""
        self._response_cache[cache_key] = {
            'cached_at': datetime.now().isoformat(),
            'data': data
        }
        self._save_data()
    
    def get_usage_summary(self, provider: Optional[APIProvider] = None) -> Dict[str, Any]:
        """
        Get usage summary for all or specific provider.
        
        Returns:
            Detailed usage statistics
        """
        summaries = {}
        
        providers = [provider] if provider else list(APIProvider)
        
        for p in providers:
            budget = self._budgets.get(p.value)
            if not budget:
                continue
            
            # Recalculate current usage
            current_usage = self._count_current_month_usage(p.value)
            budget.current_usage = current_usage
            
            usage_pct = (current_usage / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0
            remaining = max(0, budget.monthly_limit - current_usage)
            
            # Calculate estimated cost
            tier = None
            if p == APIProvider.RAPIDAPI_TIKTOK:
                tier = RAPIDAPI_TIKTOK_TIERS.get(budget.tier_name.lower())
            
            cost_per_call = tier.cost_per_call if tier else 0
            
            # Get daily breakdown for current month
            daily_usage = self._get_daily_breakdown(p.value)
            
            summaries[p.value] = {
                "provider": p.value,
                "tier": budget.tier_name,
                "period": {
                    "start": budget.period_start,
                    "end": budget.period_end
                },
                "limits": {
                    "monthly_limit": budget.monthly_limit,
                    "warning_threshold_pct": budget.warning_threshold_pct,
                    "hard_limit_pct": budget.hard_limit_pct
                },
                "usage": {
                    "current": current_usage,
                    "remaining": remaining,
                    "usage_pct": round(usage_pct, 2),
                    "status": self._get_status(usage_pct, budget)
                },
                "cost": {
                    "monthly_cost": budget.monthly_cost,
                    "cost_per_call": round(cost_per_call, 4),
                    "estimated_current": round(current_usage * cost_per_call, 2)
                },
                "daily_breakdown": daily_usage,
                "recommendations": self._get_recommendations(usage_pct, remaining, budget)
            }
        
        self._save_data()
        
        return summaries if not provider else summaries.get(provider.value, {})
    
    def _get_status(self, usage_pct: float, budget: MonthlyBudget) -> str:
        """Get status based on usage percentage"""
        if usage_pct >= budget.hard_limit_pct:
            return "BLOCKED"
        elif usage_pct >= budget.warning_threshold_pct:
            return "WARNING"
        elif usage_pct >= 50:
            return "MODERATE"
        else:
            return "OK"
    
    def _get_daily_breakdown(self, provider: str) -> List[Dict[str, Any]]:
        """Get daily usage breakdown for current month"""
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        daily: Dict[str, DailyUsage] = {}
        
        for record in self._usage_records:
            if record.provider != provider:
                continue
            try:
                record_time = datetime.fromisoformat(record.timestamp)
                if record_time < month_start:
                    continue
                
                date_str = record_time.strftime("%Y-%m-%d")
                if date_str not in daily:
                    daily[date_str] = DailyUsage(date=date_str)
                
                day = daily[date_str]
                if not record.cached:
                    day.total_calls += 1
                    if record.success:
                        day.successful_calls += 1
                    else:
                        day.failed_calls += 1
                else:
                    day.cached_responses += 1
                
                endpoint = record.endpoint
                day.calls_by_endpoint[endpoint] = day.calls_by_endpoint.get(endpoint, 0) + 1
                
            except:
                pass
        
        # Sort by date
        return [asdict(v) for v in sorted(daily.values(), key=lambda x: x.date, reverse=True)]
    
    def _get_recommendations(
        self,
        usage_pct: float,
        remaining: int,
        budget: MonthlyBudget
    ) -> List[str]:
        """Generate recommendations based on usage"""
        recs = []
        
        days_left = self._days_left_in_month()
        calls_per_day = remaining / days_left if days_left > 0 else 0
        
        if usage_pct >= budget.hard_limit_pct:
            recs.append("❌ BLOCKED: Upgrade to higher tier to continue API calls")
            recs.append(f"Consider upgrading from {budget.tier_name} to unlock more calls")
        elif usage_pct >= budget.warning_threshold_pct:
            recs.append(f"⚠️ WARNING: Only {remaining} calls remaining this month")
            recs.append(f"Limit to ~{int(calls_per_day)} calls/day to stay within budget")
        elif usage_pct >= 50:
            recs.append(f"📊 Moderate usage: {remaining} calls remaining")
            recs.append(f"Safe to make ~{int(calls_per_day)} calls/day")
        else:
            recs.append(f"✅ Healthy usage: {remaining} calls remaining")
            recs.append("Consider caching responses to maximize efficiency")
        
        # Add general tips
        recs.append("💡 Tip: Use cache_max_age_hours=6 for non-critical analytics")
        
        return recs
    
    def _days_left_in_month(self) -> int:
        """Calculate days left in current month"""
        now = datetime.now()
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        return (next_month - now).days


# Singleton instance
_tracker: Optional[APIUsageTracker] = None


def get_api_usage_tracker() -> APIUsageTracker:
    """Get singleton instance of APIUsageTracker"""
    global _tracker
    if _tracker is None:
        _tracker = APIUsageTracker()
    return _tracker
