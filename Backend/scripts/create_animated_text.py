#!/usr/bin/env python3
"""
Create Animated Text with Motion Canvas
========================================
Generate animated text graphics using Motion Canvas.

This script creates a Motion Canvas scene with animated text and renders it to video.

Usage:
    python Backend/scripts/create_animated_text.py --text "Hello World"
    python Backend/scripts/create_animated_text.py --text "My Text" --style bounce
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def create_animated_text_scene(
    project_dir: Path,
    scene_name: str,
    text: str,
    style: str = "fade",
    font_size: int = 72,
    color: str = "#ffffff",
    duration: float = 5.0,
) -> Path:
    """
    Create a Motion Canvas scene with animated text.
    
    Args:
        project_dir: Motion Canvas project directory
        scene_name: Name for the scene file
        text: Text to animate
        style: Animation style ("fade", "bounce", "slide", "scale")
        font_size: Font size in pixels
        color: Text color (hex)
        duration: Animation duration in seconds
    
    Returns:
        Path to created scene file
    """
    scenes_dir = project_dir / "src" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    
    scene_file = scenes_dir / f"{scene_name}.tsx"
    
    # Animation styles
    animations = {
        "fade": """
  // Fade in/out
  textRef().opacity(0);
  yield* textRef().opacity(1, 0.8);
  yield* waitFor(1);
  yield* textRef().opacity(0, 0.8);
""",
        "bounce": """
  // Bounce animation
  textRef().opacity(0);
  textRef().scale(0.3);
  yield* all(
    textRef().opacity(1, 0.6),
    textRef().scale(1, 0.6),
  );
  yield* waitFor(0.5);
  yield* textRef().scale(1.1, 0.2);
  yield* textRef().scale(1, 0.2);
  yield* waitFor(1);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().scale(0.5, 0.5),
  );
""",
        "slide": """
  // Slide in from bottom
  textRef().opacity(0);
  textRef().y(400);
  yield* all(
    textRef().opacity(1, 0.6),
    textRef().y(0, 0.6),
  );
  yield* waitFor(1);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().y(-400, 0.5),
  );
""",
        "scale": """
  // Scale animation
  textRef().opacity(0);
  textRef().scale(0);
  yield* all(
    textRef().opacity(1, 0.8),
    textRef().scale(1, 0.8),
  );
  yield* waitFor(1);
  yield* textRef().scale(1.2, 0.3);
  yield* textRef().scale(1, 0.3);
  yield* waitFor(0.5);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().scale(0, 0.5),
  );
""",
    }
    
    animation_code = animations.get(style, animations["fade"])
    
    scene_code = f"""import {{makeScene2D}} from '@motion-canvas/2d';
import {{Txt, Rect}} from '@motion-canvas/2d/lib/components';
import {{createRef}} from '@motion-canvas/core';
import {{all, waitFor}} from '@motion-canvas/core/lib/flow';

export default makeScene2D(function* (view) {{
  // Background for text readability
  const bgRef = createRef<Rect>();
  const bg = new Rect({{
    ref: bgRef,
    width: 1920,
    height: 250,
    fill: '#000000',
    opacity: 0.6,
    radius: 30,
  }});

  // Animated text
  const textRef = createRef<Txt>();
  const text = new Txt({{
    ref: textRef,
    text: {json.dumps(text)},
    fontSize: {font_size},
    fill: '{color}',
    fontFamily: 'Arial',
    fontWeight: 700,
    textAlign: 'center',
  }});

  view.add(bg);
  view.add(text);

{animation_code}
}});
"""
    
    scene_file.write_text(scene_code)
    logger.info(f"Created scene: {scene_file}")
    
    return scene_file


def update_project_file(project_dir: Path, scene_name: str):
    """Update project.ts to include the new scene."""
    project_file = project_dir / "src" / "project.ts"
    
    # Read existing project file
    if project_file.exists():
        content = project_file.read_text()
        
        # Check if scene is already imported
        if f"import {scene_name}" in content:
            logger.info(f"Scene {scene_name} already in project.ts")
            return
        
        # Add import
        import_line = f"import {scene_name} from './scenes/{scene_name}?scene';\n"
        
        # Find the imports section and add new import
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith("import") and "from '@motion-canvas/core'" in line:
                import_index = i + 1
                break
        
        lines.insert(import_index, import_line)
        
        # Add to scenes array
        scenes_line = f"  scenes: [{scene_name}],"
        for i, line in enumerate(lines):
            if "scenes: [" in line:
                # Replace or append
                if scene_name not in line:
                    lines[i] = line.replace("scenes: [", f"scenes: [{scene_name}, ")
                break
        
        project_file.write_text('\n'.join(lines))
        logger.info(f"Updated project.ts with {scene_name}")
    else:
        # Create new project file
        content = f"""import {{makeProject}} from '@motion-canvas/core';

import {scene_name} from './scenes/{scene_name}?scene';

export default makeProject({{
  scenes: [{scene_name}],
}});
"""
        project_file.write_text(content)
        logger.info(f"Created project.ts with {scene_name}")


def render_scene(project_dir: Path, scene_name: str, output: Optional[Path] = None) -> Path:
    """Render Motion Canvas scene to video."""
    if output is None:
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{scene_name}.mp4"
    
    logger.info(f"Rendering scene: {scene_name}")
    logger.info(f"Output: {output}")
    
    # Motion Canvas render command
    # Note: Motion Canvas CLI may vary, this is the expected format
    cmd = [
        "npx",
        "motion-canvas",
        "render",
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
        return output
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Render failed")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error("❌ Motion Canvas CLI not found")
        logger.info("💡 Try: npm install -g @motion-canvas/cli")
        raise


def main():
    parser = argparse.ArgumentParser(description="Create animated text with Motion Canvas")
    parser.add_argument("--text", required=True, help="Text to animate")
    parser.add_argument("--style", choices=["fade", "bounce", "slide", "scale"], default="fade")
    parser.add_argument("--font-size", type=int, default=72)
    parser.add_argument("--color", default="#ffffff", help="Text color (hex)")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--scene-name", help="Scene name (default: auto-generated)")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory")
    parser.add_argument("--no-render", action="store_true", help="Create scene but don't render")
    
    args = parser.parse_args()
    
    # Default project directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas")
    
    if not project_dir.exists():
        logger.error(f"Project directory not found: {project_dir}")
        return 1
    
    # Generate scene name
    if args.scene_name:
        scene_name = args.scene_name
    else:
        # Create name from text (sanitized)
        scene_name = "".join(c if c.isalnum() or c == "_" else "_" for c in args.text[:30])
        scene_name = scene_name.lower() or "animated_text"
    
    # Create scene
    try:
        scene_file = create_animated_text_scene(
            project_dir=project_dir,
            scene_name=scene_name,
            text=args.text,
            style=args.style,
            font_size=args.font_size,
            color=args.color,
            duration=args.duration,
        )
        
        # Update project file
        update_project_file(project_dir, scene_name)
        
        if args.no_render:
            logger.success(f"✅ Scene created: {scene_file}")
            logger.info("💡 Render with: python Backend/scripts/test_motion_canvas.py --render --scene {scene_name}")
            return 0
        
        # Render
        output = render_scene(project_dir, scene_name, args.output)
        
        if output.exists():
            size_mb = output.stat().st_size / 1024 / 1024
            logger.info(f"📹 Output: {output}")
            logger.info(f"📊 File size: {size_mb:.2f} MB")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

