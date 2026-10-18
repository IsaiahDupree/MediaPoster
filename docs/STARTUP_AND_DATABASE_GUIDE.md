# MediaPoster Startup & Database Guide

**Last Updated:** December 23, 2025

---

## Quick Start

### 1. Start All Services (3 Terminals)

```bash
# Terminal 1: Supabase (Local Database)
cd /Users/isaiahdupree/Documents/Software/MediaPoster/supabase
supabase start

# Terminal 2: Backend API (FastAPI)
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
source venv/bin/activate  # if using venv
uvicorn main:app --port 5555 --reload

# Terminal 3: Frontend Dashboard (Next.js)
cd /Users/isaiahdupree/Documents/Software/MediaPoster/dashboard
npm run dev
```

### 2. Verify Everything is Running

| Service | URL | Health Check |
|---------|-----|--------------|
| **Supabase** | `localhost:54322` | `supabase status` |
| **Backend API** | `http://localhost:5555` | `curl http://localhost:5555/api/health` |
| **Dashboard** | `http://localhost:5557` | Open in browser |
| **Supabase Studio** | `http://localhost:54323` | Open in browser |

### 3. Quick Health Check Command

```bash
# Check all ports at once
lsof -i :5555 -i :5557 -i :54322 | head -10

# Check API health
curl -s http://localhost:5555/api/health | python3 -m json.tool
```

---

## Database Connection

### Connection Strings

```bash
# Local Supabase (Development)
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Direct psql access
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

### Environment Variables

**Backend (`Backend/.env`):**
```env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE_KEY=<from supabase status>
OPENAI_API_KEY=<your-key>
```

**Dashboard (`dashboard/.env.local`):**
```env
NEXT_PUBLIC_API_URL=http://localhost:5555
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<from supabase status>
```

---

## Database Tables Overview (123 Tables)

### Core Content Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `videos` | All imported videos | id, file_name, source_uri, duration_sec |
| `video_analysis` | AI analysis results | video_id, transcript, topics, hooks, pre_social_score |
| `video_words` | Word-level transcript | video_id, word, start_s, end_s, is_emphasis |
| `video_frames` | Frame-by-frame analysis | video_id, timestamp_s, shot_type, has_face |
| `content_items` | Unified content graph | id, type, source_url, title |
| `content_variants` | Platform-specific versions | content_id, platform, title |

### Scheduling & Publishing
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `scheduled_posts` | Queue of posts to publish | content_id, platform, scheduled_at, status |
| `posted_content` | Published posts with metrics | platform_post_id, views, likes, comments |
| `platform_posts` | Cross-platform post tracking | platform, post_url, metrics |

### Automation & Agents
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `agent_schedules` | Cron-like agent scheduling | agent_type, topic, interval_seconds, enabled |
| `agent_runs` | Individual agent executions | agent_type, status, progress_current, progress_total |
| `agent_steps` | Step-by-step workflow tracking | run_id, step_name, status |
| `agent_events` | Timeline of agent actions | run_id, event_type, message, payload_json |
| `agent_queue` | Job queue for processing | topic, payload, claimed_by, status |
| `agent_artifacts` | Generated outputs from runs | run_id, artifact_type, content_json |

### Experiments
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `experiments` | A/B test campaigns | name, hypothesis, status, primary_metric |
| `experiment_variants` | Control vs variant content | experiment_id, name, is_control |
| `experiment_backlog` | Ideas waiting to test | hypothesis, target_metric, priority_score |
| `experiment_winners` | Winning variants | experiment_id, variant_id, uplift |

### Narrative Scheduler
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `narrative_goals` | Content planning goals | name, goal_type, target_metric |
| `narrative_pillars` | Content categories | goal_id, name, target_percentage |
| `weekly_schedules` | 7-day content plans | week_start, status, total_posts |
| `schedule_slots` | Individual scheduled items | schedule_id, video_id, scheduled_date |
| `kb_rules` | Knowledge base from experiments | rule_type, name, recommendation |

### Analytics & Trends
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `social_accounts` | Connected social accounts | platform, handle, account_role |
| `trend_hashtags` | Trending hashtags | platform, hashtag, trend_score |
| `trend_sounds` | Trending audio | platform, sound_name, usage_count |
| `industry_benchmarks` | Comparison metrics | platform, metric_name, benchmark_value |

### AI Generation
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ai_video_generations` | AI video requests | prompt, provider, status, output_url |
| `ai_characters` | Character definitions | name, description, voice_id |
| `ai_style_presets` | Visual style presets | name, prompt_modifier |
| `ai_generation_jobs` | Job tracking | job_type, status, progress |

---

## Page-to-API Mapping

### Dashboard Pages & Their Data Sources

| Page | Route | Primary API Endpoints | Tables Used |
|------|-------|----------------------|-------------|
| **Dashboard** | `/` | `/api/media-db/stats`, `/api/media-db/list` | videos, video_analysis |
| **Media Library** | `/media` | `/api/media-db/list`, `/api/videos/` | videos, video_analysis |
| **Media Detail** | `/media/[id]` | `/api/media-db/{id}`, `/api/videos/{id}/analyze` | videos, video_analysis, video_words |
| **Schedule** | `/schedule` | `/api/schedule/list`, `/api/schedule/create` | scheduled_posts, videos |
| **Automation** | `/automation` | `/api/automation/schedules`, `/api/automation/runs` | agent_schedules, agent_runs |
| **Run Details** | `/runs/[id]` | `/api/automation/runs/{id}/*` | agent_runs, agent_steps, agent_events |
| **Experiments** | `/experiments` | `/api/experiments/*` | experiments, experiment_variants |
| **Narrative Builder** | `/narrative-builder` | `/api/narrative-builder/*`, `/api/narrative/*` | narrative_goals, weekly_schedules |
| **Posted Content** | `/posted-content` | `/api/posted-content/list` | posted_content, platform_posts |
| **Analytics** | `/analytics` | `/api/analytics/*`, `/api/social-analytics/*` | posted_content, social_accounts |
| **Accounts** | `/accounts` | `/api/accounts/list` | social_accounts |
| **Trends** | `/trends` | `/api/trends/*` | trend_hashtags, trend_sounds |
| **AI Generations** | `/ai-generations` | `/api/ai-video/*` | ai_video_generations |
| **Comments** | `/comments` | `/api/comment-automation/*` | comment_threads, comment_replies |
| **Approval Queue** | `/approval-queue` | `/api/approval-queue/*` | approval_items |
| **Agent Panel** | `/agent-panel` | `/api/agents/*` | agent_runs, agent_events |

---

## Data Hydration Verification

### Check if Pages Have Data

```bash
# Dashboard stats
curl -s http://localhost:5555/api/media-db/stats | python3 -m json.tool

# Videos list
curl -s "http://localhost:5555/api/videos/?limit=5" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Videos: {len(d)}')"

# Experiments
curl -s http://localhost:5555/api/experiments/stats | python3 -m json.tool

# Automation health
curl -s http://localhost:5555/api/automation/health | python3 -m json.tool

# Posted content
curl -s "http://localhost:5555/api/posted-content/list?limit=5" | python3 -m json.tool

# Scheduled posts
curl -s http://localhost:5555/api/schedule/list | python3 -m json.tool
```

### Seed Test Data

```bash
# Seed experiments demo data
curl -X POST http://localhost:5555/api/experiments/seed-demo-data

# Seed automation schedules
curl -X POST http://localhost:5555/api/automation/seed-defaults

# Run video analysis on 10 videos
curl -X POST "http://localhost:5555/api/viral-analysis/batch-analyze?limit=10"
```

---

## Troubleshooting

### Database Not Connected

```bash
# Check if Supabase is running
supabase status

# If not running, start it
cd supabase && supabase start

# Check connection from backend
curl http://localhost:5555/api/health
# Should show: {"services":{"database":"operational"}}
```

### Backend Not Starting

```bash
# Check if port is in use
lsof -i :5555

# Kill existing process if needed
kill -9 <PID>

# Check for Python errors
cd Backend && python -c "from main import app; print('OK')"
```

### Frontend Not Loading Data

1. Check browser console for errors
2. Verify `NEXT_PUBLIC_API_URL` is set correctly
3. Check CORS - backend should allow localhost:5557
4. Try: `curl http://localhost:5555/api/health`

### Missing Tables

```bash
# Apply pending migrations
cd supabase && supabase db push --local

# List migrations
supabase migration list
```

---

## Important Notes

⚠️ **NEVER run `supabase db reset`** - This deletes all data including expensive AI analysis results.

✅ **Safe commands:**
- `supabase db push --local` - Apply migrations without data loss
- `supabase migration up` - Apply specific migrations

📊 **Current Stats:**
- 959 videos imported
- 0 analyzed (pending analysis)
- 123 database tables
- 707 API endpoints
- 42 dashboard pages

---

## Quick Reference

```bash
# One-liner to check everything
echo "=== Supabase ===" && supabase status 2>/dev/null | head -5 && \
echo "=== Backend ===" && curl -s http://localhost:5555/api/health && echo "" && \
echo "=== Stats ===" && curl -s http://localhost:5555/api/media-db/stats
```
