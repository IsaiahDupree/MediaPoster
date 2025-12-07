"""
YouTube Analytics Service
Fetches video stats and comments from YouTube Data API v3
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAnalytics:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or YOUTUBE_API_KEY
        if not self.api_key:
            raise ValueError("YouTube API key not found. Set YOUTUBE_API_KEY in .env")
    
    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """
        Get channel information
        """
        url = f"{YOUTUBE_API_BASE}/channels"
        params = {
            "part": "snippet,statistics,brandingSettings",
            "id": channel_id,
            "key": self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if not data.get("items"):
                    return None
                
                channel = data["items"][0]
                snippet = channel.get("snippet", {})
                stats = channel.get("statistics", {})
                
                return {
                    "channel_id": channel_id,
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "custom_url": snippet.get("customUrl"),
                    "published_at": snippet.get("publishedAt"),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "subscriber_count": int(stats.get("subscriberCount", 0)),
                    "video_count": int(stats.get("videoCount", 0)),
                    "view_count": int(stats.get("viewCount", 0))
                }
    
    async def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[str]:
        """
        Get list of video IDs from a channel
        """
        url = f"{YOUTUBE_API_BASE}/search"
        params = {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": min(max_results, 50),
            "key": self.api_key
        }
        
        video_ids = []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                for item in data.get("items", []):
                    video_id = item.get("id", {}).get("videoId")
                    if video_id:
                        video_ids.append(video_id)
        
        return video_ids
    
    async def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a video
        """
        url = f"{YOUTUBE_API_BASE}/videos"
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
            "key": self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if not data.get("items"):
                    return None
                
                video = data["items"][0]
                snippet = video.get("snippet", {})
                stats = video.get("statistics", {})
                content = video.get("contentDetails", {})
                
                return {
                    "video_id": video_id,
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "channel_id": snippet.get("channelId"),
                    "channel_title": snippet.get("channelTitle"),
                    "published_at": snippet.get("publishedAt"),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "tags": snippet.get("tags", []),
                    "category_id": snippet.get("categoryId"),
                    "duration": content.get("duration"),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                    "favorite_count": int(stats.get("favoriteCount", 0)),
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                }
    
    async def get_video_comments(
        self, 
        video_id: str, 
        max_results: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get comments for a video with commenter information
        """
        url = f"{YOUTUBE_API_BASE}/commentThreads"
        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": "relevance",
            "textFormat": "plainText",
            "key": self.api_key
        }
        
        all_comments = []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                for item in data.get("items", []):
                    # Top-level comment
                    top_comment = item.get("snippet", {}).get("topLevelComment", {})
                    comment_snippet = top_comment.get("snippet", {})
                    
                    comment_data = {
                        "comment_id": top_comment.get("id"),
                        "text": comment_snippet.get("textDisplay"),
                        "author_name": comment_snippet.get("authorDisplayName"),
                        "author_channel_id": comment_snippet.get("authorChannelId", {}).get("value"),
                        "author_profile_image": comment_snippet.get("authorProfileImageUrl"),
                        "author_channel_url": comment_snippet.get("authorChannelUrl"),
                        "like_count": comment_snippet.get("likeCount", 0),
                        "published_at": comment_snippet.get("publishedAt"),
                        "updated_at": comment_snippet.get("updatedAt"),
                        "is_reply": False
                    }
                    all_comments.append(comment_data)
                    
                    # Replies if enabled
                    if include_replies and "replies" in item:
                        for reply in item.get("replies", {}).get("comments", []):
                            reply_snippet = reply.get("snippet", {})
                            reply_data = {
                                "comment_id": reply.get("id"),
                                "text": reply_snippet.get("textDisplay"),
                                "author_name": reply_snippet.get("authorDisplayName"),
                                "author_channel_id": reply_snippet.get("authorChannelId", {}).get("value"),
                                "author_profile_image": reply_snippet.get("authorProfileImageUrl"),
                                "author_channel_url": reply_snippet.get("authorChannelUrl"),
                                "like_count": reply_snippet.get("likeCount", 0),
                                "published_at": reply_snippet.get("publishedAt"),
                                "updated_at": reply_snippet.get("updatedAt"),
                                "is_reply": True,
                                "parent_id": comment_data["comment_id"]
                            }
                            all_comments.append(reply_data)
        
        return all_comments
    
    async def get_channel_analytics(
        self, 
        channel_id: str, 
        max_videos: int = 50,
        fetch_comments: bool = True
    ) -> Dict[str, Any]:
        """
        Get complete analytics for a channel including videos and comments
        """
        print(f"\n🎥 Fetching YouTube analytics for channel: {channel_id}\n")
        
        # Get channel info
        channel_info = await self.get_channel_info(channel_id)
        if not channel_info:
            raise ValueError(f"Channel {channel_id} not found")
        
        print(f"📺 Channel: {channel_info['title']}")
        print(f"📊 {channel_info['subscriber_count']:,} subscribers")
        print(f"🎬 {channel_info['video_count']} videos\n")
        
        # Get video IDs
        print(f"🔍 Fetching latest {max_videos} videos...")
        video_ids = await self.get_channel_videos(channel_id, max_videos)
        print(f"✅ Found {len(video_ids)} videos\n")
        
        # Get video details
        videos = []
        for idx, video_id in enumerate(video_ids, 1):
            print(f"📹 Processing video {idx}/{len(video_ids)}: {video_id}")
            video_details = await self.get_video_details(video_id)
            
            if video_details:
                print(f"   Title: {video_details['title'][:60]}...")
                print(f"   Stats: {video_details['view_count']:,} views, {video_details['like_count']} likes, {video_details['comment_count']} comments")
                
                # Get comments if enabled
                if fetch_comments and video_details['comment_count'] > 0:
                    print(f"   💬 Fetching comments...")
                    comments = await self.get_video_comments(video_id)
                    video_details['comments'] = comments
                    print(f"   ✅ Got {len(comments)} comments")
                else:
                    video_details['comments'] = []
                
                videos.append(video_details)
            
            print()
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        return {
            "channel": channel_info,
            "videos": videos,
            "fetched_at": datetime.now().isoformat()
        }


# Convenience function
async def fetch_youtube_analytics(channel_id: str, max_videos: int = 50) -> Dict[str, Any]:
    """
    Fetch YouTube analytics for a channel
    """
    yt = YouTubeAnalytics()
    return await yt.get_channel_analytics(channel_id, max_videos=max_videos, fetch_comments=True)


if __name__ == "__main__":
    # Test with a channel ID
    import sys
    
    if len(sys.argv) > 1:
        channel_id = sys.argv[1]
    else:
        # Example: Use your channel ID here
        channel_id = input("Enter YouTube channel ID: ")
    
    data = asyncio.run(fetch_youtube_analytics(channel_id, max_videos=10))
    
    print("\n" + "="*60)
    print("📊 ANALYTICS SUMMARY")
    print("="*60)
    print(f"Channel: {data['channel']['title']}")
    print(f"Videos analyzed: {len(data['videos'])}")
    print(f"Total views: {sum(v['view_count'] for v in data['videos']):,}")
    print(f"Total likes: {sum(v['like_count'] for v in data['videos']):,}")
    print(f"Total comments: {sum(len(v['comments']) for v in data['videos']):,}")
