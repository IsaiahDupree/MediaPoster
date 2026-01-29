"""
Sora Pipeline - End-to-end video generation workflow

Orchestrates: Prompt → Generate → Download → Watermark Removal → Stitch → Caption → Schedule

ARCH-002: 3-Part Sora Batch Coordination
- EventBus integration for coordination
- Multi-part video generation with automatic stitching
- Progress events for real-time monitoring
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

# ARCH-002: EventBus integration
try:
    from services.event_bus import EventBus, Topics, Event
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False
    Event = None  # type: ignore
    logger.warning("EventBus not available, running in standalone mode")


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
        watermark_cleaner_path: Optional[Path] = None,
        event_bus: Optional['EventBus'] = None
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

        # ARCH-002: EventBus integration
        if EVENT_BUS_AVAILABLE:
            self.event_bus = event_bus or EventBus.get_instance()
            self._setup_event_subscriptions()
        else:
            self.event_bus = None

    def _setup_event_subscriptions(self) -> None:
        """
        Subscribe to EventBus topics for event-driven orchestration (ARCH-002).

        Listens for:
        - SORA_BATCH_REQUESTED: Triggered by MasterOrchestrator to start video generation
        """
        if not self.event_bus or not EVENT_BUS_AVAILABLE:
            return

        self.event_bus.subscribe(Topics.SORA_BATCH_REQUESTED, self._handle_batch_request)
        logger.info("📫 SoraPipeline subscribed to SORA_BATCH_REQUESTED events")

    async def _handle_batch_request(self, event: 'Event') -> None:
        """
        Handle SORA_BATCH_REQUESTED event from orchestrator (ARCH-002).

        Event payload should contain:
        - pipeline_id: Orchestrator pipeline ID
        - theme: Video theme/topic
        - num_parts: Number of video parts (default 3)
        - character: Optional @character
        - stitch: Whether to stitch parts (default True)
        - remove_watermark: Whether to remove watermarks (default True)
        """
        try:
            payload = event.payload
            pipeline_id = payload.get("pipeline_id")
            theme = payload.get("theme")
            num_parts = payload.get("num_parts", 3)
            character = payload.get("character")
            stitch = payload.get("stitch", True)
            remove_watermark = payload.get("remove_watermark", True)

            logger.info(f"🎬 [ARCH-002] Received batch request for pipeline {pipeline_id}: {theme}")

            # Run multi-part generation with orchestrator integration
            result = await self.generate_multi_part(
                theme=theme,
                num_parts=num_parts,
                character=character,
                auto_stitch=stitch,
                auto_analyze=True,
                remove_watermarks=remove_watermark,
                pipeline_id=pipeline_id
            )

            logger.info(f"✅ [ARCH-002] Batch request completed for pipeline {pipeline_id}: {result.get('status')}")

        except Exception as e:
            logger.error(f"❌ [ARCH-002] Error handling batch request: {e}")

            # Publish failure event
            if self.event_bus and EVENT_BUS_AVAILABLE:
                await self.event_bus.publish(
                    Topics.SORA_BATCH_FAILED,
                    {
                        "pipeline_id": payload.get("pipeline_id"),
                        "theme": payload.get("theme"),
                        "error": str(e)
                    },
                    correlation_id=event.correlation_id,
                    source="sora_pipeline"
                )

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
    
    async def generate_multi_part(
        self,
        theme: str,
        num_parts: int = 3,
        character: Optional[str] = None,
        part_prompts: Optional[List[str]] = None,
        auto_stitch: bool = True,
        auto_analyze: bool = True,
        remove_watermarks: bool = True,
        pipeline_id: Optional[str] = None
    ) -> Dict:
        """
        Generate a multi-part video series (typically 3-part) with coordinated theme.

        This is the core method for creating cohesive multi-part content:
        1. Generate AI prompts for each part if not provided
        2. Queue all parts for generation (respects Sora's 3-concurrent limit)
        3. Download and remove watermarks from completed videos
        4. Stitch all parts into final video
        5. Analyze content for titles/descriptions

        Args:
            theme: Overall theme/topic for the video series
            num_parts: Number of video parts (default 3)
            character: Optional @character for Sora (e.g., "@isaiahdupree")
            part_prompts: Optional pre-defined prompts for each part
            auto_stitch: Whether to stitch parts into one video
            auto_analyze: Whether to analyze content for metadata
            remove_watermarks: Whether to remove Sora watermarks
            pipeline_id: Optional pipeline ID for orchestrator integration (ARCH-002)

        Returns:
            Dict with job status, video paths, and analysis results
        """
        import uuid
        job_id = pipeline_id or str(uuid.uuid4())[:8]
        
        job = {
            "id": job_id,
            "type": "multi_part",
            "theme": theme,
            "num_parts": num_parts,
            "character": character,
            "status": "initializing",
            "started_at": datetime.now().isoformat(),
            "parts": [],
            "steps_completed": []
        }
        self.jobs[job_id] = job

        logger.info(f"🎬 [MultiPart {job_id}] Starting {num_parts}-part video: {theme}")

        # ARCH-002: Emit batch started event
        if self.event_bus and EVENT_BUS_AVAILABLE:
            await self.event_bus.publish(
                Topics.SORA_BATCH_STARTED,
                {
                    "job_id": job_id,
                    "theme": theme,
                    "num_parts": num_parts,
                    "character": character
                },
                correlation_id=job_id,
                source="sora_pipeline"
            )
        
        try:
            # Step 1: Generate prompts if not provided
            if not part_prompts or len(part_prompts) != num_parts:
                logger.info(f"📝 [MultiPart {job_id}] Generating part prompts with AI...")
                part_prompts = await self._generate_part_prompts(theme, num_parts, character)
                job["generated_prompts"] = part_prompts
            
            job["prompts"] = part_prompts
            job["steps_completed"].append("prompts_ready")
            job["status"] = "generating"
            
            # Step 2: Generate each part
            for i, prompt in enumerate(part_prompts):
                part_num = i + 1
                logger.info(f"🎥 [MultiPart {job_id}] Generating part {part_num}/{num_parts}...")
                
                part_result = await self.generate_single(
                    prompt=prompt,
                    character=character,
                    download=True,
                    remove_watermark=remove_watermarks,
                    timeout_minutes=15
                )
                
                job["parts"].append({
                    "part_number": part_num,
                    "prompt": prompt,
                    "result": part_result
                })
                
                if part_result.get("status") != "completed":
                    logger.warning(f"⚠️ [MultiPart {job_id}] Part {part_num} failed: {part_result.get('error')}")
                else:
                    logger.success(f"✅ [MultiPart {job_id}] Part {part_num} complete")
                
                # Brief delay between parts
                if i < num_parts - 1:
                    await asyncio.sleep(3)
            
            job["steps_completed"].append("generation_complete")
            
            # Collect successful video paths
            video_paths = []
            for part in job["parts"]:
                result = part.get("result", {})
                path = result.get("cleaned_video_path") or result.get("video_path")
                if path and result.get("status") == "completed":
                    video_paths.append(Path(path))
            
            job["successful_parts"] = len(video_paths)
            job["failed_parts"] = num_parts - len(video_paths)
            
            # Step 3: Stitch videos if requested and we have multiple parts
            if auto_stitch and len(video_paths) > 1:
                logger.info(f"🔗 [MultiPart {job_id}] Stitching {len(video_paths)} parts...")
                
                output_path = self.output_dir / f"multipart_{job_id}_final.mp4"
                stitched = await self.stitch_videos(video_paths, output_path)
                
                if stitched:
                    job["stitched_video"] = str(stitched)
                    job["steps_completed"].append("stitched")
                    logger.success(f"✅ [MultiPart {job_id}] Stitched to: {stitched}")
                else:
                    logger.warning(f"⚠️ [MultiPart {job_id}] Stitching failed")
            elif len(video_paths) == 1:
                job["stitched_video"] = str(video_paths[0])
            
            # Step 4: Analyze content for metadata
            if auto_analyze and job.get("stitched_video"):
                logger.info(f"🔍 [MultiPart {job_id}] Analyzing content...")
                
                analysis = await self._analyze_video_content(
                    job.get("stitched_video"),
                    theme,
                    part_prompts
                )
                
                if analysis:
                    job["analysis"] = analysis
                    job["steps_completed"].append("analyzed")
                    logger.success(f"✅ [MultiPart {job_id}] Analysis complete")
            
            # Determine final status
            if job["successful_parts"] == num_parts:
                job["status"] = "completed"
            elif job["successful_parts"] > 0:
                job["status"] = "partial"
            else:
                job["status"] = "failed"
            
            job["completed_at"] = datetime.now().isoformat()

            # ARCH-002: Emit batch completed event
            if self.event_bus and EVENT_BUS_AVAILABLE:
                await self.event_bus.publish(
                    Topics.SORA_BATCH_COMPLETED,
                    {
                        "job_id": job_id,
                        "pipeline_id": pipeline_id,  # ARCH-002: Include pipeline_id for orchestrator
                        "theme": theme,
                        "num_parts": num_parts,
                        "successful_parts": job["successful_parts"],
                        "failed_parts": job["failed_parts"],
                        "video_paths": [str(p) for p in video_paths],
                        "stitched_video": job.get("stitched_video"),
                        "analysis": job.get("analysis"),
                        "prompts": part_prompts,
                        "status": job["status"]
                    },
                    correlation_id=job_id,
                    source="sora_pipeline"
                )

            logger.info(f"🏁 [MultiPart {job_id}] Done: {job['successful_parts']}/{num_parts} parts, status={job['status']}")
            return job
            
        except Exception as e:
            logger.error(f"❌ [MultiPart {job_id}] Error: {e}")
            job["status"] = "failed"
            job["error"] = str(e)

            # ARCH-002: Emit batch failed event
            if self.event_bus and EVENT_BUS_AVAILABLE:
                await self.event_bus.publish(
                    Topics.SORA_BATCH_FAILED,
                    {
                        "job_id": job_id,
                        "pipeline_id": pipeline_id,
                        "theme": theme,
                        "error": str(e)
                    },
                    correlation_id=job_id,
                    source="sora_pipeline"
                )

            return job
    
    async def _generate_part_prompts(
        self,
        theme: str,
        num_parts: int,
        character: Optional[str] = None
    ) -> List[str]:
        """
        Generate AI prompts for each part of a multi-part video.
        
        Uses OpenAI to create cohesive, engaging prompts that flow together.
        """
        try:
            from openai import OpenAI
            import os
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            character_instruction = ""
            if character:
                character_instruction = f"\nInclude '{character}' as the main character in each prompt."
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at creating Sora AI video prompts. 
Generate prompts that are visually descriptive, dynamic, and optimized for short-form video content.
Each prompt should be 1-2 sentences, focusing on action and visual elements."""
                    },
                    {
                        "role": "user",
                        "content": f"""Create {num_parts} connected video prompts for a {num_parts}-part series about: {theme}

Requirements:
- Part 1: Hook/attention-grabber (first 5 seconds vibe)
- Part 2: Main content/demonstration
- Part 3: Payoff/conclusion with call-to-action energy
{character_instruction}

Return ONLY the prompts, one per line, no numbering or labels."""
                    }
                ],
                temperature=0.8
            )
            
            prompts_text = response.choices[0].message.content.strip()
            prompts = [p.strip() for p in prompts_text.split("\n") if p.strip()]
            
            # Ensure we have the right number
            if len(prompts) < num_parts:
                # Pad with generic prompts
                while len(prompts) < num_parts:
                    prompts.append(f"Continuation of {theme} with dynamic visuals")
            
            return prompts[:num_parts]
            
        except Exception as e:
            logger.warning(f"AI prompt generation failed: {e}, using fallback")
            # Fallback prompts
            return [
                f"Opening scene: {theme} - dramatic reveal, high energy",
                f"Main content: {theme} - detailed demonstration, engaging visuals",
                f"Conclusion: {theme} - powerful ending, call to action energy"
            ][:num_parts]
    
    async def _analyze_video_content(
        self,
        video_path: str,
        theme: str,
        prompts: List[str]
    ) -> Optional[Dict]:
        """
        Analyze video content to generate titles, descriptions, and hashtags.
        """
        try:
            from openai import OpenAI
            import os
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            prompt_context = "\n".join([f"Part {i+1}: {p}" for i, p in enumerate(prompts)])
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert social media content strategist.
Generate optimized titles, descriptions, and hashtags for viral short-form video content.
Return JSON format only."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this video content and generate metadata:

Theme: {theme}
Video Parts:
{prompt_context}

Return JSON with:
{{
    "title_tiktok": "catchy title under 100 chars",
    "title_instagram": "engaging title for reels",
    "title_youtube": "SEO-optimized title under 100 chars",
    "description": "engaging description 150-200 chars with CTA",
    "hashtags": ["list", "of", "10", "relevant", "hashtags"],
    "hook": "the first line hook for caption",
    "cta": "call to action text"
}}"""
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.warning(f"Content analysis failed: {e}")
            return {
                "title_tiktok": theme[:100],
                "title_instagram": theme[:100],
                "title_youtube": theme[:100],
                "description": f"Check out this video about {theme}!",
                "hashtags": ["viral", "fyp", "trending"],
                "hook": theme,
                "cta": "Follow for more!"
            }
    
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
