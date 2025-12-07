"""
Debug script to see raw TikTok API responses
"""
import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


async def test_raw_api():
    """Test raw API responses"""
    api_key = os.getenv("RAPIDAPI_KEY")
    username = "isaiah_dupree"
    
    print("\n" + "="*80)
    print("🔍 RAW API RESPONSE DEBUG")
    print("="*80 + "\n")
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "tiktok-video-feature-summary.p.rapidapi.com"
    }
    
    # Test 1: User Info
    print("📊 Test 1: User Info Endpoint")
    print("-" * 80)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://tiktok-video-feature-summary.p.rapidapi.com/user/info",
            headers=headers,
            params={"unique_id": username}
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        # Save full response
        with open("debug_user_info.json", "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Response saved to: debug_user_info.json")
        print(f"\nUser Data Structure:")
        if "data" in data:
            user_data = data.get("data", {})
            print(json.dumps(user_data, indent=2)[:1000] + "...")
    
    # Test 2: User Posts
    print("\n\n📊 Test 2: User Posts Endpoint")
    print("-" * 80)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://tiktok-video-feature-summary.p.rapidapi.com/user/posts",
            headers=headers,
            params={"unique_id": username, "count": 5}
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        # Save full response
        with open("debug_user_posts.json", "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Response saved to: debug_user_posts.json")
        
        if "data" in data and "videos" in data["data"]:
            videos = data["data"]["videos"]
            print(f"\n✅ Found {len(videos)} videos")
            
            if videos:
                print(f"\n📹 First Video Structure:")
                first_video = videos[0]
                
                # Check what fields are available
                print(f"\nAvailable fields:")
                for key in first_video.keys():
                    print(f"  - {key}: {type(first_video[key]).__name__}")
                
                # Check stats specifically
                if "stats" in first_video:
                    print(f"\n📈 Stats structure:")
                    print(json.dumps(first_video["stats"], indent=2))
                
                print(f"\n📄 Full first video (truncated):")
                print(json.dumps(first_video, indent=2)[:2000] + "...")
    
    # Test 3: Try Scraper7 API
    print("\n\n📊 Test 3: TikTok Scraper7 API (Fallback)")
    print("-" * 80)
    
    headers2 = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://tiktok-scraper7.p.rapidapi.com/user/posts",
            headers=headers2,
            params={"unique_id": username, "count": 5}
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        # Save full response
        with open("debug_scraper7_posts.json", "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Response saved to: debug_scraper7_posts.json")
        
        if "data" in data and "videos" in data["data"]:
            videos = data["data"]["videos"]
            print(f"\n✅ Found {len(videos)} videos from Scraper7")
            
            if videos:
                print(f"\n📹 First Video from Scraper7:")
                first_video = videos[0]
                
                # Check engagement data
                print(f"\nEngagement fields:")
                for key in ["diggCount", "commentCount", "playCount", "shareCount"]:
                    if key in first_video:
                        print(f"  - {key}: {first_video[key]}")
    
    print("\n" + "="*80)
    print("✅ DEBUG COMPLETE - Check the JSON files for full responses")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_raw_api())
