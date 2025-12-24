# 🎓 First Time Setup - Complete Guide

**For developers opening this project for the first time**

---

## 📋 Pre-Flight Checklist

Before you start, verify you have:

- ✅ Python 3.10+ (`python3 --version`)
- ✅ Node.js 18+ (`node --version`)
- ✅ FFmpeg (`ffmpeg -version`)
- ✅ Supabase CLI (`supabase --version`)
- ✅ Docker Desktop running (for Supabase)

**Missing something?**
```bash
# macOS
brew install python@3.10 node ffmpeg supabase/tap/supabase
brew install --cask docker
```

---

## 🚀 Startup Sequence (3 Terminals)

### Terminal 1: Database
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/supabase
supabase start
```
**Wait for:** "API URL: http://127.0.0.1:54321"

**First time:** Downloads Docker images (~500MB, 2-3 minutes)

---

### Terminal 2: Backend API
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend

# Activate virtual environment
source venv/bin/activate

# If venv doesn't exist:
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt

# Start server
uvicorn main:app --port 5555 --reload
```
**Wait for:** "Uvicorn running on http://0.0.0.0:5555"

**Verify:** `curl http://localhost:5555/api/health`

---

### Terminal 3: Frontend Dashboard
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/dashboard

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```
**Wait for:** "Ready on http://localhost:5557"

**Verify:** Open http://localhost:5557 in browser

---

## 🔍 Verify Everything Works

### 1. Check Services
```bash
# Backend health
curl http://localhost:5555/api/health

# Media provider health
curl http://localhost:5555/api/media-provider/health

# Supabase status
cd supabase && supabase status
```

### 2. Check Ports
```bash
lsof -i :5555 -i :5557 -i :54322 -i :54321
```
Should show processes on all 4 ports.

### 3. Open UIs
- **Dashboard:** http://localhost:5557
- **API Docs:** http://localhost:5555/docs
- **Database UI:** http://localhost:54323

---

## ⚙️ Configuration

### Backend Environment (`Backend/.env`)

Create from template:
```bash
cd Backend
cp .env.example .env  # If .env.example exists
```

**Required variables:**
```env
# Database (from supabase status)
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=<from: supabase status>

# API Keys (get from respective services)
OPENAI_API_KEY=sk-...
BLOTATO_API_KEY=blt_...
```

**Get Supabase keys:**
```bash
cd supabase
supabase status
# Copy the anon key and service_role key
```

### Frontend Environment (`dashboard/.env.local`)

Create file:
```env
NEXT_PUBLIC_API_URL=http://localhost:5555
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<from: supabase status>
```

---

## 🗂️ Understanding the Structure

### Key Directories

| Directory | Purpose | Port |
|-----------|---------|------|
| `Backend/` | Python FastAPI API server | 5555 |
| `dashboard/` | Next.js frontend (main UI) | 5557 |
| `supabase/` | Local PostgreSQL database | 54322 |
| `Frontend/` | Alternative frontend (legacy) | - |

### Key Files

| File | Purpose |
|------|---------|
| `Backend/main.py` | API server entry point |
| `Backend/config/__init__.py` | Configuration settings |
| `dashboard/app/(dashboard)/` | Frontend pages |
| `supabase/migrations/` | Database schema |

---

## 🐛 Common Issues & Solutions

### Issue 1: "Connection refused" to database
**Solution:**
```bash
cd supabase
supabase start
# Wait for "API URL: http://127.0.0.1:54321"
```

### Issue 2: "ModuleNotFoundError" in Python
**Solution:**
```bash
cd Backend
source venv/bin/activate  # Must activate venv first
pip install -r requirements.txt
```

### Issue 3: "Cannot find module" in Node
**Solution:**
```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
```

### Issue 4: Port already in use
**Solution:**
```bash
# Find what's using the port
lsof -i :5555

# Kill the process
kill -9 <PID>
```

### Issue 5: Database migrations not applied
**Solution:**
```bash
cd supabase
supabase db reset  # ⚠️ WARNING: Deletes all data!
# OR
supabase db push  # Apply migrations without reset
```

---

## 📊 Service Status Dashboard

| Service | URL | Status Check |
|---------|-----|--------------|
| Backend API | http://localhost:5555 | `curl http://localhost:5555/api/health` |
| Frontend | http://localhost:5557 | Open in browser |
| Database | localhost:54322 | `cd supabase && supabase status` |
| API Docs | http://localhost:5555/docs | Open in browser |
| DB Studio | http://localhost:54323 | Open in browser |

---

## 🎯 What to Do First

1. **Start all 3 services** (see above)
2. **Open dashboard:** http://localhost:5557
3. **Browse API docs:** http://localhost:5555/docs
4. **Check database:** http://localhost:54323
5. **Read:** `ONBOARDING_GUIDE.md` for detailed navigation

---

## 📚 Documentation Hierarchy

1. **`START_HERE.md`** - Quick 3-step setup
2. **`ONBOARDING_GUIDE.md`** - Complete navigation guide
3. **`PROJECT_STRUCTURE.md`** - Directory map
4. **`docs/DATABASE_ARCHITECTURE.md`** - Database schema
5. **`README.md`** - Project overview

---

## 🔗 Quick Links

- **Dashboard:** http://localhost:5557
- **API Docs:** http://localhost:5555/docs
- **Database UI:** http://localhost:54323
- **Health Check:** http://localhost:5555/api/health

---

**Last Updated:** December 24, 2025

