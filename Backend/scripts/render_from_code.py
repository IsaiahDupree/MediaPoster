#!/usr/bin/env python3
"""
Render Motion Canvas from Code - Complete Solution
==================================================
Complete programmatic workflow: Create scene and render to video.

This uses the Motion Canvas adapter to generate scenes and provides
a working programmatic rendering solution.

Usage:
    python Backend/scripts/render_from_code.py --text "Hello World"
    python Backend/scripts/render_from_code.py --text "Test" --style bounce --output my_video.mp4
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from services.video_renderer import MotionCanvasAdapter, RenderRequest
from services.video_renderer.base import Layer


async def create_and_render_animated_text(
    text: str,
    style: str = "fade",
    font_size: int = 72,
    color: str = "#ffffff",
    duration: float = 5.0,
    output_path: Path = None,
    project_dir: Path = None,
) -> Path:
    """
    Create animated text scene and render it programmatically.
    
    This uses the Motion Canvas adapter to generate the scene code
    and then attempts to render it.
    """
    if project_dir is None:
        project_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas")
    
    if output_path is None:
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"animated_{uuid4().hex[:8]}.mp4"
    
    logger.info(f"🎨 Creating animated text: '{text}'")
    logger.info(f"   Style: {style}")
    logger.info(f"   Duration: {duration}s")
    
    # Create adapter
    adapter = MotionCanvasAdapter(project_dir=str(project_dir))
    
    # Build animation based on style
    animation_layers = build_animation_layers(text, style, font_size, color, duration)
    
    # Create render request
    request = RenderRequest(
        job_id=f"text_{uuid4().hex[:8]}",
        composition="AnimatedText",
        layers=animation_layers,
        audio_tracks=[],
        duration=duration,
        fps=30,
        resolution={"width": 1920, "height": 1080},
    )
    
    logger.info("📝 Generating Motion Canvas scene...")
    
    # Render using adapter
    try:
        response = await adapter.render(request)
        logger.success(f"✅ Render complete: {response.video_path}")
        return Path(response.video_path)
    except Exception as e:
        logger.error(f"❌ Render failed: {e}")
        logger.info("💡 Motion Canvas programmatic rendering may require the editor")
        logger.info("💡 Alternative: Use FFmpeg for simple text overlays")
        raise


def build_animation_layers(
    text: str,
    style: str,
    font_size: int,
    color: str,
    duration: float,
) -> list[Layer]:
    """
    Build animation layers based on style.
    
    Returns list of Layer objects for the Motion Canvas adapter.
    """
    from services.video_renderer.base import Layer
    
    layers = []
    
    # Background layer for readability
    bg_layer = Layer(
        id="bg",
        type="shape",
        position={"x": 0, "y": 0, "width": 1920, "height": 250},
        style={"fill": "#000000", "opacity": 0.6},
        start=0.0,
        end=duration,
    )
    layers.append(bg_layer)
    
    # Text layer with animation
    text_layer = Layer(
        id="text",
        type="text",
        content=text,
        position={"x": 0, "y": 0},  # Centered
        style={
            "fontSize": font_size,
            "color": color,
            "fontFamily": "Arial",
            "fontWeight": 700,
        },
        start=0.0,
        end=duration,
        opacity=1.0,
        animation=style,  # fade, bounce, slide, scale
    )
    layers.append(text_layer)
    
    return layers


def main():
    parser = argparse.ArgumentParser(
        description="Render animated text from code (complete workflow)"
    )
    parser.add_argument("--text", required=True, help="Text to animate")
    parser.add_argument("--style", choices=["fade", "bounce", "slide", "scale"], default="bounce")
    parser.add_argument("--font-size", type=int, default=72)
    parser.add_argument("--color", default="#ffffff")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory")
    
    args = parser.parse_args()
    
    try:
        output_path = asyncio.run(
            create_and_render_animated_text(
                text=args.text,
                style=args.style,
                font_size=args.font_size,
                color=args.color,
                duration=args.duration,
                output_path=args.output,
                project_dir=args.project_dir,
            )
        )
        
        if output_path.exists():
            size_mb = output_path.stat().st_size / 1024 / 1024
            logger.info(f"📹 Video: {output_path}")
            logger.info(f"📊 File size: {size_mb:.2f} MB")
            return 0
        else:
            logger.warning("⚠️  Output file not found")
            return 1
            
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

