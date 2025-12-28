#!/usr/bin/env python3
"""
Generate Explainer Video Using TTS Folder Resources
===================================================
Generate explainer videos using resources from the TTS folder:
- Uses call_indextts2_api.py directly
- Finds voice references from audio_samples or training_data
- Generates complete explainer video

Usage:
    python Backend/scripts/generate_explainer_with_tts_folder.py \
      --topic "Thermodynamics" \
      --duration 60
"""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add TTS folder to path
tts_folder = Path("/Users/isaiahdupree/Documents/Software/TTS")
if str(tts_folder) not in sys.path:
    sys.path.insert(0, str(tts_folder))

from loguru import logger

# Import TTS API
try:
    from call_indextts2_api import call_indextts2_api
    TTS_AVAILABLE = True
except ImportError:
    logger.warning("TTS API not available. Install gradio_client: pip install gradio_client")
    TTS_AVAILABLE = False


def find_voice_reference(tts_folder: Path, preferred: str = None) -> Path:
    """
    Find a voice reference file from TTS folder.
    
    Searches in:
    1. audio_samples/ (preferred - real voice samples)
    2. training_data/ (training audio)
    3. isolated_audio/ (if available)
    """
    logger.info("🔍 Searching for voice reference in TTS folder...")
    
    # Priority order
    search_paths = [
        tts_folder / "audio_samples",
        tts_folder / "training_data",
        tts_folder / "isolated_audio",
        tts_folder / "refined_audio",
    ]
    
    # If preferred voice specified, try that first
    if preferred:
        preferred_path = tts_folder / preferred
        if preferred_path.exists() and preferred_path.suffix.lower() in ['.wav', '.mp3']:
            logger.info(f"✅ Using preferred voice: {preferred_path.name}")
            return preferred_path
    
    # Search in priority order
    for search_path in search_paths:
        if not search_path.exists():
            continue
        
        # Find audio files
        audio_files = list(search_path.glob("*.wav")) + list(search_path.glob("*.mp3"))
        
        if audio_files:
            # Prefer longer files (better for voice cloning)
            audio_files.sort(key=lambda p: p.stat().st_size, reverse=True)
            chosen = audio_files[0]
            logger.info(f"✅ Found voice reference: {chosen.name} ({chosen.parent.name})")
            logger.info(f"   Size: {chosen.stat().st_size / 1024:.1f} KB")
            return chosen
    
    logger.error("❌ No voice reference found in TTS folder")
    logger.info("💡 Place a WAV or MP3 file in:")
    logger.info("   - /Users/isaiahdupree/Documents/Software/TTS/audio_samples/")
    logger.info("   - /Users/isaiahdupree/Documents/Software/TTS/training_data/")
    return None


def generate_script(topic: str, duration_seconds: int = 60) -> dict:
    """
    Generate a script about the given topic.
    
    Creates structured segments with timing and visuals.
    """
    # Calculate segments based on duration
    num_segments = max(3, duration_seconds // 15)  # ~15 seconds per segment
    
    segments = []
    segment_duration = duration_seconds / num_segments
    
    # Generate content based on topic
    if topic.lower() == "thermodynamics":
        content_segments = [
            "What is thermodynamics? It's the study of energy, heat, and work in physical systems.",
            "The three laws of thermodynamics are fundamental. First law: Energy cannot be created or destroyed, only transferred. Second law: Entropy always increases in isolated systems.",
            "Think of a hot cup of coffee. Heat flows from the coffee to the air until they reach thermal equilibrium. That's the second law in action.",
            "Your car engine converts heat energy into mechanical motion. That's the first law - energy transformation.",
            "Entropy measures disorder. A broken egg has more entropy than a whole one. The universe tends toward disorder, which is why time only moves forward.",
            "Thermodynamics governs everything from engines to life itself. Understanding these laws helps us build better technology and understand our universe."
        ]
    else:
        # Generic explainer structure
        content_segments = [
            f"Let's explore {topic}. This is a fascinating subject that affects many aspects of our daily lives.",
            f"To understand {topic}, we need to look at its fundamental principles and how they apply in practice.",
            f"Real-world examples help illustrate {topic}. Think about how it appears in everyday situations.",
            f"The key concepts of {topic} are interconnected. Understanding one helps you understand the others.",
            f"Applications of {topic} are everywhere. From technology to nature, these principles shape our world.",
            f"In conclusion, {topic} is essential knowledge. Understanding it helps us make better decisions and build better systems."
        ]
    
    # Distribute content across segments
    for i in range(num_segments):
        start = i * segment_duration
        end = (i + 1) * segment_duration if i < num_segments - 1 else duration_seconds
        
        # Cycle through content if we have more segments than content
        text = content_segments[i % len(content_segments)]
        
        segments.append({
            "id": f"segment_{i+1:02d}",
            "start": start,
            "end": end,
            "text": text,
            "visual": "text_overlay" if i % 2 == 0 else "diagram",
            "animation": "fade_in" if i == 0 else ("fade_out" if i == num_segments - 1 else "slide")
        })
    
    return {
        "title": f"{topic} Explained",
        "topic": topic,
        "duration_seconds": duration_seconds,
        "segments": segments
    }


def generate_voice_with_tts_folder(
    script: dict,
    voice_reference: Path,
    output_path: Path,
    hf_token: str = None,
) -> Path:
    """
    Generate voice audio using TTS folder's call_indextts2_api.
    """
    logger.info("🎤 Generating voice audio using TTS folder API...")
    logger.info(f"   Voice reference: {voice_reference.name}")
    logger.info(f"   Output: {output_path}")
    
    # Combine all text
    all_text = " ".join([seg["text"] for seg in script["segments"]])
    
    # Set HF token if provided
    if hf_token:
        import os
        os.environ["HF_TOKEN"] = hf_token
        os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token
        logger.info("✅ Hugging Face token set")
    
    # Call the API
    logger.info("Calling IndexTTS2 API (this may take a while)...")
    
    success = call_indextts2_api(
        voice_reference=str(voice_reference),
        text=all_text,
        output_file=str(output_path),
        emo_control_method="Same as the voice reference",
        emotion_weight=0.8,
        max_text_tokens=120,
    )
    
    if success and output_path.exists():
        size_mb = output_path.stat().st_size / 1024 / 1024
        logger.success(f"✅ Voice generated: {output_path}")
        logger.info(f"📊 File size: {size_mb:.2f} MB")
        return output_path
    else:
        raise RuntimeError("Voice generation failed")


def create_video_with_ffmpeg(
    script: dict,
    voice_audio: Path,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """
    Create explainer video with text overlays and voice audio.
    """
    logger.info("🎬 Creating explainer video...")
    logger.info(f"   Resolution: {width}x{height}")
    
    # Get audio duration
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(voice_audio),
    ]
    
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        audio_duration = float(result.stdout.strip())
    except:
        audio_duration = script["duration_seconds"]
    
    # Build text overlay filters for each segment
    filters = []
    
    for segment in script["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        
        # Escape text for FFmpeg
        escaped_text = text.replace("'", "\\'").replace(":", "\\:").replace("[", "\\[").replace("]", "\\]")
        
        # Truncate if too long (FFmpeg has limits)
        if len(escaped_text) > 100:
            escaped_text = escaped_text[:97] + "..."
        
        # Create text overlay
        drawtext = (
            f"drawtext=text='{escaped_text}':"
            f"fontsize=48:"
            f"fontcolor=white:"
            f"x=(w-text_w)/2:"
            f"y=h-th-100:"
            f"box=1:boxcolor=black@0.7:boxborderw=5:"
            f"enable='between(t,{start},{end})'"
        )
        
        filters.append(drawtext)
    
    # Combine filters
    filter_complex = ",".join(filters)
    
    # Create video
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={width}x{height}:d={audio_duration}:r=30",
        "-i", str(voice_audio),
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    
    logger.info("Rendering video with FFmpeg...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        
        if output_path.exists():
            size_mb = output_path.stat().st_size / 1024 / 1024
            logger.success(f"✅ Video created: {output_path}")
            logger.info(f"📊 File size: {size_mb:.2f} MB")
            return output_path
        else:
            raise RuntimeError("Output file not created")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error("FFmpeg not found. Install with: brew install ffmpeg")
        raise


def open_video(video_path: Path):
    """Open video file."""
    try:
        subprocess.run(["open", str(video_path)], check=True)
        logger.info(f"🎬 Opened video: {video_path}")
    except:
        logger.info(f"📹 Video: {video_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="Generate explainer video using TTS folder resources"
    )
    parser.add_argument("--topic", default="Thermodynamics", help="Topic to explain")
    parser.add_argument("--duration", type=int, default=60, help="Video duration in seconds")
    parser.add_argument("--voice", type=Path, help="Specific voice reference file (optional)")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--hf-token", help="Hugging Face API token (optional)")
    parser.add_argument("--width", type=int, default=1920, help="Video width")
    parser.add_argument("--height", type=int, default=1080, help="Video height")
    parser.add_argument("--no-open", action="store_true", help="Don't open video automatically")
    parser.add_argument("--tts-folder", type=Path, help="TTS folder path")
    
    args = parser.parse_args()
    
    # TTS folder path
    if args.tts_folder:
        tts_folder = Path(args.tts_folder)
    else:
        tts_folder = Path("/Users/isaiahdupree/Documents/Software/TTS")
    
    if not tts_folder.exists():
        logger.error(f"TTS folder not found: {tts_folder}")
        return 1
    
    # Check TTS availability
    if not TTS_AVAILABLE:
        logger.error("TTS API not available")
        logger.info("💡 Install: pip install gradio_client")
        return 1
    
    # Find voice reference
    if args.voice:
        voice_reference = Path(args.voice)
        if not voice_reference.exists():
            logger.error(f"Voice file not found: {voice_reference}")
            return 1
    else:
        voice_reference = find_voice_reference(tts_folder)
        if not voice_reference:
            return 1
    
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"Generating Explainer Video: {args.topic}")
    logger.info("=" * 80)
    logger.info("")
    
    # Step 1: Generate script
    logger.info("📝 Step 1: Generating script...")
    script = generate_script(args.topic, args.duration)
    logger.success(f"✅ Script created: {len(script['segments'])} segments")
    logger.info(f"   Total text: {sum(len(s['text']) for s in script['segments'])} characters")
    
    # Step 2: Generate voice
    logger.info("")
    logger.info("🎤 Step 2: Generating voice audio...")
    voice_output = Path("Backend/data/tts_outputs") / f"explainer_{uuid4().hex[:8]}.wav"
    voice_output.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        voice_audio = generate_voice_with_tts_folder(
            script=script,
            voice_reference=voice_reference,
            output_path=voice_output,
            hf_token=args.hf_token,
        )
    except Exception as e:
        logger.error(f"Voice generation failed: {e}")
        logger.info("💡 Make sure:")
        logger.info("   1. gradio_client is installed: pip install gradio_client")
        logger.info("   2. Hugging Face token is set (optional but recommended)")
        logger.info("   3. Voice reference file is valid")
        return 1
    
    # Step 3: Create video
    logger.info("")
    logger.info("🎬 Step 3: Creating video...")
    
    if args.output:
        video_output = Path(args.output)
    else:
        video_output = Path("Backend/data/rendered_videos") / f"explainer_{args.topic.lower().replace(' ', '_')}_{uuid4().hex[:8]}.mp4"
        video_output.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        final_video = create_video_with_ffmpeg(
            script=script,
            voice_audio=voice_audio,
            output_path=video_output,
            width=args.width,
            height=args.height,
        )
        
        logger.info("")
        logger.success("=" * 80)
        logger.success("✅ EXPLAINER VIDEO COMPLETE!")
        logger.success("=" * 80)
        logger.info("")
        logger.info(f"📹 Video: {final_video}")
        logger.info(f"🎤 Voice: {voice_audio}")
        logger.info(f"📝 Topic: {args.topic}")
        logger.info(f"⏱️  Duration: {args.duration}s")
        
        if not args.no_open:
            open_video(final_video)
        
        return 0
        
    except Exception as e:
        logger.error(f"Video creation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

