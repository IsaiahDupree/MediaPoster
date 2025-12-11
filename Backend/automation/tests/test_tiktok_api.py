"""
TikTok API Data Extraction via RapidAPI
========================================

Compare API vs browser scraping for extracting TikTok comments.

RapidAPI TikTok APIs to explore:
- TikTok Data API
- TikTok Scraper
- TikTok API by Suspended
"""

import os
import requests
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Test video URL
TEST_VIDEO_URL = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
VIDEO_ID = "7564912360520011038"


def extract_video_id(url: str) -> str:
    """Extract video ID from TikTok URL."""
    # URL format: https://www.tiktok.com/@username/video/VIDEO_ID
    if "/video/" in url:
        return url.split("/video/")[-1].split("?")[0]
    return url


class TikTokRapidAPI:
    """TikTok data extraction via RapidAPI."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            print("⚠️  RAPIDAPI_KEY not set. Set it in environment or pass to constructor.")
        
        # Common RapidAPI TikTok endpoints
        self.apis = {
            "tiktok_scraper": {
                "host": "tiktok-scraper7.p.rapidapi.com",
                "comments_endpoint": "/video/comments"
            },
            "tiktok_api": {
                "host": "tiktok-api23.p.rapidapi.com",
                "comments_endpoint": "/api/post/comments"
            },
            "tiktok_data": {
                "host": "tiktok-video-no-watermark2.p.rapidapi.com",
                "comments_endpoint": "/video/comments"
            }
        }
    
    def get_comments_scraper7(self, video_id: str, count: int = 50):
        """Get comments using tiktok-scraper7 API."""
        url = "https://tiktok-scraper7.p.rapidapi.com/video/comments"
        
        querystring = {
            "video_id": video_id,
            "count": str(count),
            "cursor": "0"
        }
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
        }
        
        print(f"Calling tiktok-scraper7 API for video {video_id}...")
        response = requests.get(url, headers=headers, params=querystring)
        
        return response.json() if response.status_code == 200 else {"error": response.text, "status": response.status_code}
    
    def get_comments_api23(self, video_id: str, count: int = 50):
        """Get comments using tiktok-api23 API."""
        url = "https://tiktok-api23.p.rapidapi.com/api/post/comments"
        
        querystring = {
            "videoId": video_id,
            "count": str(count)
        }
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
        }
        
        print(f"Calling tiktok-api23 API for video {video_id}...")
        response = requests.get(url, headers=headers, params=querystring)
        
        return response.json() if response.status_code == 200 else {"error": response.text, "status": response.status_code}
    
    def get_video_info(self, video_url: str):
        """Get video metadata."""
        url = "https://tiktok-scraper7.p.rapidapi.com/video/info"
        
        querystring = {"video_url": video_url}
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
        }
        
        print(f"Getting video info for {video_url[:50]}...")
        response = requests.get(url, headers=headers, params=querystring)
        
        return response.json() if response.status_code == 200 else {"error": response.text, "status": response.status_code}


def discover_all_endpoints(api_key: str):
    """
    Discover ALL available endpoints on tiktok-scraper7.
    Tests common TikTok API endpoint patterns.
    """
    
    host = "tiktok-scraper7.p.rapidapi.com"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": host
    }
    
    test_url = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
    test_user = "mewtru"
    test_hashtag = "arduino"
    
    # All potential endpoints to test
    endpoints = [
        # Video endpoints
        {"path": "/", "params": {"url": test_url}, "desc": "Video info by URL"},
        {"path": "/video/info", "params": {"url": test_url}, "desc": "Video info alt"},
        
        # Comment endpoints
        {"path": "/comment/list", "params": {"url": test_url, "count": "50", "cursor": "0"}, "desc": "Comments (paginated)"},
        {"path": "/comment/reply/list", "params": {"url": test_url, "comment_id": "0", "count": "20"}, "desc": "Comment replies"},
        
        # User endpoints
        {"path": "/user/info", "params": {"unique_id": test_user}, "desc": "User info"},
        {"path": "/user/posts", "params": {"unique_id": test_user, "count": "30", "cursor": "0"}, "desc": "User posts"},
        {"path": "/user/followers", "params": {"unique_id": test_user, "count": "30"}, "desc": "User followers"},
        {"path": "/user/following", "params": {"unique_id": test_user, "count": "30"}, "desc": "User following"},
        {"path": "/user/liked", "params": {"unique_id": test_user, "count": "30"}, "desc": "User liked videos"},
        
        # Search endpoints
        {"path": "/search/user", "params": {"keywords": test_user, "count": "30"}, "desc": "Search users"},
        {"path": "/search/video", "params": {"keywords": test_hashtag, "count": "30"}, "desc": "Search videos"},
        {"path": "/search/general", "params": {"keywords": test_hashtag, "count": "30"}, "desc": "General search"},
        
        # Feed endpoints
        {"path": "/feed/list", "params": {"count": "30"}, "desc": "Trending feed"},
        {"path": "/feed/recommended", "params": {"count": "30"}, "desc": "Recommended feed"},
        
        # Hashtag/Challenge endpoints
        {"path": "/challenge/posts", "params": {"challenge_name": test_hashtag, "count": "30"}, "desc": "Hashtag posts"},
        {"path": "/challenge/info", "params": {"challenge_name": test_hashtag}, "desc": "Hashtag info"},
        
        # Music endpoints
        {"path": "/music/info", "params": {"music_id": "0"}, "desc": "Music info"},
        {"path": "/music/posts", "params": {"music_id": "0", "count": "30"}, "desc": "Music posts"},
    ]
    
    working_endpoints = []
    failed_endpoints = []
    
    print(f"\n{'='*60}")
    print("DISCOVERING ALL TIKTOK-SCRAPER7 ENDPOINTS")
    print(f"{'='*60}\n")
    
    for ep in endpoints:
        try:
            response = requests.get(
                f"https://{host}{ep['path']}",
                headers=headers,
                params=ep["params"],
                timeout=10
            )
            
            status = response.status_code
            if status == 200:
                data = response.json()
                working_endpoints.append({
                    "path": ep["path"],
                    "params": list(ep["params"].keys()),
                    "desc": ep["desc"],
                    "sample_response": str(data)[:100]
                })
                print(f"✅ {ep['path']:25} - {ep['desc']}")
            else:
                failed_endpoints.append({"path": ep["path"], "status": status, "desc": ep["desc"]})
                print(f"❌ {ep['path']:25} - {status}")
        except Exception as e:
            failed_endpoints.append({"path": ep["path"], "error": str(e), "desc": ep["desc"]})
            print(f"❌ {ep['path']:25} - Error: {str(e)[:30]}")
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {len(working_endpoints)} working, {len(failed_endpoints)} failed")
    print(f"{'='*60}\n")
    
    return {"working": working_endpoints, "failed": failed_endpoints}


def get_all_comments_paginated(api_key: str, video_url: str, max_comments: int = 500):
    """
    Get ALL comments using pagination.
    The API returns ~50 comments per request with a cursor for pagination.
    """
    
    host = "tiktok-scraper7.p.rapidapi.com"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": host
    }
    
    all_comments = []
    cursor = 0
    page = 1
    
    print(f"\n--- Fetching ALL comments (max {max_comments}) ---")
    
    while len(all_comments) < max_comments:
        response = requests.get(
            f"https://{host}/comment/list",
            headers=headers,
            params={"url": video_url, "count": "50", "cursor": str(cursor)},
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"Error on page {page}: {response.status_code}")
            break
        
        data = response.json()
        
        if "data" not in data or "comments" not in data["data"]:
            print(f"No more comments on page {page}")
            break
        
        comments = data["data"]["comments"]
        if not comments:
            print(f"Empty comments on page {page}")
            break
        
        all_comments.extend(comments)
        print(f"Page {page}: Got {len(comments)} comments (total: {len(all_comments)})")
        
        # Check for next cursor
        cursor = data["data"].get("cursor", 0)
        has_more = data["data"].get("hasMore", False)
        
        if not has_more or cursor == 0:
            print("No more pages")
            break
        
        page += 1
    
    print(f"\n✅ Total comments fetched: {len(all_comments)}")
    return all_comments


def try_tiktok_scraper7(api_key: str, video_id: str, video_url: str):
    """
    Try tiktok-scraper7 API endpoints.
    
    CONFIRMED WORKING ENDPOINTS:
    - GET /                    : Video info by URL
    - GET /comment/list        : Comments with pagination (cursor)
    - GET /user/info           : User profile info
    - GET /user/posts          : User's videos
    - GET /challenge/posts     : Hashtag videos
    - GET /feed/list           : Trending feed
    - GET /search/user         : Search users
    - GET /search/video        : Search videos
    """
    
    host = "tiktok-scraper7.p.rapidapi.com"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": host
    }
    
    results = {}
    
    # Endpoint 1: Get video info by URL (root endpoint)
    print("\n--- Testing: GET / (video info) ---")
    try:
        response = requests.get(
            f"https://{host}/",
            headers=headers,
            params={"url": video_url},
            timeout=15
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results["video_info"] = data
            print(f"✅ Video info retrieved!")
            if "data" in data:
                d = data["data"]
                print(f"   Title: {str(d.get('title', 'N/A'))[:50]}")
                print(f"   Author: {d.get('author', {}).get('nickname', 'N/A')}")
                print(f"   Likes: {d.get('digg_count', 'N/A')}")
                print(f"   Comments: {d.get('comment_count', 'N/A')}")
                print(f"   Shares: {d.get('share_count', 'N/A')}")
                print(f"   Views: {d.get('play_count', 'N/A')}")
        else:
            print(f"❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Endpoint 2: Get comments with pagination
    print("\n--- Testing: GET /comment/list (with pagination) ---")
    try:
        all_comments = get_all_comments_paginated(api_key, video_url, max_comments=100)
        results["all_comments"] = all_comments
        
        # Show sample
        print("\nSample comments:")
        for i, c in enumerate(all_comments[:5]):
            user = c.get("user", {}).get("nickname", "Unknown")
            text = c.get("text", "")[:50]
            likes = c.get("digg_count", 0)
            print(f"   {i+1}. @{user} ({likes} likes): {text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Endpoint 3: User info
    print("\n--- Testing: GET /user/info ---")
    try:
        response = requests.get(
            f"https://{host}/user/info",
            headers=headers,
            params={"unique_id": "mewtru"},
            timeout=15
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results["user_info"] = data
            print(f"✅ User info retrieved!")
            if "data" in data:
                u = data["data"]
                print(f"   Nickname: {u.get('nickname', 'N/A')}")
                print(f"   Followers: {u.get('follower_count', 'N/A')}")
                print(f"   Following: {u.get('following_count', 'N/A')}")
                print(f"   Likes: {u.get('heart_count', 'N/A')}")
                print(f"   Videos: {u.get('video_count', 'N/A')}")
        else:
            print(f"❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return results


def try_multiple_apis(api_key: str, video_id: str, video_url: str):
    """Try multiple TikTok APIs to find one that works."""
    
    apis_to_try = [
        {
            "name": "TikTok Scraper7 - Video Info",
            "host": "tiktok-scraper7.p.rapidapi.com",
            "endpoint": f"/?url={video_url}"
        },
        {
            "name": "TikTok Scraper7 - Comments",
            "host": "tiktok-scraper7.p.rapidapi.com",
            "endpoint": f"/comment/list?url={video_url}&count=50"
        }
    ]
    
    for api in apis_to_try:
        print(f"\n--- Trying: {api['name']} ---")
        try:
            response = requests.get(
                f"https://{api['host']}{api['endpoint']}",
                headers={
                    "x-rapidapi-key": api_key,
                    "x-rapidapi-host": api['host']
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS! Status: {response.status_code}")
                print(f"Response preview: {str(data)[:200]}...")
                return {"api": api['name'], "data": data}
            else:
                print(f"❌ Failed: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return None


def test_api_comments():
    """Test getting comments via RapidAPI tiktok-scraper7."""
    
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        print("\n" + "="*60)
        print("⚠️  RAPIDAPI_KEY environment variable not set!")
        print("="*60)
        return
    
    print(f"\n{'='*60}")
    print(f"TIKTOK-SCRAPER7 API TEST")
    print(f"{'='*60}")
    print(f"Video: {TEST_VIDEO_URL}")
    print(f"Video ID: {VIDEO_ID}")
    print(f"API Key: {api_key[:20]}...")
    print(f"\nNOTE: You must subscribe to tiktok-scraper7 on RapidAPI:")
    print(f"https://rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7")
    
    # Try tiktok-scraper7 specific endpoints
    results = try_tiktok_scraper7(api_key, VIDEO_ID, TEST_VIDEO_URL)
    
    if results:
        # Save results to file
        output_dir = Path(__file__).parent / "extracted_data"
        output_dir.mkdir(exist_ok=True)
        
        filename = f"api_data_{VIDEO_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Saved results to: {filepath}")
    else:
        print("\n❌ No data retrieved.")
        print("\nTo use this API:")
        print("1. Go to: https://rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7")
        print("2. Click 'Subscribe to Test' (free tier available)")
        print("3. Your existing RAPIDAPI_KEY will work once subscribed")


def compare_api_vs_scraping():
    """Compare API speed vs browser scraping."""
    import time
    
    print("\n=== API vs BROWSER SCRAPING COMPARISON ===\n")
    
    # API timing
    api_key = os.getenv("RAPIDAPI_KEY")
    if api_key:
        api = TikTokRapidAPI(api_key)
        
        start = time.time()
        comments = api.get_comments_scraper7(VIDEO_ID, count=50)
        api_time = time.time() - start
        
        api_count = len(comments.get("data", {}).get("comments", [])) if "data" in comments else 0
        print(f"API: Retrieved {api_count} comments in {api_time:.2f}s")
    else:
        print("API: Skipped (no RAPIDAPI_KEY)")
    
    print("\nBrowser scraping would take ~10-30 seconds for same data")
    print("API is typically 10-50x faster for bulk data extraction")


def test_discover_endpoints():
    """Discover all working endpoints."""
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("RAPIDAPI_KEY not set")
        return
    
    results = discover_all_endpoints(api_key)
    
    # Save results
    output_dir = Path(__file__).parent / "extracted_data"
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / "api_endpoints_discovered.json"
    
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Saved to: {filepath}")
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "discover":
        test_discover_endpoints()
    else:
        test_api_comments()
        print("\n" + "="*60)
        compare_api_vs_scraping()
