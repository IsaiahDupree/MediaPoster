"""
Enhanced Motion Canvas Animation Templates
==========================================
Advanced animation templates for Motion Canvas with more effects:
- Particle effects
- Gradient backgrounds
- Text animations with multiple styles
- Transitions
- Visual effects
"""

import json
from pathlib import Path
from typing import Dict, Any
from loguru import logger


# Enhanced animation templates
ENHANCED_ANIMATIONS = {
    "fade": """
  // Fade in/out
  textRef().opacity(0);
  yield* textRef().opacity(1, 0.8);
  yield* waitFor(1);
  yield* textRef().opacity(0, 0.8);
""",
    
    "bounce": """
  // Bounce animation with scale
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
  // Scale animation with pop
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
    
    "typewriter": """
  // Typewriter effect
  const fullText = textRef().text();
  textRef().text('');
  textRef().opacity(1);
  for (let i = 0; i <= fullText.length; i++) {
    textRef().text(fullText.substring(0, i));
    yield* waitFor(0.05);
  }
  yield* waitFor(1);
  yield* textRef().opacity(0, 0.5);
""",
    
    "glow": """
  // Glow effect with pulse
  textRef().opacity(0);
  textRef().shadowBlur(0);
  yield* all(
    textRef().opacity(1, 0.8),
    textRef().shadowBlur(50, 0.8),
  );
  yield* waitFor(0.5);
  yield* textRef().shadowBlur(80, 0.3);
  yield* textRef().shadowBlur(50, 0.3);
  yield* waitFor(1);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().shadowBlur(0, 0.5),
  );
""",
    
    "rotate": """
  // Rotate in with scale
  textRef().opacity(0);
  textRef().scale(0);
  textRef().rotation(180);
  yield* all(
    textRef().opacity(1, 0.8),
    textRef().scale(1, 0.8),
    textRef().rotation(0, 0.8),
  );
  yield* waitFor(1);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().scale(0.5, 0.5),
    textRef().rotation(-90, 0.5),
  );
""",
    
    "wave": """
  // Wave animation
  textRef().opacity(0);
  textRef().y(0);
  yield* all(
    textRef().opacity(1, 0.6),
    textRef().y(-20, 0.3),
  );
  yield* textRef().y(20, 0.3);
  yield* textRef().y(0, 0.3);
  yield* waitFor(1);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().y(100, 0.5),
  );
""",
    
    "zoom": """
  // Zoom in effect
  textRef().opacity(0);
  textRef().scale(2);
  yield* all(
    textRef().opacity(1, 0.6),
    textRef().scale(1, 0.6),
  );
  yield* waitFor(1);
  yield* textRef().scale(1.1, 0.2);
  yield* textRef().scale(1, 0.2);
  yield* waitFor(0.5);
  yield* all(
    textRef().opacity(0, 0.4),
    textRef().scale(0.3, 0.4),
  );
""",
}


def create_enhanced_scene(
    project_dir: Path,
    scene_name: str,
    text: str,
    style: str = "fade",
    font_size: int = 64,
    color: str = "#ffffff",
    duration: float = 5.0,
    background_color: str = "#1a1a1a",
    gradient: bool = False,
    particles: bool = False,
) -> Path:
    """
    Create enhanced Motion Canvas scene with advanced effects.
    
    Args:
        project_dir: Motion Canvas project directory
        scene_name: Name for the scene
        text: Text to display
        style: Animation style (fade, bounce, slide, scale, typewriter, glow, rotate, wave, zoom)
        font_size: Font size
        color: Text color
        duration: Animation duration
        background_color: Background color
        gradient: Add gradient background
        particles: Add particle effects (future)
    """
    scenes_dir = project_dir / "src" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    
    scene_file = scenes_dir / f"{scene_name}.tsx"
    
    animation_code = ENHANCED_ANIMATIONS.get(style, ENHANCED_ANIMATIONS["fade"])
    
    # Build background with optional gradient
    if gradient:
        bg_code = """
  // Gradient background
  const bgRef = createRef<Rect>();
  const bg = new Rect({
    ref: bgRef,
    width: 1920,
    height: 1080,
    fill: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    opacity: 0.8,
  });
"""
    else:
        bg_code = f"""
  // Solid background
  const bgRef = createRef<Rect>();
  const bg = new Rect({{
    ref: bgRef,
    width: 1920,
    height: 250,
    fill: '{background_color}',
    opacity: 0.7,
    radius: 30,
  }});
"""
    
    # Build text with shadow for glow effect
    if style == "glow":
        text_code = f"""
  // Text with glow effect
  const textRef = createRef<Txt>();
  const text = new Txt({{
    ref: textRef,
    text: {json.dumps(text)},
    fontSize: {font_size},
    fill: '{color}',
    fontFamily: 'Arial',
    fontWeight: 700,
    textAlign: 'center',
    shadowColor: '{color}',
    shadowBlur: 0,
  }});
"""
    else:
        text_code = f"""
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
"""
    
    scene_code = f"""import {{makeScene2D}} from '@motion-canvas/2d';
import {{Txt, Rect}} from '@motion-canvas/2d/lib/components';
import {{createRef}} from '@motion-canvas/core';
import {{all, waitFor}} from '@motion-canvas/core/lib/flow';

export default makeScene2D(function* (view) {{
{bg_code}

{text_code}

  view.add(bg);
  view.add(text);

  // Initialize background
  bgRef().opacity(0);
  yield* bgRef().opacity(0.7, 0.5);

{animation_code}
  
  // Fade out background
  yield* bgRef().opacity(0, 0.5);
}});
"""
    
    scene_file.write_text(scene_code)
    logger.info(f"Created enhanced scene: {scene_file}")
    
    return scene_file

