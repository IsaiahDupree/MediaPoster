#!/usr/bin/env python3
"""
Create Animated Text and Play Video
====================================
Create animated text scene, render it, and automatically open the video.

This script:
1. Creates Motion Canvas scene from code
2. Renders using FFmpeg (reliable, works from code)
3. Automatically opens the video

Usage:
    python Backend/scripts/create_and_play_animated_text.py --text "Hello World"
"""

import argparse
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Import scene creation
from create_animated_text import create_animated_text_scene, update_project_file


def create_video_with_ffmpeg(
    text: str,
    style: str,
    font_size: int,
    color: str,
    duration: float,
    output_path: Path,
) -> bool:
    """
    Create animated text video using FFmpeg.
    
    This is a reliable way to create animated text videos from code.
    """
    logger.info(f"Creating animated text video with FFmpeg...")
    logger.info(f"  Text: '{text}'")
    logger.info(f"  Style: {style}")
    logger.info(f"  Duration: {duration}s")
    
    # FFmpeg command to create animated text video
    # We'll create a video with animated text overlay
    
    # Build animation filter based on style
    if style == "fade":
        # Fade in/out
        drawtext_filter = (
            f"drawtext=text='{text}':"
            f"fontsize={font_size}:"
            f"fontcolor={color}:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"box=1:boxcolor=black@0.5:boxborderw=5:"
            f"enable='between(t,0,{duration*0.2})':"
            f"alpha='if(lt(t,{duration*0.2}),1,if(gt(t,{duration*0.8}),1-(t-{duration*0.8})/{duration*0.2},1))'"
        )
    elif style == "bounce":
        # Bounce animation (scale + fade)
        drawtext_filter = (
            f"drawtext=text='{text}':"
            f"fontsize={font_size}:"
            f"fontcolor={color}:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"box=1:boxcolor=black@0.5:boxborderw=5"
        )
    elif style == "slide":
        # Slide from bottom
        drawtext_filter = (
            f"drawtext=text='{text}':"
            f"fontsize={font_size}:"
            f"fontcolor={color}:"
            f"x=(w-text_w)/2:"
            f"y='if(lt(t,{duration*0.3}),h-th+(h-th)*(t/{duration*0.3}),(h-th))':"
            f"box=1:boxcolor=black@0.5:boxborderw=5"
        )
    else:  # scale or default
        drawtext_filter = (
            f"drawtext=text='{text}':"
            f"fontsize={font_size}:"
            f"fontcolor={color}:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"box=1:boxcolor=black@0.5:boxborderw=5"
        )
    
    # Create video with animated text
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-f", "lavfi",
        "-i", f"color=c=black:s=1920x1080:d={duration}:r=30",
        "-vf", drawtext_filter,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        str(output_path),
    ]
    
    logger.info(f"Running FFmpeg...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.success(f"✅ Video created: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg failed: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("❌ FFmpeg not found. Install with: brew install ffmpeg")
        return False


def open_video(video_path: Path):
    """Open video file using macOS 'open' command."""
    if not video_path.exists():
        logger.error(f"Video not found: {video_path}")
        return False
    
    try:
        subprocess.run(
            ["open", str(video_path)],
            check=True,
        )
        logger.info(f"🎬 Opened video: {video_path}")
        return True
    except subprocess.CalledProcessError:
        logger.error("Failed to open video")
        return False
    except FileNotFoundError:
        logger.error("'open' command not found (not macOS?)")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create animated text video and play it automatically"
    )
    parser.add_argument("--text", required=True, help="Text to animate")
    parser.add_argument("--style", choices=["fade", "bounce", "slide", "scale"], default="bounce")
    parser.add_argument("--font-size", type=int, default=72)
    parser.add_argument("--color", default="#ffffff", help="Text color (hex)")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory (for scene creation)")
    parser.add_argument("--no-scene", action="store_true", help="Don't create Motion Canvas scene, just render video")
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path("Backend/data/rendered_videos")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"animated_{uuid4().hex[:8]}.mp4"
    
    # Step 1: Create Motion Canvas scene (optional)
    if not args.no_scene:
        if args.project_dir:
            project_dir = Path(args.project_dir)
        else:
            project_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas")
        
        if project_dir.exists():
            logger.info("🎨 Creating Motion Canvas scene...")
            try:
                scene_name = "".join(c if c.isalnum() or c == "_" else "_" for c in args.text[:30])
                scene_name = scene_name.lower() or "animated_text"
                
                scene_file = create_animated_text_scene(
                    project_dir=project_dir,
                    scene_name=scene_name,
                    text=args.text,
                    style=args.style,
                    font_size=args.font_size,
                    color=args.color,
                    duration=args.duration,
                )
                
                update_project_file(project_dir, scene_name)
                logger.success(f"✅ Scene created: {scene_file.name}")
            except Exception as e:
                logger.warning(f"Scene creation failed: {e}")
                logger.info("Continuing with video creation...")
    
    # Step 2: Create video with FFmpeg
    logger.info("")
    logger.info("🎬 Creating animated text video...")
    
    success = create_video_with_ffmpeg(
        text=args.text,
        style=args.style,
        font_size=args.font_size,
        color=args.color,
        duration=args.duration,
        output_path=output_path,
    )
    
    if not success:
        return 1
    
    # Step 3: Open video automatically
    logger.info("")
    logger.info("🎥 Opening video...")
    
    if open_video(output_path):
        size_mb = output_path.stat().st_size / 1024 / 1024
        logger.success(f"✅ Video opened!")
        logger.info(f"📹 File: {output_path}")
        logger.info(f"📊 Size: {size_mb:.2f} MB")
        logger.info(f"⏱️  Duration: {args.duration}s")
        return 0
    else:
        logger.info(f"📹 Video created: {output_path}")
        logger.info("💡 Open manually or use: open " + str(output_path))
        return 0


if __name__ == "__main__":
    sys.exit(main())

