#!/usr/bin/env python3
"""
Phase 2 Testing - Highlight Detection
Test all highlight detection components
"""
import sys
from pathlib import Path
from loguru import logger

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.highlight_detection import (
    SceneDetector,
    AudioSignalProcessor,
    TranscriptScanner,
    VisualSalienceDetector,
    HighlightRanker,
    GPTRecommender
)


def test_scene_detection():
    """Test scene detection"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Scene Detection")
    logger.info("="*60)
    
    video_path_str = input("\nEnter path to video file: ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return None
    
    video_path = Path(video_path_str).expanduser()
    
    if not video_path.exists():
        logger.error(f"File not found: {video_path}")
        return None
    
    try:
        detector = SceneDetector()
        
        # Detect scenes
        logger.info("Detecting scenes...")
        scenes = detector.detect_scenes(video_path, threshold=0.3)
        
        logger.success(f"✓ Detected {len(scenes)} scenes")
        
        # Show top scenes
        for i, scene in enumerate(scenes[:5]):
            logger.info(f"\n  Scene {i+1}:")
            logger.info(f"    Time: {scene['start']:.1f}s - {scene['end']:.1f}s ({scene['duration']:.1f}s)")
            logger.info(f"    Change score: {scene['change_score']:.3f}")
        
        # Score scenes
        scored = detector.score_scenes(scenes)
        
        logger.info("\n📊 Top scored scenes:")
        for i, scene in enumerate(scored[:3]):
            logger.info(f"\n  #{i+1} - Score: {scene['highlight_score']:.2f}")
            logger.info(f"    Time: {scene['start']:.1f}s - {scene['end']:.1f}s")
            logger.info(f"    Factors: {', '.join(scene.get('score_factors', []))}")
        
        return {
            'video_path': video_path,
            'scenes': scenes,
            'scored_scenes': scored
        }
        
    except Exception as e:
        logger.error(f"Scene detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_audio_signals(video_path: Path):
    """Test audio signal processing"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Audio Signal Processing")
    logger.info("="*60)
    
    try:
        processor = AudioSignalProcessor()
        
        # Volume spikes
        logger.info("\n1. Detecting volume spikes...")
        spikes = processor.detect_volume_spikes(video_path)
        logger.success(f"✓ Found {len(spikes)} volume spikes")
        for i, spike in enumerate(spikes[:3]):
            logger.info(f"  Spike {i+1}: {spike['timestamp']:.1f}s (intensity: {spike['relative_intensity']:.2f}x)")
        
        # Energy curve
        logger.info("\n2. Calculating energy curve...")
        energy_curve = processor.calculate_energy_curve(video_path)
        logger.success(f"✓ Generated {len(energy_curve)} energy points")
        
        # Energy peaks
        logger.info("\n3. Finding energy peaks...")
        peaks = processor.find_energy_peaks(energy_curve)
        logger.success(f"✓ Found {len(peaks)} energy peaks")
        for i, peak in enumerate(peaks[:3]):
            logger.info(f"  Peak {i+1}: {peak['timestamp']:.1f}s (energy: {peak['energy']:.2f})")
        
        # Combine all audio events
        audio_events = spikes + peaks
        
        return audio_events
        
    except Exception as e:
        logger.error(f"Audio signal processing failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_transcript_scanning():
    """Test transcript scanning"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Transcript Scanning")
    logger.info("="*60)
    
    logger.info("\nNote: This requires a transcript JSON file.")
    logger.info("First run: python3 -m modules.ai_analysis.whisper_service video.mp4")
    
    transcript_path_str = input("\nEnter path to transcript JSON (or press Enter to skip): ").strip()
    if not transcript_path_str:
        logger.warning("Skipped")
        return {}
    
    transcript_path = Path(transcript_path_str).expanduser()
    
    if not transcript_path.exists():
        logger.error(f"File not found: {transcript_path}")
        return {}
    
    try:
        import json
        with open(transcript_path) as f:
            transcript = json.load(f)
        
        scanner = TranscriptScanner()
        
        # Comprehensive scan
        results = scanner.scan_comprehensive(transcript)
        
        # Display results
        for highlight_type, highlights in results.items():
            if highlights:
                logger.info(f"\n{highlight_type.upper()}: {len(highlights)} found")
                for i, h in enumerate(highlights[:2]):
                    logger.info(f"  {i+1}. [{h['timestamp']:.1f}s] {h['text'][:50]}...")
        
        return results
        
    except Exception as e:
        logger.error(f"Transcript scanning failed: {e}")
        import traceback
        traceback.print_exc()
        return {}


def test_complete_highlight_detection():
    """Test complete highlight detection workflow"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Complete Highlight Detection")
    logger.info("="*60)
    
    video_path_str = input("\nEnter path to video file: ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return False
    
    video_path = Path(video_path_str).expanduser()
    
    if not video_path.exists():
        logger.error(f"File not found: {video_path}")
        return False
    
    # Ask for analysis JSON (optional)
    logger.info("\nOptional: Provide analysis JSON from Phase 1 for better results")
    analysis_path_str = input("Enter path to analysis JSON (or press Enter to skip): ").strip()
    
    analysis_data = None
    if analysis_path_str:
        analysis_path = Path(analysis_path_str).expanduser()
        if analysis_path.exists():
            import json
            with open(analysis_path) as f:
                analysis_data = json.load(f)
            logger.success("✓ Loaded analysis data")
    
    try:
        logger.info("\n🎬 Starting complete highlight detection...")
        logger.info("="*60)
        
        # Initialize all components
        scene_detector = SceneDetector(min_scene_duration=10.0, max_scene_duration=60.0)
        audio_processor = AudioSignalProcessor()
        ranker = HighlightRanker(min_duration=10.0, max_duration=60.0, min_score=0.4)
        
        # Step 1: Detect scenes
        logger.info("\n📍 Step 1/5: Detecting scenes...")
        scenes = scene_detector.detect_scenes(video_path, threshold=0.3)
        logger.success(f"✓ Detected {len(scenes)} scenes")
        
        # Step 2: Audio analysis
        logger.info("\n🔊 Step 2/5: Analyzing audio signals...")
        volume_spikes = audio_processor.detect_volume_spikes(video_path)
        energy_curve = audio_processor.calculate_energy_curve(video_path)
        energy_peaks = audio_processor.find_energy_peaks(energy_curve)
        audio_events = volume_spikes + energy_peaks
        logger.success(f"✓ Found {len(audio_events)} audio events")
        
        # Step 3: Transcript analysis (if available)
        logger.info("\n📝 Step 3/5: Scanning transcript...")
        transcript_highlights = {}
        if analysis_data and 'transcript' in analysis_data:
            scanner = TranscriptScanner()
            transcript_highlights = scanner.scan_comprehensive(analysis_data['transcript'])
            total_transcript = sum(len(v) for v in transcript_highlights.values())
            logger.success(f"✓ Found {total_transcript} transcript highlights")
        else:
            logger.info("No transcript available, skipping")
        
        # Step 4: Visual analysis (if available)
        logger.info("\n👁️  Step 4/5: Analyzing visuals...")
        visual_highlights = {}
        if analysis_data and 'visual_analysis' in analysis_data:
            visual_detector = VisualSalienceDetector()
            visual_highlights = visual_detector.analyze_comprehensive(analysis_data['visual_analysis'])
            total_visual = sum(len(v) for v in visual_highlights.values())
            logger.success(f"✓ Found {total_visual} visual highlights")
        else:
            logger.info("No visual analysis available, skipping")
        
        # Step 5: Rank and select highlights
        logger.info("\n🏆 Step 5/5: Ranking highlights...")
        
        # Score scenes
        scored_scenes = scene_detector.score_scenes(
            scenes,
            audio_peaks=audio_events,
            transcript_segments=analysis_data.get('transcript', {}).get('segments', []) if analysis_data else []
        )
        
        # Rank all highlights
        ranked_highlights = ranker.rank_highlights(
            scored_scenes,
            audio_events=audio_events,
            transcript_highlights=transcript_highlights if transcript_highlights else None,
            visual_highlights=visual_highlights if visual_highlights else None
        )
        
        logger.success(f"✓ Ranked {len(ranked_highlights)} potential highlights")
        
        # Select top highlights
        selected_highlights = ranker.select_top_highlights(
            ranked_highlights,
            max_highlights=5,
            min_gap=10.0
        )
        
        logger.info("\n" + "="*60)
        logger.success(f"🎉 FOUND {len(selected_highlights)} TOP HIGHLIGHTS!")
        logger.info("="*60)
        
        for i, highlight in enumerate(selected_highlights, 1):
            logger.info(f"\n🎬 HIGHLIGHT #{i}")
            logger.info(f"   Time: {highlight['start']:.1f}s - {highlight['end']:.1f}s ({highlight['duration']:.1f}s)")
            logger.info(f"   Score: {highlight['composite_score']:.2f}")
            logger.info(f"   Signals:")
            for signal, score in highlight['signal_scores'].items():
                logger.info(f"     - {signal}: {score:.2f}")
            
            metadata = highlight.get('metadata', {})
            features = []
            if metadata.get('has_audio_peaks'):
                features.append("High energy")
            if metadata.get('has_transcript_hooks'):
                features.append("Strong hooks")
            if metadata.get('has_visual_interest'):
                features.append("Dynamic visuals")
            
            if features:
                logger.info(f"   Features: {', '.join(features)}")
        
        # Save highlights to JSON
        output_path = video_path.parent / f"{video_path.stem}_highlights.json"
        import json
        with open(output_path, 'w') as f:
            json.dump({
                'video': str(video_path),
                'highlights': selected_highlights,
                'all_ranked': ranked_highlights[:20]
            }, f, indent=2, default=str)
        
        logger.success(f"\n✓ Highlights saved to: {output_path}")
        
        # Optional: GPT recommendations
        use_gpt = input("\n💡 Get GPT-4 recommendations for these highlights? (y/n) [n]: ").strip().lower() == 'y'
        
        if use_gpt:
            try:
                logger.info("\n🤖 Getting GPT-4 recommendations...")
                gpt = GPTRecommender()
                
                video_context = {
                    'duration': analysis_data.get('transcript', {}).get('duration', 0) if analysis_data else 0,
                    'content_type': analysis_data.get('insights', {}).get('content_type', 'unknown') if analysis_data else 'unknown',
                    'key_topics': analysis_data.get('insights', {}).get('key_topics', []) if analysis_data else [],
                    'transcript_preview': analysis_data.get('transcript', {}).get('text', '')[:500] if analysis_data else '',
                    'video_name': video_path.stem
                }
                
                gpt_recommendations = gpt.recommend_highlights(
                    video_context,
                    selected_highlights,
                    target_count=3
                )
                
                logger.success("\n✨ GPT-4 RECOMMENDATIONS:")
                for i, rec in enumerate(gpt_recommendations, 1):
                    logger.info(f"\n🎯 RECOMMENDATION #{i}")
                    logger.info(f"   Time: {rec['start']:.1f}s - {rec['end']:.1f}s")
                    
                    reasoning = rec.get('gpt_reasoning', {})
                    if reasoning:
                        logger.info(f"   Reason: {reasoning.get('reason', 'N/A')}")
                        logger.info(f"   Angle: {reasoning.get('clip_angle', 'N/A')}")
                        logger.info(f"   Viral Potential: {reasoning.get('viral_potential', 'N/A')}")
                
            except Exception as e:
                logger.error(f"GPT recommendations failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Complete highlight detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main menu"""
    print("\n" + "="*60)
    print("   MediaPoster - Phase 2 Testing (Highlight Detection)")
    print("="*60)
    print("\nChoose a test:")
    print("  1. Scene Detection")
    print("  2. Audio Signal Processing")
    print("  3. Transcript Scanning")
    print("  4. Complete Highlight Detection (recommended)")
    print("  0. Exit")
    print()
    
    choice = input("Enter choice (0-4): ").strip()
    print()
    
    if choice == '0':
        logger.info("Goodbye!")
        return
    
    elif choice == '1':
        result = test_scene_detection()
        if result and input("\nTest audio signals too? (y/n) [y]: ").lower() != 'n':
            test_audio_signals(result['video_path'])
    
    elif choice == '2':
        video_path_str = input("Enter path to video file: ").strip()
        if video_path_str:
            video_path = Path(video_path_str).expanduser()
            if video_path.exists():
                test_audio_signals(video_path)
    
    elif choice == '3':
        test_transcript_scanning()
    
    elif choice == '4':
        success = test_complete_highlight_detection()
        if success:
            logger.success("\n🎉 Phase 2 test passed!")
    
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    main()
