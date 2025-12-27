# Run Passport Organization

## Quick Start

Open a terminal and run:

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
python3 scripts/organize_passport_comprehensive.py \
  --passport "/Volumes/My Passport" \
  --output "passport_organization_docs" \
  --max-depth 3
```

## Alternative: Use the Runner Script

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
python3 run_organize.py
```

## What It Does

1. ✅ Scans the entire Passport drive structure
2. ✅ Creates INDEX.txt files for each directory
3. ✅ Saves documentation locally in `passport_organization_docs/`
4. ✅ Generates master organizational report
5. ✅ Logs everything to `/tmp/mediaposter/logs/passport_organization.log`

## Expected Output

- **Directory**: `Backend/passport_organization_docs/`
- **Files**: INDEX.txt for each directory on the drive
- **Master Report**: `MASTER_INDEX.txt` with complete statistics
- **Log**: Detailed logs in `/tmp/mediaposter/logs/`

## Notes

- Drive is read-only, so files are created locally
- Can take several minutes depending on drive size
- Progress is shown in real-time
- Safe to interrupt (Ctrl+C) - partial results will be saved

