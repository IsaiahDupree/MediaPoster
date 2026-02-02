"""
Sora Pipeline (ARCH-002)
========================
Coordinates multi-part AI video generation via Sora, with automatic
stitching and content analysis.

Provides:
    - generate_multi_part(): Generate coordinated N-part video series
    - generate_batch(): Generate a batch of independent videos
    - generate_prompts(): AI-generate part prompts from a theme

Integrates with:
    - VideoStitcher: Concatenate generated clips
    - ContentAnalyzer: Analyze final video for publishing metadata
    - EventBus: Progress events for orchestrator tracking

Usage:
    pipeline = SoraPipeline()
    result = await pipeline.generate_multi_part(
        theme="AI automation revolutionizing content creation",
        num_parts=3,
        character="@isaiahdupree",
        auto_stitch=True,
        auto_analyze=True
    )
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Output directories
SORA_OUTPUT_DIR = Path(
    os.getenv(
        "SORA_OUTPUT_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "sora_downloads"),
    )
)
SORA_PROCESSED_DIR = Path(
    os.getenv(
        "SORA_PROCESSED_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "sora_processed"),
    )
)


class SoraPipeline:
    """
    Sora multi-part video pipeline (ARCH-002).

    Coordinates generation of 1-5 part video series with automatic
    stitching and AI content analysis.
    """

    def __init__(self):
        # Ensure output dirs exist
        SORA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        SORA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

        # Lazy-loaded dependencies
        self._stitcher = None
        self._analyzer = None
        self._prompt_client = None

        logger.info("SoraPipeline initialized")

    # ------------------------------------------------------------------
    # Properties (lazy-loaded)
    # ------------------------------------------------------------------

    @property
    def stitcher(self):
        if self._stitcher is None:
            from services.ai_video_pipeline.stitcher import VideoStitcher

            self._stitcher = VideoStitcher(output_dir=str(SORA_PROCESSED_DIR))
        return self._stitcher

    @property
    def analyzer(self):
        if self._analyzer is None:
            from services.content_analyzer import ContentAnalyzer

            self._analyzer = ContentAnalyzer()
        return self._analyzer

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_multi_part(
        self,
        theme: str,
        num_parts: int = 3,
        character: Optional[str] = None,
        part_prompts: Optional[List[str]] = None,
        auto_stitch: bool = True,
        auto_analyze: bool = True,
        remove_watermarks: bool = True,
        pipeline_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a coordinated multi-part video series.

        This is the primary method called by MasterOrchestrator via SoraWorker
        for ARCH-002 batch coordination.

        Args:
            theme: Overall theme/topic for the video series.
            num_parts: Number of video parts to generate (1-5).
            character: Sora @character reference (e.g. "@isaiahdupree").
            part_prompts: Pre-written prompts per part. If None, AI-generates them.
            auto_stitch: Whether to stitch parts into a single video.
            auto_analyze: Whether to run content analysis on the final video.
            remove_watermarks: Whether to remove Sora watermarks.
            pipeline_id: Upstream pipeline ID for correlation.

        Returns:
            Dict with keys:
                id, status, theme, num_parts, parts, prompts,
                stitched_video, analysis, total_generation_time
        """
        job_id = pipeline_id or f"sora-batch-{uuid4().hex[:8]}"
        start_time = time.time()

        logger.info(
            f"[{job_id}] Starting {num_parts}-part generation: '{theme}'"
        )

        # Step 1: Generate or validate prompts
        if part_prompts and len(part_prompts) >= num_parts:
            prompts = part_prompts[:num_parts]
        else:
            prompts = await self._generate_part_prompts(
                theme, num_parts, character
            )

        # Step 2: Generate each part
        parts: List[Dict[str, Any]] = []
        successful_count = 0
        failed_count = 0

        for i, prompt in enumerate(prompts):
            part_num = i + 1
            logger.info(
                f"[{job_id}] Generating part {part_num}/{num_parts}..."
            )

            part_result = await self._generate_single_part(
                prompt=prompt,
                part_num=part_num,
                job_id=job_id,
                character=character,
                remove_watermark=remove_watermarks,
            )

            parts.append(part_result)

            if part_result["status"] == "completed":
                successful_count += 1
                logger.info(
                    f"[{job_id}] Part {part_num} completed: "
                    f"{part_result.get('video_path', 'no path')}"
                )
            else:
                failed_count += 1
                logger.warning(
                    f"[{job_id}] Part {part_num} failed: "
                    f"{part_result.get('error', 'unknown')}"
                )

        # Step 3: Stitch parts together
        stitched_video = None
        if auto_stitch and successful_count > 0:
            clip_paths = [
                p["video_path"]
                for p in parts
                if p["status"] == "completed" and p.get("video_path")
            ]
            if len(clip_paths) > 1:
                stitched_video = await self._stitch_parts(
                    clip_paths, job_id, theme
                )
            elif len(clip_paths) == 1:
                stitched_video = clip_paths[0]

        # Step 4: Content analysis
        analysis = None
        if auto_analyze and stitched_video:
            analysis = await self._analyze_content(
                stitched_video, theme, prompts
            )

        total_time = time.time() - start_time

        result = {
            "id": job_id,
            "status": "completed" if successful_count > 0 else "failed",
            "theme": theme,
            "num_parts": num_parts,
            "successful_parts": successful_count,
            "failed_parts": failed_count,
            "parts": parts,
            "prompts": prompts,
            "stitched_video": stitched_video,
            "video_path": stitched_video,
            "analysis": analysis,
            "total_generation_time": round(total_time, 2),
        }

        logger.info(
            f"[{job_id}] Multi-part generation complete: "
            f"{successful_count}/{num_parts} parts, "
            f"{total_time:.1f}s total"
        )

        return result

    async def generate_batch(
        self,
        prompts: List[Dict[str, str]],
        stitch_output: bool = False,
        add_captions: bool = False,
        schedule_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a batch of independent videos.

        Args:
            prompts: List of dicts with "prompt" and optional "character" keys.
            stitch_output: Whether to stitch all outputs into one video.
            add_captions: Whether to add captions overlay.
            schedule_to: Platform to schedule to after generation.

        Returns:
            Batch result with per-prompt status.
        """
        batch_id = f"sora-batch-{uuid4().hex[:8]}"
        start_time = time.time()

        logger.info(f"[{batch_id}] Starting batch of {len(prompts)} videos")

        jobs = []
        completed = 0
        failed = 0

        for i, prompt_config in enumerate(prompts):
            prompt_text = prompt_config.get("prompt", "")
            character = prompt_config.get("character")

            result = await self._generate_single_part(
                prompt=prompt_text,
                part_num=i + 1,
                job_id=batch_id,
                character=character,
                remove_watermark=True,
            )

            jobs.append(result)

            if result["status"] == "completed":
                completed += 1
            else:
                failed += 1

        # Stitch if requested
        stitched_video = None
        if stitch_output and completed > 1:
            clip_paths = [
                j["video_path"]
                for j in jobs
                if j["status"] == "completed" and j.get("video_path")
            ]
            stitched_video = await self._stitch_parts(
                clip_paths, batch_id, "batch"
            )

        total_time = time.time() - start_time

        return {
            "id": batch_id,
            "status": "completed" if completed > 0 else "failed",
            "total_prompts": len(prompts),
            "completed": completed,
            "failed": failed,
            "jobs": jobs,
            "stitched_video": stitched_video,
            "total_generation_time": round(total_time, 2),
        }

    async def generate_prompts(
        self,
        theme: str,
        num_parts: int = 3,
        character: Optional[str] = None,
    ) -> List[str]:
        """
        Generate Sora-optimized prompts for a multi-part video.

        Public wrapper around the internal prompt generation.

        Args:
            theme: Overall theme or topic.
            num_parts: Number of parts to generate prompts for.
            character: Optional Sora character reference.

        Returns:
            List of prompt strings, one per part.
        """
        return await self._generate_part_prompts(theme, num_parts, character)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    async def _generate_part_prompts(
        self,
        theme: str,
        num_parts: int,
        character: Optional[str] = None,
    ) -> List[str]:
        """
        Generate coordinated prompts for each part using AI.

        Each part follows a narrative arc:
            Part 1: Hook / Setup
            Part 2: Development / Tension
            Part 3: Resolution / CTA
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            character_directive = ""
            if character:
                character_directive = (
                    f"\nIMPORTANT: Feature the character {character} in every part. "
                    f"Reference them with @mention syntax for Sora character consistency."
                )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert at writing Sora video generation prompts. "
                            "Sora prompts should be highly visual and cinematic. "
                            "Describe camera angles, lighting, movement, and emotion. "
                            "Keep each prompt under 200 words. "
                            "Always respond with valid JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"""Generate {num_parts} coordinated Sora video prompts for a multi-part series.

Theme: {theme}
{character_directive}

Each part should:
- Be a complete visual scene (10-20 seconds)
- Follow a narrative arc across all parts
- Part 1: Hook/setup (grab attention immediately)
- Part 2: Development/tension (build the story)
- Part {num_parts}: Resolution/payoff (satisfying conclusion)
- Include cinematic details: camera angles, lighting, transitions
- Be optimized for vertical (9:16) video format

Return JSON: {{"prompts": ["part 1 prompt", "part 2 prompt", ...]}}""",
                    },
                ],
                temperature=0.8,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            prompts = result.get("prompts", [])

            if len(prompts) < num_parts:
                # Pad with fallback prompts
                for i in range(len(prompts), num_parts):
                    prompts.append(
                        f"Cinematic scene about {theme}, part {i + 1}. "
                        f"Beautiful lighting, smooth camera movement, 9:16 vertical."
                    )

            logger.info(
                f"Generated {len(prompts)} prompts for theme: {theme}"
            )
            return prompts[:num_parts]

        except Exception as e:
            logger.warning(f"AI prompt generation failed: {e}, using fallback")
            return self._fallback_prompts(theme, num_parts, character)

    def _fallback_prompts(
        self, theme: str, num_parts: int, character: Optional[str] = None
    ) -> List[str]:
        """Generate fallback prompts without AI."""
        char_ref = f" featuring {character}" if character else ""

        arc_labels = {
            1: "Opening hook",
            2: "Development and tension",
            3: "Climax and resolution",
            4: "Epilogue",
            5: "Behind the scenes",
        }

        prompts = []
        for i in range(1, num_parts + 1):
            arc = arc_labels.get(i, f"Part {i}")
            prompts.append(
                f"Cinematic 4K vertical video (9:16): {arc} of a story about {theme}{char_ref}. "
                f"Beautiful lighting, smooth camera movements, dramatic composition. "
                f"10-15 seconds."
            )
        return prompts

    async def _generate_single_part(
        self,
        prompt: str,
        part_num: int,
        job_id: str,
        character: Optional[str] = None,
        remove_watermark: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a single video part.

        Attempts to use Safari automation if available, falls back to
        creating a placeholder that records the generation request.
        """
        part_id = f"{job_id}_part{part_num}"
        start_time = time.time()

        try:
            # Try Safari-based Sora automation
            video_path = await self._sora_generate(
                prompt=prompt,
                character=character,
                part_id=part_id,
            )

            if video_path and Path(video_path).exists():
                # Optionally remove watermark
                if remove_watermark:
                    video_path = await self._remove_watermark(
                        video_path, part_id
                    )

                generation_time = time.time() - start_time
                return {
                    "part_num": part_num,
                    "part_id": part_id,
                    "status": "completed",
                    "prompt": prompt,
                    "video_path": video_path,
                    "generation_time": round(generation_time, 2),
                }

            # If Safari automation not available, record as pending
            return {
                "part_num": part_num,
                "part_id": part_id,
                "status": "pending_manual",
                "prompt": prompt,
                "video_path": None,
                "message": "Safari automation unavailable, prompt recorded for manual generation",
            }

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"[{part_id}] Generation failed: {e}")
            return {
                "part_num": part_num,
                "part_id": part_id,
                "status": "failed",
                "prompt": prompt,
                "video_path": None,
                "error": str(e),
                "generation_time": round(generation_time, 2),
            }

    async def _sora_generate(
        self,
        prompt: str,
        character: Optional[str] = None,
        part_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate video via Sora Safari automation or daily pipeline.

        Falls back gracefully if automation is not available (e.g. Safari
        files were deleted or running in CI).
        """
        # Try the daily pipeline's generation method first
        try:
            from services.sora_daily.daily_scheduler import get_daily_scheduler

            scheduler = get_daily_scheduler()

            # Create a generation job
            job = scheduler.create_job(
                prompt=prompt,
                theme=part_id or "batch",
                character=character,
            )

            if job:
                logger.info(f"Queued Sora generation job: {job.id}")

                # Poll for completion (with timeout)
                video_path = await self._poll_for_video(
                    job_id=job.id, timeout=600
                )
                return video_path

        except ImportError:
            logger.debug("sora_daily not available, trying direct automation")
        except Exception as e:
            logger.warning(f"Daily scheduler failed: {e}")

        # Try direct file-based approach (check for pre-existing downloads)
        existing = self._find_existing_download(part_id)
        if existing:
            return existing

        logger.info(
            f"No automation available for {part_id}, returning None"
        )
        return None

    async def _poll_for_video(
        self, job_id: str, timeout: int = 600
    ) -> Optional[str]:
        """Poll for a completed Sora video with timeout."""
        poll_interval = 10
        elapsed = 0

        while elapsed < timeout:
            # Check output directory for completed file
            for ext in [".mp4", ".webm", ".mov"]:
                candidate = SORA_OUTPUT_DIR / f"{job_id}{ext}"
                if candidate.exists() and candidate.stat().st_size > 0:
                    return str(candidate)

            # Also check by pattern
            for f in SORA_OUTPUT_DIR.glob(f"*{job_id}*"):
                if f.suffix in [".mp4", ".webm", ".mov"] and f.stat().st_size > 0:
                    return str(f)

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(f"Polling timeout for {job_id} after {timeout}s")
        return None

    def _find_existing_download(self, part_id: str) -> Optional[str]:
        """Check if a video was already downloaded for this part."""
        if not part_id:
            return None

        for ext in [".mp4", ".webm", ".mov"]:
            candidate = SORA_OUTPUT_DIR / f"{part_id}{ext}"
            if candidate.exists() and candidate.stat().st_size > 0:
                return str(candidate)

        # Pattern match
        for f in SORA_OUTPUT_DIR.glob(f"*{part_id}*"):
            if f.suffix in [".mp4", ".webm", ".mov"] and f.stat().st_size > 0:
                return str(f)

        return None

    async def _remove_watermark(
        self, video_path: str, part_id: str
    ) -> str:
        """Remove Sora watermark from video."""
        try:
            from services.sora_daily.watermark_service import get_watermark_service

            watermark_svc = get_watermark_service()
            result = await watermark_svc.remove_watermark(
                video_path, job_id=part_id
            )
            output = result.get("output_path")
            if output and Path(output).exists():
                return output
        except ImportError:
            logger.debug("Watermark service not available")
        except Exception as e:
            logger.warning(f"Watermark removal failed: {e}")

        # Return original if watermark removal fails
        return video_path

    async def _stitch_parts(
        self,
        clip_paths: List[str],
        job_id: str,
        theme: str,
    ) -> Optional[str]:
        """Stitch multiple video clips into a single video."""
        if len(clip_paths) < 2:
            return clip_paths[0] if clip_paths else None

        output_filename = f"{job_id}_stitched.mp4"
        output_path = str(SORA_PROCESSED_DIR / output_filename)

        logger.info(
            f"[{job_id}] Stitching {len(clip_paths)} clips..."
        )

        try:
            from services.ai_video_pipeline.stitcher import (
                StitchConfig,
                VideoStitcher,
            )

            stitcher = VideoStitcher(output_dir=str(SORA_PROCESSED_DIR))

            config = StitchConfig(
                output_path=output_path,
                clips=clip_paths,
            )

            result_path = stitcher.stitch_full_video(config)

            if result_path and Path(result_path).exists():
                logger.info(f"[{job_id}] Stitched video: {result_path}")
                return result_path

        except Exception as e:
            logger.error(f"[{job_id}] Stitching failed: {e}")

        # Fallback: simple concatenation
        try:
            success = self.stitcher.concatenate_clips(clip_paths, output_path)
            if success:
                return output_path
        except Exception as e:
            logger.error(f"[{job_id}] Fallback concatenation failed: {e}")

        return None

    async def _analyze_content(
        self,
        video_path: str,
        theme: str,
        prompts: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Run AI content analysis on the stitched video.

        Uses the prompts as a pseudo-transcript if no real transcript
        is available (since Sora videos are AI-generated without audio).
        """
        try:
            # Build pseudo-transcript from prompts + theme
            pseudo_transcript = (
                f"Video theme: {theme}\n\n"
                + "\n\n".join(
                    f"Scene {i + 1}: {p}" for i, p in enumerate(prompts)
                )
            )

            analysis = self.analyzer.analyze_transcript(
                transcript=pseudo_transcript,
                video_metadata={
                    "source": "sora_pipeline",
                    "theme": theme,
                    "num_parts": len(prompts),
                    "video_path": video_path,
                },
            )

            logger.info(
                f"Content analysis complete: "
                f"viral_score={analysis.get('pre_social_score', 'N/A')}"
            )

            # Map pre_social_score to viral_score for downstream compatibility
            if "pre_social_score" in analysis and "viral_score" not in analysis:
                analysis["viral_score"] = analysis["pre_social_score"]

            return analysis

        except Exception as e:
            logger.warning(f"Content analysis failed: {e}")
            return {
                "detected_hook": theme,
                "topics": [theme],
                "viral_score": 50,
                "hashtags": [],
                "error": str(e),
            }
