#!/usr/bin/env python3
"""
Compare Passport and iPhone Import Videos

This script:
1. Scans Passport folder for videos
2. Scans iPhone Import folder for videos
3. Compares videos to find duplicates
4. Deletes duplicates from Passport that exist in iPhone Import

Extensive logging is provided for all operations.
"""
import hashlib
import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set
import argparse
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# Default paths
DEFAULT_IPHONE_IMPORT = Path.home() / "Documents" / "IphoneImport"
DEFAULT_PASSPORT = Path("/Volumes/Passport")  # Common external drive name

# Setup logging
LOG_DIR = Path("/tmp/mediaposter/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "passport_duplicate_cleanup.log"

# Create logger
logger = logging.getLogger("passport_cleanup")
logger.setLevel(logging.DEBUG)

# File handler with rotation
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)-8s | %(message)s')
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


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
        logger.debug(f"Error hashing content of {file_path}: {e}")
        return ""


def scan_videos(folder: Path, use_content_hash: bool = False, source_name: str = "Unknown") -> Dict[str, List[Path]]:
    """Scan folder for videos and return hash -> files mapping"""
    import time
    start_time = time.time()
    
    logger.info(f"Starting video scan: folder={folder}, method={'content_hash' if use_content_hash else 'metadata_hash'}, source={source_name}")
    print(f"🔍 Scanning videos in: {folder}")
    print(f"   Method: {'Content hash (slower, more accurate)' if use_content_hash else 'Metadata hash (fast)'}")
    print("")
    
    video_exts = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm', '.3gp', '.hevc', '.MOV', '.MP4'}
    hash_to_files: Dict[str, List[Path]] = defaultdict(list)
    total_files = 0
    video_count = 0
    errors = []
    skipped = []
    last_progress_time = time.time()
    
    try:
        # First pass: count videos for progress estimation
        logger.info("First pass: counting video files...")
        video_paths = []
        for file_path in folder.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in video_exts:
                video_paths.append(file_path)
        
        total_videos = len(video_paths)
        logger.info(f"Found {total_videos} video files to process")
        print(f"  📊 Found {total_videos} video files to process")
        print("")
        
        # Second pass: hash videos
        logger.info("Second pass: hashing video files...")
        for i, file_path in enumerate(video_paths, 1):
            total_files += 1
            video_count += 1
            
            # Show progress every 100 files or every 5 seconds
            current_time = time.time()
            if i % 100 == 0 or (current_time - last_progress_time) >= 5:
                elapsed = current_time - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (total_videos - i) / rate if rate > 0 else 0
                progress_pct = (i / total_videos * 100) if total_videos > 0 else 0
                
                print(f"  ⏳ Progress: {i}/{total_videos} ({progress_pct:.1f}%) | "
                      f"Rate: {rate:.1f} files/sec | "
                      f"ETA: {remaining/60:.1f} min", end='\r')
                logger.debug(f"Progress: {i}/{total_videos} ({progress_pct:.1f}%)")
                last_progress_time = current_time
            
            try:
                if use_content_hash:
                    file_hash = get_file_hash_content(file_path)
                    if i % 50 == 0:  # Log less frequently for content hash
                        logger.debug(f"Content hash for {file_path.name}: {file_hash[:16]}...")
                else:
                    file_hash = get_file_hash_fast(file_path)
                
                if file_hash:
                    hash_to_files[file_hash].append(file_path)
                    if i % 1000 == 0:  # Log every 1000th file
                        logger.debug(f"Added video {i}: {file_path.name} (hash: {file_hash[:16]}...)")
                else:
                    skipped.append(str(file_path))
                    logger.warning(f"Failed to generate hash for: {file_path}")
            except Exception as e:
                errors.append((str(file_path), str(e)))
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Scan complete: {total_files} files scanned, {video_count} videos found, {len(errors)} errors, {len(skipped)} skipped, took {elapsed_time:.1f}s")
        print(f"\n  ✅ Scanned {total_files} files, found {video_count} videos in {elapsed_time:.1f}s")
        
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during scan")
            for file_path, error in errors[:10]:  # Log first 10 errors
                logger.warning(f"  Error with {Path(file_path).name}: {error}")
        
        if skipped:
            logger.info(f"Skipped {len(skipped)} files (could not generate hash)")
        
        print("")
        
    except Exception as e:
        logger.error(f"Critical error during scan: {e}", exc_info=True)
        raise
    
    return hash_to_files


def find_duplicates(
    passport_videos: Dict[str, List[Path]],
    iphone_videos: Dict[str, List[Path]]
) -> List[Tuple[Path, Path]]:
    """Find videos in Passport that match videos in iPhone Import"""
    logger.info("Starting duplicate comparison")
    logger.info(f"Passport videos: {sum(len(files) for files in passport_videos.values())} unique hashes")
    logger.info(f"iPhone videos: {sum(len(files) for files in iphone_videos.values())} unique hashes")
    
    duplicates = []
    matches_found = 0
    
    print("🔍 Comparing videos...")
    logger.info("Comparing video hashes to find duplicates...")
    
    for hash_val, passport_files in passport_videos.items():
        if hash_val in iphone_videos:
            # Found a match!
            matches_found += 1
            iphone_files = iphone_videos[hash_val]
            
            logger.info(f"Match #{matches_found} found (hash: {hash_val[:16]}...):")
            logger.info(f"  Passport files: {len(passport_files)}")
            logger.info(f"  iPhone files: {len(iphone_files)}")
            
            # For each passport file, mark it as duplicate if iPhone has a match
            for passport_file in passport_files:
                for iphone_file in iphone_files:
                    duplicates.append((passport_file, iphone_file))
                    logger.info(f"  Duplicate pair: {passport_file.name} <-> {iphone_file.name}")
                    logger.debug(f"    Passport: {passport_file}")
                    logger.debug(f"    iPhone: {iphone_file}")
    
    logger.info(f"Comparison complete: {matches_found} hash matches, {len(duplicates)} duplicate pairs found")
    print(f"  ✅ Found {matches_found} matching hash groups")
    
    return duplicates


def delete_duplicates(duplicates: List[Tuple[Path, Path]], dry_run: bool = True) -> Tuple[int, int]:
    """Delete duplicate files from Passport"""
    logger.info(f"Starting deletion process: dry_run={dry_run}, {len(duplicates)} duplicate pairs")
    
    deleted_count = 0
    freed_bytes = 0
    errors = []
    
    # Group by passport file (to avoid deleting same file multiple times)
    passport_files_to_delete: Set[Path] = set()
    for passport_file, iphone_file in duplicates:
        passport_files_to_delete.add(passport_file)
    
    logger.info(f"Unique Passport files to delete: {len(passport_files_to_delete)}")
    
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
            
            logger.info(f"Processing: {passport_file.name} ({format_size(file_size)})")
            if matching_iphone:
                logger.info(f"  Matches: {matching_iphone.name} in iPhone Import")
            
            if dry_run:
                print(f"   🗑️  Would delete: {passport_file.name}")
                if matching_iphone:
                    print(f"      (matches: {matching_iphone.name} in iPhone Import)")
                print(f"      Size: {format_size(file_size)}")
                logger.debug(f"  DRY RUN: Would delete {passport_file}")
            else:
                logger.info(f"  Deleting: {passport_file}")
                passport_file.unlink()
                deleted_count += 1
                logger.info(f"  ✅ Successfully deleted: {passport_file.name}")
                print(f"   ✅ Deleted: {passport_file.name} ({format_size(file_size)})")
                if matching_iphone:
                    print(f"      (matched: {matching_iphone.name})")
        except FileNotFoundError:
            error_msg = f"File not found (may have been deleted): {passport_file}"
            errors.append((str(passport_file), error_msg))
            logger.warning(error_msg)
            print(f"   ⚠️  File not found: {passport_file.name} (may have been deleted)")
        except PermissionError:
            error_msg = f"Permission denied: {passport_file}"
            errors.append((str(passport_file), error_msg))
            logger.error(error_msg)
            print(f"   ❌ Permission denied: {passport_file.name}")
        except Exception as e:
            error_msg = f"Error deleting {passport_file}: {e}"
            errors.append((str(passport_file), str(e)))
            logger.error(error_msg, exc_info=True)
            print(f"   ❌ Error deleting {passport_file.name}: {e}")
    
    logger.info(f"Deletion complete: {deleted_count} deleted, {len(errors)} errors, {format_size(freed_bytes)} freed")
    if errors:
        logger.warning(f"Encountered {len(errors)} errors during deletion")
        for file_path, error in errors:
            logger.warning(f"  Error with {Path(file_path).name}: {error}")
    
    return deleted_count, freed_bytes


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("Starting Passport Duplicate Cleanup Process")
    logger.info("=" * 80)
    
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
    logger.info("Locating Passport folder...")
    passport_path = None
    if args.passport:
        passport_path = Path(args.passport).expanduser()
        logger.info(f"Using provided Passport path: {passport_path}")
    else:
        # Try common locations
        possible_paths = [
            Path("/Volumes/Passport"),
            Path("/Volumes/My Passport"),
            Path.home() / "Passport",
            Path.home() / "Documents" / "Passport",
        ]
        
        logger.info(f"Searching for Passport in {len(possible_paths)} possible locations...")
        for path in possible_paths:
            logger.debug(f"  Checking: {path}")
            if path.exists() and path.is_dir():
                passport_path = path
                logger.info(f"  ✅ Found Passport at: {path}")
                break
            else:
                logger.debug(f"  ❌ Not found: {path}")
        
        if not passport_path:
            logger.error("Passport folder not found in any searched location")
            print("❌ Passport folder not found. Please specify with --passport")
            print("   Searched locations:")
            for path in possible_paths:
                print(f"     • {path}")
            return 1
    
    iphone_path = Path(args.iphone_import).expanduser()
    
    logger.info(f"Passport path: {passport_path}")
    logger.info(f"iPhone Import path: {iphone_path}")
    
    if not passport_path.exists():
        logger.error(f"Passport path does not exist: {passport_path}")
        print(f"❌ Passport path not found: {passport_path}")
        return 1
    
    if not iphone_path.exists():
        logger.error(f"iPhone Import path does not exist: {iphone_path}")
        print(f"❌ iPhone Import path not found: {iphone_path}")
        return 1
    
    logger.info("Both paths verified and exist")
    
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
    logger.info("=" * 80)
    logger.info("STEP 1: Scanning iPhone Import folder")
    logger.info("=" * 80)
    print("📋 Step 1: Scanning iPhone Import folder...")
    iphone_videos = scan_videos(iphone_path, use_content_hash=args.content_hash, source_name="iPhone Import")
    iphone_count = sum(len(files) for files in iphone_videos.values())
    logger.info(f"iPhone Import scan complete: {iphone_count} videos found, {len(iphone_videos)} unique hashes")
    print(f"   ✅ Found {iphone_count} videos")
    print("")
    
    # Step 2: Scan Passport
    logger.info("=" * 80)
    logger.info("STEP 2: Scanning Passport folder")
    logger.info("=" * 80)
    print("📋 Step 2: Scanning Passport folder...")
    passport_videos = scan_videos(passport_path, use_content_hash=args.content_hash, source_name="Passport")
    passport_count = sum(len(files) for files in passport_videos.values())
    logger.info(f"Passport scan complete: {passport_count} videos found, {len(passport_videos)} unique hashes")
    print(f"   ✅ Found {passport_count} videos")
    print("")
    
    # Step 3: Find duplicates
    logger.info("=" * 80)
    logger.info("STEP 3: Finding duplicates")
    logger.info("=" * 80)
    print("📋 Step 3: Finding duplicates...")
    duplicates = find_duplicates(passport_videos, iphone_videos)
    
    if not duplicates:
        logger.info("No duplicates found - cleanup complete")
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
    logger.info("=" * 80)
    logger.info("STEP 4: Deletion Process")
    logger.info("=" * 80)
    
    if not args.execute:
        logger.info("DRY RUN MODE - No files will be deleted")
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
        logger.info(f"Dry run complete: Would delete {len(passport_files_to_delete)} files, free {format_size(total_size)}")
    else:
        logger.info("EXECUTE MODE - Files will be permanently deleted")
        # Confirmation
        if not args.confirm:
            print("=" * 60)
            print("⚠️  WARNING: This will PERMANENTLY DELETE files from Passport!")
            print("=" * 60)
            response = input(f"Delete {len(passport_files_to_delete)} duplicate files from Passport? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.warning("User cancelled deletion")
                print("❌ Cancelled")
                return 1
            logger.info("User confirmed deletion")
        
        logger.info("Starting actual deletion...")
        deleted_count, freed_bytes = delete_duplicates(duplicates, dry_run=False)
        
        logger.info("=" * 80)
        logger.info("DELETION COMPLETE")
        logger.info(f"Deleted: {deleted_count} files")
        logger.info(f"Freed: {format_size(freed_bytes)}")
        logger.info("=" * 80)
        
        print("\n" + "=" * 60)
        print("✅ DELETION COMPLETE")
        print("=" * 60)
        print(f"📊 Deleted: {deleted_count} files from Passport")
        print(f"💾 Freed: {format_size(freed_bytes)}")
        print(f"\n📝 Full log saved to: {LOG_FILE}")
    
    logger.info("=" * 80)
    logger.info("Process Complete")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    try:
        logger.info(f"Script started: {sys.argv}")
        result = main()
        logger.info(f"Script completed with exit code: {result}")
        sys.exit(result)
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
        print("\n\n⚠️  Interrupted by user")
        print(f"📝 Partial log saved to: {LOG_FILE}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\n\n❌ Error: {e}")
        print(f"📝 Full error log saved to: {LOG_FILE}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

