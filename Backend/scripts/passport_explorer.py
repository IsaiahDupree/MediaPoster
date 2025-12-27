#!/usr/bin/env python3
"""
My Passport Explorer & Duplicate Cleaner
========================================
1. Explores My Passport drive structure
2. Creates clear inventory of contents
3. Finds duplicates between My Passport and IphoneImport
4. Deletes duplicates FROM IphoneImport (keeps My Passport copies)
"""

import os
import sys
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# =============================================================================
# CONFIGURATION
# =============================================================================

MY_PASSPORT = "/Volumes/My Passport"
IPHONE_IMPORT = "/Users/isaiahdupree/Documents/IphoneImport"
OUTPUT_DIR = Path("/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/logs")

VIDEO_EXT = {'.mov', '.mp4', '.m4v', '.avi', '.mkv', '.MOV', '.MP4', '.M4V'}
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.JPG', '.JPEG', '.PNG', '.HEIC'}

# =============================================================================
# LOGGING
# =============================================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = OUTPUT_DIR / f"passport_explore_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# =============================================================================
# STEP 1: EXPLORE MY PASSPORT
# =============================================================================

def explore_passport():
    """Explore and document My Passport structure."""
    log.info("=" * 60)
    log.info("STEP 1: EXPLORING MY PASSPORT DRIVE")
    log.info("=" * 60)
    
    if not os.path.exists(MY_PASSPORT):
        log.error(f"My Passport not mounted at {MY_PASSPORT}")
        return None
    
    log.info(f"📂 Reading top-level contents of {MY_PASSPORT}...")
    
    inventory = {}
    total_files = 0
    total_size = 0
    
    # Get top-level directories
    all_items = sorted(os.listdir(MY_PASSPORT))
    log.info(f"   Found {len(all_items)} top-level items")
    
    top_level = []
    processed = 0
    
    for item in all_items:
        if item.startswith('.') or item.startswith('$') or item == 'System Volume Information':
            log.info(f"   ⏭️  Skipping system folder: {item}")
            continue
        
        processed += 1
        item_path = os.path.join(MY_PASSPORT, item)
        
        if os.path.isdir(item_path):
            log.info(f"   [{processed}] 📂 Scanning folder: {item}...")
            # Count contents
            file_count = 0
            dir_size = 0
            scan_count = 0
            for root, dirs, files in os.walk(item_path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        dir_size += os.path.getsize(fp)
                        file_count += 1
                        scan_count += 1
                        if scan_count % 1000 == 0:
                            log.info(f"       ... scanned {scan_count} files in {item}")
                    except:
                        pass
            
            log.info(f"       ✅ {item}: {file_count} files, {format_size(dir_size)}")
            top_level.append({
                "name": item,
                "type": "directory",
                "files": file_count,
                "size": dir_size,
                "size_human": format_size(dir_size)
            })
            total_files += file_count
            total_size += dir_size
        else:
            fsize = os.path.getsize(item_path) if os.path.exists(item_path) else 0
            log.info(f"   [{processed}] 📄 File: {item} ({format_size(fsize)})")
            top_level.append({
                "name": item,
                "type": "file",
                "size": fsize,
                "size_human": format_size(fsize)
            })
            total_files += 1
            total_size += fsize
    
    # Print inventory
    log.info(f"\n📁 MY PASSPORT CONTENTS ({format_size(total_size)} total, {total_files} files)")
    log.info("-" * 60)
    
    # Sort by size descending
    top_level.sort(key=lambda x: x.get('size', 0), reverse=True)
    
    for item in top_level:
        if item["type"] == "directory":
            log.info(f"  📂 {item['name']:50} {item['size_human']:>12} ({item['files']} files)")
        else:
            log.info(f"  📄 {item['name']:50} {item['size_human']:>12}")
    
    # Save to txt file
    txt_file = OUTPUT_DIR / f"passport_inventory_{timestamp}.txt"
    with open(txt_file, 'w') as f:
        f.write(f"MY PASSPORT INVENTORY - {datetime.now().isoformat()}\n")
        f.write(f"Total: {format_size(total_size)} | {total_files} files\n")
        f.write("=" * 70 + "\n\n")
        
        for item in top_level:
            if item["type"] == "directory":
                f.write(f"📂 {item['name']}\n")
                f.write(f"   Size: {item['size_human']} | Files: {item['files']}\n\n")
            else:
                f.write(f"📄 {item['name']} ({item['size_human']})\n")
    
    log.info(f"\n✅ Inventory saved to: {txt_file}")
    return top_level


def format_size(size_bytes):
    """Format bytes as human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


# =============================================================================
# STEP 2: BUILD FILE INDEX
# =============================================================================

def build_file_index(path, label):
    """Build index of video/image files by filename and size."""
    log.info(f"\n📊 Building index for: {label}")
    log.info(f"   Path: {path}")
    
    index = {}  # filename -> {path, size}
    count = 0
    scanned = 0
    dirs_scanned = 0
    
    for root, dirs, files in os.walk(path):
        # Skip system directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['$RECYCLE.BIN', 'System Volume Information']]
        
        dirs_scanned += 1
        if dirs_scanned % 50 == 0:
            log.info(f"   ... scanned {dirs_scanned} directories, found {count} media files so far")
        
        for filename in files:
            scanned += 1
            ext = Path(filename).suffix.lower()
            if ext in {e.lower() for e in VIDEO_EXT | IMAGE_EXT}:
                filepath = os.path.join(root, filename)
                try:
                    size = os.path.getsize(filepath)
                    index[filename] = {
                        "path": filepath,
                        "size": size,
                        "ext": ext
                    }
                    count += 1
                    if count % 500 == 0:
                        log.info(f"   ... indexed {count} media files")
                except Exception as e:
                    log.warning(f"   ⚠️  Could not read: {filename}: {e}")
    
    log.info(f"   ✅ Finished: {count} video/image files indexed from {scanned} total files")
    return index


# =============================================================================
# STEP 3: FIND DUPLICATES
# =============================================================================

def find_duplicates(passport_index, iphone_index):
    """Find files that exist in both locations (by filename AND size)."""
    log.info("\n" + "=" * 60)
    log.info("STEP 3: FINDING DUPLICATES")
    log.info("=" * 60)
    
    duplicates = []
    
    for filename, passport_info in passport_index.items():
        if filename in iphone_index:
            iphone_info = iphone_index[filename]
            # Match by filename AND similar size (within 1%)
            size_diff = abs(passport_info["size"] - iphone_info["size"])
            size_tolerance = max(passport_info["size"], iphone_info["size"]) * 0.01
            
            if size_diff <= size_tolerance:
                duplicates.append({
                    "filename": filename,
                    "passport_path": passport_info["path"],
                    "iphone_path": iphone_info["path"],
                    "size": iphone_info["size"],
                    "size_human": format_size(iphone_info["size"])
                })
    
    log.info(f"\n🔍 Found {len(duplicates)} duplicate files")
    
    if duplicates:
        total_dup_size = sum(d["size"] for d in duplicates)
        log.info(f"   Total size to free: {format_size(total_dup_size)}")
        
        # Save duplicate report
        dup_file = OUTPUT_DIR / f"duplicates_to_delete_{timestamp}.txt"
        with open(dup_file, 'w') as f:
            f.write(f"DUPLICATES FOUND - {datetime.now().isoformat()}\n")
            f.write(f"These files exist in BOTH My Passport AND IphoneImport\n")
            f.write(f"Recommendation: DELETE from IphoneImport (keep My Passport)\n")
            f.write(f"Total: {len(duplicates)} files | {format_size(total_dup_size)}\n")
            f.write("=" * 70 + "\n\n")
            
            for d in sorted(duplicates, key=lambda x: x["size"], reverse=True):
                f.write(f"📄 {d['filename']} ({d['size_human']})\n")
                f.write(f"   KEEP:   {d['passport_path']}\n")
                f.write(f"   DELETE: {d['iphone_path']}\n\n")
        
        log.info(f"✅ Duplicate report saved to: {dup_file}")
    
    return duplicates


# =============================================================================
# STEP 4: DELETE DUPLICATES FROM IPHONE IMPORT
# =============================================================================

def delete_duplicates(duplicates, dry_run=True):
    """Delete duplicate files from IphoneImport folder."""
    log.info("\n" + "=" * 60)
    if dry_run:
        log.info("STEP 4: DRY RUN - SIMULATING DELETE")
    else:
        log.info("STEP 4: DELETING DUPLICATES FROM IPHONE IMPORT")
    log.info("=" * 60)
    
    deleted = 0
    freed = 0
    errors = []
    
    for d in duplicates:
        iphone_path = d["iphone_path"]
        
        if dry_run:
            log.info(f"  [DRY RUN] Would delete: {d['filename']} ({d['size_human']})")
            deleted += 1
            freed += d["size"]
        else:
            try:
                os.remove(iphone_path)
                log.info(f"  ✅ Deleted: {d['filename']} ({d['size_human']})")
                deleted += 1
                freed += d["size"]
            except Exception as e:
                log.error(f"  ❌ Failed to delete {d['filename']}: {e}")
                errors.append({"file": d["filename"], "error": str(e)})
    
    log.info(f"\n📊 Summary:")
    log.info(f"   Files deleted: {deleted}")
    log.info(f"   Space freed: {format_size(freed)}")
    if errors:
        log.warning(f"   Errors: {len(errors)}")
    
    return deleted, freed, errors


# =============================================================================
# MAIN
# =============================================================================

def main():
    log.info("🚀 MY PASSPORT EXPLORER & DUPLICATE CLEANER")
    log.info(f"   Log file: {log_file}")
    log.info("")
    
    # Step 1: Explore My Passport
    inventory = explore_passport()
    if not inventory:
        return
    
    # Step 2: Build file indexes
    log.info("\n" + "=" * 60)
    log.info("STEP 2: BUILDING FILE INDEXES")
    log.info("=" * 60)
    
    passport_index = build_file_index(MY_PASSPORT, "My Passport")
    iphone_index = build_file_index(IPHONE_IMPORT, "IphoneImport")
    
    # Step 3: Find duplicates
    duplicates = find_duplicates(passport_index, iphone_index)
    
    if not duplicates:
        log.info("\n✨ No duplicates found! Nothing to delete.")
        return
    
    # Step 4: Delete (dry run first)
    log.info("\n" + "=" * 60)
    log.info("READY TO DELETE DUPLICATES")
    log.info("=" * 60)
    log.info(f"\nFound {len(duplicates)} duplicates to delete from IphoneImport")
    log.info("Run with --delete flag to actually delete files")
    log.info("Example: python passport_explorer.py --delete")
    
    if "--delete" in sys.argv:
        confirm = input("\n⚠️  Are you sure you want to delete duplicates from IphoneImport? (yes/no): ")
        if confirm.lower() == "yes":
            delete_duplicates(duplicates, dry_run=False)
        else:
            log.info("Cancelled.")
    else:
        delete_duplicates(duplicates, dry_run=True)
    
    log.info("\n✅ Done!")


if __name__ == "__main__":
    main()
