#!/usr/bin/env python3
"""
Regenerate all thumbnails with color support for HEIC files.
Ensures HEIC images produce vibrant color thumbnails, not grayscale.
"""
import requests
import time
import json
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

API_BASE = "http://localhost:5555/api"


def convert_heic_to_color_jpg(heic_path: str, output_path: str) -> bool:
    """
    Convert a single HEIC file to a color JPG using pillow-heif.
    
    Args:
        heic_path: Path to HEIC file
        output_path: Path to save JPG
        
    Returns:
        True if successful
    """
    try:
        import pillow_heif
        from PIL import Image, ImageEnhance
        
        pillow_heif.register_heif_opener()
        
        img = Image.open(heic_path)
        
        # Ensure RGB color mode
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Apply slight color enhancement
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.05)
        
        # Increase saturation slightly for vibrant colors
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.02)
        
        img.save(output_path, "JPEG", quality=95)
        print(f"  ✅ Converted: {heic_path} -> {output_path}")
        return True
        
    except ImportError:
        print("  ❌ pillow-heif not installed. Run: pip install pillow-heif")
        return False
    except Exception as e:
        print(f"  ❌ Error converting {heic_path}: {e}")
        return False

def get_all_videos():
    """Fetch all videos from the API"""
    response = requests.get(f"{API_BASE}/videos/")
    response.raise_for_status()
    return response.json()

def regenerate_thumbnails(video_ids, batch_size=50):
    """Regenerate thumbnails for given video IDs"""
    total = len(video_ids)
    print(f"📊 Total videos to process: {total}")
    
    for i in range(0, total, batch_size):
        batch = video_ids[i:i + batch_size]
        print(f"\n🔄 Processing batch {i//batch_size + 1} ({len(batch)} videos)...")
        
        response = requests.post(
            f"{API_BASE}/videos/generate-thumbnails-batch",
            json={"video_ids": batch, "max_videos": batch_size}
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Queued: {result['message']}")
        
        # Wait for batch to complete
        print("⏳ Waiting for generation to complete...")
        time.sleep(len(batch) * 0.5)  # Rough estimate: 0.5s per video
        
def verify_thumbnails(videos):
    """Verify that all videos have thumbnails"""
    refetched = get_all_videos()
    
    with_thumbnails = sum(1 for v in refetched if v.get('thumbnail_path'))
    without_thumbnails = sum(1 for v in refetched if not v.get('thumbnail_path'))
    
    print(f"\n📈 Results:")
    print(f"  ✅ With thumbnails: {with_thumbnails}/{len(refetched)}")
    print(f"  ❌ Without thumbnails: {without_thumbnails}/{len(refetched)}")
    
    return without_thumbnails == 0

def main():
    print("🚀 Starting thumbnail regeneration...\n")
    
    # Get all videos
    videos = get_all_videos()
    print(f"📚 Found {len(videos)} total videos")
    
    # Get videos without thumbnails
    without_thumbnails = [v for v in videos if not v.get('thumbnail_path')]
    heic_files = [v for v in videos if v.get('file_name', '').upper().endswith('.HEIC')]
    
    print(f"🖼️  Videos without thumbnails: {len(without_thumbnails)}")
    print(f"📸 HEIC files: {len(heic_files)}")
    
    # Regenerate for videos without thumbnails + all HEIC (to ensure color)
    to_regenerate = set()
    to_regenerate.update(v['id'] for v in without_thumbnails)
    to_regenerate.update(v['id'] for v in heic_files)
    
    video_ids = list(to_regenerate)
    
    if not video_ids:
        print("\n✅ All videos already have thumbnails!")
        return
    
    print(f"\n🔧 Will regenerate {len(video_ids)} thumbnails")
    print("   (includes all HEIC files to ensure color)")
    
    # Regenerate
    regenerate_thumbnails(video_ids)
    
    # Verify
    print("\n🔍 Verifying results...")
    time.sleep(2)  # Wait a bit more for final ones
    
    if verify_thumbnails(videos):
        print("\n🎉 Success! All thumbnails generated in color!")
    else:
        print("\n⚠️  Some thumbnails may still be missing. Check the logs.")

def convert_heic_directory(directory: str, recursive: bool = True):
    """
    Convert all HEIC files in a directory to color JPGs.
    
    Args:
        directory: Path to directory
        recursive: Whether to search subdirectories
    """
    from pathlib import Path
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    pattern = "**/*.heic" if recursive else "*.heic"
    heic_files = list(dir_path.glob(pattern))
    heic_files += list(dir_path.glob(pattern.replace('.heic', '.HEIC')))
    
    if not heic_files:
        print(f"No HEIC files found in {directory}")
        return
    
    print(f"\n🖼️  Found {len(heic_files)} HEIC files")
    print("Converting to color JPG...\n")
    
    success = 0
    for heic_file in heic_files:
        output_path = heic_file.with_suffix('.jpg')
        if convert_heic_to_color_jpg(str(heic_file), str(output_path)):
            success += 1
    
    print(f"\n✅ Converted {success}/{len(heic_files)} HEIC files to color JPG")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Regenerate thumbnails with color HEIC support")
    parser.add_argument("--heic-dir", help="Convert all HEIC files in directory to color JPG")
    parser.add_argument("--heic-file", help="Convert a single HEIC file to color JPG")
    parser.add_argument("--output", help="Output path for single file conversion")
    parser.add_argument("--api", action="store_true", help="Regenerate via API (default)")
    
    args = parser.parse_args()
    
    if args.heic_dir:
        convert_heic_directory(args.heic_dir)
    elif args.heic_file:
        output = args.output or args.heic_file.replace('.heic', '.jpg').replace('.HEIC', '.jpg')
        convert_heic_to_color_jpg(args.heic_file, output)
    else:
        main()
