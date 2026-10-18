"""
RapidAPI Comments Service
Fetches comments from TikTok, Instagram, Threads, Facebook via RapidAPI
"""
import os
import logging
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PlatformComment(BaseModel):
    """A comment from any platform"""
    comment_id: str
    post_id: str
    platform: str
    author_name: str
    author_username: Optional[str] = None
    author_profile_url: Optional[str] = None
    author_avatar: Optional[str] = None
    text: str
    like_count: int = 0
    reply_count: int = 0
    published_at: Optional[str] = None
    is_reply: bool = False
    is_author: bool = False


class RapidAPICommentsService:
    """
    Service for fetching comments from multiple platforms via RapidAPI
    
    Supported platforms:
    - TikTok: tiktok-scraper7.p.rapidapi.com
    - Instagram: instagram-scraper-api2.p.rapidapi.com
    - Threads: threads-api4.p.rapidapi.com
    - Facebook: facebook-scraper3.p.rapidapi.com
    """
    
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.timeout = 30
        
        # Platform configurations
        self.configs = {
            "tiktok": {
                "host": "tiktok-scraper7.p.rapidapi.com",
                "base_url": "https://tiktok-scraper7.p.rapidapi.com",
                "comments_endpoint": "/comment/list",
                "user_posts_endpoint": "/user/posts",
            },
            "instagram": {
                "host": "instagram-scraper-api2.p.rapidapi.com",
                "base_url": "https://instagram-scraper-api2.p.rapidapi.com",
                "comments_endpoint": "/v1/comments",
                "user_posts_endpoint": "/v1.2/posts",
            },
            "threads": {
                "host": "threads-api4.p.rapidapi.com",
                "base_url": "https://threads-api4.p.rapidapi.com",
                "comments_endpoint": "/api/post/replies",
                "user_posts_endpoint": "/api/user/threads",
            },
            "facebook": {
                "host": "facebook-scraper3.p.rapidapi.com",
                "base_url": "https://facebook-scraper3.p.rapidapi.com",
                "comments_endpoint": "/post/comments",
                "user_posts_endpoint": "/page/posts",
            },
        }
        
        # Account usernames from env
        self.usernames = {
            "tiktok": os.getenv("TIKTOK_USERNAME", ""),
            "instagram": os.getenv("INSTAGRAM_USERNAME", ""),
            "threads": os.getenv("THREADS_USERNAME", ""),
            "facebook": os.getenv("FACEBOOK_PAGE_ID", ""),
        }
    
    def _get_headers(self, platform: str) -> Dict[str, str]:
        """Get headers for RapidAPI request"""
        config = self.configs.get(platform, {})
        return {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": config.get("host", ""),
        }
    
    async def fetch_tiktok_comments(
        self, 
        video_url: str = None,
        video_id: str = None,
        count: int = 50
    ) -> List[PlatformComment]:
        """
        Fetch comments from a TikTok video
        
        Args:
            video_url: Full TikTok video URL
            video_id: TikTok video ID (alternative to URL)
            count: Maximum comments to fetch
        """
        if not self.rapidapi_key:
            logger.error("RAPIDAPI_KEY not configured")
            return []
        
        config = self.configs["tiktok"]
        headers = self._get_headers("tiktok")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {"count": str(count), "cursor": "0"}
                if video_url:
                    params["url"] = video_url
                elif video_id:
                    params["video_id"] = video_id
                else:
                    logger.error("Either video_url or video_id required")
                    return []
                
                response = await client.get(
                    f"{config['base_url']}{config['comments_endpoint']}",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    comments_data = data.get("data", {}).get("comments", [])
                    
                    comments = []
                    for c in comments_data:
                        user = c.get("user", {})
                        comments.append(PlatformComment(
                            comment_id=str(c.get("cid", "")),
                            post_id=video_id or self._extract_tiktok_video_id(video_url),
                            platform="tiktok",
                            author_name=user.get("nickname", ""),
                            author_username=user.get("unique_id", ""),
                            author_avatar=user.get("avatar_thumb", {}).get("url_list", [""])[0] if isinstance(user.get("avatar_thumb"), dict) else "",
                            text=c.get("text", ""),
                            like_count=c.get("digg_count", 0),
                            reply_count=c.get("reply_comment_total", 0),
                            published_at=datetime.fromtimestamp(c.get("create_time", 0)).isoformat() if c.get("create_time") else None,
                            is_reply=False,
                            is_author=user.get("unique_id", "").lower() == self.usernames.get("tiktok", "").lower(),
                        ))
                    
                    logger.info(f"✓ Fetched {len(comments)} TikTok comments")
                    return comments
                else:
                    logger.warning(f"TikTok API returned {response.status_code}: {response.text[:200]}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching TikTok comments: {e}")
            return []
    
    def _extract_tiktok_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL"""
        if url and "/video/" in url:
            return url.split("/video/")[-1].split("?")[0]
        return ""
    
    async def fetch_instagram_comments(
        self,
        post_url: str = None,
        post_id: str = None,
        count: int = 50
    ) -> List[PlatformComment]:
        """
        Fetch comments from an Instagram post
        """
        if not self.rapidapi_key:
            logger.error("RAPIDAPI_KEY not configured")
            return []
        
        config = self.configs["instagram"]
        headers = self._get_headers("instagram")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {"count": str(count)}
                if post_url:
                    params["code_or_id_or_url"] = post_url
                elif post_id:
                    params["code_or_id_or_url"] = post_id
                else:
                    return []
                
                response = await client.get(
                    f"{config['base_url']}{config['comments_endpoint']}",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    comments_data = data.get("data", {}).get("items", [])
                    
                    comments = []
                    for c in comments_data:
                        user = c.get("user", {})
                        comments.append(PlatformComment(
                            comment_id=str(c.get("pk", "")),
                            post_id=post_id or post_url,
                            platform="instagram",
                            author_name=user.get("full_name", ""),
                            author_username=user.get("username", ""),
                            author_avatar=user.get("profile_pic_url", ""),
                            text=c.get("text", ""),
                            like_count=c.get("comment_like_count", 0),
                            reply_count=c.get("child_comment_count", 0),
                            published_at=datetime.fromtimestamp(c.get("created_at", 0)).isoformat() if c.get("created_at") else None,
                            is_reply=False,
                            is_author=user.get("username", "").lower() == self.usernames.get("instagram", "").lower(),
                        ))
                    
                    logger.info(f"✓ Fetched {len(comments)} Instagram comments")
                    return comments
                else:
                    logger.warning(f"Instagram API returned {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching Instagram comments: {e}")
            return []
    
    async def fetch_threads_comments(
        self,
        post_id: str,
        count: int = 50
    ) -> List[PlatformComment]:
        """
        Fetch replies from a Threads post
        """
        if not self.rapidapi_key:
            logger.error("RAPIDAPI_KEY not configured")
            return []
        
        config = self.configs["threads"]
        headers = self._get_headers("threads")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}{config['comments_endpoint']}",
                    headers=headers,
                    params={"postId": post_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    replies_data = data.get("data", {}).get("replies", [])
                    
                    comments = []
                    for r in replies_data:
                        user = r.get("user", {})
                        comments.append(PlatformComment(
                            comment_id=str(r.get("id", "")),
                            post_id=post_id,
                            platform="threads",
                            author_name=user.get("full_name", ""),
                            author_username=user.get("username", ""),
                            author_avatar=user.get("profile_pic_url", ""),
                            text=r.get("text", ""),
                            like_count=r.get("like_count", 0),
                            reply_count=r.get("reply_count", 0),
                            published_at=r.get("created_at"),
                            is_reply=True,
                            is_author=user.get("username", "").lower() == self.usernames.get("threads", "").lower(),
                        ))
                    
                    logger.info(f"✓ Fetched {len(comments)} Threads replies")
                    return comments
                else:
                    logger.warning(f"Threads API returned {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching Threads comments: {e}")
            return []
    
    async def fetch_facebook_comments(
        self,
        post_id: str,
        count: int = 50
    ) -> List[PlatformComment]:
        """
        Fetch comments from a Facebook post
        """
        if not self.rapidapi_key:
            logger.error("RAPIDAPI_KEY not configured")
            return []
        
        config = self.configs["facebook"]
        headers = self._get_headers("facebook")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{config['base_url']}{config['comments_endpoint']}",
                    headers=headers,
                    params={"post_id": post_id, "count": str(count)}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    comments_data = data.get("comments", [])
                    
                    comments = []
                    for c in comments_data:
                        comments.append(PlatformComment(
                            comment_id=str(c.get("id", "")),
                            post_id=post_id,
                            platform="facebook",
                            author_name=c.get("author_name", ""),
                            author_username=c.get("author_id", ""),
                            author_avatar=c.get("author_avatar", ""),
                            text=c.get("text", ""),
                            like_count=c.get("like_count", 0),
                            reply_count=c.get("reply_count", 0),
                            published_at=c.get("created_time"),
                            is_reply=False,
                            is_author=False,
                        ))
                    
                    logger.info(f"✓ Fetched {len(comments)} Facebook comments")
                    return comments
                else:
                    logger.warning(f"Facebook API returned {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching Facebook comments: {e}")
            return []
    
    async def fetch_user_posts(self, platform: str, username: str = None, count: int = 10) -> List[Dict]:
        """
        Fetch recent posts from a user's profile
        """
        username = username or self.usernames.get(platform, "")
        if not username:
            logger.error(f"No username configured for {platform}")
            return []
        
        config = self.configs.get(platform)
        if not config:
            logger.error(f"Unknown platform: {platform}")
            return []
        
        headers = self._get_headers(platform)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {"count": str(count)}
                
                if platform == "tiktok":
                    params["unique_id"] = username
                elif platform == "instagram":
                    params["username_or_id_or_url"] = username
                elif platform == "threads":
                    params["username"] = username
                elif platform == "facebook":
                    params["page_id"] = username
                
                response = await client.get(
                    f"{config['base_url']}{config['user_posts_endpoint']}",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract posts based on platform response format
                    if platform == "tiktok":
                        posts = data.get("data", {}).get("videos", [])
                        return [{"id": p.get("video_id"), "url": p.get("play_addr")} for p in posts]
                    elif platform == "instagram":
                        posts = data.get("data", {}).get("items", [])
                        return [{"id": p.get("pk"), "code": p.get("code")} for p in posts]
                    elif platform == "threads":
                        posts = data.get("data", {}).get("threads", [])
                        return [{"id": p.get("id")} for p in posts]
                    elif platform == "facebook":
                        posts = data.get("posts", [])
                        return [{"id": p.get("post_id")} for p in posts]
                    
                    return []
                else:
                    logger.warning(f"{platform} posts API returned {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching {platform} posts: {e}")
            return []
    
    async def fetch_all_comments_for_platform(
        self,
        platform: str,
        username: str = None,
        max_posts: int = 5,
        max_comments_per_post: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch comments for all recent posts from a platform
        """
        # Get user's recent posts
        posts = await self.fetch_user_posts(platform, username, count=max_posts)
        
        all_comments = []
        posts_with_comments = []
        
        for post in posts:
            post_id = post.get("id") or post.get("code")
            if not post_id:
                continue
            
            # Fetch comments for this post
            if platform == "tiktok":
                comments = await self.fetch_tiktok_comments(video_id=str(post_id), count=max_comments_per_post)
            elif platform == "instagram":
                comments = await self.fetch_instagram_comments(post_id=str(post_id), count=max_comments_per_post)
            elif platform == "threads":
                comments = await self.fetch_threads_comments(post_id=str(post_id), count=max_comments_per_post)
            elif platform == "facebook":
                comments = await self.fetch_facebook_comments(post_id=str(post_id), count=max_comments_per_post)
            else:
                continue
            
            if comments:
                posts_with_comments.append({
                    "post_id": post_id,
                    "comment_count": len(comments),
                    "comments": [c.model_dump() for c in comments]
                })
                all_comments.extend(comments)
        
        return {
            "platform": platform,
            "total_comments": len(all_comments),
            "posts_checked": len(posts),
            "posts_with_comments": len(posts_with_comments),
            "comments_by_post": posts_with_comments,
            "all_comments": [c.model_dump() for c in all_comments],
            "fetched_at": datetime.now().isoformat(),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration status for all platforms"""
        return {
            "rapidapi_key_configured": bool(self.rapidapi_key),
            "platforms": {
                "tiktok": {
                    "configured": bool(self.usernames.get("tiktok")),
                    "username": self.usernames.get("tiktok"),
                },
                "instagram": {
                    "configured": bool(self.usernames.get("instagram")),
                    "username": self.usernames.get("instagram"),
                },
                "threads": {
                    "configured": bool(self.usernames.get("threads")),
                    "username": self.usernames.get("threads"),
                },
                "facebook": {
                    "configured": bool(self.usernames.get("facebook")),
                    "page_id": self.usernames.get("facebook"),
                },
            }
        }


# Singleton instance
_rapidapi_comments_service: Optional[RapidAPICommentsService] = None


def get_rapidapi_comments_service() -> RapidAPICommentsService:
    """Get singleton instance"""
    global _rapidapi_comments_service
    if _rapidapi_comments_service is None:
        _rapidapi_comments_service = RapidAPICommentsService()
    return _rapidapi_comments_service
