#!/usr/bin/env python3
"""
Agentic Stick Figure Scene Generator

This script takes a video transcript and agentically:
1. Analyzes the transcript to identify key scenes
2. Generates optimized DALL-E prompts for stick figure illustrations
3. Creates consistent stick figure images for each scene
4. Outputs images ready to be stitched with audio

Usage:
    python scripts/stickfigure_scene_generator.py --transcript path/to/transcript.json --output path/to/output/
"""

import os
import json
import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from openai import OpenAI
import httpx

load_dotenv()

# Constants
STICK_FIGURE_STYLE = """minimalist black and white stick figure illustration on a clean white background, 
simple line art style, educational explainer aesthetic, clear and readable, 
stick figure character with round head and simple body made of lines, 
no shading, bold black lines, whiteboard animation style"""

@dataclass
class Scene:
    """Represents a single scene with timing and content"""
    index: int
    start_time: float
    end_time: float
    duration: float
    transcript_text: str
    key_concept: str
    image_prompt: str
    image_path: Optional[str] = None

@dataclass
class ProjectConfig:
    """Configuration for the generation project"""
    transcript_path: str
    output_dir: str
    style_consistency: str = STICK_FIGURE_STYLE
    image_size: str = "1024x1792"  # Vertical for shorts/reels
    num_scenes: int = 8


class StickFigureSceneGenerator:
    """Agentic system for generating stick figure scene illustrations"""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.client = OpenAI()
        self.scenes: List[Scene] = []
        self.transcript_data: Dict = {}
        
        # Ensure output directory exists
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        
    def load_transcript(self) -> Dict:
        """Load transcript from JSON file"""
        print(f"📄 Loading transcript from {self.config.transcript_path}")
        
        with open(self.config.transcript_path, 'r') as f:
            self.transcript_data = json.load(f)
            
        print(f"   Duration: {self.transcript_data.get('duration', 0):.1f}s")
        print(f"   Segments: {len(self.transcript_data.get('segments', []))}")
        
        return self.transcript_data
    
    def analyze_transcript_for_scenes(self) -> List[Dict]:
        """Use GPT to analyze transcript and identify optimal scene breakpoints"""
        print("\n🧠 Analyzing transcript for scene breakdown...")
        
        segments_text = "\n".join([
            f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}"
            for s in self.transcript_data.get('segments', [])
        ])
        
        analysis_prompt = f"""Analyze this video transcript and break it into {self.config.num_scenes} distinct scenes for stick figure illustration.

FULL TRANSCRIPT:
"{self.transcript_data.get('text', '')}"

SEGMENTS WITH TIMESTAMPS:
{segments_text}

For each scene, identify:
1. start_time and end_time (in seconds, matching segment boundaries)
2. key_concept - the main idea being explained (1-2 sentences)
3. visual_description - what should be shown in a stick figure illustration to explain this concept

Return as JSON with this structure:
{{
    "scenes": [
        {{
            "start_time": 0.0,
            "end_time": 6.1,
            "key_concept": "Introduction to feedback system concept",
            "visual_description": "Stick figure with thought bubble containing question mark, looking curious"
        }}
    ]
}}

Make sure:
- Scenes cover the entire transcript duration
- Each scene represents a distinct concept or idea shift
- Visual descriptions are concrete and drawable
- Scenes flow logically from one to the next"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": analysis_prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        analysis = json.loads(response.choices[0].message.content)
        scenes = analysis.get("scenes", [])
        
        print(f"   Identified {len(scenes)} scenes")
        for i, scene in enumerate(scenes):
            print(f"   Scene {i+1}: [{scene['start_time']:.1f}s - {scene['end_time']:.1f}s] {scene['key_concept'][:50]}...")
            
        return scenes
    
    def generate_image_prompts(self, scene_analysis: List[Dict]) -> List[Scene]:
        """Generate optimized DALL-E prompts for each scene"""
        print("\n✍️ Generating optimized image prompts...")
        
        # Get all visual descriptions for consistency planning
        all_descriptions = [s['visual_description'] for s in scene_analysis]
        
        prompt_generation = f"""Generate DALL-E image prompts for a series of {len(scene_analysis)} stick figure illustrations.

IMPORTANT CONSISTENCY REQUIREMENTS:
- All images must use the SAME stick figure character design
- The stick figure should be: simple black lines on white background, round circle head, straight line body, stick limbs
- Style must be consistent across ALL scenes like a cohesive explainer video
- No realistic humans - only minimalist stick figures
- Educational/whiteboard animation aesthetic

BASE STYLE (include in every prompt):
"{self.config.style_consistency}"

SCENES TO ILLUSTRATE:
{json.dumps(scene_analysis, indent=2)}

For each scene, create a detailed DALL-E prompt that:
1. Starts with the base style description
2. Describes the stick figure's pose and action clearly
3. Includes relevant visual elements (icons, symbols, text labels)
4. Maintains the whiteboard/explainer aesthetic
5. Is optimized for DALL-E 3 image generation

Return JSON:
{{
    "prompts": [
        {{
            "scene_index": 0,
            "prompt": "detailed DALL-E prompt here..."
        }}
    ]
}}"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt_generation}],
            response_format={"type": "json_object"},
            temperature=0.8
        )
        
        prompts_data = json.loads(response.choices[0].message.content)
        prompts = prompts_data.get("prompts", [])
        
        # Create Scene objects
        self.scenes = []
        for i, scene_data in enumerate(scene_analysis):
            prompt = next((p['prompt'] for p in prompts if p['scene_index'] == i), None)
            if not prompt:
                # Fallback prompt generation
                prompt = f"{self.config.style_consistency}, {scene_data['visual_description']}"
            
            scene = Scene(
                index=i,
                start_time=scene_data['start_time'],
                end_time=scene_data['end_time'],
                duration=scene_data['end_time'] - scene_data['start_time'],
                transcript_text=scene_data.get('key_concept', ''),
                key_concept=scene_data['key_concept'],
                image_prompt=prompt
            )
            self.scenes.append(scene)
            print(f"   Scene {i+1} prompt: {prompt[:80]}...")
            
        return self.scenes
    
    def generate_scene_image(self, scene: Scene) -> str:
        """Generate a single scene image using DALL-E"""
        print(f"\n🎨 Generating image for Scene {scene.index + 1}...")
        print(f"   Concept: {scene.key_concept[:60]}...")
        
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=scene.image_prompt,
                size=self.config.image_size,
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            revised_prompt = response.data[0].revised_prompt
            
            print(f"   ✓ Image generated")
            print(f"   Revised prompt: {revised_prompt[:80]}...")
            
            # Download and save image
            image_filename = f"scene_{scene.index + 1:02d}.png"
            image_path = os.path.join(self.config.output_dir, image_filename)
            
            # Download image
            with httpx.Client() as client:
                img_response = client.get(image_url)
                with open(image_path, 'wb') as f:
                    f.write(img_response.content)
            
            print(f"   ✓ Saved to {image_path}")
            scene.image_path = image_path
            
            return image_path
            
        except Exception as e:
            print(f"   ✗ Error generating image: {e}")
            raise
    
    def generate_all_images(self) -> List[str]:
        """Generate images for all scenes"""
        print(f"\n🖼️ Generating {len(self.scenes)} scene images...")
        
        image_paths = []
        for scene in self.scenes:
            path = self.generate_scene_image(scene)
            image_paths.append(path)
            
        return image_paths
    
    def save_project_manifest(self) -> str:
        """Save project manifest with all scene data"""
        manifest = {
            "created_at": datetime.now().isoformat(),
            "transcript_path": self.config.transcript_path,
            "output_dir": self.config.output_dir,
            "total_duration": self.transcript_data.get('duration', 0),
            "num_scenes": len(self.scenes),
            "scenes": [asdict(s) for s in self.scenes]
        }
        
        manifest_path = os.path.join(self.config.output_dir, "manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        print(f"\n📋 Saved manifest to {manifest_path}")
        return manifest_path
    
    def run(self) -> Dict:
        """Run the complete generation pipeline"""
        print("=" * 60)
        print("🎬 STICK FIGURE SCENE GENERATOR")
        print("=" * 60)
        
        # Step 1: Load transcript
        self.load_transcript()
        
        # Step 2: Analyze for scenes
        scene_analysis = self.analyze_transcript_for_scenes()
        
        # Step 3: Generate optimized prompts
        self.generate_image_prompts(scene_analysis)
        
        # Step 4: Generate all images
        image_paths = self.generate_all_images()
        
        # Step 5: Save manifest
        manifest_path = self.save_project_manifest()
        
        print("\n" + "=" * 60)
        print("✅ GENERATION COMPLETE")
        print("=" * 60)
        print(f"   Scenes generated: {len(self.scenes)}")
        print(f"   Images saved to: {self.config.output_dir}")
        print(f"   Manifest: {manifest_path}")
        
        return {
            "success": True,
            "scenes": len(self.scenes),
            "images": image_paths,
            "manifest": manifest_path
        }


def main():
    parser = argparse.ArgumentParser(description="Generate stick figure scene illustrations from transcript")
    parser.add_argument("--transcript", required=True, help="Path to transcript JSON file")
    parser.add_argument("--output", required=True, help="Output directory for images")
    parser.add_argument("--scenes", type=int, default=8, help="Number of scenes to generate")
    parser.add_argument("--size", default="1024x1792", help="Image size (default: 1024x1792 for vertical)")
    
    args = parser.parse_args()
    
    config = ProjectConfig(
        transcript_path=args.transcript,
        output_dir=args.output,
        num_scenes=args.scenes,
        image_size=args.size
    )
    
    generator = StickFigureSceneGenerator(config)
    result = generator.run()
    
    return result


if __name__ == "__main__":
    main()
