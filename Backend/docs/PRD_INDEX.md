# MediaPoster PRD Index

**Complete list of Product Requirement Documents and feature specifications**  
**Last Updated:** 2026-01-19

---

## 0. NEW PRDs - Gap Analysis 2026

### 0.1 Feature PRDs (January 2026)

| PRD | Location | Description | Effort |
|-----|----------|-------------|--------|
| **Link-in-Bio / Start Page** | `docs/PRD_LINK_IN_BIO.md` | Custom landing page builder with click analytics (Buffer/Later competitor) | 2 weeks |
| **Community Inbox** | `docs/PRD_COMMUNITY_INBOX.md` | Unified comments/DMs with AI reply suggestions | 3 weeks |
| **Content Repurposing Engine** | `docs/PRD_CONTENT_REPURPOSING_ENGINE.md` | Long video → shorts with AI clipping (Opus competitor) | 4-6 weeks |
| **Modal Voice Cloning** | `docs/PRD_MODAL_VOICE_CLONING.md` | AI voice cloning via Modal GPU, integrates with ai-video-platform repo | 1-2 weeks |
| **Media Asset Discovery** | `docs/PRD_MEDIA_ASSET_DISCOVERY.md` | Unified search for GIFs, videos, images (Giphy, Pexels, Unsplash, etc.) | 2-3 weeks |
| **E2E Testing & Debug Framework** | `docs/PRD_E2E_TESTING_DEBUG_FRAMEWORK.md` | Playwright E2E tests with structured console logging for debugging | 2 weeks |
| **Safari Session Manager** | `docs/PRD_SAFARI_SESSION_MANAGER.md` | Session keep-alive, health dashboard, multi-account support, analytics | 1-2 weeks |
| **System Benchmarks** | `docs/PRD_SYSTEM_BENCHMARKS.md` | Critical workflows: Ingestion→Export, Sora→Twitter, DM Sync, DevVlog→Shorts | 3-4 weeks |
| **Frontend Consistency** | `docs/PRD_FRONTEND_CONSISTENCY.md` | UI/UX audit, design system, component library, styling standards | 2-3 weeks |
| **YouTube Playlist Automation** | `docs/PRD_YOUTUBE_PLAYLIST_AUTOMATION.md` | YouTube playlist → transcript → AI analysis → Medium/social distribution | Active (Make.com) |

### 0.2 Gap Analysis & Roadmap

| Document | Location | Description |
|----------|----------|-------------|
| **Gap Analysis 2026** | `docs/PRD_GAP_ANALYSIS_2026.md` | Comprehensive competitor gap analysis, feature roadmap, Q1-Q4 2026 plan |
| **Code Improvements Roadmap** | `docs/CODE_IMPROVEMENTS_ROADMAP.md` | Technical debt, Supabase fix, Redis caching, error handling |

---

## 1. Core Content Ops PRDs (NEW)

| PRD | Location | Description |
|-----|----------|-------------|
| **Content Ops Controller** | `Backend/docs/PRD_CONTENT_OPS_CONTROLLER.md` | AI feedback loop agent: FATE stack, 5 Awareness Levels, scoring, template allocation |
| **Content Ops Technical** | `Backend/docs/PRD_CONTENT_OPS_TECHNICAL.md` | API endpoints, event bus, worker contracts, TypeScript interfaces |
| **Content Ops Tests** | `Backend/docs/PRD_CONTENT_OPS_TESTS.md` | Test specification: unit, integration, E2E, safety tests |

---

## 2. All PRDs by Category

### 2.1 Content Generation & AI

| PRD | Location |
|-----|----------|
| AI-Assisted Curation | `docs/PRD_AI_ASSISTED_CURATION.md` |
| AI Narrative Scheduling | `docs/AI_NARRATIVE_SCHEDULING_PRD.md` |
| AI Character Generation | `Backend/docs/PRD-AI-CHARACTER-GENERATION.md` |
| Automated Content Pipeline | `docs/PRD_AUTOMATED_CONTENT_PIPELINE.md` |
| Twitter Feedback Loop Agent | `Backend/docs/PRD_TWITTER_FEEDBACK_LOOP_AGENT.md` |

### 2.2 Video & Media Processing

| PRD | Location |
|-----|----------|
| Sora Video Generation | `Backend/docs/PRD-SORA-VIDEO-GENERATION.md` |
| Sora Video Orchestrator | `docs/PRD_SORA_VIDEO_ORCHESTRATOR.md` |
| Sora Browser Automation | `docs/SORA_BROWSER_AUTOMATION_PRD.md` |
| Sora Characters & Styles | `docs/SORA_CHARACTERS_STYLES_PRD.md` |
| Sora Watermark Remover (Railway) | `Backend/docs/PRD_SORA_WATERMARK_REMOVER_RAILWAY.md` |
| SFX Audio Pipeline | `Backend/docs/PRD-SFX-AUDIO-PIPELINE.md` |
| Video Orientation YouTube Routing | `docs/PRD_VIDEO_ORIENTATION_YOUTUBE_ROUTING.md` |
| Background Music Detection | `docs/BACKGROUND_MUSIC_DETECTION_PRD.md` |
| Auto Music Matching | `docs/AUTO_MUSIC_MATCHING_PRD.md` |
| Media Factory | `Backend/docs/MEDIA_FACTORY_PRD.md` |

### 2.3 Trends & Discovery

| PRD | Location |
|-----|----------|
| Trend Discovery | `docs/PRD_TrendDiscovery.md` |
| Enhanced Trends Discovery | `docs/PRD-Enhanced-Trends-Discovery.md` |
| Trend Intelligence System | `docs/PRD_TREND_INTELLIGENCE_SYSTEM.md` |
| Trending Keywords Video Analysis | `docs/PRD-Trending-Keywords-Video-Analysis.md` |
| Instagram TrendTok Clone | `docs/PRD_Instagram_TrendTok_Clone.md` |
| ReelTrends Instagram Tools | `Backend/services/trend_intelligence/PRD_reeltrends_instagram_tools.md` |
| Multi-Platform Trends | `Backend/services/trend_intelligence/PRD_multi_platform_trends.md` |

### 2.4 Competitor Research

| PRD | Location |
|-----|----------|
| Competitor Research System | `docs/PRD-Competitor-Research-System.md` |

### 2.5 Scheduling & Publishing

| PRD | Location |
|-----|----------|
| Schedule Page Enhancements | `docs/PRD-Schedule-Page-Enhancements.md` |
| Experiments Scheduler | `docs/EXPERIMENTS_SCHEDULER_PRD.md` |
| Story Posting | `docs/STORY_POSTING_PRD.md` |
| Everreach Content Calendar | `Backend/services/everreach/PRD_everreach_content_calendar.md` |

### 2.6 Architecture & Infrastructure

| PRD | Location |
|-----|----------|
| Event-Driven Architecture | `docs/EVENT_DRIVEN_ARCHITECTURE_PRD.md` |
| Background Jobs Migration | `docs/PRD_BACKGROUND_JOBS_MIGRATION.md` |
| Automation Center | `docs/AUTOMATION_CENTER_PRD.md` |
| Advanced Queries | `docs/PRD_AdvancedQueries.md` |
| Expandable Content Stats | `docs/PRD_EXPANDABLE_CONTENT_STATS.md` |

### 2.7 Competitive Audits (Reference)

| PRD | Location |
|-----|----------|
| Buffer PRD | `BUFFER_PRD.md` |
| Later PRD | `LATER_PRD.md` |
| Planoly PRD | `PLANOLY_PRD.md` |
| Opus Clip Schedule PRD | `OPUS_CLIP_SCHEDULE_PRD.md` |
| Stelle PRD | `STELLE_PRD.md` |

### 2.8 Testing & Coverage

| PRD | Location |
|-----|----------|
| PRD Test Coverage | `Backend/tests/PRD_TEST_COVERAGE.md` |
| PRD Implementation Assessment | `docs/PRD_IMPLEMENTATION_ASSESSMENT.md` |
| PRD Coverage Assessment | `docs/PRD_COVERAGE_ASSESSMENT.md` |
| PRD Systematic Test Report | `PRD_SYSTEMATIC_TEST_REPORT.md` |
| Comprehensive PRD Test Report | `COMPREHENSIVE_PRD_TEST_REPORT.md` |

---

## 3. Features from new_social_posts_feedbackloop.txt

### 3.1 Persuasion Frameworks

| Feature | Description |
|---------|-------------|
| **FATE Stack** | Focus, Authority, Tribe, Emotion (Chase Hughes, SRS #253) |
| **5 Awareness Levels** | Unaware → Problem → Solution → Product → Most-Aware (Eugene Schwartz) |

### 3.2 Core Feedback Loop System

| Feature | Description |
|---------|-------------|
| **Prompt Traceback** | Every post traces to template_id → prompt_run_id → offer_id → icp_id |
| **Metrics Snapshots** | Pull at 1h, 6h, 24h, 72h, 7d intervals |
| **Rate-Based Scoring** | like_rate, reply_rate, repost_rate, click_rate (vs impressions) |
| **Z-Score Normalization** | Rolling z-score vs last N posts |
| **Template Leaderboard** | Track avg_score, early_velocity, stability per template |
| **Bandit Allocation** | 70% exploit, 20% explore, 10% experiment |
| **Template Forking** | Winners forked (tpl_09a, tpl_09b), never overwritten |

### 3.3 Data Model Entities

| Entity | Key Fields |
|--------|------------|
| **CreatorProfile** | voice_rules, banned_phrases, tone_descriptors |
| **Brand** | positioning, allowed/disallowed_topics, offers[] |
| **Offer** | promise, landing_url, primary_cta, for_who, not_for, icps[] |
| **ICP** | pains, desired_outcomes, objections, language_to_use/avoid |
| **Template** | awareness_level, fate_weights, format, intent, cta_strength, prompt_text |
| **Slot** | scheduled_time, awareness, fate_target, target_offers/icps |
| **PromptRun** | template_id, inputs, model_info, generated_text |
| **Post** | post_id, post_url, prompt_run_id, shortlink_id |
| **MetricsSnapshot** | metrics JSON at each interval |
| **Score** | score_6h, score_24h, score_7d, labels, blame_notes |
| **Touchpoint** | Unified model for post/comment/dm/email |

### 3.4 25 AI Templates (Awareness × FATE)

| Awareness Level | Count | Examples |
|-----------------|-------|----------|
| **Problem-Aware** | 8 | Symptom mirror, Cost of inaction, Mistake story, Myth bust, Identity callout |
| **Solution-Aware** | 7 | 3 approaches comparison, Framework steps, Decision tree, Tool stack, Case study |
| **Product-Aware** | 6 | Why we built it, Feature→outcome, Objection handling, Before/after, Walkthrough |
| **Most-Aware** | 4 | Offer reminder, Bonus/deadline, Risk reversal, Exactly what you get |

### 3.5 Scoring Modes

| Mode | Primary Weights |
|------|-----------------|
| **Followers** | reply_rate 1.0, repost_rate 0.8, profile_clicks 0.6, likes 0.4 |
| **Leads** | click_rate 1.0, reply_rate 0.7, profile_clicks 0.5, reposts 0.4 |
| **Purchases** | conversion_rate 1.0, click_rate 0.7, reply_rate 0.3 |

### 3.6 Multi-Channel Extensions

| Channel | Goal | Key Signals |
|---------|------|-------------|
| **Posts** | Build awareness + trust at scale | Impressions, replies, clicks |
| **Comments** | Public helpfulness → DM routing | Reply rate, profile clicks, DM initiated |
| **DMs** | Qualify + convert relationships | Reply depth, progression, booking rate |
| **Email** | Nurture + sell over time | Opens, clicks, replies, conversions |

### 3.7 DM Conversation Loop

| Feature | Description |
|---------|-------------|
| **Trigger Types** | Inbound DM, keyword DM ("RADAR"), comment-to-DM |
| **Classification** | Intent stage, topic, sentiment, safety flags |
| **1-Step-Forward** | Ask single qualifying question OR deliver promised asset |
| **Permission Gate** | Links only after consent or asset delivery |
| **DM Scoring** | +1 reply, +2 qualify answer, +3 link click, +5 email, +8 booking, +10 purchase |

### 3.8 Comment Loop

| Feature | Description |
|---------|-------------|
| **Triggers** | Your posts, mentions, competitor posts |
| **Classification** | Question, objection, hate, curiosity + awareness stage |
| **Response Rules** | 1-3 lines max, high signal, route to DM |
| **Keyword CTAs** | "Comment 'RADAR' and I'll DM you the template" |

### 3.9 Email/Newsletter Loop

| Feature | Description |
|---------|-------------|
| **Capture Sources** | DM, link in bio, lead magnet, site |
| **Segmentation** | By offer, ICP, awareness stage, engagement |
| **Sequence Types** | Welcome, nurture, conversion, behavior-based |
| **Signals** | Open rate, click rate, reply rate, conversions |

### 3.10 Autonomous Operations

| Frequency | Jobs |
|-----------|------|
| **Real-time** | Inbound listener, Responder, Attribution logger |
| **Daily (2-6x)** | Slot executor, Early performance check, Same-day adjustments |
| **Weekly** | Planner, Template evolution, Forks + retirements |

### 3.11 Safety Guardrails

| Guardrail | Rule |
|-----------|------|
| **DM Permission Gate** | Links only after consent or asset delivery |
| **User Cooldown** | Max DM/day per user |
| **Offer Fatigue** | Max direct CTA/day per offer |
| **Spam Heuristics** | Blocklist phrases + pattern detection |
| **Human Review Queue** | Route uncertain content for approval |

### 3.12 Interchangeable Offers (4 brands defined)

| Brand | Offer | ICP |
|-------|-------|-----|
| **EverReach** | Free Trial (personal CRM) | Indie founders/operators |
| **MatrixLoop.app** | Waitlist (Meta analytics) | Creators on Meta platforms |
| **KeywordRadar.app** | Subscription (demand radar) | Indie founders validating products |
| **BlankLogo** | Credits (watermark removal) | Editors/UGC agencies |

### 3.13 Technical Stack (Recommended)

| Component | Tool |
|-----------|------|
| Database | Postgres (Supabase) |
| Analytics | PostHog |
| Shortlinks | Custom redirect service |
| Orchestrator | n8n |
| Gen | OpenAI API |
| Dashboard | Next.js admin |

---

## 4. Quick Reference: PRD Locations

```
MediaPoster/
├── Backend/docs/
│   ├── PRD_CONTENT_OPS_CONTROLLER.md     ← NEW: Main Content Ops PRD
│   ├── PRD_CONTENT_OPS_TECHNICAL.md      ← NEW: API/Events/Workers
│   ├── PRD_CONTENT_OPS_TESTS.md          ← NEW: Test specification
│   ├── PRD_TWITTER_FEEDBACK_LOOP_AGENT.md
│   ├── PRD-SORA-VIDEO-GENERATION.md
│   ├── PRD-SFX-AUDIO-PIPELINE.md
│   ├── PRD-AI-CHARACTER-GENERATION.md
│   ├── MEDIA_FACTORY_PRD.md
│   └── PRD_SORA_WATERMARK_REMOVER_RAILWAY.md
│
├── docs/
│   ├── PRD_TrendDiscovery.md
│   ├── PRD_TREND_INTELLIGENCE_SYSTEM.md
│   ├── PRD_AUTOMATED_CONTENT_PIPELINE.md
│   ├── PRD_AI_ASSISTED_CURATION.md
│   ├── EVENT_DRIVEN_ARCHITECTURE_PRD.md
│   ├── SORA_BROWSER_AUTOMATION_PRD.md
│   └── ... (25+ more)
│
└── (root)
    ├── BUFFER_PRD.md
    ├── LATER_PRD.md
    ├── PLANOLY_PRD.md
    ├── OPUS_CLIP_SCHEDULE_PRD.md
    └── STELLE_PRD.md
```

---

## 5. Implementation Priority

### Tier 1: Core Loop (Build First)
1. Template library (25 templates)
2. Content plan generator (slots)
3. AI generation + attribution IDs
4. Post publishing + shortlinks
5. Metrics snapshots
6. Scoring + leaderboard
7. Traceback UI

### Tier 2: Multi-Channel
1. Comment listener + reply templates
2. DM listener + qualification flow
3. Email capture + sequences
4. Cross-platform adapters

### Tier 3: Autonomy
1. n8n orchestration workflows
2. Bandit allocation automation
3. Template evolution (auto-fork)
4. Human approval queue integration
