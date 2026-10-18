#!/usr/bin/env python3
"""
Delete Duplicates in iPhone Import Folder

This script:
1. Scans the iPhone import folder for duplicate files
2. Uses file hash (size + name + mtime) to identify duplicates
3. Deletes duplicate files, keeping the first occurrence
4. Reports what was deleted
"""
import hashlib
import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import json

# Default import path
DEFAULT_IMPORT_PATH = Path.home() / "Documents" / "IphoneImport"


def get_file_hash(file_path: Path) -> str:
    """Generate a hash for file identification (using size + name + mtime)"""
    try:
        stat = file_path.stat()
        hash_input = f"{file_path.name}:{stat.st_size}:{int(stat.st_mtime)}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    except Exception as e:
        print(f"  ⚠️  Error hashing {file_path}: {e}")
        return ""


def get_content_hash(file_path: Path) -> str:
    """Generate a hash based on file content (for true duplicate detection)"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"  ⚠️  Error hashing content of {file_path}: {e}")
        return ""


def find_duplicates_by_hash(import_path: Path, use_content_hash: bool = False) -> Dict[str, List[Path]]:
    """Find duplicate files by hash"""
    print(f"🔍 Scanning for duplicates in: {import_path}")
    print(f"   Method: {'Content hash' if use_content_hash else 'File metadata hash'}")
    print("")
    
    hash_to_files: Dict[str, List[Path]] = defaultdict(list)
    total_files = 0
    processed = 0
    
    # First pass: collect all files
    for file_path in import_path.rglob("*"):
        if not file_path.is_file():
            continue
        
        total_files += 1
        if total_files % 100 == 0:
            print(f"  📂 Scanned {total_files} files...", end='\r')
    
    print(f"  📂 Found {total_files} files")
    print("  🔍 Analyzing duplicates...")
    print("")
    
    # Second pass: hash files
    for file_path in import_path.rglob("*"):
        if not file_path.is_file():
            continue
        
        processed += 1
        if processed % 100 == 0:
            print(f"  ⏳ Processed {processed}/{total_files} files...", end='\r')
        
        if use_content_hash:
            file_hash = get_content_hash(file_path)
        else:
            file_hash = get_file_hash(file_path)
        
        if file_hash:
            hash_to_files[file_hash].append(file_path)
    
    print(f"  ✅ Processed {processed} files")
    print("")
    
    # Find duplicates (hashes with more than one file)
    duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
    
    return duplicates


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def delete_duplicates(duplicates: Dict[str, List[Path]], dry_run: bool = True) -> Tuple[int, int]:
    """Delete duplicate files, keeping the first occurrence"""
    deleted_count = 0
    freed_bytes = 0
    
    print(f"\n{'🔍 DRY RUN - ' if dry_run else '🗑️  DELETING '}Duplicates:")
    print("=" * 60)
    
    for hash_val, files in duplicates.items():
        if len(files) <= 1:
            continue
        
        # Sort by path (keep the first one alphabetically)
        files_sorted = sorted(files)
        keep_file = files_sorted[0]
        delete_files = files_sorted[1:]
        
        print(f"\n📁 Duplicate Group ({len(files)} files):")
        print(f"   ✅ Keep: {keep_file.relative_to(keep_file.parents[len(keep_file.parts) - 3])}")
        
        for delete_file in delete_files:
            try:
                file_size = delete_file.stat().st_size
                freed_bytes += file_size
                
                if dry_run:
                    print(f"   🗑️  Would delete: {delete_file.relative_to(delete_file.parents[len(delete_file.parts) - 3])} ({format_size(file_size)})")
                else:
                    delete_file.unlink()
                    deleted_count += 1
                    print(f"   ✅ Deleted: {delete_file.relative_to(delete_file.parents[len(delete_file.parts) - 3])} ({format_size(file_size)})")
            except Exception as e:
                print(f"   ❌ Error deleting {delete_file}: {e}")
    
    return deleted_count, freed_bytes


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete duplicates in iPhone import folder")
    parser.add_argument(
        "--path",
        type=str,
        default=str(DEFAULT_IMPORT_PATH),
        help=f"Path to iPhone import folder (default: {DEFAULT_IMPORT_PATH})"
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
    
    import_path = Path(args.path).expanduser()
    
    if not import_path.exists():
        print(f"❌ Import path not found: {import_path}")
        print(f"💡 Please provide a valid path:")
        print(f"   python {sys.argv[0]} --path /path/to/IphoneImport")
        return 1
    
    if not import_path.is_dir():
        print(f"❌ Path is not a directory: {import_path}")
        return 1
    
    print("=" * 60)
    print("🗑️  Delete Duplicates in iPhone Import Folder")
    print("=" * 60)
    print(f"📂 Import Path: {import_path}")
    print(f"🔍 Method: {'Content hash' if args.content_hash else 'Metadata hash'}")
    print(f"⚙️  Mode: {'DRY RUN' if not args.execute else 'DELETE MODE'}")
    print("=" * 60)
    print("")
    
    # Find duplicates
    duplicates = find_duplicates_by_hash(import_path, use_content_hash=args.content_hash)
    
    if not duplicates:
        print("✅ No duplicates found!")
        return 0
    
    total_duplicate_files = sum(len(files) - 1 for files in duplicates.values())
    print(f"📊 Found {len(duplicates)} duplicate groups")
    print(f"📊 Total duplicate files: {total_duplicate_files}")
    print("")
    
    # Calculate total size
    total_size = 0
    for files in duplicates.values():
        for file_path in files[1:]:  # Skip first (kept) file
            try:
                total_size += file_path.stat().st_size
            except:
                pass
    
    print(f"💾 Total space that can be freed: {format_size(total_size)}")
    print("")
    
    # Delete duplicates
    deleted_count, freed_bytes = delete_duplicates(duplicates, dry_run=not args.execute)
    
    if not args.execute:
        print("\n" + "=" * 60)
        print("🔍 DRY RUN COMPLETE")
        print("=" * 60)
        print(f"📊 Would delete: {total_duplicate_files} files")
        print(f"💾 Would free: {format_size(total_size)}")
        print("")
        print("💡 To actually delete, run with --execute flag:")
        print(f"   python {sys.argv[0]} --path {import_path} --execute")
        if not args.content_hash:
            print("   (Add --content-hash for more accurate duplicate detection)")
    else:
        # Confirmation
        if not args.confirm:
            print("\n" + "=" * 60)
            print("⚠️  WARNING: This will PERMANENTLY DELETE files!")
            print("=" * 60)
            response = input(f"Delete {total_duplicate_files} duplicate files? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("❌ Cancelled")
                return 1
        
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

