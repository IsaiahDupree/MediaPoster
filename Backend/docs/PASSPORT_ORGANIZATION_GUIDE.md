# Passport Drive Organization Guide

**Date:** 2025-12-26  
**Status:** Ready to Execute

## Overview

We've created a comprehensive organization system for the "My Passport" drive. Since the drive is currently read-only (NTFS mounted with macOS's fskit driver), the system creates local organizational documentation that mirrors the drive structure.

## What's Been Created

### 1. Comprehensive Organization Script
**Location:** `Backend/scripts/organize_passport_comprehensive.py`

**Features:**
- Scans entire drive structure (configurable depth)
- Creates INDEX.txt files for each directory
- Generates local documentation mirroring drive structure
- Can attempt to write directly to drive if write access becomes available
- Extensive logging throughout the process

### 2. Master Report (Already Generated)
**Location:** `Backend/passport_organization_docs/MASTER_INDEX.txt`

Contains:
- Complete directory structure
- File counts and sizes
- File type breakdowns
- Total drive statistics

## How to Run

### Option 1: Basic Organization (Recommended)
```bash
cd Backend
python3 scripts/organize_passport_comprehensive.py \
  --passport "/Volumes/My Passport" \
  --output "passport_organization_docs" \
  --max-depth 3
```

### Option 2: Full Depth Organization
```bash
cd Backend
python3 scripts/organize_passport_comprehensive.py \
  --passport "/Volumes/My Passport" \
  --output "passport_organization_docs"
```

### Option 3: Try Writing to Drive (If Write Access Available)
```bash
cd Backend
python3 scripts/organize_passport_comprehensive.py \
  --passport "/Volumes/My Passport" \
  --output "passport_organization_docs" \
  --try-write
```

## What It Does

1. **Scans Drive Structure**
   - Recursively scans all directories
   - Collects file metadata (size, type, modification date)
   - Tracks file types and sizes

2. **Creates INDEX.txt Files**
   - For each directory, creates an INDEX.txt with:
     - Directory summary (file count, size)
     - File type breakdown
     - List of subdirectories
     - List of files (organized by type)
   - Saves locally in `passport_organization_docs/` mirroring drive structure

3. **Generates Reports**
   - Master index in output directory
   - Per-directory indexes
   - Detailed logging in `/tmp/mediaposter/logs/passport_organization.log`

## Output Structure

```
passport_organization_docs/
├── MASTER_INDEX.txt                    # Master summary
├── INDEX.txt                           # Root directory index
├── [Directory Name]/
│   ├── INDEX.txt                       # Directory index
│   └── [Subdirectory]/
│       └── INDEX.txt                   # Subdirectory index
└── ...
```

## Current Drive Status

- **Mount Status:** Read-only (NTFS with fskit driver)
- **Write Access:** ❌ Not available
- **Read Access:** ✅ Available
- **Solution:** Local documentation created (can be copied to drive later if needed)

## Next Steps

1. **Run the organization script** (commands above)
2. **Review the generated documentation** in `passport_organization_docs/`
3. **If write access becomes available:**
   - Run with `--try-write` flag
   - Or manually copy INDEX.txt files from local docs to drive

## Example INDEX.txt Content

Each INDEX.txt file contains:
- Directory summary (files, directories, total size)
- File type breakdown
- List of subdirectories with sizes
- List of files organized by type
- Modification dates

## Logging

All operations are logged to:
- **File:** `/tmp/mediaposter/logs/passport_organization.log`
- **Level:** DEBUG (detailed information)
- **Rotation:** 10MB files, keeps 5 backups

## Troubleshooting

### Drive Not Found
```bash
# Check if drive is mounted
ls -la "/Volumes/My Passport"

# If not mounted, mount it first
# (Drive should auto-mount when connected)
```

### Permission Errors
- Expected for read-only drive
- Script will create local documentation instead
- Check logs for details

### Script Takes Too Long
- Use `--max-depth` to limit scanning depth
- Example: `--max-depth 2` for faster execution

## Integration with Duplicate Detection

After organization, you can:
1. Run duplicate comparison script
2. Use organizational docs to understand file locations
3. Make informed decisions about which duplicates to delete

