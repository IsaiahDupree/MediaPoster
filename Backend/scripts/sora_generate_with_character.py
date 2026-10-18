#!/usr/bin/env python3
"""
Sora Generate with Character - Automated video generation with @isaiahdupree

Usage:
    python scripts/sora_generate_with_character.py "your prompt here"
    python scripts/sora_generate_with_character.py  # Uses default prompt

Features:
- Automatically uses @isaiahdupree character
- Enters prompt in Sora
- Polls /drafts page for new videos
- Downloads completed videos
- Triggers watermark removal pipeline
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.sora_full_automation import SoraFullAutomation


# Default prompt if none provided
DEFAULT_PROMPT = "ever feel like managing all your social media is like juggling cats? what if there was a way to simplify the chaos with just one click? curious? there's more to this than meets the eye..."

# Character to use
CHARACTER = "isaiahdupree"


async def generate_sora_video(prompt: str, character: str = CHARACTER) -> str:
    """
    Generate a Sora video with the specified prompt and character.
    
    Returns: Path to downloaded video or None if failed
    """
    sora = SoraFullAutomation()
    
    print("\n" + "="*60)
    print("🎬 SORA VIDEO GENERATION")
    print("="*60)
    print(f"Character: @{character}")
    print(f"Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print("="*60)
    
    # Step 1: Navigate to Sora and check login
    print("\n📍 Step 1: Checking Sora login status...")
    sora.navigate_to_explore()
    time.sleep(3)
    
    if not sora.check_login():
        print("❌ Not logged into Sora - please log in manually")
        return None
    print("✅ Logged into Sora")
    
    # Step 2: Check usage/credits
    print("\n📊 Step 2: Checking usage...")
    usage = sora.get_usage()
    gens_left = usage.get('video_gens_left', 0)
    print(f"   Video generations left: {gens_left}")
    
    if gens_left == 0:
        print("❌ No generations left - wait for reset")
        return None
    
    # Step 3: Check queue
    print("\n📋 Step 3: Checking queue...")
    if not sora.can_generate():
        print("⏳ Queue full, waiting for slot...")
        while not sora.can_generate():
            await asyncio.sleep(30)
    print("✅ Queue has space")
    
    # Step 4: Generate video
    print(f"\n🎬 Step 4: Starting generation with @{character}...")
    
    success = await sora.generate_video(
        prompt=prompt,
        character=character,
        duration=15,
        aspect_ratio="Portrait",
        wait_for_slot=True
    )
    
    if not success:
        print("❌ Failed to start generation")
        return None
    
    print("✅ Generation started!")
    
    # Step 5: Poll for completion
    print("\n⏳ Step 5: Polling for completion (this may take a few minutes)...")
    
    # Navigate to drafts and poll
    completed = await poll_drafts_for_new_videos(sora, timeout=600)
    
    if not completed:
        print("⚠️ No new videos detected within timeout")
        print("   Check Sora manually - video may still be generating")
        return None
    
    # Step 6: Download
    print(f"\n📥 Step 6: Downloading {len(completed)} video(s)...")
    downloaded_paths = []
    
    for video in completed:
        video_src = video.get('video_src')
        if video_src:
            path = download_video_direct(video_src, sora.DOWNLOAD_DIR)
            if path:
                downloaded_paths.append(path)
                print(f"   ✅ Downloaded: {path}")
    
    if downloaded_paths:
        # Step 7: Trigger watermark removal
        print("\n🧹 Step 7: Triggering watermark removal...")
        for path in downloaded_paths:
            await trigger_watermark_removal(path)
        
        print("\n" + "="*60)
        print("✅ GENERATION COMPLETE")
        print(f"   Downloaded: {len(downloaded_paths)} video(s)")
        print(f"   Location: {sora.DOWNLOAD_DIR}")
        print("="*60)
        
        return downloaded_paths[0] if downloaded_paths else None
    
    return None


async def poll_drafts_for_new_videos(sora: SoraFullAutomation, timeout: int = 600):
    """
    Poll the /drafts page for new videos.
    
    Returns list of new video dicts when found.
    """
    logger.info("Navigating to /drafts to poll for new videos...")
    
    # Get initial video count
    initial_videos = sora.get_completed_videos(scroll_count=2)
    initial_count = len(initial_videos)
    initial_srcs = set(v.get('video_src', '') for v in initial_videos)
    
    logger.info(f"Initial drafts count: {initial_count}")
    
    start_time = time.time()
    poll_count = 0
    
    while time.time() - start_time < timeout:
        poll_count += 1
        elapsed = int(time.time() - start_time)
        
        # Poll drafts
        current_videos = sora.get_completed_videos(scroll_count=2)
        current_count = len(current_videos)
        
        # Check for new videos
        new_videos = [
            v for v in current_videos 
            if v.get('video_src') and v.get('video_src') not in initial_srcs
        ]
        
        if new_videos:
            logger.info(f"✅ Found {len(new_videos)} new video(s)!")
            return new_videos
        
        logger.info(f"Poll #{poll_count}: {current_count} videos, {elapsed}s elapsed, waiting...")
        await asyncio.sleep(30)
    
    logger.warning("Timeout reached while polling for new videos")
    return []


def download_video_direct(video_url: str, download_dir: Path) -> str:
    """Download video directly from URL."""
    import subprocess
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"sora_{CHARACTER}_{timestamp}.mp4"
    local_path = download_dir / filename
    
    try:
        result = subprocess.run(
            ['curl', '-L', '-o', str(local_path), video_url],
            capture_output=True,
            timeout=180
        )
        
        if local_path.exists() and local_path.stat().st_size > 10000:
            size_mb = local_path.stat().st_size / 1024 / 1024
            logger.info(f"Downloaded: {local_path} ({size_mb:.1f} MB)")
            return str(local_path)
    except Exception as e:
        logger.error(f"Download failed: {e}")
    
    return None


async def trigger_watermark_removal(video_path: str):
    """Trigger watermark removal via the pipeline."""
    try:
        from services.sora_daily.watermark_service import WatermarkRemovalService
        
        service = WatermarkRemovalService()
        if service.is_available:
            result = await service.remove_watermark(video_path)
            if result.get('success'):
                logger.info(f"✅ Watermark removed: {result.get('output_path')}")
                return result.get('output_path')
            else:
                logger.warning(f"Watermark removal failed: {result.get('error')}")
        else:
            logger.warning("BlankLogo not available - skipping watermark removal")
    except Exception as e:
        logger.error(f"Watermark removal error: {e}")
    
    return None


async def main():
    """Main entry point."""
    # Get prompt from command line or use default
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = DEFAULT_PROMPT
        print(f"Using default prompt (pass custom prompt as argument)")
    
    # Generate video
    result = await generate_sora_video(prompt, CHARACTER)
    
    if result:
        print(f"\n🎉 Success! Video saved to: {result}")
    else:
        print("\n⚠️ Generation did not complete - check Sora manually")


if __name__ == "__main__":
    asyncio.run(main())
