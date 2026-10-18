# Memory vs Database Audit
**Generated:** 2025-12-27

## Summary

This audit identifies data stored in-memory (lost on restart) vs database (persisted).

---

## 🔴 CRITICAL: In-Memory Storage (Lost on Restart)

### API Endpoints with In-Memory Stores

| File | Variable | Purpose | Should be in DB? |
|------|----------|---------|------------------|
| `android_import_api.py:33` | `_import_history` | Import job history | ✅ Yes - jobs table |
| `ios_import_api.py:32` | `_import_history` | Import job history | ✅ Yes - jobs table |
| `clip_extraction.py:77` | `_extraction_jobs` | Extraction job tracking | ✅ Yes - jobs table |
| `video_render.py:28` | `_render_jobs` | Render job tracking | ✅ Yes - jobs table |
| `posted_content_matcher.py:261` | `_scrape_jobs` | Scrape job tracking | ✅ Yes - jobs table |
| `video_orchestrator.py:228-232` | `_projects`, `_briefs`, `_scripts`, `_clip_plans`, `_generations` | Video orchestration state | ✅ Yes - dedicated tables |
| `videos.py:502` | `_active_scans` | Active folder scans | ⚠️ Maybe - transient OK |

### ✅ FIXED: formats_api.py

Previously used `_seeded_formats` in-memory dict. Now uses database queries.

---

## 🟢 Database-Backed Storage (Persisted)

### Core Tables (Already in DB)

| Table | Purpose | Status |
|-------|---------|--------|
| `videos` | Video library | ✅ Persisted |
| `video_analysis` | AI analysis results | ✅ Persisted |
| `formats` | Format templates | ✅ Persisted (fixed today) |
| `format_runs` | Format execution history | ✅ Persisted |
| `scheduled_posts` | Publishing schedule | ✅ Persisted |
| `posted_content` | Published content tracking | ✅ Persisted |
| `platform_accounts` | Social media accounts | ✅ Persisted |
| `trend_queries` | Trend monitoring queries | ✅ Persisted |
| `engagement_rules` | Auto-engagement rules | ✅ Persisted |

---

## 📋 Migration Priority

### Priority 1: Job Tracking (High Impact)
These jobs are lost on restart, causing confusion:

```
_import_history → jobs table with type='import'
_extraction_jobs → jobs table with type='extraction'  
_render_jobs → jobs table with type='render'
_scrape_jobs → jobs table with type='scrape'
```

**Recommended:** Create unified `background_jobs` table:
```sql
CREATE TABLE background_jobs (
    id UUID PRIMARY KEY,
    job_type TEXT NOT NULL,  -- 'import', 'extraction', 'render', 'scrape'
    status TEXT DEFAULT 'pending',
    progress NUMERIC(5,2),
    input_json JSONB,
    output_json JSONB,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Priority 2: Video Orchestrator State (Medium Impact)
Complex state that would benefit from persistence:

```
_projects → video_projects table
_briefs → creative_briefs table (may already exist)
_scripts → video_scripts table
_clip_plans → clip_plans table
_generations → generation_jobs table
```

### Priority 3: Transient State (Low Impact)
Can remain in-memory (OK to lose on restart):

```
_active_scans → Transient folder scan state
WebSocket connections → Naturally transient
```

---

## 🔧 Quick Fixes Applied Today

1. **formats_api.py** - Changed from `_seeded_formats` dict to database queries
   - `list_formats()` → Now queries `formats` table
   - `seed_sample_formats()` → Now inserts to `formats` table with commit
   - `get_format()` → Now reads from database
   - `run_format()` → Now validates against database

---

## 📊 Database Tables Status

### Confirmed Existing Tables
```
videos
video_analysis
formats
format_runs
quality_profiles
scheduled_posts
posted_content
platform_accounts
trend_queries
engagement_rules
knowledge_items
creative_briefs
```

### Tables That Should Exist (Check/Create)
```
background_jobs - For unified job tracking
video_projects - For orchestrator state
broll_selections - For locked B-roll choices
```

---

## Action Items

- [ ] Create `background_jobs` table migration
- [ ] Update import APIs to use background_jobs table
- [ ] Update extraction API to use background_jobs table
- [ ] Update render API to use background_jobs table
- [ ] Update video_orchestrator to persist state
- [ ] Create `broll_selections` table for locked selections
