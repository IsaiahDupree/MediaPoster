"""
Ad Batch Renderer (AD-003)
===========================
Renders ad creative variations into platform-ready assets using Remotion-style
JSON spec generation.

Manages batches of ad creatives through a rendering pipeline:
    1. create_batch() - Register a set of variations for rendering
    2. render_batch() - Generate rendering specs and output paths
    3. get_batch_status() - Poll batch progress

Supports text overlays, voiceover references, and platform-specific sizing.

Usage:
    renderer = get_batch_renderer()
    batch_id = renderer.create_batch(variations)
    result = renderer.render_batch(batch_id)
    status = renderer.get_batch_status(batch_id)
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Default output directory for rendered specs
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "output",
    "ad_renders",
)

# Platform aspect ratios for ad creatives
PLATFORM_SPECS: Dict[str, Dict[str, Any]] = {
    "facebook": {"width": 1080, "height": 1080, "aspect": "1:1", "max_duration": 60},
    "instagram": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 60},
    "instagram_feed": {"width": 1080, "height": 1080, "aspect": "1:1", "max_duration": 60},
    "stories": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 15},
    "reels": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 90},
}


class AdBatchRenderer:
    """
    Batch renderer for ad creative variations (AD-003).

    Generates Remotion-compatible JSON specs for rendering ad creatives.
    Tracks batch state in memory.
    """

    _instance: Optional["AdBatchRenderer"] = None

    def __init__(self, output_dir: Optional[str] = None) -> None:
        self._output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self._batches: Dict[str, Dict[str, Any]] = {}
        logger.info(f"[AD-003] AdBatchRenderer initialized (output_dir={self._output_dir})")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_batch(
        self,
        variations: List[Dict[str, Any]],
        template: str = "ad_creative_v1",
        base_video_path: Optional[str] = None,
    ) -> str:
        """
        Create a new rendering batch from ad variations.

        Args:
            variations: List of variation dicts from AdVariationGenerator.
            template: Remotion template name to use.
            base_video_path: Optional path to a base video for overlay rendering.

        Returns:
            batch_id: Unique identifier for this rendering batch.
        """
        batch_id = f"batch-{uuid4().hex[:8]}"

        batch = {
            "batch_id": batch_id,
            "template": template,
            "base_video_path": base_video_path,
            "status": "created",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_variations": len(variations),
            "rendered_count": 0,
            "failed_count": 0,
            "variations": [],
            "rendered_paths": [],
            "specs": [],
        }

        # Register each variation in the batch
        for var in variations:
            var_entry = {
                "variation_id": var.get("id", _make_id()),
                "status": "pending",
                "spec": None,
                "output_path": None,
                "error": None,
            }
            batch["variations"].append(var_entry)

        self._batches[batch_id] = batch

        logger.info(
            f"[AD-003] Created batch {batch_id} with {len(variations)} variations "
            f"(template={template})"
        )
        return batch_id

    def render_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Render all variations in a batch by generating Remotion-style specs.

        In production this would call the Remotion rendering service.
        For dev/testing it generates the JSON specs and placeholder output paths.

        Args:
            batch_id: The batch to render.

        Returns:
            Dict with status, rendered_paths, specs, failed_count.
        """
        batch = self._batches.get(batch_id)
        if batch is None:
            logger.error(f"[AD-003] Batch {batch_id} not found")
            return {"error": "Batch not found", "status": "error"}

        batch["status"] = "rendering"
        batch["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Ensure output directory exists
        batch_output_dir = os.path.join(self._output_dir, batch_id)
        os.makedirs(batch_output_dir, exist_ok=True)

        rendered_paths: List[str] = []
        specs: List[Dict[str, Any]] = []

        for var_entry in batch["variations"]:
            try:
                spec = self._generate_remotion_spec(
                    var_entry["variation_id"],
                    batch["template"],
                    batch.get("base_video_path"),
                    var_entry,
                )
                output_path = os.path.join(
                    batch_output_dir,
                    f"{var_entry['variation_id']}.json",
                )

                # Write spec to disk
                with open(output_path, "w") as f:
                    json.dump(spec, f, indent=2)

                var_entry["status"] = "rendered"
                var_entry["spec"] = spec
                var_entry["output_path"] = output_path
                batch["rendered_count"] += 1
                rendered_paths.append(output_path)
                specs.append(spec)

            except Exception as exc:
                logger.error(
                    f"[AD-003] Failed to render variation {var_entry['variation_id']}: {exc}"
                )
                var_entry["status"] = "failed"
                var_entry["error"] = str(exc)
                batch["failed_count"] += 1

        # Determine final batch status
        if batch["failed_count"] == batch["total_variations"]:
            batch["status"] = "failed"
        elif batch["rendered_count"] == batch["total_variations"]:
            batch["status"] = "completed"
        else:
            batch["status"] = "partial"

        batch["rendered_paths"] = rendered_paths
        batch["specs"] = specs
        batch["updated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[AD-003] Batch {batch_id} rendering complete: "
            f"{batch['rendered_count']}/{batch['total_variations']} rendered, "
            f"{batch['failed_count']} failed"
        )

        return {
            "batch_id": batch_id,
            "status": batch["status"],
            "rendered_paths": rendered_paths,
            "rendered_count": batch["rendered_count"],
            "failed_count": batch["failed_count"],
            "total_variations": batch["total_variations"],
        }

    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get the current status of a rendering batch.

        Args:
            batch_id: The batch to query.

        Returns:
            Dict with batch_id, status, rendered_count, failed_count,
            total_variations, created_at, updated_at.
        """
        batch = self._batches.get(batch_id)
        if batch is None:
            return {"error": "Batch not found", "status": "not_found"}

        return {
            "batch_id": batch_id,
            "status": batch["status"],
            "template": batch["template"],
            "rendered_count": batch["rendered_count"],
            "failed_count": batch["failed_count"],
            "total_variations": batch["total_variations"],
            "rendered_paths": batch.get("rendered_paths", []),
            "created_at": batch["created_at"],
            "updated_at": batch["updated_at"],
        }

    def list_batches(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all batches, optionally filtered by status."""
        batches = list(self._batches.values())
        if status:
            batches = [b for b in batches if b["status"] == status]
        return [
            {
                "batch_id": b["batch_id"],
                "status": b["status"],
                "total_variations": b["total_variations"],
                "rendered_count": b["rendered_count"],
                "created_at": b["created_at"],
            }
            for b in batches
        ]

    # ------------------------------------------------------------------
    # Remotion spec generation
    # ------------------------------------------------------------------

    def _generate_remotion_spec(
        self,
        variation_id: str,
        template: str,
        base_video_path: Optional[str],
        var_entry: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a Remotion-compatible rendering spec for a single variation.

        The spec contains all the information needed to render the ad creative,
        including text overlays, voiceover references, and platform sizing.
        """
        # Determine platform specs
        platform = var_entry.get("platform", "facebook")
        platform_spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["facebook"])

        spec: Dict[str, Any] = {
            "id": variation_id,
            "template": template,
            "composition": f"AdCreative-{variation_id}",
            "output": {
                "format": "mp4",
                "codec": "h264",
                "width": platform_spec["width"],
                "height": platform_spec["height"],
                "fps": 30,
            },
            "props": {
                "headline": var_entry.get("headline", ""),
                "body": var_entry.get("body", ""),
                "cta": var_entry.get("cta", "Learn More"),
                "hook": var_entry.get("hook", ""),
                "platform": platform,
                "aspect_ratio": platform_spec["aspect"],
            },
            "overlays": {
                "text_overlays": [
                    {
                        "type": "headline",
                        "text": var_entry.get("headline", ""),
                        "position": "top",
                        "style": "bold",
                        "font_size": 48,
                        "color": "#FFFFFF",
                        "start_frame": 0,
                        "duration_frames": 90,
                    },
                    {
                        "type": "body",
                        "text": var_entry.get("body", ""),
                        "position": "center",
                        "style": "regular",
                        "font_size": 32,
                        "color": "#FFFFFF",
                        "start_frame": 60,
                        "duration_frames": 120,
                    },
                    {
                        "type": "cta",
                        "text": var_entry.get("cta", "Learn More"),
                        "position": "bottom",
                        "style": "button",
                        "font_size": 36,
                        "color": "#FFFFFF",
                        "background_color": "#1877F2",
                        "start_frame": 150,
                        "duration_frames": 90,
                    },
                ],
                "logo": None,
            },
            "audio": {
                "voiceover_ref": None,
                "background_music": None,
                "volume": 0.8,
            },
            "metadata": {
                "strategy": var_entry.get("strategy", "unknown"),
                "target_audience": var_entry.get("target_audience"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Add base video if provided
        if base_video_path:
            spec["props"]["base_video"] = base_video_path
            spec["audio"]["voiceover_ref"] = base_video_path

        return spec


def _make_id() -> str:
    return f"var-{uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_batch_renderer_instance: Optional[AdBatchRenderer] = None


def get_batch_renderer(output_dir: Optional[str] = None) -> AdBatchRenderer:
    """Get or create the singleton AdBatchRenderer instance."""
    global _batch_renderer_instance
    if _batch_renderer_instance is None:
        _batch_renderer_instance = AdBatchRenderer(output_dir=output_dir)
    return _batch_renderer_instance
