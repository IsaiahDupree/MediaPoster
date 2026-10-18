# iPhone Import Setup - Single Source of Truth

## Primary Video Source

**Location:** `/Users/isaiahdupree/Documents/IphoneImport`
- **Size:** 116.92 GB
- **Items:** 8,491 files
- **Created:** November 19, 2025

## Key Principles

1. **SINGLE SOURCE** - All scripts reference only `IphoneImport` folder
2. **NO DUPLICATES** - Videos are referenced by path, not copied
3. **100% ANALYSIS** - Scripts wait for ALL analyses before scheduling

## Configuration Locations

### Environment Variables (`.env`)
```bash
VIDEO_SOURCE_DIR=/Users/isaiahdupree/Documents/IphoneImport
WATCH_DIRECTORIES=/Users/isaiahdupree/Documents/IphoneImport
```

### Docker (`docker-compose.yml`)
```yaml
volumes:
  - ~/Documents/IphoneImport:/media/IphoneImport:ro
environment:
  - VIDEO_SOURCE_DIR=/media/IphoneImport
```

## Database Setup

The database stores references to videos via `source_uri` field pointing to the original file.
No video files are copied or duplicated.

### Clean Slate Command
If you need to reset the video database:
```python
# Run in Backend directory
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@127.0.0.1:54322/postgres')
with engine.connect() as conn:
    conn.execute(text('DELETE FROM video_analysis'))
    conn.execute(text('DELETE FROM videos'))
    conn.execute(text('DELETE FROM scheduled_posts'))
    conn.commit()
    print('✅ Database cleaned')
"
```

## Updated Scripts

All these scripts now reference `~/Documents/IphoneImport`:

| Script | Purpose |
|--------|---------|
| `scripts/import_analyze_schedule_25_videos.py` | Main import + analyze + schedule pipeline |
| `scripts/import_and_analyze_for_month.py` | Monthly content preparation |
| `import_from_iphone.py` | iPhone USB import utility |
| `import_via_imagecapture.py` | Image Capture automation |
| `quickstart.py` | Quick start server |
| `demo_video_ingestion.py` | Demo/testing |

## Running the Full Pipeline

```bash
cd Backend
source venv/bin/activate
python scripts/import_analyze_schedule_25_videos.py
```

This will:
1. Scan `~/Documents/IphoneImport` for videos
2. Ingest up to 25 videos (references only, no copy)
3. Run FULL analysis on ALL videos (2-4 hours)
4. Schedule 8 videos across next 3 days

## Expected Timeline

- **Ingestion:** ~1-2 minutes for 25 videos
- **Analysis:** ~5-10 minutes per video = 2-4 hours total
- **Scheduling:** ~30 seconds

Total: **2-4 hours** for complete pipeline with 100% analysis.
