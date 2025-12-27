#!/usr/bin/env python3
"""
Organize Passport Drive - Create Local Documentation

Since the drive is read-only, we'll create organizational docs in a local folder
that mirrors the structure, then run duplicate comparison.
"""
import sys
from pathlib import Path
import shutil
from scripts.organize_and_document_passport import generate_report
import logging

logger = logging.getLogger(__name__)

def main():
    """Create local organizational docs, then run duplicate comparison"""
    print("=" * 60)
    print("📁 Passport Drive Organization (Local Docs)")
    print("=" * 60)
    print("")
    print("ℹ️  Note: Drive is read-only (NTFS), creating docs locally")
    print("")
    
    passport_path = Path("/Volumes/My Passport")
    output_dir = Path("passport_organization_docs")
    output_dir.mkdir(exist_ok=True)
    
    # Generate report
    print("📊 Step 1: Generating organizational report...")
    report_text, directory_info = generate_report(passport_path, max_depth=3)
    
    # Save master report
    master_report = output_dir / "MASTER_INDEX.txt"
    with open(master_report, 'w') as f:
        f.write(report_text)
    print(f"✅ Master report saved: {master_report}")
    print("")
    
    # Create per-directory docs in local folder
    print("📝 Step 2: Creating per-directory documentation...")
    print("   (Saving to local folder since drive is read-only)")
    
    def create_local_docs(info, local_base: Path, depth=0):
        """Create local documentation mirroring drive structure"""
        if depth > 3:  # Limit depth
            return
        
        # Create local directory
        local_dir = local_base / info['name']
        local_dir.mkdir(exist_ok=True)
        
        # Create INDEX.txt for this directory
        index_path = local_dir / "INDEX.txt"
        lines = []
        lines.append("=" * 80)
        lines.append(f"DIRECTORY INDEX: {info['name']}")
        lines.append("=" * 80)
        lines.append(f"Source Path: {info['path']}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"Directories: {len(info['directories'])}")
        lines.append(f"Files: {len(info['files'])}")
        lines.append(f"Total Size: {format_size(info.get('total_size', 0))}")
        lines.append("")
        
        if info.get('directories'):
            lines.append("SUBDIRECTORIES:")
            for subdir in info['directories']:
                lines.append(f"  📁 {subdir['name']}/")
        lines.append("")
        
        if info.get('files'):
            lines.append("FILES:")
            for file_info in info['files'][:100]:  # Limit to 100 files
                if 'error' not in file_info:
                    lines.append(f"  • {file_info['name']} ({file_info.get('size_formatted', 'unknown')})")
        lines.append("")
        
        with open(index_path, 'w') as f:
            f.write("\n".join(lines))
        
        # Recursively process subdirectories
        for subdir_info in info.get('directories', []):
            create_local_docs(subdir_info, local_dir, depth + 1)
    
    from datetime import datetime
    from scripts.organize_and_document_passport import format_size
    
    create_local_docs(directory_info, output_dir)
    print(f"✅ Local documentation created in: {output_dir}")
    print("")
    
    print("=" * 60)
    print("✅ ORGANIZATION COMPLETE")
    print("=" * 60)
    print(f"📁 Local docs: {output_dir.absolute()}")
    print(f"📄 Master report: {master_report.absolute()}")
    print("")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())






