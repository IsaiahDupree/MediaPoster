#!/usr/bin/env python3
"""
Compare Passport and iPhone Import Videos

This script:
1. Scans Passport folder for videos
2. Scans iPhone Import folder for videos
3. Compares videos to find duplicates
4. Deletes duplicates from Passport that exist in iPhone Import
"""
import hashlib
import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set
import argparse
from datetime import datetime

# Default paths
DEFAULT_IPHONE_IMPORT = Path.home() / "Documents" / "IphoneImport"
DEFAULT_PASSPORT = Path("/Volumes/Passport")  # Common external drive name


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_file_hash_fast(file_path: Path) -> str:
    """Generate a fast hash using filename + size + mtime"""
    try:
        stat = file_path.stat()
        hash_input = f"{file_path.name}:{stat.st_size}:{int(stat.st_mtime)}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    except Exception as e:
        return ""


def get_file_hash_content(file_path: Path) -> str:
    """Generate a hash based on file content (slower but more accurate)"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            # Read first 1MB for quick comparison
            chunk = f.read(1024 * 1024)
            hash_md5.update(chunk)
            # Also read last 1MB
            if stat := file_path.stat():
                if stat.st_size > 2 * 1024 * 1024:
                    f.seek(-1024 * 1024, 2)
                    chunk = f.read(1024 * 1024)
                    hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return ""


def scan_videos(folder: Path, use_content_hash: bool = False) -> Dict[str, List[Path]]:
    """Scan folder for videos and return hash -> files mapping"""
    print(f"🔍 Scanning videos in: {folder}")
    
    video_exts = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm', '.3gp', '.hevc', '.MOV', '.MP4'}
    hash_to_files: Dict[str, List[Path]] = defaultdict(list)
    total_files = 0
    video_count = 0
    
    for file_path in folder.rglob("*"):
        if not file_path.is_file():
            continue
        
        total_files += 1
        if total_files % 1000 == 0:
            print(f"  📂 Scanned {total_files} files, found {video_count} videos...", end='\r')
        
        if file_path.suffix.lower() not in video_exts:
            continue
        
        video_count += 1
        
        if use_content_hash:
            file_hash = get_file_hash_content(file_path)
        else:
            file_hash = get_file_hash_fast(file_path)
        
        if file_hash:
            hash_to_files[file_hash].append(file_path)
    
    print(f"  ✅ Scanned {total_files} files, found {video_count} videos")
    print("")
    
    return hash_to_files


def find_duplicates(
    passport_videos: Dict[str, List[Path]],
    iphone_videos: Dict[str, List[Path]]
) -> List[Tuple[Path, Path]]:
    """Find videos in Passport that match videos in iPhone Import"""
    duplicates = []
    
    print("🔍 Comparing videos...")
    
    for hash_val, passport_files in passport_videos.items():
        if hash_val in iphone_videos:
            # Found a match!
            iphone_files = iphone_videos[hash_val]
            
            # For each passport file, mark it as duplicate if iPhone has a match
            for passport_file in passport_files:
                for iphone_file in iphone_files:
                    duplicates.append((passport_file, iphone_file))
    
    return duplicates


def delete_duplicates(duplicates: List[Tuple[Path, Path]], dry_run: bool = True) -> Tuple[int, int]:
    """Delete duplicate files from Passport"""
    deleted_count = 0
    freed_bytes = 0
    
    # Group by passport file (to avoid deleting same file multiple times)
    passport_files_to_delete: Set[Path] = set()
    for passport_file, iphone_file in duplicates:
        passport_files_to_delete.add(passport_file)
    
    print(f"\n{'🔍 DRY RUN - ' if dry_run else '🗑️  DELETING '}Duplicates from Passport:")
    print("=" * 60)
    
    for passport_file in sorted(passport_files_to_delete):
        try:
            file_size = passport_file.stat().st_size
            freed_bytes += file_size
            
            # Find matching iPhone file for display
            matching_iphone = None
            for p_file, i_file in duplicates:
                if p_file == passport_file:
                    matching_iphone = i_file
                    break
            
            if dry_run:
                print(f"   🗑️  Would delete: {passport_file.name}")
                if matching_iphone:
                    print(f"      (matches: {matching_iphone.name} in iPhone Import)")
                print(f"      Size: {format_size(file_size)}")
            else:
                passport_file.unlink()
                deleted_count += 1
                print(f"   ✅ Deleted: {passport_file.name} ({format_size(file_size)})")
                if matching_iphone:
                    print(f"      (matched: {matching_iphone.name})")
        except Exception as e:
            print(f"   ❌ Error deleting {passport_file}: {e}")
    
    return deleted_count, freed_bytes


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Compare Passport and iPhone Import videos, delete duplicates from Passport")
    parser.add_argument(
        "--passport",
        type=str,
        help="Path to Passport folder (default: /Volumes/Passport or will search)"
    )
    parser.add_argument(
        "--iphone-import",
        type=str,
        default=str(DEFAULT_IPHONE_IMPORT),
        help=f"Path to iPhone Import folder (default: {DEFAULT_IPHONE_IMPORT})"
    )
    parser.add_argument(
        "--content-hash",
        action="store_true",
        help="Use content hash instead of metadata hash (slower but more accurate)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete files (default is dry-run)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Find Passport folder
    passport_path = None
    if args.passport:
        passport_path = Path(args.passport).expanduser()
    else:
        # Try common locations
        possible_paths = [
            Path("/Volumes/Passport"),
            Path("/Volumes/My Passport"),
            Path.home() / "Passport",
            Path.home() / "Documents" / "Passport",
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                passport_path = path
                break
        
        if not passport_path:
            print("❌ Passport folder not found. Please specify with --passport")
            print("   Searched locations:")
            for path in possible_paths:
                print(f"     • {path}")
            return 1
    
    iphone_path = Path(args.iphone_import).expanduser()
    
    if not passport_path.exists():
        print(f"❌ Passport path not found: {passport_path}")
        return 1
    
    if not iphone_path.exists():
        print(f"❌ iPhone Import path not found: {iphone_path}")
        return 1
    
    print("=" * 60)
    print("🔍 Compare Passport and iPhone Import Videos")
    print("=" * 60)
    print(f"📂 Passport: {passport_path}")
    print(f"📂 iPhone Import: {iphone_path}")
    print(f"🔍 Method: {'Content hash' if args.content_hash else 'Metadata hash'}")
    print(f"⚙️  Mode: {'DRY RUN' if not args.execute else 'DELETE MODE'}")
    print("=" * 60)
    print("")
    
    # Step 1: Scan iPhone Import
    print("📋 Step 1: Scanning iPhone Import folder...")
    iphone_videos = scan_videos(iphone_path, use_content_hash=args.content_hash)
    print(f"   ✅ Found {sum(len(files) for files in iphone_videos.values())} videos")
    print("")
    
    # Step 2: Scan Passport
    print("📋 Step 2: Scanning Passport folder...")
    passport_videos = scan_videos(passport_path, use_content_hash=args.content_hash)
    print(f"   ✅ Found {sum(len(files) for files in passport_videos.values())} videos")
    print("")
    
    # Step 3: Find duplicates
    print("📋 Step 3: Finding duplicates...")
    duplicates = find_duplicates(passport_videos, iphone_videos)
    
    if not duplicates:
        print("✅ No duplicates found!")
        return 0
    
    # Group duplicates
    passport_files_to_delete: Set[Path] = set()
    for passport_file, iphone_file in duplicates:
        passport_files_to_delete.add(passport_file)
    
    total_size = sum(f.stat().st_size for f in passport_files_to_delete if f.exists())
    
    print(f"📊 Found {len(passport_files_to_delete)} duplicate videos in Passport")
    print(f"💾 Total size: {format_size(total_size)}")
    print("")
    
    # Show preview
    print("📋 Preview (first 20 duplicates):")
    for i, passport_file in enumerate(sorted(passport_files_to_delete)[:20]):
        try:
            size = passport_file.stat().st_size
            print(f"   • {passport_file.name} ({format_size(size)})")
        except:
            pass
    
    if len(passport_files_to_delete) > 20:
        print(f"   ... and {len(passport_files_to_delete) - 20} more files")
    
    print("")
    
    # Delete duplicates
    if not args.execute:
        print("=" * 60)
        print("🔍 DRY RUN COMPLETE")
        print("=" * 60)
        print(f"📊 Would delete: {len(passport_files_to_delete)} files from Passport")
        print(f"💾 Would free: {format_size(total_size)}")
        print("")
        print("💡 To actually delete, run with --execute flag:")
        print(f"   python {sys.argv[0]} --passport {passport_path} --execute")
        if not args.content_hash:
            print("   (Add --content-hash for more accurate duplicate detection)")
    else:
        # Confirmation
        if not args.confirm:
            print("=" * 60)
            print("⚠️  WARNING: This will PERMANENTLY DELETE files from Passport!")
            print("=" * 60)
            response = input(f"Delete {len(passport_files_to_delete)} duplicate files from Passport? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("❌ Cancelled")
                return 1
        
        deleted_count, freed_bytes = delete_duplicates(duplicates, dry_run=False)
        
        print("\n" + "=" * 60)
        print("✅ DELETION COMPLETE")
        print("=" * 60)
        print(f"📊 Deleted: {deleted_count} files from Passport")
        print(f"💾 Freed: {format_size(freed_bytes)}")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

