#!/usr/bin/env python3
"""
Find and Combine Voice Training Data

Identifies videos with clear spoken content and combines them for voice cloning training.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import json
import tempfile
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.voice_cloning_quality_assessor import VoiceCloningQualityAssessor, VoiceQualityMetrics
from services.whisper_transcriber import WhisperTranscriber
from loguru import logger


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
    except:
        pass
    return 0.0


def extract_transcript_safe(video_path: Path) -> Tuple[str, bool]:
    """Safely extract transcript, returns (transcript, has_speech)"""
    try:
        transcriber = WhisperTranscriber()
        transcript_data = transcriber.transcribe_video(str(video_path))
        transcript = transcript_data.get("text", "")
        
        # Check if transcript has meaningful content
        words = transcript.split()
        has_speech = len(words) > 10  # At least 10 words
        
        return transcript, has_speech
    except Exception as e:
        logger.warning(f"Failed to extract transcript from {video_path.name}: {e}")
        return "", False


def assess_video_with_transcript(video_path: Path, transcript: str) -> VoiceQualityMetrics:
    """Assess video quality with transcript"""
    assessor = VoiceCloningQualityAssessor()
    return assessor.assess_audio_quality(
        audio_path=video_path,
        transcript=transcript
    )


def find_videos_with_speech(
    directory: Path,
    min_duration: float = 10.0,
    max_videos: int = 50,
    require_transcript: bool = True
) -> List[Dict]:
    """Find videos that likely contain speech"""
    
    logger.info(f"Scanning {directory} for videos with speech...")
    
    video_extensions = {'.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm'}
    videos = []
    
    # Find all video files
    for ext in video_extensions:
        videos.extend(directory.glob(f"*{ext}"))
        videos.extend(directory.glob(f"*{ext.upper()}"))
    
    logger.info(f"Found {len(videos)} video files")
    
    # Filter and analyze videos
    candidates = []
    
    for i, video_path in enumerate(videos[:max_videos], 1):
        logger.info(f"[{i}/{min(len(videos), max_videos)}] Analyzing {video_path.name}...")
        
        duration = get_video_duration(video_path)
        
        if duration < min_duration:
            logger.debug(f"  Skipping {video_path.name}: too short ({duration:.1f}s)")
            continue
        
        # Extract transcript to check for speech
        transcript = ""
        has_speech = False
        
        if require_transcript:
            transcript, has_speech = extract_transcript_safe(video_path)
            
            if not has_speech:
                logger.debug(f"  Skipping {video_path.name}: no clear speech detected")
                continue
        
        # Assess quality
        try:
            metrics = assess_video_with_transcript(video_path, transcript)
            
            # Only include videos with reasonable quality
            if metrics.overall_score >= 0.3:  # At least fair quality
                candidates.append({
                    'path': video_path,
                    'duration': duration,
                    'score': metrics.overall_score,
                    'suitability': metrics.suitability_for_cloning,
                    'transcript': transcript,
                    'word_count': metrics.transcript_length_words,
                    'snr_db': metrics.snr_db,
                    'speech_percentage': metrics.speech_percentage,
                    'silence_percentage': metrics.silence_percentage,
                    'has_speech': has_speech,
                    'metrics': metrics
                })
                
                logger.success(
                    f"  ✓ {video_path.name}: {duration:.1f}s, "
                    f"score {metrics.overall_score:.2f}, "
                    f"{metrics.transcript_length_words} words"
                )
            else:
                logger.debug(f"  Skipping {video_path.name}: low quality ({metrics.overall_score:.2f})")
        except Exception as e:
            logger.error(f"  Failed to assess {video_path.name}: {e}")
            continue
    
    # Sort by quality score (descending)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return candidates


def combine_videos_for_training(
    video_paths: List[Path],
    output_path: Path,
    target_duration: float = 300.0  # 5 minutes
) -> Path:
    """Combine multiple videos into a single training file"""
    
    logger.info(f"Combining {len(video_paths)} videos into {output_path.name}...")
    
    # Create concat file for FFmpeg
    concat_file = output_path.parent / "concat_list.txt"
    
    with open(concat_file, 'w') as f:
        for video_path in video_paths:
            # Escape single quotes in path
            escaped_path = str(video_path).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    # Use FFmpeg to concatenate videos
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',  # Stream copy (fast, no re-encoding)
        '-y',
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr}")
            raise RuntimeError(f"Failed to combine videos: {result.stderr}")
        
        logger.success(f"✓ Combined videos: {output_path.name}")
        
        # Cleanup concat file
        concat_file.unlink()
        
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to combine videos: {e}")
        # Cleanup on error
        if concat_file.exists():
            concat_file.unlink()
        raise


def select_best_videos(
    candidates: List[Dict],
    target_duration: float = 300.0,  # 5 minutes
    min_score: float = 0.4
) -> List[Dict]:
    """Select best videos to reach target duration"""
    
    # Filter by minimum score
    filtered = [v for v in candidates if v['score'] >= min_score]
    
    # Sort by score (best first)
    filtered.sort(key=lambda x: x['score'], reverse=True)
    
    selected = []
    total_duration = 0.0
    
    for candidate in filtered:
        if total_duration >= target_duration:
            break
        
        selected.append(candidate)
        total_duration += candidate['duration']
    
    return selected, total_duration


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Find and combine best quality videos for voice cloning training"
    )
    
    parser.add_argument(
        "--directory", "-d",
        type=str,
        default="/Users/isaiahdupree/Documents/IphoneImport",
        help="Directory containing video files"
    )
    
    parser.add_argument(
        "--target-duration", "-t",
        type=float,
        default=300.0,
        help="Target duration in seconds (default: 300 = 5 minutes)"
    )
    
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.4,
        help="Minimum quality score (default: 0.4)"
    )
    
    parser.add_argument(
        "--max-videos",
        type=int,
        default=50,
        help="Maximum videos to analyze (default: 50)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="combined_voice_training.mp4",
        help="Output file name"
    )
    
    parser.add_argument(
        "--no-transcript",
        action="store_true",
        help="Skip transcript extraction (faster but less accurate)"
    )
    
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list candidates, don't combine"
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        sys.exit(1)
    
    # Find videos with speech
    candidates = find_videos_with_speech(
        directory,
        min_duration=10.0,
        max_videos=args.max_videos,
        require_transcript=not args.no_transcript
    )
    
    if not candidates:
        logger.error("No suitable videos found")
        sys.exit(1)
    
    logger.info(f"\nFound {len(candidates)} candidate videos with speech")
    
    # Select best videos
    selected, total_duration = select_best_videos(
        candidates,
        target_duration=args.target_duration,
        min_score=args.min_score
    )
    
    logger.info(f"\nSelected {len(selected)} videos:")
    logger.info(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    logger.info(f"Average score: {sum(v['score'] for v in selected) / len(selected):.2f}")
    
    print("\n" + "="*80)
    print("SELECTED VIDEOS FOR VOICE TRAINING")
    print("="*80)
    for i, video in enumerate(selected, 1):
        print(f"\n{i}. {video['path'].name}")
        print(f"   Duration: {video['duration']:.1f}s")
        print(f"   Score: {video['score']:.2f} ({video['suitability']})")
        print(f"   Words: {video['word_count']}")
        if video['snr_db']:
            print(f"   SNR: {video['snr_db']:.1f} dB")
        print(f"   Speech: {video['speech_percentage']:.1f}%")
    
    if args.list_only:
        logger.info("\nList-only mode: not combining videos")
        return
    
    # Combine videos
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    
    try:
        combined_path = combine_videos_for_training(
            [v['path'] for v in selected],
            output_path,
            target_duration=args.target_duration
        )
        
        logger.success(f"\n✓ Combined training file created: {combined_path}")
        logger.info(f"  Duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        logger.info(f"  File size: {combined_path.stat().st_size / (1024*1024):.1f} MB")
        
        # Re-assess combined file
        logger.info("\nAssessing combined file...")
        combined_transcript = " ".join(v['transcript'] for v in selected if v['transcript'])
        metrics = assess_video_with_transcript(combined_path, combined_transcript)
        
        print("\n" + "="*80)
        print("COMBINED FILE ASSESSMENT")
        print("="*80)
        print(f"Overall Score: {metrics.overall_score:.2f}/1.00")
        print(f"Suitability: {metrics.suitability_for_cloning.upper()}")
        print(f"Duration: {metrics.duration_seconds:.1f}s ({metrics.duration_seconds/60:.1f} minutes)")
        print(f"Total Words: {metrics.transcript_length_words}")
        if metrics.snr_db:
            print(f"SNR: {metrics.snr_db:.1f} dB")
        print(f"Speech: {metrics.speech_percentage:.1f}%")
        print(f"Silence: {metrics.silence_percentage:.1f}%")
        
        if metrics.issues:
            print("\nIssues:")
            for issue in metrics.issues:
                print(f"  - {issue}")
        
        if metrics.recommendations:
            print("\nRecommendations:")
            for rec in metrics.recommendations:
                print(f"  - {rec}")
        
    except Exception as e:
        logger.error(f"Failed to combine videos: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

