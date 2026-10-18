# Local Storage Directory Structure

This directory stores all media files locally during development to avoid cloud storage limitations.

## Directory Structure

```
local_storage/
├── videos/          # Original uploaded videos
├── thumbnails/      # Generated video thumbnails
├── clips/           # Generated short-form clips
└── temp/            # Temporary processing files
```

## Usage

- **Videos**: Place your source videos here or upload through the UI
- **Thumbnails**: Auto-generated when you click "Generate Thumbnails"
- **Clips**: Created when processing videos in the Studio
- **Temp**: Automatically cleaned up after processing

## File Naming Convention

- Videos: `{video_id}.{ext}`
- Thumbnails: `{video_id}_thumb.jpg`
- Clips: `{clip_id}.mp4`

## Notes

- Files in this directory are `.gitignore`d - they won't be committed
- For production, configure cloud storage (S3, Supabase Storage, etc.)
- Max file size configurable in `.env` (default: 500MB)
