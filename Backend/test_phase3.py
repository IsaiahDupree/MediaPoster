#!/usr/bin/env python3
"""
Phase 3 Testing - Clip Generation
Test all clip generation components
"""
import sys
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))

from modules.clip_generation import (
    VideoEditor,
    CaptionGenerator,
    HookGenerator,
    VisualEnhancer,
    ClipAssembler
)


def test_video_editor():
    """Test video editing"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Video Editor")
    logger.info("="*60)
    
    video_path_str = input("\nEnter video path: ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return None
    
    video_path = Path(video_path_str).expanduser()
    if not video_path.exists():
        logger.error(f"Not found: {video_path}")
        return None
    
    try:
        editor = VideoEditor()
        
        logger.info("\n1. Extracting 15s clip...")
        clip = editor.extract_clip(video_path, start_time=5.0, duration=15.0)
        logger.success(f"\u2713 Clip: {clip}")
        
        logger.info("\n2. Converting to vertical (9:16)...")
        vertical = editor.convert_to_vertical(clip, crop_mode="blur")
        logger.success(f"\u2713 Vertical: {vertical}")
        
        return {'video_path': video_path, 'clip': clip, 'vertical': vertical}
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_caption_generator():
    """Test caption generation"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Caption Generator")
    logger.info("="*60)
    
    logger.info("\nRequires: video file + transcript JSON")
    
    video_path_str = input("Enter video path (or skip): ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return
    
    video_path = Path(video_path_str).expanduser()
    
    transcript_path_str = input("Enter transcript JSON path: ").strip()
    if not transcript_path_str:
        logger.warning("Skipped")
        return
    
    transcript_path = Path(transcript_path_str).expanduser()
    
    try:
        import json
        with open(transcript_path) as f:
            transcript = json.load(f)
        
        cap_gen = CaptionGenerator(style='viral')
        
        logger.info("\n1. Creating SRT file...")
        srt = cap_gen.create_srt_from_transcript(
            transcript,
            start_time=0,
            end_time=30.0
        )
        logger.success(f"\u2713 SRT: {srt}")
        
        logger.info("\n2. Burning captions into video...")
        captioned = cap_gen.burn_captions(video_path, srt)
        logger.success(f"\u2713 Captioned: {captioned}")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()


def test_hook_generator():
    """Test hook generation"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Hook Generator")
    logger.info("="*60)
    
    logger.info("\nRequires: OpenAI API key")
    
    try:
        hook_gen = HookGenerator()
        
        highlight = {
            'start': 10.0,
            'end': 30.0,
            'duration': 20.0,
            'composite_score': 0.85,
            'metadata': {
                'strengths': ['High energy', 'Strong hooks']
            }
        }
        
        video_context = {
            'content_type': 'podcast',
            'key_topics': ['technology', 'AI', 'future'],
            'video_name': 'test_video'
        }
        
        logger.info("\n1. Generating viral hooks...")
        hooks = hook_gen.generate_hooks(highlight, video_context, count=5)
        
        logger.success(f"\u2713 Generated {len(hooks)} hooks:")
        for i, hook in enumerate(hooks, 1):
            logger.info(f"  {i}. {hook['text']}")
        
        logger.info("\n2. Generating hashtags...")
        hashtags = hook_gen.suggest_hashtags(video_context, count=10)
        logger.success(f"\u2713 Hashtags: {' '.join(hashtags[:5])}")
        
        logger.info("\n3. Generating CTA...")
        cta = hook_gen.generate_cta(video_context)
        logger.success(f"\u2713 CTA: {cta['recommended']}")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()


def test_complete_clip_generation():
    """Test complete clip generation pipeline"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Complete Clip Generation")
    logger.info("="*60)
    
    video_path_str = input("\nEnter video path: ").strip()
    if not video_path_str:
        logger.warning("Skipped")
        return False
    
    video_path = Path(video_path_str).expanduser()
    if not video_path.exists():
        logger.error(f"Not found: {video_path}")
        return False
    
    # Ask for highlights JSON
    logger.info("\nOptional: Provide highlights JSON from Phase 2")
    highlights_path_str = input("Enter highlights JSON path (or skip): ").strip()
    
    highlights = None
    if highlights_path_str:
        highlights_path = Path(highlights_path_str).expanduser()
        if highlights_path.exists():
            import json
            with open(highlights_path) as f:
                data = json.load(f)
                highlights = data.get('highlights') or data.get('selected', [])
            logger.success(f"\u2713 Loaded {len(highlights)} highlights")
    
    if not highlights:
        # Manual highlight
        logger.info("\nNo highlights provided, using manual time")
        start = float(input("Start time (seconds) [10]: ").strip() or "10")
        duration = float(input("Duration (seconds) [20]: ").strip() or "20")
        highlights = [{
            'start': start,
            'end': start + duration,
            'duration': duration,
            'composite_score': 0.8,
            'metadata': {}
        }]
    
    # Ask for transcript
    transcript = None
    transcript_path_str = input("\nTranscript JSON path (optional): ").strip()
    if transcript_path_str:
        transcript_path = Path(transcript_path_str).expanduser()
        if transcript_path.exists():
            import json
            with open(transcript_path) as f:
                transcript = json.load(f)
            logger.success("\u2713 Transcript loaded")
    
    try:
        logger.info("\n" + "="*60)
        logger.info("STARTING CLIP GENERATION")
        logger.info("="*60)
        
        assembler = ClipAssembler()
        
        video_context = {
            'content_type': 'video',
            'key_topics': ['content'],
            'video_name': video_path.stem
        }
        
        # Generate first highlight only for testing
        highlight = highlights[0]
        
        logger.info(f"\nGenerating clip: {highlight['start']:.1f}s - {highlight['end']:.1f}s")
        
        clip_meta = assembler.create_clip(
            video_path,
            highlight,
            transcript=transcript,
            video_context=video_context,
            template='viral_basic',
            platform='tiktok'
        )
        
        logger.info("\n" + "="*60)
        logger.success("\u2713 CLIP GENERATED!")
        logger.info("="*60)
        logger.info(f"\n\u2713 File: {clip_meta['clip_path']}")
        logger.info(f"\u2713 Size: {clip_meta['file_size_mb']:.2f} MB")
        logger.info(f"\u2713 Duration: {clip_meta['duration']:.1f}s")
        
        if clip_meta.get('hook_text'):
            logger.info(f"\u2713 Hook: {clip_meta['hook_text']}")
        if clip_meta.get('hashtags'):
            logger.info(f"\u2713 Hashtags: {' '.join(clip_meta['hashtags'][:5])}")
        
        # Ask to generate more
        if len(highlights) > 1:
            more = input(f"\nGenerate all {len(highlights)} clips? (y/n) [n]: ").strip().lower() == 'y'
            
            if more:
                logger.info("\nGenerating batch...")
                all_clips = assembler.create_clips_batch(
                    video_path,
                    highlights,
                    transcript,
                    video_context,
                    template='viral_basic',
                    platforms=['tiktok']
                )
                
                logger.success(f"\n\u2713 Generated {len(all_clips)} clips!")
                for i, clip in enumerate(all_clips, 1):
                    logger.info(f"  {i}. {Path(clip['clip_path']).name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main menu"""
    print("\n" + "="*60)
    print("   MediaPoster - Phase 3 Testing (Clip Generation)")
    print("="*60)
    print("\nChoose a test:")
    print("  1. Video Editor (extract + vertical)")
    print("  2. Caption Generator")
    print("  3. Hook Generator (requires OpenAI API key)")
    print("  4. Complete Clip Generation (recommended)")
    print("  0. Exit")
    print()
    
    choice = input("Enter choice (0-4): ").strip()
    print()
    
    if choice == '0':
        logger.info("Goodbye!")
        return
    
    elif choice == '1':
        test_video_editor()
    
    elif choice == '2':
        test_caption_generator()
    
    elif choice == '3':
        test_hook_generator()
    
    elif choice == '4':
        success = test_complete_clip_generation()
        if success:
            logger.success("\n\U0001F389 Phase 3 test passed!")
    
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    main()
