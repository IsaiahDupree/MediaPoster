# PRD: MediaPoster Architecture Overview

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Living Document  
**Purpose:** Complete system architecture reference

---

## Executive Summary

MediaPoster is a distributed content management and publishing platform consisting of a main backend API, two microservices, four integrated external repos, and connections to multiple external services.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MEDIAPOSTER PLATFORM                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ╔═════════════════════════════════════════════════════════════════════════════════════╗   │
│  ║                              PRESENTATION LAYER                                      ║   │
│  ╠═════════════════════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                                      ║   │
│  ║   ┌──────────────────────────────────────────────────────────────────────────────┐  ║   │
│  ║   │                    Next.js Dashboard (Port 5557)                              │  ║   │
│  ║   │                                                                               │  ║   │
│  ║   │   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │  ║   │
│  ║   │   │  Content    │ │ Automation  │ │  Schedule   │ │    Analytics        │   │  ║   │
│  ║   │   │  Library    │ │   Center    │ │  Calendar   │ │    Dashboard        │   │  ║   │
│  ║   │   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘   │  ║   │
│  ║   │   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │  ║   │
│  ║   │   │ Narrative   │ │ Experiments │ │ Competitor  │ │   Posted Content    │   │  ║   │
│  ║   │   │  Builder    │ │   A/B Test  │ │  Research   │ │    Performance      │   │  ║   │
│  ║   │   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘   │  ║   │
│  ║   │                                                                               │  ║   │
│  ║   │   Tech: Next.js 14, React 18, TailwindCSS, shadcn/ui, Lucide Icons          │  ║   │
│  ║   └──────────────────────────────────────────────────────────────────────────────┘  ║   │
│  ║                                                                                      ║   │
│  ╚══════════════════════════════════════════════════════════════════════════════════════╝   │
│                                           │                                                  │
│                                           ▼                                                  │
│  ╔═════════════════════════════════════════════════════════════════════════════════════╗   │
│  ║                              APPLICATION LAYER                                       ║   │
│  ╠═════════════════════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                                      ║   │
│  ║   ┌──────────────────────────────────────────────────────────────────────────────┐  ║   │
│  ║   │                    FastAPI Backend (Port 5555)                                │  ║   │
│  ║   │                                                                               │  ║   │
│  ║   │   ┌─────────────────────────────────────────────────────────────────────┐    │  ║   │
│  ║   │   │                        API ENDPOINTS                                 │    │  ║   │
│  ║   │   │                                                                      │    │  ║   │
│  ║   │   │  Content:                    Automation:                             │    │  ║   │
│  ║   │   │  • /api/content/*            • /api/automation/*                     │    │  ║   │
│  ║   │   │  • /api/ingest/*             • /api/narrative/*                      │    │  ║   │
│  ║   │   │  • /api/media/*              • /api/experiments/*                    │    │  ║   │
│  ║   │   │                                                                      │    │  ║   │
│  ║   │   │  Publishing:                 Analytics:                              │    │  ║   │
│  ║   │   │  • /api/schedule/*           • /api/analytics/*                      │    │  ║   │
│  ║   │   │  • /api/blotato/*            • /api/performance/*                    │    │  ║   │
│  ║   │   │  • /api/publishing/*         • /api/insights/*                       │    │  ║   │
│  ║   │   │                                                                      │    │  ║   │
│  ║   │   │  DM & CRM:                   Microservice Proxy:                     │    │  ║   │
│  ║   │   │  • /api/dm/*                 • /api/media-pipeline/*                 │    │  ║   │
│  ║   │   │  • /api/crm/*                • /api/content-intelligence/*           │    │  ║   │
│  ║   │   └─────────────────────────────────────────────────────────────────────┘    │  ║   │
│  ║   │                                                                               │  ║   │
│  ║   │   ┌─────────────────────────────────────────────────────────────────────┐    │  ║   │
│  ║   │   │                     CORE SERVICES                                    │    │  ║   │
│  ║   │   │                                                                      │    │  ║   │
│  ║   │   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │    │  ║   │
│  ║   │   │  │   Agent     │ │  Narrative  │ │ Experiments │ │  Analytics  │   │    │  ║   │
│  ║   │   │  │  Framework  │ │  Scheduler  │ │  Scheduler  │ │  Feedback   │   │    │  ║   │
│  ║   │   │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │    │  ║   │
│  ║   │   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │    │  ║   │
│  ║   │   │  │  DM         │ │  Trend      │ │  Daily      │ │  Master     │   │    │  ║   │
│  ║   │   │  │  Outreach   │ │  Flash      │ │  Automation │ │ Orchestrator│   │    │  ║   │
│  ║   │   │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │    │  ║   │
│  ║   │   │                                                                      │    │  ║   │
│  ║   │   └─────────────────────────────────────────────────────────────────────┘    │  ║   │
│  ║   │                                                                               │  ║   │
│  ║   │   Tech: FastAPI, Python 3.11, Pydantic, SQLAlchemy, asyncio                  │  ║   │
│  ║   └──────────────────────────────────────────────────────────────────────────────┘  ║   │
│  ║                                                                                      ║   │
│  ╚══════════════════════════════════════════════════════════════════════════════════════╝   │
│                                           │                                                  │
│                    ┌──────────────────────┴──────────────────────┐                          │
│                    ▼                                             ▼                          │
│  ╔═════════════════════════════════════╗  ╔═════════════════════════════════════╗          │
│  ║       MICROSERVICE: media-pipeline  ║  ║  MICROSERVICE: content-intelligence ║          │
│  ║              Port 6004              ║  ║              Port 6006               ║          │
│  ╠═════════════════════════════════════╣  ╠═════════════════════════════════════╣          │
│  ║                                     ║  ║                                      ║          │
│  ║  19 Endpoints:                      ║  ║  20 Endpoints:                       ║          │
│  ║                                     ║  ║                                      ║          │
│  ║  Analysis:                          ║  ║  Analysis:                           ║          │
│  ║  • /api/analyze                     ║  ║  • /api/score/fate                   ║          │
│  ║  • /api/transcribe                  ║  ║  • /api/classify/awareness           ║          │
│  ║  • /api/audio/analyze               ║  ║  • /api/analyze/sentiment            ║          │
│  ║                                     ║  ║  • /api/vision/analyze               ║          │
│  ║  Processing:                        ║  ║                                      ║          │
│  ║  • /api/thumbnail/generate          ║  ║  Generation:                         ║          │
│  ║  • /api/clip/extract                ║  ║  • /api/generate/title               ║          │
│  ║  • /api/format/detect               ║  ║  • /api/generate/caption             ║          │
│  ║  • /api/deduplicate/check           ║  ║  • /api/brief/generate               ║          │
│  ║                                     ║  ║  • /api/hashtags/generate            ║          │
│  ║  Orchestration:                     ║  ║                                      ║          │
│  ║  • /api/orchestrate/plan            ║  ║  Intelligence:                       ║          │
│  ║  • /api/render/video                ║  ║  • /api/narrative/plan               ║          │
│  ║  • /api/tts/generate                ║  ║  • /api/experiments/hypothesis       ║          │
│  ║  • /api/music/search                ║  ║  • /api/competitor/analyze           ║          │
│  ║  • /api/sfx/search                  ║  ║  • /api/trends/detect                ║          │
│  ║                                     ║  ║  • /api/engagement/predict           ║          │
│  ║  External Integrations:             ║  ║                                      ║          │
│  ║  • /api/tts/indextts2 → TTS repo    ║  ║  External Integrations:              ║          │
│  ║  • /api/remotion/render → Remotion  ║  ║  • /api/crm/* → EverReach CRM        ║          │
│  ║  • /api/remotion/brief              ║  ║  • /api/safari/* → Safari Auto       ║          │
│  ║  • /api/scrape/instagram            ║  ║  • /api/dm/outreach                  ║          │
│  ║  • /api/workers/status              ║  ║  • /api/inbox/auto-reply             ║          │
│  ║  • /api/matting/remove-bg           ║  ║                                      ║          │
│  ║                                     ║  ║                                      ║          │
│  ║  Tech: Flask, Python 3.11           ║  ║  Tech: Flask, Python 3.11            ║          │
│  ╚═════════════════════════════════════╝  ╚═════════════════════════════════════╝          │
│                    │                                             │                          │
│                    └──────────────────────┬──────────────────────┘                          │
│                                           │                                                  │
│                                           ▼                                                  │
│  ╔═════════════════════════════════════════════════════════════════════════════════════╗   │
│  ║                           EXTERNAL REPO INTEGRATIONS                                 ║   │
│  ╠═════════════════════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                                      ║   │
│  ║   ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐    ║   │
│  ║   │        TTS          │  │      Remotion       │  │   Safari Automation     │    ║   │
│  ║   │                     │  │                     │  │                         │    ║   │
│  ║   │  Path: /TTS/        │  │  Path: /Remotion/   │  │  Path: /Safari Auto/    │    ║   │
│  ║   │                     │  │                     │  │                         │    ║   │
│  ║   │  Features:          │  │  Features:          │  │  Features:              │    ║   │
│  ║   │  • IndexTTS2        │  │  • Video render     │  │  • Browser automation   │    ║   │
│  ║   │  • ElevenLabs       │  │  • Brief generation │  │  • Sora video gen       │    ║   │
│  ║   │  • Voice cloning    │  │  • Ad templates     │  │  • Twitter posting      │    ║   │
│  ║   │  • Emotion control  │  │  • Stickers/effects │  │  • Instagram scraping   │    ║   │
│  ║   │                     │  │                     │  │  • DM automation        │    ║   │
│  ║   │  Tech: Python       │  │  Tech: TypeScript   │  │  Tech: TypeScript       │    ║   │
│  ║   └─────────────────────┘  └─────────────────────┘  └─────────────────────────┘    ║   │
│  ║                                                                                      ║   │
│  ║   ┌─────────────────────────────────────────────────────────────────────────────┐   ║   │
│  ║   │                      Local EverReach CRM                                     │   ║   │
│  ║   │                                                                              │   ║   │
│  ║   │  Path: /Local EverReach CRM/                                                 │   ║   │
│  ║   │                                                                              │   ║   │
│  ║   │  Features:                                                                   │   ║   │
│  ║   │  • Lead management            • Relationship scoring                        │   ║   │
│  ║   │  • DM coaching engine         • AI copilot replies                          │   ║   │
│  ║   │  • Pipeline analytics         • Automated outreach                          │   ║   │
│  ║   │                                                                              │   ║   │
│  ║   │  Tech: TypeScript, Supabase                                                  │   ║   │
│  ║   └─────────────────────────────────────────────────────────────────────────────┘   ║   │
│  ║                                                                                      ║   │
│  ╚══════════════════════════════════════════════════════════════════════════════════════╝   │
│                                           │                                                  │
│                                           ▼                                                  │
│  ╔═════════════════════════════════════════════════════════════════════════════════════╗   │
│  ║                                 DATA LAYER                                           ║   │
│  ╠═════════════════════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                                      ║   │
│  ║   ┌─────────────────────────────────┐  ┌─────────────────────────────────────────┐  ║   │
│  ║   │          Supabase               │  │           Local Storage                 │  ║   │
│  ║   │                                 │  │                                         │  ║   │
│  ║   │  • PostgreSQL database          │  │  Path: /Volumes/My Passport/MediaPoster/│  ║   │
│  ║   │  • Auth (JWT)                   │  │                                         │  ║   │
│  ║   │  • Storage (media files)        │  │  • workspace1/iphone_import/ (182 GB)   │  ║   │
│  ║   │  • Realtime subscriptions       │  │  • workspace1/android_import/           │  ║   │
│  ║   │  • Edge Functions               │  │  • rapidapi_media/                      │  ║   │
│  ║   │                                 │  │                                         │  ║   │
│  ║   │  Tables: 50+                    │  │  Files: 11,182+                         │  ║   │
│  ║   └─────────────────────────────────┘  └─────────────────────────────────────────┘  ║   │
│  ║                                                                                      ║   │
│  ╚══════════════════════════════════════════════════════════════════════════════════════╝   │
│                                           │                                                  │
│                                           ▼                                                  │
│  ╔═════════════════════════════════════════════════════════════════════════════════════╗   │
│  ║                              EXTERNAL SERVICES                                       ║   │
│  ╠═════════════════════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                                      ║   │
│  ║   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐ ║   │
│  ║   │   OpenAI     │ │    Groq      │ │  Anthropic   │ │       Blotato API          │ ║   │
│  ║   │              │ │              │ │              │ │                            │ ║   │
│  ║   │  • GPT-4     │ │  • LLaMA 3   │ │  • Claude 3  │ │  • 22 social accounts      │ ║   │
│  ║   │  • GPT-4V    │ │  • Fast inf. │ │  • Sonnet    │ │  • 10 platforms            │ ║   │
│  ║   │  • Whisper   │ │              │ │              │ │  • Instagram, TikTok       │ ║   │
│  ║   │  • DALL-E    │ │              │ │              │ │  • Twitter, YouTube        │ ║   │
│  ║   │              │ │              │ │              │ │  • Threads, Pinterest      │ ║   │
│  ║   └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────────────┘ ║   │
│  ║                                                                                      ║   │
│  ║   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐ ║   │
│  ║   │  RapidAPI    │ │   Pexels     │ │   Pixabay    │ │   Sora (Browser)           │ ║   │
│  ║   │              │ │              │ │              │ │                            │ ║   │
│  ║   │  • Instagram │ │  • Stock     │ │  • Stock     │ │  • sora.chatgpt.com        │ ║   │
│  ║   │    Looter    │ │    video     │ │    video     │ │  • @character feature      │ ║   │
│  ║   │  • TikTok    │ │  • Images    │ │  • Images    │ │  • Safari automation       │ ║   │
│  ║   │    Scraper   │ │              │ │              │ │                            │ ║   │
│  ║   └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────────────┘ ║   │
│  ║                                                                                      ║   │
│  ╚══════════════════════════════════════════════════════════════════════════════════════╝   │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Service Communication

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE COMMUNICATION MAP                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   Dashboard (5557) ◄─── HTTP/REST ───► Backend API (5555)                           │
│                                              │                                       │
│                         ┌───────────────────┼───────────────────┐                   │
│                         ▼                   ▼                   ▼                   │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                     MicroservicesClient (Async HTTP)                         │   │
│   │                                                                              │   │
│   │   class MicroservicesClient:                                                 │   │
│   │       MEDIA_PIPELINE_URL = "http://localhost:6004"                          │   │
│   │       CONTENT_INTEL_URL = "http://localhost:6006"                           │   │
│   │                                                                              │   │
│   │       async def analyze_video(...)      # → media-pipeline                  │   │
│   │       async def score_fate(...)         # → content-intelligence            │   │
│   │       async def generate_thumbnails(...)# → media-pipeline                  │   │
│   │       async def generate_caption(...)   # → content-intelligence            │   │
│   │       ... (31 methods total)                                                 │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                         │                   │                                        │
│                         ▼                   ▼                                        │
│               media-pipeline (6004)   content-intelligence (6006)                   │
│                         │                   │                                        │
│                         │                   │                                        │
│              ┌──────────┴─────┐   ┌────────┴────────┐                              │
│              ▼                ▼   ▼                  ▼                              │
│         TTS repo      Remotion   Safari Auto   EverReach CRM                        │
│        (subprocess)  (subprocess) (subprocess)  (subprocess)                        │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Examples

### 1. Content Upload & Analysis
```
User uploads video
        │
        ▼
Dashboard (5557) ──POST /api/ingest/upload──► Backend (5555)
                                                    │
                                                    ├──► Supabase (store metadata)
                                                    │
                                                    ├──► media-pipeline (6004)
                                                    │         │
                                                    │         ├──► /api/analyze
                                                    │         ├──► /api/transcribe
                                                    │         └──► /api/thumbnail/generate
                                                    │
                                                    └──► content-intelligence (6006)
                                                              │
                                                              ├──► /api/score/fate
                                                              ├──► /api/generate/title
                                                              └──► /api/generate/caption
```

### 2. Scheduled Publishing
```
Scheduler triggers publish
        │
        ▼
Backend (5555) ──checks schedule──► Supabase
        │
        ├──► Blotato API (primary)
        │         │
        │         └──► Instagram, TikTok, YouTube, etc.
        │
        └──► Safari Automation (fallback/browser-only)
                  │
                  └──► Sora, Twitter (when API unavailable)
```

### 3. AI Video Generation
```
User requests video generation
        │
        ▼
Backend (5555) ──► media-pipeline (6004)
                        │
                        ├──► /api/orchestrate/plan (GPT-4)
                        │
                        ├──► Safari Automation
                        │         │
                        │         └──► Sora (sora.chatgpt.com)
                        │
                        └──► /api/render/video
                                  │
                                  └──► Remotion (subprocess)
```

---

## Port Reference

| Service | Port | URL | Protocol |
|---------|------|-----|----------|
| Dashboard | 5557 | http://localhost:5557 | HTTP |
| Backend API | 5555 | http://localhost:5555 | HTTP/REST |
| media-pipeline | 6004 | http://localhost:6004 | HTTP/REST |
| content-intelligence | 6006 | http://localhost:6006 | HTTP/REST |
| Supabase | 443 | https://xxx.supabase.co | HTTPS |

---

## Directory Structure

```
~/Documents/Software/
├── MediaPoster/                    # Main repository
│   ├── Backend/                    # FastAPI backend
│   │   ├── api/endpoints/          # API routes
│   │   ├── services/               # Business logic
│   │   ├── models/                 # Data models
│   │   └── main.py                 # Entry point (port 5555)
│   ├── dashboard/                  # Next.js frontend
│   │   ├── app/                    # App router pages
│   │   ├── components/             # React components
│   │   └── lib/                    # Utilities
│   ├── docs/                       # Documentation (52 PRDs)
│   ├── scripts/                    # Utility scripts
│   └── supabase/                   # Database migrations
│
├── media-pipeline/                 # Microservice 1
│   ├── app.py                      # Flask app (port 6004)
│   ├── services/                   # Processing services
│   │   ├── analysis/
│   │   ├── transcription/
│   │   ├── thumbnail/
│   │   ├── video_orchestrator/
│   │   ├── scrapers/
│   │   └── workers/
│   └── tests/
│
├── content-intelligence/           # Microservice 2
│   ├── app.py                      # Flask app (port 6006)
│   ├── services/                   # AI services
│   │   ├── fate_scorer/
│   │   ├── awareness_classifier/
│   │   ├── sentiment/
│   │   ├── narrative/
│   │   ├── competitor_audit/
│   │   ├── dm_outreach/
│   │   └── inbox/
│   └── tests/
│
├── TTS/                            # Voice synthesis repo
│   ├── call_indextts2_api.py
│   └── clone_voice_elevenlabs.py
│
├── Remotion/                       # Video rendering repo
│   ├── src/
│   └── scripts/
│
├── Safari Automation/              # Browser automation repo
│   ├── apps/runner/
│   └── packages/
│
└── Local EverReach CRM/            # Lead management repo
    ├── packages/crm-core/
    └── packages/instagram-dm/
```

---

## Environment Variables

```bash
# ═══════════════════════════════════════════════════════════════
# SUPABASE
# ═══════════════════════════════════════════════════════════════
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# ═══════════════════════════════════════════════════════════════
# AI PROVIDERS
# ═══════════════════════════════════════════════════════════════
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...

# ═══════════════════════════════════════════════════════════════
# SOCIAL PUBLISHING
# ═══════════════════════════════════════════════════════════════
BLOTATO_API_KEY=...

# ═══════════════════════════════════════════════════════════════
# EXTERNAL APIS
# ═══════════════════════════════════════════════════════════════
RAPIDAPI_KEY=...
PEXELS_API_KEY=...
PIXABAY_API_KEY=...
ELEVENLABS_API_KEY=...
HF_TOKEN=...

# ═══════════════════════════════════════════════════════════════
# SERVICES
# ═══════════════════════════════════════════════════════════════
BACKEND_PORT=5555
DASHBOARD_PORT=5557
MEDIA_PIPELINE_PORT=6004
CONTENT_INTELLIGENCE_PORT=6006
```

---

## Quick Start

```bash
# 1. Start all services
cd ~/Documents/Software/MediaPoster
./scripts/start_microservices.sh

# 2. Or start individually:

# Backend API
cd Backend && python main.py

# Dashboard
cd dashboard && npm run dev

# Microservices
cd ~/Documents/Software/media-pipeline && ./start.sh
cd ~/Documents/Software/content-intelligence && ./start.sh

# 3. Verify all services
curl http://localhost:5555/health
curl http://localhost:6004/health
curl http://localhost:6006/health
```

---

## GitHub Repositories

| Repository | URL | Status |
|------------|-----|--------|
| MediaPoster | https://github.com/IsaiahDupree/MediaPoster | ✅ Active |
| media-pipeline | https://github.com/IsaiahDupree/media-pipeline | ✅ Active |
| content-intelligence | https://github.com/IsaiahDupree/content-intelligence | ✅ Active |

---

*Document created: February 1, 2026*
*Last updated: February 1, 2026*
