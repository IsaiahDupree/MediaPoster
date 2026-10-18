# MediaPoster Master Work Breakdown PRD

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Active Planning  
**Estimated Total Remaining:** 22-28 weeks

---

## Executive Summary

This document consolidates all remaining work across MediaPoster PRDs into a prioritized, actionable breakdown. Work is organized into **6 tracks** that can be executed in parallel.

---

## Track Overview

| Track | Name | Effort | Priority | Owner |
|-------|------|--------|----------|-------|
| **T1** | Video Intelligence | 6-8 weeks | 🔴 Critical | - |
| **T2** | Community & Engagement | 5-6 weeks | 🔴 Critical | - |
| **T3** | Content Repurposing | 4-6 weeks | 🟡 High | - |
| **T4** | Sales & DM Automation | 4-5 weeks | 🟡 High | - |
| **T5** | Advertising & Revenue | 8-10 weeks | 🟢 Medium | - |
| **T6** | Platform Integrations | 3-4 weeks | 🟢 Medium | - |

---

## Track 1: Video Intelligence (6-8 weeks)

### T1.1 Sora Video Orchestrator Completion
**PRD:** `PRD_SORA_VIDEO_ORCHESTRATOR.md`  
**Current:** 40% → **Target:** 100%  
**Effort:** 3-4 weeks

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T1.1.1 Database schema migration | ❌ | 2d | None |
| T1.1.2 Core models (SQLAlchemy + Pydantic) | ❌ | 2d | T1.1.1 |
| T1.1.3 Multi-provider fallback (Runway, Kling) | ❌ | 1w | T1.1.2 |
| T1.1.4 Director Service (Script → ClipPlan) | ❌ | 3d | T1.1.2 |
| T1.1.5 Scene Crafter (prompt baking) | ❌ | 2d | T1.1.4 |
| T1.1.6 Assessor Service (quality checks) | ❌ | 3d | T1.1.3 |
| T1.1.7 Repair Loop (retry strategies) | ❌ | 2d | T1.1.6 |
| T1.1.8 Timeline Assembler (FFmpeg/MoviePy) | ❌ | 3d | T1.1.6 |
| T1.1.9 Storyboard UI | ❌ | 4d | T1.1.4 |
| T1.1.10 Character/style bibles | ❌ | 2d | T1.1.5 |

**Files to Create:**
```
Backend/services/video_orchestrator/
├── director_service.py
├── scene_crafter.py
├── assessor_service.py
├── timeline_assembler.py
├── providers/
│   ├── sora_provider.py (exists, enhance)
│   ├── runway_provider.py
│   └── kling_provider.py
└── models.py

dashboard/app/(dashboard)/video-studio/
├── page.tsx
├── storyboard/page.tsx
└── components/
    ├── SceneEditor.tsx
    ├── TimelineView.tsx
    └── ProviderSelector.tsx
```

### T1.2 Whisper Integration
**PRD:** Part of Content Analyzer  
**Current:** Ready → **Target:** Integrated  
**Effort:** 1 week

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T1.2.1 Video upload endpoint | ❌ | 1d | None |
| T1.2.2 FFmpeg audio extraction | ❌ | 1d | T1.2.1 |
| T1.2.3 Whisper API integration | ⚠️ Ready | 1d | T1.2.2 |
| T1.2.4 Store transcript in DB | ❌ | 1d | T1.2.3 |
| T1.2.5 Feed to content analyzer | ❌ | 1d | T1.2.4 |
| T1.2.6 Speaker diarization | ❌ | 2d | T1.2.5 |

### T1.3 Video Analytics Enhancement
**Current:** 60% → **Target:** 100%  
**Effort:** 1-2 weeks

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T1.3.1 AI emotional peak detection | ❌ | 2d | T1.2 |
| T1.3.2 Hook scoring algorithm | ⚠️ 50% | 2d | T1.2 |
| T1.3.3 Virality prediction model | ❌ | 3d | T1.3.1, T1.3.2 |
| T1.3.4 Highlight auto-extraction | ❌ | 2d | T1.3.1 |

---

## Track 2: Community & Engagement (5-6 weeks)

### T2.1 Community Inbox
**PRD:** `PRD_COMMUNITY_INBOX.md`  
**Current:** 70% backend → **Target:** 100%  
**Effort:** 3-4 weeks

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T2.1.1 Platform connectors (IG, TikTok, Twitter, YouTube) | ⚠️ 40% | 1w | Safari Automation |
| T2.1.2 Unified inbox UI | ❌ | 4d | T2.1.1 |
| T2.1.3 Conversation threading | ❌ | 2d | T2.1.2 |
| T2.1.4 AI reply suggestions (OpenAI) | ❌ | 2d | T2.1.2 |
| T2.1.5 Real-time sentiment analysis | ❌ | 2d | T2.1.4 |
| T2.1.6 Engagement scoring | ❌ | 1d | T2.1.5 |
| T2.1.7 Saved replies library | ❌ | 2d | T2.1.2 |
| T2.1.8 Comment → Content pipeline | ❌ | 2d | T2.1.7 |
| T2.1.9 Automation rules engine | ❌ | 3d | T2.1.8 |

**API Endpoints (17):**
```
GET    /api/inbox/messages
GET    /api/inbox/messages/{id}
GET    /api/inbox/messages/unread/count
PUT    /api/inbox/messages/{id}/status
PUT    /api/inbox/messages/{id}/assign
POST   /api/inbox/messages/{id}/tags
POST   /api/inbox/messages/{id}/reply
GET    /api/inbox/messages/{id}/ai-suggestions
POST   /api/inbox/messages/{id}/ai-generate
GET    /api/inbox/saved-replies
POST   /api/inbox/saved-replies
PUT    /api/inbox/saved-replies/{id}
DELETE /api/inbox/saved-replies/{id}
POST   /api/inbox/messages/{id}/to-idea
GET    /api/inbox/content-ideas
GET    /api/inbox/automation/rules
POST   /api/inbox/sync/{platform}
```

**Database Tables:**
```sql
inbox_messages
inbox_replies
saved_replies
inbox_content_ideas
inbox_automation_rules
inbox_message_tags
```

### T2.2 Competitor Research Completion
**PRD:** `PRD-Competitor-Research-System.md`  
**Current:** 85% → **Target:** 100%  
**Effort:** 1 week

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T2.2.1 Background sync scheduler | ❌ | 2d | None |
| T2.2.2 Cross-account pattern analysis | ❌ | 2d | T2.2.1 |
| T2.2.3 Auto hook suggestions in composer | ❌ | 1d | T2.2.2 |
| T2.2.4 Posting time recommendations | ❌ | 1d | T2.2.2 |

---

## Track 3: Content Repurposing (4-6 weeks)

### T3.1 Content Repurposing Engine
**PRD:** `PRD_CONTENT_REPURPOSING_ENGINE.md`  
**Current:** 10% → **Target:** 100%  
**Effort:** 4-6 weeks

**Goal:** Build Opus.pro competitor

| Phase | Task | Status | Effort |
|-------|------|--------|--------|
| **Phase 1** | | | **1.5 weeks** |
| | T3.1.1 YouTube URL import | ⚠️ 30% | 2d |
| | T3.1.2 Twitch VOD import | ❌ | 2d |
| | T3.1.3 RSS feed import | ❌ | 1d |
| | T3.1.4 Whisper transcription integration | ⚠️ Ready | 1d |
| | T3.1.5 AI highlight detection | ❌ | 3d |
| | T3.1.6 Hook-first clip ordering | ❌ | 2d |
| **Phase 2** | | | **1.5 weeks** |
| | T3.1.7 Aspect ratio conversion (9:16, 1:1, 16:9, 4:5) | ❌ | 3d |
| | T3.1.8 AI object/face tracking | ❌ | 3d |
| | T3.1.9 B-Roll integration (Pexels/Pixabay) | ❌ | 2d |
| **Phase 3** | | | **1 week** |
| | T3.1.10 AI animated captions | ❌ | 3d |
| | T3.1.11 Caption customization (20+ fonts) | ❌ | 2d |
| | T3.1.12 Brand templates | ❌ | 2d |
| **Phase 4** | | | **1 week** |
| | T3.1.13 Virality prediction (0-100 score) | ❌ | 3d |
| | T3.1.14 Platform optimization (TikTok, Reels, Shorts) | ❌ | 2d |
| | T3.1.15 Export options (ZIP, direct publish, cloud) | ❌ | 2d |

**Database Tables:**
```sql
repurpose_sources
repurpose_transcripts
repurpose_clips
repurpose_renders
```

**Files to Create:**
```
Backend/services/repurposing/
├── source_importer.py
├── highlight_detector.py
├── clip_generator.py
├── aspect_converter.py
├── caption_renderer.py
├── broll_service.py
├── virality_predictor.py
└── export_service.py

dashboard/app/(dashboard)/repurpose/
├── page.tsx
├── [sourceId]/page.tsx
└── components/
    ├── SourceImporter.tsx
    ├── ClipEditor.tsx
    ├── CaptionStyler.tsx
    └── ExportPanel.tsx
```

---

## Track 4: Sales & DM Automation (4-5 weeks)

### T4.1 DM Automation (Revio-style)
**PRD:** `PRD_DM_Automation.md`, `PRD_Relationship_First_DM_System.md`  
**Current:** 5% → **Target:** 100%  
**Effort:** 4-5 weeks

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T4.1.1 Relationship Health Score (0-100, 6 factors) | ❌ | 3d | None |
| T4.1.2 8-stage relationship pipeline | ❌ | 3d | T4.1.1 |
| T4.1.3 Intent Ladder (A/B/C lanes) | ❌ | 2d | T4.1.2 |
| T4.1.4 3:1 Rule enforcement | ❌ | 2d | T4.1.3 |
| T4.1.5 Context Cards (building, struggles, values, wins) | ❌ | 3d | T4.1.2 |
| T4.1.6 AI Next-Best-Action engine | ❌ | 4d | T4.1.5 |
| T4.1.7 Offer timing rules | ❌ | 2d | T4.1.6 |
| T4.1.8 Touch cadences (daily/weekly/monthly) | ⚠️ 50% | 2d | T4.1.7 |
| T4.1.9 Multi-platform DM sending | ⚠️ Safari ready | 3d | Safari Automation |
| T4.1.10 DM analytics dashboard | ❌ | 3d | T4.1.8 |

**Key Differentiator:**
```
Revio: Lead score = "buy soon"
MediaPoster: Relationship health = "who needs care"
```

**Database Tables:**
```sql
dm_contacts (with context cards)
dm_conversations
dm_value_delivered
dm_offers
dm_relationship_scores
dm_touch_history
```

### T4.2 Twitter Automation Completion
**PRD:** `PRD_Twitter_Video_Automation.md`  
**Current:** 70% → **Target:** 100%  
**Effort:** 1 week

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T4.2.1 Multi-account switching | ❌ | 2d | None |
| T4.2.2 Session health monitoring | ❌ | 1d | T4.2.1 |
| T4.2.3 TwitterWorker pub/sub integration | ⚠️ 60% | 2d | T4.2.2 |
| T4.2.4 Advanced rate limit cool-down | ⚠️ 40% | 1d | T4.2.3 |

---

## Track 5: Advertising & Revenue (8-10 weeks)

### T5.1 Meta Ads Programmatic Testing
**PRD:** `PRD_Programmatic_Ad_Testing.md`  
**Current:** 0% → **Target:** 100%  
**Effort:** 8-10 weeks

**Prerequisites:**
| Requirement | Status |
|-------------|--------|
| Meta Business Manager | ❓ Setup needed |
| Facebook App | ❓ Setup needed |
| Marketing API access | ❓ Setup needed |
| Meta Pixel | ❓ Setup needed |

| Phase | Task | Status | Effort |
|-------|------|--------|--------|
| **Setup** | | | **1 week** |
| | T5.1.1 Meta Business Manager setup | ❌ | 2d |
| | T5.1.2 Facebook App creation | ❌ | 1d |
| | T5.1.3 Marketing API access | ❌ | 2d |
| **Phase 1** | | | **2 weeks** |
| | T5.1.4 Transcript extraction (hooks, CTAs, pain points) | ❌ | 3d |
| | T5.1.5 Variation generator (50-100+ variants) | ❌ | 4d |
| | T5.1.6 Batch rendering (Remotion) | ❌ | 3d |
| **Phase 2** | | | **2 weeks** |
| | T5.1.7 Meta Campaign deployment | ❌ | 4d |
| | T5.1.8 Meta Insights tracking | ❌ | 3d |
| | T5.1.9 Performance dashboard | ❌ | 3d |
| **Phase 3** | | | **2 weeks** |
| | T5.1.10 AI Insights engine | ❌ | 4d |
| | T5.1.11 Campaign management (pause, scale, budget) | ❌ | 3d |
| | T5.1.12 Dynamic Creative Optimization | ❌ | 3d |

**Environment Variables:**
```bash
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=
META_AD_ACCOUNT_ID=
META_PIXEL_ID=
META_PAGE_ID=
```

**Files to Create:**
```
Backend/services/meta_ads/
├── client.py
├── campaign_manager.py
├── insights_fetcher.py
├── video_uploader.py
├── variation_generator.py
└── optimizer.py

Backend/api/endpoints/meta_ads.py
Backend/services/workers/meta_ads_worker.py

dashboard/app/(dashboard)/ads/
├── page.tsx
├── campaigns/[id]/page.tsx
├── insights/page.tsx
└── components/
    ├── CampaignBuilder.tsx
    ├── VariationGrid.tsx
    └── InsightsChart.tsx
```

---

## Track 6: Platform Integrations (3-4 weeks)

### T6.1 Instagram Graph API
**PRD:** `PRD_Instagram_TrendTok_Clone.md`  
**Current:** 0% → **Target:** 100%  
**Effort:** 2-3 weeks

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T6.1.1 OAuth flow implementation | ❌ | 3d | None |
| T6.1.2 Graph API adapter | ❌ | 3d | T6.1.1 |
| T6.1.3 Real-time follower activity | ❌ | 2d | T6.1.2 |
| T6.1.4 Official Insights API | ❌ | 3d | T6.1.2 |
| T6.1.5 Owned account data sync | ❌ | 2d | T6.1.4 |

### T6.2 Microservices Enhancement
**Current:** 39 endpoints → **Target:** 50+ endpoints  
**Effort:** 1 week

| Task | Status | Effort | Dependencies |
|------|--------|--------|--------------|
| T6.2.1 Add remaining video endpoints | ⚠️ | 2d | T1 |
| T6.2.2 Add community endpoints | ⚠️ | 2d | T2 |
| T6.2.3 Add DM endpoints | ⚠️ | 1d | T4 |
| T6.2.4 Load balancing setup | ❌ | 1d | All |

---

## Priority Matrix

### 🔴 Immediate (Next 2 Weeks)

| # | Task | Track | Effort | Impact |
|---|------|-------|--------|--------|
| 1 | T1.2 Whisper Integration | T1 | 1w | Enables transcription everywhere |
| 2 | T4.2 Twitter Automation | T4 | 1w | Full publishing automation |
| 3 | T2.2 Competitor Sync | T2 | 1w | Background intelligence |

### 🟡 Short-Term (Weeks 3-6)

| # | Task | Track | Effort | Impact |
|---|------|-------|--------|--------|
| 4 | T2.1 Community Inbox Phase 1 | T2 | 2w | Unified engagement |
| 5 | T1.1 Sora Orchestrator | T1 | 2w | Video production |
| 6 | T4.1 DM Automation Core | T4 | 2w | Sales automation |

### 🟢 Medium-Term (Weeks 7-14)

| # | Task | Track | Effort | Impact |
|---|------|-------|--------|--------|
| 7 | T3.1 Content Repurposing | T3 | 4-6w | Content multiplication |
| 8 | T2.1 Community Inbox Phase 2-3 | T2 | 2w | AI engagement |

### 🔵 Long-Term (Weeks 15-28)

| # | Task | Track | Effort | Impact |
|---|------|-------|--------|--------|
| 9 | T5.1 Meta Ads | T5 | 8w | Revenue generation |
| 10 | T6.1 Instagram Graph API | T6 | 3w | Official API access |

---

## Summary Metrics

| Metric | Value |
|--------|-------|
| **Total Tasks** | 85 |
| **Completed** | ~25 (29%) |
| **In Progress** | ~15 (18%) |
| **Not Started** | ~45 (53%) |
| **Total Estimated Effort** | 22-28 weeks |

---

## Parallel Execution Strategy

```
Week 1-2:   T1.2 ─────────────  T4.2 ─────────────  T2.2 ─────────────
Week 3-4:   T2.1 Phase 1 ───────────────────────── T1.1 (start) ──────
Week 5-6:   T2.1 Phase 2 ───────────────────────── T1.1 (continue) ───
Week 7-10:  T3.1 Phase 1-2 ────────────────────── T4.1 ───────────────
Week 11-14: T3.1 Phase 3-4 ────────────────────── T2.1 Phase 3 ───────
Week 15-22: T5.1 Meta Ads ─────────────────────────────────────────────
Week 23-28: T6.1 Instagram Graph API ─────────── Polish & Testing ────
```

---

## Quick Start: Next Actions

1. **Today:** Start T1.2.1 (Video upload endpoint)
2. **This Week:** Complete Whisper integration
3. **Next Week:** Twitter automation + Competitor sync
4. **Week 3:** Begin Community Inbox UI

---

*Document generated: February 1, 2026*
*Next review: February 8, 2026*
