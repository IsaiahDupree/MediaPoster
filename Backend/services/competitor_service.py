"""
Competitor Research Service
Fetches, stores, and analyzes competitor Instagram content.
"""
import os
import httpx
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel

# Competitor research storage directory
COMPETITOR_RESEARCH_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch")
COMPETITOR_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)


class CompetitorAccount(BaseModel):
    """Competitor account data"""
    username: str
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    media_count: int = 0
    is_verified: bool = False
    profile_pic_url: Optional[str] = None
    category: Optional[str] = None
    external_url: Optional[str] = None


class CompetitorContent(BaseModel):
    """Competitor content item"""
    media_id: str
    shortcode: Optional[str] = None
    media_type: str  # 'reel', 'post', 'carousel'
    caption: Optional[str] = None
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    save_count: int = 0
    share_count: int = 0
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    audio_title: Optional[str] = None
    audio_artist: Optional[str] = None
    audio_id: Optional[str] = None
    is_original_audio: bool = False
    posted_at: Optional[datetime] = None
    hashtags: List[str] = []
    mentions: List[str] = []


class CompetitorService:
    """
    Service for competitor research and analysis.
    Uses Instagram Scraper Stable API (RapidAPI) with instagram-looter2 fallback.
    """
    
    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        # Primary API
        self.host = "instagram-scraper-stable-api.p.rapidapi.com"
        self.base_url = f"https://{self.host}"
        # Fallback API (confirmed working)
        self.fallback_host = "instagram-looter2.p.rapidapi.com"
        self.fallback_base_url = f"https://{self.fallback_host}"
        self.timeout = 30.0
        self.storage_dir = COMPETITOR_RESEARCH_DIR
        
        if not self.api_key:
            logger.warning("RAPIDAPI_KEY not set - competitor service will fail")
    
    def _get_headers(self, host: Optional[str] = None) -> Dict[str, str]:
        """Get RapidAPI headers"""
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": host or self.host,
            "Content-Type": "application/x-www-form-urlencoded"
        }
    
    def _get_account_dir(self, username: str) -> Path:
        """Get storage directory for an account"""
        account_dir = self.storage_dir / "accounts" / username
        account_dir.mkdir(parents=True, exist_ok=True)
        (account_dir / "reels").mkdir(exist_ok=True)
        (account_dir / "posts").mkdir(exist_ok=True)
        (account_dir / "analysis").mkdir(exist_ok=True)
        return account_dir
    
    async def fetch_account_info(self, username: str) -> Optional[CompetitorAccount]:
        """
        Fetch competitor account profile information.
        Tries primary API first, falls back to instagram-looter2.
        """
        # Try primary API
        result = await self._fetch_profile_primary(username)
        if result:
            return result
        
        # Fallback to instagram-looter2
        logger.info(f"Primary API failed for @{username}, trying fallback...")
        return await self._fetch_profile_fallback(username)
    
    async def _fetch_profile_primary(self, username: str) -> Optional[CompetitorAccount]:
        """Fetch profile via primary API (instagram-scraper-stable-api)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Fetching account info for @{username} (primary)")
                
                response = await client.post(
                    f"{self.base_url}/ig_get_fb_profile.php",
                    headers=self._get_headers(),
                    data={"username_or_url": username}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "error" in data:
                        logger.warning(f"Primary API error: {data.get('error')}")
                        return None
                    
                    return CompetitorAccount(
                        username=data.get("username", username),
                        user_id=str(data.get("id", data.get("pk", ""))),
                        full_name=data.get("full_name", ""),
                        bio=data.get("biography", ""),
                        followers_count=data.get("follower_count", 0),
                        following_count=data.get("following_count", 0),
                        media_count=data.get("media_count", 0),
                        is_verified=data.get("is_verified", False),
                        profile_pic_url=data.get("profile_pic_url_hd", data.get("profile_pic_url")),
                        category=data.get("category_name"),
                        external_url=data.get("external_url")
                    )
                else:
                    logger.error(f"Primary API failed: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error in primary profile fetch: {e}")
                return None
    
    async def _fetch_profile_fallback(self, username: str) -> Optional[CompetitorAccount]:
        """Fetch profile via fallback API (instagram-looter2 - confirmed working)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Fetching account info for @{username} (fallback: looter2)")
                
                response = await client.get(
                    f"{self.fallback_base_url}/v1/info",
                    headers=self._get_headers(self.fallback_host),
                    params={"username": username}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # instagram-looter2 returns data in a different structure
                    user_data = data.get("data", data)
                    
                    return CompetitorAccount(
                        username=user_data.get("username", username),
                        user_id=str(user_data.get("id", user_data.get("pk", ""))),
                        full_name=user_data.get("full_name", ""),
                        bio=user_data.get("biography", user_data.get("bio", "")),
                        followers_count=user_data.get("follower_count", user_data.get("followers", 0)),
                        following_count=user_data.get("following_count", user_data.get("following", 0)),
                        media_count=user_data.get("media_count", 0),
                        is_verified=user_data.get("is_verified", False),
                        profile_pic_url=user_data.get("profile_pic_url_hd", user_data.get("profile_pic_url")),
                        category=user_data.get("category_name", user_data.get("category")),
                        external_url=user_data.get("external_url")
                    )
                else:
                    logger.error(f"Fallback API failed: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error in fallback profile fetch: {e}")
                return None
    
    async def fetch_user_reels(self, username: str, count: int = 50) -> List[CompetitorContent]:
        """
        Fetch user reels with metrics.
        
        Endpoint: POST /get_ig_user_reels.php
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Fetching reels for @{username}")
                
                response = await client.post(
                    f"{self.base_url}/get_ig_user_reels.php",
                    headers=self._get_headers(),
                    data={"username_or_url": username}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "error" in data and data["error"]:
                        logger.warning(f"API error fetching reels: {data.get('error')}")
                        return []
                    
                    # Parse reels from response - structure is reels[].node.media
                    raw_reels = data.get("reels", [])
                    
                    reels = []
                    for reel_wrapper in raw_reels[:count]:
                        node = reel_wrapper.get("node", {})
                        media = node.get("media", {})
                        if media:
                            reel = self._parse_content_item(media, "reel")
                            if reel:
                                reels.append(reel)
                    
                    logger.info(f"Fetched {len(reels)} reels for @{username}")
                    return reels
                else:
                    logger.error(f"Failed to fetch reels: {response.status_code}")
                    return []
                    
            except Exception as e:
                logger.error(f"Error fetching reels: {e}")
                return []
    
    async def fetch_user_posts(self, username: str, count: int = 50) -> List[CompetitorContent]:
        """
        Fetch user posts with metrics.
        
        Endpoint: POST /get_ig_user_posts.php
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Fetching posts for @{username}")
                
                response = await client.post(
                    f"{self.base_url}/get_ig_user_posts.php",
                    headers=self._get_headers(),
                    data={"username_or_url": username}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "error" in data and data["error"]:
                        logger.warning(f"API error fetching posts: {data.get('error')}")
                        return []
                    
                    # Parse posts from response - structure is posts[].node
                    raw_posts = data.get("posts", [])
                    
                    posts = []
                    for post_wrapper in raw_posts[:count]:
                        node = post_wrapper.get("node", {})
                        if node:
                            post = self._parse_post_node(node)
                            if post:
                                posts.append(post)
                    
                    logger.info(f"Fetched {len(posts)} posts for @{username}")
                    return posts
                else:
                    logger.error(f"Failed to fetch posts: {response.status_code}")
                    return []
                    
            except Exception as e:
                logger.error(f"Error fetching posts: {e}")
                return []
    
    def _parse_post_node(self, node: Dict[str, Any]) -> Optional[CompetitorContent]:
        """Parse post node from posts API response"""
        try:
            # Get video URL if video
            video_url = None
            video_versions = node.get("video_versions", [])
            if video_versions:
                video_url = video_versions[0].get("url")
            
            # Get thumbnail
            thumbnail_url = None
            image_versions = node.get("image_versions2", {})
            candidates = image_versions.get("candidates", [])
            if candidates:
                thumbnail_url = candidates[0].get("url")
            
            # Get caption
            caption = ""
            caption_data = node.get("caption")
            if caption_data:
                caption = caption_data.get("text", "") if isinstance(caption_data, dict) else str(caption_data)
            
            # Determine media type
            media_type = "post"
            if video_versions:
                media_type = "video"
            
            # Get timestamp
            posted_at = None
            taken_at = node.get("taken_at")
            if taken_at:
                try:
                    posted_at = datetime.fromtimestamp(taken_at)
                except:
                    pass
            
            return CompetitorContent(
                media_id=str(node.get("id", node.get("pk", ""))),
                shortcode=node.get("code", ""),
                media_type=media_type,
                caption=caption[:500] if caption else None,
                play_count=node.get("play_count", 0),
                like_count=node.get("like_count", 0),
                comment_count=node.get("comment_count", 0),
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                posted_at=posted_at
            )
            
        except Exception as e:
            logger.error(f"Error parsing post node: {e}")
            return None
    
    def _parse_content_item(self, item: Dict[str, Any], media_type: str) -> Optional[CompetitorContent]:
        """Parse content item from API response"""
        try:
            # Get video URL
            video_url = None
            video_versions = item.get("video_versions", [])
            if video_versions:
                video_url = video_versions[0].get("url")
            
            # Get thumbnail
            thumbnail_url = None
            image_versions = item.get("image_versions2", {})
            candidates = image_versions.get("candidates", [])
            if candidates:
                thumbnail_url = candidates[0].get("url")
            
            # Get caption
            caption = ""
            caption_data = item.get("caption")
            if caption_data:
                caption = caption_data.get("text", "") if isinstance(caption_data, dict) else str(caption_data)
            
            # Get audio info
            audio_title = None
            audio_artist = None
            clips_metadata = item.get("clips_metadata", {})
            music_info = clips_metadata.get("music_info", {})
            if music_info:
                music_asset = music_info.get("music_asset_info", {})
                audio_title = music_asset.get("title")
                audio_artist = music_asset.get("display_artist")
            
            # Get timestamp
            posted_at = None
            taken_at = item.get("taken_at")
            if taken_at:
                try:
                    posted_at = datetime.fromtimestamp(taken_at)
                except:
                    pass
            
            return CompetitorContent(
                media_id=str(item.get("id", item.get("pk", ""))),
                shortcode=item.get("code", ""),
                media_type=media_type,
                caption=caption[:500] if caption else None,
                play_count=item.get("play_count", 0),
                like_count=item.get("like_count", 0),
                comment_count=item.get("comment_count", 0),
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                audio_title=audio_title,
                audio_artist=audio_artist,
                posted_at=posted_at
            )
            
        except Exception as e:
            logger.error(f"Error parsing content item: {e}")
            return None
    
    async def download_video(self, content: CompetitorContent, username: str) -> Optional[Path]:
        """Download video content to local storage"""
        if not content.video_url:
            return None
        
        account_dir = self._get_account_dir(username)
        folder = "reels" if content.media_type == "reel" else "posts"
        filename = f"{content.shortcode or content.media_id}.mp4"
        file_path = account_dir / folder / filename
        
        if file_path.exists():
            logger.debug(f"Video already exists: {file_path}")
            return file_path
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.info(f"Downloading video: {filename}")
                response = await client.get(content.video_url)
                response.raise_for_status()
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Downloaded: {file_path} ({len(response.content)} bytes)")
                return file_path
                
            except Exception as e:
                logger.error(f"Error downloading video: {e}")
                return None
    
    async def sync_account(self, username: str) -> Dict[str, Any]:
        """
        Full sync of a competitor account.
        Fetches profile, reels, posts, and stores locally.
        """
        logger.info(f"Starting full sync for @{username}")
        
        results = {
            "username": username,
            "profile": None,
            "reels_fetched": 0,
            "posts_fetched": 0,
            "videos_downloaded": 0,
            "errors": []
        }
        
        # Fetch profile
        profile = await self.fetch_account_info(username)
        if profile:
            results["profile"] = profile.model_dump()
            
            # Save profile to JSON
            account_dir = self._get_account_dir(username)
            import json
            with open(account_dir / "profile.json", "w") as f:
                json.dump(profile.model_dump(), f, indent=2, default=str)
        else:
            results["errors"].append("Failed to fetch profile")
        
        # Fetch reels
        reels = await self.fetch_user_reels(username, count=50)
        results["reels_fetched"] = len(reels)
        
        # Fetch posts
        posts = await self.fetch_user_posts(username, count=50)
        results["posts_fetched"] = len(posts)
        
        # Download videos (limit to top 10 for now)
        all_content = sorted(
            reels + posts,
            key=lambda x: (x.play_count or 0) + (x.like_count or 0),
            reverse=True
        )[:10]
        
        for content in all_content:
            path = await self.download_video(content, username)
            if path:
                results["videos_downloaded"] += 1
        
        logger.info(f"Sync complete for @{username}: {results}")
        return results
    
    def get_stored_accounts(self) -> List[str]:
        """Get list of stored competitor accounts"""
        accounts_dir = self.storage_dir / "accounts"
        if not accounts_dir.exists():
            return []
        return [d.name for d in accounts_dir.iterdir() if d.is_dir()]
    
    def get_stored_account_details(self) -> List[Dict[str, Any]]:
        """Get detailed info for all stored accounts including profile data"""
        import json as json_mod
        accounts_dir = self.storage_dir / "accounts"
        if not accounts_dir.exists():
            return []
        
        details = []
        for d in accounts_dir.iterdir():
            if not d.is_dir() or d.name.startswith('.'):
                continue
            
            info = {"username": d.name, "has_profile": False, "has_analysis": False}
            
            # Load profile
            profile_path = d / "profile.json"
            if profile_path.exists():
                try:
                    with open(profile_path) as f:
                        info["profile"] = json_mod.load(f)
                    info["has_profile"] = True
                except Exception:
                    pass
            
            # Check analysis
            analysis_path = d / "analysis" / "learnings.json"
            info["has_analysis"] = analysis_path.exists()
            
            # Count local videos
            posts_dir = d / "posts"
            reels_dir = d / "reels"
            video_count = 0
            if posts_dir.exists():
                video_count += len(list(posts_dir.glob("*.mp4")))
            if reels_dir.exists():
                video_count += len(list(reels_dir.glob("*.mp4")))
            info["local_videos"] = video_count
            
            details.append(info)
        
        return details
    
    def load_stored_content(self, username: str) -> List[CompetitorContent]:
        """Load previously stored content from local JSON files"""
        import json as json_mod
        import re
        account_dir = self._get_account_dir(username)
        content = []
        
        # Load from reels.json
        reels_file = account_dir / "reels" / "reels.json"
        if reels_file.exists():
            try:
                with open(reels_file) as f:
                    reels = json_mod.load(f)
                for r in reels:
                    hashtags = re.findall(r'#(\w+)', r.get("caption", ""))
                    content.append(CompetitorContent(
                        media_id=str(r.get("id", r.get("pk", ""))),
                        shortcode=r.get("code", r.get("shortcode", "")),
                        media_type="reel",
                        caption=r.get("caption", ""),
                        play_count=r.get("play_count", 0),
                        like_count=r.get("like_count", 0),
                        comment_count=r.get("comment_count", 0),
                        hashtags=[f"#{t}" for t in hashtags],
                    ))
            except Exception as e:
                logger.error(f"Error loading reels for @{username}: {e}")
        
        # Load from posts.json
        posts_file = account_dir / "posts" / "posts.json"
        if posts_file.exists():
            try:
                with open(posts_file) as f:
                    posts = json_mod.load(f)
                for p in posts:
                    hashtags = re.findall(r'#(\w+)', p.get("caption", ""))
                    content.append(CompetitorContent(
                        media_id=str(p.get("id", p.get("pk", ""))),
                        shortcode=p.get("code", p.get("shortcode", "")),
                        media_type="post",
                        caption=p.get("caption", ""),
                        play_count=p.get("play_count", 0),
                        like_count=p.get("like_count", 0),
                        comment_count=p.get("comment_count", 0),
                        hashtags=[f"#{t}" for t in hashtags],
                    ))
            except Exception as e:
                logger.error(f"Error loading posts for @{username}: {e}")
        
        return content


# Singleton instance
_competitor_service: Optional[CompetitorService] = None


def get_competitor_service() -> CompetitorService:
    """Get singleton competitor service instance"""
    global _competitor_service
    if _competitor_service is None:
        _competitor_service = CompetitorService()
    return _competitor_service
