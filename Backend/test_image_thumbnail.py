"""
Test thumbnail generation for images (PNG/HEIC)
"""
import sys
import os
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')

from services.thumbnail_generator import ThumbnailGenerator
from pathlib import Path

def test_image_thumbnail():
    # Test files
    png_path = "/Users/isaiahdupree/Documents/IphoneImport/IMG_0811.PNG"
    heic_path = "/Users/isaiahdupree/Documents/IphoneImport/IMG_3445.HEIC"
    
    files_to_test = [png_path, heic_path]
    
    generator = ThumbnailGenerator()
    
    for file_path in files_to_test:
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"\n🖼️  Testing thumbnail generation for: {file_path}")
        
        try:
            # Test extract_frames directly
            frames = generator.extract_frames(file_path, num_frames=1)
            print(f"✅ Extracted frames: {frames}")
            
            if not frames:
                print("❌ No frames returned")
                continue
                
            # Test full generation flow
            best_frame_path, analysis = generator.select_best_frame(
                video_path=file_path,
                num_candidates=1
            )
            
            print(f"✅ Best frame selected: {best_frame_path}")
            print(f"📊 Analysis score: {analysis.get('overall_score', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_image_thumbnail()
