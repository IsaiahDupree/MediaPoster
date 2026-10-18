# MediaPoster — Master Product Requirements Document

**Version:** 1.0  
**Date:** February 2026  
**Status:** Active Development  
**Priority:** P1 (Tier 1 Core Infrastructure)

---

## Executive Summary

**MediaPoster** is an autonomous content operations controller for multi-platform social media publishing. It combines Safari browser automation, AI-powered content analysis, video production pipelines (Sora), voice cloning, and intelligent scheduling to create a fully automated content machine.

**Core Value:** Generate, analyze, optimize, and publish content across 22+ social accounts with minimal human intervention. Tweet every 2 hours, track engagement, optimize, and drive offer traffic — all on autopilot.

---

## Target Users

- **Solo creators** managing multiple social accounts
- **Agencies** running content for multiple brands
- **Growth marketers** doing high-volume social content
- **E-commerce brands** driving traffic via social content

---

## Product Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MEDIAPOSTER PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │  Content  │──▶│  Content  │──▶│  Auto-   │──▶│  Publishing  │ │
│  │  Sources  │   │  Analyzer │   │  Fill    │   │  (Blotato)   │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘ │
│       │                                              │           │
│  ┌──────────┐                                  ┌──────────────┐ │
│  │   Sora   │                                  │   Twitter    │ │
│  │  Safari  │                                  │  Campaigns   │ │
│  │  Auto    │                                  │  (2hr loop)  │ │
│  └──────────┘                                  └──────┬───────┘ │
│       │                                              │           │
│  ┌──────────┐   ┌──────────┐                  ┌──────────────┐ │
│  │  Video   │──▶│  Voice   │                  │  Analytics   │ │
│  │  Stitch  │   │  Clone   │                  │  + Feedback  │ │
│  └──────────┘   └──────────┘                  └──────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                    SLEEP/WAKE MODE                            ││
│  │  Enters low-power when idle, wakes for scheduled tasks       ││
│  └──────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Modules

### 1. Safari Automation Engine
- **Sora Video Generation:** Automated browser-based video generation via Safari AppleScript
- **3-Part Batch:** Generate multi-part videos and auto-stitch
- **Watermark Removal:** Automated post-processing pipeline
- **Platform Publishing:** Browser-based posting when APIs unavailable

### 2. Content Operations Controller
- **Master Orchestrator:** Coordinates all subsystems via EventBus
- **Content Analyzer:** AI-powered title/description/hashtag generation
- **Auto-Fill Pipeline:** Analyzer output → publish payload injection
- **Template System:** 25 AI-powered content templates

### 3. Multi-Platform Publishing
- **Blotato Integration:** Publish to 22+ accounts simultaneously
- **Platform Support:** Twitter/X, Instagram, TikTok, YouTube, Threads, Facebook
- **Scheduling:** Calendar-based + interval-based (every 2h for tweets)
- **Queue Management:** Priority queues with retry logic

### 4. Video Production Pipeline (Media Factory)
- **Sora Integration:** AI video generation via Safari automation
- **Video Stitching:** Combine multi-part clips into single output
- **Voice Cloning:** IndexTTS-2 via Modal GPU for narration
- **SFX Pipeline:** Sound effects generation and layering
- **Character Generation:** AI character creation for content

### 5. Community Engagement
- **Community Inbox:** Unified comments/DMs across all platforms
- **AI Reply Suggestions:** Context-aware reply generation
- **Relationship-First DM System:** Warm outreach, not cold spam
- **Auto-Engagement:** Strategic liking, commenting, following

### 6. Content Intelligence
- **Competitor Research:** Track competitor content performance
- **Trending Keywords:** Video and topic analysis
- **AI Curation:** Discover and curate relevant content
- **Content Repurposing:** Long video → shorts (Opus-style clipping)

### 7. Analytics & Optimization
- **Analytics Dashboard:** Cross-platform performance metrics
- **Twitter Feedback Loop:** AI agent that tracks and optimizes tweet strategy
- **Offer Traffic Tracking:** Attribution from social → landing page → conversion
- **Growth Data Plane:** Event tracking, segmentation, Meta CAPI

### 8. Sleep/Wake Mode
- **CPU Efficiency:** Pause all workers when idle
- **Wake Triggers:** Scheduled posts, Safari tasks, checkback periods, user access
- **Scheduled Wake:** Pre-wake 5 minutes before post time

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python FastAPI |
| **Database** | Supabase (PostgreSQL) |
| **Queue** | Redis + BullMQ |
| **Automation** | Safari AppleScript |
| **AI** | OpenAI API (real calls, no mocks) |
| **Video** | Sora (Safari), ffmpeg (stitching) |
| **Voice** | IndexTTS-2 via Modal GPU |
| **Dashboard** | Next.js 16 |
| **Analytics** | PostHog, Meta Pixel/CAPI |
| **Email** | Resend |

---

## Database Schema (Key Tables)

| Table | Purpose |
|-------|---------|
| `posts` | Content items with platform targets |
| `publish_queue` | Scheduled + queued posts |
| `publish_log` | Publish results per platform |
| `media_assets` | Videos, images, audio files |
| `ai_analysis` | Content analyzer outputs |
| `platform_accounts` | Connected social accounts |
| `automation_runs` | Safari automation sessions |
| `engagement_log` | Comments, DMs, interactions |
| `analytics_daily` | Daily performance snapshots |
| `sleep_wake_log` | Sleep/wake state transitions |

---

## API Endpoints (Key)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/posts` | Create new post |
| POST | `/api/posts/{id}/publish` | Publish a post |
| GET | `/api/analytics/overview` | Dashboard metrics |
| POST | `/api/automation/sora/generate` | Start Sora generation |
| POST | `/api/orchestrator/run` | Trigger full pipeline |
| GET | `/api/sleep/status` | Sleep mode status |
| POST | `/api/sleep/wake` | Force wake |

---

## PRD Index (Detailed Sub-PRDs)

### Core System
| PRD | Location | Status |
|-----|----------|--------|
| Content Ops Controller | `Backend/docs/PRD_CONTENT_OPS_CONTROLLER.md` | Active |
| Content Ops Technical | `Backend/docs/PRD_CONTENT_OPS_TECHNICAL.md` | Active |
| Content Ops Tests | `Backend/docs/PRD_CONTENT_OPS_TESTS.md` | Active |
| Media Factory | `Backend/docs/MEDIA_FACTORY_PRD.md` | Active |
| System Architecture | `docs/PRD_SYSTEM_ARCHITECTURE_INTEGRATION.md` | Active |
| Architecture Overview | `docs/PRD_ARCHITECTURE_OVERVIEW.md` | Active |

### Content & Publishing
| PRD | Location | Status |
|-----|----------|--------|
| Automated Content Pipeline | `docs/PRD_AUTOMATED_CONTENT_PIPELINE.md` | Active |
| Content Repurposing | `docs/PRD_CONTENT_REPURPOSING_ENGINE.md` | Active |
| Schedule Enhancements | `docs/PRD-Schedule-Page-Enhancements.md` | Active |
| AI Assisted Curation | `docs/PRD_AI_ASSISTED_CURATION.md` | Active |

### Video & Audio
| PRD | Location | Status |
|-----|----------|--------|
| Sora Video Generation | `Backend/docs/PRD-SORA-VIDEO-GENERATION.md` | Active |
| Voice Cloning | `Backend/docs/PRD_VOICE_CLONING_SERVICE.md` | Active |
| SFX Audio Pipeline | `Backend/docs/PRD-SFX-AUDIO-PIPELINE.md` | Active |
| AI Character Generation | `Backend/docs/PRD-AI-CHARACTER-GENERATION.md` | Active |
| Daily Sora Automation | `docs/PRD_Daily_Sora_Automation.md` | Active |

### Engagement & DMs
| PRD | Location | Status |
|-----|----------|--------|
| Community Inbox | `docs/PRD_COMMUNITY_INBOX.md` | Active |
| DM Automation | `docs/PRD_DM_AUTOMATION_SYSTEM.md` | Active |
| Relationship-First DM | `docs/PRD_Relationship_First_DM_System.md` | Active |
| Auto Engagement | `Backend/docs/PRD_AUTO_ENGAGEMENT.md` | Active |

### Analytics & Growth
| PRD | Location | Status |
|-----|----------|--------|
| Analytics Dashboard | `docs/PRD_ANALYTICS_DASHBOARD.md` | Active |
| Twitter Feedback Loop | `Backend/docs/PRD_TWITTER_FEEDBACK_LOOP_AGENT.md` | Active |
| Growth Data Plane | `docs/PRD_GROWTH_DATA_PLANE.md` | Active |
| Meta Pixel Tracking | `docs/PRD_META_PIXEL_TRACKING.md` | Active |
| Event Tracking | `docs/PRD_EVENT_TRACKING.md` | Active |
| Gap Analysis 2026 | `docs/PRD_GAP_ANALYSIS_2026.md` | Active |

### Testing & Quality
| PRD | Location | Status |
|-----|----------|--------|
| E2E Testing Framework | `docs/PRD_E2E_TESTING_DEBUG_FRAMEWORK.md` | Active |
| Test Coverage | `Backend/tests/PRD_TEST_COVERAGE.md` | Active |
| Benchmark Gap Analysis | `Backend/tests/PRD_BENCHMARK_GAP_ANALYSIS.md` | Active |

---

## Feature Count

**538 features** across 10 phases:
1. Core Infrastructure & Auth
2. Content Management
3. Multi-Platform Publishing
4. Safari Automation (Sora)
5. Video Production Pipeline
6. Community Engagement
7. Analytics & Reporting
8. Sleep/Wake Mode
9. Growth & Tracking
10. Testing & Quality

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Posts published/day | 50+ |
| Platform accounts managed | 22+ |
| Content generation time | <5 min per post |
| Publish success rate | >95% |
| Sleep mode CPU reduction | >80% |
| Tweet engagement rate | >2% |
| Offer traffic attribution | >60% tracked |

---

## Development Priority

1. **P0:** System Architecture Integration (ARCH-001 to ARCH-008)
2. **P0:** Master Orchestrator wiring all subsystems
3. **P1:** Community Inbox + AI replies
4. **P1:** Content Repurposing Engine
5. **P2:** Advanced analytics + feedback loops
6. **P2:** Growth Data Plane integration

---

## Important Rules

1. **Never use `supabase db reset`** — destroys AI analysis data
2. **Never skip any process step** — must fail with error, not silently skip
3. **Always use real OpenAI API calls** — no mocks for AI features
4. **Reference media files, don't duplicate** — use `source_uri`
