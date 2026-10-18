# PRD: Unified Content Automation System

**Version**: 2.0  
**Date**: January 26, 2026  
**Status**: ✅ Implementation Complete  

---

## 1. Executive Summary

This PRD defines the requirements for a fully automated content creation and distribution system that orchestrates Sora AI video generation, video stitching, content analysis, multi-platform publishing via Blotato, and a Twitter engagement subsystem optimized for driving traffic to offers.

### Target Workflow
```
Sora (1 or 3-part) → Stitch → Analyze → Auto-fill Titles/Descriptions → Post via Blotato (all accounts/platforms)
                                                                      ↓
Tweet Subsystem (every 2h) → Track Engagement → Optimize → Drive Traffic to Offers
```

---

## 2. Current System Inventory

### 2.1 Existing Components

| Component | Status | Location | Description |
|-----------|--------|----------|-------------|
| **Sora Safari Automation** | ✅ Working | `Backend/automation/sora_full_automation.py`, `Backend/automation/sora/pipeline.py` | Safari AppleScript automation for Sora video generation |
| **Video Stitching (ffmpeg)** | ✅ Working | `Backend/services/ai_video_pipeline/stitcher.py` | Concatenation, text overlays, audio mixing |
| **Content Analysis (AI)** | ✅ Working | `Backend/services/content_analyzer.py` | Hooks, tone, viral score, topics extraction |
| **Blotato Publishing** | ✅ Working | `Backend/services/publish_service.py`, `Backend/services/blotato_service.py` | Multi-platform content publishing |
| **Blotato Accounts** | ✅ Configured | `Backend/config/blotato_accounts.py` | 22 accounts across 10 platforms |
| **Twitter Campaign System** | ✅ Exists | `Backend/services/twitter_campaign_service.py`, `Backend/services/twitter_campaign_scheduler.py` | Tweet generation, scheduling, posting |
| **Engagement Automation** | ✅ Running | `Backend/scripts/auto_engagement/` | Comments on Threads/IG/TikTok/Twitter |
| **Event Bus (Pub/Sub)** | ✅ Working | `Backend/services/event_bus.py` | Coordinates workers via events |
| **Sora Worker** | ✅ Exists | `Backend/services/workers/sora_worker.py` | Event-driven video generation |
| **Publish Worker** | ✅ Exists | `Backend/services/workers/publish_worker.py` | Full publish pipeline |

### 2.2 Platform Coverage (Blotato)

| Platform | Accounts | Account IDs |
|----------|----------|-------------|
| TikTok | 4 | 710, 243, 4508, 571 |
| Instagram | 4 | 807, 670, 1369, 4508 |
| Threads | 4 | 173, 201, 1369, 4150 |
| YouTube | 2 | 228, 3370 |
| Twitter/X | 1 | 4151 |
| Pinterest | 2 | 173, 243 |
| LinkedIn | 1 | 571 |
| Facebook | 1 | 786 |
| Bluesky | 1 | 201 |

---

## 3. Requirements

### 3.1 Sora Video Generation Pipeline

#### REQ-SORA-001: Single Video Generation
- **Description**: Generate a single video from a text prompt via Safari automation
- **Status**: ✅ Implemented
- **Acceptance Criteria**:
  - [ ] Navigate to sora.chatgpt.com
  - [ ] Inject prompt into textarea
  - [ ] Configure aspect ratio (9:16 portrait, 16:9 landscape)
  - [ ] Configure duration (10s, 15s, 25s)
  - [ ] Select @character if specified
  - [ ] Click generate and poll for completion
  - [ ] Download completed video

#### REQ-SORA-002: Multi-Part Video Generation (3-Part)
- **Description**: Generate 3 related videos and queue them for stitching
- **Status**: ✅ Implemented
- **Implementation**: `SoraPipeline.generate_multi_part()` in `Backend/automation/sora/pipeline.py`
- **Acceptance Criteria**:
  - [ ] Accept array of 3 prompts with shared theme
  - [ ] Generate all 3 videos (respect Sora's 3-concurrent limit)
  - [ ] Track completion status for each part
  - [ ] Queue completed set for stitching
  - [ ] Handle partial failures gracefully

#### REQ-SORA-003: Usage Monitoring
- **Description**: Check Sora usage limits before generation
- **Status**: ✅ Implemented
- **Acceptance Criteria**:
  - [ ] Extract video_gens_left, free_count, paid_count
  - [ ] Return reset_date
  - [ ] Block generation if no credits available

### 3.2 Video Stitching Pipeline

#### REQ-STITCH-001: Video Concatenation
- **Description**: Concatenate multiple video clips into one
- **Status**: ✅ Implemented
- **Acceptance Criteria**:
  - [ ] Accept list of video file paths
  - [ ] Concatenate in order using ffmpeg
  - [ ] Normalize audio levels
  - [ ] Output single MP4 file

#### REQ-STITCH-002: Text Overlays
- **Description**: Add text overlays (captions, titles) to video
- **Status**: ✅ Implemented
- **Acceptance Criteria**:
  - [ ] Support timed text entries
  - [ ] Configurable font, size, position
  - [ ] Support emoji rendering

#### REQ-STITCH-003: Audio Mixing
- **Description**: Mix narration and background music
- **Status**: ✅ Implemented
- **Acceptance Criteria**:
  - [ ] Layer narration audio over video
  - [ ] Add background music at configurable volume
  - [ ] Ducking support (lower music during speech)

### 3.3 Content Analysis

#### REQ-ANALYSIS-001: Transcript Analysis
- **Description**: Analyze video transcript for viral patterns
- **Status**: ✅ Implemented
- **Acceptance Criteria**:
  - [ ] Extract hooks (attention-grabbing phrases)
  - [ ] Identify tone (energetic/calm/educational/etc.)
  - [ ] Calculate viral_score (0-100)
  - [ ] Extract topics and pain_points
  - [ ] Generate key_moments breakdown

#### REQ-ANALYSIS-002: Auto-Generate Titles
- **Description**: Generate platform-optimized titles from analysis
- **Status**: ✅ Implemented
- **Implementation**: `PublishWorker._generate_ai_metadata()` in `Backend/services/workers/publish_worker.py`
- **Acceptance Criteria**:
  - [ ] Generate title for each platform (character limits vary)
  - [ ] Include detected hook in title
  - [ ] A/B test title variations

#### REQ-ANALYSIS-003: Auto-Generate Descriptions
- **Description**: Generate platform-optimized descriptions
- **Status**: ✅ Implemented
- **Implementation**: `PublishWorker._build_platform_caption()` in `Backend/services/workers/publish_worker.py`
- **Acceptance Criteria**:
  - [ ] Generate description with hashtags
  - [ ] Include CTA for offers
  - [ ] Platform-specific formatting (TikTok vs YouTube)

### 3.4 Publishing Pipeline

#### REQ-PUBLISH-001: Multi-Platform Publishing
- **Description**: Publish content to all configured platforms via Blotato
- **Status**: ✅ Implemented
- **Acceptance Criteria**:
  - [ ] Upload media to Blotato
  - [ ] Submit to each platform with metadata
  - [ ] Poll for published URL
  - [ ] Record in database

#### REQ-PUBLISH-002: Auto-Metadata Injection
- **Description**: Automatically populate title/description from analysis
- **Status**: ✅ Implemented
- **Implementation**: Auto-generates metadata in `_run_publish_pipeline()` before platform submission
- **Acceptance Criteria**:
  - [ ] Analyze content before publish
  - [ ] Inject AI-generated title
  - [ ] Inject AI-generated description
  - [ ] Allow manual override

#### REQ-PUBLISH-003: Duplicate Prevention
- **Description**: Prevent posting same content twice to same account
- **Status**: ✅ Implemented
- **Acceptance Criteria**:
  - [ ] Hash content for fingerprinting
  - [ ] Check against posted_content table
  - [ ] Skip if duplicate detected

### 3.5 Twitter Campaign Subsystem

#### REQ-TWITTER-001: Scheduled Tweet Posting
- **Description**: Post tweets at configurable intervals
- **Status**: ✅ Implemented
- **Implementation**: `TwitterCampaignService(interval_minutes=120)` - default 2-hour intervals
- **Acceptance Criteria**:
  - [ ] Configurable interval_minutes (default 120)
  - [ ] Pull from scheduled_tweets queue
  - [ ] Post via Blotato API with Safari fallback
  - [ ] Record posted_at timestamp

#### REQ-TWITTER-002: Offer-Focused Tweet Generation
- **Description**: Generate tweets that drive traffic to offers
- **Status**: ✅ Implemented
- **Implementation**: `TwitterCampaignService.generate_offer_tweet()` and `schedule_offer_tweets()`
- **Acceptance Criteria**:
  - [ ] Accept offer configuration (URL, description, CTA)
  - [ ] Generate engaging tweet with offer CTA
  - [ ] Include UTM tracking parameters
  - [ ] Vary messaging to avoid repetition

#### REQ-TWITTER-003: Engagement Analytics
- **Description**: Track tweet performance and optimize
- **Status**: ⚠️ 40% Complete
- **Acceptance Criteria**:
  - [ ] Fetch likes, retweets, replies via API
  - [ ] Calculate engagement_rate
  - [ ] Identify top-performing tweet patterns
  - [ ] Feed insights back to generation

### 3.6 Offer Traffic Tracking

#### REQ-OFFERS-001: UTM Link Generation
- **Description**: Generate trackable links for offers
- **Status**: ✅ Implemented
- **Implementation**: `OfferTracker.generate_utm_link()` in `Backend/services/offer_tracker.py`
- **Acceptance Criteria**:
  - [ ] Accept base offer URL
  - [ ] Add UTM parameters (source, medium, campaign)
  - [ ] Optional link shortening
  - [ ] Store link mapping in database

#### REQ-OFFERS-002: Conversion Tracking
- **Description**: Track clicks and conversions from offer links
- **Status**: ✅ Implemented
- **Implementation**: `OfferTracker.record_click()`, `record_conversion()`, Stripe webhooks at `/api/orchestrator/webhooks/stripe`
- **Acceptance Criteria**:
  - [ ] Record click events
  - [ ] Track conversion events (if webhook available)
  - [ ] Attribute conversions to source tweet/post
  - [ ] Generate ROI reports

### 3.7 Master Orchestrator

#### REQ-ORCH-001: End-to-End Pipeline Coordination
- **Description**: Coordinate all subsystems via EventBus
- **Status**: ✅ Implemented
- **Implementation**: `MasterOrchestrator` in `Backend/services/master_orchestrator.py` with REST API at `/api/orchestrator/`
- **Acceptance Criteria**:
  - [ ] Accept content creation request
  - [ ] Trigger Sora generation (1 or 3-part)
  - [ ] Wait for completion, trigger stitch
  - [ ] Analyze stitched video
  - [ ] Auto-fill metadata
  - [ ] Publish to all platforms
  - [ ] Schedule related tweets
  - [ ] Track engagement and conversions

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MASTER ORCHESTRATOR                          │
│            (coordinates all subsystems via EventBus)            │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  SORA PIPELINE  │  │  TWEET ENGINE   │  │  ENGAGEMENT     │
│  ───────────────│  │  ───────────────│  │  AUTOMATION     │
│  - Generate 1-3 │  │  - Every 2h     │  │  ───────────────│
│  - Stitch       │  │  - Offer CTAs   │  │  - Comments     │
│  - Analyze      │  │  - Track clicks │  │  - Likes        │
│  - Queue        │  │  - Optimize     │  │  - Follows      │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BLOTATO PUBLISHER                            │
│  - 22 accounts across 10 platforms                              │
│  - Auto titles/descriptions from AI analysis                    │
│  - Duplicate prevention                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS & OPTIMIZATION                     │
│  - Track engagement metrics                                     │
│  - Offer conversion tracking (UTM)                              │
│  - Feed back to AI for content improvement                      │
└─────────────────────────────────────────────────────────────────┘
```

### 4.1 Event Topics

| Topic | Publisher | Subscriber | Description |
|-------|-----------|------------|-------------|
| `sora.video.requested` | Orchestrator | SoraWorker | Request video generation |
| `sora.video.completed` | SoraWorker | Orchestrator | Video generation done |
| `stitch.requested` | Orchestrator | StitchWorker | Request video stitching |
| `stitch.completed` | StitchWorker | Orchestrator | Stitching done |
| `analysis.requested` | Orchestrator | AnalysisWorker | Request content analysis |
| `analysis.completed` | AnalysisWorker | Orchestrator | Analysis done |
| `blotato.publish.requested` | Orchestrator | PublishWorker | Request publish |
| `blotato.publish.completed` | PublishWorker | Orchestrator | Publish done |
| `tweet.scheduled` | Orchestrator | TweetScheduler | Schedule tweet |
| `tweet.posted` | TweetScheduler | Analytics | Tweet was posted |

---

## 5. Implementation Status

| Requirement | Status | Effort | Priority |
|-------------|--------|--------|----------|
| REQ-SORA-001 | ✅ Done | - | - |
| REQ-SORA-002 | ⚠️ Partial | ~2 hours | P1 |
| REQ-SORA-003 | ✅ Done | - | - |
| REQ-STITCH-001 | ✅ Done | - | - |
| REQ-STITCH-002 | ✅ Done | - | - |
| REQ-STITCH-003 | ✅ Done | - | - |
| REQ-ANALYSIS-001 | ✅ Done | - | - |
| REQ-ANALYSIS-002 | ⚠️ Partial | ~1 hour | P1 |
| REQ-ANALYSIS-003 | ⚠️ Partial | ~1 hour | P1 |
| REQ-PUBLISH-001 | ✅ Done | - | - |
| REQ-PUBLISH-002 | ⚠️ Partial | ~1 hour | P1 |
| REQ-PUBLISH-003 | ✅ Done | - | - |
| REQ-TWITTER-001 | ⚠️ Partial | ~30 min | P2 |
| REQ-TWITTER-002 | ❌ Missing | ~2 hours | P2 |
| REQ-TWITTER-003 | ⚠️ Partial | ~2 hours | P2 |
| REQ-OFFERS-001 | ❌ Missing | ~2 hours | P3 |
| REQ-OFFERS-002 | ❌ Missing | ~2 hours | P3 |
| REQ-ORCH-001 | ⚠️ Partial | ~4 hours | P1 |

**Total Estimated Effort**: ~18 hours

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Video Generation Success Rate | >95% | completed / requested |
| Publish Success Rate | >98% | published / attempted |
| Tweet Posting Adherence | 100% | posted within 5min of scheduled |
| Offer Click-Through Rate | >2% | clicks / impressions |
| Content Analysis Accuracy | >85% | manual review sample |

---

## 7. Next Steps

1. **P1**: Wire 3-part Sora + stitch (REQ-SORA-002)
2. **P1**: Auto-inject AI titles into publish (REQ-PUBLISH-002)
3. **P2**: Configure tweet scheduler to 2h (REQ-TWITTER-001)
4. **P2**: Add offer-focused tweet generation (REQ-TWITTER-002)
5. **P3**: Add offer tracking service (REQ-OFFERS-001, REQ-OFFERS-002)
6. **P1**: Build master orchestrator (REQ-ORCH-001)

---

## 8. Appendix

### 8.1 File Locations

```
Backend/
├── automation/
│   ├── sora_full_automation.py      # Sora Safari control
│   ├── sora/
│   │   ├── pipeline.py              # Sora pipeline orchestration
│   │   ├── sora_controller.py       # Low-level Sora control
│   │   ├── generation_monitor.py    # Poll for completion
│   │   └── video_downloader.py      # Download completed videos
├── services/
│   ├── ai_video_pipeline/
│   │   ├── pipeline.py              # Video creation orchestrator
│   │   └── stitcher.py              # ffmpeg stitching
│   ├── content_analyzer.py          # AI content analysis
│   ├── blotato_service.py           # Blotato API client
│   ├── publish_service.py           # Publishing logic
│   ├── twitter_campaign_service.py  # Tweet generation
│   ├── twitter_campaign_scheduler.py # Tweet scheduling
│   ├── event_bus.py                 # Pub/sub coordination
│   └── workers/
│       ├── sora_worker.py           # Event-driven Sora
│       └── publish_worker.py        # Event-driven publishing
├── scripts/auto_engagement/
│   ├── threads_engagement.py
│   ├── instagram_engagement.py
│   └── tiktok_engagement.py
└── config/
    └── blotato_accounts.py          # Account mappings
```

### 8.2 Database Tables

| Table | Purpose |
|-------|---------|
| `scheduled_tweets` | Tweet queue with scheduled_for timestamp |
| `posted_tweets` | Record of posted tweets with metrics |
| `posted_content` | All published content across platforms |
| `content_analysis` | AI analysis results |
| `offer_links` | UTM-tracked offer links (to be created) |
| `offer_conversions` | Conversion events (to be created) |
