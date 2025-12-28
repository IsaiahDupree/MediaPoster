#!/usr/bin/env python3
"""
Render Motion Canvas Scene Programmatically
===========================================
Render Motion Canvas scenes to video purely from code, no editor needed.

Usage:
    python Backend/scripts/render_motion_canvas.py --scene animatedText
    python Backend/scripts/render_motion_canvas.py --scene hello_motion_canvas_ --output my_video.mp4
"""

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger


def render_scene_programmatically(
    project_dir: Path,
    scene_name: str,
    output_path: Path,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
) -> bool:
    """
    Render Motion Canvas scene to video using Vite build.
    
    This uses Vite's build mode to render without the editor.
    """
    logger.info(f"Rendering scene '{scene_name}' programmatically...")
    logger.info(f"Output: {output_path}")
    logger.info(f"Resolution: {width}x{height} @ {fps}fps")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Motion Canvas uses Vite for rendering
    # We'll use the build command with render mode
    cmd = [
        "npm",
        "run",
        "build",
        "--",
        "--mode", "render",
        "--scene", scene_name,
        "--output", str(output_path),
        "--fps", str(fps),
        "--width", str(width),
        "--height", str(height),
    ]
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        
        if output_path.exists():
            size_mb = output_path.stat().st_size / 1024 / 1024
            logger.success(f"✅ Render complete: {output_path}")
            logger.info(f"📊 File size: {size_mb:.2f} MB")
            return True
        else:
            logger.warning("⚠️  Output file not found, but command succeeded")
            logger.info("💡 Check the output directory for rendered files")
            return True
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Render failed")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        
        # Try alternative method using direct Vite
        logger.info("💡 Trying alternative rendering method...")
        return render_with_vite_direct(project_dir, scene_name, output_path, fps, width, height)
    except FileNotFoundError:
        logger.error("❌ npm not found")
        return False


def render_with_vite_direct(
    project_dir: Path,
    scene_name: str,
    output_path: Path,
    fps: int,
    width: int,
    height: int,
) -> bool:
    """
    Alternative: Render using Vite directly with environment variables.
    """
    import os
    
    logger.info("Trying direct Vite rendering...")
    
    # Set environment variables for Motion Canvas
    env = os.environ.copy()
    env["MOTION_CANVAS_SCENE"] = scene_name
    env["MOTION_CANVAS_OUTPUT"] = str(output_path)
    env["MOTION_CANVAS_FPS"] = str(fps)
    env["MOTION_CANVAS_WIDTH"] = str(width)
    env["MOTION_CANVAS_HEIGHT"] = str(height)
    
    cmd = [
        "npx",
        "vite",
        "build",
        "--mode", "render",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        
        if output_path.exists():
            logger.success(f"✅ Render complete: {output_path}")
            return True
        else:
            logger.warning("⚠️  Output not found at expected path")
            # Check default output location
            default_output = project_dir / "output" / f"{scene_name}.mp4"
            if default_output.exists():
                logger.info(f"📹 Found output at: {default_output}")
                import shutil
                shutil.copy2(default_output, output_path)
                logger.success(f"✅ Copied to: {output_path}")
                return True
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Vite render failed: {e.stderr}")
        return False


def render_with_ffmpeg_fallback(
    project_dir: Path,
    scene_name: str,
    output_path: Path,
) -> bool:
    """
    Fallback: Use Motion Canvas to export frames, then FFmpeg to create video.
    This is more reliable for programmatic rendering.
    """
    logger.info("Using FFmpeg fallback method...")
    
    # This would require Motion Canvas to export frames first
    # For now, just log the approach
    logger.info("💡 Motion Canvas programmatic rendering requires:")
    logger.info("   1. Export frames from Motion Canvas")
    logger.info("   2. Use FFmpeg to combine frames into video")
    logger.info("   3. Or use the editor's export feature")
    
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Render Motion Canvas scene programmatically"
    )
    parser.add_argument("--scene", required=True, help="Scene name to render")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--width", type=int, default=1920, help="Video width")
    parser.add_argument("--height", type=int, default=1080, help="Video height")
    
    args = parser.parse_args()
    
    # Default project directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas")
    
    if not project_dir.exists():
        logger.error(f"Project directory not found: {project_dir}")
        return 1
    
    # Check if scene exists
    scene_file = project_dir / "src" / "scenes" / f"{args.scene}.tsx"
    if not scene_file.exists():
        # Try .ts extension
        scene_file = project_dir / "src" / "scenes" / f"{args.scene}.ts"
        if not scene_file.exists():
            logger.error(f"Scene not found: {args.scene}")
            logger.info(f"💡 Available scenes in: {project_dir / 'src' / 'scenes'}")
            return 1
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{args.scene}.mp4"
    
    # Render
    success = render_scene_programmatically(
        project_dir=project_dir,
        scene_name=args.scene,
        output_path=output_path,
        fps=args.fps,
        width=args.width,
        height=args.height,
    )
    
    if success:
        logger.info(f"📹 Video: {output_path}")
        return 0
    else:
        logger.error("❌ Rendering failed")
        logger.info("💡 Tip: Motion Canvas programmatic rendering may require the editor")
        logger.info("💡 Alternative: Use the editor (npm start) and export from there")
        return 1


if __name__ == "__main__":
    sys.exit(main())

