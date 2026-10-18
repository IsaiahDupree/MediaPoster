# 🚀 MediaPoster Backend Quick Start

## One-Command Start

The easiest way to start the backend (handles virtual env, dependencies, and port conflicts):

```bash
cd Backend
./start.sh
```
*Select option **3** for development (auto-reload).*

---

## Manual Start

If you prefer running commands manually:

### 1. Setup (First Time Only)
```bash
cd Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg  # Required for thumbnails
```

### 2. Start Server
```bash
# Activate environment
source venv/bin/activate

# Start server on port 5555 (Required for Frontend)
uvicorn main:app --reload --port 5555
```

---

## ⚠️ Troubleshooting

### "Address already in use"
If you see `[Errno 48] Address already in use`, a previous server instance is still running.

**Fix:**
```bash
# Find and kill the process on port 5555
lsof -ti:5555 | xargs kill -9
```
*Note: The `./start.sh` script does this automatically!*

### "ffprobe not found"
Thumbnail generation requires FFmpeg.
**Fix:** `brew install ffmpeg`

### "Module not found"
Make sure your virtual environment is activated:
```bash
source venv/bin/activate
```
