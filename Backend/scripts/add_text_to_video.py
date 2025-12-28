#!/usr/bin/env python3
"""
Add Text Overlay to Video
==========================
Simple script to add text overlays to videos using FFmpeg.
Can also demonstrate Motion Canvas/Remotion integration.

Usage:
    python scripts/add_text_to_video.py --video path/to/video.mp4 --text "Hello World"
    python scripts/add_text_to_video.py --random --text "Random Video Text"
"""

import argparse
import random
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def find_random_video() -> Optional[Path]:
    """Find a random video file from the project."""
    # Get project root (assuming script is in Backend/scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    video_paths = [
        project_root / "Backend" / "test_video_analysis.mp4",
        *list((project_root / "Backend" / "data" / "rendered_videos").glob("*.mp4")),
        *list((project_root / "local_storage" / "videos").glob("*.mp4")),
        Path("/Users/isaiahdupree/Documents/IphoneImport") / "*.mp4",
    ]
    
    # Also check absolute paths
    video_paths.extend([
        Path("/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/test_video_analysis.mp4"),
        *list(Path("/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/data/rendered_videos").glob("*.mp4")),
    ])
    
    # Filter to only existing files
    existing = [p for p in video_paths if p.exists() and p.is_file()]
    
    if not existing:
        logger.error("No video files found")
        logger.info(f"Searched in: {[str(p) for p in video_paths[:5]]}")
        return None
    
    chosen = random.choice(existing)
    logger.info(f"Found {len(existing)} videos, chose: {chosen}")
    return chosen


def add_text_with_ffmpeg(
    input_video: Path,
    output_video: Path,
    text: str,
    position: str = "center",
    font_size: int = 48,
    font_color: str = "white",
    x: Optional[int] = None,
    y: Optional[int] = None,
    start_time: float = 0.0,
    duration: Optional[float] = None,
) -> bool:
    """
    Add text overlay to video using FFmpeg.
    
    Args:
        input_video: Input video path
        output_video: Output video path
        text: Text to overlay
        position: Position preset ("top", "center", "bottom", "custom")
        font_size: Font size in pixels
        font_color: Font color (e.g., "white", "yellow", "#FF0000")
        x: X position (for custom position)
        y: Y position (for custom position)
        start_time: When to start showing text (seconds)
        duration: How long to show text (seconds, None = entire video)
    
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Adding text '{text}' to {input_video}")
    
    # Escape text for FFmpeg
    escaped_text = text.replace("'", "\\'").replace(":", "\\:")
    
    # Build position filter
    if position == "top":
        drawtext_pos = f"x=(w-text_w)/2:y=50"
    elif position == "center":
        drawtext_pos = f"x=(w-text_w)/2:y=(h-text_h)/2"
    elif position == "bottom":
        drawtext_pos = f"x=(w-text_w)/2:y=h-th-50"
    elif position == "custom" and x is not None and y is not None:
        drawtext_pos = f"x={x}:y={y}"
    else:
        drawtext_pos = f"x=(w-text_w)/2:y=(h-text_h)/2"
    
    # Build time filter
    time_filter = ""
    if start_time > 0 or duration:
        if duration:
            time_filter = f":enable='between(t,{start_time},{start_time + duration})'"
        else:
            time_filter = f":enable='gte(t,{start_time})'"
    
    # FFmpeg filter
    filter_complex = (
        f"drawtext=text='{escaped_text}'"
        f":fontsize={font_size}"
        f":fontcolor={font_color}"
        f":{drawtext_pos}"
        f":box=1:boxcolor=black@0.5:boxborderw=5"
        f"{time_filter}"
    )
    
    # FFmpeg command
    cmd = [
        "ffmpeg",
        "-i", str(input_video),
        "-vf", filter_complex,
        "-c:a", "copy",  # Copy audio without re-encoding
        "-y",  # Overwrite output file
        str(output_video),
    ]
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.success(f"✅ Text added successfully: {output_video}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg failed: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("❌ FFmpeg not found. Install with: brew install ffmpeg")
        return False


def add_text_with_motion_canvas(
    input_video: Path,
    output_video: Path,
    text: str,
    **kwargs
) -> bool:
    """
    Add text overlay using Motion Canvas (more advanced, requires setup).
    
    This is a placeholder - would require Motion Canvas project setup.
    """
    logger.warning("Motion Canvas integration requires project setup")
    logger.info("Using FFmpeg instead (simpler for now)")
    return add_text_with_ffmpeg(input_video, output_video, text, **kwargs)


def main():
    parser = argparse.ArgumentParser(description="Add text overlay to video")
    parser.add_argument("--video", type=Path, help="Input video path")
    parser.add_argument("--random", action="store_true", help="Use random video")
    parser.add_argument("--text", required=True, help="Text to overlay")
    parser.add_argument("--output", type=Path, help="Output video path (default: input_video_text.mp4)")
    parser.add_argument("--position", choices=["top", "center", "bottom", "custom"], default="center")
    parser.add_argument("--font-size", type=int, default=48)
    parser.add_argument("--font-color", default="white")
    parser.add_argument("--x", type=int, help="X position (for custom)")
    parser.add_argument("--y", type=int, help="Y position (for custom)")
    parser.add_argument("--start-time", type=float, default=0.0, help="Start time in seconds")
    parser.add_argument("--duration", type=float, help="Duration in seconds")
    parser.add_argument("--engine", choices=["ffmpeg", "motion_canvas", "remotion"], default="ffmpeg")
    
    args = parser.parse_args()
    
    # Find input video
    if args.random:
        input_video = find_random_video()
        if not input_video:
            logger.error("No random video found")
            return 1
        logger.info(f"Using random video: {input_video}")
    elif args.video:
        input_video = Path(args.video)
        if not input_video.exists():
            logger.error(f"Video not found: {input_video}")
            return 1
    else:
        logger.error("Must specify --video or --random")
        return 1
    
    # Determine output path
    if args.output:
        output_video = Path(args.output)
    else:
        output_video = input_video.parent / f"{input_video.stem}_text{input_video.suffix}"
    
    # Add text overlay
    if args.engine == "ffmpeg":
        success = add_text_with_ffmpeg(
            input_video=input_video,
            output_video=output_video,
            text=args.text,
            position=args.position,
            font_size=args.font_size,
            font_color=args.font_color,
            x=args.x,
            y=args.y,
            start_time=args.start_time,
            duration=args.duration,
        )
    elif args.engine == "motion_canvas":
        success = add_text_with_motion_canvas(
            input_video=input_video,
            output_video=output_video,
            text=args.text,
        )
    else:
        logger.error(f"Engine {args.engine} not yet implemented")
        return 1
    
    if success:
        logger.info(f"📹 Output video: {output_video}")
        logger.info(f"📊 File size: {output_video.stat().st_size / 1024 / 1024:.2f} MB")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

