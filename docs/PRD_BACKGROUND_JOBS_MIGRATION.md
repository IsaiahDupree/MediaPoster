# PRD: Background Jobs Database Migration

**Status:** In Progress  
**Created:** 2025-12-27  
**Author:** Cascade AI  

---

## Problem Statement

Currently, job tracking for import, extraction, render, and scrape operations uses in-memory Python dictionaries. This causes:

1. **Data Loss** - All job history is lost on server restart
2. **No Persistence** - Users can't see job history after restart
3. **No Recovery** - Failed jobs can't be retried after restart
4. **Inconsistent State** - Frontend shows stale data after backend restart

### Before State

```python
# android_import_api.py, ios_import_api.py
_import_history: Dict[str, Dict[str, Any]] = {}

# clip_extraction.py
_extraction_jobs: Dict[str, Dict[str, Any]] = {}

# video_render.py
_render_jobs: Dict[str, Dict[str, Any]] = {}

# posted_content_matcher.py
_scrape_jobs: Dict[str, Dict[str, Any]] = {}

# video_orchestrator.py
_projects: Dict[str, Dict] = {}
_briefs: Dict[str, Dict] = {}
_scripts: Dict[str, Dict] = {}
_clip_plans: Dict[str, Dict] = {}
_generations: Dict[str, Dict] = {}
```

---

## Solution

### New Database Table

```sql
CREATE TABLE background_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,  -- 'import', 'extraction', 'render', 'scrape'
    status TEXT DEFAULT 'pending',
    progress NUMERIC(5,2) DEFAULT 0,
    input_json JSONB,
    output_json JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID,
    related_id UUID,
    related_type TEXT
);
```

### New Service Layer

```python
# services/background_jobs_service.py
class BackgroundJobsService:
    async def create_job(job_type, input_data) -> str
    async def update_progress(job_id, progress, status) -> bool
    async def complete_job(job_id, output_data) -> bool
    async def fail_job(job_id, error_message) -> bool
    async def get_job(job_id) -> dict
    async def list_jobs(job_type, status, limit) -> list
```

---

## Migration Plan

### Phase 1: Create Infrastructure ✅
- [x] Create `background_jobs` table migration
- [x] Apply migration to database
- [x] Create `BackgroundJobsService` class
- [x] Add background jobs API endpoints

### Phase 2: Migrate Import APIs
- [ ] Update `android_import_api.py` to use service
- [ ] Update `ios_import_api.py` to use service
- [ ] Remove `_import_history` global variable

### Phase 3: Migrate Other APIs
- [ ] Update `clip_extraction.py` to use service
- [ ] Update `video_render.py` to use service
- [ ] Update `posted_content_matcher.py` to use service

### Phase 4: Migrate Video Orchestrator (Future)
- [ ] Create dedicated tables for orchestrator state
- [ ] Update `video_orchestrator.py` to use database

---

## API Changes

### Job Endpoints (New)

```
GET  /api/jobs/list?type=import&status=running
GET  /api/jobs/{job_id}
POST /api/jobs/{job_id}/cancel
```

### Existing Endpoints (Updated)

Import, extraction, and render endpoints will now return persistent job IDs that survive restarts.

---

## Success Metrics

1. **Job Persistence** - Jobs visible after server restart
2. **History Retention** - Job history available for 30+ days
3. **Progress Recovery** - In-progress jobs resumable after restart
4. **Query Performance** - Job list queries < 100ms

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Migration breaks existing jobs | Run migration during low-traffic period |
| Database connection issues | Add fallback to in-memory with warning log |
| Performance degradation | Add indexes, use connection pooling |

---

## Timeline

- **Day 1:** Infrastructure + Import APIs (This PR)
- **Day 2:** Extraction + Render APIs
- **Day 3:** Video Orchestrator (Optional)

---

## Files Changed

### New Files ✅
- `supabase/migrations/20251227_create_background_jobs.sql` ✅
- `Backend/services/background_jobs_service.py` ✅
- `Backend/api/endpoints/jobs.py` (extended with background job endpoints) ✅

### Modified Files (Phase 2 - Pending)
- `Backend/api/endpoints/android_import_api.py`
- `Backend/api/endpoints/ios_import_api.py`
- `Backend/api/endpoints/clip_extraction.py`
- `Backend/api/endpoints/video_render.py`

---

## Current State (After Phase 1)

### API Endpoints Available

```
GET  /api/jobs/background/list?type=import&status=running
GET  /api/jobs/background/{job_id}
POST /api/jobs/background/{job_id}/cancel
GET  /api/jobs/background/active
```

### Service Methods Available

```python
from services.background_jobs_service import BackgroundJobsService

service = BackgroundJobsService(db)
job_id = await service.create_job("extraction", input_data)
await service.start_job(job_id)
await service.update_progress(job_id, 50.0)
await service.complete_job(job_id, output_data)
await service.fail_job(job_id, "Error message")
await service.cancel_job(job_id)
job = await service.get_job(job_id)
jobs = await service.list_jobs(job_type="extraction", status="running")
```

### Database Table

```sql
SELECT * FROM background_jobs;
-- id, job_type, status, progress, input_json, output_json,
-- error_message, started_at, completed_at, created_at, updated_at
```
