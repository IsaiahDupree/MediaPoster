# MediaPoster Developer Handoff Guide

**For new developers joining the project**  
**Last Updated:** 2026-01-16

---

## 1. Quick Reference - Ports & URLs

| Service | URL | Port | Status Check |
|---------|-----|------|--------------|
| **Backend API** | http://localhost:5555 | 5555 | `curl http://localhost:5555/health` |
| **Frontend Dashboard** | http://localhost:5557 | 5557 | Open in browser |
| **Supabase Studio** | http://localhost:54323 | 54323 | `supabase status` |
| **Supabase API** | http://localhost:54321 | 54321 | `supabase status` |
| **Supabase DB** | postgresql://localhost:54322 | 54322 | `psql` connection |
| **API Docs (Swagger)** | http://localhost:5555/docs | 5555 | Open in browser |

---

## 2. Project Structure

```
MediaPoster/
├── Backend/                     # Python FastAPI backend
│   ├── main.py                  # Entry point
│   ├── api/                     # API endpoints
│   ├── automation/              # Safari automation scripts
│   │   ├── safari_twitter_poster.py
│   │   ├── safari_instagram_poster.py
│   │   ├── safari_instagram_scraper.py
│   │   └── safari_session_manager.py
│   ├── config/                  # Configuration
│   │   ├── paths.py             # Centralized path config
│   │   └── blotato_accounts.py  # Social account mappings
│   ├── docs/                    # Backend documentation
│   │   ├── PRD_CONTENT_OPS_CONTROLLER.md
│   │   ├── PRD_CONTENT_OPS_TECHNICAL.md
│   │   ├── PRD_CONTENT_OPS_TESTS.md
│   │   └── SAFARI_AUTOMATION_CAPABILITIES.md
│   ├── modules/                 # Core processing modules
│   ├── services/                # External service integrations
│   │   └── platform_publishers.py
│   ├── scripts/                 # Utility scripts
│   └── requirements.txt
│
├── Frontend/                    # React/Next.js frontend (legacy)
│   └── src/components/
│
├── dashboard/                   # Next.js 16 dashboard (primary UI)
│   ├── app/                     # App router pages
│   ├── lib/services/            # API client services
│   └── package.json
│
├── supabase/                    # Database migrations
│   └── migrations/
│
├── Examples/                    # Example scripts
│   └── VideoPackaging4/         # Legacy video processing
│
└── docs/                        # Project documentation
```

---

## 3. Getting Started

### 3.1 Prerequisites

```bash
# Required
- macOS 12.0+ (Apple Silicon recommended)
- Python 3.10+
- Node.js 20+
- FFmpeg
- Docker (for Supabase local)

# Check versions
python3 --version   # 3.10+
node --version      # 20+
ffmpeg -version
docker --version
```

### 3.2 First Time Setup

```bash
# 1. Clone repo
git clone <repo-url>
cd MediaPoster

# 2. Backend setup
cd Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# 3. Start Supabase (local database)
cd ..
supabase start
# Note the anon key and service_role key output

# 4. Dashboard setup
cd dashboard
npm install

# 5. Start services (3 terminals)
```

### 3.3 Daily Startup (3 Terminals)

**Terminal 1 - Database:**
```bash
cd MediaPoster
supabase start
# Dashboard: http://localhost:54323
```

**Terminal 2 - Backend API:**
```bash
cd MediaPoster/Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload
# API: http://localhost:5555
# Docs: http://localhost:5555/docs
```

**Terminal 3 - Frontend:**
```bash
cd MediaPoster/dashboard
npm run dev
# Dashboard: http://localhost:5557
```

---

## 4. Key Configuration Files

### 4.1 Backend Environment (.env)

```bash
# Backend/.env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=<from supabase start>
SUPABASE_SERVICE_ROLE_KEY=<from supabase start>
OPENAI_API_KEY=<your-key>
BLOTATO_API_KEY=<your-key>
```

### 4.2 Centralized Paths (Backend/config/paths.py)

```python
# External drive locations
MY_PASSPORT_BASE = "/Volumes/My Passport/MediaPoster"
IPHONE_IMPORT_DIR = MY_PASSPORT_BASE / "workspace1/iphone_import"
RAPIDAPI_MEDIA_DIR = MY_PASSPORT_BASE / "rapidapi_media"

# Use these functions:
from config.paths import get_iphone_import_dir, is_external_drive_connected
```

### 4.3 Blotato Account IDs (Backend/config/blotato_accounts.py)

Maps social media account IDs to usernames for TikTok, Instagram, YouTube, Twitter, Threads, etc.

---

## 5. Key Features & Where to Find Them

### 5.1 Safari Browser Automation

| Feature | File | CLI Command |
|---------|------|-------------|
| Twitter posting | `automation/safari_twitter_poster.py` | `python safari_twitter_poster.py --post "text"` |
| Instagram DMs | `automation/safari_instagram_poster.py` | `python safari_instagram_poster.py dm --list` |
| Instagram scraping | `automation/safari_instagram_scraper.py` | `python safari_instagram_scraper.py @username` |
| Session management | `automation/safari_session_manager.py` | `python safari_session_manager.py --check all` |

### 5.2 Platform Publishing

| Platform | Method | File |
|----------|--------|------|
| TikTok | API (Blotato) | `services/platform_publishers.py` |
| Instagram | API + Safari | `services/platform_publishers.py`, `automation/safari_instagram_poster.py` |
| YouTube | API | `services/platform_publishers.py` |
| Twitter/X | Safari | `automation/safari_twitter_poster.py` |
| Threads | Safari | `automation/safari_session_manager.py` |

### 5.3 Content Ops Controller (PRD)

Documentation for the autonomous feedback loop system:
- `Backend/docs/PRD_CONTENT_OPS_CONTROLLER.md` - Main PRD
- `Backend/docs/PRD_CONTENT_OPS_TECHNICAL.md` - API/Events/Workers
- `Backend/docs/PRD_CONTENT_OPS_TESTS.md` - Test specification

---

## 6. Database

### 6.1 Access Methods

```bash
# Supabase Studio (GUI)
open http://localhost:54323

# Direct psql
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# View tables
supabase db diff
```

### 6.2 Key Tables

| Table | Purpose |
|-------|---------|
| `content_files` | All ingested media files |
| `ai_analysis_results` | AI transcriptions and analysis |
| `clips` | Generated video clips |
| `posts` | Published social posts |
| `post_metrics` | Engagement metrics snapshots |
| `scheduled_posts` | Pending scheduled posts |

### 6.3 Migrations

```bash
# Apply migrations
supabase db push

# Create new migration
supabase migration new <name>

# NEVER use: supabase db reset (destroys data!)
```

### 6.4 Weekly Backups

Automatic weekly backups to external drive (see Section 8).

---

## 7. Testing

### 7.1 Backend Tests

```bash
cd Backend
source venv/bin/activate

# All tests
pytest

# Specific module
pytest tests/test_api.py -v

# With coverage
pytest --cov=. --cov-report=html
```

### 7.2 E2E Tests (Playwright)

```bash
cd MediaPoster
npx playwright test

# With UI
npx playwright test --ui
```

### 7.3 Test Files Structure

```
Backend/tests/          # Python unit/integration tests
e2e/                    # Playwright E2E tests
tests/                  # (future) Content Ops tests per PRD
```

---

## 8. Database Backup System

### 8.1 Manual Backup

```bash
# Run backup now
python Backend/scripts/db_backup.py

# Backup location
/Volumes/My Passport/MediaPoster/backups/
```

### 8.2 Scheduled Weekly Backup

Runs every Sunday at 2 AM via launchd:

```bash
# Install scheduler
launchctl load ~/Library/LaunchAgents/com.mediaposter.db-backup.plist

# Check status
launchctl list | grep mediaposter

# Uninstall
launchctl unload ~/Library/LaunchAgents/com.mediaposter.db-backup.plist
```

### 8.3 Restore from Backup

```bash
# List available backups
ls /Volumes/My\ Passport/MediaPoster/backups/

# Restore specific backup
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres < backup_file.sql
```

---

## 9. Common Tasks

### 9.1 Add New API Endpoint

1. Create route in `Backend/api/endpoints/`
2. Register in `Backend/main.py`
3. Add tests in `Backend/tests/`
4. Update API docs if needed

### 9.2 Add New Safari Automation

1. Add methods to relevant `automation/safari_*.py`
2. Update `SAFARI_AUTOMATION_CAPABILITIES.md`
3. Add to session manager if login required

### 9.3 Add Database Migration

```bash
cd MediaPoster
supabase migration new add_my_feature
# Edit supabase/migrations/<timestamp>_add_my_feature.sql
supabase db push
```

---

## 10. Troubleshooting

### Port Already in Use

```bash
lsof -ti:5555 | xargs kill -9  # Backend
lsof -ti:5557 | xargs kill -9  # Frontend
lsof -ti:54322 | xargs kill -9 # Supabase DB
```

### Supabase Issues

```bash
supabase stop
supabase start
```

### External Drive Not Connected

```python
from config.paths import is_external_drive_connected
if not is_external_drive_connected():
    print("Connect My Passport drive")
```

### Safari Automation Fails

```bash
# Check login status
python Backend/automation/safari_session_manager.py --check all

# Manually login if needed
python Backend/automation/safari_session_manager.py --refresh twitter
```

---

## 11. Important Rules

1. **Never use `supabase db reset`** - destroys AI analysis data ($10+ to regenerate)
2. **Never use `git checkout` to revert files** - destroys work
3. **Never skip any process step** - must fail with error, not silently skip
4. **Always use real OpenAI API calls** - no mocks for AI features
5. **Reference media files, don't duplicate** - use `source_uri` to original location

---

## 12. Contacts & Resources

- **API Docs:** http://localhost:5555/docs
- **Supabase Studio:** http://localhost:54323
- **Project Docs:** `/docs/` folder
- **Architecture:** `ARCHITECTURE_PLAN.md`
- **PRDs:** `Backend/docs/PRD_*.md`

---

## Quick Command Reference

```bash
# Start everything
supabase start && cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload &
cd ../dashboard && npm run dev

# Check services
curl http://localhost:5555/health
supabase status

# Run tests
cd Backend && pytest

# Backup database
python Backend/scripts/db_backup.py

# Check Safari sessions
python Backend/automation/safari_session_manager.py --check all
```
