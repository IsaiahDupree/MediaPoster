#!/usr/bin/env python3
"""
Extract and Combine Audio for Voice Cloning Training

Extracts audio from selected videos and combines them into a single training file.
"""

import sys
import subprocess
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def extract_audio_from_video(video_path: Path, output_path: Path) -> Path:
    """Extract audio from video file"""
    logger.info(f"Extracting audio from {video_path.name}...")
    
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # 16-bit PCM
        '-ar', '22050',  # 22.05 kHz (good for voice)
        '-ac', '1',  # Mono
        '-y',  # Overwrite
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        logger.success(f"✓ Audio extracted: {output_path.name}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to extract audio: {e}")
        raise


def combine_audio_files(audio_files: list[Path], output_path: Path) -> Path:
    """Combine multiple audio files into one"""
    logger.info(f"Combining {len(audio_files)} audio files...")
    
    # Create concat file
    concat_file = output_path.parent / "audio_concat_list.txt"
    
    with open(concat_file, 'w') as f:
        for audio_file in audio_files:
            escaped_path = str(audio_file).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    # Combine using FFmpeg
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-acodec', 'pcm_s16le',
        '-ar', '22050',
        '-ac', '1',
        '-y',
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        # Cleanup concat file
        concat_file.unlink()
        
        logger.success(f"✓ Combined audio: {output_path.name}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to combine audio: {e}")
        if concat_file.exists():
            concat_file.unlink()
        raise


def get_audio_info(audio_path: Path) -> dict:
    """Get audio file information"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration,size,bit_rate',
        '-of', 'json',
        str(audio_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            return {
                'duration': float(format_info.get('duration', 0)),
                'size_mb': int(format_info.get('size', 0)) / (1024 * 1024),
                'bitrate': int(format_info.get('bit_rate', 0)) // 1000 if format_info.get('bit_rate') else None
            }
    except:
        pass
    
    return {}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract and combine audio from videos for voice cloning"
    )
    
    parser.add_argument(
        "--videos",
        nargs="+",
        help="Video files to process"
    )
    
    parser.add_argument(
        "--from-json",
        type=str,
        help="Load video list from JSON file (from identify_best_voice_training_videos.py)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="combined_voice_training_audio.wav",
        help="Output audio file name"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=['wav', 'mp3', 'flac'],
        default='wav',
        help="Output audio format (default: wav)"
    )
    
    parser.add_argument(
        "--keep-individual",
        action="store_true",
        help="Keep individual extracted audio files"
    )
    
    args = parser.parse_args()
    
    # Get video list
    video_paths = []
    
    if args.from_json:
        with open(args.from_json, 'r') as f:
            data = json.load(f)
            video_paths = [Path(v['path']) for v in data.get('selected_videos', [])]
            logger.info(f"Loaded {len(video_paths)} videos from {args.from_json}")
    elif args.videos:
        video_paths = [Path(v) for v in args.videos]
    else:
        logger.error("Must provide --videos or --from-json")
        sys.exit(1)
    
    # Verify all videos exist
    for video_path in video_paths:
        if not video_path.exists():
            logger.error(f"Video not found: {video_path}")
            sys.exit(1)
    
    # Create output directory
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Set output format
    if args.format == 'mp3':
        output_path = output_path.with_suffix('.mp3')
        codec = 'libmp3lame'
        bitrate = '192k'
    elif args.format == 'flac':
        output_path = output_path.with_suffix('.flac')
        codec = 'flac'
        bitrate = None
    else:  # wav
        output_path = output_path.with_suffix('.wav')
        codec = 'pcm_s16le'
        bitrate = None
    
    # Extract audio from each video
    temp_dir = output_path.parent / "temp_audio"
    temp_dir.mkdir(exist_ok=True)
    
    audio_files = []
    
    for i, video_path in enumerate(video_paths, 1):
        logger.info(f"[{i}/{len(video_paths)}] Processing {video_path.name}...")
        
        audio_file = temp_dir / f"{video_path.stem}_audio.wav"
        
        try:
            extract_audio_from_video(video_path, audio_file)
            audio_files.append(audio_file)
        except Exception as e:
            logger.error(f"Failed to extract audio from {video_path.name}: {e}")
            continue
    
    if not audio_files:
        logger.error("No audio files extracted")
        sys.exit(1)
    
    # Combine audio files
    if len(audio_files) == 1:
        # Just rename if only one file
        import shutil
        shutil.move(str(audio_files[0]), str(output_path))
        logger.info(f"Single audio file saved as {output_path.name}")
    else:
        combine_audio_files(audio_files, output_path)
    
    # Get final audio info
    info = get_audio_info(output_path)
    
    # Cleanup temp files
    if not args.keep_individual:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("Cleaned up temporary files")
    
    # Print summary
    print("\n" + "="*80)
    print("AUDIO EXTRACTION COMPLETE")
    print("="*80)
    print(f"\nOutput File: {output_path}")
    print(f"Format: {args.format.upper()}")
    if info:
        print(f"Duration: {info['duration']:.1f}s ({info['duration']/60:.1f} minutes)")
        print(f"Size: {info['size_mb']:.1f} MB")
        if info['bitrate']:
            print(f"Bitrate: {info['bitrate']} kbps")
    
    print(f"\n✓ Audio file ready for voice cloning training!")
    print(f"  File: {output_path}")
    print(f"  Duration: {info.get('duration', 0):.1f}s ({info.get('duration', 0)/60:.1f} minutes)")
    
    # Save metadata
    metadata = {
        'output_file': str(output_path),
        'format': args.format,
        'source_videos': [str(v) for v in video_paths],
        'duration_seconds': info.get('duration', 0),
        'duration_minutes': info.get('duration', 0) / 60.0,
        'size_mb': info.get('size_mb', 0),
        'bitrate_kbps': info.get('bitrate'),
        'generated_at': datetime.now().isoformat()
    }
    
    metadata_file = output_path.parent / f"{output_path.stem}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.success(f"\n✓ Metadata saved: {metadata_file}")


if __name__ == "__main__":
    main()

