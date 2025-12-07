#!/usr/bin/env python3
"""
iPhone Video Importer - Direct USB Import
Automatically detect and import videos from connected iPhone
"""
import subprocess
import os
from pathlib import Path
from datetime import datetime
import time

class iPhoneImporter:
    """Import videos from iPhone via USB"""
    
    def __init__(self, destination_dir: Path = None):
        self.destination_dir = destination_dir or Path.home() / "Downloads" / "iPhone_Videos"
        self.destination_dir.mkdir(parents=True, exist_ok=True)
    
    def is_iphone_connected(self) -> bool:
        """Check if iPhone is connected via USB"""
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return 'iPhone' in result.stdout
        except Exception as e:
            print(f"Error checking USB devices: {e}")
            return False
    
    def get_iphone_info(self) -> dict:
        """Get iPhone details"""
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            lines = result.stdout.split('\n')
            iphone_info = {}
            in_iphone_section = False
            
            for line in lines:
                if 'iPhone' in line:
                    in_iphone_section = True
                    iphone_info['name'] = line.strip().replace(':', '')
                elif in_iphone_section:
                    if 'Product ID' in line:
                        iphone_info['product_id'] = line.split(':')[1].strip()
                    elif 'Serial Number' in line:
                        iphone_info['serial'] = line.split(':')[1].strip()
                    elif line.strip() and not line.startswith(' ' * 10):
                        break  # End of iPhone section
            
            return iphone_info
        except Exception as e:
            print(f"Error getting iPhone info: {e}")
            return {}
    
    def open_image_capture(self):
        """Open Image Capture app for manual import"""
        print("\n📱 Opening Image Capture...")
        print("Instructions:")
        print("  1. Select your iPhone in the left sidebar")
        print("  2. Select videos to import")
        print("  3. Click 'Import' or 'Import All'")
        print(f"  4. Videos will be imported to: {self.destination_dir}")
        
        try:
            subprocess.run(['open', '-a', 'Image Capture'])
            return True
        except Exception as e:
            print(f"Error opening Image Capture: {e}")
            return False
    
    def watch_for_new_videos(self, duration_seconds: int = 300):
        """Watch destination directory for new videos"""
        print(f"\n👀 Watching for new videos in: {self.destination_dir}")
        print(f"Duration: {duration_seconds}s ({duration_seconds//60} minutes)")
        print("Import videos now, and I'll detect them!\n")
        
        # Get existing videos
        existing = set()
        for pattern in ['*.mp4', '*.mov', '*.m4v', '*.MOV', '*.MP4']:
            existing.update(self.destination_dir.glob(pattern))
        
        print(f"Existing videos: {len(existing)}")
        
        start_time = time.time()
        new_videos = []
        
        try:
            while time.time() - start_time < duration_seconds:
                # Check for new videos
                current = set()
                for pattern in ['*.mp4', '*.mov', '*.m4v', '*.MOV', '*.MP4']:
                    current.update(self.destination_dir.glob(pattern))
                
                new = current - existing
                
                if new:
                    for video in new:
                        print(f"✓ New video detected: {video.name}")
                        new_videos.append(video)
                        existing.add(video)
                
                time.sleep(2)  # Check every 2 seconds
        
        except KeyboardInterrupt:
            print("\n\nStopped watching")
        
        return new_videos
    
    def import_with_photos_app(self):
        """Open Photos app for import"""
        print("\n📱 Opening Photos app...")
        print("Instructions:")
        print("  1. Your iPhone should appear in the sidebar")
        print("  2. Select videos to import")
        print("  3. Click 'Import Selected' or 'Import All New Videos'")
        print("  4. Videos will be in Photos library")
        
        try:
            subprocess.run(['open', '-a', 'Photos'])
            return True
        except Exception as e:
            print(f"Error opening Photos: {e}")
            return False


def main():
    """Main import flow"""
    print("\n" + "="*60)
    print("  iPhone Video Importer - USB Direct Import")
    print("="*60)
    
    importer = iPhoneImporter()
    
    # Check if iPhone is connected
    print("\n🔍 Checking for iPhone...")
    if importer.is_iphone_connected():
        print("✓ iPhone detected!")
        
        # Get iPhone info
        info = importer.get_iphone_info()
        if info:
            print(f"\nDevice: {info.get('name', 'iPhone')}")
            if 'serial' in info:
                print(f"Serial: {info['serial']}")
    else:
        print("✗ No iPhone detected via USB")
        print("\nMake sure:")
        print("  1. iPhone is plugged in via USB cable")
        print("  2. iPhone is unlocked")
        print("  3. You've tapped 'Trust This Computer' on iPhone")
        print("\nPlease connect your iPhone and run again.")
        return
    
    # Choose import method
    print("\n" + "="*60)
    print("Choose Import Method:")
    print("="*60)
    print("1. Image Capture (Recommended - Direct control)")
    print("2. Photos App (Organizes in library)")
    print("3. Watch folder for manual import")
    print("4. Cancel")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        print(f"\n📁 Import destination: {importer.destination_dir}")
        print("\nTip: In Image Capture, change 'Import To' dropdown to:")
        print(f"  {importer.destination_dir}")
        input("\nPress Enter to open Image Capture...")
        importer.open_image_capture()
        
        # Watch for new videos
        print("\nWould you like me to watch for new videos? (y/n): ", end='')
        if input().lower() == 'y':
            duration = 300  # 5 minutes
            new_videos = importer.watch_for_new_videos(duration)
            
            if new_videos:
                print(f"\n✓ Imported {len(new_videos)} video(s)!")
                for video in new_videos:
                    print(f"  - {video.name} ({video.stat().st_size / (1024*1024):.1f} MB)")
                
                print(f"\n🎬 Videos are ready at: {importer.destination_dir}")
                print("\n💡 Next steps:")
                print("  1. Videos will appear in MediaPoster server")
                print("  2. Refresh: curl http://localhost:8000/api/videos/scan")
                print("  3. Or open: http://localhost:8000/docs")
    
    elif choice == '2':
        importer.import_with_photos_app()
        print("\n⚠️  Note: Videos imported via Photos app will be in:")
        print("  ~/Pictures/Photos Library.photoslibrary")
        print("  These may not appear in MediaPoster's default scan")
    
    elif choice == '3':
        print(f"\n📁 Watching: {importer.destination_dir}")
        print("\nImport videos manually (AirDrop, Finder, etc.)")
        print("I'll detect them automatically!\n")
        
        duration = int(input("Watch duration in seconds (default 300): ") or "300")
        new_videos = importer.watch_for_new_videos(duration)
        
        if new_videos:
            print(f"\n✓ Detected {len(new_videos)} new video(s)!")
    
    else:
        print("\nCancelled")
    
    print("\n" + "="*60)
    print("✓ Import complete!")
    print("="*60)


if __name__ == "__main__":
    main()
