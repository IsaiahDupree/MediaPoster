#!/usr/bin/env python3
"""
Sora Full Pipeline - Complete Video Generation Automation
==========================================================

Full end-to-end automation:
1. Enter prompt with @isaiahdupree character
2. Select video options (duration, aspect ratio)
3. Submit for generation
4. Poll /drafts for completion (count-based detection)
5. Download new videos automatically

Usage:
    python scripts/sora_full_pipeline.py "your prompt here"
    python scripts/sora_full_pipeline.py "prompt" --duration 25 --aspect Landscape
    python scripts/sora_full_pipeline.py "prompt1" "prompt2" "prompt3"  # Batch

Success Criteria:
    ✅ Enter prompt text
    ✅ Select @isaiahdupree character
    ✅ Select duration (10s, 15s, 25s)
    ✅ Select aspect ratio (Portrait/Landscape)
    ✅ Click "Create video"
    ✅ Poll /drafts for new videos
    ✅ Detect completion (count increases)
    ✅ Download to local machine
    ✅ Handle queue limit (max 3)
"""

import sys
import time
import asyncio
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from loguru import logger

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.sora_full_automation import SoraFullAutomation


# Constants
DEFAULT_CHARACTER = "isaiahdupree"
DEFAULT_DURATION = 15
DEFAULT_ASPECT = "Portrait"
MAX_QUEUE_SIZE = 3
POLL_INTERVAL = 30  # seconds
DEFAULT_TIMEOUT = 600  # 10 minutes


@dataclass
class GenerationResult:
    """Result of a video generation."""
    success: bool
    prompt: str
    character: str
    duration: int
    aspect_ratio: str
    video_path: Optional[str] = None
    generation_time: int = 0  # seconds
    file_size_mb: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "prompt": self.prompt[:50] + "..." if len(self.prompt) > 50 else self.prompt,
            "character": self.character,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
            "video_path": self.video_path,
            "generation_time": self.generation_time,
            "file_size_mb": self.file_size_mb,
            "error": self.error
        }


class SoraFullPipeline:
    """
    Full Sora video generation pipeline.
    
    Handles the complete flow from prompt to downloaded video.
    """
    
    def __init__(self):
        self.sora = SoraFullAutomation()
        self.results: List[GenerationResult] = []
        
    def _log(self, msg: str, level: str = "info"):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == "info":
            logger.info(f"[{timestamp}] {msg}")
        elif level == "error":
            logger.error(f"[{timestamp}] {msg}")
        elif level == "success":
            logger.success(f"[{timestamp}] {msg}")
        print(f"[{timestamp}] {msg}")
    
    def check_login(self) -> bool:
        """Check if logged into Sora."""
        self._log("Checking Sora login status...")
        self.sora.navigate_to_explore()
        time.sleep(3)
        logged_in = self.sora.check_login()
        if logged_in:
            self._log("✅ Logged into Sora")
        else:
            self._log("❌ Not logged into Sora - please log in manually", "error")
        return logged_in
    
    def get_drafts_count(self) -> int:
        """Get current number of videos in /drafts."""
        videos = self.sora.get_completed_videos(scroll_count=1)
        return len(videos)
    
    def enter_prompt(self, prompt: str) -> bool:
        """Enter prompt text into textarea."""
        self._log(f"Entering prompt: {prompt[:40]}...")
        
        # Clear existing prompt first
        self.sora.clear_prompt()
        time.sleep(0.3)
        
        # Set new prompt
        success = self.sora.set_prompt(prompt)
        if success:
            self._log("✅ Prompt entered")
        else:
            self._log("❌ Failed to enter prompt", "error")
        return success
    
    def select_character(self, character: str) -> bool:
        """Select character (e.g., @isaiahdupree)."""
        self._log(f"Selecting character: @{character}...")
        
        success = self.sora.select_character(character)
        if success:
            self._log(f"✅ Selected @{character}")
        else:
            self._log(f"⚠️ Character @{character} may not be available", "error")
        return success
    
    def set_duration(self, duration: int) -> bool:
        """Set video duration (10, 15, or 25 seconds)."""
        self._log(f"Setting duration: {duration}s...")
        
        success = self.sora.set_duration(duration)
        if success:
            self._log(f"✅ Duration set to {duration}s")
        else:
            self._log(f"⚠️ Could not set duration (using default)")
        return success
    
    def set_aspect_ratio(self, aspect: str) -> bool:
        """Set aspect ratio (Portrait or Landscape)."""
        self._log(f"Setting aspect ratio: {aspect}...")
        
        success = self.sora.set_aspect_ratio(aspect)
        if success:
            self._log(f"✅ Aspect ratio set to {aspect}")
        else:
            self._log(f"⚠️ Could not set aspect ratio (using default)")
        return success
    
    def click_create(self) -> bool:
        """Click the Create video button."""
        self._log("Clicking 'Create video'...")
        
        success = self.sora.click_create_video()
        if success:
            self._log("✅ Video generation started!")
        else:
            self._log("❌ Failed to start generation", "error")
        return success
    
    def wait_for_queue_slot(self) -> bool:
        """Wait until there's a slot in the queue (max 3)."""
        while True:
            if self.sora.can_generate():
                return True
            self._log(f"Queue full ({MAX_QUEUE_SIZE}/{MAX_QUEUE_SIZE}), waiting 30s...")
            time.sleep(30)
    
    def poll_for_completion(self, initial_count: int, timeout: int = DEFAULT_TIMEOUT) -> Optional[Dict]:
        """
        Poll /drafts until a new video appears.
        
        Args:
            initial_count: Number of videos before generation started
            timeout: Max seconds to wait
            
        Returns:
            New video dict or None if timeout
        """
        self._log(f"Polling for completion (initial count: {initial_count})...")
        
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < timeout:
            poll_count += 1
            elapsed = int(time.time() - start_time)
            
            # Navigate to drafts and get count
            videos = self.sora.get_completed_videos(scroll_count=1)
            current_count = len(videos)
            
            self._log(f"Poll #{poll_count}: {current_count} videos ({elapsed}s elapsed)")
            
            if current_count > initial_count:
                self._log("✅ New video detected!")
                # Return the newest video (first in list)
                return videos[0] if videos else None
            
            time.sleep(POLL_INTERVAL)
        
        self._log(f"⚠️ Timeout after {timeout}s", "error")
        return None
    
    def download_video(self, video: Dict) -> Optional[str]:
        """Download a video from its URL."""
        video_src = video.get('video_src')
        if not video_src:
            self._log("❌ No video URL found", "error")
            return None
        
        self._log("Downloading video...")
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sora_{DEFAULT_CHARACTER}_{timestamp}.mp4"
        local_path = self.sora.DOWNLOAD_DIR / filename
        
        try:
            result = subprocess.run(
                ['curl', '-L', '-o', str(local_path), video_src],
                capture_output=True,
                timeout=180
            )
            
            if local_path.exists() and local_path.stat().st_size > 10000:
                size_mb = local_path.stat().st_size / 1024 / 1024
                self._log(f"✅ Downloaded: {filename} ({size_mb:.1f} MB)", "success")
                return str(local_path)
            else:
                self._log("❌ Download failed or file too small", "error")
        except Exception as e:
            self._log(f"❌ Download error: {e}", "error")
        
        return None
    
    async def generate_video(
        self,
        prompt: str,
        character: str = DEFAULT_CHARACTER,
        duration: int = DEFAULT_DURATION,
        aspect_ratio: str = DEFAULT_ASPECT,
        auto_download: bool = True,
        timeout: int = DEFAULT_TIMEOUT
    ) -> GenerationResult:
        """
        Generate a single video - full pipeline.
        
        Args:
            prompt: Video description
            character: Character to use (default: isaiahdupree)
            duration: Video length in seconds (10, 15, 25)
            aspect_ratio: Portrait or Landscape
            auto_download: Download when complete
            timeout: Max wait time in seconds
            
        Returns:
            GenerationResult with video path and metadata
        """
        start_time = time.time()
        
        result = GenerationResult(
            success=False,
            prompt=prompt,
            character=character,
            duration=duration,
            aspect_ratio=aspect_ratio
        )
        
        print("\n" + "="*60)
        print("SORA FULL PIPELINE - VIDEO GENERATION")
        print("="*60)
        print(f"Prompt: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
        print(f"Character: @{character}")
        print(f"Duration: {duration}s")
        print(f"Aspect: {aspect_ratio}")
        print("="*60 + "\n")
        
        # Step 1: Check login
        if not self.check_login():
            result.error = "Not logged in"
            return result
        
        # Step 2: Check queue
        self._log("Checking queue...")
        self.wait_for_queue_slot()
        
        # Step 3: Get initial drafts count BEFORE submitting
        self._log("Getting initial drafts count...")
        initial_count = self.get_drafts_count()
        self._log(f"Initial drafts count: {initial_count}")
        
        # Step 4: Navigate to explore page
        self._log("Navigating to explore page...")
        self.sora.navigate_to_explore()
        time.sleep(2)
        
        # Step 5: Select character
        self.select_character(character)
        time.sleep(0.5)
        
        # Step 6: Enter prompt
        if not self.enter_prompt(prompt):
            result.error = "Failed to enter prompt"
            return result
        time.sleep(0.5)
        
        # Step 7: Set options (duration and aspect - may not always work)
        self.set_duration(duration)
        time.sleep(0.3)
        self.set_aspect_ratio(aspect_ratio)
        time.sleep(0.3)
        
        # Step 8: Click Create
        if not self.click_create():
            result.error = "Failed to start generation"
            return result
        
        # Step 9: Poll for completion
        new_video = self.poll_for_completion(initial_count, timeout)
        
        if not new_video:
            result.error = "Timeout waiting for video"
            result.generation_time = int(time.time() - start_time)
            return result
        
        # Step 10: Download
        if auto_download:
            video_path = self.download_video(new_video)
            if video_path:
                result.video_path = video_path
                result.file_size_mb = Path(video_path).stat().st_size / 1024 / 1024
        
        result.success = True
        result.generation_time = int(time.time() - start_time)
        
        print("\n" + "="*60)
        print("✅ VIDEO GENERATION COMPLETE")
        print(f"Time: {result.generation_time}s")
        if result.video_path:
            print(f"File: {result.video_path}")
            print(f"Size: {result.file_size_mb:.1f} MB")
        print("="*60 + "\n")
        
        self.results.append(result)
        return result
    
    async def batch_generate(
        self,
        prompts: List[str],
        character: str = DEFAULT_CHARACTER,
        duration: int = DEFAULT_DURATION,
        aspect_ratio: str = DEFAULT_ASPECT
    ) -> List[GenerationResult]:
        """
        Generate multiple videos respecting queue limit.
        
        Args:
            prompts: List of prompts
            character, duration, aspect_ratio: Applied to all
            
        Returns:
            List of GenerationResult
        """
        self._log(f"Starting batch generation of {len(prompts)} videos...")
        
        results = []
        for i, prompt in enumerate(prompts):
            self._log(f"\n--- Video {i+1}/{len(prompts)} ---")
            result = await self.generate_video(
                prompt=prompt,
                character=character,
                duration=duration,
                aspect_ratio=aspect_ratio
            )
            results.append(result)
            
            # Small delay between submissions
            if i < len(prompts) - 1:
                time.sleep(5)
        
        # Summary
        success_count = sum(1 for r in results if r.success)
        self._log(f"\nBatch complete: {success_count}/{len(prompts)} succeeded")
        
        return results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sora Full Pipeline - Video Generation")
    parser.add_argument("prompts", nargs="+", help="Video prompt(s)")
    parser.add_argument("--character", default=DEFAULT_CHARACTER, help="Character name")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, choices=[10, 15, 25])
    parser.add_argument("--aspect", default=DEFAULT_ASPECT, choices=["Portrait", "Landscape"])
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds")
    parser.add_argument("--no-download", action="store_true", help="Skip auto-download")
    
    args = parser.parse_args()
    
    pipeline = SoraFullPipeline()
    
    if len(args.prompts) == 1:
        # Single video
        result = await pipeline.generate_video(
            prompt=args.prompts[0],
            character=args.character,
            duration=args.duration,
            aspect_ratio=args.aspect,
            auto_download=not args.no_download,
            timeout=args.timeout
        )
        
        if result.success:
            print(f"\n🎉 Success! Video saved to: {result.video_path}")
            sys.exit(0)
        else:
            print(f"\n❌ Failed: {result.error}")
            sys.exit(1)
    else:
        # Batch
        results = await pipeline.batch_generate(
            prompts=args.prompts,
            character=args.character,
            duration=args.duration,
            aspect_ratio=args.aspect
        )
        
        success_count = sum(1 for r in results if r.success)
        print(f"\n🎉 Batch complete: {success_count}/{len(results)} succeeded")
        sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
