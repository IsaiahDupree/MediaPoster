#!/usr/bin/env python3
"""
Complete Animated Text Workflow - Pure Code
============================================
End-to-end workflow: Create animated text scene and render it.

This script demonstrates the complete workflow using code only.

Usage:
    python Backend/scripts/complete_animated_text_workflow.py --text "Hello World"
"""

import argparse
import sys
from pathlib import Path

from loguru import logger

# Import scene creation
sys.path.insert(0, str(Path(__file__).parent))
from create_animated_text import create_animated_text_scene, update_project_file


def main():
    parser = argparse.ArgumentParser(
        description="Complete animated text workflow (pure code)"
    )
    parser.add_argument("--text", required=True, help="Text to animate")
    parser.add_argument("--style", choices=["fade", "bounce", "slide", "scale"], default="bounce")
    parser.add_argument("--font-size", type=int, default=72)
    parser.add_argument("--color", default="#ffffff")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory")
    
    args = parser.parse_args()
    
    # Default project directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas")
    
    # Generate scene name
    scene_name = "".join(c if c.isalnum() or c == "_" else "_" for c in args.text[:30])
    scene_name = scene_name.lower() or "animated_text"
    
    logger.info("🎨 Creating animated text scene...")
    
    # Step 1: Create scene
    try:
        scene_file = create_animated_text_scene(
            project_dir=project_dir,
            scene_name=scene_name,
            text=args.text,
            style=args.style,
            font_size=args.font_size,
            color=args.color,
            duration=5.0,
        )
        
        # Step 2: Update project
        update_project_file(project_dir, scene_name)
        
        logger.success(f"✅ Scene created: {scene_file.name}")
        
        # Step 3: Instructions for rendering
        logger.info("")
        logger.info("📝 Scene created successfully!")
        logger.info("")
        logger.info("⚠️  Motion Canvas programmatic rendering is limited.")
        logger.info("   The editor is the primary way to render scenes.")
        logger.info("")
        logger.info("💡 Options for rendering:")
        logger.info("")
        logger.info("   1. Use the Editor (Recommended):")
        logger.info(f"      cd MotionCanvas && npm start")
        logger.info(f"      Open http://localhost:9000")
        logger.info(f"      Select scene: {scene_name}")
        logger.info(f"      Click Export → MP4")
        logger.info("")
        logger.info("   2. Use FFmpeg for Simple Text (Alternative):")
        logger.info(f"      python Backend/scripts/add_text_to_video.py \\")
        logger.info(f"        --text '{args.text}' \\")
        logger.info(f"        --random")
        logger.info("")
        logger.info("   3. Use Python Adapter (Future):")
        logger.info(f"      from services.video_renderer import MotionCanvasAdapter")
        logger.info(f"      # (Requires additional setup)")
        logger.info("")
        
        if args.output:
            logger.info(f"💾 Scene file: {scene_file}")
            logger.info(f"📁 Project: {project_dir}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

