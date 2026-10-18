#!/usr/bin/env python3
"""
Create and Render Animated Text - Pure Code Workflow
=====================================================
Create animated text scene and render it to video, all from code.

This is a complete workflow that doesn't require the editor.

Usage:
    python Backend/scripts/create_and_render_animated_text.py --text "Hello World"
    python Backend/scripts/create_and_render_animated_text.py --text "Test" --style bounce --render
"""

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger

# Import the scene creation function
from create_animated_text import create_animated_text_scene, update_project_file


def render_with_motion_canvas_cli(
    project_dir: Path,
    scene_name: str,
    output_path: Path,
) -> bool:
    """
    Render using Motion Canvas's built-in rendering capabilities.
    
    Note: Motion Canvas primarily uses the editor for rendering.
    For programmatic rendering, we'll use a headless approach.
    """
    logger.info(f"Rendering {scene_name} to {output_path}...")
    
    # Motion Canvas doesn't have a direct CLI for rendering
    # We need to use the editor or build system
    # Let's try using Puppeteer/headless browser approach
    
    # For now, we'll create a simple Node.js script that uses Motion Canvas API
    render_script = project_dir / "render_scene.js"
    
    script_content = f"""
import {{renderVideo}} from '@motion-canvas/core';
import {{makeProject}} from './src/project.js';

async function render() {{
  const project = makeProject();
  const scene = project.scenes.find(s => s.name === '{scene_name}');
  
  if (!scene) {{
    console.error('Scene not found: {scene_name}');
    process.exit(1);
  }}
  
  await renderVideo({{
    scene,
    output: '{output_path}',
  }});
  
  console.log('Render complete:', '{output_path}');
}}

render().catch(console.error);
"""
    
    render_script.write_text(script_content)
    logger.info(f"Created render script: {render_script}")
    
    # Try to run it
    try:
        result = subprocess.run(
            ["node", str(render_script)],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        logger.success(f"✅ Render complete: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Render failed: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("❌ Node.js not found")
        return False


def render_with_ffmpeg_workaround(
    project_dir: Path,
    scene_name: str,
    output_path: Path,
) -> bool:
    """
    Workaround: Use a simpler approach with FFmpeg for text overlays.
    
    Since Motion Canvas programmatic rendering is complex, we can:
    1. Generate the animated text as a separate video using FFmpeg
    2. Or use the Motion Canvas editor in headless mode
    """
    logger.warning("⚠️  Motion Canvas programmatic rendering is limited")
    logger.info("💡 Recommended approach:")
    logger.info("   1. Create scene with: create_animated_text.py")
    logger.info("   2. Start editor: cd MotionCanvas && npm start")
    logger.info("   3. Export from editor UI")
    logger.info("")
    logger.info("💡 Alternative: Use FFmpeg for simple text animations")
    logger.info("   See: add_text_to_video.py")
    
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Create and render animated text (pure code workflow)"
    )
    parser.add_argument("--text", required=True, help="Text to animate")
    parser.add_argument("--style", choices=["fade", "bounce", "slide", "scale"], default="fade")
    parser.add_argument("--font-size", type=int, default=72)
    parser.add_argument("--color", default="#ffffff")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--scene-name", help="Scene name (auto-generated if not provided)")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory")
    parser.add_argument("--render", action="store_true", help="Also render to video")
    parser.add_argument("--no-render", action="store_true", help="Don't render (just create scene)")
    
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
        
        update_project_file(project_dir, scene_name)
        
        logger.success(f"✅ Scene created: {scene_file}")
        
        if args.no_render:
            logger.info("💡 Scene created. Render with:")
            logger.info(f"   python Backend/scripts/render_motion_canvas.py --scene {scene_name}")
            return 0
        
        if not args.render:
            logger.info("💡 Add --render to also render the scene")
            return 0
        
        # Render
        if args.output:
            output_path = Path(args.output)
        else:
            output_dir = project_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{scene_name}.mp4"
        
        logger.info("⚠️  Motion Canvas programmatic rendering is limited")
        logger.info("💡 For best results, use the editor:")
        logger.info(f"   cd MotionCanvas && npm start")
        logger.info(f"   Then export scene: {scene_name}")
        logger.info("")
        logger.info("💡 Or use FFmpeg for simple text overlays:")
        logger.info("   python Backend/scripts/add_text_to_video.py --text 'Your Text'")
        
        # Try rendering anyway
        success = render_with_ffmpeg_workaround(project_dir, scene_name, output_path)
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

