# MediaPoster - Next Session Priorities
**Updated:** 2026-01-19
**Current Completion:** 97/322 (30.1%)

---

## 🔥 TOP 3 CRITICAL PRIORITIES

### 1. Fix Import Errors (BLOCKERS) ⚠️
**Estimated Time:** 1-2 hours
**Impact:** Unblocks all e2e testing

#### Tasks:
- [ ] Create `Backend/services/permission_gate.py`
  - Permission checking service for content gates
  - Interface: `check_permission(user_id, resource, action) → bool`
  - Needed by: `tests/e2e/test_permission_gates.py`

- [ ] Create `Backend/connectors/twitter_adapter.py` (ADAPT-001)
  - X/Twitter platform adapter
  - Methods: `post()`, `get_metrics()`, `schedule()`
  - Integration with Safari automation
  - Needed by: `tests/e2e/test_twitter_adapter.py`

- [ ] Fix `RateLimiter` import in `services/rate_limiter.py`
  - Current: exports `rate_limiter` function
  - Tests expect: `RateLimiter` class
  - Add class wrapper or fix tests

- [ ] Fix async/await in e2e tests
  - `test_post_lifecycle.py` has 6 errors
  - Change: `db_session.commit()` → `await db_session.commit()`
  - Change: `db_session.refresh()` → `await db_session.refresh()`
  - Change: `session.close()` → `await session.close()`

---

### 2. Complete Phase 4: Platform Adapters (96% → 100%) 🎯
**Estimated Time:** 4-6 hours
**Impact:** Full multi-platform publishing capability

#### Remaining Features (8/34):
- [ ] **STORY-001:** Instagram Story Posting (P1)
- [ ] **STORY-002:** Story Scheduling UI (P1)
- [ ] **VID-001:** Video Orientation Router (P1)
- [ ] **SAF-001:** Safari AppleScript Controller (P0) ⭐ **CRITICAL**
- [ ] **SAF-002:** TikTok Comment Automation (P1)
- [ ] **SAF-003:** Safari Session Manager (P1)
- [ ] **SAF-004:** Safari Error Recovery (P1)
- [ ] **SAF-005:** Safari Rate Limiting (P1)

**Focus on SAF-001 first** - it's the only P0 and enables all other Safari features.

---

### 3. Phase 5: Health Checks & Stability (2% → 15%) 🏥
**Estimated Time:** 3-4 hours
**Impact:** Production readiness, monitoring, reliability

#### Critical P0 Features:
- [ ] **MOD-005:** Health Check Endpoints (P0)
  - `/api/health/services` - All service status
  - `/api/health/workers` - Background worker health
  - `/api/health/external` - DB, Redis, APIs
  - Return: service name, status, latency, last_check

- [ ] **MOD-006:** Graceful Shutdown (P0)
  - Complete in-flight operations before shutdown
  - Save state for resume on restart
  - Timeout: 30s max
  - Log incomplete operations

- [ ] **MF-007:** Media Factory JSON Contracts (P0)
  - Define contracts for all pipeline stages
  - Schema: Script → TTS → Music → Visuals → Render
  - Validation for each stage
  - Files: `Backend/services/media_factory/contracts/`

---

## 📋 SECONDARY PRIORITIES

### Phase 6: Content Pipeline (4% → 25%)
**Estimated Time:** 8-12 hours

#### Top P0 Features:
1. **PIPE-001:** Content Sourcing Engine
   - Auto-discover media from folders
   - Deduplication via hash
   - Priority queue by file date

2. **PIPE-002:** AI Content Analysis
   - Scene detection
   - Object recognition
   - Mood/niche classification
   - Quality scoring

3. **PIPE-005:** Tinder-Style Swipe Approval UI
   - Dashboard: `dashboard/app/swipe/page.tsx`
   - Swipe right = approve, left = skip
   - Keyboard shortcuts (arrow keys)

4. **PIPE-006:** Smart Scheduling (4hr intervals)
   - Post every 4 hours during 6AM-10PM
   - Timezone-aware
   - Fill empty slots from approval queue

---

## 🧪 TESTING PRIORITIES

### Fix E2E Tests
- [ ] Fix `test_post_lifecycle.py` (5 failed, 6 errors)
- [ ] Fix `test_permission_gates.py` (import error)
- [ ] Fix `test_rate_limiting.py` (import error)
- [ ] Fix `test_twitter_adapter.py` (import error)
- [ ] Run full e2e suite: `pytest tests/e2e/ -v`

### Add New Tests
- [ ] Safari automation tests
- [ ] Platform adapter tests
- [ ] Health check endpoint tests
- [ ] Media factory contract validation tests

### Test Coverage Goals
- [ ] Core services: >80%
- [ ] API endpoints: >70%
- [ ] Workers: >60%

---

## 🎯 RECOMMENDED SESSION WORKFLOW

### Session 1: Unblock Testing (2 hours)
1. Fix import errors
2. Fix async/await issues
3. Run full e2e suite
4. Verify all tests pass or have clear next steps

### Session 2: Platform Adapters (6 hours)
1. Implement SAF-001 (Safari AppleScript Controller)
2. Complete STORY-001, STORY-002 (Instagram Stories)
3. Complete VID-001 (Video Orientation Router)
4. Test all platform adapters with real posts

### Session 3: Health & Stability (4 hours)
1. Implement MOD-005 (Health Check Endpoints)
2. Implement MOD-006 (Graceful Shutdown)
3. Implement MF-007 (Media Factory Contracts)
4. Add monitoring dashboard widget

### Session 4: Content Pipeline Start (8 hours)
1. Implement PIPE-001 (Content Sourcing)
2. Implement PIPE-002 (AI Analysis)
3. Implement PIPE-005 (Swipe UI)
4. Test full ingestion → analysis → approval flow

---

## 📊 SUCCESS METRICS

### By End of Next 4 Sessions
- [ ] Feature completion: 30% → 40% (97 → 129 features)
- [ ] Phase 4 complete: 100%
- [ ] Phase 5 progress: 2% → 25%
- [ ] Phase 6 progress: 4% → 20%
- [ ] E2E test pass rate: 50% → 85%
- [ ] All P0 blockers resolved

---

## 🚨 KNOWN BLOCKERS

1. **Missing Safari Automation** (SAF-001)
   - Blocks: TikTok automation, Instagram Stories, all browser-based publishing
   - Priority: P0 - Must implement ASAP

2. **Import Errors**
   - Blocks: E2E testing, integration tests
   - Priority: P0 - Fixes are straightforward but required

3. **Async/Await Issues**
   - Blocks: Post lifecycle tests
   - Priority: P1 - Easy fix, low impact

4. **Missing Platform Adapters**
   - Blocks: Multi-platform publishing
   - Priority: P1 - Phase 4 completion

---

## 💡 QUICK WINS (< 1 hour each)

1. Fix Pydantic deprecation warnings (change `env=` to `json_schema_extra`)
2. Fix SQLAlchemy deprecation (change `declarative_base()` to `orm.declarative_base()`)
3. Add `__init__.py` to missing test directories
4. Update all endpoint docstrings with OpenAPI examples
5. Add logging to all worker start/stop events

---

## 📖 REFERENCE DOCS

- **Feature List:** `/feature_list.json` (322 features tracked)
- **PRD Index:** `/PRD_INDEX.md`
- **Content Ops PRD:** `/Backend/docs/PRD_CONTENT_OPS_CONTROLLER.md`
- **Test Spec:** `/Backend/docs/PRD_CONTENT_OPS_TESTS.md`
- **Session Report:** `/SESSION_REPORT_2026-01-19_COMPLETION_STATUS.md`

---

## 🎓 LESSONS LEARNED

1. **Always verify existing implementations** before creating new code
   - Event Bus was already complete, just needed alias fix
   - Sleep Mode was complete, just needed verification

2. **Test early and often**
   - Running tests revealed import issues immediately
   - Event Bus tests confirmed implementation quality

3. **Track features systematically**
   - `feature_list.json` is source of truth
   - Update immediately after verifying/implementing

4. **Follow existing patterns**
   - Event Bus follows clean pub/sub pattern
   - Sleep Mode uses singleton pattern consistently
   - Workers all implement start/stop lifecycle

---

**Ready to implement? Start with Priority 1 (Fix Import Errors) to unblock all testing!**

Generated: 2026-01-19
Next Update: After completing Priority 1
