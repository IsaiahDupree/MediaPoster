# 📁 MediaPoster Project Structure

**Complete directory map and file organization**

---

## 🗂️ Root Directory

```
MediaPoster/
├── 📄 README.md                    # Main project overview
├── 📄 ONBOARDING_GUIDE.md          # ⭐ START HERE - First time setup
├── 📄 PROJECT_STRUCTURE.md         # This file
│
├── 🐍 Backend/                      # Python FastAPI backend
├── ⚛️ dashboard/                    # Next.js frontend (MAIN UI)
├── ⚛️ Frontend/                     # Alternative frontend (legacy)
├── 🗄️ supabase/                     # Local Supabase database
├── 📚 docs/                         # Documentation
├── 🔧 scripts/                      # Utility scripts
│
├── 📋 *.md                          # Various documentation files
└── 🐳 docker-compose.yml            # Docker configuration
```

---

## 🐍 Backend/ (Python FastAPI)

**Purpose:** REST API server, business logic, database operations

```
Backend/
├── 🚀 main.py                       # Application entry point
├── 📦 requirements.txt              # Python dependencies
├── 🔐 .env                          # Environment variables (create this)
├── 🔐 .env.example                  # Environment template
│
├── ⚙️ config/                       # Configuration
│   └── __init__.py                  # Settings from .env
│
├── 🌐 api/                          # API endpoints
│   ├── endpoints/                   # Individual endpoint modules
│   │   ├── media_provider.py        # Media serving (thumbnails, streaming)
│   │   ├── narrative_builder.py     # AI content planning
│   │   ├── schedule.py              # Content scheduling
│   │   └── ...
│   ├── media_processing_db.py       # Database-backed media API
│   └── ...
│
├── 🧠 services/                     # Business logic
│   ├── media_provider.py            # Media serving service
│   ├── thumbnail_service.py         # Thumbnail generation
│   ├── youtube_analytics.py         # YouTube API integration
│   └── ...
│
├── 🗄️ database/                     # Database layer
│   ├── models.py                    # SQLAlchemy ORM models
│   ├── connection.py                # Database connection setup
│   └── ...
│
├── 🤖 automation/                   # Automation scripts
│   ├── tiktok_engagement.py         # TikTok automation
│   └── ...
│
├── 🧪 tests/                         # Test suite
│   ├── unit/                        # Unit tests
│   ├── api/                         # API endpoint tests
│   ├── e2e/                         # End-to-end tests
│   ├── comprehensive/                # Comprehensive workflow tests
│   ├── performance/                 # Performance tests
│   ├── security/                    # Security tests
│   └── database/                    # Database tests
│
├── 📜 scripts/                       # Utility scripts
│   ├── import_and_analyze_for_month.py
│   ├── analyze_10_videos.py
│   └── ...
│
└── 📝 logs/                          # Application logs
```

**Key Files:**
- `main.py` - FastAPI app, registers routers, startup/shutdown
- `config/__init__.py` - Settings class, loads from .env
- `database/connection.py` - Database initialization
- `api/endpoints/media_provider.py` - Media serving endpoints
- `services/media_provider.py` - Media provider service logic

---

## ⚛️ dashboard/ (Next.js Frontend - MAIN UI)

**Purpose:** User interface, content management, analytics dashboard

```
dashboard/
├── 📦 package.json                  # Node dependencies
├── 🔐 .env.local                    # Frontend environment variables
│
├── 📱 app/                          # Next.js App Router
│   ├── layout.tsx                   # Root layout
│   ├── globals.css                  # Global styles
│   │
│   └── (dashboard)/                # Dashboard pages (grouped route)
│       ├── layout.tsx               # Dashboard layout (sidebar, etc.)
│       │
│       ├── media/                    # Media library
│       │   ├── page.tsx              # Media list/grid view
│       │   └── [id]/page.tsx         # Media detail with video player
│       │
│       ├── schedule/                # Content scheduling
│       │   └── page.tsx              # Calendar view, scheduling
│       │
│       ├── posted-content/          # Published content
│       │   └── page.tsx              # Posted content analytics
│       │
│       ├── narrative-builder/      # AI content planning
│       │   └── page.tsx              # Narrative goals & planning
│       │
│       ├── experiments/             # A/B testing
│       │   └── page.tsx              # Experiment management
│       │
│       └── ...                      # Other pages
│
├── 🧩 app/components/               # Shared React components
│   ├── MediaThumbnail.tsx           # Thumbnail display component
│   ├── VideoThumbnail.tsx           # Clickable video thumbnails
│   ├── VideoPlayer.tsx              # Video playback component
│   ├── Sidebar.tsx                  # Navigation sidebar
│   └── ...
│
├── 🧪 __tests__/                    # Frontend tests
│
└── 📝 README.md                      # Frontend documentation
```

**Key Files:**
- `app/layout.tsx` - Root layout wrapper
- `app/(dashboard)/layout.tsx` - Dashboard layout with sidebar
- `app/components/VideoThumbnail.tsx` - Video thumbnail component
- `app/components/VideoPlayer.tsx` - Video player component

---

## ⚛️ Frontend/ (Alternative Frontend - Legacy)

**Purpose:** Older/experimental frontend implementation

**Note:** The main frontend is in `dashboard/`. This directory may contain:
- Legacy code
- Experimental features
- Alternative UI implementations

**Recommendation:** Use `dashboard/` for development.

---

## 🗄️ supabase/ (Local Database)

**Purpose:** PostgreSQL database with Supabase tooling

```
supabase/
├── ⚙️ config.toml                   # Supabase configuration
│   ├── project_id = "MediaPoster"
│   ├── [api] port = 54321
│   └── [db] port = 54322
│
├── 📜 migrations/                    # Database migrations (39 files)
│   ├── 20251207000000_automation_features.sql
│   ├── 20251222000000_trends_analytics_system.sql
│   ├── 20251223000002_posted_content_table.sql
│   └── ...
│
└── 📝 seed.sql                       # Seed data (if any)
```

**Key Commands:**
```bash
cd supabase
supabase start      # Start database
supabase status     # Check status
supabase db reset   # Reset (⚠️ deletes data)
supabase db push    # Apply migrations
```

**Access:**
- Database: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- Studio UI: http://localhost:54323
- API: http://127.0.0.1:54321

---

## 📚 docs/ (Documentation)

```
docs/
├── DATABASE_ARCHITECTURE.md          # Database schema & tables
├── STARTUP_AND_DATABASE_GUIDE.md    # Startup instructions
└── ...
```

---

## 🔧 scripts/ (Utility Scripts)

**Purpose:** Standalone utility scripts for various tasks

---

## 🎯 Service Ports Reference

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Backend API** | 5555 | http://localhost:5555 | FastAPI REST API |
| **Frontend Dashboard** | 5557 | http://localhost:5557 | Next.js UI |
| **Supabase API** | 54321 | http://127.0.0.1:54321 | Supabase REST API |
| **PostgreSQL** | 54322 | postgresql://...:54322/... | Database |
| **Supabase Studio** | 54323 | http://localhost:54323 | Database UI |

---

## 🔑 Environment Variables

### Backend (`Backend/.env`)
```env
# Database
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Supabase
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=<from: supabase status>

# API Keys
OPENAI_API_KEY=sk-...
BLOTATO_API_KEY=blt_...
```

### Frontend (`dashboard/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:5555
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
```

---

## 🚨 Common File Locations

| What You Need | Where to Find It |
|---------------|------------------|
| **Start backend** | `Backend/main.py` |
| **API endpoints** | `Backend/api/endpoints/` |
| **Database models** | `Backend/database/models.py` |
| **Frontend pages** | `dashboard/app/(dashboard)/` |
| **Frontend components** | `dashboard/app/components/` |
| **Database config** | `supabase/config.toml` |
| **Migrations** | `supabase/migrations/` |
| **Tests** | `Backend/tests/` |
| **Logs** | `Backend/logs/app.log` |

---

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| `ONBOARDING_GUIDE.md` | ⭐ **START HERE** - First time setup |
| `PROJECT_STRUCTURE.md` | This file - directory map |
| `README.md` | Project overview |
| `docs/DATABASE_ARCHITECTURE.md` | Database schema |
| `Backend/SETUP.md` | Backend setup |
| `QUICKSTART_STARTUP.md` | Quick start |

---

## 🎓 Understanding the Flow

### Data Flow
```
iPhone Video
    ↓
Backend/scripts/import_and_analyze_for_month.py
    ↓
Backend/api/media_processing_db.py (ingest)
    ↓
Backend/api/media_processing_db.py (analyze)
    ↓
Database (videos, video_analysis tables)
    ↓
dashboard/app/(dashboard)/media/page.tsx (display)
    ↓
dashboard/app/(dashboard)/schedule/page.tsx (schedule)
    ↓
Backend/api/endpoints/schedule.py (save)
    ↓
Backend/services/background_publisher.py (publish)
    ↓
Database (posted_content table)
    ↓
dashboard/app/(dashboard)/posted-content/page.tsx (analytics)
```

### API Request Flow
```
Frontend (dashboard)
    ↓
HTTP Request → http://localhost:5555/api/...
    ↓
Backend/main.py (FastAPI router)
    ↓
Backend/api/endpoints/*.py (endpoint handler)
    ↓
Backend/services/*.py (business logic)
    ↓
Backend/database/connection.py (database)
    ↓
PostgreSQL (supabase)
    ↓
Response → Frontend
```

---

## 🔍 Finding Things

### "Where is the video upload code?"
→ `Backend/api/media_processing_db.py` (ingest endpoint)

### "Where is the analysis code?"
→ `Backend/api/media_processing_db.py` (analyze endpoint)

### "Where is the scheduling UI?"
→ `dashboard/app/(dashboard)/schedule/page.tsx`

### "Where are thumbnails generated?"
→ `Backend/services/thumbnail_service.py`

### "Where are videos streamed?"
→ `Backend/services/media_provider.py` (get_video_stream)

### "Where is the database schema?"
→ `supabase/migrations/` (SQL files)

### "Where are the tests?"
→ `Backend/tests/` (organized by type)

---

## ⚡ Quick Commands

```bash
# Start everything
cd supabase && supabase start &
cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload &
cd dashboard && npm run dev &

# Check status
curl http://localhost:5555/api/health
curl http://localhost:5555/api/media-provider/health
cd supabase && supabase status

# Run tests
cd Backend && pytest tests/ -v

# View logs
tail -f Backend/logs/app.log
```

---

**Last Updated:** December 24, 2025

