#!/usr/bin/env python3
"""
Find Duplicate Filenames and Clean Import Folder

This script:
1. Finds files with duplicate filenames (same name, different paths)
2. If no duplicates found, deletes ~5GB of recently imported files
"""
import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime
import argparse

# Default import path
DEFAULT_IMPORT_PATH = Path.home() / "Documents" / "IphoneImport"


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def find_duplicate_filenames(import_path: Path) -> Dict[str, List[Path]]:
    """Find files with duplicate filenames"""
    print(f"🔍 Scanning for duplicate filenames in: {import_path}")
    print("")
    
    filename_to_files: Dict[str, List[Path]] = defaultdict(list)
    total_files = 0
    
    for file_path in import_path.rglob("*"):
        if not file_path.is_file():
            continue
        
        total_files += 1
        if total_files % 1000 == 0:
            print(f"  📂 Scanned {total_files} files...", end='\r')
        
        filename = file_path.name
        filename_to_files[filename].append(file_path)
    
    print(f"  ✅ Scanned {total_files} files")
    print("")
    
    # Find duplicates (filenames with more than one file)
    duplicates = {name: files for name, files in filename_to_files.items() if len(files) > 1}
    
    return duplicates


def get_recent_files(import_path: Path, target_size_gb: float = 5.0) -> List[Tuple[Path, int, float]]:
    """Get recently imported files sorted by modification time (newest first)"""
    print(f"🔍 Finding recent files to delete (~{target_size_gb}GB)...")
    print("")
    
    files_with_info = []
    total_files = 0
    
    for file_path in import_path.rglob("*"):
        if not file_path.is_file():
            continue
        
        total_files += 1
        if total_files % 1000 == 0:
            print(f"  📂 Scanned {total_files} files...", end='\r')
        
        try:
            stat = file_path.stat()
            size_bytes = stat.st_size
            mtime = stat.st_mtime
            
            # Only include videos and images
            ext = file_path.suffix.lower()
            video_exts = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm', '.3gp', '.hevc'}
            image_exts = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif', '.webp', '.tiff', '.bmp'}
            
            if ext in video_exts or ext in image_exts:
                files_with_info.append((file_path, size_bytes, mtime))
        except Exception as e:
            continue
    
    print(f"  ✅ Scanned {total_files} files")
    print("")
    
    # Sort by modification time (newest first)
    files_with_info.sort(key=lambda x: x[2], reverse=True)
    
    # Select files until we reach target size
    selected_files = []
    total_size = 0
    target_size_bytes = target_size_gb * 1024 * 1024 * 1024
    
    for file_path, size_bytes, mtime in files_with_info:
        if total_size >= target_size_bytes:
            break
        selected_files.append((file_path, size_bytes, mtime))
        total_size += size_bytes
    
    return selected_files


def delete_files(files: List[Tuple[Path, int, float]], dry_run: bool = True) -> Tuple[int, int]:
    """Delete files"""
    deleted_count = 0
    freed_bytes = 0
    
    print(f"\n{'🔍 DRY RUN - ' if dry_run else '🗑️  DELETING '}Files:")
    print("=" * 60)
    
    for file_path, size_bytes, mtime in files:
        try:
            freed_bytes += size_bytes
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            if dry_run:
                print(f"   🗑️  Would delete: {file_path.name} ({format_size(size_bytes)}) - {mtime_str}")
            else:
                file_path.unlink()
                deleted_count += 1
                print(f"   ✅ Deleted: {file_path.name} ({format_size(size_bytes)}) - {mtime_str}")
        except Exception as e:
            print(f"   ❌ Error deleting {file_path}: {e}")
    
    return deleted_count, freed_bytes


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Find duplicate filenames or clean import folder")
    parser.add_argument(
        "--path",
        type=str,
        default=str(DEFAULT_IMPORT_PATH),
        help=f"Path to iPhone import folder (default: {DEFAULT_IMPORT_PATH})"
    )
    parser.add_argument(
        "--size-gb",
        type=float,
        default=5.0,
        help="Target size to delete in GB (default: 5.0)"
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
    
    import_path = Path(args.path).expanduser()
    
    if not import_path.exists():
        print(f"❌ Import path not found: {import_path}")
        return 1
    
    if not import_path.is_dir():
        print(f"❌ Path is not a directory: {import_path}")
        return 1
    
    print("=" * 60)
    print("🔍 Find Duplicate Filenames & Clean Import Folder")
    print("=" * 60)
    print(f"📂 Import Path: {import_path}")
    print(f"⚙️  Mode: {'DRY RUN' if not args.execute else 'DELETE MODE'}")
    print("=" * 60)
    print("")
    
    # Step 1: Find duplicate filenames
    print("📋 Step 1: Finding duplicate filenames...")
    duplicates = find_duplicate_filenames(import_path)
    
    if duplicates:
        print(f"✅ Found {len(duplicates)} duplicate filename groups")
        print("")
        
        total_duplicate_files = sum(len(files) - 1 for files in duplicates.values())
        total_size = 0
        
        print("📊 Duplicate Filename Groups:")
        print("=" * 60)
        
        for filename, files in list(duplicates.items())[:20]:  # Show first 20
            print(f"\n📁 Filename: {filename} ({len(files)} copies)")
            for i, file_path in enumerate(files):
                try:
                    size = file_path.stat().st_size
                    if i == 0:
                        print(f"   ✅ Keep: {file_path.parent.name}/{filename} ({format_size(size)})")
                    else:
                        print(f"   🗑️  Delete: {file_path.parent.name}/{filename} ({format_size(size)})")
                        total_size += size
                except:
                    pass
        
        if len(duplicates) > 20:
            print(f"\n   ... and {len(duplicates) - 20} more groups")
        
        print("")
        print(f"💾 Total space that can be freed: {format_size(total_size)}")
        print("")
        
        # Delete duplicates
        deleted_count = 0
        freed_bytes = 0
        
        for filename, files in duplicates.items():
            if len(files) <= 1:
                continue
            
            # Keep the first file (alphabetically by path), delete the rest
            files_sorted = sorted(files)
            keep_file = files_sorted[0]
            delete_files_list = files_sorted[1:]
            
            for delete_file in delete_files_list:
                try:
                    file_size = delete_file.stat().st_size
                    freed_bytes += file_size
                    
                    if not args.execute:
                        print(f"   🗑️  Would delete: {delete_file.parent.name}/{filename} ({format_size(file_size)})")
                    else:
                        delete_file.unlink()
                        deleted_count += 1
                        print(f"   ✅ Deleted: {delete_file.parent.name}/{filename} ({format_size(file_size)})")
                except Exception as e:
                    print(f"   ❌ Error deleting {delete_file}: {e}")
        
        if not args.execute:
            print("\n" + "=" * 60)
            print("🔍 DRY RUN COMPLETE")
            print("=" * 60)
            print(f"📊 Would delete: {total_duplicate_files} duplicate files")
            print(f"💾 Would free: {format_size(freed_bytes)}")
            print("")
            print("💡 To actually delete, run with --execute flag:")
            print(f"   python {sys.argv[0]} --path {import_path} --execute")
        else:
            print("\n" + "=" * 60)
            print("✅ DELETION COMPLETE")
            print("=" * 60)
            print(f"📊 Deleted: {deleted_count} duplicate files")
            print(f"💾 Freed: {format_size(freed_bytes)}")
        
        return 0
    
    else:
        print("✅ No duplicate filenames found")
        print("")
        
        # Step 2: Delete recent files
        print(f"📋 Step 2: Finding recent files to delete (~{args.size_gb}GB)...")
        recent_files = get_recent_files(import_path, target_size_gb=args.size_gb)
        
        if not recent_files:
            print("❌ No files found to delete")
            return 1
        
        total_size = sum(size for _, size, _ in recent_files)
        print(f"📊 Found {len(recent_files)} files to delete")
        print(f"💾 Total size: {format_size(total_size)}")
        print("")
        
        # Show preview
        print("📋 Preview (first 20 files):")
        for file_path, size_bytes, mtime in recent_files[:20]:
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"   • {file_path.name} ({format_size(size_bytes)}) - {mtime_str}")
        
        if len(recent_files) > 20:
            print(f"   ... and {len(recent_files) - 20} more files")
        
        print("")
        
        # Delete files
        if not args.execute:
            print("=" * 60)
            print("🔍 DRY RUN COMPLETE")
            print("=" * 60)
            print(f"📊 Would delete: {len(recent_files)} files")
            print(f"💾 Would free: {format_size(total_size)}")
            print("")
            print("💡 To actually delete, run with --execute flag:")
            print(f"   python {sys.argv[0]} --path {import_path} --execute --size-gb {args.size_gb}")
        else:
            # Confirmation
            if not args.confirm:
                print("=" * 60)
                print("⚠️  WARNING: This will PERMANENTLY DELETE files!")
                print("=" * 60)
                response = input(f"Delete {len(recent_files)} recent files (~{format_size(total_size)})? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("❌ Cancelled")
                    return 1
            
            deleted_count, freed_bytes = delete_files(recent_files, dry_run=False)
            
            print("\n" + "=" * 60)
            print("✅ DELETION COMPLETE")
            print("=" * 60)
            print(f"📊 Deleted: {deleted_count} files")
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

