#!/usr/bin/env python3
"""
Sora Story Test: @isaiahdupree Preparing to Go to Space

3-scene story with short, optimized prompts:
- Scene 1: 10s - Suiting up
- Scene 2: 15s - Walking to rocket
- Scene 3: 10s - Launch

All scenes use @isaiahdupree character with short phrases for accuracy.
"""

import asyncio
import subprocess
import time
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from automation.sora_full_automation import SoraFullAutomation

# Story scenes with SHORT prompts for better accuracy
STORY_SCENES = [
    {
        "scene": 1,
        "duration": 10,
        "prompt": "putting on a white space suit, determined expression, NASA facility",
        "description": "Suiting up for the mission"
    },
    {
        "scene": 2, 
        "duration": 15,
        "prompt": "walking towards a rocket on launch pad, epic slow motion, sunrise",
        "description": "Walking to the rocket"
    },
    {
        "scene": 3,
        "duration": 10,
        "prompt": "inside rocket cockpit, countdown begins, lights flashing, excited",
        "description": "Launch sequence"
    }
]

OUTPUT_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch/sora_downloads/space_story")


async def generate_all_scenes(automation: SoraFullAutomation, character: str = "isaiahdupree"):
    """Generate all story scenes with @character prefix"""
    
    print("\n" + "="*60)
    print("SORA STORY: PREPARING TO GO TO SPACE")
    print("="*60)
    print(f"Character: @{character}")
    print(f"Scenes: {len(STORY_SCENES)}")
    print("="*60)
    
    generated_count = 0
    
    for scene in STORY_SCENES:
        print(f"\n--- Scene {scene['scene']}: {scene['description']} ---")
        print(f"Duration: {scene['duration']}s")
        print(f"Prompt: @{character} {scene['prompt']}")
        
        # Check queue before generating
        while not automation.can_generate():
            print("Queue full (3 videos), waiting 30s...")
            await asyncio.sleep(30)
        
        # Navigate to explore page
        automation.navigate_to_explore()
        await asyncio.sleep(2)
        
        # Clear any existing prompt
        automation.clear_prompt()
        await asyncio.sleep(0.5)
        
        # Click Characters tab and select character
        automation.click_characters_tab()
        await asyncio.sleep(0.5)
        
        if automation.select_character(character):
            print(f"✅ Selected @{character}")
        else:
            print(f"⚠️ Could not select character, adding manually")
        
        await asyncio.sleep(0.5)
        
        # Add the prompt text (character already added by selection)
        automation.set_prompt(scene['prompt'])
        await asyncio.sleep(0.5)
        
        # Click Create video
        if automation.click_create_video():
            print(f"✅ Scene {scene['scene']} submitted!")
            generated_count += 1
        else:
            print(f"❌ Failed to submit Scene {scene['scene']}")
        
        # Wait between submissions
        await asyncio.sleep(3)
    
    print(f"\n{'='*60}")
    print(f"Submitted {generated_count}/{len(STORY_SCENES)} scenes")
    print("="*60)
    
    return generated_count


async def poll_and_download(automation: SoraFullAutomation, expected_count: int = 3):
    """Poll for completion and download videos"""
    
    print("\n--- Polling for video completion ---")
    print(f"Expected videos: {expected_count}")
    print("This may take 5-10 minutes...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Wait for videos to generate (poll every 30s for up to 15 min)
    start_time = time.time()
    timeout = 900  # 15 minutes
    
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        print(f"Polling... {elapsed}s elapsed")
        
        # Check if videos are ready by going to profile
        videos = automation.get_completed_videos()
        print(f"Videos on profile: {len(videos)}")
        
        # We need to wait until all 3 new videos appear
        # For now, just wait a reasonable time then download
        await asyncio.sleep(30)
        
        # After 5 minutes, start checking more aggressively
        if elapsed > 300:
            break
    
    print("\n--- Downloading videos ---")
    
    # Download the 3 most recent videos (our new ones)
    downloaded = automation.download_recent_videos(count=expected_count)
    
    # Move to story folder with scene names
    final_paths = []
    for i, path in enumerate(downloaded):
        if path and Path(path).exists():
            scene_num = expected_count - i  # Reverse order (newest first)
            new_name = f"scene_{scene_num:02d}.mp4"
            new_path = OUTPUT_DIR / new_name
            
            # Copy instead of move to preserve original
            subprocess.run(['cp', path, str(new_path)])
            final_paths.append(str(new_path))
            print(f"✅ Saved: {new_name}")
    
    return final_paths


def stitch_videos(video_paths: list, output_name: str = "space_story_final.mp4"):
    """Stitch multiple videos together using FFmpeg"""
    
    if not video_paths:
        print("No videos to stitch!")
        return None
    
    print(f"\n--- Stitching {len(video_paths)} videos ---")
    
    # Sort by scene number
    video_paths = sorted(video_paths)
    
    output_path = OUTPUT_DIR / output_name
    
    # Create concat file for FFmpeg
    concat_file = OUTPUT_DIR / "concat_list.txt"
    with open(concat_file, 'w') as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")
    
    # Run FFmpeg concat
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        str(output_path)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and output_path.exists():
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"✅ Created: {output_path} ({size_mb:.1f} MB)")
        return str(output_path)
    else:
        print(f"❌ FFmpeg error: {result.stderr}")
        return None


async def main():
    """Main workflow: Generate -> Poll -> Download -> Stitch"""
    
    automation = SoraFullAutomation()
    
    # Check login
    if not automation.check_login():
        print("❌ Not logged into Sora - please log in first")
        return
    
    print("✅ Logged into Sora")
    
    # Step 1: Generate all scenes
    generated = await generate_all_scenes(automation, character="isaiahdupree")
    
    if generated == 0:
        print("❌ No scenes generated")
        return
    
    # Step 2: Poll and download
    print("\n" + "="*60)
    print("WAITING FOR VIDEOS TO GENERATE")
    print("="*60)
    print("Sora typically takes 2-5 minutes per video.")
    print("Total wait: ~10-15 minutes for 3 videos")
    print("="*60)
    
    downloaded = await poll_and_download(automation, expected_count=generated)
    
    # Step 3: Stitch together
    if len(downloaded) >= 2:
        final = stitch_videos(downloaded)
        
        print("\n" + "="*60)
        print("STORY COMPLETE!")
        print("="*60)
        if final:
            print(f"Final video: {final}")
        print(f"Individual scenes: {OUTPUT_DIR}")
        print("="*60)
    else:
        print(f"\n⚠️ Only {len(downloaded)} videos downloaded, need at least 2 to stitch")


if __name__ == "__main__":
    asyncio.run(main())
