#!/usr/bin/env python3
"""
Organize Passport Drive with Text Documentation

This script:
1. Scans each directory on the Passport drive
2. Creates organizational text files (INDEX.txt) in each directory
3. Documents what's in each directory and subdirectories
4. Provides extensive logging throughout
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# Setup logging
LOG_DIR = Path("/tmp/mediaposter/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "passport_organization.log"

# Create logger
logger = logging.getLogger("passport_organize")
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

INDEX_FILENAME = "INDEX.txt"  # Organizational file name


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def scan_directory(directory: Path, max_depth: int = None, current_depth: int = 0) -> Dict:
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
            logger.warning(f"Directory does not exist or is not a directory: {directory}")
            return info
        
        # Check max depth
        if max_depth is not None and current_depth >= max_depth:
            logger.debug(f"Reached max depth {max_depth} at {directory}")
            return info
        
        # Get directory contents
        try:
            items = list(directory.iterdir())
        except PermissionError:
            logger.warning(f"Permission denied: {directory}")
            info["error"] = "Permission denied"
            return info
        except Exception as e:
            logger.error(f"Error reading {directory}: {e}", exc_info=True)
            info["error"] = str(e)
            return info
        
        # Separate directories and files
        dirs = sorted([item for item in items if item.is_dir()])
        files = sorted([item for item in items if item.is_file()])
        
        logger.debug(f"Found {len(dirs)} directories and {len(files)} files in {directory.name}")
        
        # Process subdirectories
        for subdir in dirs:
            # Skip system directories
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
            # Skip index files we create
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
                
                # Track file types
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


def create_index_file(directory: Path, info: Dict) -> bool:
    """Create INDEX.txt file in directory with organizational information"""
    logger.info(f"Creating index file in: {directory}")
    
    index_path = directory / INDEX_FILENAME
    
    try:
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
        
        # Directories in this folder
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
        
        # Files in this folder
        if info["files"]:
            lines.append("FILES")
            lines.append("-" * 80)
            # Group by type
            files_by_type = {}
            for file_info in info["files"]:
                ext = file_info["extension"]
                if ext not in files_by_type:
                    files_by_type[ext] = []
                files_by_type[ext].append(file_info)
            
            for ext in sorted(files_by_type.keys()):
                files_list = files_by_type[ext]
                lines.append(f"\n  {ext} ({len(files_list)} files):")
                for file_info in files_list:
                    lines.append(f"    • {file_info['name']:50s} {file_info['size_formatted']:>12s}  {file_info['modified']}")
            lines.append("")
        
        # Subdirectory details (summary)
        if info.get("subdirectory_count", 0) > 0:
            lines.append("SUBDIRECTORY DETAILS")
            lines.append("-" * 80)
            lines.append("See individual INDEX.txt files in each subdirectory for details.")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("End of Index")
        lines.append("=" * 80)
        
        # Check if we can write to this directory
        try:
            # Test write access
            test_file = directory / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot write to {directory}: {e} (read-only or permission denied)")
            return False
        
        # Write index file
        index_content = "\n".join(lines)
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
            logger.info(f"Index file created: {index_path} ({len(index_content)} bytes)")
            return True
        except OSError as e:
            if e.errno == 30:  # Read-only file system
                logger.warning(f"Read-only file system: {directory} - skipping")
            else:
                logger.error(f"OS error creating index in {directory}: {e}")
            return False
        
    except PermissionError:
        logger.warning(f"Permission denied creating index in {directory}")
        return False
    except Exception as e:
        logger.error(f"Error creating index file in {directory}: {e}", exc_info=True)
        return False


def organize_directory(directory: Path, max_depth: int = None, current_depth: int = 0) -> Tuple[int, int]:
    """Recursively organize directory by creating index files"""
    logger.info(f"Organizing directory: {directory} (depth: {current_depth})")
    
    created_count = 0
    error_count = 0
    
    try:
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Directory does not exist: {directory}")
            return created_count, error_count
        
        # Check max depth
        if max_depth is not None and current_depth >= max_depth:
            logger.debug(f"Reached max depth {max_depth} at {directory}")
            return created_count, error_count
        
        # Scan directory
        info = scan_directory(directory, max_depth, current_depth)
        
        # Create index file
        if create_index_file(directory, info):
            created_count += 1
            logger.info(f"✅ Created index in {directory.name}")
        else:
            error_count += 1
            logger.warning(f"⚠️  Failed to create index in {directory.name}")
        
        # Recursively organize subdirectories
        for subdir_info in info.get("directories", []):
            subdir_path = Path(subdir_info["path"])
            # Skip system directories
            if subdir_path.name.startswith('.') or subdir_path.name.startswith('$'):
                continue
            
            sub_created, sub_errors = organize_directory(subdir_path, max_depth, current_depth + 1)
            created_count += sub_created
            error_count += sub_errors
        
    except Exception as e:
        logger.error(f"Error organizing {directory}: {e}", exc_info=True)
        error_count += 1
    
    return created_count, error_count


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("Passport Drive Organization Script Started")
    logger.info("=" * 80)
    
    parser = argparse.ArgumentParser(description="Organize Passport drive with text documentation")
    parser.add_argument(
        "--passport",
        type=str,
        help="Path to Passport drive (default: /Volumes/My Passport)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum directory depth to organize (default: unlimited)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip directories that already have INDEX.txt"
    )
    
    args = parser.parse_args()
    
    # Find Passport drive
    logger.info("Locating Passport drive...")
    if args.passport:
        passport_path = Path(args.passport).expanduser()
        logger.info(f"Using provided path: {passport_path}")
    else:
        possible_paths = [
            Path("/Volumes/My Passport"),
            Path("/Volumes/Passport"),
        ]
        
        passport_path = None
        for path in possible_paths:
            logger.debug(f"  Checking: {path}")
            if path.exists() and path.is_dir():
                passport_path = path
                logger.info(f"  ✅ Found Passport at: {path}")
                break
        
        if not passport_path:
            logger.error("Passport drive not found")
            print("❌ Passport drive not found. Please specify with --passport")
            return 1
    
    if not passport_path.exists():
        logger.error(f"Passport path does not exist: {passport_path}")
        print(f"❌ Passport path not found: {passport_path}")
        return 1
    
    logger.info(f"Passport drive located: {passport_path}")
    
    print("=" * 60)
    print("📁 Organizing Passport Drive")
    print("=" * 60)
    print(f"📂 Drive: {passport_path}")
    print(f"📏 Max depth: {args.max_depth if args.max_depth else 'unlimited'}")
    print(f"⚙️  Skip existing: {args.skip_existing}")
    print("")
    
    import time
    start_time = time.time()
    
    # Organize drive
    logger.info("Starting organization process...")
    print("🔍 Scanning and organizing directories...")
    print("")
    
    created_count, error_count = organize_directory(passport_path, max_depth=args.max_depth)
    
    elapsed_time = time.time() - start_time
    
    logger.info(f"Organization complete: {created_count} index files created, {error_count} errors, took {elapsed_time:.1f}s")
    
    print("")
    print("=" * 60)
    print("✅ ORGANIZATION COMPLETE")
    print("=" * 60)
    print(f"📄 Index files created: {created_count}")
    if error_count > 0:
        print(f"⚠️  Errors: {error_count}")
    print(f"⏱️  Time: {elapsed_time:.1f} seconds")
    print(f"📝 Log: {LOG_FILE}")
    print("")
    print("💡 Each directory now has an INDEX.txt file documenting its contents")
    print("")
    
    logger.info("=" * 80)
    logger.info("Passport Organization Complete")
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

