#!/usr/bin/env python3
"""
Download a single TikTok video using RapidAPI
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def extract_video_id(url: str) -> str:
    """Extract video ID from TikTok URL"""
    if '/video/' in url:
        return url.split('/video/')[-1].split('?')[0]
    raise ValueError(f"Could not extract video ID from URL: {url}")

def download_tiktok_video(video_url: str, output_dir: str):
    """
    Download TikTok video using RapidAPI tiktok-scraper7
    """
    rapidapi_key = os.getenv('RAPIDAPI_KEY')
    if not rapidapi_key:
        raise ValueError("RAPIDAPI_KEY not found in environment")
    
    video_id = extract_video_id(video_url)
    print(f"Video ID: {video_id}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Fetch video info from RapidAPI using TikTok Video No Watermark API
    print("Fetching video info from RapidAPI...")
    api_url = "https://tiktok-video-no-watermark2.p.rapidapi.com/"
    
    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": "tiktok-video-no-watermark2.p.rapidapi.com",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data_payload = {
        "url": video_url,
        "hd": "1"
    }
    
    response = requests.post(api_url, headers=headers, data=data_payload)
    response.raise_for_status()
    
    data = response.json()
    
    # Extract download URL from response
    download_url = None
    quality = "Standard"
    
    if 'data' in data:
        video_data = data['data']
        # Try different possible fields for download URL
        if isinstance(video_data, dict):
            download_url = (video_data.get('hdplay') or 
                          video_data.get('play') or 
                          video_data.get('wmplay') or
                          video_data.get('download_addr'))
            title = video_data.get('title', 'untitled')
            author = video_data.get('author', {}).get('unique_id', 'unknown') if isinstance(video_data.get('author'), dict) else 'unknown'
        elif isinstance(video_data, list) and len(video_data) > 0:
            download_url = video_data[0]
            title = 'untitled'
            author = 'unknown'
    elif 'play' in data:
        download_url = data['play']
        title = data.get('title', 'untitled')
        author = data.get('author', 'unknown')
    
    if not download_url:
        raise ValueError(f"No download URL found in API response. Response: {data}")
    
    print(f"Download URL found ({quality} quality)")
    
    # Clean filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_title:
        safe_title = f"tiktok_{video_id}"
    
    filename = f"{safe_title}_{video_id}.mp4"
    output_file = output_path / filename
    
    # Download video
    print(f"Downloading video to: {output_file}")
    video_response = requests.get(download_url, stream=True)
    video_response.raise_for_status()
    
    total_size = int(video_response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(output_file, 'wb') as f:
        for chunk in video_response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\rProgress: {percent:.1f}%", end='', flush=True)
    
    print(f"\n✓ Video downloaded successfully!")
    print(f"  File: {output_file}")
    print(f"  Size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"  Author: @{author}")
    print(f"  Title: {title}")
    
    return str(output_file)

if __name__ == "__main__":
    video_url = "https://www.tiktok.com/@isaiah_dupree/video/7589759762259086606"
    output_dir = "/Users/isaiahdupree/Documents/Software/Remotion/public/assets/videos"
    
    try:
        result = download_tiktok_video(video_url, output_dir)
        print(f"\n✓ Success! Video saved to: {result}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
