#!/usr/bin/env python3
"""
Test Motion Canvas Setup
========================
Test script to verify Motion Canvas is working and create animated graphics.

Usage:
    python Backend/scripts/test_motion_canvas.py
    python Backend/scripts/test_motion_canvas.py --scene animatedText
    python Backend/scripts/test_motion_canvas.py --render
"""

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger


def check_motion_canvas_setup(project_dir: Path) -> bool:
    """Check if Motion Canvas project is properly set up."""
    logger.info(f"Checking Motion Canvas setup in: {project_dir}")
    
    required_files = [
        project_dir / "package.json",
        project_dir / "vite.config.ts",
        project_dir / "tsconfig.json",
        project_dir / "src" / "project.ts",
    ]
    
    missing = [f for f in required_files if not f.exists()]
    
    if missing:
        logger.error(f"Missing files: {[str(f) for f in missing]}")
        return False
    
    logger.success("✅ All required files present")
    return True


def start_editor(project_dir: Path) -> bool:
    """Start Motion Canvas editor."""
    logger.info("Starting Motion Canvas editor...")
    logger.info("Editor will open at: http://localhost:9000")
    
    try:
        subprocess.run(
            ["npm", "start"],
            cwd=str(project_dir),
            check=True,
        )
        return True
    except KeyboardInterrupt:
        logger.info("Editor stopped")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start editor: {e}")
        return False
    except FileNotFoundError:
        logger.error("npm not found. Make sure Node.js is installed.")
        return False


def render_scene(project_dir: Path, scene_name: str = "animatedText", output: Path = None) -> bool:
    """Render a Motion Canvas scene to video."""
    logger.info(f"Rendering scene: {scene_name}")
    
    if output is None:
        output = project_dir / "output" / f"{scene_name}.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
    
    # Motion Canvas render command
    cmd = [
        "npm", "run", "render",
        "--",
        scene_name,
        "--output", str(output),
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
        logger.success(f"✅ Render complete: {output}")
        logger.info(f"📹 Output: {output}")
        if output.exists():
            size_mb = output.stat().st_size / 1024 / 1024
            logger.info(f"📊 File size: {size_mb:.2f} MB")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Render failed: {e.stderr}")
        return False


def list_scenes(project_dir: Path):
    """List available scenes."""
    scenes_dir = project_dir / "src" / "scenes"
    
    if not scenes_dir.exists():
        logger.error(f"Scenes directory not found: {scenes_dir}")
        return
    
    scenes = list(scenes_dir.glob("*.tsx")) + list(scenes_dir.glob("*.ts"))
    
    if not scenes:
        logger.warning("No scenes found")
        return
    
    logger.info("Available scenes:")
    for scene in scenes:
        logger.info(f"  - {scene.stem}")


def main():
    parser = argparse.ArgumentParser(description="Test Motion Canvas setup")
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory")
    parser.add_argument("--check", action="store_true", help="Check setup only")
    parser.add_argument("--start", action="store_true", help="Start editor")
    parser.add_argument("--render", action="store_true", help="Render scene")
    parser.add_argument("--scene", default="animatedText", help="Scene name to render")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--list", action="store_true", help="List available scenes")
    
    args = parser.parse_args()
    
    # Default project directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas")
    
    if not project_dir.exists():
        logger.error(f"Project directory not found: {project_dir}")
        logger.info("💡 Run: python Backend/scripts/setup_motion_canvas.py")
        return 1
    
    # Check setup
    if not check_motion_canvas_setup(project_dir):
        logger.error("Motion Canvas setup incomplete")
        return 1
    
    if args.check:
        logger.success("✅ Setup check complete")
        return 0
    
    if args.list:
        list_scenes(project_dir)
        return 0
    
    if args.start:
        return 0 if start_editor(project_dir) else 1
    
    if args.render:
        return 0 if render_scene(project_dir, args.scene, args.output) else 1
    
    # Default: show info
    logger.info("Motion Canvas project ready!")
    logger.info("")
    logger.info("Available commands:")
    logger.info("  --check     Check setup")
    logger.info("  --start     Start editor (http://localhost:9000)")
    logger.info("  --render    Render scene to video")
    logger.info("  --list      List available scenes")
    logger.info("")
    logger.info("Example:")
    logger.info("  python Backend/scripts/test_motion_canvas.py --start")
    logger.info("  python Backend/scripts/test_motion_canvas.py --render --scene animatedText")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

