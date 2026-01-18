#!/usr/bin/env python3
"""
Enhanced Stick Figure Scene Generator v2

Improvements:
- 2-second scene intervals for more dynamic visuals
- Filler word removal from transcript
- Captions overlay on video
- Eye-catching title at top with white rounded background
- Better scene detection based on content changes

Usage:
    python scripts/stickfigure_scene_generator_v2.py --transcript path/to/transcript.json --output path/to/output/
"""

import os
import json
import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from openai import OpenAI
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

# Constants
STICK_FIGURE_STYLE = """minimalist black and white stick figure illustration on a clean white background, 
simple line art style, educational explainer aesthetic, clear and readable, 
stick figure character with round head and simple body made of lines, 
no shading, bold black lines, whiteboard animation style"""

FILLER_WORDS = [
    r'\bum\b', r'\buh\b', r'\blike\b', r'\byou know\b', r'\bbasically\b',
    r'\bactually\b', r'\bliterally\b', r'\bkind of\b', r'\bsort of\b',
    r'\bright\?', r'\bright\b', r'\bso\b(?=\s*,)', r'\band\s+and\b'
]

@dataclass
class Scene:
    """Represents a single 2-second scene"""
    index: int
    start_time: float
    end_time: float
    duration: float
    transcript_text: str
    cleaned_text: str
    visual_description: str
    image_prompt: str
    image_path: Optional[str] = None

@dataclass 
class ProjectConfig:
    """Configuration for the generation project"""
    transcript_path: str
    output_dir: str
    style_consistency: str = STICK_FIGURE_STYLE
    image_size: str = "1024x1792"
    scene_duration: float = 2.0  # 2 seconds per scene
    video_title: str = ""  # Will be generated


class EnhancedStickFigureGenerator:
    """Enhanced system for generating stick figure scene illustrations"""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.client = OpenAI()
        self.scenes: List[Scene] = []
        self.transcript_data: Dict = {}
        self.video_title: str = ""
        
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        
    def load_transcript(self) -> Dict:
        """Load transcript from JSON file"""
        print(f"📄 Loading transcript from {self.config.transcript_path}")
        
        with open(self.config.transcript_path, 'r') as f:
            self.transcript_data = json.load(f)
            
        print(f"   Duration: {self.transcript_data.get('duration', 0):.1f}s")
        return self.transcript_data
    
    def clean_filler_words(self, text: str) -> str:
        """Remove filler words and clean up transcript"""
        cleaned = text
        for pattern in FILLER_WORDS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        # Clean up multiple spaces and punctuation
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\s+([,.])', r'\1', cleaned)
        cleaned = re.sub(r'([,.])\s*\1+', r'\1', cleaned)
        return cleaned.strip()
    
    def generate_video_title(self) -> str:
        """Generate eye-catching title (max 40 chars) for the video"""
        print("\n🎯 Generating eye-catching video title...")
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"""Create an eye-catching, viral-style title for this video transcript.

TRANSCRIPT:
"{self.transcript_data.get('text', '')[:500]}"

Requirements:
- Maximum 40 characters
- Catchy and attention-grabbing
- Summarizes the main concept
- Would work as a hook at the top of a TikTok/Reel

Return ONLY the title text, nothing else."""
            }],
            max_tokens=50,
            temperature=0.9
        )
        
        self.video_title = response.choices[0].message.content.strip().strip('"')[:40]
        print(f"   Title: \"{self.video_title}\"")
        return self.video_title
    
    def create_2_second_scenes(self) -> List[Dict]:
        """Break transcript into 2-second scenes with content analysis"""
        print("\n🎬 Creating 2-second scene breakdown...")
        
        total_duration = self.transcript_data.get('duration', 90)
        segments = self.transcript_data.get('segments', [])
        
        # Calculate number of 2-second scenes
        num_scenes = int(total_duration / self.config.scene_duration)
        print(f"   Total duration: {total_duration:.1f}s")
        print(f"   Scene duration: {self.config.scene_duration}s")
        print(f"   Number of scenes: {num_scenes}")
        
        # Create time-based scenes and map transcript text
        scenes_data = []
        for i in range(num_scenes):
            start_time = i * self.config.scene_duration
            end_time = min((i + 1) * self.config.scene_duration, total_duration)
            
            # Find transcript text for this time range
            scene_text = ""
            for seg in segments:
                seg_start = seg['start']
                seg_end = seg['end']
                # Check if segment overlaps with scene
                if seg_start < end_time and seg_end > start_time:
                    scene_text += " " + seg['text']
            
            cleaned_text = self.clean_filler_words(scene_text.strip())
            
            scenes_data.append({
                'index': i,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'transcript_text': scene_text.strip(),
                'cleaned_text': cleaned_text
            })
        
        return scenes_data
    
    def generate_visual_descriptions(self, scenes_data: List[Dict]) -> List[Dict]:
        """Use GPT to generate visual descriptions for each scene"""
        print("\n🧠 Generating visual descriptions for all scenes...")
        
        # Batch scenes for efficiency (groups of 10)
        batch_size = 10
        all_scenes = []
        
        for batch_start in range(0, len(scenes_data), batch_size):
            batch = scenes_data[batch_start:batch_start + batch_size]
            batch_info = "\n".join([
                f"Scene {s['index']+1} [{s['start_time']:.1f}s-{s['end_time']:.1f}s]: {s['cleaned_text'][:100]}"
                for s in batch
            ])
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": f"""Generate visual descriptions for these video scenes to be illustrated with stick figures.

SCENES:
{batch_info}

For each scene, describe what the stick figure should be doing to visually explain the concept.
Keep descriptions concrete and drawable. Each should be unique but maintain a consistent character.

Return JSON:
{{
    "scenes": [
        {{"index": 0, "visual": "Stick figure pointing at a question mark bubble"}},
        ...
    ]
}}"""
                }],
                response_format={"type": "json_object"},
                temperature=0.8
            )
            
            result = json.loads(response.choices[0].message.content)
            for scene_visual in result.get('scenes', []):
                idx = scene_visual['index']
                for s in batch:
                    if s['index'] == batch_start + idx:
                        s['visual_description'] = scene_visual['visual']
                        break
            
            all_scenes.extend(batch)
            print(f"   Processed scenes {batch_start+1}-{min(batch_start+batch_size, len(scenes_data))}")
        
        return all_scenes
    
    def generate_image_prompt(self, scene: Dict) -> str:
        """Generate optimized DALL-E prompt for a scene"""
        visual = scene.get('visual_description', 'Stick figure explaining a concept')
        return f"{self.config.style_consistency}. {visual}"
    
    def generate_scene_image(self, scene: Dict) -> str:
        """Generate a single scene image using DALL-E"""
        prompt = self.generate_image_prompt(scene)
        
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=self.config.image_size,
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            
            # Download and save image
            image_filename = f"scene_{scene['index'] + 1:03d}.png"
            image_path = os.path.join(self.config.output_dir, image_filename)
            
            with httpx.Client() as client:
                img_response = client.get(image_url)
                with open(image_path, 'wb') as f:
                    f.write(img_response.content)
            
            return image_path
            
        except Exception as e:
            print(f"   ✗ Error generating scene {scene['index']+1}: {e}")
            return None
    
    def generate_all_images(self, scenes_data: List[Dict]) -> List[Scene]:
        """Generate images for all scenes with progress tracking"""
        print(f"\n🖼️ Generating {len(scenes_data)} scene images...")
        
        self.scenes = []
        
        # Generate images sequentially (DALL-E rate limits)
        for i, scene_data in enumerate(scenes_data):
            print(f"   Generating scene {i+1}/{len(scenes_data)}...", end=" ")
            
            image_path = self.generate_scene_image(scene_data)
            
            scene = Scene(
                index=scene_data['index'],
                start_time=scene_data['start_time'],
                end_time=scene_data['end_time'],
                duration=scene_data['duration'],
                transcript_text=scene_data['transcript_text'],
                cleaned_text=scene_data['cleaned_text'],
                visual_description=scene_data.get('visual_description', ''),
                image_prompt=self.generate_image_prompt(scene_data),
                image_path=image_path
            )
            self.scenes.append(scene)
            
            if image_path:
                print("✓")
            else:
                print("✗")
        
        return self.scenes
    
    def create_video_with_overlays(self, audio_path: str) -> str:
        """Create final video with captions and title overlay"""
        print("\n🎥 Creating video with overlays...")
        
        output_video = os.path.join(self.config.output_dir, "final_video_v2.mp4")
        
        # Create concat file
        concat_file = os.path.join(self.config.output_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            for scene in self.scenes:
                if scene.image_path:
                    f.write(f"file '{os.path.abspath(scene.image_path)}'\n")
                    f.write(f"duration {scene.duration}\n")
            # Last image repeat
            if self.scenes and self.scenes[-1].image_path:
                f.write(f"file '{os.path.abspath(self.scenes[-1].image_path)}'\n")
        
        # Create captions file (SRT format)
        srt_file = os.path.join(self.config.output_dir, "captions.srt")
        with open(srt_file, 'w') as f:
            for i, scene in enumerate(self.scenes):
                if scene.cleaned_text:
                    start_h = int(scene.start_time // 3600)
                    start_m = int((scene.start_time % 3600) // 60)
                    start_s = int(scene.start_time % 60)
                    start_ms = int((scene.start_time % 1) * 1000)
                    
                    end_h = int(scene.end_time // 3600)
                    end_m = int((scene.end_time % 3600) // 60)
                    end_s = int(scene.end_time % 60)
                    end_ms = int((scene.end_time % 1) * 1000)
                    
                    f.write(f"{i+1}\n")
                    f.write(f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> ")
                    f.write(f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n")
                    # Limit caption length
                    caption = scene.cleaned_text[:80]
                    f.write(f"{caption}\n\n")
        
        # Escape title for ffmpeg
        escaped_title = self.video_title.replace("'", "'\\''").replace(":", "\\:")
        
        # Build complex ffmpeg filter for title box and captions
        filter_complex = (
            f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:white,"
            f"drawbox=x=(w-800)/2:y=50:w=800:h=80:color=white@0.9:t=fill,"
            f"drawbox=x=(w-800)/2:y=50:w=800:h=80:color=black:t=3,"
            f"drawtext=text='{escaped_title}':fontsize=36:fontcolor=black:x=(w-text_w)/2:y=75,"
            f"subtitles={srt_file}:force_style='FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Alignment=2,MarginV=200'"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-i', audio_path,
            '-vf', filter_complex,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-shortest',
            '-pix_fmt', 'yuv420p',
            output_video
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            size = os.path.getsize(output_video) / (1024*1024)
            print(f"   ✅ Video created: {output_video}")
            print(f"   Size: {size:.1f} MB")
        else:
            print(f"   ❌ FFmpeg error: {result.stderr[-500:]}")
            # Try simpler version without subtitles
            print("   Trying without subtitles filter...")
            filter_simple = (
                f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:white,"
                f"drawbox=x=(w-800)/2:y=50:w=800:h=80:color=white@0.9:t=fill,"
                f"drawtext=text='{escaped_title}':fontsize=36:fontcolor=black:x=(w-text_w)/2:y=75"
            )
            cmd[cmd.index('-vf') + 1] = filter_simple
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ Video created (without captions)")
        
        return output_video
    
    def save_manifest(self) -> str:
        """Save project manifest"""
        manifest = {
            "created_at": datetime.now().isoformat(),
            "video_title": self.video_title,
            "total_duration": self.transcript_data.get('duration', 0),
            "scene_duration": self.config.scene_duration,
            "num_scenes": len(self.scenes),
            "scenes": [asdict(s) for s in self.scenes]
        }
        
        manifest_path = os.path.join(self.config.output_dir, "manifest_v2.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        print(f"\n📋 Saved manifest to {manifest_path}")
        return manifest_path
    
    def run(self, audio_path: str) -> Dict:
        """Run the complete enhanced generation pipeline"""
        print("=" * 60)
        print("🎬 ENHANCED STICK FIGURE GENERATOR v2")
        print("=" * 60)
        
        # Step 1: Load transcript
        self.load_transcript()
        
        # Step 2: Generate catchy title
        self.generate_video_title()
        
        # Step 3: Create 2-second scene breakdown
        scenes_data = self.create_2_second_scenes()
        
        # Step 4: Generate visual descriptions
        scenes_data = self.generate_visual_descriptions(scenes_data)
        
        # Step 5: Generate all images
        self.generate_all_images(scenes_data)
        
        # Step 6: Create video with overlays
        video_path = self.create_video_with_overlays(audio_path)
        
        # Step 7: Save manifest
        self.save_manifest()
        
        print("\n" + "=" * 60)
        print("✅ ENHANCED GENERATION COMPLETE")
        print("=" * 60)
        print(f"   Title: \"{self.video_title}\"")
        print(f"   Scenes: {len(self.scenes)}")
        print(f"   Video: {video_path}")
        
        return {
            "success": True,
            "title": self.video_title,
            "scenes": len(self.scenes),
            "video": video_path
        }


def main():
    parser = argparse.ArgumentParser(description="Enhanced stick figure scene generator")
    parser.add_argument("--transcript", required=True, help="Path to transcript JSON")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--duration", type=float, default=2.0, help="Scene duration in seconds")
    
    args = parser.parse_args()
    
    config = ProjectConfig(
        transcript_path=args.transcript,
        output_dir=args.output,
        scene_duration=args.duration
    )
    
    generator = EnhancedStickFigureGenerator(config)
    result = generator.run(args.audio)
    
    return result


if __name__ == "__main__":
    main()
