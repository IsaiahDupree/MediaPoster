#!/usr/bin/env python3
"""
Discover actual RapidAPI Instagram Scraper Stable API endpoints
Tests various endpoint patterns to find working ones
"""

import httpx
import os
import json
import asyncio
from typing import List, Dict

API_BASE = "https://instagram-scraper-stable-api.p.rapidapi.com"
API_KEY = os.getenv("RAPIDAPI_KEY")

if not API_KEY:
    print("ERROR: RAPIDAPI_KEY not set in environment")
    exit(1)

def get_headers() -> Dict[str, str]:
    return {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
        "Content-Type": "application/json"
    }


async def test_endpoint(method: str, endpoint: str, payload: Dict = None, params: Dict = None):
    """Test a single endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "POST":
                response = await client.post(
                    f"{API_BASE}{endpoint}",
                    headers=get_headers(),
                    json=payload
                )
            else:
                response = await client.get(
                    f"{API_BASE}{endpoint}",
                    headers=get_headers(),
                    params=params or payload
                )
            
            return {
                "endpoint": endpoint,
                "method": method,
                "status": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code == 200 else response.text[:500]
            }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "method": method,
                "status": "error",
                "success": False,
                "error": str(e)[:200]
            }


async def discover_endpoints():
    """Discover working endpoints"""
    
    # Based on the playground screenshot, try these patterns
    endpoints_to_test = [
        # Search endpoints
        ("POST", "/v1/search", {"query": "instagram"}),
        ("POST", "/search", {"query": "instagram"}),
        ("POST", "/Search", {"query": "instagram"}),
        
        # User Reels endpoints (various patterns)
        ("POST", "/User%20Reels", {"username_or_id_or_url": "instagram", "count": 5}),
        ("POST", "/user_reels", {"username_or_id_or_url": "instagram", "count": 5}),
        ("POST", "/UserReels", {"username_or_id_or_url": "instagram", "count": 5}),
        ("POST", "/v1/user_reels", {"username_or_id_or_url": "instagram", "count": 5}),
        ("POST", "/v1/reels", {"username_or_id_or_url": "instagram", "count": 5}),
        ("POST", "/user/reels", {"username_or_id_or_url": "instagram", "count": 5}),
        
        # User info endpoints
        ("POST", "/v1/info", {"username_or_id_or_url": "instagram"}),
        ("POST", "/Account%20Data", {"username_or_id_or_url": "instagram"}),
        ("POST", "/Account Data", {"username_or_id_or_url": "instagram"}),
        ("POST", "/account_data", {"username_or_id_or_url": "instagram"}),
        
        # User posts
        ("POST", "/v1/posts", {"username_or_id_or_url": "instagram", "count": 5}),
        ("POST", "/User%20Posts", {"username_or_id_or_url": "instagram", "count": 5}),
        
        # Detailed media endpoints
        ("GET", "/v1/reel_by_shortcode", {"shortcode": "CxYZaBC1234"}),
        ("GET", "/v1/media_by_shortcode", {"shortcode": "CxYZaBC1234"}),
        ("GET", "/Detailed%20Reel%20Data", {"shortcode": "CxYZaBC1234"}),
    ]
    
    print("=" * 80)
    print("RapidAPI Instagram Scraper Stable API - Endpoint Discovery")
    print("=" * 80)
    print()
    
    results = []
    
    for method, endpoint, payload in endpoints_to_test:
        print(f"Testing {method} {endpoint}...", end=" ")
        result = await test_endpoint(method, endpoint, payload)
        results.append(result)
        
        if result["success"]:
            print(f"✓ SUCCESS ({result['status']})")
            
            # Analyze response structure
            if isinstance(result["response"], dict):
                print(f"  Response keys: {list(result['response'].keys())}")
                
                # Check for music/audio data
                if "data" in result["response"]:
                    data = result["response"]["data"]
                    if isinstance(data, dict):
                        if "items" in data:
                            items = data["items"]
                            if items and isinstance(items[0], dict):
                                item = items[0]
                                if "clips_metadata" in item:
                                    print(f"  ✓ Has clips_metadata!")
                                    clips = item["clips_metadata"]
                                    if "music_info" in clips:
                                        print(f"  ✓ Has music_info!")
                                        music = clips["music_info"]
                                        if "music_asset_info" in music:
                                            asset = music["music_asset_info"]
                                            print(f"  ✓ Has music_asset_info!")
                                            if "progressive_download_url" in asset:
                                                print(f"  ✓✓✓ MUSIC URL FOUND!")
                                                print(f"     Title: {asset.get('title', 'N/A')}")
                                                print(f"     Artist: {asset.get('display_artist', 'N/A')}")
                                                print(f"     URL: {asset.get('progressive_download_url', 'N/A')[:80]}...")
        else:
            print(f"✗ FAILED ({result.get('status', 'error')})")
            if "error" in result:
                print(f"  Error: {result['error']}")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r["success"]]
    print(f"\n✓ Successful endpoints: {len(successful)}/{len(results)}")
    
    for result in successful:
        print(f"  {result['method']} {result['endpoint']}")
    
    # Check for music extraction capability
    music_endpoints = []
    for result in successful:
        if isinstance(result.get("response"), dict):
            # Check if response structure suggests music data
            data = result["response"].get("data", {})
            if isinstance(data, dict) and "items" in data:
                items = data["items"]
                if items and isinstance(items[0], dict):
                    if "clips_metadata" in items[0]:
                        music_endpoints.append(result["endpoint"])
    
    if music_endpoints:
        print(f"\n✓ Endpoints with music data: {len(music_endpoints)}")
        for endpoint in music_endpoints:
            print(f"  {endpoint}")
    else:
        print("\n⚠️  No endpoints with music data found in successful responses")
    
    return results


if __name__ == "__main__":
    asyncio.run(discover_endpoints())

