# Next Session Implementation Plan
**Created:** 2026-01-18
**For:** Next Autonomous Coding Session
**Priority:** Fix blockers, complete Phase 2, start Phase 3

---

## Session Goals

### Primary Objectives
1. ✅ **Fix Supabase Import Error** - Unblock 20+ tests (30 min)
2. ✅ **Complete Phase 2 Content Ops** - Get to 100% phase completion (2-3 hours)
3. ✅ **Create First 10 AI Templates** - Problem-Aware & Solution-Aware (2-3 hours)
4. ✅ **Test All Content Ops Workers** - Validate worker coordination (1 hour)

### Stretch Goals
5. 🎯 **Build Instagram Adapter** - ADAPT-004 to ADAPT-006 (3-4 hours)
6. 🎯 **Implement Trend Discovery** - TREND-001 basic ingestion (2 hours)

---

## Quick Start Commands

### 1. Fix Supabase Import (FIRST TASK)
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend

# Check Supabase package
pip list | grep supabase

# Run blocked tests to see error
pytest tests/unit/test_content_ops_entities.py -v

# Fix: Update Backend/database/connection.py line 8
# Should be: from supabase import create_client, Client
```

### 2. Run Test Suite
```bash
# All unit tests
pytest tests/unit/ -v

# Content Ops tests
pytest tests/unit/test_template_validation.py -v
pytest tests/unit/test_awareness_classifier.py -v
pytest tests/unit/test_sleep_mode_service.py -v
```

### 3. Start Backend Server
```bash
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload
```

---

## Current Status (from PROJECT_STATUS_2026-01-18.md)

- **Total Features:** 310
- **Completed:** 61 (19.7%)
- **Phase 1 (Sleep/Wake):** ✅ 100% complete (12/12 features)
- **Phase 2 (Content Ops):** ⚙️ 55% complete (11/20 features)
- **Phase 3 (Templates):** 🔄 12.5% complete (1/8 features)

**Test Results:**
- Sleep Mode: 32/32 passing ✅
- Template Validation: 41/41 passing ✅
- Awareness Classifier: 13/13 passing ✅
- **Total: 86/86 unit tests passing (100%)**

**Blockers:**
- Supabase import error blocking database tests
- FATE scorer: 25/31 tests passing (6 failures)

---

## Detailed Task Breakdown

### TASK 1: Fix Supabase Import (CRITICAL - 30 min)

**Error:**
```
ImportError: cannot import name 'create_client' from 'supabase'
Location: Backend/database/connection.py:8
```

**Steps:**
1. Check installed package version: `pip show supabase`
2. Read current import statement: `Backend/database/connection.py`
3. Fix import (likely one of these):
   ```python
   # Option A: Standard import
   from supabase import create_client, Client
   
   # Option B: Async client
   from supabase._async.client import create_client, AsyncClient
   
   # Option C: Check if using supabase-py
   from supabase_py import create_client, Client
   ```
4. Test the fix:
   ```bash
   pytest tests/unit/test_content_ops_entities.py -v
   pytest tests/unit/test_touchpoint_service.py -v
   ```

**Success:** All database import errors resolved

---

### TASK 2: Complete Phase 2 Content Ops (2-3 hours)

**Files that exist but need testing:**

#### 2.1 Run existing service tests
```bash
pytest tests/unit/test_dlq_service.py -v
pytest tests/unit/test_rate_limiter.py -v
pytest tests/unit/test_planner_service.py -v
pytest tests/unit/test_dm_permission_service.py -v
pytest tests/unit/test_touchpoint_service.py -v
pytest tests/unit/test_shortlink_service.py -v
pytest tests/unit/test_metrics_snapshot.py -v
```

#### 2.2 Fix FATE Scorer (6 failing tests)
**Current:** 25/31 tests passing (81%)
**File:** `Backend/services/fate_scorer.py`
**Test:** `Backend/tests/unit/test_fate_scoring.py`

**Action:**
1. Run tests: `pytest tests/unit/test_fate_scoring.py -v`
2. Identify failing tests
3. Fix implementation
4. Re-run until 31/31 passing

#### 2.3 Test Content Ops Workers
```bash
pytest tests/unit/test_content_ops_workers.py -v
```

**Workers to validate:**
- Slot Executor Worker (OPS-013)
- Learner Worker (OPS-014)
- Inbound Listener Worker (OPS-015)
- Responder Worker (OPS-016)

**Success:** Phase 2 at 90%+ completion

---

### TASK 3: Create 25 AI Templates (2-3 hours)

**Template Structure:**
```json
{
  "id": "template-001",
  "name": "Contrarian Hook",
  "category": "problem-aware",
  "awareness_level": "problem-aware",
  "prompt_text": "Everyone thinks {common_belief}, but here's why {contrarian_truth}. Let me explain {key_insight}.",
  "variables": ["common_belief", "contrarian_truth", "key_insight"],
  "fate_weights": {
    "focus": 0.3,
    "authority": 0.2,
    "tribe": 0.2,
    "emotion": 0.3
  },
  "cta_strength": "soft",
  "platforms": ["twitter", "instagram", "tiktok"],
  "banned_phrases": ["click here", "buy now"]
}
```

#### Template Categories:

**1. Problem-Aware (8 templates)**
```
- Contrarian Hook
- Hidden Problem
- Consequence Frame
- Pattern Interrupt
- Problem Amplification
- Root Cause Reveal
- Time-Sensitive Problem
- Permission to Acknowledge
```

**2. Solution-Aware (7 templates)**
```
- Solution Framework
- Case Study
- Comparison Matrix
- Myth Buster
- Solution Preview
- Risk Reversal
- Expert Insight
```

**3. Product-Aware (6 templates)**
```
- Unique Mechanism
- Transformation Story
- Feature Benefit
- Social Proof Stack
- Objection Handler
- Comparison
```

**4. Most-Aware (4 templates)**
```
- Limited Offer
- Bonus Stack
- Urgency
- Guarantee
```

#### Implementation:
1. Create JSON files in `Backend/templates/` directory
2. Validate each template:
   ```bash
   python -c "from services.template_validator import get_template_validator; validator = get_template_validator(); result = validator.validate_template(template); print(result)"
   ```
3. Seed into database:
   ```bash
   python Backend/scripts/seed_content_templates.py
   ```
4. Test retrieval:
   ```bash
   curl http://localhost:5555/api/templates | jq
   ```

**Success:** 25 templates created, validated, and seeded

---

### TASK 4: Test Content Ops Workers (1 hour)

**Test file:** `Backend/tests/unit/test_content_ops_workers.py`

**Tests to verify:**
1. **Slot Executor Worker**
   - Subscribes to `schedule.due` events
   - Executes scheduled content publication
   - Emits `publish.requested` on execution

2. **Learner Worker**
   - Subscribes to `publish.completed` and `metrics.updated`
   - Updates template leaderboard scores
   - Adjusts bandit arm allocations

3. **Inbound Listener Worker**
   - Subscribes to `comment.received`, `dm.received`
   - Analyzes sentiment and intent
   - Emits `comment.analyzed`, `dm.analyzed`

4. **Responder Worker**
   - Subscribes to `comment.analyzed`, `dm.analyzed`
   - Generates contextual responses
   - Checks DM permissions before sending

**Command:**
```bash
pytest tests/unit/test_content_ops_workers.py -v --tb=short
```

**Success:** All worker tests passing, event flow validated

---

### TASK 5 (STRETCH): Build Instagram Adapter (3-4 hours)

#### ADAPT-004: Instagram Base Adapter

**File:** `Backend/connectors/instagram/instagram_adapter.py`

**Implementation:**
```python
class InstagramAdapter:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.graph_api_url = "https://graph.instagram.com"
    
    async def publish_post(self, content: dict) -> dict:
        # POST to /me/media
        # Parameters: image_url, caption, location_id
        pass
    
    async def publish_story(self, content: dict) -> dict:
        # POST to /me/media with media_type=STORIES
        pass
    
    async def publish_reel(self, content: dict) -> dict:
        # POST to /me/media with media_type=REELS
        pass
    
    async def fetch_metrics(self, post_id: str) -> dict:
        # GET /{media-id}/insights
        # Metrics: likes, comments, shares, saves, reach
        pass
    
    async def fetch_comments(self, post_id: str) -> list:
        # GET /{media-id}/comments
        pass
```

#### ADAPT-005: Instagram Publishing API

**File:** `Backend/api/endpoints/instagram_api.py`

**Endpoints:**
```python
@router.post("/api/instagram/publish")
async def publish_instagram_post(request: PublishRequest):
    # Validate content
    # Call adapter.publish_post()
    # Store in database
    # Emit publish.requested event
    pass

@router.get("/api/instagram/metrics/{post_id}")
async def get_instagram_metrics(post_id: str):
    # Call adapter.fetch_metrics()
    # Return metrics
    pass
```

#### ADAPT-006: Instagram Metrics Integration

**Implementation:**
- Add Instagram to metrics checkback schedule
- Fetch at 1h, 6h, 24h, 72h, 7d intervals
- Store in `touchpoints` table
- Update template leaderboard scores

**Success:** Instagram adapter publishes and fetches metrics

---

### TASK 6 (STRETCH): Trend Discovery (2 hours)

#### TREND-001: Basic Trend Ingestion

**File:** `Backend/services/trend_ingestion_service.py`

**Data Model:**
```python
@dataclass
class TrendItem:
    id: str
    platform: str  # tiktok, instagram, youtube, twitter
    trend_type: str  # hashtag, audio, topic, format
    name: str
    score: float  # trending score
    velocity: float  # rate of growth
    timestamp: datetime
    metadata: dict
```

**Implementation:**
1. Create service class
2. Add provider connectors (TikTok, Instagram)
3. Normalize data from different sources
4. Store in database
5. Emit `trend.raw_ingested` event

**Test:**
```bash
pytest tests/unit/test_trend_ingestion.py -v
```

**Success:** Trends ingested from 2+ platforms

---

## Testing Checklist

### Pre-Session
- [ ] Pull latest code: `git pull`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Check Supabase running: `curl http://localhost:54321`
- [ ] Baseline test run: `pytest tests/unit/ -v --tb=no`

### During Session
- [ ] Write tests FIRST for new features
- [ ] Run tests after each implementation
- [ ] Commit working code frequently
- [ ] Update feature_list.json with passes: true

### Post-Session
- [ ] Full test suite: `pytest tests/ -v`
- [ ] Update PROJECT_STATUS document
- [ ] Create session summary
- [ ] Git commit with descriptive message

---

## Success Metrics

**Minimum (Core Objectives):**
- [ ] Supabase import fixed
- [ ] Phase 2 at 90%+ completion
- [ ] 10+ templates created
- [ ] Worker tests passing

**Good (Primary + Stretch):**
- [ ] All above
- [ ] 25 templates created and seeded
- [ ] Instagram adapter basics working

**Excellent (All Objectives):**
- [ ] All above
- [ ] Instagram fully tested
- [ ] Trend ingestion working
- [ ] 80+ features passing

---

## Files Reference

### Core Files (Already Implemented)
```
Backend/services/sleep_mode_service.py (520 lines)
Backend/services/template_validator.py
Backend/services/awareness_classifier.py
Backend/services/fate_scorer.py
Backend/api/endpoints/sleep.py (275 lines)
Backend/tests/unit/test_sleep_mode_service.py (502 lines)
```

### Files to Fix
```
Backend/database/connection.py (Line 8 - Supabase import)
Backend/services/fate_scorer.py (6 failing tests)
```

### Files to Test
```
Backend/services/dlq_service.py
Backend/services/rate_limiter.py
Backend/services/planner_service.py
Backend/services/dm_permission_service.py
Backend/services/touchpoint_service.py
Backend/services/shortlink_service.py
Backend/services/metrics_snapshot_service.py
```

### Files to Create
```
Backend/templates/problem_aware/*.json (8 files)
Backend/templates/solution_aware/*.json (7 files)
Backend/templates/product_aware/*.json (6 files)
Backend/templates/most_aware/*.json (4 files)
Backend/connectors/instagram/instagram_adapter.py
Backend/api/endpoints/instagram_api.py
Backend/tests/unit/test_instagram_adapter.py
Backend/services/trend_ingestion_service.py
```

---

## Important Notes

### Rules (from DEVELOPER_HANDOFF.md)
1. **Never use `supabase db reset`** - destroys AI analysis data
2. **Never skip process steps** - fail with error, don't skip silently
3. **Always use real OpenAI calls** - no mocks for AI features
4. **Reference media files** - don't duplicate, use source_uri

### Architecture Patterns
- ✅ Event-driven design working well
- ✅ Singleton pattern for services
- ✅ Worker base class for background tasks
- ✅ Pub/Sub via EventBus

### Context for Next Agent
- Sleep Mode (Phase 1) is production-ready
- Content Ops infrastructure is solid
- Template system is well-architected
- Event bus coordination is working

---

**Prepared by:** Claude Sonnet 4.5
**Estimated Session Time:** 4-6 hours
**Expected Outcome:** 80+ features passing, Phase 2 complete, templates ready
**Next Milestone:** Platform adapters and trend discovery
