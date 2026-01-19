# MediaPoster Next Session Action Plan
**Date:** 2026-01-19  
**Prepared for:** Next development session

## Current Status Summary

### ✅ Completed (Phase 1)
- Sleep/Wake Mode (12/12 features - 100%)
- All sleep mode services tested and working
- CPU monitoring with auto-sleep
- Wake triggers fully functional
- Event bus integration complete

### 🔄 In Progress (Phase 2)
- Content Ops Controller (~25/50 features - 50%)
- Twitter connector implemented
- Content ops entities (Brand, Offer, ICP)
- Content ops services (FATE scoring, QA gate, etc.)
- Content ops workers running

### ⏭️ Not Started
- Phase 3: 25 AI Templates
- Phase 4: Additional Platform Adapters
- Phase 5: Media Factory enhancements
- Phase 6-10: Advanced features

## Priority 1: Complete Phase 2 Tests

### Test Coverage Gaps
1. **Twitter Connector Tests** (27 tests, 11 failures)
   - Fix DM-related test failures
   - Mock Safari automation properly
   - Fix publishing tests with proper Blotato mocks

2. **Content Ops Service Tests**
   - `test_dm_permission_service.py` - Verify DM consent workflow
   - `test_touchpoint_service.py` - Test touchpoint tracking
   - `test_rate_limiter.py` - Test rate limiting
   - `test_shortlink_service.py` - Test shortlink generation
   - `test_dlq_service.py` - Test dead letter queue
   - `test_metrics_snapshot.py` - Test metrics snapshots

3. **Content Ops Worker Tests**
   - `test_content_ops_workers.py` - Test all 4 workers
   - Integration tests for worker coordination

### Action Items:
```bash
# Run each test file and fix failures
pytest tests/unit/test_twitter_connector.py -v
pytest tests/unit/test_dm_permission_service.py -v
pytest tests/unit/test_touchpoint_service.py -v
pytest tests/unit/test_rate_limiter.py -v
pytest tests/unit/test_shortlink_service.py -v
pytest tests/unit/test_dlq_service.py -v
pytest tests/unit/test_metrics_snapshot.py -v
pytest tests/unit/test_content_ops_workers.py -v
```

## Priority 2: Phase 3 - 25 AI Templates

### Template Categories (TPL-001 to TPL-008)

**Problem-Aware Templates (8):**
1. Problem Discovery - Help user identify they have a problem
2. Problem Amplification - Show severity of the problem
3. Problem Consequences - What happens if not solved
4. Problem Common Mistakes - What doesn't work
5. Problem Hidden Costs - Unexpected impacts
6. Problem Timeline - How long this has been an issue
7. Problem Variants - Different manifestations
8. Problem Myths - Misconceptions about the problem

**Solution-Aware Templates (7):**
1. Solution Introduction - Present the solution category
2. Solution Comparison - Compare different approaches
3. Solution Pros/Cons - Balanced view
4. Solution Case Studies - Real examples
5. Solution Process - How it works
6. Solution Requirements - What's needed
7. Solution Objection Handling - Address concerns

**Product-Aware Templates (6):**
1. Product Differentiation - Why this product vs others
2. Product Features - Key capabilities
3. Product Benefits - Outcomes delivered
4. Product Social Proof - Testimonials/reviews
5. Product Guarantee - Risk reversal
6. Product FAQ - Common questions

**Most-Aware Templates (4):**
1. Limited Offer - Scarcity/urgency
2. New Feature Announcement - Latest updates
3. Customer Success Story - Detailed case study
4. Exclusive Access - VIP/insider content

### Implementation Plan:

**Step 1: Template Data Model** ✅ (Already exists)
- `Backend/database/models.py` - ContentTemplate table
- `Backend/api/endpoints/templates.py` - CRUD API

**Step 2: Seed Templates**
- Create `Backend/scripts/seed_content_templates.py` ✅
- Add all 25 templates with:
  - Name, awareness level, FATE scoring criteria
  - Variable placeholders: `{problem}`, `{solution}`, `{product}`, `{benefit}`, etc.
  - Example content for each template

**Step 3: Template Engine**
- Variable substitution system
- Template validation
- Template versioning (forks)

**Step 4: Template Selection Algorithm**
- Match template to awareness level
- Consider FATE scores
- Use leaderboard for A/B testing

### Action Items:
```bash
# 1. Review existing templates API
cat Backend/api/endpoints/templates.py

# 2. Run seed script (if not already run)
python Backend/scripts/seed_content_templates.py

# 3. Test template CRUD
curl http://localhost:5555/api/templates
curl http://localhost:5555/api/templates/{id}

# 4. Test template leaderboard
curl http://localhost:5555/api/template-leaderboard
```

## Priority 3: Platform Adapters (Phase 4)

### Remaining Adapters (ADAPT-004 to ADAPT-013)

**Instagram Adapter (ADAPT-004, ADAPT-005, ADAPT-006):**
- Publish posts (Feed, Stories, Reels)
- Fetch metrics
- DM handling

**TikTok Adapter (ADAPT-007, ADAPT-008, ADAPT-009):**
- Publish videos
- Fetch metrics  
- DM/comment handling

**YouTube Adapter (ADAPT-010, ADAPT-011, ADAPT-012):**
- Upload videos (Shorts, regular)
- Fetch analytics
- Comment handling

**Threads Adapter (ADAPT-013):**
- Publish threads
- Fetch metrics

### Implementation Approach:
1. Create connector structure: `Backend/connectors/{platform}/connector.py`
2. Implement `SourceAdapter` interface
3. Add Blotato API integration
4. Add platform-specific API calls
5. Write unit tests
6. Register in `Backend/connectors/__init__.py`

## Priority 4: Media Factory (Phase 5)

### Components (MF-001 to MF-008)
- Script generation
- TTS (Text-to-Speech) ✅ (Already implemented)
- Music selection ✅ (Already implemented)
- Visual assets ✅ (Already implemented)
- Remotion rendering ✅ (Already implemented)
- Sora integration ✅ (Already implemented)
- Publishing pipeline ✅ (Already implemented)

**Note:** Most Media Factory features are already implemented. Focus on integration and testing.

## Quick Wins (Low Effort, High Impact)

### 1. Run Full Test Suite
```bash
# Run all unit tests
pytest tests/unit/ -v --tb=short

# Generate coverage report
pytest tests/unit/ --cov=services --cov-report=html
```

### 2. Fix Database Migration Warning
```python
# Update Backend/database/models.py
# Change from:
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# To:
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

### 3. Fix Pytest Asyncio Warning
```ini
# Add to pytest.ini
[pytest]
asyncio_default_fixture_loop_scope = function
```

### 4. Start Backend and Verify
```bash
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# In another terminal, test endpoints
curl http://localhost:5555/health
curl http://localhost:5555/api/sleep/status
curl http://localhost:5555/api/cpu/status
curl http://localhost:5555/api/templates
```

## Testing Checklist

### Unit Tests (Priority Order)
- [ ] Fix Twitter connector tests (11 failures)
- [ ] Run DM permission tests
- [ ] Run touchpoint service tests
- [ ] Run rate limiter tests
- [ ] Run shortlink service tests
- [ ] Run DLQ service tests
- [ ] Run metrics snapshot tests
- [ ] Run content ops workers tests
- [ ] Run template leaderboard tests
- [ ] Run planner service tests

### Integration Tests
- [ ] Sleep mode + scheduler integration
- [ ] Content generation pipeline end-to-end
- [ ] Twitter publishing flow
- [ ] Template selection + generation

### E2E Tests
- [ ] User creates post → Sleep mode → Wake → Publish → Metrics
- [ ] Auto-sleep after idle → Wake on user access
- [ ] Content ops: Generate → QA Gate → Approve → Publish

## Documentation Tasks

### 1. API Documentation
- [ ] Document all sleep mode endpoints
- [ ] Document template API
- [ ] Document platform adapter API
- [ ] Update OpenAPI/Swagger docs

### 2. Developer Handoff
- [ ] Update DEVELOPER_HANDOFF.md with sleep mode
- [ ] Document template system
- [ ] Document worker architecture

### 3. User Documentation
- [ ] Sleep mode usage guide
- [ ] Template selection guide
- [ ] Platform connection guide

## Performance Monitoring

### Metrics to Track
1. **Sleep Mode Effectiveness**
   - Average CPU usage when sleeping
   - Average sleep duration
   - Wake trigger distribution
   - Sleep/wake cycles per day

2. **Template Performance**
   - FATE scores by template
   - Conversion rates
   - Engagement metrics
   - A/B test results

3. **System Health**
   - Worker uptime
   - Event bus throughput
   - API response times
   - Database query performance

### Monitoring Setup
```bash
# Check sleep mode status
curl http://localhost:5555/api/sleep/status | jq

# Check CPU monitor status  
curl http://localhost:5555/api/cpu/status | jq

# Check template leaderboard
curl http://localhost:5555/api/template-leaderboard | jq
```

## Session Preparation Checklist

Before starting next session:
- [ ] Pull latest code from git
- [ ] Review this action plan
- [ ] Start backend server
- [ ] Run health checks
- [ ] Check for any errors in logs
- [ ] Review feature_list.json for completed features
- [ ] Check git status for uncommitted changes

## Success Criteria

### Phase 2 Complete:
- [ ] All unit tests passing (target: 95%+)
- [ ] Content ops workflow tested end-to-end
- [ ] Twitter adapter fully functional
- [ ] DM permission service working
- [ ] Touchpoint tracking verified

### Phase 3 Started:
- [ ] All 25 templates seeded in database
- [ ] Template API tested
- [ ] Template selection algorithm implemented
- [ ] First template-generated post published

## Notes

**Current Strengths:**
- Excellent sleep mode implementation
- Comprehensive event bus architecture
- Good test coverage for core features
- Well-structured codebase

**Areas for Improvement:**
- Complete test coverage for Phase 2
- Fix failing Twitter connector tests
- Add integration tests
- Improve documentation

**Technical Debt:**
- SQLAlchemy deprecation warning
- Pytest asyncio configuration
- Some untested code paths in Twitter connector

---
**End of Action Plan**  
**Next Update:** After Phase 2 completion
