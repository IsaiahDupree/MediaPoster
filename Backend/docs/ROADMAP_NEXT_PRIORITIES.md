# MediaPoster - Next Priorities Roadmap

**Updated:** January 20, 2026
**Current Status:** 162/293 features complete (55.3%)

---

## Phases Complete ✅

| Phase | Name | Progress | Status |
|-------|------|----------|--------|
| **Phase 1** | Sleep/Wake Mode | 12/12 (100%) | ✅ Complete |
| **Phase 2** | Content Ops Controller | 35/35 (100%) | ✅ Complete |
| **Phase 3** | AI Templates | 21/21 (100%) | ✅ Complete |
| **Phase 4** | Platform Adapters | 34/34 (100%) | ✅ Complete |
| **Phase 5** | Media Factory | 8/8 (100%) | ✅ Complete |
| **Phase 7** | Multi-Channel | 8/8 (100%) | ✅ Complete |

---

## Recommended Next Phase: **Phase 6 - Content Pipeline** 🎯

**Progress:** 12/50 features (24%)
**Category:** Content sourcing, analysis, approval, scheduling

### Why Phase 6?
1. **High Impact:** Automates content sourcing and curation
2. **P0 Features:** 6 critical P0 features ready to implement
3. **User Value:** Tinder-style approval UI, smart scheduling, auto-analysis
4. **Foundation:** Required for Phase 8 (Autonomy)

### Phase 6 Top Priorities (P0 Features)

#### 1. PIPE-001: Content Sourcing Engine [P0, 4h]
**Status:** Not started
**Description:** Auto-discover and ingest content from local media folders
**Files:** `Backend/services/content_sourcing_engine.py`
**Acceptance:**
- Monitor local media folders (iPhone Import: 8491 items)
- Auto-ingest new videos/images
- Deduplication on file hash
- Status tracking (pending, ingested, failed)

**Implementation Notes:**
- Use watchdog for file system monitoring
- Integrate with existing `IphoneDirectImport` service
- Store in `media_library` table

---

#### 2. PIPE-002: AI Content Analysis [P0, 4h]
**Status:** Not started
**Description:** Analyze visual content: scene, objects, mood, niche, quality score
**Files:** `Backend/services/ai_content_analyzer.py`
**Acceptance:**
- Extract frames from video
- GPT-4 Vision analysis: scene, objects, mood
- Niche classification (fitness, tech, travel, etc.)
- Quality score (1-10)
- Store in `content_analysis` table

**Implementation Notes:**
- Use existing `enhanced_vision_analyzer.py` as base
- Add structured JSON output
- Batch processing for efficiency

---

#### 3. PIPE-003: AI Title/Description Generator [P0, 3h]
**Status:** Not started
**Description:** Generate 3-5 title and description variations per content
**Files:** `Backend/services/title_generator.py`
**Acceptance:**
- Generate 3-5 title variations
- Generate 3-5 description variations
- Platform-specific optimization (IG, TikTok, YouTube)
- Store in `title_variations` table

**Implementation Notes:**
- Use GPT-4 with structured output
- Template-based generation
- Length limits per platform

---

#### 4. PIPE-004: Platform Matching Engine [P0, 3h]
**Status:** Not started
**Description:** Match content to platforms based on format, niche, quality
**Files:** `Backend/services/platform_matcher.py`
**Acceptance:**
- Analyze aspect ratio (9:16, 16:9, 1:1)
- Niche → platform mapping
- Quality threshold filtering
- Return list of suitable platforms

**Implementation Notes:**
- Rule-based matching
- Configurable thresholds
- Integration with platform adapters

---

#### 5. PIPE-005: Tinder-Style Swipe Approval [P0, 4h]
**Status:** Not started
**Description:** Rapid content curation with swipe gestures (right=approve, left=skip)
**Files:**
- `Backend/api/endpoints/content_approval.py`
- `dashboard/app/approval/page.tsx`
**Acceptance:**
- Swipe right = approve
- Swipe left = skip
- Keyboard shortcuts (arrow keys)
- Batch approval mode
- Undo last action

**Implementation Notes:**
- React Beautiful DND or Framer Motion
- Mobile-friendly gestures
- Queue management

---

#### 6. PIPE-006: Smart Scheduling [P0, 3h]
**Status:** Not started
**Description:** Post every 4 hours during daylight (6AM-10PM) with timezone awareness
**Files:** `Backend/services/smart_scheduler.py`
**Acceptance:**
- 4-hour intervals
- Daylight hours only (6AM-10PM)
- Timezone-aware
- Skip if slot already filled
- Integration with PostScheduler

**Implementation Notes:**
- Use existing scheduler infrastructure
- Add timezone detection
- Conflict resolution

---

### Phase 6 Additional P0 Features

#### 7. ANALYTICS-001: Multi-Platform Analytics Aggregator [P0, 4h]
Aggregate analytics from IG, TikTok, YouTube, Twitter

#### 8. CUR-001: Batch Video Analysis [P0, 4h]
Queue all unanalyzed videos for AI analysis (transcript, sentiment)

#### 9. CUR-002: Sentiment Analysis [P0, 3h]
Score transcripts (-1 to 1) with labels (negative/neutral/positive)

#### 10. CUR-003: Duplicate Transcript Detection [P0, 3h]
Fuzzy matching to identify >90% similar transcripts

#### 11. CUR-004: Bulk Delete with Audit Log [P0, 2h]
Bulk delete duplicates from iPhone Import folder with confirmation

#### 12. IPHONE-001: iPhone Direct Import [P0, 4h]
Direct import from iPhone via USB/local folder monitoring

---

## Alternative Priority: **Phase 8 - Autonomy** 🤖

**Progress:** 1/27 features (3.7%)
**Category:** Experiments, bandit allocation, auto-fork, approval queue

### Why Phase 8?
1. **True Autonomy:** Self-optimizing content system
2. **Bandit Allocation:** Automated 70/20/10 template allocation
3. **Human-in-the-Loop:** Approval queue for uncertain content
4. **Agent Monitoring:** Automation Center dashboard

### Phase 8 Top Priorities (P0 Features)

#### 1. AUTO-002: Bandit Allocation Automation [P0, 4h]
Automated 70/20/10 allocation based on template performance

#### 2. AUTO-005: Human Approval Queue [P0, 3h]
Queue uncertain content for human review

#### 3. AUTO-006: Autonomous Slot Executor [P0, 4h]
Execute scheduled slots without human intervention

#### 4. AC-001: Automation Center Dashboard [P0, 4h]
Unified automation center with Narrative Builder + Experiments tabs

#### 5. AC-002: Agent Schedules System [P0, 3h]
Schedule agent runs with cron/interval, enable/disable

#### 6. AC-003: Agent Runs Tracking [P0, 4h]
Track runs with status, progress, heartbeat, artifacts

#### 7. AC-004: Agent Steps Timeline [P0, 3h]
Step-by-step tracking with status, duration, summary

#### 8. NAR-001: Narrative Goals System [P0, 4h]
Define goals with statement, CTA, audience, time horizon, targets

---

## Other High-Value Phases

### Phase 11: Community Inbox (0% complete)
**Value:** Unified comments/DMs with AI reply suggestions
**Top Feature:** INBOX-004 (AI Reply Suggestions) [P0]

### Phase 12: Content Repurposing (0% complete)
**Value:** Long video → shorts (Opus-style)
**Top Features:**
- REPURPOSE-001: Video Analyzer Service [P0]
- REPURPOSE-002: Clip Extraction Engine [P0]
- REPURPOSE-004: Repurposing Queue UI [P0]

### Phase 13: Asset Discovery (0% complete)
**Value:** GIFs, videos, images search (Giphy, Pexels, Unsplash)
**Top Feature:** ASSET-004 (Unified Asset Search UI) [P0]

### Phase 14: E2E Testing (0% complete)
**Value:** Playwright E2E tests with debug logging
**Top Features:** All 6 features are P0 or P1

### Phase 15: Safari Session Manager (0% complete)
**Value:** Health dashboard, multi-account support, analytics
**Top Features:**
- SSM-001: Session Health Dashboard [P0]
- SSM-002: Safari Accounts Table [P0]
- SSM-003: Session Logs Table [P0]

---

## Recommended Implementation Order

### Sprint 1 (Week 1): Content Pipeline Foundation
1. **PIPE-001:** Content Sourcing Engine (4h)
2. **PIPE-002:** AI Content Analysis (4h)
3. **PIPE-003:** AI Title/Description Generator (3h)
4. **PIPE-004:** Platform Matching Engine (3h)
**Total:** 14 hours

### Sprint 2 (Week 2): Content Pipeline UI
1. **PIPE-005:** Tinder-Style Swipe Approval (4h)
2. **PIPE-006:** Smart Scheduling (3h)
3. **CUR-001:** Batch Video Analysis (4h)
4. **CUR-002:** Sentiment Analysis (3h)
**Total:** 14 hours

### Sprint 3 (Week 3): Content Curation
1. **CUR-003:** Duplicate Transcript Detection (3h)
2. **CUR-004:** Bulk Delete with Audit Log (2h)
3. **IPHONE-001:** iPhone Direct Import (4h)
4. **ANALYTICS-001:** Multi-Platform Analytics Aggregator (4h)
**Total:** 13 hours

### Sprint 4 (Week 4): Autonomy Foundation
1. **AUTO-002:** Bandit Allocation Automation (4h)
2. **AUTO-005:** Human Approval Queue (3h)
3. **AUTO-006:** Autonomous Slot Executor (4h)
4. **AC-001:** Automation Center Dashboard (4h)
**Total:** 15 hours

---

## Technical Dependencies

### Phase 6 Dependencies
- ✅ Database (Supabase) - Complete
- ✅ OpenAI API integration - Complete
- ✅ Event Bus - Complete
- ✅ Media Factory pipeline - Complete
- ✅ Platform Adapters - Complete
- ⚠️ File system monitoring (watchdog) - Need to install
- ⚠️ Vision analysis batch processing - Optimization needed

### Phase 8 Dependencies
- ✅ Content Ops Controller - Complete
- ✅ Template system - Complete
- ✅ Scheduler - Complete
- ⚠️ Bandit algorithm implementation - New
- ⚠️ Automation Center UI - New

---

## Testing Strategy

### For Each New Feature:
1. **Unit Tests:** Service-level logic
2. **Integration Tests:** Database + API
3. **E2E Tests:** (Phase 14) Full user workflows

### Test Coverage Goals:
- **Phase 6:** 80% coverage (critical path)
- **Phase 8:** 90% coverage (autonomous operations)

---

## Success Metrics

### Phase 6 Success Criteria:
- ✅ 8491 iPhone videos auto-ingested
- ✅ 100% videos analyzed within 24h
- ✅ Swipe approval throughput: >100 videos/hour
- ✅ Smart scheduling: 4 posts/day, 6AM-10PM

### Phase 8 Success Criteria:
- ✅ Bandit allocation: autonomous 70/20/10 split
- ✅ Human approval queue: <10% of content
- ✅ Autonomous execution: >90% success rate
- ✅ Template auto-fork: >5 new templates/week

---

## Decision: Start with Phase 6 🎯

**Recommendation:** Begin with Phase 6 (Content Pipeline)

**Rationale:**
1. **Immediate Value:** Automates tedious content curation
2. **Foundation for Autonomy:** Phase 8 requires Phase 6 data
3. **User Experience:** Tinder-style UI is highly engaging
4. **Data Generation:** Creates training data for future AI improvements

**Next Steps:**
1. Install dependencies (watchdog, additional AI libraries)
2. Create database migrations for new tables
3. Implement PIPE-001 (Content Sourcing Engine)
4. Run tests and validate with real iPhone Import folder
5. Proceed with PIPE-002, PIPE-003, PIPE-004
6. Build Tinder-style approval UI (PIPE-005)

---

## Notes

- All sleep mode features are production-ready
- Content Ops, Templates, and Platform Adapters are solid
- Media Factory pipeline is complete and tested
- Next logical step is content automation via Phase 6
- Phase 8 (Autonomy) can follow once Phase 6 is complete

**Ready to implement Phase 6!**
