#!/usr/bin/env python3
"""
Comprehensive Passport Drive Organization

This script creates organizational documentation for the Passport drive.
Since the drive is read-only, it creates local documentation that can be
used to organize files when write access is available.

Features:
1. Scans entire drive structure
2. Creates INDEX.txt files locally (mirroring drive structure)
3. Generates master organizational report
4. Creates per-directory documentation
5. Can be run again when write access is available to place files on drive
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import shutil

# Setup logging
LOG_DIR = Path("/tmp/mediaposter/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "passport_organization.log"

logger = logging.getLogger("passport_organize")
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)-8s | %(message)s')
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

INDEX_FILENAME = "INDEX.txt"


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def scan_directory(directory: Path, max_depth: Optional[int] = None, current_depth: int = 0) -> Dict:
    """Scan a directory and collect information"""
    logger.info(f"Scanning directory: {directory} (depth: {current_depth})")
    
    info = {
        "path": str(directory),
        "name": directory.name,
        "depth": current_depth,
        "directories": [],
        "files": [],
        "total_files": 0,
        "total_size": 0,
        "file_types": {},
        "subdirectory_count": 0
    }
    
    try:
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Directory does not exist: {directory}")
            return info
        
        if max_depth is not None and current_depth >= max_depth:
            logger.debug(f"Reached max depth {max_depth} at {directory}")
            return info
        
        try:
            items = list(directory.iterdir())
        except (PermissionError, OSError) as e:
            logger.warning(f"Permission denied: {directory} - {e}")
            info["error"] = str(e)
            return info
        except Exception as e:
            logger.error(f"Error reading {directory}: {e}", exc_info=True)
            info["error"] = str(e)
            return info
        
        dirs = sorted([item for item in items if item.is_dir()])
        files = sorted([item for item in items if item.is_file()])
        
        logger.debug(f"Found {len(dirs)} directories and {len(files)} files in {directory.name}")
        
        # Process subdirectories
        for subdir in dirs:
            if subdir.name.startswith('.') or subdir.name.startswith('$'):
                continue
            
            try:
                subdir_info = scan_directory(subdir, max_depth, current_depth + 1)
                info["directories"].append(subdir_info)
                info["subdirectory_count"] += 1 + subdir_info.get("subdirectory_count", 0)
                info["total_files"] += subdir_info.get("total_files", 0)
                info["total_size"] += subdir_info.get("total_size", 0)
            except Exception as e:
                logger.error(f"Error processing subdirectory {subdir}: {e}", exc_info=True)
        
        # Process files
        for file_path in files:
            if file_path.name == INDEX_FILENAME:
                continue
            
            try:
                stat = file_path.stat()
                file_size = stat.st_size
                file_ext = file_path.suffix.lower() or "(no extension)"
                
                file_info = {
                    "name": file_path.name,
                    "size": file_size,
                    "size_formatted": format_size(file_size),
                    "extension": file_ext,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                }
                
                info["files"].append(file_info)
                info["total_files"] += 1
                info["total_size"] += file_size
                
                if file_ext not in info["file_types"]:
                    info["file_types"][file_ext] = {"count": 0, "size": 0}
                info["file_types"][file_ext]["count"] += 1
                info["file_types"][file_ext]["size"] += file_size
                
            except Exception as e:
                logger.warning(f"Error processing file {file_path}: {e}")
        
        logger.info(f"Completed scanning {directory.name}: {len(info['directories'])} dirs, {len(info['files'])} files, {format_size(info['total_size'])}")
        
    except Exception as e:
        logger.error(f"Critical error scanning {directory}: {e}", exc_info=True)
        info["error"] = str(e)
    
    return info


def create_index_content(info: Dict) -> str:
    """Create INDEX.txt content for a directory"""
    lines = []
    lines.append("=" * 80)
    lines.append(f"DIRECTORY INDEX: {info['name']}")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Path: {info['path']}")
    lines.append("")
    
    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Directories: {len(info['directories'])}")
    lines.append(f"Files: {len(info['files'])}")
    lines.append(f"Total Size: {format_size(info['total_size'])}")
    if info.get("subdirectory_count", 0) > 0:
        lines.append(f"Total Subdirectories (recursive): {info['subdirectory_count']}")
    lines.append("")
    
    # File types breakdown
    if info.get("file_types"):
        lines.append("FILE TYPES")
        lines.append("-" * 80)
        for ext, data in sorted(info["file_types"].items(), key=lambda x: x[1]["size"], reverse=True):
            lines.append(f"  {ext:20s} {data['count']:5d} files  {format_size(data['size']):>12s}")
        lines.append("")
    
    # Directories
    if info["directories"]:
        lines.append("DIRECTORIES")
        lines.append("-" * 80)
        for subdir_info in info["directories"]:
            subdir_size = format_size(subdir_info.get("total_size", 0))
            subdir_files = subdir_info.get("total_files", 0)
            lines.append(f"  📁 {subdir_info['name']}/")
            lines.append(f"     Files: {subdir_files} | Size: {subdir_size}")
            if subdir_info.get("subdirectory_count", 0) > 0:
                lines.append(f"     Subdirectories: {subdir_info['subdirectory_count']}")
        lines.append("")
    
    # Files
    if info["files"]:
        lines.append("FILES")
        lines.append("-" * 80)
        files_by_type = {}
        for file_info in info["files"]:
            ext = file_info["extension"]
            if ext not in files_by_type:
                files_by_type[ext] = []
            files_by_type[ext].append(file_info)
        
        for ext in sorted(files_by_type.keys()):
            files_list = files_by_type[ext]
            lines.append(f"\n  {ext} ({len(files_list)} files):")
            for file_info in files_list[:100]:  # Limit to 100 files per type
                lines.append(f"    • {file_info['name']:50s} {file_info['size_formatted']:>12s}  {file_info['modified']}")
            if len(files_list) > 100:
                lines.append(f"    ... and {len(files_list) - 100} more files")
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("End of Index")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def organize_directory(
    source_dir: Path,
    local_base: Path,
    passport_path: Path,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    try_write: bool = False
) -> Tuple[int, int, int]:
    """Organize directory by creating index files"""
    logger.info(f"Organizing directory: {source_dir} (depth: {current_depth})")
    
    created_on_drive = 0
    created_local = 0
    error_count = 0
    
    try:
        if not source_dir.exists() or not source_dir.is_dir():
            return created_on_drive, created_local, error_count
        
        if max_depth is not None and current_depth >= max_depth:
            return created_on_drive, created_local, error_count
        
        # Scan directory
        info = scan_directory(source_dir, max_depth, current_depth)
        
        # Create relative path for local mirror
        try:
            relative_path = source_dir.relative_to(passport_path)
            local_dir = local_base / relative_path
        except ValueError:
            # If not a subdirectory, use name
            if source_dir == passport_path:
                local_dir = local_base
            else:
                local_dir = local_base / source_dir.name
        
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # Create index content
        index_content = create_index_content(info)
        
        # Try to write to drive if requested and possible
        if try_write:
            drive_index_path = source_dir / INDEX_FILENAME
            try:
                with open(drive_index_path, 'w', encoding='utf-8') as f:
                    f.write(index_content)
                logger.info(f"✅ Created index on drive: {drive_index_path}")
                created_on_drive += 1
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot write to drive: {source_dir} - {e}")
                error_count += 1
        
        # Always create local copy
        local_index_path = local_dir / INDEX_FILENAME
        try:
            with open(local_index_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
            logger.info(f"✅ Created local index: {local_index_path}")
            created_local += 1
        except Exception as e:
            logger.error(f"Error creating local index: {e}", exc_info=True)
            error_count += 1
        
        # Recursively organize subdirectories
        for subdir_info in info.get("directories", []):
            subdir_path = Path(subdir_info["path"])
            if subdir_path.name.startswith('.') or subdir_path.name.startswith('$'):
                continue
            
            sub_drive, sub_local, sub_errors = organize_directory(
                subdir_path, local_base, passport_path, max_depth, current_depth + 1, try_write
            )
            created_on_drive += sub_drive
            created_local += sub_local
            error_count += sub_errors
        
    except Exception as e:
        logger.error(f"Error organizing {source_dir}: {e}", exc_info=True)
        error_count += 1
    
    return created_on_drive, created_local, error_count


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("Comprehensive Passport Organization Script Started")
    logger.info("=" * 80)
    
    parser = argparse.ArgumentParser(description="Comprehensively organize Passport drive")
    parser.add_argument(
        "--passport",
        type=str,
        default="/Volumes/My Passport",
        help="Path to Passport drive"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="passport_organization_docs",
        help="Local output directory for documentation"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum directory depth to organize"
    )
    parser.add_argument(
        "--try-write",
        action="store_true",
        help="Try to write INDEX.txt files directly to drive (if write access available)"
    )
    
    args = parser.parse_args()
    
    passport_path = Path(args.passport).expanduser()
    output_dir = Path(args.output).expanduser().resolve()
    
    logger.info(f"Passport path: {passport_path}")
    logger.info(f"Output directory: {output_dir}")
    
    if not passport_path.exists():
        logger.error(f"Passport path does not exist: {passport_path}")
        print(f"❌ Passport drive not found: {passport_path}")
        print("   Please ensure the drive is mounted")
        return 1
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("📁 Comprehensive Passport Drive Organization")
    print("=" * 80)
    print(f"📂 Drive: {passport_path}")
    print(f"📁 Local Docs: {output_dir}")
    print(f"📏 Max depth: {args.max_depth if args.max_depth else 'unlimited'}")
    print(f"✍️  Try write to drive: {'Yes' if args.try_write else 'No (read-only)'}")
    print("")
    
    import time
    start_time = time.time()
    
    print("🔍 Scanning and organizing directories...")
    print("")
    
    created_on_drive, created_local, error_count = organize_directory(
        passport_path, output_dir, passport_path, args.max_depth, try_write=args.try_write
    )
    
    elapsed_time = time.time() - start_time
    
    # Create master index
    master_index = output_dir / "MASTER_INDEX.txt"
    with open(master_index, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PASSPORT DRIVE MASTER INDEX\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source: {passport_path}\n")
        f.write(f"Local Documentation: {output_dir}\n")
        f.write("\n")
        f.write("This directory contains organizational documentation for the Passport drive.\n")
        f.write("Each subdirectory mirrors the drive structure with INDEX.txt files.\n")
        f.write("\n")
        f.write(f"Index files created on drive: {created_on_drive}\n")
        f.write(f"Index files created locally: {created_local}\n")
        f.write(f"Errors: {error_count}\n")
        f.write(f"Time: {elapsed_time:.1f} seconds\n")
    
    print("")
    print("=" * 80)
    print("✅ ORGANIZATION COMPLETE")
    print("=" * 80)
    print(f"📄 Index files on drive: {created_on_drive}")
    print(f"📄 Index files locally: {created_local}")
    if error_count > 0:
        print(f"⚠️  Errors: {error_count}")
    print(f"⏱️  Time: {elapsed_time:.1f} seconds")
    print(f"📁 Local docs: {output_dir}")
    print(f"📝 Log: {LOG_FILE}")
    print("")
    
    logger.info("=" * 80)
    logger.info("Organization Complete")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        print("\n⚠️  Interrupted")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)

