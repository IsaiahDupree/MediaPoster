#!/usr/bin/env python3
"""
Generate Thermodynamics Explainer Video
========================================
Generate an explainer video about thermodynamics using:
- AI-generated script
- Your voice from Hugging Face TTS
- Motion Canvas animations
- Video composition

Usage:
    python Backend/scripts/generate_thermodynamics_explainer.py \
      --voice-reference /path/to/your_voice.wav \
      --duration 60
"""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Import services
from models.creative_brief_models import CreativeBrief, VideoFormat, AspectRatio
from services.video_renderer.creative_brief_renderer import CreativeBriefRenderer, ContentType


def generate_thermodynamics_script(duration_seconds: int = 60) -> dict:
    """
    Generate a script about thermodynamics.
    
    Returns a structured script with segments, timings, and visuals.
    """
    # Calculate words per minute (typical speaking rate: 150-160 WPM)
    wpm = 155
    total_words = int((duration_seconds / 60) * wpm)
    
    script_content = {
        "title": "Thermodynamics Explained",
        "duration_seconds": duration_seconds,
        "segments": [
            {
                "id": "intro",
                "start": 0.0,
                "end": 5.0,
                "text": "What is thermodynamics? It's the study of energy, heat, and work.",
                "visual": "text_overlay",
                "animation": "fade_in"
            },
            {
                "id": "laws",
                "start": 5.0,
                "end": 20.0,
                "text": "The three laws of thermodynamics are fundamental. First law: Energy cannot be created or destroyed, only transferred. Second law: Entropy always increases. Third law: Absolute zero is unattainable.",
                "visual": "diagram",
                "animation": "slide"
            },
            {
                "id": "examples",
                "start": 20.0,
                "end": 40.0,
                "text": "Think of a hot cup of coffee. Heat flows from the coffee to the air until they reach the same temperature. That's the second law in action. Your car engine converts heat into motion. That's the first law.",
                "visual": "b_roll",
                "animation": "fade"
            },
            {
                "id": "entropy",
                "start": 40.0,
                "end": 55.0,
                "text": "Entropy measures disorder. A broken egg has more entropy than a whole one. The universe tends toward disorder, which is why time only moves forward.",
                "visual": "diagram",
                "animation": "scale"
            },
            {
                "id": "outro",
                "start": 55.0,
                "end": duration_seconds,
                "text": "Thermodynamics governs everything from engines to life itself. Understanding these laws helps us build better technology and understand our universe.",
                "visual": "text_overlay",
                "animation": "fade_out"
            }
        ]
    }
    
    return script_content


async def generate_voice_with_huggingface(
    script_text: str,
    voice_reference: Path,
    output_path: Path,
    hf_token: str = None,
) -> Path:
    """
    Generate voice audio using Hugging Face TTS (IndexTTS2).
    
    This uses the existing TTS service infrastructure.
    """
    logger.info(f"Generating voice audio with Hugging Face TTS...")
    logger.info(f"  Voice reference: {voice_reference}")
    logger.info(f"  Output: {output_path}")
    
    # Check if TTS API is available
    try:
        import requests
        
        # Use the TTS API endpoint
        api_url = "http://localhost:5555/api/tts/generate"
        
        # Prepare request
        payload = {
            "text": script_text,
            "model": "indextts2",
            "voice_reference": str(voice_reference),
            "output_format": "wav",
            "sample_rate": 22050,
        }
        
        if hf_token:
            # Add token if provided
            headers = {"Authorization": f"Bearer {hf_token}"}
        else:
            headers = {}
        
        logger.info(f"Calling TTS API: {api_url}")
        
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=300,  # 5 minute timeout for long audio
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get("job_id")
            
            logger.info(f"TTS job queued: {job_id}")
            logger.info("Waiting for TTS generation...")
            
            # Poll for completion
            status_url = f"http://localhost:5555/api/tts/status/{job_id}"
            
            max_wait = 300  # 5 minutes
            waited = 0
            while waited < max_wait:
                await asyncio.sleep(2)
                status_response = requests.get(status_url)
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    status_state = status.get("status")
                    
                    if status_state == "completed":
                        audio_path = status.get("audio_path")
                        if audio_path:
                            logger.success(f"✅ Voice generated: {audio_path}")
                            return Path(audio_path)
                    elif status_state == "failed":
                        error = status.get("error", "Unknown error")
                        raise RuntimeError(f"TTS generation failed: {error}")
                
                waited += 2
            
            raise RuntimeError("TTS generation timed out")
        else:
            logger.warning(f"TTS API not available (status {response.status_code})")
            logger.info("💡 Falling back to local TTS generation...")
            raise ConnectionError("TTS API not available")
            
    except (ConnectionError, requests.exceptions.ConnectionError):
        # Fallback: Use direct Hugging Face API
        logger.info("Using direct Hugging Face API...")
        return await generate_voice_direct_hf(script_text, voice_reference, output_path, hf_token)
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise


async def generate_voice_direct_hf(
    script_text: str,
    voice_reference: Path,
    output_path: Path,
    hf_token: str = None,
) -> Path:
    """
    Generate voice directly using Hugging Face API.
    
    This is a fallback if the TTS service isn't running.
    """
    logger.info("Using direct Hugging Face API for TTS...")
    
    try:
        from transformers import pipeline
        
        # Load IndexTTS2 pipeline
        # Note: This requires the model to be downloaded first
        logger.info("Loading IndexTTS2 model...")
        
        tts_pipeline = pipeline(
            "text-to-speech",
            model="IndexTTS2",
            token=hf_token,
        )
        
        # Read voice reference
        with open(voice_reference, "rb") as f:
            voice_ref_audio = f.read()
        
        # Generate speech
        logger.info("Generating speech...")
        audio = tts_pipeline(
            script_text,
            voice_reference=voice_ref_audio,
        )
        
        # Save output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio["audio"])
        
        logger.success(f"✅ Voice generated: {output_path}")
        return output_path
        
    except ImportError:
        logger.error("transformers library not installed")
        logger.info("💡 Install with: pip install transformers")
        raise
    except Exception as e:
        logger.error(f"Direct HF TTS failed: {e}")
        logger.info("💡 Make sure you have:")
        logger.info("   1. Hugging Face token (--hf-token)")
        logger.info("   2. transformers library installed")
        logger.info("   3. Voice reference audio file")
        raise


def create_explainer_video(
    script: dict,
    voice_audio: Path,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """
    Create explainer video by combining visuals and voice audio.
    
    Uses FFmpeg to composite:
    - Animated text overlays
    - Diagrams/visuals
    - Voice narration
    - Background music (optional)
    """
    logger.info("Creating explainer video...")
    logger.info(f"  Voice audio: {voice_audio}")
    logger.info(f"  Output: {output_path}")
    logger.info(f"  Resolution: {width}x{height}")
    
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
    
    logger.info(f"  Audio duration: {audio_duration:.2f}s")
    
    # Create video with text overlays for each segment
    # For now, create a simple video with text overlays
    # In production, this would use Motion Canvas for animations
    
    # Build complex filter for multiple text overlays
    filters = []
    
    for i, segment in enumerate(script["segments"]):
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        
        # Escape text for FFmpeg
        escaped_text = text.replace("'", "\\'").replace(":", "\\:")
        
        # Create text overlay filter
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
        description="Generate thermodynamics explainer video with your voice"
    )
    parser.add_argument("--voice-reference", type=Path, required=True, help="Path to your voice reference audio (WAV)")
    parser.add_argument("--duration", type=int, default=60, help="Video duration in seconds")
    parser.add_argument("--output", type=Path, help="Output video path")
    parser.add_argument("--hf-token", help="Hugging Face API token")
    parser.add_argument("--width", type=int, default=1920, help="Video width")
    parser.add_argument("--height", type=int, default=1080, help="Video height")
    parser.add_argument("--no-open", action="store_true", help="Don't open video automatically")
    
    args = parser.parse_args()
    
    # Validate voice reference
    if not args.voice_reference.exists():
        logger.error(f"Voice reference not found: {args.voice_reference}")
        return 1
    
    # Generate script
    logger.info("📝 Generating thermodynamics script...")
    script = generate_thermodynamics_script(args.duration)
    
    # Combine all text for TTS
    all_text = " ".join([seg["text"] for seg in script["segments"]])
    logger.info(f"Script length: {len(all_text)} characters")
    
    # Generate voice audio
    voice_output = Path("Backend/data/tts_outputs") / f"thermodynamics_voice_{uuid4().hex[:8]}.wav"
    voice_output.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        voice_audio = await generate_voice_with_huggingface(
            script_text=all_text,
            voice_reference=args.voice_reference,
            output_path=voice_output,
            hf_token=args.hf_token,
        )
    except Exception as e:
        logger.error(f"Voice generation failed: {e}")
        logger.info("💡 Make sure:")
        logger.info("   1. Backend TTS service is running (or provide --hf-token)")
        logger.info("   2. Voice reference file is valid WAV format")
        logger.info("   3. Hugging Face token has access to IndexTTS2")
        return 1
    
    # Create video
    if args.output:
        video_output = Path(args.output)
    else:
        video_output = Path("Backend/data/rendered_videos") / f"thermodynamics_explainer_{uuid4().hex[:8]}.mp4"
        video_output.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        final_video = create_explainer_video(
            script=script,
            voice_audio=voice_audio,
            output_path=video_output,
            width=args.width,
            height=args.height,
        )
        
        logger.success("✅ Explainer video created!")
        logger.info(f"📹 Video: {final_video}")
        logger.info(f"🎤 Voice: {voice_audio}")
        
        if not args.no_open:
            open_video(final_video)
        
        return 0
        
    except Exception as e:
        logger.error(f"Video creation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

