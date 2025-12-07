#!/usr/bin/env python3
"""
Phase 1 Testing - AI Analysis Module
Quick test script for individual components
"""
import sys
from pathlib import Path
from loguru import logger

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.ai_analysis import (
    WhisperService,
    FrameExtractor,
    VisionAnalyzer,
    AudioAnalyzer,
    ContentAnalyzer
)


def test_whisper_transcription():
    """Test Whisper transcription"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Whisper Transcription")
    logger.info("="*60)
    
    video_path_str = input("\nEnter path to video file: ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return False
    
    video_path = Path(video_path_str).expanduser()
    
    if not video_path.exists():
        logger.error(f"File not found: {video_path}")
        return False
    
    try:
        service = WhisperService()
        result = service.transcribe_video(video_path)
        
        logger.success("✓ Transcription complete!")
        logger.info(f"Language: {result.get('language', 'unknown')}")
        logger.info(f"Duration: {result.get('duration', 0):.1f}s")
        logger.info(f"Word count: {len(result['text'].split())}")
        logger.info(f"\nTranscript preview:\n{result['text'][:200]}...")
        
        # Save SRT
        srt_path = video_path.parent / f"{video_path.stem}_subtitles.srt"
        service.generate_srt(result, srt_path)
        logger.success(f"✓ SRT saved: {srt_path}")
        
        return True
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return False


def test_frame_extraction():
    """Test frame extraction"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Frame Extraction")
    logger.info("="*60)
    
    video_path_str = input("\nEnter path to video file: ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return False
    
    video_path = Path(video_path_str).expanduser()
    
    if not video_path.exists():
        logger.error(f"File not found: {video_path}")
        return False
    
    try:
        extractor = FrameExtractor()
        
        # Extract key frames
        logger.info("Extracting key frames...")
        key_frames = extractor.extract_key_frames(video_path, max_frames=10)
        
        logger.success(f"✓ Extracted {len(key_frames)} key frames")
        for i, kf in enumerate(key_frames[:5]):
            logger.info(f"  Frame {i+1}: {kf['timestamp']:.2f}s - {kf['path'].name}")
        
        logger.info(f"\n✓ Frames saved to: {extractor.output_dir / video_path.stem}")
        
        return True
    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")
        return False


def test_vision_analysis():
    """Test GPT-4 Vision analysis"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: GPT-4 Vision Analysis")
    logger.info("="*60)
    
    image_path_str = input("\nEnter path to image/frame file: ").strip()
    if not image_path_str:
        logger.warning("Skipped")
        return False
    
    image_path = Path(image_path_str).expanduser()
    
    if not image_path.exists():
        logger.error(f"File not found: {image_path}")
        return False
    
    try:
        analyzer = VisionAnalyzer()
        
        logger.info("Analyzing frame with GPT-4 Vision...")
        result = analyzer.analyze_frame(image_path)
        
        logger.success("✓ Analysis complete!")
        logger.info(f"Tokens used: {result['usage']['total_tokens']}")
        logger.info(f"\nDescription:\n{result['description']}")
        
        return True
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return False


def test_audio_analysis():
    """Test audio analysis"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Audio Analysis")
    logger.info("="*60)
    
    video_path_str = input("\nEnter path to video file: ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return False
    
    video_path = Path(video_path_str).expanduser()
    
    if not video_path.exists():
        logger.error(f"File not found: {video_path}")
        return False
    
    try:
        analyzer = AudioAnalyzer()
        
        logger.info("Analyzing audio...")
        analysis = analyzer.analyze_audio_comprehensive(video_path)
        
        logger.success("✓ Audio analysis complete!")
        logger.info(f"Silence periods: {analysis['num_silence_periods']}")
        logger.info(f"Audio peaks: {analysis['num_peaks']}")
        logger.info(f"Total silence: {analysis['total_silence_duration']:.2f}s")
        
        return True
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        return False


def test_complete_analysis():
    """Test complete content analysis"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Complete Content Analysis")
    logger.info("="*60)
    
    video_path_str = input("\nEnter path to video file: ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return False
    
    video_path = Path(video_path_str).expanduser()
    
    if not video_path.exists():
        logger.error(f"File not found: {video_path}")
        return False
    
    # Ask what to analyze
    logger.info("\nWhat should be analyzed?")
    transcribe = input("Transcribe audio? (y/n) [y]: ").strip().lower() != 'n'
    analyze_frames = input("Analyze frames with GPT-4 Vision? (y/n) [y]: ").strip().lower() != 'n'
    analyze_audio = input("Analyze audio? (y/n) [y]: ").strip().lower() != 'n'
    
    try:
        analyzer = ContentAnalyzer()
        
        logger.info("\n🎬 Starting complete analysis...")
        analysis = analyzer.analyze_video_complete(
            video_path,
            extract_frames=True,
            analyze_vision=analyze_frames,
            transcribe_audio=transcribe,
            analyze_audio=analyze_audio,
            max_frames=10
        )
        
        logger.success("\n✓ Complete analysis finished!")
        
        # Show summary
        logger.info("\n" + "="*60)
        logger.info("ANALYSIS SUMMARY")
        logger.info("="*60)
        
        logger.info(f"\nModules run: {', '.join(analysis['modules_run'])}")
        
        if 'transcript' in analysis and 'text' in analysis['transcript']:
            word_count = len(analysis['transcript']['text'].split())
            logger.info(f"📝 Transcript: {word_count} words")
        
        if 'frames' in analysis:
            logger.info(f"🎞️  Frames: {len(analysis['frames'])} extracted")
        
        if 'visual_analysis' in analysis:
            logger.info(f"👁️  Vision: {len(analysis['visual_analysis'])} frames analyzed")
        
        if 'audio_analysis' in analysis:
            logger.info(f"🔊 Audio: {analysis['insights'].get('audio_peaks', 0)} peaks detected")
        
        if 'video_summary' in analysis:
            logger.info(f"\n📋 Video Summary:\n{analysis['video_summary']}")
        
        insights = analysis.get('insights', {})
        logger.info(f"\n🎯 Content Type: {insights.get('content_type', 'unknown')}")
        logger.info(f"✨ Viral Indicators: {', '.join(insights.get('viral_indicators', []))}")
        
        # Save analysis
        output_path = video_path.parent / f"{video_path.stem}_analysis.json"
        analyzer.save_analysis(analysis, output_path)
        logger.success(f"\n✓ Analysis saved to: {output_path}")
        
        return True
    except Exception as e:
        logger.error(f"Complete analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main menu"""
    print("\n" + "="*60)
    print("   MediaPoster - Phase 1 Testing (AI Analysis)")
    print("="*60)
    print("\nChoose a test:")
    print("  1. Whisper Transcription")
    print("  2. Frame Extraction")
    print("  3. GPT-4 Vision Analysis (single frame)")
    print("  4. Audio Analysis")
    print("  5. Complete Content Analysis (recommended)")
    print("  0. Exit")
    print()
    
    choice = input("Enter choice (0-5): ").strip()
    print()
    
    tests = {
        '1': test_whisper_transcription,
        '2': test_frame_extraction,
        '3': test_vision_analysis,
        '4': test_audio_analysis,
        '5': test_complete_analysis,
    }
    
    if choice == '0':
        logger.info("Goodbye!")
        return
    
    if choice in tests:
        try:
            success = tests[choice]()
            if success:
                logger.success("\n🎉 Test passed!")
            else:
                logger.warning("\n⚠️  Test incomplete")
        except Exception as e:
            logger.error(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    main()
