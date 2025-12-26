#!/usr/bin/env python3
"""
Voice Cloning Quality Assessment Runner

Runs quality assessment on video files and generates a comprehensive report.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.voice_cloning_quality_assessor import VoiceCloningQualityAssessor, VoiceQualityMetrics
from services.whisper_transcriber import WhisperTranscriber
from loguru import logger


def format_report(metrics: VoiceQualityMetrics, video_path: Path, transcript: Optional[str] = None) -> str:
    """Format assessment results as a readable report"""
    
    report = []
    report.append("=" * 80)
    report.append("VOICE CLONING QUALITY ASSESSMENT REPORT")
    report.append("=" * 80)
    report.append(f"\nFile: {video_path.name}")
    report.append(f"Path: {video_path}")
    report.append(f"Assessment Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n" + "-" * 80)
    
    # Overall Score
    report.append("\n📊 OVERALL ASSESSMENT")
    report.append("-" * 80)
    score_bar = "█" * int(metrics.overall_score * 50) + "░" * (50 - int(metrics.overall_score * 50))
    report.append(f"Overall Score: {metrics.overall_score:.2f}/1.00 [{score_bar}]")
    report.append(f"Suitability: {metrics.suitability_for_cloning.upper()}")
    
    # Signal Quality
    report.append("\n🎤 SIGNAL QUALITY")
    report.append("-" * 80)
    if metrics.snr_db is not None:
        snr_status = "✅ Excellent" if metrics.snr_db >= 35 else "✅ Good" if metrics.snr_db >= 20 else "⚠️  Fair" if metrics.snr_db >= 15 else "❌ Poor"
        report.append(f"Signal-to-Noise Ratio: {metrics.snr_db:.1f} dB {snr_status}")
    else:
        report.append("Signal-to-Noise Ratio: N/A")
    
    if metrics.background_noise_level_db is not None:
        noise_status = "✅ Low" if metrics.background_noise_level_db <= -35 else "✅ Acceptable" if metrics.background_noise_level_db <= -30 else "⚠️  High"
        report.append(f"Background Noise: {metrics.background_noise_level_db:.1f} dB {noise_status}")
    else:
        report.append("Background Noise: N/A")
    
    clarity_bar = "█" * int(metrics.speech_clarity_score * 30) + "░" * (30 - int(metrics.speech_clarity_score * 30))
    report.append(f"Speech Clarity: {metrics.speech_clarity_score:.2f}/1.00 [{clarity_bar}]")
    
    # Audio Characteristics
    report.append("\n🔊 AUDIO CHARACTERISTICS")
    report.append("-" * 80)
    report.append(f"Duration: {metrics.duration_seconds:.1f} seconds ({metrics.duration_seconds/60:.1f} minutes)")
    
    duration_status = "✅ Excellent" if metrics.duration_seconds >= 1800 else "✅ Good" if metrics.duration_seconds >= 300 else "⚠️  Fair" if metrics.duration_seconds >= 30 else "❌ Insufficient"
    report.append(f"Duration Status: {duration_status}")
    
    if metrics.mean_volume_db is not None:
        report.append(f"Mean Volume: {metrics.mean_volume_db:.1f} dB")
    else:
        report.append("Mean Volume: N/A")
    
    volume_bar = "█" * int(metrics.volume_consistency * 30) + "░" * (30 - int(metrics.volume_consistency * 30))
    report.append(f"Volume Consistency: {metrics.volume_consistency:.2f}/1.00 [{volume_bar}]")
    
    if metrics.dynamic_range_db is not None:
        report.append(f"Dynamic Range: {metrics.dynamic_range_db:.1f} dB")
    
    # Technical Specs
    report.append("\n⚙️  TECHNICAL SPECIFICATIONS")
    report.append("-" * 80)
    if metrics.sample_rate_hz:
        sr_status = "✅ Excellent" if metrics.sample_rate_hz >= 44100 else "✅ Good" if metrics.sample_rate_hz >= 22050 else "⚠️  Acceptable" if metrics.sample_rate_hz >= 16000 else "❌ Low"
        report.append(f"Sample Rate: {metrics.sample_rate_hz} Hz {sr_status}")
    else:
        report.append("Sample Rate: N/A")
    
    if metrics.bitrate_kbps:
        report.append(f"Bitrate: {metrics.bitrate_kbps} kbps")
    else:
        report.append("Bitrate: N/A")
    
    channels_status = "✅ Mono" if metrics.channels == 1 else "⚠️  Multi-channel (mono preferred)"
    report.append(f"Channels: {metrics.channels} {channels_status}")
    
    if metrics.audio_format:
        report.append(f"Audio Format: {metrics.audio_format}")
    
    # Frequency Analysis
    report.append("\n📡 FREQUENCY ANALYSIS")
    report.append("-" * 80)
    if metrics.fundamental_frequency_hz:
        report.append(f"Fundamental Frequency: {metrics.fundamental_frequency_hz:.1f} Hz")
    else:
        report.append("Fundamental Frequency: N/A")
    
    freq_bar = "█" * int(metrics.frequency_response_score * 30) + "░" * (30 - int(metrics.frequency_response_score * 30))
    report.append(f"Frequency Response Score: {metrics.frequency_response_score:.2f}/1.00 [{freq_bar}]")
    
    voice_range_status = "✅ Covered" if metrics.voice_range_covered else "⚠️  Limited"
    report.append(f"Voice Range Coverage: {voice_range_status}")
    
    # Speech Analysis
    report.append("\n🗣️  SPEECH ANALYSIS")
    report.append("-" * 80)
    report.append(f"Speech Percentage: {metrics.speech_percentage:.1f}%")
    
    silence_status = "✅ Good" if metrics.silence_percentage <= 20 else "⚠️  High" if metrics.silence_percentage <= 40 else "❌ Excessive"
    report.append(f"Silence Percentage: {metrics.silence_percentage:.1f}% {silence_status}")
    
    report.append(f"Pause Count: {metrics.pause_count}")
    if metrics.avg_pause_duration_s > 0:
        report.append(f"Average Pause Duration: {metrics.avg_pause_duration_s:.2f} seconds")
    
    # Transcript Analysis
    if transcript or metrics.transcript_length_words > 0:
        report.append("\n📝 TRANSCRIPT ANALYSIS")
        report.append("-" * 80)
        report.append(f"Word Count: {metrics.transcript_length_words}")
        report.append(f"Character Count: {metrics.transcript_length_chars}")
        
        if metrics.words_per_minute > 0:
            wpm_status = "✅ Normal" if 100 <= metrics.words_per_minute <= 200 else "⚠️  Slow" if metrics.words_per_minute < 100 else "⚠️  Fast"
            report.append(f"Words Per Minute: {metrics.words_per_minute:.1f} {wpm_status}")
        
        align_bar = "█" * int(metrics.transcript_alignment_score * 30) + "░" * (30 - int(metrics.transcript_alignment_score * 30))
        report.append(f"Transcript Alignment: {metrics.transcript_alignment_score:.2f}/1.00 [{align_bar}]")
    
    # Distortion Detection
    report.append("\n🔍 DISTORTION DETECTION")
    report.append("-" * 80)
    distortion_status = "❌ Detected" if metrics.has_distortion else "✅ None"
    report.append(f"Distortion: {distortion_status}")
    
    clipping_status = "❌ Detected" if metrics.has_clipping else "✅ None"
    report.append(f"Clipping: {clipping_status}")
    
    dist_bar = "█" * int(metrics.distortion_score * 30) + "░" * (30 - int(metrics.distortion_score * 30))
    report.append(f"Distortion Score: {metrics.distortion_score:.2f}/1.00 [{dist_bar}]")
    
    # Issues
    if metrics.issues:
        report.append("\n⚠️  CRITICAL ISSUES")
        report.append("-" * 80)
        for i, issue in enumerate(metrics.issues, 1):
            report.append(f"{i}. {issue}")
    
    # Recommendations
    if metrics.recommendations:
        report.append("\n💡 RECOMMENDATIONS")
        report.append("-" * 80)
        for i, rec in enumerate(metrics.recommendations, 1):
            report.append(f"{i}. {rec}")
    
    # Summary
    report.append("\n" + "=" * 80)
    report.append("SUMMARY")
    report.append("=" * 80)
    
    if metrics.overall_score >= 0.8:
        report.append("✅ This audio is EXCELLENT for voice cloning training.")
    elif metrics.overall_score >= 0.65:
        report.append("✅ This audio is GOOD for voice cloning training.")
        report.append("   Minor improvements may enhance results.")
    elif metrics.overall_score >= 0.5:
        report.append("⚠️  This audio is FAIR for voice cloning training.")
        report.append("   Consider addressing the recommendations above.")
    else:
        report.append("❌ This audio is POOR for voice cloning training.")
        report.append("   Significant improvements needed before use.")
    
    report.append("\n" + "=" * 80)
    
    return "\n".join(report)


def assess_video_file(
    video_path: Path,
    get_transcript: bool = False,
    transcript_text: Optional[str] = None
) -> tuple[VoiceQualityMetrics, Optional[str]]:
    """Assess a single video file"""
    
    logger.info(f"Assessing video: {video_path.name}")
    
    # Get transcript if requested
    transcript = transcript_text
    if get_transcript and not transcript:
        try:
            logger.info("Extracting transcript using Whisper...")
            transcriber = WhisperTranscriber()
            transcript_data = transcriber.transcribe_video(str(video_path))
            transcript = transcript_data.get("text", "")
            logger.info(f"Extracted transcript: {len(transcript)} characters")
        except Exception as e:
            logger.warning(f"Failed to extract transcript: {e}")
            transcript = None
    
    # Run assessment
    assessor = VoiceCloningQualityAssessor()
    metrics = assessor.assess_audio_quality(
        audio_path=video_path,
        transcript=transcript
    )
    
    return metrics, transcript


def main():
    parser = argparse.ArgumentParser(
        description="Assess video files for voice cloning quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Assess a single video file
  python run_voice_quality_assessment.py video.mp4
  
  # Assess with automatic transcript extraction
  python run_voice_quality_assessment.py video.mp4 --transcript
  
  # Assess multiple videos
  python run_voice_quality_assessment.py video1.mp4 video2.mp4 video3.mp4
  
  # Assess all videos in a directory
  python run_voice_quality_assessment.py --directory /path/to/videos
  
  # Save report to file
  python run_voice_quality_assessment.py video.mp4 --output report.txt
        """
    )
    
    parser.add_argument(
        "files",
        nargs="*",
        help="Video files to assess (MP4, MOV, AVI, etc.)"
    )
    
    parser.add_argument(
        "--directory", "-d",
        type=str,
        help="Directory containing video files to assess"
    )
    
    parser.add_argument(
        "--transcript", "-t",
        action="store_true",
        help="Extract transcript using Whisper (requires OPENAI_API_KEY)"
    )
    
    parser.add_argument(
        "--transcript-file",
        type=str,
        help="Path to transcript text file"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for report (default: stdout)"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show only summary statistics"
    )
    
    args = parser.parse_args()
    
    # Collect video files
    video_files = []
    
    if args.directory:
        dir_path = Path(args.directory)
        if not dir_path.exists():
            logger.error(f"Directory not found: {dir_path}")
            sys.exit(1)
        
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.flv', '.wmv'}
        video_files = [f for f in dir_path.iterdir() if f.suffix.lower() in video_extensions]
        
        if not video_files:
            logger.error(f"No video files found in {dir_path}")
            sys.exit(1)
        
        logger.info(f"Found {len(video_files)} video files in {dir_path}")
    
    elif args.files:
        for file_path in args.files:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {path}")
                sys.exit(1)
            video_files.append(path)
    
    else:
        parser.print_help()
        sys.exit(1)
    
    # Load transcript if provided
    transcript_text = None
    if args.transcript_file:
        try:
            with open(args.transcript_file, 'r') as f:
                transcript_text = f.read()
            logger.info(f"Loaded transcript from {args.transcript_file}")
        except Exception as e:
            logger.error(f"Failed to load transcript: {e}")
            sys.exit(1)
    
    # Assess all files
    results = []
    
    for video_file in video_files:
        try:
            metrics, transcript = assess_video_file(
                video_file,
                get_transcript=args.transcript,
                transcript_text=transcript_text
            )
            
            results.append({
                "file": str(video_file),
                "metrics": metrics,
                "transcript": transcript
            })
            
        except Exception as e:
            logger.error(f"Failed to assess {video_file.name}: {e}", exc_info=True)
            results.append({
                "file": str(video_file),
                "error": str(e)
            })
    
    # Generate output
    output_lines = []
    
    if args.json:
        # JSON output
        json_data = []
        for result in results:
            if "error" in result:
                json_data.append({
                    "file": result["file"],
                    "error": result["error"]
                })
            else:
                metrics = result["metrics"]
                json_data.append({
                    "file": result["file"],
                    "overall_score": metrics.overall_score,
                    "suitability": metrics.suitability_for_cloning,
                    "snr_db": metrics.snr_db,
                    "duration_seconds": metrics.duration_seconds,
                    "speech_percentage": metrics.speech_percentage,
                    "silence_percentage": metrics.silence_percentage,
                    "has_distortion": metrics.has_distortion,
                    "has_clipping": metrics.has_clipping,
                    "issues": metrics.issues,
                    "recommendations": metrics.recommendations
                })
        
        output = json.dumps(json_data, indent=2)
        output_lines.append(output)
    
    elif args.summary:
        # Summary output
        output_lines.append("=" * 80)
        output_lines.append("VOICE CLONING QUALITY ASSESSMENT - SUMMARY")
        output_lines.append("=" * 80)
        output_lines.append(f"\nAssessed {len(results)} video file(s)\n")
        
        valid_results = [r for r in results if "error" not in r]
        
        if valid_results:
            avg_score = sum(r["metrics"].overall_score for r in valid_results) / len(valid_results)
            total_duration = sum(r["metrics"].duration_seconds for r in valid_results)
            
            output_lines.append(f"Average Score: {avg_score:.2f}/1.00")
            output_lines.append(f"Total Duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
            output_lines.append("\n" + "-" * 80)
            output_lines.append("File-by-File Results:")
            output_lines.append("-" * 80)
            
            for result in results:
                if "error" in result:
                    output_lines.append(f"\n❌ {Path(result['file']).name}: ERROR - {result['error']}")
                else:
                    metrics = result["metrics"]
                    status_icon = "✅" if metrics.overall_score >= 0.65 else "⚠️" if metrics.overall_score >= 0.5 else "❌"
                    output_lines.append(
                        f"\n{status_icon} {Path(result['file']).name}: "
                        f"Score {metrics.overall_score:.2f} ({metrics.suitability_for_cloning}) | "
                        f"Duration: {metrics.duration_seconds:.1f}s | "
                        f"SNR: {metrics.snr_db:.1f} dB" if metrics.snr_db else "SNR: N/A"
                    )
        else:
            output_lines.append("❌ No valid assessments completed")
    
    else:
        # Full report output
        for i, result in enumerate(results, 1):
            if "error" in result:
                output_lines.append(f"\n{'='*80}")
                output_lines.append(f"ERROR: {Path(result['file']).name}")
                output_lines.append(f"{'='*80}")
                output_lines.append(f"Error: {result['error']}\n")
            else:
                report = format_report(
                    result["metrics"],
                    Path(result["file"]),
                    result.get("transcript")
                )
                output_lines.append(report)
                
                if i < len(results):
                    output_lines.append("\n\n")
    
    # Write output
    output_text = "\n".join(output_lines)
    
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            f.write(output_text)
        logger.success(f"Report saved to: {output_path}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()

