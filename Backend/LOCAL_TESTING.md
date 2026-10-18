# Local Testing Guide (No Mocks!)

## Quick Start - Test Everything Now

### 1. Install Dependencies

```bash
cd backend

# Create virtual environment (if not done)
python3 -m venv venv
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### 2. Run Interactive Tests

```bash
# Run the local testing script
python3 test_local.py
```

**Menu options:**
1. **Test database connection** - Verify PostgreSQL/Supabase works
2. **Test video validator** - Validate a real video file
3. **Test database operations** - Real CRUD operations
4. **Test file watcher** - Real-time file detection
5. **Start API server** - Run FastAPI backend
6. **Run all tests** - Complete test suite

---

## Individual Test Instructions

### Test 1: Database Connection

**Without Supabase (Local PostgreSQL)**:
```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL
brew services start postgresql

# Create database
createdb mediaposter

# Run schema
psql -d mediaposter -f database/schema.sql

# Update .env
DATABASE_URL=postgresql://localhost/mediaposter
```

**With Supabase (Recommended)**:
```bash
# 1. Go to https://supabase.com
# 2. Create a new project
# 3. Copy database/schema.sql into SQL Editor and run it
# 4. Copy connection string to .env

DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[YOUR-PROJECT].supabase.co
SUPABASE_KEY=[YOUR-ANON-KEY]
```

**Test it:**
```bash
python3 test_local.py
# Choose option 1
```

---

### Test 2: Video Validator

**Prepare a test video:**
```bash
# Option 1: Use your own video
# Just have any .mp4 or .mov file ready

# Option 2: Create test video with FFmpeg
ffmpeg -f lavfi -i testsrc=duration=10:size=1920x1080:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=10 \
       -c:v libx264 -c:a aac test_video.mp4
```

**Test it:**
```bash
python3 test_local.py
# Choose option 2
# Enter path to your video file
```

**What it does:**
- ✅ Validates video format
- ✅ Extracts metadata (duration, resolution, codec)
- ✅ Generates thumbnail
- ✅ No mocks - real FFmpeg processing!

---

### Test 3: Database Operations

**Test real CRUD operations:**
```bash
python3 test_local.py
# Choose option 3
```

**What it does:**
- ✅ Creates a video record in PostgreSQL
- ✅ Reads it back
- ✅ Updates the record
- ✅ Deletes it
- ✅ All using real database queries!

---

### Test 4: File Watcher (Real-Time)

**Test real-time file detection:**
```bash
python3 test_local.py
# Choose option 4
# Enter directory to watch (or use default: ~/Desktop)
```

**Then:**
1. Script starts watching the directory
2. Copy/move a video file into that directory
3. Watch it get detected in real-time!
4. Press Ctrl+C to stop

**What it does:**
- ✅ Uses watchdog for real file system events
- ✅ Detects videos as soon as they appear
- ✅ Validates each detected video
- ✅ No mocks - real file system monitoring!

---

### Test 5: Start API Server

**Run the full FastAPI backend:**
```bash
python3 test_local.py
# Choose option 5

# Or run directly:
uvicorn main:app --reload
```

**Then visit:**
- http://localhost:8000 - API root
- http://localhost:8000/docs - Interactive API docs
- http://localhost:8000/health - Health check

**Test the API:**
```bash
# Health check
curl http://localhost:8000/health

# List videos
curl http://localhost:8000/api/videos/

# Start ingestion
curl -X POST http://localhost:8000/api/ingestion/start \
  -H "Content-Type: application/json" \
  -d '{"enable_icloud": false, "enable_airdrop": true}'

# Check ingestion status
curl http://localhost:8000/api/ingestion/status

# Upload a video
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@/path/to/video.mp4" \
  -F "source=manual_upload"
```

---

## Complete End-to-End Test

### Scenario: Upload and Process a Video

**Step 1: Start the backend**
```bash
# Terminal 1
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

**Step 2: Upload a video via API**
```bash
# Terminal 2
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@test_video.mp4" \
  -F "source=manual_upload"
```

**Response:**
```json
{
  "message": "Video uploaded successfully",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "file_name": "test_video.mp4",
  "duration": 10.5
}
```

**Step 3: Check database**
```bash
# Terminal 3
psql -d mediaposter -c "SELECT video_id, file_name, duration_seconds, processing_status FROM original_videos;"
```

**Step 4: Start ingestion service**
```bash
curl -X POST http://localhost:8000/api/ingestion/start \
  -H "Content-Type: application/json" \
  -d '{
    "enable_icloud": false,
    "enable_usb": false, 
    "enable_airdrop": true,
    "enable_file_watcher": true,
    "watch_directories": ["/Users/yourname/Desktop"]
  }'
```

**Step 5: Drop a video on Desktop**
- AirDrop a video from iPhone → Mac
- Or copy a video to Desktop
- Watch it appear in the database automatically!

**Step 6: Verify**
```bash
curl http://localhost:8000/api/videos/ | jq
```

---

## Testing Video Ingestion (Complete Flow)

### Test iCloud Photos Sync

**Prerequisites:**
- iCloud Photos enabled on Mac and iPhone
- Photos.app configured

**Test:**
```bash
# Start ingestion with iCloud enabled
curl -X POST http://localhost:8000/api/ingestion/start \
  -H "Content-Type: application/json" \
  -d '{"enable_icloud": true}'

# Take a video on iPhone
# Wait ~30 seconds for iCloud sync
# Check API for new video:
curl http://localhost:8000/api/videos/ | jq
```

### Test AirDrop

```bash
# Start ingestion
curl -X POST http://localhost:8000/api/ingestion/start \
  -d '{"enable_airdrop": true}'

# Send video via AirDrop from iPhone
# Should appear in API within seconds
```

### Test File Watcher

```bash
# Start watching Desktop
curl -X POST http://localhost:8000/api/ingestion/start \
  -d '{"enable_file_watcher": true, "watch_directories": ["/Users/$(whoami)/Desktop"]}'

# Copy video to Desktop
cp test_video.mp4 ~/Desktop/

# Check API
curl http://localhost:8000/api/videos/ | jq '.[] | select(.source == "file_watcher")'
```

---

## Debugging

### Enable Debug Logging

**In `.env`:**
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

**View logs:**
```bash
tail -f logs/app.log
```

### Common Issues

**"Database connection failed"**
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL -c "SELECT 1"
```

**"FFmpeg not found"**
```bash
# Install FFmpeg
brew install ffmpeg

# Verify
ffmpeg -version
```

**"No module named 'X'"**
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Performance Monitoring

### Watch Database Activity

```bash
# PostgreSQL
watch -n 1 'psql -d mediaposter -c "SELECT COUNT(*) as total_videos FROM original_videos;"'

# Or use API
watch -n 2 'curl -s http://localhost:8000/api/analytics/summary | jq'
```

### Monitor File Detection

```bash
# Terminal 1: Run ingestion
uvicorn main:app --reload

# Terminal 2: Watch logs
tail -f logs/app.log | grep "New video detected"

# Terminal 3: Copy videos
cp test_video.mp4 ~/Desktop/test_$(date +%s).mp4
```

---

## Next Steps After Testing

Once local testing works:

1. **Build AI Analysis Module** - Add Whisper transcription
2. **Add Clip Generation** - FFmpeg editing with hooks
3. **Integrate Blotato** - Multi-platform posting
4. **Deploy to Production** - Railway + Vercel

---

## Quick Commands Cheat Sheet

```bash
# Start backend
uvicorn main:app --reload

# Run tests
python3 test_local.py

# Check health
curl http://localhost:8000/health

# Upload video
curl -X POST http://localhost:8000/api/videos/upload -F "file=@video.mp4"

# Start ingestion
curl -X POST http://localhost:8000/api/ingestion/start -d '{"enable_airdrop":true}'

# Get status
curl http://localhost:8000/api/ingestion/status | jq

# View logs
tail -f logs/app.log

# Database queries
psql -d mediaposter -c "SELECT * FROM original_videos ORDER BY date_uploaded DESC LIMIT 5;"
```

---

## Success Criteria

✅ **All tests passing:**
- Database connection works
- Video validation processes real files
- Database CRUD operations complete
- File watcher detects real files
- API server responds to all endpoints
- Video upload works end-to-end

✅ **Ready for next modules:**
- AI Analysis
- Highlight Detection  
- Clip Generation
- Blotato Integration

**No mocks. Everything real. Test now!** 🚀
