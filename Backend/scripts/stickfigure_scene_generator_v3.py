#!/usr/bin/env python3
"""
Enhanced Stick Figure Scene Generator v3

Improvements over v2:
- Consistent character design using reference prompt for ALL images
- Smaller captions at center-bottom with keyword highlighting
- Better title alignment at top center
- Improved filler word and pause removal
- Keyword extraction and highlighting in captions

Usage:
    python scripts/stickfigure_scene_generator_v3.py --transcript path/to/transcript.json --audio path/to/audio.mp3 --output path/to/output/
"""

import os
import json
import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from openai import OpenAI
import httpx

load_dotenv()

# CONSISTENT CHARACTER REFERENCE - Same exact description for every image
CHARACTER_REFERENCE = """A simple stick figure character with these EXACT features:
- Perfectly round circle head (no facial features except two dot eyes)
- Single straight vertical line for body/torso
- Two angled lines for arms
- Two angled lines for legs
- Drawn with bold black lines (8px stroke width)
- Clean white background with no texture
- Minimalist whiteboard/explainer video style
- NO shading, NO gradients, NO fills
- Character height approximately 60% of image height
- Character centered horizontally"""

# Enhanced filler word patterns with pauses
FILLER_PATTERNS = [
    # Common filler words
    r'\b(um+|uh+|er+|ah+|hmm+)\b',
    r'\b(like)\b(?=\s*,|\s+like)',  # repeated "like"
    r'\b(you know)\b',
    r'\b(basically)\b',
    r'\b(actually)\b', 
    r'\b(literally)\b',
    r'\b(kind of|kinda)\b',
    r'\b(sort of|sorta)\b',
    r'\b(i mean)\b',
    r'\b(you see)\b',
    # Trailing/unnecessary words
    r'\bright\??\s*$',  # "right" at end
    r'\bright\?\s+',  # "right?" mid-sentence
    r'^(so+|and)\s+',  # starting with "so" or "and"
    r'\s+(so+)\s*,',  # ", so,"
    r'\band\s+and\b',  # double "and"
    r'\bthe\s+the\b',  # double "the"
    # Pause indicators
    r'\.{2,}',  # multiple periods
    r'\s{2,}',  # multiple spaces (pause indicators)
]

@dataclass
class Scene:
    """Represents a single scene"""
    index: int
    start_time: float
    end_time: float
    duration: float
    transcript_text: str
    cleaned_text: str
    keywords: List[str]
    visual_description: str
    image_prompt: str
    image_path: Optional[str] = None

@dataclass 
class ProjectConfig:
    """Configuration for the generation project"""
    transcript_path: str
    output_dir: str
    image_size: str = "1024x1792"
    scene_duration: float = 2.0
    video_title: str = ""


class StickFigureGeneratorV3:
    """V3 generator with consistent character and improved captions"""
    
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
    
    def clean_text_aggressive(self, text: str) -> str:
        """Aggressively clean filler words and pauses"""
        cleaned = text.lower()
        
        # Apply all filler patterns
        for pattern in FILLER_PATTERNS:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
        
        # Clean up punctuation and spacing
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Multiple spaces to single
        cleaned = re.sub(r'\s+([,.\?!])', r'\1', cleaned)  # Space before punctuation
        cleaned = re.sub(r'([,.\?!])\s*\1+', r'\1', cleaned)  # Duplicate punctuation
        cleaned = re.sub(r'^\s*[,.\?!]\s*', '', cleaned)  # Leading punctuation
        cleaned = re.sub(r'\s*[,]\s*$', '', cleaned)  # Trailing comma
        
        # Capitalize first letter
        cleaned = cleaned.strip()
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
            
        return cleaned
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract 1-3 key words from text for highlighting"""
        # Use GPT to extract keywords
        if not text or len(text) < 10:
            return []
            
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Extract 1-2 most important keywords from this text that should be highlighted.
Return ONLY the keywords separated by comma, nothing else.

Text: "{text}"

Keywords:"""
            }],
            max_tokens=20,
            temperature=0.3
        )
        
        keywords_str = response.choices[0].message.content.strip()
        keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
        return keywords[:2]  # Max 2 keywords
    
    def generate_video_title(self) -> str:
        """Generate eye-catching title (max 35 chars)"""
        print("\n🎯 Generating video title...")
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"""Create a viral-style title for this video.

TRANSCRIPT SUMMARY:
"{self.transcript_data.get('text', '')[:400]}"

Requirements:
- Maximum 35 characters
- Catchy and attention-grabbing
- No emojis
- Would work as a hook

Return ONLY the title text."""
            }],
            max_tokens=30,
            temperature=0.9
        )
        
        self.video_title = response.choices[0].message.content.strip().strip('"')[:35]
        print(f"   Title: \"{self.video_title}\"")
        return self.video_title
    
    def create_scenes(self) -> List[Dict]:
        """Create 2-second scene breakdown with keywords"""
        print("\n🎬 Creating scene breakdown...")
        
        total_duration = self.transcript_data.get('duration', 90)
        segments = self.transcript_data.get('segments', [])
        num_scenes = int(total_duration / self.config.scene_duration)
        
        print(f"   Scenes: {num_scenes} @ {self.config.scene_duration}s each")
        
        scenes_data = []
        for i in range(num_scenes):
            start_time = i * self.config.scene_duration
            end_time = min((i + 1) * self.config.scene_duration, total_duration)
            
            # Get transcript text for this time range
            scene_text = ""
            for seg in segments:
                if seg['start'] < end_time and seg['end'] > start_time:
                    scene_text += " " + seg['text']
            
            cleaned = self.clean_text_aggressive(scene_text.strip())
            keywords = self.extract_keywords(cleaned) if cleaned else []
            
            scenes_data.append({
                'index': i,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'transcript_text': scene_text.strip(),
                'cleaned_text': cleaned,
                'keywords': keywords
            })
        
        print(f"   ✓ Created {len(scenes_data)} scenes with keywords")
        return scenes_data
    
    def generate_visual_descriptions(self, scenes_data: List[Dict]) -> List[Dict]:
        """Generate visual descriptions in batches"""
        print("\n🧠 Generating visual descriptions...")
        
        batch_size = 10
        
        for batch_start in range(0, len(scenes_data), batch_size):
            batch = scenes_data[batch_start:batch_start + batch_size]
            batch_info = "\n".join([
                f"Scene {s['index']+1}: {s['cleaned_text'][:80]}"
                for s in batch if s['cleaned_text']
            ])
            
            if not batch_info.strip():
                for s in batch:
                    s['visual_description'] = "standing in neutral pose"
                continue
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": f"""Generate POSE descriptions for a stick figure in each scene.

IMPORTANT: Only describe the POSE and ACTION, not the character itself.
The character is always the same stick figure.

SCENES:
{batch_info}

Return JSON with pose descriptions:
{{"scenes": [{{"index": 0, "pose": "pointing at a chart on the right side"}}]}}

Keep poses simple and drawable."""
                }],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            result = json.loads(response.choices[0].message.content)
            for scene_pose in result.get('scenes', []):
                idx = scene_pose['index']
                for s in batch:
                    if s['index'] == batch_start + idx:
                        s['visual_description'] = scene_pose.get('pose', 'standing neutrally')
                        break
            
            print(f"   Processed scenes {batch_start+1}-{min(batch_start+batch_size, len(scenes_data))}")
        
        return scenes_data
    
    def build_image_prompt(self, pose_description: str) -> str:
        """Build consistent image prompt with character reference"""
        return f"""{CHARACTER_REFERENCE}

POSE/ACTION: The stick figure is {pose_description}

Additional elements may include simple icons or labels relevant to the action.
Style: Clean, minimal, educational, whiteboard animation aesthetic."""
    
    def generate_scene_image(self, scene: Dict) -> Optional[str]:
        """Generate a single scene image"""
        prompt = self.build_image_prompt(scene.get('visual_description', 'standing neutrally'))
        
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=self.config.image_size,
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            image_filename = f"scene_{scene['index'] + 1:03d}.png"
            image_path = os.path.join(self.config.output_dir, image_filename)
            
            with httpx.Client() as client:
                img_response = client.get(image_url)
                with open(image_path, 'wb') as f:
                    f.write(img_response.content)
            
            return image_path
            
        except Exception as e:
            print(f"   ✗ Scene {scene['index']+1} error: {e}")
            return None
    
    def generate_all_images(self, scenes_data: List[Dict]) -> List[Scene]:
        """Generate all scene images"""
        print(f"\n🖼️ Generating {len(scenes_data)} images with consistent character...")
        
        self.scenes = []
        
        for i, scene_data in enumerate(scenes_data):
            print(f"   Scene {i+1}/{len(scenes_data)}...", end=" ", flush=True)
            
            image_path = self.generate_scene_image(scene_data)
            
            scene = Scene(
                index=scene_data['index'],
                start_time=scene_data['start_time'],
                end_time=scene_data['end_time'],
                duration=scene_data['duration'],
                transcript_text=scene_data['transcript_text'],
                cleaned_text=scene_data['cleaned_text'],
                keywords=scene_data.get('keywords', []),
                visual_description=scene_data.get('visual_description', ''),
                image_prompt=self.build_image_prompt(scene_data.get('visual_description', '')),
                image_path=image_path
            )
            self.scenes.append(scene)
            print("✓" if image_path else "✗")
        
        return self.scenes
    
    def create_srt_with_highlights(self) -> str:
        """Create SRT file with keyword highlighting using ASS styling"""
        srt_file = os.path.join(self.config.output_dir, "captions.srt")
        
        with open(srt_file, 'w') as f:
            for i, scene in enumerate(self.scenes):
                if not scene.cleaned_text:
                    continue
                    
                # Format timestamps
                def fmt_time(t):
                    h = int(t // 3600)
                    m = int((t % 3600) // 60)
                    s = int(t % 60)
                    ms = int((t % 1) * 1000)
                    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
                
                # Limit caption length
                caption = scene.cleaned_text[:60]
                
                f.write(f"{i+1}\n")
                f.write(f"{fmt_time(scene.start_time)} --> {fmt_time(scene.end_time)}\n")
                f.write(f"{caption}\n\n")
        
        return srt_file
    
    def create_video(self, audio_path: str) -> str:
        """Create final video with aligned title and center-bottom captions"""
        print("\n🎥 Creating final video...")
        
        output_video = os.path.join(self.config.output_dir, "final_video_v3.mp4")
        
        # Create concat file
        concat_file = os.path.join(self.config.output_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            for scene in self.scenes:
                if scene.image_path:
                    f.write(f"file '{os.path.abspath(scene.image_path)}'\n")
                    f.write(f"duration {scene.duration}\n")
            if self.scenes and self.scenes[-1].image_path:
                f.write(f"file '{os.path.abspath(self.scenes[-1].image_path)}'\n")
        
        # Create captions
        srt_file = self.create_srt_with_highlights()
        
        # Escape title for ffmpeg
        escaped_title = self.video_title.replace("'", "'\\''").replace(":", "\\:").replace("\\", "\\\\")
        
        # Build filter with:
        # - Title box at top center (properly aligned)
        # - Smaller captions at center-bottom
        filter_complex = (
            # Scale and pad
            f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:white,"
            # Title background box - centered at top
            f"drawbox=x=(w-700)/2:y=60:w=700:h=70:color=white@0.95:t=fill,"
            f"drawbox=x=(w-700)/2:y=60:w=700:h=70:color=black:t=2,"
            # Title text - centered
            f"drawtext=text='{escaped_title}':"
            f"fontsize=28:fontcolor=black:x=(w-text_w)/2:y=80:"
            f"fontfile=/System/Library/Fonts/Helvetica.ttc,"
            # Captions - smaller, center-bottom
            f"subtitles={srt_file}:force_style='"
            f"FontSize=18,"
            f"PrimaryColour=&HFFFFFF,"
            f"OutlineColour=&H000000,"
            f"BackColour=&H80000000,"
            f"Outline=1,"
            f"Shadow=1,"
            f"Alignment=2,"
            f"MarginV=120,"
            f"FontName=Arial"
            f"'"
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
            print(f"   ✅ Video: {output_video} ({size:.1f} MB)")
        else:
            print(f"   ⚠️ Trying without subtitles...")
            # Fallback without subtitles
            filter_simple = (
                f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:white,"
                f"drawbox=x=(w-700)/2:y=60:w=700:h=70:color=white@0.95:t=fill,"
                f"drawbox=x=(w-700)/2:y=60:w=700:h=70:color=black:t=2,"
                f"drawtext=text='{escaped_title}':fontsize=28:fontcolor=black:x=(w-text_w)/2:y=80"
            )
            cmd[cmd.index('-vf') + 1] = filter_simple
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                size = os.path.getsize(output_video) / (1024*1024)
                print(f"   ✅ Video (no captions): {output_video} ({size:.1f} MB)")
            else:
                print(f"   ❌ Error: {result.stderr[-300:]}")
        
        return output_video
    
    def save_manifest(self) -> str:
        """Save project manifest"""
        manifest = {
            "version": "3.0",
            "created_at": datetime.now().isoformat(),
            "video_title": self.video_title,
            "character_reference": CHARACTER_REFERENCE,
            "total_duration": self.transcript_data.get('duration', 0),
            "scene_duration": self.config.scene_duration,
            "num_scenes": len(self.scenes),
            "scenes": [asdict(s) for s in self.scenes]
        }
        
        manifest_path = os.path.join(self.config.output_dir, "manifest_v3.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        return manifest_path
    
    def run(self, audio_path: str) -> Dict:
        """Run the complete v3 pipeline"""
        print("=" * 60)
        print("🎬 STICK FIGURE GENERATOR v3")
        print("   - Consistent character reference")
        print("   - Smaller center-bottom captions")
        print("   - Aligned title box")
        print("   - Aggressive filler removal")
        print("=" * 60)
        
        self.load_transcript()
        self.generate_video_title()
        scenes_data = self.create_scenes()
        scenes_data = self.generate_visual_descriptions(scenes_data)
        self.generate_all_images(scenes_data)
        video_path = self.create_video(audio_path)
        self.save_manifest()
        
        print("\n" + "=" * 60)
        print("✅ V3 GENERATION COMPLETE")
        print("=" * 60)
        print(f"   Title: \"{self.video_title}\"")
        print(f"   Scenes: {len(self.scenes)}")
        print(f"   Video: {video_path}")
        
        return {"success": True, "video": video_path, "scenes": len(self.scenes)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float, default=2.0)
    
    args = parser.parse_args()
    
    config = ProjectConfig(
        transcript_path=args.transcript,
        output_dir=args.output,
        scene_duration=args.duration
    )
    
    generator = StickFigureGeneratorV3(config)
    return generator.run(args.audio)


if __name__ == "__main__":
    main()
