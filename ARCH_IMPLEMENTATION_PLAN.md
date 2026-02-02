# ARCH-001 to ARCH-008 Implementation Plan

## Goal
Wire together existing subsystems (Sora, Stitcher, ContentAnalyzer, PublishWorker, Twitter, Analytics) into unified orchestrated pipeline.

## Target Workflow
```
Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                          ↓
Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic
```

## Implementation Sequence

### PHASE 1: Core Pipeline (ARCH-001 to ARCH-003)

#### ARCH-001: Master Orchestrator Service
**Status**: Partially complete - `/Backend/services/master_orchestrator.py` exists
**Work Needed**:
- ✅ Service scaffolding exists
- ✅ EventBus integration present
- ✅ Pipeline state tracking in memory
- ✅ Subsystem initialization
- [ ] Complete `start_pipeline()` implementation
- [ ] Complete event handler methods
- [ ] Add database persistence (if not done)
- [ ] Wire all event subscriptions
- [ ] Add proper error handling

**Key Methods**:
- `start_pipeline(config) -> str` - Returns pipeline_id, emits SORA_BATCH_REQUESTED
- `_handle_sora_batch_completed(event)` - Triggers stitching and analysis
- `_handle_publish_completed(event)` - Triggers twitter scheduling
- `_handle_twitter_scheduled(event)` - Marks pipeline step complete
- `get_pipeline_status(pipeline_id) -> dict` - Returns current progress
- `list_pipelines(status, limit) -> List[dict]` - Lists recent pipelines
- `cancel_pipeline(pipeline_id) -> bool` - Cancels running pipeline

**Events**:
- Publishes: `sora.batch.requested`, `stitching.requested`, `analysis.requested`, `publish.requested`
- Subscribes: `sora.batch.completed`, `stitching.completed`, `analysis.completed`, `publish.completed`, `twitter.campaign.scheduled`

---

#### ARCH-002: 3-Part Sora Batch Coordination
**File**: `/Backend/automation/sora/pipeline.py`
**Work Needed**:
- [ ] Add `generate_multi_part(theme, num_parts, character) -> List[str]` method
- [ ] Batch video generation with part numbering
- [ ] Wait for all parts to complete
- [ ] Return list of output paths
- [ ] Emit `sora.batch.completed` event

**Integration**:
- Called by MasterOrchestrator after receiving `sora.batch.requested`
- Emits `sora.part.generated` for each part
- Final event: `sora.batch.completed` with all video paths

---

#### ARCH-003: Content Analyzer → Publisher Integration
**Files**: `/Backend/services/workers/publish_worker.py`, `/Backend/services/content_analyzer.py`
**Work Needed**:
- [ ] Add analysis hooks in PublishWorker
- [ ] Extract ContentAnalyzer results (titles, hooks, descriptions, hashtags)
- [ ] Auto-inject into publish payload before Blotato submission
- [ ] Create `AnalysisInjector` class to handle payload enrichment

**Integration**:
1. MasterOrchestrator receives `analysis.completed` event
2. Extracts analysis results (hooks, descriptions, etc.)
3. Updates pipeline state with analysis
4. Emits `publish.requested` with enriched payload including:
   - `ai_title`: auto-generated title
   - `ai_description`: auto-generated description
   - `ai_hashtags`: AI-suggested hashtags
   - `detected_hook`: best hook from analysis
   - `emotional_drivers`: key emotions to highlight
5. PublishWorker receives enriched payload and submits to Blotato

---

### PHASE 2: Scheduling & Tracking (ARCH-004 to ARCH-006)

#### ARCH-004: Tweet Scheduler (2-Hour Intervals)
**File**: `/Backend/services/tweet_scheduler.py` (NEW)
**Work Needed**:
- [ ] Create new service for scheduling tweets
- [ ] Implement `schedule_tweet_campaign(offer_url, tweets_per_day, duration_days) -> List[str]`
- [ ] Calculate 2-hour intervals from now
- [ ] Create scheduled tasks in database
- [ ] Emit `twitter.campaign.scheduled` event

**Integration**:
- Called by MasterOrchestrator after publish completes
- Schedules tweets every 2 hours for 24+ hours
- Includes offer URL tracking parameter
- Coordinates with ARCH-005 for traffic attribution

---

#### ARCH-005: Offer Traffic Tracking Service
**File**: `/Backend/services/offer_traffic_tracker.py` (NEW)
**Work Needed**:
- [ ] Create service for tracking traffic and conversions
- [ ] Implement click tracking (UTM parameters)
- [ ] Track conversion metrics
- [ ] Create `get_pipeline_traffic_report(pipeline_id) -> dict`
- [ ] Implement `get_platform_performance(start_date, end_date) -> dict`
- [ ] Implement `get_top_performing_campaigns(limit, metric) -> List[dict]`

**Integration**:
- Receives `publish.completed` and `twitter.campaign.scheduled` events
- Creates tracking links with `campaign_id=pipeline_id`
- Monitors clicks, views, conversions
- Reports included in ARCH-007 API responses

---

#### ARCH-006: Analytics Feedback Loop
**File**: `/Backend/services/analytics_feedback_loop.py` (VERIFY/ENHANCE)
**Work Needed**:
- [ ] Create/complete `AnalyticsFeedbackLoop` service
- [ ] Implement `analyze_pipeline_performance(pipeline_id) -> dict`
- [ ] Calculate engagement metrics from pipeline posts
- [ ] Use AI to suggest optimizations
- [ ] Store feedback in database for learning
- [ ] Implement `get_top_performing_themes(limit) -> List[dict]`
- [ ] Implement `get_historical_insights(days, min_rating) -> List[dict]`

**Integration**:
- Triggered 24-72 hours after publish by checkback scheduler
- Analyzes views, likes, comments, shares
- Generates AI-powered suggestions for next content
- Results available via ARCH-007 API

---

### PHASE 3: API & Dashboard (ARCH-007 to ARCH-008)

#### ARCH-007: Unified Pipeline API Endpoint
**File**: `/Backend/api/endpoints/orchestrator.py` (ALREADY EXISTS)
**Verification Needed**:
- ✅ `POST /api/orchestrator/pipeline/start` - Start pipeline
- ✅ `GET /api/orchestrator/pipeline/{pipeline_id}` - Get status
- ✅ `GET /api/orchestrator/pipelines` - List pipelines
- ✅ `DELETE /api/orchestrator/pipeline/{pipeline_id}` - Cancel
- ✅ `GET /api/orchestrator/pipeline/{pipeline_id}/events` - Debugging
- ✅ `GET /api/orchestrator/stats` - Overall metrics
- ✅ `GET /api/orchestrator/metrics` - Dashboard metrics
- ✅ Analytics endpoints (ARCH-006 integration)
- ✅ Traffic endpoints (ARCH-005 integration)
- Health check endpoint

**Work Needed**:
- [ ] Verify all endpoints are wired to actual implementations
- [ ] Test end-to-end API calls
- [ ] Add error handling for edge cases

---

#### ARCH-008: Pipeline Dashboard Widget
**File**: `/dashboard/app/components/` (NEW)
**Work Needed**:
- [ ] Create PipelineStatus widget (shows current active pipeline)
- [ ] Create PipelineList widget (shows recent pipelines)
- [ ] Create PipelineMetrics widget (shows stats)
- [ ] Create PipelineCharts component (visualize progress)
- [ ] Add real-time WebSocket updates
- [ ] Add start pipeline form
- [ ] Add cancel pipeline button

**Features**:
- Display current pipeline status with progress bar
- Show estimated time remaining
- List recent pipelines with status badges
- Display key metrics: videos generated, posts published, tweets scheduled
- Show traffic and engagement metrics
- AI feedback and optimization suggestions

---

## Database Schema Updates

### New Tables/Columns Needed

#### `pipeline_executions` table
```sql
CREATE TABLE pipeline_executions (
  id UUID PRIMARY KEY,
  theme TEXT NOT NULL,
  status VARCHAR(50) NOT NULL,  -- initializing, generating_video, analyzing, publishing, scheduling_tweets, completed, failed
  num_parts INTEGER DEFAULT 3,
  character VARCHAR(255),
  publish_platforms TEXT[] DEFAULT ['tiktok','instagram','youtube'],
  schedule_tweets BOOLEAN DEFAULT true,
  tweets_per_day INTEGER,
  offer_url TEXT,

  -- Pipeline outputs
  video_paths TEXT[],
  stitched_video TEXT,
  analysis_results JSONB,

  -- Progress tracking
  steps_completed INTEGER DEFAULT 0,
  total_steps INTEGER DEFAULT 8,
  current_step VARCHAR(255),
  progress_percent INTEGER DEFAULT 0,

  -- Publishing results
  published_count INTEGER DEFAULT 0,
  tweets_scheduled INTEGER DEFAULT 0,

  -- Timing
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,

  -- Error tracking
  error_message TEXT,
  error_step VARCHAR(255),
  retry_count INTEGER DEFAULT 0
);
```

#### `campaign_traffic` table
```sql
CREATE TABLE campaign_traffic (
  id UUID PRIMARY KEY,
  pipeline_id UUID REFERENCES pipeline_executions(id),
  offer_url TEXT NOT NULL,
  tracking_code VARCHAR(255) UNIQUE,

  -- Metrics
  total_clicks INTEGER DEFAULT 0,
  conversions INTEGER DEFAULT 0,
  revenue_usd DECIMAL(10, 2) DEFAULT 0,

  -- Platform breakdown
  platform TEXT,  -- tiktok, instagram, twitter, youtube
  platform_clicks INTEGER DEFAULT 0,
  platform_conversions INTEGER DEFAULT 0,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `pipeline_feedback` table
```sql
CREATE TABLE pipeline_feedback (
  id UUID PRIMARY KEY,
  pipeline_id UUID REFERENCES pipeline_executions(id),

  -- Performance metrics
  total_views INTEGER,
  total_engagement INTEGER,
  engagement_rate DECIMAL(5, 2),
  conversion_rate DECIMAL(5, 2),

  -- AI Feedback
  rating VARCHAR(20),  -- excellent, good, average, poor
  suggestions JSONB,  -- AI-generated suggestions
  top_performing_hooks TEXT[],
  top_performing_hashtags TEXT[],

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Testing Strategy

### Unit Tests
- Master Orchestrator: test state transitions, event handling
- SoraBatch: test multi-part generation
- Analyzer integration: test payload enrichment
- Traffic tracker: test URL generation and click tracking

### Integration Tests
- Full pipeline: Sora → Stitch → Analyze → Publish
- Event ordering and correlation
- Database persistence
- Error recovery and retries

### E2E Tests
- API endpoint testing
- Frontend widget functionality
- Real workflow with mock services

---

## Success Criteria

### ARCH-001
- [x] EventBus subscriptions working
- [ ] All event handlers implemented and tested
- [ ] Pipeline state persisted to database
- [ ] Status API returning correct values
- [ ] Error cases handled gracefully

### ARCH-002
- [ ] `generate_multi_part()` method exists and works
- [ ] Emits individual part completion events
- [ ] Final `batch.completed` event has all video paths
- [ ] Handles failures in individual parts

### ARCH-003
- [ ] PublishWorker receives analysis results
- [ ] Titles/descriptions auto-injected into payload
- [ ] Blotato receives enriched publish request
- [ ] AI-generated content visible in published posts

### ARCH-004
- [ ] Tweet scheduler creates scheduled tweets
- [ ] 2-hour intervals calculated correctly
- [ ] Includes offer URL with tracking params
- [ ] Proper coordination with traffic tracking

### ARCH-005
- [ ] Tracking URLs generated correctly
- [ ] Click events recorded
- [ ] Conversion tracking working
- [ ] Reports show platform breakdown

### ARCH-006
- [ ] Feedback loop triggered automatically
- [ ] Analytics data aggregated correctly
- [ ] AI suggestions generated
- [ ] Historical data stored for learning

### ARCH-007
- [ ] All endpoints tested and working
- [ ] Proper error responses
- [ ] WebSocket updates real-time
- [ ] CORS headers correct

### ARCH-008
- [ ] Widgets render correctly
- [ ] Real-time updates working
- [ ] Forms submit to API
- [ ] Progress bar updates smoothly

---

## Implementation Timeline

1. **Start with ARCH-001**: Verify master orchestrator is complete
2. **Then ARCH-002**: Add Sora batch coordination
3. **Then ARCH-003**: Wire analyzer to publisher
4. **Then ARCH-004 & ARCH-005**: Add scheduling and tracking in parallel
5. **Then ARCH-006**: Complete feedback loop
6. **Then ARCH-007**: Verify and test all API endpoints
7. **Finally ARCH-008**: Build frontend dashboard

---

## Key Files to Modify

```
Backend/services/
├── master_orchestrator.py (ARCH-001) - Complete
├── tweet_scheduler.py (ARCH-004) - CREATE NEW
├── offer_traffic_tracker.py (ARCH-005) - CREATE NEW
├── analytics_feedback_loop.py (ARCH-006) - Verify/enhance
├── workers/
│   └── publish_worker.py (ARCH-003) - Add analysis hooks
├── event_bus/
│   └── topics.py - Add new topics as needed
└── event_bus/bus.py - Already has pub/sub

Backend/automation/sora/
└── pipeline.py (ARCH-002) - Add generate_multi_part()

Backend/api/endpoints/
└── orchestrator.py (ARCH-007) - Already exists, verify

Dashboard/app/
├── components/
│   ├── PipelineStatus.tsx (ARCH-008)
│   ├── PipelineList.tsx (ARCH-008)
│   ├── PipelineMetrics.tsx (ARCH-008)
│   └── PipelineStartForm.tsx (ARCH-008)
└── hooks/
    └── usePipelineStatus.ts (ARCH-008)

feature_list.json - Update ARCH-001 through ARCH-008 to passes: true
```

---

## Notes

- All services use EventBus for decoupling
- Correlation IDs track requests through entire pipeline
- Database provides audit trail for debugging
- Real OpenAI calls for content analysis (no mocks)
- Sleep mode integrated automatically (workers pause/resume)
- Error handling uses clear messages, no silent skips
