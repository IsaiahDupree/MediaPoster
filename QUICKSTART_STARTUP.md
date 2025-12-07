# 🚀 MediaPoster Quick Start Guide

**Last Updated**: November 21, 2024

## Overview
This guide shows you how to start MediaPoster with all services running on the correct ports.

## Service Ports

| Service | URL | Port | Framework |
|---------|-----|------|-----------|
| **Backend API** | http://localhost:8000 | 8000 | FastAPI |
| **Dashboard** | http://localhost:3000 | 3000 | Next.js 16 |
| **API Docs** | http://localhost:8000/docs | 8000 | Swagger UI |

---

## Prerequisites

### Required
- ✅ **Python 3.10+** (project uses 3.14)
- ✅ **Node.js 20+** and npm
- ✅ **FFmpeg** (for video processing)
- ✅ **PostgreSQL/Supabase** (database)

### Optional
- OpenAI API key (for AI features)
- Google Drive credentials (for Phase 4)

---

## 🎯 Fastest Start (Automated)

### Backend
```bash
cd Backend
./start.sh
```
Choose option 2 or 3 to start the API server.

### Dashboard
```bash
cd dashboard
npm install  # First time only
npm run dev
```

**That's it!** Services will be available at:
- Backend: http://localhost:8000/docs
- Dashboard: http://localhost:3000

---

## 📋 Manual Setup (Step-by-Step)

### 1️⃣ Backend Setup

#### a. Create Virtual Environment
```bash
cd Backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate
```

#### b. Install Dependencies
```bash
pip install -r requirements.txt
```

#### c. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
# Minimum required:
# - DATABASE_URL (Supabase connection string)
# - OPENAI_API_KEY (for AI features)
```

#### d. Start Backend API
```bash
# Development mode (auto-reload)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

✅ **Backend running at**: http://localhost:8000
📚 **API Documentation**: http://localhost:8000/docs

---

### 2️⃣ Dashboard Setup

#### a. Install Dependencies
```bash
cd dashboard
npm install  # or: npm ci for exact versions
```

#### b. Configure Environment (Optional)
```bash
# Create .env.local if needed
# Next.js will use default settings if not present
```

#### c. Start Development Server
```bash
npm run dev
```

The dashboard will start on **port 3000** by default.

✅ **Dashboard running at**: http://localhost:3000

---

## 🧪 Testing Everything

### Backend Tests

#### Run All Tests
```bash
cd Backend
source venv/bin/activate
pytest
```

#### Interactive Test Menu
```bash
cd Backend
python3 test_local.py
```

#### Phase-Specific Tests
```bash
# Phase 0: Backend Infrastructure
./start.sh  # Choose option 1

# Phase 1: AI Analysis
python3 test_phase1.py

# Phase 2: Highlight Detection
python3 test_phase2.py

# Phase 3: Clip Generation
python3 test_phase3.py

# Phase 4: Publishing (Blotato)
python3 test_phase4.py
```

### Quick Health Check
```bash
# Backend
curl -s http://localhost:8000/health | python3 -m json.tool

# Expected output:
# {
#   "status": "healthy",
#   "environment": "development",
#   "services": {
#     "api": "operational",
#     "database": "operational"
#   }
# }
```

---

## 🔧 Common Issues & Solutions

### Port Already in Use

**Problem**: `Address already in use` error

**Solution**:
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Find process using port 3000
lsof -ti:3000 | xargs kill -9
```

### Missing Dependencies

**Problem**: Import errors or module not found

**Solution**:
```bash
# Backend
cd Backend
source venv/bin/activate
pip install -r requirements.txt

# Dashboard
cd dashboard
rm -rf node_modules package-lock.json
npm install
```

### Database Connection Failed

**Problem**: Cannot connect to database

**Solution**:
1. Check `.env` file has correct `DATABASE_URL`
2. Verify Supabase project is running
3. Check network connectivity
4. View logs in `Backend/logs/app.log`

### FFmpeg Not Found

**Problem**: Video processing fails

**Solution**:
```bash
# macOS
brew install ffmpeg

# Check installation
ffmpeg -version
```

### CORS Errors

**Problem**: Frontend can't reach API

**Solution**:
1. Ensure backend is running on `0.0.0.0:8000` (not `127.0.0.1`)
2. Check CORS configuration in `Backend/main.py` (lines 70-80)
3. Verify dashboard URL matches allowed origins

---

## 🎯 One-Command Startup Script

Create a file `start_all.sh` in the project root:

```bash
#!/bin/bash
# MediaPoster - Start All Services

echo "🚀 Starting MediaPoster..."
echo ""

# Start Backend (background)
echo "📡 Starting Backend API (port 8000)..."
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start Dashboard (foreground)
echo "🎨 Starting Dashboard (port 3000)..."
cd dashboard
npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
```

Make it executable:
```bash
chmod +x start_all.sh
./start_all.sh
```

---

## 📊 What's Working Now

### ✅ Phase 0: Backend Infrastructure
- FastAPI server with WebSocket support
- PostgreSQL database (11 tables)
- Video ingestion (iCloud, USB, AirDrop)
- REST API endpoints
- Real-time updates

### ✅ Phase 1: AI Analysis
- Whisper transcription
- GPT-4 Vision frame analysis
- Audio characteristic detection
- Content insights generation

### ✅ Phase 2: Highlight Detection
- Multi-signal analysis
- Scene detection
- Audio peak detection
- Transcript scanning
- GPT-4 recommendations

### ✅ Phase 3: Clip Generation
- Video editing and cropping
- Caption burning
- Hook generation
- Visual effects
- Platform optimization (TikTok, Instagram, YouTube)

### 🔜 Phase 4: Publishing (Next)
- Google Drive upload
- Blotato multi-platform posting
- Scheduling
- Performance tracking

---

## 🔍 Verify Everything Is Running

### 1. Backend Health Check
```bash
curl http://localhost:8000/health
```

### 2. API Documentation
Open: http://localhost:8000/docs

### 3. Dashboard
Open: http://localhost:3000

### 4. WebSocket Connection
```bash
# Test WebSocket
websocat ws://localhost:8000/ws
```

---

## 📁 Project Structure

```
MediaPoster/
├── Backend/                    # FastAPI backend (port 8000)
│   ├── main.py                # Entry point
│   ├── start.sh               # Quick start script
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # Configuration
│   ├── modules/               # Core modules (9 modules)
│   ├── api/endpoints/         # API routes
│   ├── database/              # Models & connection
│   ├── tests/                 # Test suites
│   └── test_phase*.py         # Phase testing scripts
│
├── dashboard/                  # Next.js frontend (port 3000)
│   ├── package.json           # Node dependencies
│   ├── app/                   # Next.js app directory
│   └── public/                # Static assets
│
└── docs/                       # Documentation
    ├── ARCHITECTURE_PLAN.md
    ├── STATUS.md
    └── PHASE*_COMPLETE.md
```

---

## 🎓 Next Steps

1. **Test Backend**: Run `./start.sh` and choose option 1
2. **Test Phases**: Run phase-specific tests (test_phase1.py, etc.)
3. **Start API**: Run backend on port 8000
4. **Start Dashboard**: Run frontend on port 3000
5. **Upload Video**: Use API docs to test video processing
6. **Continue Development**: Start Phase 4 (Blotato integration)

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Architecture Plan**: `ARCHITECTURE_PLAN.md`
- **Current Status**: `STATUS.md`
- **Phase Details**: `PHASE*_COMPLETE.md`
- **Testing Guide**: `TEST_NOW.md`

---

## 🆘 Need Help?

1. Check logs: `Backend/logs/app.log`
2. View API errors in browser console
3. Run health check: `curl http://localhost:8000/health`
4. Check process status: `ps aux | grep uvicorn`

---

## 💡 Pro Tips

- Use `--reload` flag during development for auto-restart
- Keep backend logs open in a separate terminal
- Use API docs for testing endpoints quickly
- Run tests before making changes
- Check `.env` file if something doesn't work

---

**Ready to go!** 🚀

Start with: `cd Backend && ./start.sh`
