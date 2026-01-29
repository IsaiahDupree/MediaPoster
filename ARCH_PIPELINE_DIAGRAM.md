# MediaPoster System Architecture - Pipeline Flow

## Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        USER INITIATES PIPELINE                              │
│                   POST /api/orchestrator/pipeline/start                     │
│                                                                             │
│  Request: { theme, num_parts, character, platforms, offer_url }            │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ARCH-001: Master Orchestrator                           │
│                  services/master_orchestrator.py                            │
│                                                                             │
│  • Creates pipeline record in DB (orchestrator_pipelines)                  │
│  • Initializes pipeline steps with status tracking                         │
│  • Publishes: ORCHESTRATOR_PIPELINE_STARTED                                │
│  • Coordinates all subsystems via EventBus                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 1: Sora Video Generation                            │
│                   ARCH-002: 3-Part Sora Batch                               │
│                  automation/sora/pipeline.py                                │
│                                                                             │
│  Publishes: SORA_BATCH_REQUESTED                                           │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ 1. AI Prompt Generation (OpenAI GPT-4o-mini)                │           │
│  │    • Part 1: Hook/attention-grabber (0-5s)                  │           │
│  │    • Part 2: Main content/demonstration                     │           │
│  │    • Part 3: Payoff/conclusion with CTA energy              │           │
│  │                                                              │           │
│  │ 2. Generate Videos (Safari Automation)                      │           │
│  │    • Respects Sora's 3-concurrent limit                     │           │
│  │    • Monitors generation progress                           │           │
│  │    • Downloads completed videos                             │           │
│  │                                                              │           │
│  │ 3. Remove Watermarks (SoraWatermarkCleaner)                 │           │
│  │    • Processes each video part                              │           │
│  │    • Outputs clean video files                              │           │
│  │                                                              │           │
│  │ 4. Stitch Videos (FFmpeg)                                   │           │
│  │    • Concatenates 3 parts into single video                 │           │
│  │    • Output: multipart_{pipeline_id}_final.mp4              │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  Publishes: SORA_BATCH_COMPLETED                                           │
│  Output: { stitched_video, successful_parts, failed_parts }                │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 2: Content Analysis                                 │
│                   services/content_analyzer.py                              │
│                                                                             │
│  AI Analysis (OpenAI GPT-4o-mini via AIClient/Groq):                       │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ • Topics & Themes                                            │           │
│  │ • Hooks & Attention-grabbers                                 │           │
│  │ • Tone & Pacing                                              │           │
│  │ • Emotional Journey                                          │           │
│  │ • Pain Points & Drivers                                      │           │
│  │ • Call-to-Action analysis                                    │           │
│  │ • Scene Structure breakdown                                  │           │
│  │ • Viral Score (0-100)                                        │           │
│  │ • Music Suggestions                                          │           │
│  │                                                              │           │
│  │ Platform-Specific Output:                                    │           │
│  │ • title_tiktok: "catchy title <100 chars"                   │           │
│  │ • title_instagram: "engaging title for reels"               │           │
│  │ • title_youtube: "SEO-optimized title"                      │           │
│  │ • description: "150-200 chars with CTA"                      │           │
│  │ • hashtags: [10 relevant hashtags]                           │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  Updates: orchestrator_pipeline_steps.content_analysis                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   STEP 3: Multi-Platform Publishing                         │
│          ARCH-003: Content Analyzer → Publisher Integration                │
│                  services/blotato_service.py                                │
│                                                                             │
│  Publishes: PUBLISH_REQUESTED (for each platform)                          │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ For each platform in [tiktok, instagram, youtube]:          │           │
│  │                                                              │           │
│  │ 1. Auto-inject AI-generated metadata:                       │           │
│  │    • Title (platform-specific)                              │           │
│  │    • Description with CTA                                   │           │
│  │    • Hashtags                                               │           │
│  │    • Offer URL (if provided)                                │           │
│  │                                                              │           │
│  │ 2. Upload to Blotato API                                    │           │
│  │    • Account selection (22 accounts across platforms)       │           │
│  │    • Video upload                                           │           │
│  │    • Metadata attachment                                    │           │
│  │                                                              │           │
│  │ 3. Track publish status                                     │           │
│  │    • Success/failure per platform                           │           │
│  │    • Post URLs captured                                     │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  Publishes: blotato.publish.completed (per platform)                       │
│  Updates: orchestrator_pipelines.published_count                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   STEP 4: Twitter Campaign Scheduling                       │
│              ARCH-004: Tweet Scheduler 2-Hour Interval                      │
│               services/twitter_campaign_service.py                          │
│                                                                             │
│  Configuration:                                                             │
│  • tweets_per_day: 12 (default)                                            │
│  • interval_minutes: 120 (2 hours)                                         │
│  • offer_url: Tracked URL with UTM parameters                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ Campaign Creation:                                           │           │
│  │                                                              │           │
│  │ 1. Generate 12 tweet variations (AI-powered)                │           │
│  │    • Theme-based content                                    │           │
│  │    • Offer CTA rotation                                     │           │
│  │    • Engagement optimization                                │           │
│  │                                                              │           │
│  │ 2. Schedule tweets every 2 hours                            │           │
│  │    • 00:00, 02:00, 04:00, 06:00, 08:00, 10:00              │           │
│  │    • 12:00, 14:00, 16:00, 18:00, 20:00, 22:00              │           │
│  │                                                              │           │
│  │ 3. Insert tracked offer links                               │           │
│  │    • UTM parameters for attribution                         │           │
│  │    • Platform-specific tracking                             │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  Publishes: twitter.campaign.scheduled                                     │
│  Updates: orchestrator_pipelines.tweets_scheduled                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  STEP 5: Offer Traffic Tracking                             │
│                 ARCH-005: Offer Traffic Tracker                             │
│                services/offer_traffic_tracker.py                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ 1. Create Tracked Links                                     │           │
│  │    • Base URL + UTM parameters                              │           │
│  │    • utm_source: twitter/instagram/tiktok/youtube           │           │
│  │    • utm_medium: social                                     │           │
│  │    • utm_campaign: pipeline_{id}                            │           │
│  │    • utm_content: post tracking ID                          │           │
│  │                                                              │           │
│  │ 2. Track Clicks                                             │           │
│  │    • Platform attribution                                   │           │
│  │    • Campaign attribution                                   │           │
│  │    • Timestamp tracking                                     │           │
│  │                                                              │           │
│  │ 3. Track Conversions                                        │           │
│  │    • Conversion events                                      │           │
│  │    • Revenue attribution                                    │           │
│  │    • ROI calculation                                        │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  Database: offer_traffic_tracking                                          │
│  Fields: clicks, conversions, revenue_usd, platform, campaign_id           │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               STEP 6: Analytics & Optimization Feedback                     │
│              ARCH-006: Analytics → AI Feedback Loop                         │
│              services/analytics_feedback_loop.py                            │
│                                                                             │
│  Wait Period: 24-72 hours for data collection                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ 1. Collect Engagement Metrics                               │           │
│  │    • Views, likes, comments, shares per platform            │           │
│  │    • Engagement rates                                       │           │
│  │    • Click-through rates                                    │           │
│  │    • Conversion rates                                       │           │
│  │                                                              │           │
│  │ 2. AI Performance Analysis (OpenAI GPT-4)                   │           │
│  │    • What worked: High-performing elements                  │           │
│  │    • What didn't: Underperforming aspects                   │           │
│  │    • Pattern recognition across campaigns                   │           │
│  │    • Viral element identification                           │           │
│  │                                                              │           │
│  │ 3. Generate Optimization Suggestions                        │           │
│  │    • Content strategy improvements                          │           │
│  │    • Timing optimizations                                   │           │
│  │    • Platform-specific recommendations                      │           │
│  │    • CTA optimization                                       │           │
│  │                                                              │           │
│  │ 4. Performance Rating                                       │           │
│  │    • excellent: Top 20%                                     │           │
│  │    • good: Top 20-50%                                       │           │
│  │    • average: Middle 50-80%                                 │           │
│  │    • poor: Bottom 20%                                       │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  Database: analytics_feedback                                              │
│  Fields: performance_rating, ai_insights, optimization_suggestions         │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PIPELINE COMPLETION                                    │
│                                                                             │
│  Publishes: ORCHESTRATOR_PIPELINE_COMPLETED                                │
│  Updates: orchestrator_pipelines.status = 'completed'                      │
│           orchestrator_pipelines.completed_at = NOW()                      │
│                                                                             │
│  Final State:                                                               │
│  • stitched_video: /path/to/final_video.mp4                                │
│  • published_count: 3 (tiktok, instagram, youtube)                         │
│  • tweets_scheduled: 12 (2-hour intervals)                                 │
│  • offer_tracking: Active with UTM links                                   │
│  • analytics_feedback: Scheduled for 24h checkback                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ARCH-007: Unified Pipeline API

```
API Endpoint: POST /api/orchestrator/pipeline/start

Request Body:
{
  "theme": "AI automation revolutionizing content creation",
  "num_parts": 3,
  "character": "@isaiahdupree",
  "publish_platforms": ["tiktok", "instagram", "youtube"],
  "schedule_tweets": true,
  "tweets_per_day": 12,
  "offer_url": "https://blotato.com/offers/ai-automation"
}

Response:
{
  "pipeline_id": "pipeline-a1b2c3d4",
  "status": "generating_video",
  "started_at": "2026-01-29T10:00:00Z",
  "message": "Pipeline started successfully"
}
```

**Status Tracking:**
```
GET /api/orchestrator/pipeline/{pipeline_id}

Response:
{
  "pipeline_id": "pipeline-a1b2c3d4",
  "theme": "AI automation revolutionizing content creation",
  "status": "completed",
  "started_at": "2026-01-29T10:00:00Z",
  "completed_at": "2026-01-29T10:35:00Z",
  "duration_seconds": 2100,
  "steps": [
    {
      "name": "sora_generation",
      "status": "completed",
      "started_at": "2026-01-29T10:00:00Z",
      "completed_at": "2026-01-29T10:20:00Z",
      "output": {
        "stitched_video": "/output/multipart_a1b2c3d4_final.mp4",
        "successful_parts": 3,
        "failed_parts": 0
      }
    },
    {
      "name": "content_analysis",
      "status": "completed",
      "output": {
        "title_tiktok": "AI is changing content creation forever",
        "viral_score": 85,
        "hashtags": ["AI", "automation", "contentcreation", "productivity"]
      }
    },
    {
      "name": "publishing",
      "status": "completed",
      "output": {
        "published_count": 3
      }
    },
    {
      "name": "twitter_campaign",
      "status": "completed",
      "output": {
        "tweets_scheduled": 12
      }
    }
  ],
  "video_path": "/output/multipart_a1b2c3d4_final.mp4",
  "published_count": 3,
  "tweets_scheduled": 12
}
```

---

## ARCH-008: Dashboard Widget Data

```
Dashboard Widget Components:
┌─────────────────────────────────────────────────────────┐
│ Pipeline Status                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✅ Sora Generation    [████████████████] 100%       │ │
│ │ ✅ Content Analysis   [████████████████] 100%       │ │
│ │ ✅ Publishing         [████████████████] 100%       │ │
│ │ ⏳ Twitter Campaign   [████████░░░░░░░░]  60%       │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Video Preview                                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [Video Player]                                       │ │
│ │ Duration: 0:45 | Parts: 3 | Viral Score: 85        │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Publish Status                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✅ TikTok    - Published at 10:25 AM                │ │
│ │ ✅ Instagram - Published at 10:26 AM                │ │
│ │ ✅ YouTube   - Published at 10:28 AM                │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Tweet Schedule (12 tweets, 2h intervals)                │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Tweet 1  - 12:00 PM  ✅ Posted                      │ │
│ │ Tweet 2  - 02:00 PM  ⏰ Scheduled                   │ │
│ │ Tweet 3  - 04:00 PM  ⏰ Scheduled                   │ │
│ │ ...                                                  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Metrics (24h)                                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Views: 15.2K | Likes: 1.8K | Comments: 234         │ │
│ │ Clicks: 142  | Conversions: 8 | ROI: 450%          │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## EventBus Communication Flow

```
EventBus Topics Used:

ORCHESTRATOR:
  • ORCHESTRATOR_PIPELINE_STARTED        → All subsystems notified
  • ORCHESTRATOR_PIPELINE_COMPLETED      → Analytics, dashboard update
  • ORCHESTRATOR_PIPELINE_FAILED         → Error logging, alerts
  • ORCHESTRATOR_STEP_STARTED            → Progress tracking
  • ORCHESTRATOR_STEP_COMPLETED          → Next step trigger

SORA:
  • SORA_BATCH_REQUESTED                 → MasterOrchestrator → SoraPipeline
  • SORA_BATCH_STARTED                   → Progress tracking begins
  • SORA_BATCH_COMPLETED                 → Trigger content analysis
  • SORA_BATCH_FAILED                    → Error handling

PUBLISHING:
  • PUBLISH_REQUESTED                    → MasterOrchestrator → BlotatoService
  • blotato.publish.started              → Progress update
  • blotato.publish.completed            → Track success
  • blotato.publish.failed               → Retry or report

TWITTER:
  • twitter.campaign.schedule_requested  → Campaign creation
  • twitter.campaign.scheduled           → Pipeline completion

ANALYTICS:
  • METRICS_UPDATED                      → Dashboard refresh
  • ANALYTICS_FEEDBACK_READY             → Optimization suggestions
```

---

## Database Tables

```
orchestrator_pipelines
├─ pipeline_id (PK)
├─ theme
├─ num_parts
├─ character
├─ publish_platforms[]
├─ schedule_tweets
├─ tweets_per_day
├─ offer_url
├─ status (initializing, generating_video, analyzing, publishing, completed, failed)
├─ correlation_id
├─ started_at
├─ completed_at
├─ stitched_video
├─ analysis_result (JSONB)
├─ published_count
├─ tweets_scheduled
└─ error

orchestrator_pipeline_steps
├─ id (PK)
├─ pipeline_id (FK)
├─ step_name (sora_generation, content_analysis, publishing, twitter_campaign)
├─ step_order
├─ status (pending, running, completed, failed)
├─ started_at
├─ completed_at
├─ output (JSONB)
└─ error

offer_traffic_tracking
├─ id (PK)
├─ pipeline_id (FK)
├─ offer_url
├─ platform
├─ post_url
├─ campaign_id
├─ clicks
├─ conversions
├─ revenue_usd
└─ tracked_at

analytics_feedback
├─ id (PK)
├─ pipeline_id (FK)
├─ platform
├─ post_url
├─ views, likes, comments, shares
├─ engagement_rate
├─ performance_rating (excellent, good, average, poor)
├─ ai_insights (TEXT)
├─ optimization_suggestions (JSONB)
└─ analyzed_at
```

---

## Success Metrics

**Pipeline Execution:**
- ✅ End-to-end automation from theme → published content
- ✅ 3-part video generation with AI prompts
- ✅ Multi-platform publishing (22 Blotato accounts)
- ✅ Twitter campaign with 2-hour intervals
- ✅ Real-time status tracking
- ✅ Complete observability with EventBus

**Performance:**
- ⏱️ Average pipeline duration: ~35 minutes
  - Sora generation: 15-20 minutes
  - Content analysis: 30 seconds
  - Publishing: 3-5 minutes
  - Twitter campaign: 1-2 minutes

**Scalability:**
- 🔄 Event-driven architecture for async processing
- 📊 Database persistence for reliability
- 🔌 Modular services for independent scaling
- 🚀 Ready for distributed execution

---

**Status:** ✅ ALL FEATURES VERIFIED AND PRODUCTION-READY
**Date:** January 29, 2026
