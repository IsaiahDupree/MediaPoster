"""
Instagram Voice Extractor
=========================
Downloads Instagram posts and extracts voice audio for voice cloning.
Combines with ElevenLabs samples for enhanced Modal voice clone.
"""

import os
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from loguru import logger

# Instagram URLs to process
INSTAGRAM_URLS = [
    "https://www.instagram.com/p/DTxrEbyjk43/",
    "https://www.instagram.com/p/DTwMxg1jsFB/",
    "https://www.instagram.com/p/DTp7eGQAJH5/",
]

# Output directories
OUTPUT_DIR = Path("/tmp/instagram_voice_clone")
ELEVENLABS_DIR = Path("/tmp/elevenlabs_voice_clone")


def download_instagram_video(url: str, output_path: Path) -> Path:
    """Download Instagram video using yt-dlp"""
    
    cmd = [
        "yt-dlp",
        "--no-check-certificate",
        "-f", "best",
        "-o", str(output_path),
        url
    ]
    
    logger.info(f"Downloading: {url}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        # Find the actual downloaded file (yt-dlp may add extension)
        for ext in [".mp4", ".webm", ".mkv", ""]:
            check_path = Path(str(output_path) + ext) if ext else output_path
            if check_path.exists():
                logger.success(f"Downloaded: {check_path}")
                return check_path
        
        # Check for any file with the base name
        for f in output_path.parent.glob(f"{output_path.stem}*"):
            if f.is_file():
                return f
    
    logger.error(f"Download failed: {result.stderr}")
    raise Exception(f"Failed to download {url}")


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """Extract audio from video using ffmpeg"""
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "libmp3lame",
        "-ab", "192k",
        "-ar", "44100",
        str(output_path)
    ]
    
    logger.info(f"Extracting audio from: {video_path.name}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and output_path.exists():
        logger.success(f"Extracted: {output_path}")
        return output_path
    
    logger.error(f"Audio extraction failed: {result.stderr}")
    raise Exception(f"Failed to extract audio from {video_path}")


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


def combine_audio_files(audio_files: list[Path], output_path: Path) -> Path:
    """Combine multiple audio files"""
    
    list_path = output_path.parent / "combine_list.txt"
    
    with open(list_path, "w") as f:
        for audio_file in audio_files:
            f.write(f"file '{audio_file}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        list_path.unlink()
        logger.success(f"Combined audio: {output_path}")
        return output_path
    
    logger.error(f"Combine failed: {result.stderr}")
    raise Exception("Failed to combine audio files")


def normalize_audio(input_path: Path, output_path: Path) -> Path:
    """Normalize audio levels for consistent voice cloning"""
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-filter:a", "loudnorm=I=-16:LRA=11:TP=-1.5",
        "-ar", "44100",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.success(f"Normalized: {output_path}")
        return output_path
    
    return input_path  # Return original if normalization fails


async def main():
    """Main pipeline: Instagram → Audio → Combined with ElevenLabs"""
    
    print("\n" + "="*60)
    print("Instagram Voice Extractor for Modal Clone")
    print("="*60 + "\n")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    videos_dir = OUTPUT_DIR / "videos"
    audio_dir = OUTPUT_DIR / "audio"
    videos_dir.mkdir(exist_ok=True)
    audio_dir.mkdir(exist_ok=True)
    
    # Step 1: Download Instagram videos
    downloaded_videos = []
    for i, url in enumerate(INSTAGRAM_URLS):
        try:
            video_path = download_instagram_video(
                url,
                videos_dir / f"instagram_{i:02d}"
            )
            downloaded_videos.append(video_path)
        except Exception as e:
            logger.warning(f"Skipping {url}: {e}")
    
    print(f"\n✅ Downloaded {len(downloaded_videos)} videos")
    
    # Step 2: Extract audio from each video
    extracted_audio = []
    for i, video_path in enumerate(downloaded_videos):
        try:
            audio_path = extract_audio(
                video_path,
                audio_dir / f"instagram_audio_{i:02d}.mp3"
            )
            
            # Normalize audio
            normalized_path = audio_dir / f"instagram_audio_{i:02d}_norm.mp3"
            normalized = normalize_audio(audio_path, normalized_path)
            
            duration = get_audio_duration(normalized)
            print(f"   - {normalized.name}: {duration:.1f}s")
            
            extracted_audio.append(normalized)
        except Exception as e:
            logger.warning(f"Audio extraction failed for {video_path}: {e}")
    
    print(f"\n✅ Extracted {len(extracted_audio)} audio files")
    
    # Step 3: Combine Instagram audio
    if extracted_audio:
        instagram_combined = OUTPUT_DIR / "instagram_combined.mp3"
        combine_audio_files(extracted_audio, instagram_combined)
        
        duration = get_audio_duration(instagram_combined)
        print(f"\n✅ Instagram combined: {instagram_combined} ({duration:.1f}s)")
    
    # Step 4: Combine with ElevenLabs samples if available
    all_sources = []
    
    # Add ElevenLabs combined reference
    elevenlabs_combined = ELEVENLABS_DIR / "combined_reference.mp3"
    if elevenlabs_combined.exists():
        all_sources.append(elevenlabs_combined)
        print(f"\n📎 Including ElevenLabs reference: {elevenlabs_combined}")
    
    # Add Instagram combined
    if extracted_audio:
        all_sources.append(instagram_combined)
    
    # Create final combined reference
    if len(all_sources) > 1:
        final_combined = OUTPUT_DIR / "final_voice_reference.mp3"
        combine_audio_files(all_sources, final_combined)
        
        duration = get_audio_duration(final_combined)
        print(f"\n🎯 FINAL REFERENCE: {final_combined}")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Sources: ElevenLabs + {len(extracted_audio)} Instagram posts")
    elif all_sources:
        final_combined = all_sources[0]
        print(f"\n🎯 FINAL REFERENCE: {final_combined}")
    else:
        print("\n⚠️ No audio sources available")
        return None
    
    # Summary
    print("\n" + "="*60)
    print("Voice Reference Summary")
    print("="*60)
    print(f"""
Sources Combined:
  - ElevenLabs samples (Isaiahdupree_v2)
  - Instagram posts: {len(extracted_audio)} videos

Final Reference: {final_combined}

To use with Modal Voice Clone:

    from services.voice.modal_voice_service import ModalVoiceService
    
    service = ModalVoiceService()
    
    # Create embedding from combined reference
    result = await service.create_voice_embedding(
        voice_reference_urls=["file://{final_combined}"],
        name="Isaiah Combined Voice Clone"
    )
    
    # Generate speech
    audio = await service.generate_with_embedding(
        text="Your text here",
        embedding_id=result["embedding_id"]
    )
""")
    
    return {
        "instagram_videos": [str(v) for v in downloaded_videos],
        "instagram_audio": [str(a) for a in extracted_audio],
        "final_reference": str(final_combined),
        "total_duration": get_audio_duration(final_combined)
    }


if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print(f"\n✅ Complete! Result: {result}")
