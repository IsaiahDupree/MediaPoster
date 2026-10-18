#!/usr/bin/env python3
"""
Test Video Pipeline with Sora Videos
=====================================
Tests the video_ready_pipeline with real Sora videos.

Usage:
    python scripts/test_video_pipeline.py
    python scripts/test_video_pipeline.py --video path/to/video.mp4
    python scripts/test_video_pipeline.py --all  # Process all videos
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, format="<level>{level: <8}</level> | {message}", level="INFO")


async def test_single_video(video_path: str, publish: bool = False):
    """Test pipeline with a single video"""
    from services.video_ready_pipeline import VideoReadyPipeline
    
    print("\n" + "="*60)
    print("🎬 VIDEO PIPELINE TEST")
    print("="*60)
    print(f"Video: {video_path}")
    print(f"Size: {Path(video_path).stat().st_size / 1024 / 1024:.2f} MB")
    print(f"Publish: {'Yes' if publish else 'No (analysis only)'}")
    print("="*60 + "\n")
    
    pipeline = VideoReadyPipeline()
    
    start_time = datetime.now()
    
    result = await pipeline.process_video_ready(
        video_path=video_path,
        source="sora_test",
        publish_to=["youtube", "tiktok"] if publish else [],
        auto_publish=publish,
        metadata={
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("📊 RESULTS")
    print("="*60)
    print(f"Status: {result.get('status')}")
    print(f"Video ID: {result.get('video_id')}")
    print(f"Time: {elapsed:.1f}s")
    
    if result.get('analysis'):
        analysis = result['analysis']
        print(f"\n📝 AI ANALYSIS:")
        print(f"   Virality Score: {analysis.get('virality_score', 0)}/100")
        print(f"   Content Type: {analysis.get('content_type', 'N/A')}")
        print(f"   Mood: {analysis.get('mood', 'N/A')}")
        print(f"   Hook Strength: {analysis.get('hook_strength', 0)}/10")
        print(f"\n   YouTube Title: {analysis.get('youtube_title', 'N/A')[:60]}...")
        print(f"   TikTok Caption: {analysis.get('tiktok_caption', 'N/A')[:60]}...")
        print(f"   Hashtags: {', '.join(analysis.get('hashtags', [])[:5])}")
        
        # Count populated fields
        populated = sum(1 for v in analysis.values() if v)
        total = len(analysis)
        print(f"\n   Fields Populated: {populated}/{total} ({100*populated//total}%)")
    
    if result.get('publish_results'):
        print(f"\n📤 PUBLISH RESULTS:")
        for pr in result['publish_results']:
            status = "✅" if pr.get('success') else "❌"
            print(f"   {status} {pr.get('platform')}: {pr.get('status', pr.get('error', 'unknown'))}")
    
    print("="*60 + "\n")
    
    return result


async def list_available_videos():
    """List all available Sora videos"""
    sora_dir = Path(__file__).parent.parent / "data" / "sora_videos"
    
    videos = list(sora_dir.glob("*.mp4"))
    
    print("\n📹 AVAILABLE SORA VIDEOS:")
    print("-" * 50)
    for i, v in enumerate(videos, 1):
        size_mb = v.stat().st_size / 1024 / 1024
        print(f"  {i}. {v.name} ({size_mb:.1f} MB)")
    print(f"\nTotal: {len(videos)} videos")
    
    return videos


async def main():
    parser = argparse.ArgumentParser(description="Test Video Pipeline")
    parser.add_argument("--video", type=str, help="Path to specific video")
    parser.add_argument("--all", action="store_true", help="Process all videos")
    parser.add_argument("--publish", action="store_true", help="Actually publish to platforms")
    parser.add_argument("--list", action="store_true", help="List available videos")
    
    args = parser.parse_args()
    
    if args.list:
        await list_available_videos()
        return
    
    if args.video:
        video_path = args.video
    else:
        # Use first Sora video found
        videos = await list_available_videos()
        if not videos:
            print("❌ No videos found in data/sora_videos/")
            return
        
        # Pick smallest video for quick test
        video_path = str(min(videos, key=lambda v: v.stat().st_size))
        print(f"\n🎯 Using smallest video for test: {Path(video_path).name}")
    
    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    result = await test_single_video(video_path, publish=args.publish)
    
    # Return exit code based on result
    return 0 if result.get('status') == 'completed' else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code or 0)
