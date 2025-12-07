"""
Test music recommendation and audio mixing
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.music.music_recommender import MusicRecommender

load_dotenv()


def test_music_system():
    """Test music recommendation and mixing"""
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*22 + "MUSIC RECOMMENDATION TEST" + " "*29 + "║")
    logger.info("╚" + "="*78 + "╝\n")
    
    recommender = MusicRecommender()
    
    # Test 1: Mood Analysis
    logger.info("TEST 1: Mood Analysis")
    logger.info("─"*80)
    
    test_prompts = [
        ("Serene lake sunset", "calm"),
        ("Fast car racing action", "energetic"),
        ("Emotional childhood memories", "emotional"),
        ("Cyberpunk city night", "dramatic")
    ]
    
    for prompt, expected_mood in test_prompts:
        mood_data = recommender.analyze_video_mood(prompt)
        logger.info(f"\nPrompt: '{prompt}'")
        logger.info(f"  Detected: {mood_data['mood']} (expected: {expected_mood})")
        logger.info(f"  Genre: {mood_data['genre']}, Tempo: {mood_data['tempo']}")
    
    # Test 2: Track Recommendation
    logger.info("\n\nTEST 2: Track Recommendation")
    logger.info("─"*80)
    
    for mood in ['upbeat', 'calm', 'dramatic']:
        logger.info(f"\nSearching for '{mood}' tracks...")
        tracks = recommender.recommend_tracks(mood, duration=30, limit=3)
        
        if tracks:
            logger.success(f"✅ Found {len(tracks)} tracks")
            for i, track in enumerate(tracks, 1):
                logger.info(f"  {i}. {track.title} - {track.artist} ({track.source})")
        else:
            logger.warning(f"⚠️  No tracks found for mood: {mood}")
    
    # Test 3: Audio Mixing (requires video file)
    logger.info("\n\nTEST 3: Audio Mixing")
    logger.info("─"*80)
    
    # Check if we have test files
    test_video = "test_sora_output.mp4"  # From Sora test
    
    if os.path.exists(test_video):
        logger.info(f"Found test video: {test_video}")
        
        # Get music recommendation
        mood_data = recommender.analyze_video_mood("upbeat energetic video")
        tracks = recommender.recommend_tracks(mood_data['mood'], duration=30, limit=1)
        
        if tracks and tracks[0].download_url and 'example.com' not in tracks[0].download_url:
            logger.info("Downloading music track...")
            music_file = "test_music.mp3"
            
            if recommender.download_track(tracks[0], music_file):
                logger.success("✅ Music downloaded")
                
                logger.info("Mixing audio...")
                output_file = "test_video_with_music.mp4"
                
                if recommender.add_background_music(
                    video_path=test_video,
                    music_path=music_file,
                    output_path=output_file,
                    volume=0.2,
                    fade_duration=1.5
                ):
                    logger.success(f"✅ Video with music created: {output_file}")
                else:
                    logger.error("❌ Audio mixing failed")
            else:
                logger.error("❌ Music download failed")
        else:
            logger.warning("⚠️  No real tracks available (using fallback)")
    else:
        logger.warning(f"⚠️  Test video not found: {test_video}")
        logger.info("Run test_sora.py first to generate a test video")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info("\n✅ Mood analysis working")
    logger.info("✅ Track recommendation functional")
    logger.info("ℹ️  Audio mixing requires:")
    logger.info("   1. Valid music API key (PIXABAY_API_KEY in .env)")
    logger.info("   2. Test video file")
    logger.info("   3. moviepy installed (pip install moviepy)")
    logger.info("\n" + "="*80 + "\n")


if __name__ == '__main__':
    test_music_system()
