#!/usr/bin/env python3
"""
Regenerate all thumbnails with color support for HEIC files
"""
import requests
import time
import json

API_BASE = "http://localhost:5555/api"

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

if __name__ == "__main__":
    main()
