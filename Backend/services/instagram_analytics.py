"""
Instagram Analytics Service - Swappable API Integration
Uses Instagram Looter2 API from RapidAPI
Matches our content tracking schema
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "instagram-looter2.p.rapidapi.com"
API_BASE = f"https://{RAPIDAPI_HOST}"


class InstagramAnalytics:
    """
    Swappable Instagram analytics client
    Can easily switch between different Instagram APIs
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or RAPIDAPI_KEY
        if not self.api_key:
            raise ValueError("RapidAPI key not found. Set RAPIDAPI_KEY in .env")
        
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic request method - easy to swap out
        """
        url = f"{API_BASE}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"API Error {response.status}: {error_text}")
                    raise Exception(f"API Error {response.status}: {error_text}")
                
                result = await response.json()
                
                # Debug: Print API response structure
                if endpoint == "/profile":
                    print(f"API Response keys: {list(result.keys())}")
                elif endpoint == "/user-feeds":
                    print(f"User feeds response keys: {list(result.keys())}")
                    if "data" in result:
                        print(f"Data keys: {list(result['data'].keys()) if isinstance(result['data'], dict) else type(result['data'])}")
                
                return result
    
    async def get_user_id_from_username(self, username: str) -> str:
        """
        Convert username to user ID
        Endpoint: /id
        """
        data = await self._make_request("/id", {"username": username})
        # API returns user_id directly
        return str(data.get("user_id") or data.get("id") or data.get("pk"))
    
    async def get_user_profile(self, username: str) -> Dict[str, Any]:
        """
        Get user profile information
        Endpoint: /profile
        """
        data = await self._make_request("/profile", {"username": username})
        
        # Handle different response structures
        if "data" in data:
            user = data["data"]
        else:
            user = data
        
        # API returns these exact field names
        return {
            "user_id": str(user.get("id") or user.get("pk")),
            "username": user.get("username"),
            "full_name": user.get("full_name"),
            "biography": user.get("biography"),
            "profile_pic_url": user.get("profile_pic_url"),
            "is_verified": user.get("is_verified", False),
            "is_private": user.get("is_private", False),
            "follower_count": user.get("edge_followed_by", {}).get("count", 0),
            "following_count": user.get("edge_follow", {}).get("count", 0),
            "media_count": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "external_url": user.get("external_url")
        }
    
    async def get_user_media(
        self, 
        user_id: str, 
        max_items: int = 50,
        end_cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user's media posts
        Endpoint: /user-feeds
        """
        params = {
            "id": user_id,
            "count": min(max_items, 50)  # API accepts int
        }
        
        if end_cursor:
            params["end_cursor"] = end_cursor
        
        data = await self._make_request("/user-feeds", params)
        
        # Handle response structure - items at root level
        items_list = data.get("items", [])
        
        media_items = []
        for item in items_list:
            # Get caption text
            caption_text = ""
            if isinstance(item.get("caption"), dict):
                caption_text = item.get("caption", {}).get("text", "")
            elif isinstance(item.get("caption"), str):
                caption_text = item.get("caption", "")
            
            media_items.append({
                "media_id": item.get("id") or item.get("pk"),
                "shortcode": item.get("code"),
                "media_type": item.get("media_type"),  # 1=photo, 2=video, 8=carousel
                "caption": caption_text,
                "like_count": item.get("like_count", 0),
                "comment_count": item.get("comment_count", 0),
                "play_count": item.get("play_count", 0) if item.get("media_type") == 2 else 0,
                "taken_at": item.get("taken_at"),
                "thumbnail_url": item.get("thumbnail_url") or item.get("display_url") or item.get("image_versions2", {}).get("candidates", [{}])[0].get("url"),
                "video_url": item.get("video_url") if item.get("media_type") == 2 else None,
                "url": f"https://www.instagram.com/p/{item.get('code')}/"
            })
        
        return {
            "items": media_items,
            "has_more": data.get("more_available", False),
            "end_cursor": data.get("next_max_id")
        }
    
    async def get_media_info(self, media_url: str) -> Dict[str, Any]:
        """
        Get detailed media information
        Endpoint: /post (by URL)
        """
        data = await self._make_request("/post", {"url": media_url})
        
        item = data.get("data", {})
        
        return {
            "media_id": item.get("id"),
            "shortcode": item.get("shortcode"),
            "media_type": item.get("media_type"),
            "caption": item.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", ""),
            "like_count": item.get("edge_media_preview_like", {}).get("count", 0),
            "comment_count": item.get("edge_media_to_comment", {}).get("count", 0),
            "play_count": item.get("video_view_count", 0),
            "taken_at": item.get("taken_at_timestamp"),
            "thumbnail_url": item.get("thumbnail_src") or item.get("display_url"),
            "video_url": item.get("video_url"),
            "url": f"https://www.instagram.com/p/{item.get('shortcode')}/"
        }
    
    async def get_account_analytics(
        self, 
        username: str, 
        max_posts: int = 50
    ) -> Dict[str, Any]:
        """
        Get complete analytics for an Instagram account
        """
        print(f"\n📸 Fetching Instagram analytics for: @{username}\n")
        
        # Get profile info
        profile = await self.get_user_profile(username)
        print(f"👤 Profile: @{profile['username']}")
        print(f"📊 {profile['follower_count']:,} followers, {profile['media_count']} posts\n")
        
        # Get user ID for media fetching
        user_id = profile['user_id']
        
        # Get media posts
        print(f"🔍 Fetching latest {max_posts} posts...")
        all_media = []
        end_cursor = None
        
        while len(all_media) < max_posts:
            remaining = max_posts - len(all_media)
            batch_size = min(remaining, 50)
            
            media_data = await self.get_user_media(user_id, batch_size, end_cursor)
            all_media.extend(media_data["items"])
            
            if not media_data["has_more"] or len(media_data["items"]) == 0:
                break
            
            end_cursor = media_data["end_cursor"]
            
            # Rate limiting
            await asyncio.sleep(1)
        
        print(f"✅ Found {len(all_media)} posts\n")
        
        # Process each post
        posts = []
        for idx, media in enumerate(all_media[:max_posts], 1):
            print(f"📷 Processing post {idx}/{min(len(all_media), max_posts)}: {media['shortcode']}")
            print(f"   Stats: {media['like_count']} likes, {media['comment_count']} comments")
            
            posts.append(media)
            
            # Rate limiting
            if idx % 10 == 0:
                await asyncio.sleep(2)
        
        return {
            "profile": profile,
            "posts": posts,
            "fetched_at": datetime.now().isoformat()
        }


# Convenience function
async def fetch_instagram_analytics(username: str, max_posts: int = 50) -> Dict[str, Any]:
    """
    Fetch Instagram analytics for a username
    """
    ig = InstagramAnalytics()
    return await ig.get_account_analytics(username, max_posts=max_posts)


if __name__ == "__main__":
    # Test with a username
    import sys
    
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter Instagram username: ")
    
    data = asyncio.run(fetch_instagram_analytics(username, max_posts=20))
    
    print("\n" + "="*60)
    print("📊 ANALYTICS SUMMARY")
    print("="*60)
    print(f"Profile: @{data['profile']['username']}")
    print(f"Followers: {data['profile']['follower_count']:,}")
    print(f"Posts analyzed: {len(data['posts'])}")
    print(f"Total likes: {sum(p['like_count'] for p in data['posts']):,}")
    print(f"Total comments: {sum(p['comment_count'] for p in data['posts']):,}")
