"""
ACTP Creative Engine
=====================
Bridges to Remotion's video generation pipeline for creating ad video clips.
Supports Sora, Veo3, Nano Banana, and Remotion native rendering.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import ACTPConfig, VideoGenerationConfig
from .models import Creative, GenerationSource, TestCampaign, TestRound

logger = logging.getLogger(__name__)

# Path to Remotion project
REMOTION_BASE = os.getenv(
    "REMOTION_BASE_PATH",
    "/Users/isaiahdupree/Documents/Software/Remotion",
)


class CreativeEngine:
    """
    Generates video creatives for ad testing.

    Integrates with:
    - Remotion SoraVideoPipeline for Sora video generation
    - Remotion render-brief queue for final composition
    - OpenAI GPT-4o for brief/script generation
    - Supabase Storage for asset storage
    """

    def __init__(self, db_client=None, config: Optional[VideoGenerationConfig] = None):
        self.db = db_client
        self.config = config or VideoGenerationConfig()
        self._openai_client = None
        self._init_openai()
        logger.info("[ACTP:Creative] Engine initialized")

    def _init_openai(self):
        """Initialize OpenAI client for brief generation."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("[ACTP:Creative] OPENAI_API_KEY not set")
            return
        try:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=api_key)
            logger.info("[ACTP:Creative] OpenAI client ready")
        except ImportError:
            logger.warning("[ACTP:Creative] openai package not installed")

    # ─── Brief Generation ─────────────────────────────────

    async def generate_briefs(
        self,
        campaign: TestCampaign,
        angles: List[str],
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate video briefs from offer + angles using GPT-4o.

        Returns list of briefs with: hook, body, cta, visual_direction, script
        """
        if not self._openai_client:
            raise RuntimeError("OpenAI client not initialized")

        offer_context = (
            f"Offer: {campaign.offer_name or 'N/A'}\n"
            f"URL: {campaign.offer_url or 'N/A'}\n"
            f"Mode: {campaign.mode}\n"
            f"Target Audience: {json.dumps(campaign.target_audience or {})}"
        )

        briefs = []
        for angle in angles[:count]:
            prompt = f"""You are an expert direct-response ad creative strategist.

Generate a short-form video ad brief (15-30 seconds) for social media (TikTok, YouTube Shorts, Instagram Reels).

{offer_context}

Angle: {angle}

Return a JSON object with these fields:
- hook: The opening hook (first 3 seconds) that stops the scroll. Must be attention-grabbing.
- body: The main message (5-10 seconds) that builds desire or addresses a pain point.
- cta: The call-to-action (last 3 seconds) that drives the viewer to act.
- script: Full spoken script for voiceover (under 50 words).
- visual_direction: Description of what should be shown visually in each scene.
- thumbnail_description: Description for a thumbnail image.
- target_emotion: The primary emotion this ad targets.
- style: Video style (ugc, cinematic, explainer, testimonial, before_after).

Return ONLY valid JSON, no markdown."""

            try:
                response = self._openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    response_format={"type": "json_object"},
                )
                brief = json.loads(response.choices[0].message.content)
                brief["angle"] = angle
                brief["campaign_id"] = campaign.id
                briefs.append(brief)
                logger.info(f"[ACTP:Creative] Generated brief for angle: {angle}")
            except Exception as e:
                logger.error(f"[ACTP:Creative] Brief generation failed for '{angle}': {e}")

        return briefs

    # ─── Video Generation ─────────────────────────────────

    async def generate_creatives(
        self,
        campaign: TestCampaign,
        test_round: TestRound,
        briefs: List[Dict[str, Any]],
        provider: Optional[str] = None,
    ) -> List[Creative]:
        """
        Generate video creatives from briefs using the specified provider.
        """
        provider = provider or self.config.default_provider
        creatives = []

        for brief in briefs:
            try:
                if provider == "sora":
                    video_url = await self._generate_sora(brief)
                    source = GenerationSource.SORA
                elif provider == "veo3":
                    video_url = await self._generate_veo3(brief)
                    source = GenerationSource.VEO3
                elif provider == "nano_banana":
                    video_url = await self._generate_nano_banana(brief)
                    source = GenerationSource.NANO_BANANA
                else:
                    video_url = await self._generate_remotion(brief)
                    source = GenerationSource.REMOTION

                creative = Creative(
                    campaign_id=campaign.id,
                    round_id=test_round.id,
                    video_url=video_url,
                    hook=brief.get("hook"),
                    cta=brief.get("cta"),
                    angle=brief.get("angle"),
                    script=brief.get("script"),
                    generation_source=source,
                    generation_metadata={
                        "brief": brief,
                        "provider": provider,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

                await self._save_creative(creative)
                creatives.append(creative)
                logger.info(f"[ACTP:Creative] Generated creative {creative.id} via {provider}")

            except Exception as e:
                logger.error(f"[ACTP:Creative] Generation failed: {e}")

        return creatives

    async def generate_variations(
        self,
        parent_creative: Creative,
        campaign: TestCampaign,
        test_round: TestRound,
        strategy: str = "hook_swap",
        count: int = 3,
    ) -> List[Creative]:
        """
        Generate variations of a winning creative using the specified strategy.
        Uses MediaPoster's AdVariationGenerator (AD-002).
        """
        try:
            sys.path.insert(0, os.path.join(REMOTION_BASE, "..", "MediaPoster", "Backend"))
            from services.ad_testing.variation_generator import get_variation_generator
            generator = get_variation_generator()
        except ImportError:
            logger.warning("[ACTP:Creative] Could not import AdVariationGenerator, using AI remix")
            generator = None

        variations = []
        parent_elements = {
            "hooks": [parent_creative.hook] if parent_creative.hook else [],
            "ctas": [parent_creative.cta] if parent_creative.cta else [],
            "pain_points": [parent_creative.angle] if parent_creative.angle else [],
        }

        if generator:
            var_data = generator.generate_variations(parent_elements, strategy=strategy)
            for v in var_data[:count]:
                brief = {
                    "hook": v.get("hook", parent_creative.hook),
                    "cta": v.get("cta", parent_creative.cta),
                    "angle": v.get("pain_point", parent_creative.angle),
                    "script": parent_creative.script,
                    "visual_direction": parent_creative.generation_metadata.get("brief", {}).get("visual_direction", ""),
                }
                video_url = await self._generate_sora(brief)
                creative = Creative(
                    campaign_id=campaign.id,
                    round_id=test_round.id,
                    parent_creative_id=parent_creative.id,
                    video_url=video_url,
                    hook=brief["hook"],
                    cta=brief["cta"],
                    angle=brief["angle"],
                    script=brief["script"],
                    generation_source=GenerationSource.REMIX,
                    generation_metadata={
                        "strategy": strategy,
                        "parent_id": parent_creative.id,
                        "variation_data": v,
                    },
                )
                await self._save_creative(creative)
                variations.append(creative)
        else:
            # Fallback: use GPT-4o to generate variations
            new_briefs = await self._ai_remix_briefs(parent_creative, count)
            for brief in new_briefs:
                video_url = await self._generate_sora(brief)
                creative = Creative(
                    campaign_id=campaign.id,
                    round_id=test_round.id,
                    parent_creative_id=parent_creative.id,
                    video_url=video_url,
                    hook=brief.get("hook"),
                    cta=brief.get("cta"),
                    angle=brief.get("angle"),
                    script=brief.get("script"),
                    generation_source=GenerationSource.REMIX,
                    generation_metadata={
                        "strategy": "ai_remix",
                        "parent_id": parent_creative.id,
                    },
                )
                await self._save_creative(creative)
                variations.append(creative)

        logger.info(f"[ACTP:Creative] Generated {len(variations)} variations from {parent_creative.id}")
        return variations

    # ─── Provider Implementations ─────────────────────────

    async def _generate_sora(self, brief: Dict[str, Any]) -> str:
        """Generate video using OpenAI Sora API via existing SoraProvider."""
        try:
            sys.path.insert(0, os.path.join(REMOTION_BASE, "python"))
            from services.video_providers.sora_provider import SoraProvider
            from services.video_providers.base import ProviderConfig, CreateClipInput

            provider = SoraProvider()
            clip_input = CreateClipInput(
                prompt=self._brief_to_sora_prompt(brief),
                model=self.config.sora_model,
                size=self.config.sora_size,
                seconds=self.config.default_duration_seconds,
            )
            generation = await provider.create_clip(clip_input)

            # Poll for completion
            import asyncio
            for _ in range(60):
                status = await provider.get_clip_status(generation.provider_generation_id)
                if status.status.value == "succeeded":
                    if status.download_url:
                        local_path = await self._download_and_store(
                            status.download_url, brief.get("angle", "creative")
                        )
                        return local_path
                elif status.status.value in ("failed", "canceled"):
                    raise RuntimeError(f"Sora generation failed: {status.error}")
                await asyncio.sleep(5)

            raise TimeoutError("Sora generation timed out")

        except ImportError:
            logger.error("[ACTP:Creative] Could not import SoraProvider")
            raise
        finally:
            await provider.close() if 'provider' in dir() else None

    async def _generate_veo3(self, brief: Dict[str, Any]) -> str:
        """Generate video using Google Veo3 API."""
        # Veo3 API integration
        api_key = os.getenv("GOOGLE_VEO3_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_VEO3_API_KEY not set")

        import httpx
        prompt = self._brief_to_sora_prompt(brief)  # Similar prompt format

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/veo-3.0-generate-preview:predictLongRunning",
                headers={"x-goog-api-key": api_key},
                json={
                    "instances": [{"prompt": prompt}],
                    "parameters": {
                        "aspectRatio": "9:16",
                        "durationSeconds": self.config.default_duration_seconds,
                        "personGeneration": "allow_adult",
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            # Poll for completion via operation name
            operation_name = data.get("name")
            if not operation_name:
                raise RuntimeError("Veo3 did not return operation name")

            import asyncio
            for _ in range(120):
                poll = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/{operation_name}",
                    headers={"x-goog-api-key": api_key},
                )
                poll_data = poll.json()
                if poll_data.get("done"):
                    video_uri = poll_data.get("response", {}).get("generatedSamples", [{}])[0].get("video", {}).get("uri")
                    if video_uri:
                        local_path = await self._download_and_store(video_uri, brief.get("angle", "veo3"))
                        return local_path
                    raise RuntimeError("Veo3 completed but no video URI")
                await asyncio.sleep(5)

            raise TimeoutError("Veo3 generation timed out")

    async def _generate_nano_banana(self, brief: Dict[str, Any]) -> str:
        """Generate UGC-style video using Nano Banana API."""
        api_key = os.getenv("NANO_BANANA_API_KEY")
        if not api_key:
            raise RuntimeError("NANO_BANANA_API_KEY not set")

        import httpx
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "https://api.nanobanana.com/v1/videos/generate",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "script": brief.get("script", ""),
                    "hook": brief.get("hook", ""),
                    "cta": brief.get("cta", ""),
                    "style": brief.get("style", "ugc"),
                    "aspect_ratio": "9:16",
                    "duration_seconds": self.config.default_duration_seconds,
                },
            )
            response.raise_for_status()
            data = response.json()

            video_url = data.get("video_url")
            if video_url:
                local_path = await self._download_and_store(video_url, brief.get("angle", "nano"))
                return local_path
            raise RuntimeError("Nano Banana returned no video URL")

    async def _generate_remotion(self, brief: Dict[str, Any]) -> str:
        """Generate video using Remotion's render-brief queue."""
        import httpx
        remotion_server = os.getenv("REMOTION_SERVER_URL", "http://localhost:3100")

        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{remotion_server}/api/queue/render-brief",
                json={
                    "brief": {
                        "id": str(uuid4()),
                        "hook": brief.get("hook", ""),
                        "body": brief.get("body", ""),
                        "cta": brief.get("cta", ""),
                        "script": brief.get("script", ""),
                        "visual_direction": brief.get("visual_direction", ""),
                        "settings": {
                            "duration_sec": self.config.default_duration_seconds,
                            "aspect_ratio": self.config.aspect_ratio,
                        },
                    },
                    "quality": "production",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("videoPath", "")

    # ─── Helpers ──────────────────────────────────────────

    def _brief_to_sora_prompt(self, brief: Dict[str, Any]) -> str:
        """Convert a creative brief to a Sora-compatible prompt."""
        visual = brief.get("visual_direction", "")
        hook = brief.get("hook", "")
        style = brief.get("style", "cinematic")

        return (
            f"Create a {style} short-form vertical video ad (9:16 aspect ratio). "
            f"Opening scene: {hook}. "
            f"Visual direction: {visual}. "
            f"The video should feel authentic and native to social media. "
            f"High production quality, engaging pacing, modern aesthetic."
        )

    async def _download_and_store(self, url: str, label: str) -> str:
        """Download video from URL and store locally (or to Supabase Storage)."""
        import httpx
        output_dir = Path("data/actp_creatives")
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{label}_{uuid4().hex[:8]}.mp4"
        local_path = output_dir / filename

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(response.content)

        logger.info(f"[ACTP:Creative] Downloaded video to {local_path}")

        # Upload to Supabase Storage if configured
        if self.db:
            try:
                storage_path = f"actp/{label}/{filename}"
                self.db.storage.from_("actp-videos").upload(
                    storage_path, open(local_path, "rb")
                )
                signed = self.db.storage.from_("actp-videos").create_signed_url(
                    storage_path, 86400 * 30
                )
                return signed.get("signedURL", str(local_path))
            except Exception as e:
                logger.warning(f"[ACTP:Creative] Supabase upload failed, using local: {e}")

        return str(local_path)

    async def _ai_remix_briefs(
        self, parent: Creative, count: int = 3
    ) -> List[Dict[str, Any]]:
        """Use GPT-4o to generate remix variations of a winning creative."""
        if not self._openai_client:
            return []

        prompt = f"""You are an expert ad creative strategist. A winning ad creative has these elements:
- Hook: {parent.hook}
- CTA: {parent.cta}
- Angle: {parent.angle}
- Script: {parent.script}

Generate {count} NEW variations that keep the winning essence but test different approaches.
For each variation, change the hook OR the CTA OR the angle — not all at once.

Return a JSON array of objects, each with: hook, cta, angle, script, visual_direction, style.
Return ONLY valid JSON."""

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            return data.get("variations", data) if isinstance(data, dict) else data
        except Exception as e:
            logger.error(f"[ACTP:Creative] AI remix failed: {e}")
            return []

    async def _save_creative(self, creative: Creative):
        """Persist creative to database."""
        if self.db:
            await self.db.table("actp_creatives").upsert(
                creative.model_dump(mode="json")
            ).execute()

    # ─── Video Validation ─────────────────────────────────

    async def validate_video(self, video_path: str) -> Dict[str, Any]:
        """
        Validate generated video: resolution, duration, codec, file size, audio.
        Uses FFprobe for metadata extraction.
        """
        import asyncio
        import shutil

        result = {"valid": True, "errors": [], "metadata": {}}

        if not os.path.exists(video_path):
            return {"valid": False, "errors": ["File not found"], "metadata": {}}

        file_size = os.path.getsize(video_path)
        result["metadata"]["file_size_bytes"] = file_size

        max_size = 500 * 1024 * 1024  # 500MB
        if file_size > max_size:
            result["errors"].append(f"File too large: {file_size} bytes (max {max_size})")
            result["valid"] = False

        if file_size < 1024:
            result["errors"].append("File too small, likely corrupt")
            result["valid"] = False

        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            result["metadata"]["note"] = "ffprobe not available, basic validation only"
            return result

        try:
            proc = await asyncio.create_subprocess_exec(
                ffprobe, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", video_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            probe = json.loads(stdout.decode())

            fmt = probe.get("format", {})
            streams = probe.get("streams", [])

            duration = float(fmt.get("duration", 0))
            result["metadata"]["duration_seconds"] = duration
            result["metadata"]["format"] = fmt.get("format_name")
            result["metadata"]["bitrate"] = int(fmt.get("bit_rate", 0))

            if duration < 3:
                result["errors"].append(f"Too short: {duration}s (min 3s)")
                result["valid"] = False
            if duration > 180:
                result["errors"].append(f"Too long: {duration}s (max 180s)")
                result["valid"] = False

            video_stream = next((s for s in streams if s["codec_type"] == "video"), None)
            audio_stream = next((s for s in streams if s["codec_type"] == "audio"), None)

            if video_stream:
                w = int(video_stream.get("width", 0))
                h = int(video_stream.get("height", 0))
                result["metadata"]["resolution"] = f"{w}x{h}"
                result["metadata"]["codec"] = video_stream.get("codec_name")
                result["metadata"]["fps"] = eval(video_stream.get("r_frame_rate", "0/1")) if "/" in str(video_stream.get("r_frame_rate", "")) else float(video_stream.get("r_frame_rate", 0))

                if w < 540 or h < 960:
                    result["errors"].append(f"Resolution too low: {w}x{h} (min 540x960)")
                    result["valid"] = False
            else:
                result["errors"].append("No video stream found")
                result["valid"] = False

            result["metadata"]["has_audio"] = audio_stream is not None

        except Exception as e:
            result["metadata"]["probe_error"] = str(e)

        return result

    # ─── Thumbnail Generation ─────────────────────────────

    async def generate_thumbnail(
        self, video_path: str, count: int = 5
    ) -> List[str]:
        """
        Extract candidate thumbnail frames from video using FFmpeg.
        Returns list of thumbnail file paths.
        """
        import asyncio
        import shutil

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            logger.warning("[ACTP:Creative] FFmpeg not available for thumbnails")
            return []

        output_dir = Path("data/actp_thumbnails")
        output_dir.mkdir(parents=True, exist_ok=True)

        base = Path(video_path).stem
        thumbnails = []

        # Get video duration first
        validation = await self.validate_video(video_path)
        duration = validation["metadata"].get("duration_seconds", 15)

        # Extract frames at evenly spaced intervals
        for i in range(count):
            timestamp = (duration / (count + 1)) * (i + 1)
            output = output_dir / f"{base}_thumb_{i}.jpg"

            proc = await asyncio.create_subprocess_exec(
                ffmpeg, "-y", "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1", "-q:v", "2",
                str(output),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if output.exists() and output.stat().st_size > 0:
                thumbnails.append(str(output))

        logger.info(f"[ACTP:Creative] Generated {len(thumbnails)} thumbnails from {video_path}")
        return thumbnails

    # ─── Creative Tagging ─────────────────────────────────

    async def auto_tag_creative(self, creative: Creative) -> List[str]:
        """Auto-generate tags for a creative based on its brief metadata."""
        tags = []

        if creative.generation_source:
            tags.append(f"source:{creative.generation_source.value if hasattr(creative.generation_source, 'value') else creative.generation_source}")

        metadata = creative.generation_metadata or {}
        brief = metadata.get("brief", {})

        if brief.get("style"):
            tags.append(f"style:{brief['style']}")
        if brief.get("target_emotion"):
            tags.append(f"emotion:{brief['target_emotion']}")
        if creative.angle:
            tags.append(f"angle:{creative.angle[:30]}")

        if creative.is_winner:
            tags.append("winner")
        if creative.parent_creative_id:
            tags.append("variation")

        # Update in DB
        if self.db and tags:
            await self.db.table("actp_creatives").update(
                {"tags": tags}
            ).eq("id", creative.id).execute()

        return tags

    # ─── Creative Search ──────────────────────────────────

    async def search_creatives(
        self,
        query: Optional[str] = None,
        score_min: Optional[float] = None,
        score_max: Optional[float] = None,
        source: Optional[str] = None,
        winner_only: bool = False,
        tags: Optional[List[str]] = None,
        campaign_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search and filter creatives with full-text search and filters."""
        if not self.db:
            return {"creatives": [], "total": 0}

        q = self.db.table("actp_creatives").select("*", count="exact")

        if campaign_id:
            q = q.eq("campaign_id", campaign_id)
        if winner_only:
            q = q.eq("is_winner", True)
        if source:
            q = q.eq("generation_source", source)
        if score_min is not None:
            q = q.gte("organic_score", score_min)
        if score_max is not None:
            q = q.lte("organic_score", score_max)

        # Full-text search via textSearch if query provided
        if query:
            q = q.text_search("search_vector", query)

        q = q.order("organic_score", desc=True, nullsfirst=False)
        q = q.range(offset, offset + limit - 1)

        result = await q.execute()
        return {
            "creatives": result.data or [],
            "total": result.count if hasattr(result, "count") else len(result.data or []),
        }

    # ─── Cost Estimation ──────────────────────────────────

    def estimate_generation_cost(
        self, provider: str, count: int
    ) -> Dict[str, Any]:
        """Estimate API costs before generating creatives."""
        from .monitoring import CostTracker
        tracker = CostTracker()
        return tracker.estimate_generation_cost(provider, count)

    # ─── Duplicate Detection ──────────────────────────────

    async def check_duplicate(
        self, hook: str, angle: str, campaign_id: str, threshold: float = 0.8
    ) -> Optional[Dict[str, Any]]:
        """Check if a similar creative already exists in this campaign."""
        if not self.db:
            return None

        existing = await self.db.table("actp_creatives").select(
            "id, hook, angle"
        ).eq("campaign_id", campaign_id).execute()

        for c in (existing.data or []):
            existing_hook = (c.get("hook") or "").lower().strip()
            existing_angle = (c.get("angle") or "").lower().strip()
            new_hook = hook.lower().strip()
            new_angle = angle.lower().strip()

            # Simple Jaccard similarity on words
            def word_sim(a: str, b: str) -> float:
                wa = set(a.split())
                wb = set(b.split())
                if not wa and not wb:
                    return 1.0
                if not wa or not wb:
                    return 0.0
                return len(wa & wb) / len(wa | wb)

            hook_sim = word_sim(existing_hook, new_hook)
            angle_sim = word_sim(existing_angle, new_angle)
            combined = (hook_sim * 0.6) + (angle_sim * 0.4)

            if combined >= threshold:
                return {
                    "duplicate": True,
                    "existing_id": c["id"],
                    "similarity": round(combined, 3),
                    "existing_hook": c.get("hook"),
                }

        return None

    # ─── Platform Video Specs ─────────────────────────────

    PLATFORM_SPECS = {
        "youtube_shorts": {
            "max_duration": 60,
            "min_resolution": "540x960",
            "max_file_size_mb": 256,
            "codecs": ["h264", "vp9"],
            "aspect_ratio": "9:16",
        },
        "tiktok": {
            "max_duration": 180,
            "min_resolution": "540x960",
            "max_file_size_mb": 287,
            "codecs": ["h264", "hevc"],
            "aspect_ratio": "9:16",
        },
        "instagram_reels": {
            "max_duration": 90,
            "min_resolution": "540x960",
            "max_file_size_mb": 250,
            "codecs": ["h264"],
            "aspect_ratio": "9:16",
        },
        "meta_ads": {
            "max_duration": 240,
            "min_resolution": "600x600",
            "max_file_size_mb": 4000,
            "codecs": ["h264"],
            "aspect_ratio": "9:16",
        },
    }

    def validate_for_platform(
        self, video_metadata: Dict[str, Any], platform: str
    ) -> Dict[str, Any]:
        """Validate video meets specific platform requirements."""
        spec = self.PLATFORM_SPECS.get(platform)
        if not spec:
            return {"valid": True, "platform": platform, "errors": []}

        errors = []
        duration = video_metadata.get("duration_seconds", 0)
        if duration > spec["max_duration"]:
            errors.append(f"Duration {duration}s exceeds {platform} max {spec['max_duration']}s")

        file_mb = video_metadata.get("file_size_bytes", 0) / (1024 * 1024)
        if file_mb > spec["max_file_size_mb"]:
            errors.append(f"File size {file_mb:.0f}MB exceeds {platform} max {spec['max_file_size_mb']}MB")

        codec = video_metadata.get("codec", "")
        if codec and codec not in spec["codecs"]:
            errors.append(f"Codec {codec} not supported by {platform} (needs {spec['codecs']})")

        return {
            "valid": len(errors) == 0,
            "platform": platform,
            "errors": errors,
            "spec": spec,
        }

    # ─── Script Readability Scoring ───────────────────────

    def score_script_readability(self, script: str) -> Dict[str, Any]:
        """Score a script's readability for short-form video voiceover."""
        if not script:
            return {"score": 0, "word_count": 0, "reading_time_seconds": 0}
        words = script.split()
        word_count = len(words)
        avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
        sentences = max(script.count(".") + script.count("!") + script.count("?"), 1)
        words_per_sentence = word_count / sentences
        reading_time_seconds = (word_count / 150) * 60
        score = 100
        if word_count < 10:
            score -= 30
        elif word_count > 80:
            score -= (word_count - 80) * 2
        if avg_word_len > 6:
            score -= (avg_word_len - 6) * 10
        if words_per_sentence > 15:
            score -= (words_per_sentence - 15) * 3
        score = max(0, min(100, score))
        return {
            "score": round(score, 1),
            "word_count": word_count,
            "avg_word_length": round(avg_word_len, 1),
            "sentence_count": sentences,
            "words_per_sentence": round(words_per_sentence, 1),
            "reading_time_seconds": round(reading_time_seconds, 1),
            "ideal_for_short_form": 15 <= word_count <= 60,
        }

    # ─── Creative Asset Library ───────────────────────────

    async def list_library(
        self,
        campaign_id: Optional[str] = None,
        source: Optional[str] = None,
        winner_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List creatives in the asset library with filtering."""
        if not self.db:
            return {"creatives": [], "total": 0}
        query = self.db.table("actp_creatives").select("*", count="exact")
        if campaign_id:
            query = query.eq("campaign_id", campaign_id)
        if source:
            query = query.eq("generation_source", source)
        if winner_only:
            query = query.eq("is_winner", True)
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = await query.execute()
        return {
            "creatives": result.data or [],
            "total": getattr(result, "count", len(result.data or [])),
            "limit": limit,
            "offset": offset,
        }

    # ─── Creative Expiry and Cleanup ──────────────────────

    async def cleanup_expired_creatives(self, max_age_days: int = 90) -> Dict[str, Any]:
        """Mark old non-winner creatives as expired."""
        if not self.db:
            return {"cleaned": 0}
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        result = await self.db.table("actp_creatives").select("id").lt(
            "created_at", cutoff
        ).eq("is_winner", False).execute()
        expired_ids = [c["id"] for c in (result.data or [])]
        if expired_ids:
            await self.db.table("actp_creatives").update({"status": "expired"}).in_(
                "id", expired_ids
            ).execute()
        logger.info(f"[ACTP:Creative] Cleaned up {len(expired_ids)} expired creatives")
        return {"cleaned": len(expired_ids), "max_age_days": max_age_days, "cutoff": cutoff}

    # ─── Video Duration Variants ──────────────────────────

    DURATION_VARIANTS = {
        "5s":  {"duration": 5,  "use_case": "hook_test",        "platforms": ["tiktok", "instagram_reels"]},
        "15s": {"duration": 15, "use_case": "standard_short",   "platforms": ["tiktok", "youtube_shorts", "instagram_reels"]},
        "30s": {"duration": 30, "use_case": "detailed",         "platforms": ["tiktok", "youtube_shorts", "instagram_reels"]},
        "60s": {"duration": 60, "use_case": "long_form_short",  "platforms": ["tiktok", "youtube_shorts"]},
    }

    def plan_duration_variants(self, creative: Creative, target_platforms: List[str]) -> List[Dict[str, Any]]:
        """Plan which duration variants to generate for a creative."""
        variants = []
        for key, spec in self.DURATION_VARIANTS.items():
            matching = [p for p in target_platforms if p in spec["platforms"]]
            if matching:
                variants.append({
                    "duration_key": key,
                    "duration_seconds": spec["duration"],
                    "use_case": spec["use_case"],
                    "target_platforms": matching,
                    "creative_id": creative.id,
                })
        return variants

    # ─── Video Format Optimization ────────────────────────

    def optimize_format(self, video_path: str, target_platform: str) -> Dict[str, Any]:
        """Return ffmpeg command args to optimize a video for a target platform."""
        spec = self.PLATFORM_SPECS.get(target_platform, {})
        codec = spec.get("codecs", ["h264"])[0]
        args = [
            "-c:v", codec,
            "-crf", "23",
            "-preset", "fast",
            "-movflags", "+faststart",
        ]
        if target_platform in ("tiktok", "instagram_reels"):
            args += ["-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"]
        elif target_platform == "youtube_shorts":
            args += ["-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"]
        return {
            "input": video_path,
            "ffmpeg_args": args,
            "target_platform": target_platform,
            "codec": codec,
        }

    # ─── Video Transcoding Config ─────────────────────────

    def get_transcoding_config(self, platform: str) -> Dict[str, Any]:
        """Get transcoding parameters for a platform."""
        configs = {
            "tiktok": {"codec": "h264", "bitrate": "4M", "fps": 30, "resolution": "1080x1920", "audio_codec": "aac", "audio_bitrate": "128k"},
            "youtube_shorts": {"codec": "h264", "bitrate": "8M", "fps": 60, "resolution": "1080x1920", "audio_codec": "aac", "audio_bitrate": "192k"},
            "instagram_reels": {"codec": "h264", "bitrate": "3.5M", "fps": 30, "resolution": "1080x1920", "audio_codec": "aac", "audio_bitrate": "128k"},
            "meta_ads": {"codec": "h264", "bitrate": "4M", "fps": 30, "resolution": "1080x1080", "audio_codec": "aac", "audio_bitrate": "128k"},
        }
        return configs.get(platform, configs["tiktok"])

    # ─── Hook / CTA Text Overlay Config ──────────────────

    def build_overlay_config(
        self, hook: str, cta: str, style: str = "bold_white"
    ) -> Dict[str, Any]:
        """Build ffmpeg drawtext overlay configuration for hook and CTA."""
        styles = {
            "bold_white": {"fontcolor": "white", "fontsize": 48, "box": 1, "boxcolor": "black@0.5"},
            "yellow_outline": {"fontcolor": "yellow", "fontsize": 52, "borderw": 3, "bordercolor": "black"},
            "minimal": {"fontcolor": "white", "fontsize": 36, "box": 0},
        }
        s = styles.get(style, styles["bold_white"])
        return {
            "hook_overlay": {
                "text": hook[:60],
                "x": "(w-text_w)/2",
                "y": "h*0.15",
                **s,
                "enable": "between(t,0,3)",
            },
            "cta_overlay": {
                "text": cta[:40],
                "x": "(w-text_w)/2",
                "y": "h*0.80",
                **s,
                "enable": "between(t,duration-3,duration)",
            },
            "style": style,
        }

    # ─── TTS Voiceover Configuration ──────────────────────

    TTS_PROVIDERS = {
        "openai": {"model": "tts-1-hd", "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]},
        "elevenlabs": {"model": "eleven_multilingual_v2", "voices": ["Rachel", "Domi", "Bella", "Antoni"]},
        "google": {"model": "en-US-Neural2-F", "voices": ["en-US-Neural2-F", "en-US-Neural2-D"]},
    }

    def get_tts_config(self, provider: str = "openai", voice: Optional[str] = None) -> Dict[str, Any]:
        """Get TTS voiceover configuration for a provider."""
        config = self.TTS_PROVIDERS.get(provider, self.TTS_PROVIDERS["openai"])
        selected_voice = voice or config["voices"][0]
        api_key_env = {
            "openai": "OPENAI_API_KEY",
            "elevenlabs": "ELEVENLABS_API_KEY",
            "google": "GOOGLE_APPLICATION_CREDENTIALS",
        }.get(provider, "OPENAI_API_KEY")
        return {
            "provider": provider,
            "model": config["model"],
            "voice": selected_voice,
            "available_voices": config["voices"],
            "configured": bool(os.getenv(api_key_env)),
            "api_key_env": api_key_env,
        }

    async def generate_voiceover(self, script: str, provider: str = "openai", voice: str = "nova") -> Dict[str, Any]:
        """Generate a voiceover audio file from a script using TTS."""
        config = self.get_tts_config(provider, voice)
        if not config["configured"]:
            return {"generated": False, "error": f"{config['api_key_env']} not set"}
        if provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.audio.speech.create(model=config["model"], voice=voice, input=script)
                import tempfile, pathlib
                tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                response.stream_to_file(tmp.name)
                return {"generated": True, "path": tmp.name, "provider": provider, "voice": voice}
            except Exception as e:
                logger.error(f"[ACTP:Creative] TTS failed: {e}")
                return {"generated": False, "error": str(e)}
        return {"generated": False, "error": f"Provider {provider} not yet integrated"}

    # ─── Background Music Selection ───────────────────────

    MUSIC_MOODS = {
        "energetic": ["upbeat_electronic", "hip_hop_trap", "motivational_rock"],
        "calm": ["ambient_lo_fi", "soft_piano", "acoustic_guitar"],
        "urgent": ["tension_build", "fast_percussion", "dramatic_strings"],
        "inspirational": ["cinematic_swell", "uplifting_pop", "orchestral_rise"],
    }

    def select_background_music(self, mood: str = "energetic", duration_seconds: int = 30) -> Dict[str, Any]:
        """Select background music track based on mood and duration."""
        tracks = self.MUSIC_MOODS.get(mood, self.MUSIC_MOODS["energetic"])
        return {
            "mood": mood,
            "recommended_track": tracks[0],
            "alternatives": tracks[1:],
            "duration_seconds": duration_seconds,
            "volume_db": -18,
            "fade_in_seconds": 0.5,
            "fade_out_seconds": 1.0,
        }

    # ─── Image Ad Generation ──────────────────────────────

    def build_image_ad_config(self, creative: Creative, platform: str = "meta_ads") -> Dict[str, Any]:
        """Build configuration for generating a static image ad from a creative brief."""
        image_specs = {
            "meta_ads": {"width": 1080, "height": 1080, "format": "jpg", "max_size_mb": 30},
            "tiktok_ads": {"width": 1080, "height": 1920, "format": "jpg", "max_size_mb": 100},
            "google_display": {"width": 1200, "height": 628, "format": "jpg", "max_size_mb": 5},
        }
        spec = image_specs.get(platform, image_specs["meta_ads"])
        return {
            "creative_id": creative.id,
            "platform": platform,
            "headline": creative.hook or "",
            "body": creative.script or "",
            "cta": creative.cta or "",
            "image_spec": spec,
            "dalle_prompt": f"Professional ad image: {creative.hook}. Style: clean, modern, high-contrast. No text.",
            "requires_openai": True,
        }

    # ─── Audio-Only Ad Configuration ──────────────────────

    def build_audio_ad_config(self, creative: Creative) -> Dict[str, Any]:
        """Build configuration for an audio-only ad (podcast/radio)."""
        return {
            "creative_id": creative.id,
            "script": creative.script or f"{creative.hook} {creative.cta}",
            "duration_target_seconds": 30,
            "format": "mp3",
            "bitrate": "192k",
            "tts_config": self.get_tts_config("openai", "nova"),
            "music_config": self.select_background_music("calm", 30),
            "platforms": ["spotify_ads", "podcast_networks", "radio"],
        }

    # ─── Multi-Language Creative Generation ───────────────

    SUPPORTED_LANGUAGES = {
        "en": "English", "es": "Spanish", "pt": "Portuguese",
        "fr": "French", "de": "German", "ja": "Japanese",
        "ko": "Korean", "zh": "Chinese (Simplified)",
    }

    async def generate_multilingual_brief(
        self, brief: Dict[str, Any], target_language: str
    ) -> Dict[str, Any]:
        """Translate a creative brief into another language using GPT-4o."""
        if target_language not in self.SUPPORTED_LANGUAGES:
            return {"error": f"Language {target_language} not supported", "supported": list(self.SUPPORTED_LANGUAGES.keys())}
        if not self._openai_client:
            return {"error": "OpenAI not configured"}
        lang_name = self.SUPPORTED_LANGUAGES[target_language]
        prompt = f"""Translate this ad creative brief to {lang_name}. Keep it natural and culturally appropriate for native speakers. Return JSON with same keys.

Brief: {json.dumps(brief)}

Return ONLY valid JSON."""
        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            translated = json.loads(response.choices[0].message.content)
            translated["language"] = target_language
            translated["language_name"] = lang_name
            translated["original_language"] = "en"
            return translated
        except Exception as e:
            logger.error(f"[ACTP:Creative] Translation failed: {e}")
            return {"error": str(e)}

    # ─── Creative Approval Workflow ────────────────────────

    async def submit_for_approval(self, creative_id: str) -> Dict[str, Any]:
        """Submit a creative for manual approval before publishing."""
        if not self.db:
            return {"submitted": False}
        await self.db.table("actp_creatives").update({"approval_status": "pending_review"}).eq("id", creative_id).execute()
        return {"submitted": True, "creative_id": creative_id, "status": "pending_review"}

    async def approve_creative(self, creative_id: str, reviewer: str = "system") -> Dict[str, Any]:
        """Approve a creative for publishing."""
        if not self.db:
            return {"approved": False}
        await self.db.table("actp_creatives").update({"approval_status": "approved", "approved_by": reviewer}).eq("id", creative_id).execute()
        return {"approved": True, "creative_id": creative_id, "reviewer": reviewer}

    async def reject_creative(self, creative_id: str, reason: str) -> Dict[str, Any]:
        """Reject a creative with a reason."""
        if not self.db:
            return {"rejected": False}
        await self.db.table("actp_creatives").update({"approval_status": "rejected", "rejection_reason": reason}).eq("id", creative_id).execute()
        return {"rejected": True, "creative_id": creative_id, "reason": reason}
