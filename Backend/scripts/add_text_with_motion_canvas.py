#!/usr/bin/env python3
"""
Add Text to Video using Motion Canvas
======================================
Example of using Motion Canvas to add text overlays to videos.

Motion Canvas is a canvas-based animation framework that's great for
programmatic video generation.

Setup:
    1. Install Motion Canvas: npm install -g @motion-canvas/core @motion-canvas/2d
    2. Create a Motion Canvas project (or use existing)
    3. Run this script

Usage:
    python scripts/add_text_with_motion_canvas.py --video path/to/video.mp4 --text "Hello"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def create_motion_canvas_scene(
    project_dir: Path,
    scene_name: str,
    video_path: Path,
    text: str,
    position: str = "center",
    font_size: int = 48,
    duration: float = 5.0,
) -> Path:
    """
    Create a Motion Canvas scene file that adds text overlay to a video.
    
    Motion Canvas uses TypeScript with an imperative API.
    """
    scenes_dir = project_dir / "src" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    
    scene_file = scenes_dir / f"{scene_name}.ts"
    
    # Position mapping
    position_map = {
        "top": "y: -400",
        "center": "y: 0",
        "bottom": "y: 400",
    }
    y_pos = position_map.get(position, "y: 0")
    
    # Motion Canvas scene code
    # Note: Motion Canvas is primarily for vector animations, not video overlays
    # For video + text, we'd typically use FFmpeg or a different approach
    # This is a conceptual example showing how Motion Canvas works
    
    scene_code = f"""import {{makeScene2D}} from '@motion-canvas/2d';
import {{Txt, Rect, Video}} from '@motion-canvas/2d/lib/components';
import {{createRef}} from '@motion-canvas/core';
import {{all}} from '@motion-canvas/core/lib/flow';

export default makeScene2D(function* (view) {{
  // Background video (if Motion Canvas supports video layers)
  // Note: Motion Canvas is primarily for vector animations
  // For video + text, consider using FFmpeg or Remotion instead
  
  // Create text overlay
  const textRef = createRef<Txt>();
  const text = new Txt({{
    ref: textRef,
    text: {json.dumps(text)},
    fontSize: {font_size},
    fill: '#ffffff',
    fontFamily: 'Arial',
    {y_pos},
    x: 0,
  }});
  
  // Add semi-transparent background for text readability
  const bgRef = createRef<Rect>();
  const bg = new Rect({{
    ref: bgRef,
    width: 1920,
    height: 200,
    fill: '#000000',
    opacity: 0.6,
    {y_pos},
    x: 0,
  }});
  
  view.add(bg);
  view.add(text);
  
  // Animate text appearance
  textRef().opacity(0);
  bgRef().opacity(0);
  
  yield* all(
    textRef().opacity(1, 0.5),
    bgRef().opacity(0.6, 0.5),
  );
  
  // Hold text for duration
  yield* textRef().opacity(1, {duration - 1});
  
  // Fade out
  yield* all(
    textRef().opacity(0, 0.5),
    bgRef().opacity(0, 0.5),
  );
}});
"""
    
    scene_file.write_text(scene_code)
    logger.info(f"Created Motion Canvas scene: {scene_file}")
    
    return scene_file


def render_with_motion_canvas(
    project_dir: Path,
    scene_name: str,
    output_path: Path,
    fps: int = 30,
    duration: float = 5.0,
) -> bool:
    """
    Render Motion Canvas scene to video.
    
    Note: This requires Motion Canvas CLI to be installed and configured.
    """
    logger.info(f"Rendering Motion Canvas scene: {scene_name}")
    
    # Motion Canvas CLI command
    # Note: Actual command may vary based on Motion Canvas version
    cmd = [
        "npx",
        "motion-canvas",
        "render",
        scene_name,
        "--output", str(output_path),
        "--fps", str(fps),
        "--duration", str(duration),
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
        logger.success(f"✅ Motion Canvas render complete: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Motion Canvas render failed: {e.stderr}")
        logger.info("💡 Tip: Motion Canvas is best for vector animations, not video overlays")
        logger.info("💡 For video + text, use FFmpeg instead (see add_text_to_video.py)")
        return False
    except FileNotFoundError:
        logger.error("❌ Motion Canvas CLI not found")
        logger.info("💡 Install with: npm install -g @motion-canvas/core @motion-canvas/2d")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Add text overlay using Motion Canvas (conceptual example)"
    )
    parser.add_argument("--video", type=Path, help="Input video (for reference)")
    parser.add_argument("--text", required=True, help="Text to overlay")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--position", choices=["top", "center", "bottom"], default="center")
    parser.add_argument("--font-size", type=int, default=48)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory")
    
    args = parser.parse_args()
    
    # Default project directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path("/Users/isaiahdupree/Documents/Software/MotionCanvas")
    
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create scene
    scene_name = "text_overlay"
    scene_file = create_motion_canvas_scene(
        project_dir=project_dir,
        scene_name=scene_name,
        video_path=args.video or Path(""),
        text=args.text,
        position=args.position,
        font_size=args.font_size,
        duration=args.duration,
    )
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project_dir / "output" / f"{scene_name}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Render
    logger.warning("⚠️  Motion Canvas is primarily for vector animations, not video overlays")
    logger.info("💡 For video + text overlays, use FFmpeg (see add_text_to_video.py)")
    logger.info("💡 Motion Canvas is better for: animated graphics, explainer videos, vector art")
    
    success = render_with_motion_canvas(
        project_dir=project_dir,
        scene_name=scene_name,
        output_path=output_path,
        duration=args.duration,
    )
    
    if success:
        logger.info(f"📹 Output: {output_path}")
        return 0
    else:
        logger.info("💡 Try using FFmpeg instead: python scripts/add_text_to_video.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())

