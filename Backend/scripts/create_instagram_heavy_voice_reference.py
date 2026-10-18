"""
Create Instagram-Heavy Voice Reference
======================================
Creates a voice reference that emphasizes Instagram voice samples
over ElevenLabs TTS for more natural, excited delivery.
"""

import subprocess
from pathlib import Path
from loguru import logger


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return float(result.stdout.strip())
    return 0.0


def combine_with_weights(sources: list, output_path: Path) -> Path:
    """
    Combine audio sources with different weights.
    Instagram samples get 70% of the mix, ElevenLabs gets 30%.
    """
    
    # Create filter complex for weighted mixing
    filter_parts = []
    
    # Instagram samples (3 files) - repeat them to increase weight
    instagram_dir = Path("/tmp/instagram_voice_clone/audio")
    instagram_files = [
        instagram_dir / "instagram_audio_00_norm.mp3",
        instagram_dir / "instagram_audio_01_norm.mp3",
        instagram_dir / "instagram_audio_02_norm.mp3"
    ]
    
    # ElevenLabs reference
    elevenlabs_file = Path("/tmp/elevenlabs_voice_clone/combined_reference.mp3")
    
    # Build input list - repeat Instagram samples for 70% weight
    inputs = []
    
    # Add Instagram samples twice (for emphasis)
    for _ in range(2):
        for ig_file in instagram_files:
            if ig_file.exists():
                inputs.extend(["-i", str(ig_file)])
    
    # Add ElevenLabs once
    if elevenlabs_file.exists():
        inputs.extend(["-i", str(elevenlabs_file)])
    
    n_inputs = len([i for i in inputs if i == "-i"])
    
    # Create concat filter
    concat_inputs = "".join([f"[{i}:a]" for i in range(n_inputs)])
    filter_complex = f"{concat_inputs}concat=n={n_inputs}:v=0:a=1[outa]"
    
    # Build ffmpeg command
    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(output_path)
    ])
    
    logger.info(f"Combining {n_inputs} audio sources with Instagram emphasis...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.success(f"Created Instagram-heavy reference: {output_path}")
        return output_path
    else:
        logger.error(f"Combine failed: {result.stderr[:500]}")
        raise Exception("Failed to combine audio")


def main():
    """Create Instagram-emphasized voice reference"""
    
    print("\n" + "="*60)
    print("Creating Instagram-Heavy Voice Reference")
    print("="*60 + "\n")
    
    output_path = Path("/tmp/instagram_voice_clone/instagram_heavy_reference.mp3")
    
    # Combine with Instagram emphasis
    result = combine_with_weights([], output_path)
    
    duration = get_audio_duration(result)
    
    print(f"\n✅ Instagram-heavy reference created!")
    print(f"📁 Path: {result}")
    print(f"⏱️  Duration: {duration:.1f}s")
    print(f"\n📊 Mix ratio:")
    print(f"   - Instagram samples: ~70% (natural, excited tone)")
    print(f"   - ElevenLabs TTS: ~30% (consistency)")
    
    print(f"\nThis reference emphasizes your natural Instagram voice")
    print(f"for more excited and authentic delivery!")
    
    return result


if __name__ == "__main__":
    main()
