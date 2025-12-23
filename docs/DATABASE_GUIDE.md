# MediaPoster Database Guide

**Last Updated:** December 23, 2025  
**Purpose:** Single source of truth for database configuration and access

---

## Active Database

| Property | Value |
|----------|-------|
| **Type** | Supabase (Local Docker) |
| **Name** | MediaPoster |
| **Host** | `127.0.0.1` |
| **Port** | `54322` |
| **Database** | `postgres` |
| **User** | `postgres` |
| **Password** | `postgres` |
| **Connection String** | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |

### Supabase URLs
| Service | URL |
|---------|-----|
| API | http://127.0.0.1:54321 |
| Studio | http://127.0.0.1:54323 |
| Database | postgresql://postgres:postgres@127.0.0.1:54322/postgres |

---

## Starting the Database

```bash
# Start Supabase (from project root)
cd supabase && supabase start

# Check status
supabase status

# Stop Supabase
supabase stop
```

---

## Key Tables

### Media/Content Tables
| Table | Description |
|-------|-------------|
| `videos` | Video files imported from iPhone/local storage |
| `content_items` | Content pieces ready for publishing |
| `analyzed_videos` | Videos that have been analyzed |
| `original_videos` | Source video files |

### Automation Tables
| Table | Description |
|-------|-------------|
| `agent_schedules` | Scheduled AI agent tasks |
| `agent_runs` | Execution history of agent tasks |
| `agent_steps` | Step-by-step progress within runs |
| `agent_events` | Timeline events from agent execution |
| `agent_artifacts` | Generated outputs (schedules, reports) |
| `agent_queue` | Job queue for async processing |

### Publishing Tables
| Table | Description |
|-------|-------------|
| `scheduled_posts` | Posts scheduled for publishing |
| `publishing_queue` | Queue of posts being published |
| `platform_posts` | Posts sent to platforms |

---

## Data Population

### iPhone Media Ingestion
The database is populated from local iPhone media files.

**Source Directory:** `/Users/isaiahdupree/Documents/IphoneImport/`  
**Total Files:** ~8,419 media files (videos + images)

**To Re-populate the Database:**
```bash
# Remove old state to force re-ingestion
mv Backend/scripts/ingestion_state.json Backend/scripts/ingestion_state.json.backup

# Run ingestion script
cd Backend && source venv/bin/activate
python scripts/ingest_iphone_media.py
```

**Ingestion State File:** `Backend/scripts/ingestion_state.json`  
- Tracks which files have been processed
- Allows resume capability if interrupted

---

## ⚠️ Critical Warnings

### DO NOT RUN: `supabase db reset`
This command **DELETES ALL DATA** in the database. Avoid unless you intend to wipe everything and re-run migrations + ingestion.

### Database Backups
Before any major operations:
```bash
# Export data
pg_dump postgresql://postgres:postgres@127.0.0.1:54322/postgres > backup.sql

# Import data
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres < backup.sql
```

---

## Environment Configuration

### Backend `.env`
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
```

### Frontend `.env.local`
```bash
NEXT_PUBLIC_API_URL=http://localhost:5555
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
```

---

## Troubleshooting

### Check Database Connection
```bash
cd Backend && source venv/bin/activate
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@127.0.0.1:54322/postgres')
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM videos'))
    print(f'Videos: {result.scalar()}')
"
```

### Check Table Row Counts
```bash
cd Backend && source venv/bin/activate
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@127.0.0.1:54322/postgres')
with engine.connect() as conn:
    for t in ['videos', 'content_items', 'agent_schedules', 'agent_runs']:
        result = conn.execute(text(f'SELECT COUNT(*) FROM {t}'))
        print(f'{t}: {result.scalar()}')
"
```

### Docker Supabase Instances
Only `MediaPoster` should be used for this project:
| Instance | Port | Use |
|----------|------|-----|
| MediaPoster | 54322 | ✅ Active |
| waitlist-lab | 54332 | ❌ Different project |
| KindLetters | 54422 | ❌ Different project |

---

## Quick Reference

```bash
# Start everything
cd supabase && supabase start
cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload
cd dashboard && npm run dev

# Check database health
curl http://localhost:5555/api/automation/health
```

---

*This document should be updated whenever database configuration changes.*
