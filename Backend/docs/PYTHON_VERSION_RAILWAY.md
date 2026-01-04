# Python Version Guide for Railway Deployment

**Last Updated:** January 4, 2026

---

## Current Setup

### MediaPoster Backend
- **Local Development:** Python 3.14.2
- **Recommended for Railway:** Python 3.11

### Why Python 3.11 for Railway?

Railway uses **Nixpacks** as its default build system, which supports:
- Python 2.7
- Python 3.8
- Python 3.9
- Python 3.10
- **Python 3.11 (Default)** ✅
- Python 3.12
- Python 3.13

**Python 3.11 is the Railway default** and has the best compatibility with:
- All FastAPI features
- PyTorch/TensorFlow (for AI models)
- Most Python packages in requirements.txt
- Railway's build cache system

---

## SoraWatermarkCleaner Compatibility

The SoraWatermarkCleaner GitHub repo uses:
- **uv** package manager
- Modern Python features (3.10+)
- PyTorch for YOLO and LAMA models

**Recommended:** Python 3.11 works perfectly with all dependencies.

---

## Setting Python Version on Railway

### Method 1: runtime.txt (Recommended)
Create a file in your project root:

```txt
# runtime.txt
3.11
```

### Method 2: .python-version
```txt
# .python-version
3.11
```

### Method 3: Environment Variable
In Railway dashboard:
```
NIXPACKS_PYTHON_VERSION=3.11
```

### Method 4: .tool-versions (for asdf users)
```
python 3.11
```

---

## Railway Deployment Configuration

### Complete railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### With runtime.txt
```
project/
├── runtime.txt          # 3.11
├── requirements.txt     # Your dependencies
├── railway.json         # Railway config
└── main.py             # FastAPI app
```

---

## Dependency Compatibility

### Core Dependencies (Python 3.11 Compatible)

| Package | Version | Python 3.11 | Notes |
|---------|---------|-------------|-------|
| **FastAPI** | 0.104.1 | ✅ | Fully compatible |
| **OpenAI** | ≥1.0.0 | ✅ | Requires 3.8+ |
| **PyTorch** | Latest | ✅ | Best on 3.11 |
| **OpenCV** | 4.8.1.78 | ✅ | Works perfectly |
| **FFmpeg-python** | 0.2.0 | ✅ | No issues |
| **NumPy** | ≥1.24.0 | ✅ | Optimized for 3.11 |

### AI Model Dependencies (for SoraWatermarkCleaner)

| Package | Python 3.11 | Notes |
|---------|-------------|-------|
| **ultralytics** (YOLO) | ✅ | YOLOv11s detector |
| **torch** | ✅ | LAMA/E2FGVI models |
| **iopaint** | ✅ | Inpainting framework |

---

## Why NOT Python 3.12 or 3.13?

### Python 3.12
- ❌ Some ML libraries not fully tested
- ❌ PyTorch wheels may lag behind
- ⚠️ Potential compatibility issues with older packages

### Python 3.13
- ❌ Too new (released Oct 2024)
- ❌ Many packages don't have wheels yet
- ❌ Not recommended for production

### Python 3.14 (Your Local Version)
- ❌ Not available on Railway/Nixpacks
- ❌ Bleeding edge, unstable
- ⚠️ Use for local experimentation only

---

## Migration Guide: 3.14 → 3.11

### 1. Create runtime.txt
```bash
echo "3.11" > runtime.txt
```

### 2. Test Locally with Python 3.11
```bash
# Install Python 3.11
brew install python@3.11  # macOS

# Create virtual environment
python3.11 -m venv venv_311
source venv_311/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test
python main.py
```

### 3. Update requirements.txt (if needed)
```bash
# Regenerate with Python 3.11
pip freeze > requirements.txt
```

### 4. Deploy to Railway
```bash
# Railway will automatically detect runtime.txt
railway up
```

---

## Troubleshooting

### "Python 3.12 required" Error
**Solution:** Add `runtime.txt` with `3.11` and redeploy.

### "Package not compatible with Python 3.11"
**Solution:** Check package documentation, may need to downgrade package version.

### Railway Using Wrong Python Version
**Check:**
1. Is `runtime.txt` in project root?
2. Does it contain just `3.11` (no extra text)?
3. Redeploy after adding file

### Local vs Railway Version Mismatch
**Best Practice:**
- Use Python 3.11 locally for development
- Or use Docker to match Railway environment exactly

---

## Docker Alternative (Exact Match)

If you want 100% parity between local and Railway:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Railway will auto-detect and use this Dockerfile.

---

## Recommended Setup for MediaPoster on Railway

### File Structure
```
Backend/
├── runtime.txt                 # 3.11
├── requirements.txt            # All dependencies
├── railway.json                # Railway config
├── main.py                     # FastAPI entry point
├── services/
│   └── watermark_remover.py   # SoraWatermarkCleaner integration
└── config/
    └── railway.py              # Railway-specific config
```

### runtime.txt
```
3.11
```

### requirements.txt (Key Packages)
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
ffmpeg-python==0.2.0
opencv-python==4.8.1.78
openai>=1.0.0
numpy>=1.24.0
torch>=2.0.0
ultralytics>=8.0.0
```

---

## Summary

| Environment | Python Version | Reason |
|-------------|---------------|--------|
| **Railway Production** | 3.11 | Default, best compatibility |
| **Local Development** | 3.11 or 3.14 | Match Railway or use latest |
| **SoraWatermarkCleaner** | 3.11 | Tested and working |
| **Docker** | 3.11-slim | Lightweight, production-ready |

**Bottom Line:** Use Python 3.11 for Railway deployment. It's the default, well-tested, and compatible with all AI/ML libraries you need.
