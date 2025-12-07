#!/usr/bin/env python3
"""
Programmatic iPhone Import via Image Capture (macOS)
Works on macOS without ifuse
"""
import subprocess
from pathlib import Path
import time

class ImageCaptureImporter:
    """Import videos using Image Capture automation"""
    
    def __init__(self, destination=None):
        self.destination = destination or Path.home() / "Downloads" / "iPhone_Videos"
        self.destination.mkdir(parents=True, exist_ok=True)
    
    def get_device_udid(self):
        """Get connected iPhone UDID"""
        result = subprocess.run(
            ['idevice_id', '-l'],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() if result.returncode == 0 else None
    
    def get_device_name(self):
        """Get iPhone name"""
        result = subprocess.run(
            ['ideviceinfo', '-k', 'DeviceName'],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() if result.returncode == 0 else "iPhone"
    
    def open_image_capture_to_device(self):
        """Open Image Capture directly to iPhone"""
        print("\n📱 Opening Image Capture...")
        print(f"📁 Import destination: {self.destination}")
        print("\nIn Image Capture:")
        print("  1. Select your iPhone in left sidebar")
        print("  2. Select videos to import")
        print("  3. Choose 'Import To': Downloads/iPhone_Videos")
        print("  4. Click 'Import' or 'Import All'")
        print("\n⏳ Waiting for import...")
        
        # Open Image Capture
        subprocess.run(['open', '-a', 'Image Capture'])
        return True
    
    def watch_for_imports(self, duration=300):
        """Watch for newly imported files"""
        print(f"\n👀 Watching {self.destination} for new videos...")
        print(f"Duration: {duration}s (~{duration//60} minutes)\n")
        
        # Snapshot existing files
        existing = set()
        for pattern in ['*.mp4', '*.mov', '*.m4v', '*.MOV', '*.MP4']:
            existing.update(self.destination.glob(pattern))
        
        print(f"Existing: {len(existing)} videos")
        
        new_videos = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                current = set()
                for pattern in ['*.mp4', '*.mov', '*.m4v', '*.MOV', '*.MP4']:
                    current.update(self.destination.glob(pattern))
                
                new = current - existing
                
                for video in new:
                    size_mb = video.stat().st_size / (1024 * 1024)
                    print(f"✓ New video: {video.name} ({size_mb:.1f} MB)")
                    new_videos.append(video)
                    existing.add(video)
                
                time.sleep(2)
        
        except KeyboardInterrupt:
            print("\n\nStopped watching")
        
        return new_videos

def main():
    print("\n" + "="*60)
    print("  iPhone Video Import - Image Capture Method")
    print("="*60)
    
    importer = ImageCaptureImporter()
    
    # Check device
    print("\n🔍 Checking for iPhone...")
    udid = importer.get_device_udid()
    
    if not udid:
        print("✗ No iPhone detected")
        print("\nMake sure:")
        print("  1. iPhone is connected via USB")
        print("  2. iPhone is unlocked")
        print("  3. Device is trusted")
        return
    
    name = importer.get_device_name()
    print(f"✓ iPhone detected: {name}")
    print(f"  UDID: {udid}")
    
    # Open Image Capture
    print("\n" + "="*60)
    importer.open_image_capture_to_device()
    
    # Ask to watch
    print("\nWatch for new videos? (y/n): ", end='')
    if input().strip().lower() == 'y':
        duration = 300  # 5 minutes
        new_videos = importer.watch_for_imports(duration)
        
        if new_videos:
            print(f"\n✓ Imported {len(new_videos)} video(s)!")
            for video in new_videos:
                print(f"  - {video}")
            
            print(f"\n📁 Location: {importer.destination}")
            print("\n💡 Videos ready for MediaPoster processing!")
        else:
            print("\n⚠️ No new videos detected")
            print("Make sure you clicked 'Import' in Image Capture")

if __name__ == "__main__":
    main()
