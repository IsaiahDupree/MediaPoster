# MediaPoster Database Architecture

## Database Overview

| Property | Value |
|----------|-------|
| **Database** | PostgreSQL 17.6 |
| **Host** | Supabase (Local Docker) |
| **Connection** | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |
| **Container** | `supabase_db_MediaPoster` |

## Migration System

Migrations are stored in `/supabase/migrations/` and applied via:

```bash
# Apply migrations (SAFE - no data loss)
supabase db push

# ⚠️ NEVER USE: supabase db reset (destroys all data!)
```

### Migration Files (39 total)

| Migration | Purpose |
|-----------|---------|
| `20241121000000_everreach_blend_schema.sql` | Core schema foundation |
| `20241222_video_orchestrator.sql` | Video orchestration tables |
| `20250121000000_content_base_tables.sql` | Content items, metrics |
| `20250121000001_people_graph.sql` | People/audience tracking |
| `20250121000002_content_graph_extensions.sql` | Content relationships |
| `20250121000003_connectors.sql` | Platform connectors |
| `20250121000004_base_video_tables.sql` | Videos table |
| `20250121000005_content_intelligence_video_analysis.sql` | Video analysis |
| `20250121000006_content_intelligence_platform_tracking.sql` | Platform posts |
| `20250121000007_content_intelligence_insights_metrics.sql` | Insights/metrics |
| `20250121000008_video_library.sql` | Video library |
| `20250121000009_fix_video_library_fk.sql` | Foreign key fixes |
| `20250121000010_video_thumbnails.sql` | Thumbnail columns |
| `20250121000011_video_clips.sql` | Clip extraction |
| `20250121000012_segment_editing.sql` | Video segments |
| `20250121000013_publishing_queue.sql` | Publishing queue |
| `20250122000000_fix_schema_mismatches.sql` | Schema fixes |
| `20251220_agent_framework.sql` | AI agent framework |
| `20251221_narrative_builder.sql` | Narrative builder tables |
| `20251222000000_experiments.sql` | A/B experiments |
| `20251223000000_scheduled_posts_enhancements.sql` | Scheduler columns |
| `20251223000001_social_accounts.sql` | Social accounts |
| `20251223000002_posted_content_table.sql` | Posted content tracking |
| `20251224000000_fix_posted_content_account_id.sql` | Account ID fix |

---

## Core Tables by Feature

### 📹 Media Library (`/media`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `videos` | Source videos | `id`, `file_name`, `thumbnail_path`, `source_uri`, `duration_sec` |
| `video_analysis` | AI analysis results | `video_id`, `transcript`, `topics`, `pre_social_score`, `platform_content` |
| `video_clips` | Extracted clips | `id`, `video_id`, `start_time`, `end_time` |
| `video_frames` | Frame analysis | `video_id`, `timestamp`, `score` |

**API Endpoints:**
- `GET /api/media-db/list` - List all media
- `GET /api/media-db/thumbnail/{id}` - Get thumbnail
- `GET /api/media-db/video/{id}` - Stream video
- `GET /api/media-db/analysis/{id}` - Get analysis data

---

### 📅 Schedule (`/schedule`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `scheduled_posts` | Posts to publish | `id`, `clip_id`, `platform`, `scheduled_time`, `status` |
| `narrative_schedules` | Weekly plans | `id`, `goal_id`, `week_start` |

**Key Relationships:**
- `scheduled_posts.clip_id` → `videos.id`

**API Endpoints:**
- `GET /api/schedule/list` - List scheduled posts
- `POST /api/schedule/create` - Create scheduled post
- `GET /api/schedule/scheduler/status` - Scheduler status
- `GET /api/schedule/scheduler/queue` - Post queue

---

### 📊 Posted Content (`/posted-content`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `posted_content` | Published posts | `id`, `platform`, `account_id`, `media_id`, `posted_at`, `status` |
| `platform_posts` | Platform-specific data | `id`, `platform`, `post_id`, `metrics` |

**API Endpoints:**
- `GET /api/posted-content` - List posted content
- `POST /api/posted-content/record` - Record new post

---

### 🧪 Experiments (`/experiments`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `experiments` | A/B tests | `id`, `name`, `hypothesis`, `status`, `metric` |
| `experiment_variants` | Test variations | `id`, `experiment_id`, `variant_type` |
| `experiment_learnings` | Results | `experiment_id`, `learning` |

**API Endpoints:**
- `GET /api/experiments` - List experiments
- `POST /api/experiments` - Create experiment

---

### 🧭 Narrative Builder (`/narrative-builder`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `narrative_goals` | Content goals | `id`, `name`, `target_metric`, `target_value` |
| `narrative_pillars` | Content pillars | `id`, `goal_id`, `name`, `theme` |

**API Endpoints:**
- `GET /api/narrative-builder/goals` - List goals
- `POST /api/narrative-builder/goals` - Create goal

---

### 👥 Social Accounts (`/accounts`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `social_accounts` | Connected accounts | `id`, `platform`, `username`, `blotato_id` |

**API Endpoints:**
- `GET /api/social-accounts/accounts` - List accounts
- `GET /api/blotato/accounts` - Blotato accounts (returns array directly)

---

### 🤖 Agent Framework

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `agent_runs` | Agent executions | `id`, `agent_type`, `status`, `started_at` |
| `agent_steps` | Execution steps | `run_id`, `step_name`, `status` |
| `agent_schedules` | Recurring agents | `id`, `agent_type`, `interval_seconds` |
| `agent_artifacts` | Generated outputs | `run_id`, `artifact_type`, `data` |

---

## Page → Database Mapping

| Frontend Page | Primary Table(s) | API Endpoint |
|--------------|------------------|--------------|
| `/media` | `videos`, `video_analysis` | `/api/media-db/list` |
| `/media/[id]` | `videos`, `video_analysis` | `/api/media-db/analysis/{id}` |
| `/schedule` | `scheduled_posts`, `videos` | `/api/schedule/list` |
| `/posted-content` | `posted_content` | `/api/posted-content` |
| `/experiments` | `experiments`, `experiment_variants` | `/api/experiments` |
| `/narrative-builder` | `narrative_goals`, `narrative_pillars` | `/api/narrative-builder/goals` |
| `/accounts` | `social_accounts` | `/api/social-accounts/accounts` |
| `/analytics` | `content_metrics`, `platform_posts` | `/api/analytics/*` |
| `/runs` | `agent_runs`, `agent_steps` | `/api/agent/runs` |

---

## Connection Strings

### Backend (Python)
```python
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
```

### Direct psql
```bash
docker exec supabase_db_MediaPoster psql -U postgres -d postgres
```

---

## Common Queries

### Check table structure
```sql
\d table_name
```

### List all tables
```sql
\dt
```

### Count records
```sql
SELECT COUNT(*) FROM videos;
SELECT COUNT(*) FROM scheduled_posts;
SELECT COUNT(*) FROM posted_content;
```

### Check scheduled posts with video data
```sql
SELECT sp.id, sp.status, v.file_name, v.thumbnail_path 
FROM scheduled_posts sp 
LEFT JOIN videos v ON v.id = sp.clip_id 
LIMIT 10;
```

---

## Key Relationships

```
videos (id) ─────────────┬──────────────────────────────────────┐
                         │                                      │
                         ▼                                      ▼
              video_analysis (video_id)            scheduled_posts (clip_id)
                         │                                      │
                         ▼                                      ▼
              platform_content (JSON)              posted_content (media_id)
```

---

## ⚠️ Important Notes

1. **Never run `supabase db reset`** - This destroys all AI analysis data ($10+ in API costs)
2. **Backup before migrations**: `pg_dump postgresql://postgres:postgres@127.0.0.1:54322/postgres > backup.sql`
3. **scheduled_posts.clip_id** must reference valid `videos.id` for thumbnails to load
4. **account_id in posted_content** is TEXT type (stores Blotato IDs like "710")
5. **Blotato API** returns accounts as array directly, not `{accounts: [...]}`
