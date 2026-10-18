#!/usr/bin/env python3
"""
Organize and Document Passport Drive Structure

This script:
1. Scans the Passport drive directory structure
2. Lists all files and directories at each level
3. Creates a comprehensive text report
4. Provides extensive logging throughout the process
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import json

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


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def get_directory_info(directory: Path, max_depth: int = None, current_depth: int = 0) -> Dict:
    """Recursively scan directory and collect information"""
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
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return info
        
        if not directory.is_dir():
            logger.warning(f"Path is not a directory: {directory}")
            return info
        
        # Check if we've reached max depth
        if max_depth is not None and current_depth >= max_depth:
            logger.debug(f"Reached max depth {max_depth} at {directory}")
            return info
        
        items = []
        try:
            items = list(directory.iterdir())
        except PermissionError:
            logger.warning(f"Permission denied accessing: {directory}")
            info["error"] = "Permission denied"
            return info
        except Exception as e:
            logger.error(f"Error reading directory {directory}: {e}", exc_info=True)
            info["error"] = str(e)
            return info
        
        # Sort items: directories first, then files
        dirs = [item for item in items if item.is_dir()]
        files = [item for item in items if item.is_file()]
        
        logger.debug(f"Found {len(dirs)} directories and {len(files)} files in {directory.name}")
        
        # Process directories
        for subdir in sorted(dirs):
            try:
                subdir_info = get_directory_info(subdir, max_depth, current_depth + 1)
                info["directories"].append(subdir_info)
                info["subdirectory_count"] += 1 + subdir_info.get("subdirectory_count", 0)
                info["total_files"] += subdir_info.get("total_files", 0)
                info["total_size"] += subdir_info.get("total_size", 0)
            except Exception as e:
                logger.error(f"Error processing subdirectory {subdir}: {e}", exc_info=True)
                info["directories"].append({
                    "path": str(subdir),
                    "name": subdir.name,
                    "error": str(e)
                })
        
        # Process files
        for file_path in sorted(files):
            try:
                stat = file_path.stat()
                file_size = stat.st_size
                file_ext = file_path.suffix.lower() or "(no extension)"
                
                file_info = {
                    "name": file_path.name,
                    "size": file_size,
                    "size_formatted": format_size(file_size),
                    "extension": file_ext,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
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
                info["files"].append({
                    "name": file_path.name,
                    "error": str(e)
                })
        
        logger.info(f"Completed scanning {directory.name}: {len(info['directories'])} dirs, {len(info['files'])} files, {format_size(info['total_size'])}")
        
    except Exception as e:
        logger.error(f"Critical error scanning {directory}: {e}", exc_info=True)
        info["error"] = str(e)
    
    return info


def format_directory_tree(info: Dict, indent: str = "", output_lines: List[str] = None) -> List[str]:
    """Format directory information as a tree structure"""
    if output_lines is None:
        output_lines = []
    
    # Directory header
    output_lines.append(f"{indent}📁 {info['name']}/")
    output_lines.append(f"{indent}   Path: {info['path']}")
    output_lines.append(f"{indent}   Files: {len(info['files'])} | Directories: {len(info['directories'])}")
    output_lines.append(f"{indent}   Total Size: {format_size(info['total_size'])}")
    
    if info.get("error"):
        output_lines.append(f"{indent}   ⚠️  Error: {info['error']}")
    
    # File types summary
    if info.get("file_types"):
        output_lines.append(f"{indent}   File Types:")
        for ext, data in sorted(info["file_types"].items(), key=lambda x: x[1]["size"], reverse=True)[:10]:
            output_lines.append(f"{indent}      • {ext}: {data['count']} files ({format_size(data['size'])})")
    
    # List files in this directory
    if info["files"]:
        output_lines.append(f"{indent}   Files:")
        for file_info in info["files"][:50]:  # Limit to first 50 files per directory
            if "error" in file_info:
                output_lines.append(f"{indent}      ⚠️  {file_info['name']} (Error: {file_info['error']})")
            else:
                output_lines.append(f"{indent}      • {file_info['name']} ({file_info['size_formatted']})")
        
        if len(info["files"]) > 50:
            output_lines.append(f"{indent}      ... and {len(info['files']) - 50} more files")
    
    output_lines.append("")  # Blank line between directories
    
    # Recursively format subdirectories
    for subdir_info in info["directories"]:
        format_directory_tree(subdir_info, indent + "   ", output_lines)
    
    return output_lines


def generate_report(passport_path: Path, max_depth: int = None) -> Tuple[str, Dict]:
    """Generate comprehensive report of Passport drive"""
    logger.info("=" * 80)
    logger.info("Starting Passport Drive Organization Report")
    logger.info("=" * 80)
    logger.info(f"Passport path: {passport_path}")
    logger.info(f"Max depth: {max_depth if max_depth else 'unlimited'}")
    
    print("=" * 60)
    print("📊 Passport Drive Organization Report")
    print("=" * 60)
    print(f"📂 Scanning: {passport_path}")
    print(f"📏 Max depth: {max_depth if max_depth else 'unlimited'}")
    print("")
    
    import time
    start_time = time.time()
    
    # Scan directory structure
    logger.info("Starting directory scan...")
    print("🔍 Scanning directory structure...")
    directory_info = get_directory_info(passport_path, max_depth=max_depth)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Directory scan complete in {elapsed_time:.1f} seconds")
    print(f"✅ Scan complete in {elapsed_time:.1f} seconds")
    print("")
    
    # Generate report text
    logger.info("Generating report text...")
    print("📝 Generating report...")
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("PASSPORT DRIVE ORGANIZATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Source: {passport_path}")
    report_lines.append("")
    report_lines.append("SUMMARY")
    report_lines.append("-" * 80)
    report_lines.append(f"Total Directories: {directory_info.get('subdirectory_count', 0) + len(directory_info.get('directories', []))}")
    report_lines.append(f"Total Files: {directory_info.get('total_files', 0)}")
    report_lines.append(f"Total Size: {format_size(directory_info.get('total_size', 0))}")
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("DETAILED DIRECTORY STRUCTURE")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Format directory tree
    format_directory_tree(directory_info, "", report_lines)
    
    report_text = "\n".join(report_lines)
    
    logger.info("Report generation complete")
    print("✅ Report generated")
    print("")
    
    return report_text, directory_info


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("Passport Organization Script Started")
    logger.info("=" * 80)
    
    parser = argparse.ArgumentParser(description="Organize and document Passport drive structure")
    parser.add_argument(
        "--passport",
        type=str,
        help="Path to Passport drive (default: /Volumes/My Passport)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum directory depth to scan (default: unlimited)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: passport_organization_report.txt)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also save JSON format report"
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
            Path.home() / "Passport",
        ]
        
        logger.info(f"Searching for Passport in {len(possible_paths)} locations...")
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
            print("   Searched locations:")
            for path in possible_paths:
                print(f"     • {path}")
            return 1
    
    if not passport_path.exists():
        logger.error(f"Passport path does not exist: {passport_path}")
        print(f"❌ Passport path not found: {passport_path}")
        return 1
    
    logger.info(f"Passport drive located: {passport_path}")
    
    # Generate report
    report_text, directory_info = generate_report(passport_path, max_depth=args.max_depth)
    
    # Save report
    output_path = Path(args.output) if args.output else Path("passport_organization_report.txt")
    output_path = output_path.expanduser().resolve()
    
    logger.info(f"Saving report to: {output_path}")
    print(f"💾 Saving report to: {output_path}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        logger.info(f"Report saved successfully: {output_path}")
        print(f"✅ Report saved: {output_path}")
    except Exception as e:
        logger.error(f"Error saving report: {e}", exc_info=True)
        print(f"❌ Error saving report: {e}")
        return 1
    
    # Save JSON if requested
    if args.json:
        json_path = output_path.with_suffix('.json')
        logger.info(f"Saving JSON report to: {json_path}")
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(directory_info, f, indent=2, default=str)
            logger.info(f"JSON report saved: {json_path}")
            print(f"✅ JSON report saved: {json_path}")
        except Exception as e:
            logger.error(f"Error saving JSON report: {e}", exc_info=True)
            print(f"❌ Error saving JSON report: {e}")
    
    # Summary
    print("")
    print("=" * 60)
    print("✅ ORGANIZATION COMPLETE")
    print("=" * 60)
    print(f"📊 Total Directories: {directory_info.get('subdirectory_count', 0) + len(directory_info.get('directories', []))}")
    print(f"📊 Total Files: {directory_info.get('total_files', 0)}")
    print(f"💾 Total Size: {format_size(directory_info.get('total_size', 0))}")
    print(f"📝 Report: {output_path}")
    print(f"📝 Log: {LOG_FILE}")
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

