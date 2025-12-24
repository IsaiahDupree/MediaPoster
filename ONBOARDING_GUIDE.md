# 🚀 MediaPoster Onboarding Guide

**First Time Setup & Project Navigation**

This guide helps you understand the project structure and avoid common pitfalls when starting up.

---

## 📁 Project Structure Overview

```
MediaPoster/
├── Backend/              # FastAPI Python backend (Port 5555)
├── dashboard/            # Next.js dashboard (Port 5557) - MAIN FRONTEND
├── Frontend/             # Alternative frontend (legacy/experimental)
├── supabase/             # Local Supabase database (Port 54322)
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

---

## 🎯 Quick Start (3 Terminals)

### Terminal 1: Database (Supabase)
```bash
cd supabase
supabase start
```
**Wait for:** "API URL: http://127.0.0.1:54321"  
**Ports:** 54322 (DB), 54321 (API), 54323 (Studio)

### Terminal 2: Backend API
```bash
cd Backend
source venv/bin/activate  # Activate virtual environment
uvicorn main:app --port 5555 --reload
```
**Wait for:** "Uvicorn running on http://0.0.0.0:5555"  
**Health Check:** `curl http://localhost:5555/api/health`

### Terminal 3: Frontend Dashboard
```bash
cd dashboard
npm install  # First time only
npm run dev
```
**Wait for:** "Ready on http://localhost:5557"  
**Open:** http://localhost:5557

---

## ⚠️ Common Pitfalls & Solutions

### 1. **Wrong Port Numbers**
- ❌ **Wrong:** Backend on 8000, Frontend on 3000
- ✅ **Correct:** Backend on 5555, Frontend on 5557
- **Why:** Ports are configured in multiple places - always use 5555/5557

### 2. **Database Not Running**
- **Symptom:** `Connection refused` or `database does not exist`
- **Solution:** 
  ```bash
  cd supabase
  supabase status  # Check if running
  supabase start   # Start if not running
  ```

### 3. **Virtual Environment Not Activated**
- **Symptom:** `ModuleNotFoundError` or `command not found: uvicorn`
- **Solution:**
  ```bash
  cd Backend
  source venv/bin/activate  # You should see (venv) in prompt
  ```

### 4. **Missing Environment Variables**
- **Symptom:** API errors, authentication failures
- **Solution:** Check `Backend/.env` exists and has:
  ```env
  DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
  OPENAI_API_KEY=your-key-here
  BLOTATO_API_KEY=your-key-here
  ```

### 5. **Node Modules Not Installed**
- **Symptom:** `Cannot find module` errors in frontend
- **Solution:**
  ```bash
  cd dashboard
  rm -rf node_modules package-lock.json
  npm install
  ```

### 6. **Supabase Migrations Not Applied**
- **Symptom:** `relation does not exist` errors
- **Solution:**
  ```bash
  cd supabase
  supabase db reset  # ⚠️ WARNING: Deletes all data!
  # OR apply migrations manually:
  supabase db push
  ```

---

## 📂 Key Directories Explained

### `Backend/` - Python FastAPI Application

```
Backend/
├── main.py                    # 🚀 START HERE - Application entry point
├── config/                    # Configuration & environment variables
├── api/                       # API endpoints
│   ├── endpoints/            # Individual endpoint modules
│   └── media_processing_db.py # Database-backed media API
├── services/                  # Business logic services
│   ├── media_provider.py     # Media serving & streaming
│   └── thumbnail_service.py   # Thumbnail generation
├── database/                  # Database models & connection
│   ├── models.py             # SQLAlchemy ORM models
│   └── connection.py         # Database connection setup
├── scripts/                   # Utility scripts
│   ├── import_and_analyze_for_month.py
│   └── analyze_10_videos.py
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   ├── api/                   # API endpoint tests
│   ├── e2e/                   # End-to-end tests
│   └── comprehensive/         # Comprehensive workflow tests
├── requirements.txt           # Python dependencies
└── .env                       # Environment variables (create from .env.example)
```

**Key Files:**
- `main.py` - FastAPI app, registers all routers
- `config/__init__.py` - Settings from environment variables
- `database/connection.py` - Database initialization

### `dashboard/` - Next.js Frontend (MAIN UI)

```
dashboard/
├── app/
│   └── (dashboard)/          # Dashboard pages (Next.js App Router)
│       ├── media/            # Media library
│       ├── schedule/         # Content scheduling
│       ├── posted-content/   # Published content
│       ├── narrative-builder/ # AI content planning
│       └── experiments/     # A/B testing
├── app/components/           # Shared React components
│   ├── MediaThumbnail.tsx   # Thumbnail display
│   ├── VideoThumbnail.tsx   # Clickable video thumbnails
│   └── VideoPlayer.tsx      # Video playback component
├── package.json              # Node dependencies
└── .env.local                # Frontend environment variables
```

**Key Files:**
- `app/layout.tsx` - Root layout
- `app/(dashboard)/layout.tsx` - Dashboard layout with sidebar
- `app/components/` - Reusable components

### `supabase/` - Local Database

```
supabase/
├── config.toml               # Supabase configuration
├── migrations/               # Database migrations (39 files)
│   ├── 20251207000000_*.sql
│   └── ...
└── seed.sql                  # Seed data (if any)
```

**Key Commands:**
- `supabase start` - Start local Supabase
- `supabase status` - Check status
- `supabase db reset` - Reset database (⚠️ deletes data)
- `supabase db push` - Apply migrations

### `Frontend/` - Alternative Frontend (Legacy)

**Note:** This appears to be an older/experimental frontend. The main frontend is in `dashboard/`.

---

## 🔧 Configuration Files

### Backend Environment (`Backend/.env`)

```env
# Database (Local Supabase)
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres

# Supabase
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=<from: supabase status>
SUPABASE_SERVICE_ROLE_KEY=<from: supabase status>

# API Keys
OPENAI_API_KEY=sk-...
BLOTATO_API_KEY=blt_...
RAPIDAPI_KEY=...

# Application
APP_ENV=development
DEBUG=true
```

### Frontend Environment (`dashboard/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:5555
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<from: supabase status>
```

### Supabase Config (`supabase/config.toml`)

```toml
project_id = "MediaPoster"
[api]
port = 54321
[db]
port = 54322
```

---

## 🗄️ Database Overview

### Connection String
```
postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

### Key Tables
- `videos` - All imported media files
- `video_analysis` - AI analysis results
- `scheduled_posts` - Content scheduling
- `posted_content` - Published posts
- `social_media_accounts` - Connected accounts
- `narrative_goals` - Content strategy goals
- `experiments` - A/B testing experiments

### Access Database
```bash
# Via psql
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Via Supabase Studio
open http://localhost:54323
```

---

## 🚦 Service Health Checks

### Check All Services
```bash
# Backend API
curl http://localhost:5555/api/health

# Media Provider
curl http://localhost:5555/api/media-provider/health

# Database (via Supabase)
cd supabase && supabase status

# Frontend (open in browser)
open http://localhost:5557
```

### Check Ports in Use
```bash
lsof -i :5555 -i :5557 -i :54322 -i :54321
```

---

## 📚 Important Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project overview |
| `docs/DATABASE_ARCHITECTURE.md` | Database schema & tables |
| `docs/STARTUP_AND_DATABASE_GUIDE.md` | Startup instructions |
| `Backend/SETUP.md` | Backend setup guide |
| `QUICKSTART_STARTUP.md` | Quick start guide |

---

## 🔍 Understanding the Codebase

### API Endpoints

**Main API Base:** `http://localhost:5555`

**Key Endpoints:**
- `/api/media-db/list` - List media files
- `/api/media-db/analyze/{id}` - Analyze video
- `/api/media-provider/thumbnail/{id}` - Get thumbnail
- `/api/media-provider/stream/{id}` - Stream video
- `/api/publishing/scheduled` - Scheduled posts
- `/api/narrative-builder/*` - Narrative planning
- `/api/experiments/*` - A/B testing

**API Docs:** http://localhost:5555/docs

### Frontend Pages

**Main Dashboard:** `dashboard/app/(dashboard)/`

**Key Pages:**
- `/media` - Media library
- `/media/[id]` - Media detail with video player
- `/schedule` - Content scheduling calendar
- `/posted-content` - Published content analytics
- `/narrative-builder` - AI content planning
- `/experiments` - A/B testing experiments

---

## ⚡ Quick Troubleshooting

### Backend Won't Start
1. Check database is running: `supabase status`
2. Check virtual environment: `which python` (should show venv path)
3. Check dependencies: `pip list | grep fastapi`
4. Check logs: `Backend/logs/app.log`

### Frontend Won't Start
1. Check Node version: `node --version` (should be 18+)
2. Reinstall dependencies: `rm -rf node_modules && npm install`
3. Check port 5557 is free: `lsof -i :5557`

### Database Connection Errors
1. Verify Supabase is running: `supabase status`
2. Check connection string in `.env`
3. Test connection: `psql postgresql://postgres:postgres@127.0.0.1:54322/postgres`

### Media Not Loading
1. Check media provider service: `curl http://localhost:5555/api/media-provider/health`
2. Verify file paths exist
3. Check container path mapping in `Backend/services/media_provider.py`

---

## 🎓 Learning Path

### Day 1: Setup & Exploration
1. Start all services (3 terminals)
2. Open dashboard: http://localhost:5557
3. Browse API docs: http://localhost:5555/docs
4. Check database: http://localhost:54323

### Day 2: Understanding Data Flow
1. Upload a video via dashboard
2. Watch it get analyzed
3. Schedule a post
4. Check posted content

### Day 3: Code Navigation
1. Find where videos are ingested
2. Find where analysis happens
3. Find where posts are scheduled
4. Find where analytics are fetched

---

## 📝 Next Steps

1. **Read:** `docs/DATABASE_ARCHITECTURE.md` for database structure
2. **Explore:** API docs at http://localhost:5555/docs
3. **Test:** Run test suite: `cd Backend && pytest tests/ -v`
4. **Customize:** Update `.env` files with your API keys

---

## 🆘 Getting Help

- **Logs:** Check `Backend/logs/app.log` for errors
- **Database:** Check Supabase Studio at http://localhost:54323
- **API:** Check Swagger docs at http://localhost:5555/docs
- **Tests:** Run `cd Backend && python tests/run_all_test_types.py`

---

**Last Updated:** December 24, 2025

