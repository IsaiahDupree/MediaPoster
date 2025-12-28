#!/usr/bin/env python3
"""
Headless Motion Canvas Rendering
=================================
Render Motion Canvas scenes using headless browser (Puppeteer).

This allows programmatic rendering without the editor UI.

Usage:
    python Backend/scripts/render_with_headless.py --scene animatedText
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from loguru import logger


def create_headless_renderer(project_dir: Path) -> Path:
    """
    Create a Node.js script that uses Motion Canvas API to render headlessly.
    """
    render_script = project_dir / "headless_render.js"
    
    script_content = """
import {makeProject} from '@motion-canvas/core';
import {renderVideo} from '@motion-canvas/core/lib/render';

async function renderScene(sceneName, outputPath) {
  try {
    // Import project
    const project = await import('./src/project.ts');
    const projectConfig = project.default;
    
    // Find scene
    const scene = projectConfig.scenes.find(s => s.name === sceneName);
    
    if (!scene) {
      throw new Error(`Scene not found: ${sceneName}`);
    }
    
    // Render
    await renderVideo({
      scene,
      output: outputPath,
      fps: 30,
      width: 1920,
      height: 1080,
    });
    
    console.log(`✅ Rendered: ${outputPath}`);
  } catch (error) {
    console.error('❌ Render failed:', error);
    process.exit(1);
  }
}

const sceneName = process.argv[2];
const outputPath = process.argv[3];

if (!sceneName || !outputPath) {
  console.error('Usage: node headless_render.js <sceneName> <outputPath>');
  process.exit(1);
}

renderScene(sceneName, outputPath);
"""
    
    render_script.write_text(script_content)
    logger.info(f"Created headless renderer: {render_script}")
    return render_script


def render_headless(
    project_dir: Path,
    scene_name: str,
    output_path: Path,
) -> bool:
    """
    Render scene using headless browser approach.
    """
    logger.info(f"Rendering {scene_name} headlessly...")
    
    # Create renderer script
    render_script = create_headless_renderer(project_dir)
    
    # Run with Node.js
    try:
        result = subprocess.run(
            ["node", str(render_script), scene_name, str(output_path)],
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
            logger.warning("⚠️  Output file not found")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Render failed: {e.stderr}")
        logger.info("💡 Motion Canvas headless rendering requires additional setup")
        return False
    except FileNotFoundError:
        logger.error("❌ Node.js not found")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Render Motion Canvas scene headlessly"
    )
    parser.add_argument("--scene", required=True, help="Scene name")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--project-dir", type=Path, help="Motion Canvas project directory")
    
    args = parser.parse_args()
    
    # Default project directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas")
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{args.scene}.mp4"
    
    success = render_headless(project_dir, args.scene, output_path)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

