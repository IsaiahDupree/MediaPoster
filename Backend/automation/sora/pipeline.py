"""
Sora Pipeline - End-to-end video generation workflow

Orchestrates: Prompt → Generate → Download → Watermark Removal → Stitch → Caption → Schedule
"""
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from .sora_controller import SoraController
from .generation_monitor import GenerationMonitor, GenerationQueue
from .video_downloader import VideoDownloader


class SoraPipeline:
    """
    Complete pipeline for Sora video generation and post-processing.
    
    Workflow:
    1. Generate videos from prompts via Safari automation
    2. Download completed videos
    3. Remove watermarks using SoraWatermarkCleaner
    4. Stitch multiple videos together
    5. Add captions
    6. Schedule to social media
    """
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        watermark_cleaner_path: Optional[Path] = None
    ):
        self.controller = SoraController()
        self.monitor = GenerationMonitor(self.controller)
        self.downloader = VideoDownloader(self.controller, output_dir)
        
        # Paths
        self.output_dir = output_dir or Path("output/sora_pipeline")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.watermark_cleaner_path = watermark_cleaner_path or Path(
            "Backend/SoraWatermarkCleaner"
        )
        
        # Job tracking
        self.jobs: Dict[str, Dict] = {}
    
    async def generate_single(
        self,
        prompt: str,
        character: Optional[str] = None,
        timeout_minutes: int = 10,
        download: bool = True,
        remove_watermark: bool = True
    ) -> Dict:
        """
        Generate a single video from prompt.
        
        Args:
            prompt: Video generation prompt
            character: Optional @ character (e.g., "@isaiahdupree")
            timeout_minutes: Max generation wait time
            download: Whether to download the video
            remove_watermark: Whether to remove watermark after download
            
        Returns:
            Job result dict
        """
        import uuid
        job_id = str(uuid.uuid4())[:8]
        
        job = {
            "id": job_id,
            "prompt": prompt,
            "character": character,
            "status": "starting",
            "started_at": datetime.now().isoformat(),
            "steps_completed": []
        }
        self.jobs[job_id] = job
        
        try:
            # Step 1: Launch Sora
            logger.info(f"🚀 [Job {job_id}] Starting pipeline...")
            if not await self.controller.launch_sora():
                job["status"] = "failed"
                job["error"] = "Failed to launch Sora"
                return job
            
            await asyncio.sleep(2)
            job["steps_completed"].append("launch")
            
            # Step 2: Check login
            login_status = await self.controller.check_login_status()
            if not login_status.get("logged_in"):
                logger.warning("⚠️ Not logged in to Sora - manual login may be required")
                job["needs_login"] = True
            
            # Step 3: Submit prompt
            logger.info(f"📝 [Job {job_id}] Submitting prompt...")
            if not await self.controller.submit_prompt(prompt, character):
                job["status"] = "failed"
                job["error"] = "Failed to submit prompt"
                return job
            
            job["steps_completed"].append("prompt_submitted")
            
            # Step 4: Wait for generation
            logger.info(f"⏳ [Job {job_id}] Waiting for generation...")
            result = await self.monitor.start_monitoring(job_id, timeout_minutes)
            
            if result.get("status") != "completed":
                job["status"] = result.get("status", "failed")
                job["error"] = result.get("error")
                return job
            
            job["steps_completed"].append("generation_complete")
            job["generation_time"] = result.get("elapsed_seconds")
            
            # Step 5: Download video
            if download:
                logger.info(f"📥 [Job {job_id}] Downloading video...")
                video_path = await self.downloader.download_current_video(f"sora_{job_id}")
                
                if not video_path:
                    job["status"] = "partial"
                    job["error"] = "Failed to download video"
                    return job
                
                job["video_path"] = str(video_path)
                job["steps_completed"].append("downloaded")
                
                # Step 6: Remove watermark
                if remove_watermark and video_path:
                    logger.info(f"🧹 [Job {job_id}] Removing watermark...")
                    cleaned_path = await self.remove_watermark(video_path)
                    
                    if cleaned_path:
                        job["cleaned_video_path"] = str(cleaned_path)
                        job["steps_completed"].append("watermark_removed")
                    else:
                        logger.warning("⚠️ Watermark removal failed, using original")
            
            job["status"] = "completed"
            job["completed_at"] = datetime.now().isoformat()
            
            logger.success(f"✅ [Job {job_id}] Pipeline complete!")
            return job
            
        except Exception as e:
            logger.error(f"❌ [Job {job_id}] Pipeline error: {e}")
            job["status"] = "failed"
            job["error"] = str(e)
            return job
    
    async def generate_batch(
        self,
        prompts: List[Dict],
        stitch_output: bool = False,
        add_captions: bool = False,
        schedule_to: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate multiple videos and optionally stitch them together.
        
        Args:
            prompts: List of {"prompt": str, "character": str} dicts
            stitch_output: Whether to stitch all videos into one
            add_captions: Whether to add captions to final video
            schedule_to: List of platforms to schedule to
            
        Returns:
            Batch result dict
        """
        import uuid
        batch_id = str(uuid.uuid4())[:8]
        
        batch = {
            "id": batch_id,
            "status": "processing",
            "started_at": datetime.now().isoformat(),
            "total_prompts": len(prompts),
            "completed": 0,
            "failed": 0,
            "jobs": []
        }
        
        logger.info(f"🎬 [Batch {batch_id}] Starting batch of {len(prompts)} videos...")
        
        # Generate each video
        for i, prompt_config in enumerate(prompts):
            logger.info(f"📹 [Batch {batch_id}] Processing {i+1}/{len(prompts)}...")
            
            result = await self.generate_single(
                prompt=prompt_config.get("prompt", ""),
                character=prompt_config.get("character"),
                download=True,
                remove_watermark=True
            )
            
            batch["jobs"].append(result)
            
            if result.get("status") == "completed":
                batch["completed"] += 1
            else:
                batch["failed"] += 1
            
            # Delay between generations
            if i < len(prompts) - 1:
                await asyncio.sleep(5)
        
        # Collect video paths
        video_paths = [
            Path(j.get("cleaned_video_path") or j.get("video_path"))
            for j in batch["jobs"]
            if j.get("status") == "completed" and (j.get("cleaned_video_path") or j.get("video_path"))
        ]
        
        # Stitch videos if requested
        if stitch_output and len(video_paths) > 1:
            logger.info(f"🔗 [Batch {batch_id}] Stitching {len(video_paths)} videos...")
            output_path = self.output_dir / f"stitched_{batch_id}.mp4"
            
            stitched = await self.stitch_videos(video_paths, output_path)
            if stitched:
                batch["stitched_video"] = str(stitched)
                
                # Add captions if requested
                if add_captions:
                    logger.info(f"📝 [Batch {batch_id}] Adding captions...")
                    captioned = await self.add_captions(stitched)
                    if captioned:
                        batch["captioned_video"] = str(captioned)
        
        # Schedule if platforms specified
        if schedule_to and (batch.get("captioned_video") or batch.get("stitched_video") or video_paths):
            final_video = batch.get("captioned_video") or batch.get("stitched_video") or str(video_paths[0])
            logger.info(f"📅 [Batch {batch_id}] Scheduling to {schedule_to}...")
            # TODO: Integrate with Blotato scheduling
            batch["scheduled_to"] = schedule_to
            batch["scheduled_video"] = final_video
        
        batch["status"] = "completed"
        batch["completed_at"] = datetime.now().isoformat()
        
        logger.success(f"✅ [Batch {batch_id}] Complete: {batch['completed']}/{batch['total_prompts']} succeeded")
        return batch
    
    async def remove_watermark(self, video_path: Path) -> Optional[Path]:
        """
        Remove watermark from video using SoraWatermarkCleaner.
        
        Args:
            video_path: Path to input video
            
        Returns:
            Path to cleaned video or None
        """
        output_path = video_path.parent / f"{video_path.stem}_clean{video_path.suffix}"
        
        # Check if SoraWatermarkCleaner is available
        cleaner_script = self.watermark_cleaner_path / "cli.py"
        if not cleaner_script.exists():
            # Try relative path from Backend
            cleaner_script = Path(__file__).parent.parent.parent / "SoraWatermarkCleaner" / "cli.py"
        
        if not cleaner_script.exists():
            logger.error(f"SoraWatermarkCleaner not found at {cleaner_script}")
            return None
        
        try:
            # Run the cleaner
            result = subprocess.run(
                [
                    sys.executable,
                    str(cleaner_script),
                    "-i", str(video_path),
                    "-o", str(output_path.parent),
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(cleaner_script.parent)
            )
            
            if result.returncode != 0:
                logger.error(f"Watermark removal failed: {result.stderr}")
                return None
            
            # Find the output file
            if output_path.exists():
                logger.success(f"✅ Watermark removed: {output_path}")
                return output_path
            
            # Check for alternative output naming
            for f in output_path.parent.iterdir():
                if video_path.stem in f.stem and "clean" in f.stem.lower():
                    logger.success(f"✅ Watermark removed: {f}")
                    return f
            
            logger.warning("Watermark removal completed but output not found")
            return None
            
        except subprocess.TimeoutExpired:
            logger.error("Watermark removal timed out")
            return None
        except Exception as e:
            logger.error(f"Watermark removal error: {e}")
            return None
    
    async def stitch_videos(
        self,
        video_paths: List[Path],
        output_path: Path,
        transition: str = "fade"
    ) -> Optional[Path]:
        """
        Stitch multiple videos together using FFmpeg.
        
        Args:
            video_paths: List of video paths to stitch
            output_path: Output file path
            transition: Transition type (fade, none)
            
        Returns:
            Path to stitched video or None
        """
        if len(video_paths) < 2:
            logger.warning("Need at least 2 videos to stitch")
            return video_paths[0] if video_paths else None
        
        try:
            # Create concat file
            concat_file = output_path.parent / f"concat_{output_path.stem}.txt"
            with open(concat_file, "w") as f:
                for video in video_paths:
                    f.write(f"file '{video.absolute()}'\n")
            
            # Run FFmpeg concat
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Clean up concat file
            concat_file.unlink()
            
            if result.returncode != 0:
                logger.error(f"Video stitching failed: {result.stderr}")
                return None
            
            logger.success(f"✅ Stitched {len(video_paths)} videos: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Video stitching error: {e}")
            return None
    
    async def add_captions(
        self,
        video_path: Path,
        caption_style: str = "bottom"
    ) -> Optional[Path]:
        """
        Add captions to video using Whisper transcription.
        
        Args:
            video_path: Input video path
            caption_style: Caption position/style
            
        Returns:
            Path to captioned video or None
        """
        output_path = video_path.parent / f"{video_path.stem}_captioned{video_path.suffix}"
        
        try:
            # First, extract audio and transcribe with Whisper
            # This requires whisper to be installed
            
            # For now, log that this step needs implementation
            logger.info("📝 Caption generation requires OpenAI Whisper integration")
            logger.info("   Install: pip install openai-whisper")
            
            # TODO: Implement Whisper transcription
            # TODO: Generate SRT file
            # TODO: Burn captions into video with FFmpeg
            
            return None
            
        except Exception as e:
            logger.error(f"Caption generation error: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a specific job."""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs."""
        return list(self.jobs.values())


async def run_interactive_pipeline():
    """Run an interactive pipeline session for testing."""
    pipeline = SoraPipeline()
    
    print("\n" + "="*60)
    print("🎬 SORA PIPELINE - Interactive Mode")
    print("="*60)
    
    # Launch Sora first
    print("\n1. Launching Sora in Safari...")
    await pipeline.controller.launch_sora()
    await asyncio.sleep(3)
    
    # Check login
    print("\n2. Checking login status...")
    status = await pipeline.controller.check_login_status()
    print(f"   Logged in: {status.get('logged_in', False)}")
    
    if not status.get('logged_in'):
        print("\n⚠️  Please log in to Sora manually, then press Enter to continue...")
        input()
    
    # Get page state
    print("\n3. Analyzing page...")
    state = await pipeline.controller.get_page_state()
    print(f"   URL: {state.get('url')}")
    print(f"   Has prompt input: {state.get('has_prompt_input')}")
    
    print("\n4. Ready for prompts!")
    print("   Enter a prompt to generate a video, or 'quit' to exit.")
    
    while True:
        prompt = input("\n📝 Enter prompt: ").strip()
        
        if prompt.lower() in ['quit', 'exit', 'q']:
            break
        
        if not prompt:
            continue
        
        character = input("👤 Character (e.g., @isaiahdupree, or press Enter to skip): ").strip() or None
        
        print(f"\n🎬 Starting generation...")
        result = await pipeline.generate_single(
            prompt=prompt,
            character=character,
            timeout_minutes=10,
            download=True,
            remove_watermark=True
        )
        
        print(f"\n📊 Result: {result.get('status')}")
        if result.get('video_path'):
            print(f"   Video: {result.get('video_path')}")
        if result.get('cleaned_video_path'):
            print(f"   Cleaned: {result.get('cleaned_video_path')}")
        if result.get('error'):
            print(f"   Error: {result.get('error')}")
    
    print("\n👋 Pipeline session ended.")


if __name__ == "__main__":
    asyncio.run(run_interactive_pipeline())
