#!/usr/bin/env python3
"""
Test Music/Audio Extraction from Instagram Looter2 API

Tests the instagram-looter2.p.rapidapi.com API to extract:
- Music/audio from reels
- Video URLs
- Engagement metrics
- Captions and hashtags
"""

import httpx
import os
import json
import asyncio
from typing import List, Dict, Optional

# Configuration
API_BASE = "https://instagram-looter2.p.rapidapi.com"
API_KEY = os.getenv("RAPIDAPI_KEY")

if not API_KEY:
    print("ERROR: RAPIDAPI_KEY not set in environment")
    exit(1)


def get_headers() -> Dict[str, str]:
    return {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "instagram-looter2.p.rapidapi.com"
    }


async def get_profile_with_posts(username: str) -> Optional[Dict]:
    """Get user profile with posts using /profile endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{API_BASE}/profile",
                headers=get_headers(),
                params={"username": username}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Profile endpoint returned {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"❌ Error getting profile: {e}")
            return None


async def get_post_details(shortcode: str) -> Optional[Dict]:
    """Get detailed post information using /post endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{API_BASE}/post",
                headers=get_headers(),
                params={"shortcode": shortcode}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Post endpoint returned {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"❌ Error getting post: {e}")
            return None


async def try_v1_endpoints(username: str) -> Optional[Dict]:
    """Try v1 endpoints as fallback"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        endpoints = [
            ("/v1/info", {"username_or_id_or_url": username}),
            ("/v1/posts", {"username_or_id_or_url": username, "limit": 12}),
        ]
        
        for endpoint, params in endpoints:
            try:
                response = await client.get(
                    f"{API_BASE}{endpoint}",
                    headers=get_headers(),
                    params=params
                )
                
                if response.status_code == 200:
                    print(f"✓ {endpoint} works!")
                    return response.json()
                else:
                    print(f"✗ {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"✗ {endpoint}: {e}")
        
        return None


def extract_music_from_profile_data(data: Dict) -> List[Dict]:
    """Extract music/audio information from profile response"""
    music_tracks = []
    
    # Check different response structures
    edges = []
    
    # Structure 1: edge_owner_to_timeline_media.edges
    timeline = data.get("edge_owner_to_timeline_media", {})
    if timeline:
        edges = timeline.get("edges", [])
    
    # Structure 2: data.items (from v1/posts)
    if not edges and "data" in data:
        items = data.get("data", {}).get("items", [])
        edges = [{"node": item} for item in items]
    
    # Structure 3: items directly
    if not edges and "items" in data:
        edges = [{"node": item} for item in data["items"]]
    
    print(f"Found {len(edges)} posts/reels to analyze")
    
    for edge in edges:
        node = edge.get("node", edge)
        
        # Check if it's a video/reel
        is_video = node.get("is_video", False)
        typename = node.get("typename", "")
        is_reel = "Video" in typename or "Reel" in typename or is_video
        
        if not is_reel:
            continue
        
        # Extract video URL (can be used as audio source)
        video_url = None
        if "video_url" in node:
            video_url = node["video_url"]
        elif "display_url" in node and is_video:
            video_url = node["display_url"]
        
        # Extract caption
        caption = ""
        caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
        if caption_edges:
            caption = caption_edges[0].get("node", {}).get("text", "")
        elif "caption" in node:
            caption = node["caption"]
        
        # Extract hashtags from caption
        hashtags = []
        if caption:
            import re
            hashtags = re.findall(r'#(\w+)', caption)
        
        # Extract engagement metrics
        like_count = 0
        comment_count = 0
        view_count = 0
        
        if "edge_liked_by" in node:
            like_count = node["edge_liked_by"].get("count", 0)
        elif "like_count" in node:
            like_count = node["like_count"]
        
        if "edge_media_to_comment" in node:
            comment_count = node["edge_media_to_comment"].get("count", 0)
        elif "comment_count" in node:
            comment_count = node["comment_count"]
        
        if "video_view_count" in node:
            view_count = node["video_view_count"]
        elif "play_count" in node:
            view_count = node["play_count"]
        elif "view_count" in node:
            view_count = node["view_count"]
        
        # Note: Instagram Looter2 API may not provide direct audio URLs
        # We'll use video URL as audio source
        if video_url:
            track = {
                "type": "video_audio",  # Audio extracted from video
                "title": caption[:50] if caption else "Instagram Video",
                "artist": "Unknown",  # Not available in this API
                "audio_url": video_url,  # Video URL can be used to extract audio
                "video_url": video_url,
                "reel_id": node.get("id"),
                "reel_shortcode": node.get("shortcode"),
                "play_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "hashtags": hashtags,
                "caption": caption[:200] if caption else "",
                "taken_at": node.get("taken_at_timestamp")
            }
            music_tracks.append(track)
    
    return music_tracks


async def get_detailed_post_with_audio(shortcode: str) -> Optional[Dict]:
    """Get detailed post data which might have audio information"""
    post_data = await get_post_details(shortcode)
    
    if not post_data:
        return None
    
    # Check for audio/music in detailed post response
    audio_info = {}
    
    # Check various possible locations for audio data
    if "clips_metadata" in post_data:
        clips = post_data["clips_metadata"]
        if "music_info" in clips:
            audio_info["music"] = clips["music_info"]
        if "original_sound_info" in clips:
            audio_info["original_sound"] = clips["original_sound_info"]
    
    # Check video URL
    video_url = post_data.get("video_url")
    if not video_url:
        video_url = post_data.get("display_url")
    
    if video_url:
        audio_info["video_url"] = video_url
        audio_info["audio_source"] = "video"  # Can extract audio from video
    
    return audio_info if audio_info else None


async def main():
    """Main test function"""
    print("=" * 80)
    print("Instagram Looter2 API - Music Extraction Test")
    print("=" * 80)
    print()
    
    # Test with a known account
    test_username = "instagram"  # Change to account with reels
    
    print(f"Testing with @{test_username}...")
    print()
    
    # Try profile endpoint first
    print("1. Trying /profile endpoint...")
    profile_data = await get_profile_with_posts(test_username)
    
    if not profile_data:
        print("   ✗ /profile endpoint failed, trying /v1 endpoints...")
        profile_data = await try_v1_endpoints(test_username)
    
    if not profile_data:
        print("   ❌ All endpoints failed")
        return
    
    print("   ✓ Got profile data!")
    print()
    
    # Extract music/audio information
    print("2. Extracting music/audio information...")
    music_tracks = extract_music_from_profile_data(profile_data)
    
    if not music_tracks:
        print("   ⚠️  No video/reel content found")
        print()
        print("   Trying to get detailed post information...")
        
        # Try to get a post shortcode from the profile
        edges = profile_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
        if edges:
            first_post = edges[0].get("node", {})
            shortcode = first_post.get("shortcode")
            
            if shortcode:
                print(f"   Getting details for post: {shortcode}")
                audio_info = await get_detailed_post_with_audio(shortcode)
                if audio_info:
                    print(f"   ✓ Found audio info in detailed post")
                    print(f"   Audio info: {json.dumps(audio_info, indent=2)}")
        return
    
    print(f"   ✓ Found {len(music_tracks)} video/reel tracks")
    print()
    
    # Display results
    print("3. Music/Audio Tracks Found:")
    print("-" * 80)
    
    for i, track in enumerate(music_tracks[:10], 1):
        print(f"\n{i}. {track['title']}")
        print(f"   Type: {track['type']}")
        print(f"   Shortcode: {track['reel_shortcode']}")
        print(f"   Views: {track['play_count']:,}")
        print(f"   Likes: {track['like_count']:,}")
        print(f"   Comments: {track['comment_count']:,}")
        print(f"   Video URL: {track['video_url'][:80]}...")
        print(f"   Hashtags: {', '.join(track['hashtags'][:5]) if track['hashtags'] else 'None'}")
        if track['caption']:
            print(f"   Caption: {track['caption'][:100]}...")
    
    # Save results
    output_file = "instagram_looter_music_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "username": test_username,
            "api": "instagram-looter2",
            "total_tracks": len(music_tracks),
            "tracks": music_tracks
        }, f, indent=2)
    
    print()
    print("=" * 80)
    print(f"✓ Results saved to {output_file}")
    print()
    print("Note: Instagram Looter2 API provides video URLs which can be")
    print("      used to extract audio. Direct audio URLs may not be available.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

