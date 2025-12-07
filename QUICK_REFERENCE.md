# MediaPoster - Quick Reference Card

## 🚀 Test Phase 1 Right Now (3 Commands)

```bash
cd backend
source venv/bin/activate || python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 test_phase1.py
```

Choose option 5, enter a video path, and watch the magic happen! ✨

---

## 📋 What's Been Built

### Phase 0: Foundation ✅
- Backend API server
- Database layer
- Video ingestion (Mac/iOS)
- File validation

### Phase 1: AI Analysis ✅ NEW
- Whisper transcription
- Frame extraction
- GPT-4 Vision analysis  
- Audio analysis
- Content insights

---

## 🧪 Testing Commands

### Test Everything
```bash
./start.sh  # Backend root menu
```

### Test Phase 1
```bash
python3 test_phase1.py
```

### Test Individual Modules
```bash
# Transcribe video
python3 -m modules.ai_analysis.whisper_service video.mp4

# Extract frames
python3 -m modules.ai_analysis.frame_extractor video.mp4

# Analyze frame
python3 -m modules.ai_analysis.vision_analyzer frame.jpg

# Analyze audio
python3 -m modules.ai_analysis.audio_analyzer video.mp4

# Complete analysis
python3 -m modules.ai_analysis.content_analyzer video.mp4
```

### Start API Server
```bash
uvicorn main:app --reload
# http://localhost:8000/docs
```

---

## 🔑 Configuration

### Add to `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
DATABASE_URL=postgresql://...
```

---

## 📊 API Endpoints

### Videos
- `POST /api/videos/upload` - Upload video
- `GET /api/videos/` - List videos
- `GET /api/videos/{id}` - Get video
- `DELETE /api/videos/{id}` - Delete video

### Analysis (NEW)
- `POST /api/analysis/full-analysis/{video_id}` - Complete analysis
- `POST /api/analysis/transcribe/{video_id}` - Transcribe only
- `GET /api/analysis/results/{video_id}` - Get results
- `GET /api/analysis/transcript/{video_id}` - Get transcript

### Jobs
- `GET /api/jobs/` - List jobs
- `GET /api/jobs/{id}` - Get job status

### Ingestion
- `POST /api/ingestion/start` - Start watching
- `POST /api/ingestion/stop` - Stop watching
- `GET /api/ingestion/status` - Get status

---

## 💡 Example Workflow

```bash
# 1. Start server
uvicorn main:app --reload

# 2. Upload video (in another terminal)
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@video.mp4"
# Returns: {"video_id": "xxx-xxx-xxx"}

# 3. Start analysis
curl -X POST http://localhost:8000/api/analysis/full-analysis/xxx-xxx-xxx \
  -H "Content-Type: application/json" \
  -d '{"transcribe": true, "analyze_vision": true, "analyze_audio": true, "max_frames": 10}'
# Returns: {"job_id": "yyy-yyy-yyy"}

# 4. Check status
curl http://localhost:8000/api/jobs/yyy-yyy-yyy

# 5. Get results
curl http://localhost:8000/api/analysis/results/xxx-xxx-xxx
```

---

## 📁 Key Files

### Test Scripts
- `test_local.py` - Phase 0 tests
- `test_phase1.py` - Phase 1 tests
- `start.sh` - Quick start menu

### Documentation
- `STATUS.md` - Current progress
- `PHASE1_COMPLETE.md` - Phase 1 details
- `PHASED_DEVELOPMENT_PLAN.md` - Full roadmap

### Code
- `modules/ai_analysis/` - Phase 1 modules
- `api/endpoints/analysis.py` - Analysis API
- `main.py` - FastAPI app

---

## 🎯 What Works Now

✅ Upload video via API
✅ Auto-detect iPhone videos
✅ Validate video format
✅ Transcribe with Whisper
✅ Extract key frames
✅ Analyze with GPT-4 Vision
✅ Detect audio peaks/silence
✅ Generate content insights
✅ Background job processing
✅ WebSocket status updates

---

## 💰 Costs (Phase 1)

- Transcription: **$0.006/minute**
- Vision (10 frames): **$0.10-0.30**
- **Total: ~$0.15-0.35 per video minute**

---

## 🚦 Next Steps

**Option A**: Test Phase 1
```bash
python3 test_phase1.py
```

**Option B**: Start Phase 2
Build highlight detection next!

**Option C**: Deploy current state
Phase 0 + 1 are production-ready.

---

## 🆘 Quick Troubleshooting

**"Module not found"**
```bash
pip install -r requirements.txt
```

**"OpenAI API key not found"**
Add to `.env`:
```bash
OPENAI_API_KEY=sk-your-key
```

**"FFmpeg not found"**
```bash
brew install ffmpeg  # macOS
```

**"Database connection failed"**
Check `DATABASE_URL` in `.env`

---

## 📞 Help

- Full docs: `STATUS.md`
- Phase 1 guide: `PHASE1_COMPLETE.md`
- Testing guide: `PHASE1_TESTING.md`
- Roadmap: `PHASED_DEVELOPMENT_PLAN.md`

---

**Ready to test Phase 1!** 🚀

```bash
cd backend && python3 test_phase1.py
```
