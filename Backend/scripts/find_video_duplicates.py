#!/usr/bin/env python3
"""
Find Video Duplicates - Simplified
==================================
1. Find folders with videos on My Passport (skip code/backup folders)
2. Compare with IphoneImport
3. Delete duplicates from IphoneImport
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIG
# =============================================================================

MY_PASSPORT = "/Volumes/My Passport"
IPHONE_IMPORT = "/Users/isaiahdupree/Documents/IphoneImport"

VIDEO_EXT = {'.mov', '.mp4', '.m4v', '.MOV', '.MP4', '.M4V'}

# Skip these folders (not video content)
SKIP_FOLDERS = {
    'Coding_backup', 'coding_backup', 
    '$RECYCLE.BIN', '.fseventsd', 
    'System Volume Information',
    'SolidWorks 2017', 'FLSUN v400',
    'config', 'mappings', 'Downloads',
    '.Spotlight-V100', '.Trashes'
}

# =============================================================================
# MAIN
# =============================================================================

def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"

def main():
    print("=" * 60)
    print("🎬 FINDING VIDEO FOLDERS ON MY PASSPORT")
    print("=" * 60)
    
    if not os.path.exists(MY_PASSPORT):
        print(f"❌ My Passport not mounted at {MY_PASSPORT}")
        return
    
    # Step 1: Find folders with videos on My Passport
    print(f"\n📂 Scanning top-level folders for videos...")
    
    video_folders = {}
    passport_videos = {}  # filename -> {path, size}
    
    for item in sorted(os.listdir(MY_PASSPORT)):
        # Skip system/code folders
        if item.startswith('.') or item.startswith('$'):
            continue
        if any(skip.lower() in item.lower() for skip in SKIP_FOLDERS):
            print(f"   ⏭️  Skipping: {item}")
            continue
        
        item_path = os.path.join(MY_PASSPORT, item)
        
        # Check if it's a video file at root
        if os.path.isfile(item_path):
            ext = Path(item).suffix
            if ext in VIDEO_EXT:
                size = os.path.getsize(item_path)
                passport_videos[item] = {"path": item_path, "size": size}
                print(f"   📹 Root video: {item} ({format_size(size)})")
            continue
        
        # Scan folder for videos
        if os.path.isdir(item_path):
            folder_videos = []
            folder_size = 0
            
            for root, dirs, files in os.walk(item_path):
                # Skip nested system folders
                dirs[:] = [d for d in dirs if not any(skip.lower() in d.lower() for skip in SKIP_FOLDERS)]
                
                for f in files:
                    ext = Path(f).suffix
                    if ext in VIDEO_EXT:
                        fp = os.path.join(root, f)
                        try:
                            size = os.path.getsize(fp)
                            folder_videos.append(f)
                            folder_size += size
                            passport_videos[f] = {"path": fp, "size": size}
                        except:
                            pass
            
            if folder_videos:
                video_folders[item] = {
                    "count": len(folder_videos),
                    "size": folder_size
                }
                print(f"   📂 {item}: {len(folder_videos)} videos ({format_size(folder_size)})")
    
    print(f"\n✅ Found {len(passport_videos)} total videos on My Passport")
    
    # Step 2: Index IphoneImport videos
    print("\n" + "=" * 60)
    print("📱 SCANNING IPHONE IMPORT")
    print("=" * 60)
    
    iphone_videos = {}
    count = 0
    
    for f in os.listdir(IPHONE_IMPORT):
        ext = Path(f).suffix
        if ext in VIDEO_EXT:
            fp = os.path.join(IPHONE_IMPORT, f)
            try:
                size = os.path.getsize(fp)
                iphone_videos[f] = {"path": fp, "size": size}
                count += 1
            except:
                pass
    
    print(f"✅ Found {count} videos in IphoneImport")
    
    # Step 3: Find duplicates
    print("\n" + "=" * 60)
    print("🔍 FINDING DUPLICATES")
    print("=" * 60)
    
    duplicates = []
    
    for filename, passport_info in passport_videos.items():
        if filename in iphone_videos:
            iphone_info = iphone_videos[filename]
            # Match by filename AND similar size (within 1%)
            size_diff = abs(passport_info["size"] - iphone_info["size"])
            size_tolerance = max(passport_info["size"], iphone_info["size"]) * 0.01
            
            if size_diff <= size_tolerance:
                duplicates.append({
                    "filename": filename,
                    "passport_path": passport_info["path"],
                    "iphone_path": iphone_info["path"],
                    "size": iphone_info["size"]
                })
    
    if not duplicates:
        print("✨ No duplicates found!")
        return
    
    total_size = sum(d["size"] for d in duplicates)
    print(f"\n🔍 Found {len(duplicates)} duplicates!")
    print(f"   Total size to free: {format_size(total_size)}")
    
    # Save report
    report_path = "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/logs/duplicates_report.txt"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(f"DUPLICATE VIDEOS REPORT - {datetime.now()}\n")
        f.write(f"Files to delete from IphoneImport: {len(duplicates)}\n")
        f.write(f"Space to free: {format_size(total_size)}\n")
        f.write("=" * 60 + "\n\n")
        
        for d in sorted(duplicates, key=lambda x: x["size"], reverse=True):
            f.write(f"{d['filename']} ({format_size(d['size'])})\n")
            f.write(f"  KEEP:   {d['passport_path']}\n")
            f.write(f"  DELETE: {d['iphone_path']}\n\n")
    
    print(f"\n📄 Report saved: {report_path}")
    
    # Step 4: Delete?
    print("\n" + "=" * 60)
    print("🗑️  DELETE DUPLICATES FROM IPHONE IMPORT?")
    print("=" * 60)
    
    if "--delete" in sys.argv:
        confirm = input(f"\n⚠️  Delete {len(duplicates)} files from IphoneImport? (yes/no): ")
        if confirm.lower() == "yes":
            deleted = 0
            freed = 0
            for d in duplicates:
                try:
                    os.remove(d["iphone_path"])
                    print(f"   ✅ Deleted: {d['filename']}")
                    deleted += 1
                    freed += d["size"]
                except Exception as e:
                    print(f"   ❌ Failed: {d['filename']}: {e}")
            
            print(f"\n✅ Deleted {deleted} files, freed {format_size(freed)}")
        else:
            print("Cancelled.")
    else:
        print(f"\nRun with --delete to remove duplicates:")
        print(f"  python3 find_video_duplicates.py --delete")

if __name__ == "__main__":
    main()
