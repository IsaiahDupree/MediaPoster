#!/usr/bin/env python3
"""
Test Music Extraction from Instagram Scraper Stable API

This script will work once the correct endpoint paths are identified.
Update the ENDPOINT variable with the correct endpoint path.
"""

import httpx
import os
import json
import asyncio
from typing import List, Dict, Optional

# Configuration
API_BASE = "https://instagram-scraper-stable-api.p.rapidapi.com"
API_KEY = os.getenv("RAPIDAPI_KEY")

# TODO: Update this with the correct endpoint path once confirmed
ENDPOINT = "/v1/reels"  # Replace with actual working endpoint

if not API_KEY:
    print("ERROR: RAPIDAPI_KEY not set in environment")
    exit(1)


def get_headers() -> Dict[str, str]:
    return {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
        "Content-Type": "application/json"
    }


async def extract_music_from_reels(username: str, count: int = 12) -> List[Dict]:
    """
    Extract music/audio metadata from user reels.
    
    Args:
        username: Instagram username
        count: Number of reels to fetch
    
    Returns:
        List of music tracks with metadata
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{API_BASE}{ENDPOINT}",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": username,
                    "count": count
                }
            )
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []
            
            data = response.json()
            items = data.get("data", {}).get("items", [])
            
            if not items:
                print(f"⚠️  No reels found for @{username}")
                return []
            
            print(f"✓ Found {len(items)} reels for @{username}")
            
            music_tracks = []
            
            for item in items:
                clips_metadata = item.get("clips_metadata", {})
                
                # Extract music library audio
                music_info = clips_metadata.get("music_info", {})
                if music_info:
                    music_asset = music_info.get("music_asset_info", {})
                    audio_url = music_asset.get("progressive_download_url")
                    
                    if audio_url:
                        track = {
                            "type": "music",
                            "audio_id": music_asset.get("audio_id"),
                            "title": music_asset.get("title", "Unknown"),
                            "artist": music_asset.get("display_artist", "Unknown"),
                            "audio_url": audio_url,
                            "duration_ms": music_asset.get("duration_in_ms"),
                            "reel_id": item.get("id"),
                            "reel_shortcode": item.get("code"),
                            "play_count": item.get("play_count", 0),
                            "like_count": item.get("like_count", 0),
                            "comment_count": item.get("comment_count", 0)
                        }
                        music_tracks.append(track)
                
                # Extract original sound
                original_sound = clips_metadata.get("original_sound_info", {})
                if original_sound:
                    audio_asset = original_sound.get("audio_asset_info", {})
                    audio_url = audio_asset.get("progressive_download_url")
                    
                    if audio_url:
                        track = {
                            "type": "original_sound",
                            "title": original_sound.get("original_audio_title", "Original Sound"),
                            "artist": original_sound.get("ig_artist", {}).get("username", "Unknown"),
                            "audio_url": audio_url,
                            "reel_id": item.get("id"),
                            "reel_shortcode": item.get("code"),
                            "play_count": item.get("play_count", 0),
                            "like_count": item.get("like_count", 0),
                            "comment_count": item.get("comment_count", 0)
                        }
                        music_tracks.append(track)
            
            return music_tracks
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return []


async def test_audio_url_accessibility(audio_url: str) -> bool:
    """Test if an audio URL is accessible"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.head(audio_url, follow_redirects=True)
            return response.status_code == 200
        except:
            return False


async def main():
    """Main test function"""
    print("=" * 80)
    print("Instagram Music Extraction Test")
    print("=" * 80)
    print()
    
    # Test with a known account
    test_username = "instagram"  # Change to account with reels
    
    print(f"Testing music extraction from @{test_username}...")
    print(f"Using endpoint: {ENDPOINT}")
    print()
    
    music_tracks = await extract_music_from_reels(test_username, count=12)
    
    if not music_tracks:
        print("❌ No music tracks found")
        print()
        print("Possible reasons:")
        print("1. Endpoint path is incorrect (update ENDPOINT variable)")
        print("2. Account has no reels with music")
        print("3. API subscription doesn't have access")
        print("4. API structure has changed")
        return
    
    print(f"✓ Found {len(music_tracks)} music tracks")
    print()
    
    # Group by type
    music_library = [t for t in music_tracks if t["type"] == "music"]
    original_sounds = [t for t in music_tracks if t["type"] == "original_sound"]
    
    print(f"  Music Library: {len(music_library)}")
    print(f"  Original Sounds: {len(original_sounds)}")
    print()
    
    # Display top tracks
    print("Top Music Tracks:")
    print("-" * 80)
    
    for i, track in enumerate(music_tracks[:10], 1):
        print(f"{i}. {track['title']} by {track['artist']}")
        print(f"   Type: {track['type']}")
        print(f"   Audio ID: {track.get('audio_id', 'N/A')}")
        print(f"   Reel: {track['reel_shortcode']} ({track['play_count']:,} views)")
        print(f"   URL: {track['audio_url'][:80]}...")
        
        # Test URL accessibility
        is_accessible = await test_audio_url_accessibility(track['audio_url'])
        print(f"   Accessible: {'✓' if is_accessible else '✗'}")
        print()
    
    # Save results
    output_file = "music_extraction_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "username": test_username,
            "endpoint": ENDPOINT,
            "total_tracks": len(music_tracks),
            "music_library_count": len(music_library),
            "original_sounds_count": len(original_sounds),
            "tracks": music_tracks
        }, f, indent=2)
    
    print(f"✓ Results saved to {output_file}")
    print()
    print("=" * 80)
    print("Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

