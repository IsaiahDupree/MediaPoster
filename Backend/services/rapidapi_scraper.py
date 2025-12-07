"""
RapidAPI Scraper Service
Scrapes public profile data from social media platforms via RapidAPI
Phase 1: Multi-Platform Analytics Ingest
"""
import logging
import requests
from typing import Dict, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class RapidAPIScraper:
    """
    Scraper for social media platforms using RapidAPI endpoints
    
    Supports:
    - Instagram public profiles
    - TikTok public profiles
    - Twitter/X public profiles
    - Facebook public pages
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize RapidAPI scraper
        
        Args:
            api_key: RapidAPI key (defaults to RAPIDAPI_KEY env var)
        """
        self.api_key = api_key or os.getenv('RAPIDAPI_KEY')
        if not self.api_key:
            logger.warning("RapidAPI key not configured")
        
        self.base_url = "https://rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": ""
        }
    
    async def scrape_instagram_profile(self, username: str) -> Dict[str, Any]:
        """
        Scrape Instagram public profile data
        
        Args:
            username: Instagram username (without @)
            
        Returns:
            Dict with profile data, followers, posts, etc.
        """
        if not self.api_key:
            raise ValueError("RapidAPI key not configured")
        
        try:
            # Example RapidAPI endpoint (adjust based on actual API)
            url = "https://instagram-scraper-api2.p.rapidapi.com/user/info"
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
            }
            params = {"username_or_id_or_url": username}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Normalize response to our schema
            return {
                "platform": "instagram",
                "username": username,
                "display_name": data.get("full_name", ""),
                "bio": data.get("biography", ""),
                "profile_pic_url": data.get("profile_pic_url", ""),
                "follower_count": data.get("follower_count", 0),
                "following_count": data.get("following_count", 0),
                "posts_count": data.get("media_count", 0),
                "is_verified": data.get("is_verified", False),
                "is_business": data.get("is_business_account", False),
                "is_private": data.get("is_private", False),
                "fetched_at": datetime.now().isoformat(),
                "raw_data": data
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping Instagram profile {username}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error scraping Instagram: {e}")
            raise
    
    async def scrape_tiktok_profile(self, username: str) -> Dict[str, Any]:
        """
        Scrape TikTok public profile data
        
        Args:
            username: TikTok username (without @)
            
        Returns:
            Dict with profile data
        """
        if not self.api_key:
            raise ValueError("RapidAPI key not configured")
        
        try:
            # Example RapidAPI endpoint (adjust based on actual API)
            url = "https://tiktok-scraper2.p.rapidapi.com/user/info"
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "tiktok-scraper2.p.rapidapi.com"
            }
            params = {"username": username}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "platform": "tiktok",
                "username": username,
                "display_name": data.get("nickname", ""),
                "bio": data.get("signature", ""),
                "profile_pic_url": data.get("avatar_url", ""),
                "follower_count": data.get("follower_count", 0),
                "following_count": data.get("following_count", 0),
                "posts_count": data.get("video_count", 0),
                "likes_count": data.get("total_likes", 0),
                "is_verified": data.get("is_verified", False),
                "fetched_at": datetime.now().isoformat(),
                "raw_data": data
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping TikTok profile {username}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error scraping TikTok: {e}")
            raise
    
    async def scrape_twitter_profile(self, username: str) -> Dict[str, Any]:
        """
        Scrape Twitter/X public profile data
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            Dict with profile data
        """
        if not self.api_key:
            raise ValueError("RapidAPI key not configured")
        
        try:
            # Example RapidAPI endpoint (adjust based on actual API)
            url = "https://twitter-api45.p.rapidapi.com/user.php"
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "twitter-api45.p.rapidapi.com"
            }
            params = {"username": username}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "platform": "twitter",
                "username": username,
                "display_name": data.get("name", ""),
                "bio": data.get("bio", ""),
                "profile_pic_url": data.get("profile_pic_url", ""),
                "follower_count": data.get("followers", 0),
                "following_count": data.get("following", 0),
                "posts_count": data.get("tweets", 0),
                "is_verified": data.get("verified", False),
                "fetched_at": datetime.now().isoformat(),
                "raw_data": data
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping Twitter profile {username}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error scraping Twitter: {e}")
            raise
    
    async def scrape_platform_profile(
        self,
        platform: str,
        username: str
    ) -> Dict[str, Any]:
        """
        Generic method to scrape any platform profile
        
        Args:
            platform: Platform name (instagram, tiktok, twitter, etc.)
            username: Username to scrape
            
        Returns:
            Dict with profile data
        """
        platform_methods = {
            'instagram': self.scrape_instagram_profile,
            'tiktok': self.scrape_tiktok_profile,
            'twitter': self.scrape_twitter_profile,
        }
        
        if platform not in platform_methods:
            raise ValueError(f"Platform {platform} not supported by RapidAPI scraper")
        
        return await platform_methods[platform](username)
    
    async def get_recent_posts(
        self,
        platform: str,
        username: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent posts from a profile
        
        Args:
            platform: Platform name
            username: Username
            limit: Number of posts to fetch
            
        Returns:
            List of post data
        """
        # This would call platform-specific endpoints
        # For now, return empty list
        logger.info(f"Fetching recent posts for {platform}/{username}")
        return []






