#!/usr/bin/env python3
"""
Generate Video from Template Script
===================================
Generates a complete video from a template-based script:
1. Generates voice audio using TTS
2. Creates animated visuals for each beat
3. Composes everything together
4. Modular design for adding effects incrementally

Usage:
    python Backend/scripts/generate_video_from_template_script.py \
      --script Backend/data/scripts/thermodynamics_ice_floats.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add TTS folder to path
tts_folder = Path("/Users/isaiahdupree/Documents/Software/TTS")
if str(tts_folder) not in sys.path:
    sys.path.insert(0, str(tts_folder))

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Import TTS API
try:
    from call_indextts2_api import call_indextts2_api
    TTS_AVAILABLE = True
except ImportError:
    logger.warning("TTS API not available. Install gradio_client: pip install gradio_client")
    TTS_AVAILABLE = False


class VideoGenerator:
    """Modular video generator that can be extended with more effects"""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("Backend/data/generated_videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.audio_dir = self.output_dir / "audio"
        self.audio_dir.mkdir(exist_ok=True)
        
        self.visuals_dir = self.output_dir / "visuals"
        self.visuals_dir.mkdir(exist_ok=True)
        
        self.temp_dir = self.output_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def find_voice_reference(self, preferred: str = None) -> Optional[Path]:
        """Find voice reference from TTS folder"""
        tts_folder = Path("/Users/isaiahdupree/Documents/Software/TTS")
        
        search_paths = [
            tts_folder / "audio_samples",
            tts_folder / "training_data",
            tts_folder / "isolated_audio",
        ]
        
        if preferred:
            preferred_path = tts_folder / preferred
            if preferred_path.exists() and preferred_path.suffix.lower() in ['.wav', '.mp3']:
                return preferred_path
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            audio_files = list(search_path.glob("*.wav")) + list(search_path.glob("*.mp3"))
            if audio_files:
                audio_files.sort(key=lambda p: p.stat().st_size, reverse=True)
                return audio_files[0]
        
        return None
    
    def generate_voice_audio(self, text: str, voice_ref: Path = None) -> Optional[Path]:
        """Generate voice audio using TTS"""
        if not TTS_AVAILABLE:
            logger.error("TTS not available")
            return None
        
        logger.info(f"🎤 Generating voice audio ({len(text)} chars)...")
        
        # Find voice reference if not provided
        if not voice_ref:
            voice_ref = self.find_voice_reference()
            if not voice_ref:
                logger.error("❌ No voice reference found")
                return None
        
        logger.info(f"   Using voice: {voice_ref.name}")
        
        # Generate audio
        output_path = self.audio_dir / f"voice_{uuid4().hex[:8]}.wav"
        
        try:
            # Call TTS API (signature: voice_reference, text, output_file)
            result = call_indextts2_api(
                voice_reference=str(voice_ref),
                text=text,
                output_file=str(output_path),
            )
            
            if result and output_path.exists():
                size_mb = output_path.stat().st_size / 1024 / 1024
                logger.success(f"✅ Voice audio generated: {size_mb:.2f} MB")
                return output_path
            else:
                logger.error("❌ TTS generation failed")
                return None
                
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
            return None
    
    def create_visual_for_beat(
        self,
        beat: Dict[str, Any],
        beat_index: int,
        style: str = "fade"
    ) -> Optional[Path]:
        """Create animated visual for a beat"""
        logger.info(f"🎨 Creating visual for beat {beat_index + 1}: {beat.get('role', 'unknown')}")
        
        text = beat.get("text", "")
        start_sec = beat.get("start_sec", 0)
        end_sec = beat.get("end_sec", 0)
        duration = end_sec - start_sec
        
        if duration <= 0:
            logger.warning(f"⚠️  Invalid duration for beat {beat_index}")
            return None
        
        # For now, use FFmpeg to create simple animated text
        # Later we can add Motion Canvas animations
        output_path = self.visuals_dir / f"beat_{beat_index:02d}_{beat.get('role', 'unknown')}.mp4"
        
        # Escape text for FFmpeg
        escaped_text = text.replace(":", "\\:").replace("'", "\\'").replace("[", "\\[").replace("]", "\\]")
        
        # Create animated text video
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"color=c=#1a1a1a:s=1920x1080:d={duration}:r=30",
            "-vf", (
                f"drawtext=text='{escaped_text}':"
                f"fontsize=64:"
                f"fontcolor=white:"
                f"x=(w-text_w)/2:"
                f"y=(h-text_h)/2:"
                f"box=1:boxcolor=black@0.5:boxborderw=10:"
                f"fontfile=/System/Library/Fonts/Helvetica.ttc"
            ),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            str(output_path),
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.success(f"✅ Visual created: {output_path.name}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFmpeg failed: {e.stderr[:200]}")
            return None
        except FileNotFoundError:
            logger.error("❌ FFmpeg not found")
            return None
    
    def compose_final_video(
        self,
        audio_path: Path,
        visual_paths: List[Path],
        output_path: Path,
        script_data: Dict[str, Any]
    ) -> bool:
        """Compose final video from audio and visuals"""
        logger.info("🎬 Composing final video...")
        
        if not audio_path.exists():
            logger.error(f"❌ Audio not found: {audio_path}")
            return False
        
        if not visual_paths:
            logger.error("❌ No visuals to compose")
            return False
        
        # Create concat file for visuals
        concat_file = self.temp_dir / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for visual_path in visual_paths:
                if visual_path.exists():
                    f.write(f"file '{visual_path.absolute()}'\n")
        
        # First, concatenate all visuals
        combined_visuals = self.temp_dir / "combined_visuals.mp4"
        cmd_concat = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(combined_visuals),
        ]
        
        try:
            subprocess.run(cmd_concat, capture_output=True, text=True, check=True)
            logger.info("✅ Visuals concatenated")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to concatenate visuals: {e.stderr[:200]}")
            return False
        
        # Now combine audio and video
        cmd_final = [
            "ffmpeg",
            "-y",
            "-i", str(combined_visuals),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",  # Match shortest stream
            "-map", "0:v:0",
            "-map", "1:a:0",
            str(output_path),
        ]
        
        try:
            subprocess.run(cmd_final, capture_output=True, text=True, check=True)
            
            size_mb = output_path.stat().st_size / 1024 / 1024
            logger.success(f"✅ Final video created: {size_mb:.2f} MB")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to compose video: {e.stderr[:200]}")
            return False
    
    def generate(self, script_path: Path, voice_ref: Path = None) -> Optional[Path]:
        """Generate complete video from script"""
        logger.info("=" * 80)
        logger.info("🎬 Video Generation Pipeline")
        logger.info("=" * 80)
        logger.info("")
        
        # Load script
        logger.info(f"📄 Loading script: {script_path.name}")
        with open(script_path, 'r') as f:
            script_data = json.load(f)
        
        script_text = script_data.get("script", "")
        beats = script_data.get("beats", [])
        
        logger.info(f"   Duration: {script_data.get('estimated_duration', 0)}s")
        logger.info(f"   Beats: {len(beats)}")
        logger.info("")
        
        # Step 1: Generate voice audio
        logger.info("Step 1: Voice Generation")
        logger.info("-" * 80)
        audio_path = self.generate_voice_audio(script_text, voice_ref)
        if not audio_path:
            logger.error("❌ Voice generation failed")
            return None
        logger.info("")
        
        # Step 2: Create visuals for each beat
        logger.info("Step 2: Visual Generation")
        logger.info("-" * 80)
        visual_paths = []
        for i, beat in enumerate(beats):
            visual_path = self.create_visual_for_beat(beat, i)
            if visual_path:
                visual_paths.append(visual_path)
        logger.info("")
        
        if not visual_paths:
            logger.error("❌ No visuals created")
            return None
        
        # Step 3: Compose final video
        logger.info("Step 3: Video Composition")
        logger.info("-" * 80)
        output_path = self.output_dir / f"video_{uuid4().hex[:8]}.mp4"
        
        success = self.compose_final_video(
            audio_path=audio_path,
            visual_paths=visual_paths,
            output_path=output_path,
            script_data=script_data
        )
        
        if not success:
            logger.error("❌ Video composition failed")
            return None
        
        logger.info("")
        logger.info("=" * 80)
        logger.success("✅ Video Generation Complete!")
        logger.info("=" * 80)
        logger.info(f"📹 Output: {output_path}")
        logger.info(f"📊 Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        return output_path


def open_video(video_path: Path):
    """Open video file"""
    if not video_path.exists():
        logger.error(f"Video not found: {video_path}")
        return False
    
    try:
        subprocess.run(["open", str(video_path)], check=True)
        logger.info(f"🎬 Opened video: {video_path}")
        return True
    except Exception as e:
        logger.warning(f"Could not open video: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate video from template script"
    )
    parser.add_argument(
        "--script",
        type=Path,
        required=True,
        help="Path to script JSON file"
    )
    parser.add_argument(
        "--voice",
        type=Path,
        help="Path to voice reference file (optional)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output video path (optional)"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open video after generation"
    )
    
    args = parser.parse_args()
    
    if not args.script.exists():
        logger.error(f"Script not found: {args.script}")
        return 1
    
    # Generate video
    generator = VideoGenerator()
    video_path = generator.generate(args.script, args.voice)
    
    if not video_path:
        logger.error("Video generation failed")
        return 1
    
    # Open video if requested
    if args.open:
        open_video(video_path)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

