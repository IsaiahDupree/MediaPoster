# Backend Setup Guide

## Quick Start

### 1. Install Python Dependencies

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Install System Dependencies

#### macOS (Required for Video Processing)

```bash
# Install FFmpeg
brew install ffmpeg

# Install Redis (for job queue)
brew install redis

# Start Redis
brew services start redis
```

### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required variables:**
- `BLOTATO_API_KEY` - Already set: `blt_nRMU7mx13OAGEFEs8NVZ/cv6ThhEeZ/VcozFFq4f6to=`
- `OPENAI_API_KEY` - Get from https://platform.openai.com/api-keys
- `SUPABASE_URL` and `SUPABASE_KEY` - Get from your Supabase project

### 4. Setup Database

#### Option A: Using Supabase (Recommended)

1. Create account at https://supabase.com
2. Create a new project
3. Go to SQL Editor
4. Copy and paste contents of `database/schema.sql`
5. Run the SQL
6. Copy your project URL and anon key to `.env`

#### Option B: Local PostgreSQL

```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL
brew services start postgresql

# Create database
createdb mediaposter

# Run schema
psql -d mediaposter -f database/schema.sql

# Update DATABASE_URL in .env
```

## Testing the Video Ingestion System

### Run Demo Script

```bash
# Make sure you're in the backend directory with venv activated
python3 demo_video_ingestion.py
```

The demo script provides 6 interactive demos:
1. **Test video validator** - Validate a single video file
2. **Watch directory** - Monitor a folder for new videos
3. **Monitor AirDrop** - Detect videos received via AirDrop
4. **Monitor iCloud Photos** - Watch for iPhone videos syncing via iCloud
5. **Monitor ALL sources** - Run all ingestion methods simultaneously
6. **Scan existing** - Find videos already on your Mac

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_video_validator.py -v

# Run with coverage report
pytest tests/ -v --cov=modules --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## Video Ingestion Features

### 1. iCloud Photos Monitoring
Automatically detects videos synced from iPhone via iCloud Photos.

**Requirements:**
- iCloud Photos enabled on Mac and iPhone
- Photos.app configured
- Photos library at default location or specified in `.env`

**Test it:**
1. Run demo #4 or #5
2. Take a video on your iPhone
3. Wait for iCloud sync (usually <1 minute)
4. Video will be automatically detected and processed

### 2. USB Import (Image Capture)
Detects when iPhone is connected via USB and imports videos.

**Requirements:**
- iPhone connected via USB cable
- Image Capture permissions granted

**Test it:**
1. Run demo #5
2. Connect iPhone via USB
3. System will automatically import videos
4. Videos are processed immediately

### 3. AirDrop Monitoring
Watches Downloads folder for videos received via AirDrop.

**Requirements:**
- AirDrop enabled on Mac and iPhone
- Bluetooth and WiFi enabled

**Test it:**
1. Run demo #3 or #5
2. Send a video from iPhone via AirDrop
3. Accept the transfer
4. Video is detected when transfer completes

### 4. File System Watching
Monitors specified directories for new video files.

**Default watched directories:**
- `~/Desktop`
- `~/Downloads`
- `~/Movies`

**Test it:**
1. Run demo #2 or #5
2. Copy or move a video file to watched directory
3. Video is detected immediately

## Configuration Options

### Video Validation Settings

Edit these in `.env`:

```bash
# Supported video formats
SUPPORTED_VIDEO_FORMATS=mp4,mov,m4v,avi,mkv

# Duration limits (seconds)
MIN_VIDEO_DURATION_SECONDS=10
MAX_VIDEO_DURATION_SECONDS=3600

# File size limit (MB)
MAX_VIDEO_SIZE_MB=500
```

### Watch Directories

```bash
# Comma-separated list of directories to watch
WATCH_DIRECTORIES=/Users/yourname/Desktop,/Users/yourname/Downloads
```

### iCloud Photos

```bash
# Path to Photos library
ICLOUD_PHOTOS_LIBRARY_PATH=~/Pictures/Photos Library.photoslibrary

# Enable/disable automatic import
AUTO_IMPORT_FROM_IPHONE=true
```

## Troubleshooting

### "Photos library not accessible"

**Solution:**
1. Open Photos.app
2. Go to Photos > Settings > General
3. Ensure "iCloud Photos" is checked
4. Grant terminal/Python full disk access:
   - System Settings > Privacy & Security > Full Disk Access
   - Add Terminal.app or your IDE

### "FFmpeg not found"

**Solution:**
```bash
# Install FFmpeg
brew install ffmpeg

# Verify installation
ffmpeg -version
```

### "No module named 'watchdog'"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Tests fail with timeout

**Solution:**
- Increase timeout in test configuration
- Ensure FFmpeg is installed and working
- Check system resources (CPU/RAM)

### USB device not detected

**Solution:**
1. Ensure iPhone is unlocked
2. Trust the computer on iPhone
3. Check USB cable connection
4. Try running: `system_profiler SPUSBDataType | grep iPhone`

## Usage Examples

### Example 1: Simple File Watcher

```python
from modules.video_ingestion import watch_for_videos
from pathlib import Path

def on_video(path: Path, metadata: dict):
    print(f"New video: {path}")
    print(f"Duration: {metadata['duration']}s")

# Start watching
service = watch_for_videos(
    callback=on_video,
    watch_dirs=["/Users/yourname/Desktop"]
)

# Service runs until stopped (Ctrl+C)
```

### Example 2: Validate Single Video

```python
from modules.video_ingestion import VideoValidator
from pathlib import Path

validator = VideoValidator()
is_valid, error, metadata = validator.validate(Path("video.mp4"))

if is_valid:
    print(f"Valid! Duration: {metadata['duration']}s")
else:
    print(f"Invalid: {error}")
```

### Example 3: Custom Ingestion Service

```python
from modules.video_ingestion import VideoIngestionService
from pathlib import Path

def process_video(path: Path, metadata: dict):
    print(f"Processing {path.name}...")
    # Your custom processing here
    # - Upload to database
    # - Start AI analysis
    # - Generate clips

service = VideoIngestionService(
    enable_icloud=True,
    enable_usb=True,
    enable_airdrop=True,
    enable_file_watcher=True,
    watch_directories=[
        "/Users/yourname/Desktop",
        "/Users/yourname/Movies"
    ],
    callback=process_video
)

service.start_all()
# Runs until stopped
```

## Next Steps

After setting up video ingestion:

1. **Test the system** - Run demo script and verify all ingestion methods work
2. **Configure Blotato** - Set up social media accounts in Blotato dashboard
3. **Set up AI services** - Configure OpenAI API for transcription and analysis
4. **Build pipeline** - Connect ingestion to AI analysis module
5. **Deploy dashboard** - Set up Next.js frontend for monitoring

## Support

For issues:
- Check `tests/README.md` for test-specific help
- Review logs in console output (loguru provides detailed logging)
- Ensure all system dependencies are installed
- Verify macOS permissions for Photos, Files, and Bluetooth

## Performance Notes

- **iCloud monitoring**: Polls every 60 seconds by default
- **File watching**: Real-time detection using filesystem events
- **USB monitoring**: Polls every 5 seconds for new devices
- **Video validation**: Typically <1 second per video
- **Concurrent processing**: Max 3 videos processed simultaneously (configurable)

## Security

- API keys stored in `.env` (not committed to git)
- `.env` is in `.gitignore` by default
- Use environment variables for production deployment
- Consider using macOS Keychain for sensitive data
