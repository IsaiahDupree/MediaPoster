#!/usr/bin/env python3
"""
Identify Best Voice Training Videos

Finds the highest quality videos for voice cloning training without requiring transcripts.
Uses duration, file size, and basic audio analysis to identify candidates.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.voice_cloning_quality_assessor import VoiceCloningQualityAssessor
from loguru import logger


def get_video_info(video_path: Path) -> Dict:
    """Get video metadata using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration,size,bit_rate:stream=codec_name,sample_rate,channels',
            '-of', 'json',
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            stream_info = data.get('streams', [{}])[0]
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'size_bytes': int(format_info.get('size', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)) // 1000 if format_info.get('bit_rate') else None,
                'codec': stream_info.get('codec_name', 'unknown'),
                'sample_rate': int(stream_info.get('sample_rate', 0)) if stream_info.get('sample_rate') else None,
                'channels': int(stream_info.get('channels', 1))
            }
    except Exception as e:
        logger.debug(f"Failed to get info for {video_path.name}: {e}")
    
    return {}


def quick_audio_check(video_path: Path) -> Dict:
    """Quick audio quality check without full assessment"""
    try:
        # Use FFmpeg to check if audio exists and get basic stats
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-af', 'volumedetect',
            '-f', 'null',
            '-'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        mean_volume = None
        max_volume = None
        
        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                try:
                    mean_volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                except:
                    pass
            elif 'max_volume:' in line:
                try:
                    max_volume = float(line.split('max_volume:')[1].split('dB')[0].strip())
                except:
                    pass
        
        # Check for silence
        cmd_silence = [
            'ffmpeg',
            '-i', str(video_path),
            '-af', 'silencedetect=noise=-40dB:d=0.5',
            '-f', 'null',
            '-'
        ]
        result_silence = subprocess.run(cmd_silence, capture_output=True, text=True, timeout=60)
        
        silence_count = result_silence.stderr.count('silence_start:')
        
        return {
            'mean_volume_db': mean_volume,
            'max_volume_db': max_volume,
            'has_audio': mean_volume is not None,
            'silence_detections': silence_count
        }
    except Exception as e:
        logger.debug(f"Audio check failed for {video_path.name}: {e}")
        return {}


def find_candidate_videos(
    directory: Path,
    min_duration: float = 30.0,
    max_duration: float = 600.0,  # 10 minutes max
    max_videos: int = 100
) -> List[Dict]:
    """Find candidate videos based on duration and basic checks"""
    
    logger.info(f"Scanning {directory} for candidate videos...")
    
    video_extensions = {'.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm'}
    videos = []
    
    for ext in video_extensions:
        videos.extend(directory.glob(f"*{ext}"))
        videos.extend(directory.glob(f"*{ext.upper()}"))
    
    logger.info(f"Found {len(videos)} video files")
    
    candidates = []
    
    for i, video_path in enumerate(videos[:max_videos], 1):
        if i % 10 == 0:
            logger.info(f"Processing {i}/{min(len(videos), max_videos)}...")
        
        # Get basic info
        info = get_video_info(video_path)
        duration = info.get('duration', 0)
        
        if duration < min_duration or duration > max_duration:
            continue
        
        # Quick audio check
        audio_info = quick_audio_check(video_path)
        
        if not audio_info.get('has_audio'):
            continue
        
        # Score based on duration and audio quality
        # Longer videos with good audio levels score higher
        duration_score = min(1.0, duration / 300.0)  # Normalize to 5 minutes
        volume_score = 1.0
        if audio_info.get('mean_volume_db'):
            # Prefer volumes between -20 and -10 dB
            vol = audio_info['mean_volume_db']
            if -20 <= vol <= -10:
                volume_score = 1.0
            elif -30 <= vol < -20 or -10 < vol <= 0:
                volume_score = 0.7
            else:
                volume_score = 0.4
        
        # Lower silence count is better (more speech)
        silence_score = max(0.5, 1.0 - (audio_info.get('silence_detections', 0) / 50.0))
        
        overall_score = (duration_score * 0.4 + volume_score * 0.4 + silence_score * 0.2)
        
        candidates.append({
            'path': video_path,
            'duration': duration,
            'size_mb': info.get('size_bytes', 0) / (1024 * 1024),
            'sample_rate': info.get('sample_rate'),
            'channels': info.get('channels', 1),
            'mean_volume_db': audio_info.get('mean_volume_db'),
            'silence_detections': audio_info.get('silence_detections', 0),
            'score': overall_score,
            'info': info,
            'audio_info': audio_info
        })
    
    # Sort by score (best first)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return candidates


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Identify best videos for voice cloning training"
    )
    
    parser.add_argument(
        "--directory", "-d",
        type=str,
        default="/Users/isaiahdupree/Documents/IphoneImport",
        help="Directory containing video files"
    )
    
    parser.add_argument(
        "--min-duration",
        type=float,
        default=30.0,
        help="Minimum duration in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--max-duration",
        type=float,
        default=600.0,
        help="Maximum duration in seconds (default: 600 = 10 min)"
    )
    
    parser.add_argument(
        "--max-videos",
        type=int,
        default=100,
        help="Maximum videos to check (default: 100)"
    )
    
    parser.add_argument(
        "--target-duration",
        type=float,
        default=300.0,
        help="Target total duration in seconds (default: 300 = 5 min)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output JSON file for selected videos"
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        sys.exit(1)
    
    # Find candidates
    candidates = find_candidate_videos(
        directory,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        max_videos=args.max_videos
    )
    
    if not candidates:
        logger.error("No suitable videos found")
        sys.exit(1)
    
    logger.info(f"\nFound {len(candidates)} candidate videos")
    
    # Select videos to reach target duration
    selected = []
    total_duration = 0.0
    
    for candidate in candidates:
        if total_duration >= args.target_duration:
            break
        selected.append(candidate)
        total_duration += candidate['duration']
    
    # Print results
    print("\n" + "="*80)
    print("BEST VOICE TRAINING VIDEO CANDIDATES")
    print("="*80)
    print(f"\nSelected {len(selected)} videos")
    print(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"Average score: {sum(v['score'] for v in selected) / len(selected):.2f}")
    
    print("\n" + "-"*80)
    print("TOP CANDIDATES:")
    print("-"*80)
    
    for i, video in enumerate(selected, 1):
        print(f"\n{i}. {video['path'].name}")
        print(f"   Duration: {video['duration']:.1f}s ({video['duration']/60:.1f} min)")
        print(f"   Score: {video['score']:.2f}")
        print(f"   Size: {video['size_mb']:.1f} MB")
        if video['mean_volume_db']:
            print(f"   Volume: {video['mean_volume_db']:.1f} dB")
        if video['sample_rate']:
            print(f"   Sample Rate: {video['sample_rate']} Hz")
        print(f"   Channels: {video['channels']}")
        print(f"   Silence Detections: {video['silence_detections']}")
        print(f"   Path: {video['path']}")
    
    # Save to JSON if requested
    if args.output:
        output_data = {
            'selected_videos': [
                {
                    'path': str(v['path']),
                    'duration': v['duration'],
                    'score': v['score'],
                    'size_mb': v['size_mb'],
                    'mean_volume_db': v['mean_volume_db'],
                    'sample_rate': v['sample_rate'],
                    'channels': v['channels']
                }
                for v in selected
            ],
            'total_duration': total_duration,
            'total_duration_minutes': total_duration / 60.0,
            'average_score': sum(v['score'] for v in selected) / len(selected),
            'generated_at': datetime.now().isoformat()
        }
        
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.success(f"\n✓ Results saved to: {output_path}")
    
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Review the selected videos above")
    print("2. Run full quality assessment with transcripts:")
    print(f"   python scripts/run_voice_quality_assessment.py {' '.join(str(v['path']) for v in selected[:5])} --transcript")
    print("3. Combine selected videos:")
    print(f"   python scripts/find_and_combine_voice_training_data.py --directory {directory} --target-duration {args.target_duration}")


if __name__ == "__main__":
    main()

