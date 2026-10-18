# Engagement System Audit

**Date:** 2026-01-30
**Issue:** Bot starts but immediately shows "stopped" on next API call

---

## Root Cause Analysis

### Primary Issue: Uvicorn Reload Resets Singleton

The backend runs with `uvicorn main:app --reload`, which reloads Python modules when files change. This causes:

1. `EngagementController._instance` gets reset to `None`
2. Next API call creates a **new** instance with `state=STOPPED`
3. Previous async tasks are orphaned (still running but unreferenced)

### Evidence
```bash
# Start shows "running"
curl -X POST http://localhost:5555/api/engagement-control/start
# {"state":"running","started_at":"2026-01-26T03:28:18..."}

# Stop immediately shows "Already stopped" (new instance!)
curl -X POST http://localhost:5555/api/engagement-control/stop
# {"state":"stopped","started_at":null,...}  # Note: started_at is null!
```

---

## Files Audited

### Services
| File | Status | Notes |
|------|--------|-------|
| `services/engagement/engagement_controller.py` | ⚠️ | Singleton lost on reload |
| `services/engagement/engagement_runner.py` | ✅ | Works correctly |
| `services/engagement/comment_tracker.py` | ✅ | DB persistence works |
| `services/engagement/engagement_service.py` | ✅ | Pub/sub integration |

### Platform Modules
| File | Status | Notes |
|------|--------|-------|
| `scripts/auto_engagement/threads_engagement.py` | ✅ | Has duplicate detection |
| `scripts/auto_engagement/instagram_engagement.py` | ✅ | Has duplicate detection |
| `scripts/auto_engagement/tiktok_engagement.py` | ✅ | Has duplicate detection |
| `scripts/auto_engagement/twitter_engagement.py` | ✅ | Has duplicate detection |
| `scripts/auto_engagement/safari_controller.py` | ✅ | AppleScript foundation |
| `scripts/auto_engagement/ai_comment_generator.py` | ✅ | OpenAI integration |

### API Endpoints
| File | Status | Notes |
|------|--------|-------|
| `api/endpoints/engagement_control.py` | ✅ | Clean API |

---

## Solutions

### Solution 1: Persist State in Database (Recommended)
Store engagement controller state in Supabase:
- `engagement_state` table with running/stopped status
- Restore state on startup
- Survive uvicorn reloads

### Solution 2: Use Redis for State
Store volatile state in Redis for fast access.

### Solution 3: Remove --reload in Production
Run without `--reload` flag to prevent resets.

---

## Recommended Fix

Add database persistence for controller state:

1. Create `engagement_state` table
2. Save state changes to DB
3. Load state on controller initialization
4. Add recovery logic for orphaned tasks

---

## Current Workaround

The bot IS working - it just appears stopped after uvicorn reload. Check:
1. Backend logs for actual engagement activity
2. `engagement_comments` table for new entries
3. Screenshots in `/tmp/` for proof
