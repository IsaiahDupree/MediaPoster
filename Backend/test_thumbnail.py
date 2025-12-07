"""
Test thumbnail generation directly
"""
import asyncio
import sys
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')

from services.thumbnail_generator import ThumbnailGenerator
from pathlib import Path

def test_thumbnail_gen():
    # Test file (one of the .MOV videos)
    video_path = "/Users/isaiahdupree/Documents/IphoneImport/IMG_3816.MOV"
    
    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    print("✅ Video file exists")
    print(f"🎬 Testing thumbnail generation for: {video_path}")
    
    try:
        generator = ThumbnailGenerator()
        print("✅ ThumbnailGenerator created")
        
        best_frame_path, analysis = generator.select_best_frame(
            video_path=video_path,
            num_candidates=5
        )
        
        print(f"✅ Best frame selected: {best_frame_path}")
        print(f"📊 Analysis score: {analysis.get('overall_score', 'N/A')}")
        print("✅ Thumbnail generation works!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_thumbnail_gen()
