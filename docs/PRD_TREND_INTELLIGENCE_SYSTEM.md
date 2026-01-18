# Trend Intelligence System - Product Requirements Document

**Version:** 1.0  
**Date:** December 29, 2025  
**Status:** MVP Development

---

## Overview

A complete trend-to-content pipeline that turns social media trends into actionable content briefs and rendered videos. The system ingests raw social data, clusters emerging trends, extracts "lingo" and context, generates content briefs, and renders videos via Remotion/Motion Canvas.

---

## System Architecture

### Services

#### A) API Gateway (Next.js API / `/api/v1`)
- Auth, rate limits, workspace/niche configs
- Reads "ready" trends + briefs
- Creates jobs (brief + render)

#### B) Trend Pipeline Workers (background jobs)
- Ingest → Normalize → Embed → Cluster → Score → Lingo/Context → Store

#### C) Render Service
- Remotion service on `:8686` (or Motion Canvas service)
- Accepts a `render_job` with `format_template_id` + `brief_id`
- Returns `video_url` + metadata

#### D) Storage
- **Postgres** (Supabase) for structured data
- **Object storage** (R2/S3/Supabase Storage) for assets + final renders
- **Redis** for queues + caching

---

## Database Schema (v1)

### 1) `workspaces`
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| name | text | Workspace name |
| plan | text | Subscription plan |
| created_at | timestamp | Creation time |

### 2) `workspace_sources`
Stores "what to track"

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| workspace_id | uuid | FK to workspaces |
| platform | text | tiktok/instagram/youtube/threads |
| niche | text | fitness, saas, etc. |
| seed_accounts | jsonb | Account handles to track |
| seed_keywords | jsonb | Keywords to monitor |
| is_enabled | boolean | Active status |

### 3) `posts_raw`
Raw normalized content (one schema across platforms)

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| workspace_id | uuid | FK to workspaces |
| platform | text | Source platform |
| platform_post_id | text | Original post ID |
| author_handle | text | Creator handle |
| author_followers | integer | Follower count at fetch |
| posted_at | timestamp | Original post time |
| fetched_at | timestamp | When we fetched it |
| caption_text | text | Caption/description |
| hashtags | jsonb | Array of hashtags |
| metrics | jsonb | views/likes/comments/shares/saves |
| audio_ref | jsonb | sound_id, title, creator |
| permalink | text | URL to original |
| language | text | Detected language |
| extra | jsonb | Platform-specific data |

### 4) `post_enrichment`
Optional "heavy" add-ons

| Column | Type | Description |
|--------|------|-------------|
| post_id | uuid | PK/FK to posts_raw |
| top_comments | jsonb | Top comment text |
| transcript | text | Video speech transcript |
| ocr_text | text | On-screen text extracted |
| enriched_at | timestamp | Enrichment time |

### 5) `text_embeddings`
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| workspace_id | uuid | FK to workspaces |
| source_type | text | post/caption/comment/transcript/ocr |
| source_id | uuid | Reference ID |
| embedding | vector | Vector embedding |
| created_at | timestamp | Creation time |

### 6) `trend_clusters`
Each cluster = one emerging "thing"

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| workspace_id | uuid | FK to workspaces |
| cluster_type | text | phrase/topic/sound/format |
| title | text | Cluster label |
| centroid_embedding | vector | Center of cluster |
| created_at | timestamp | Creation time |
| status | text | emerging/peak/declining |

### 7) `cluster_members`
| Column | Type | Description |
|--------|------|-------------|
| cluster_id | uuid | FK to trend_clusters |
| post_id | uuid | FK to posts_raw |
| weight | float | Membership weight |
| added_at | timestamp | Addition time |

### 8) `trend_scores`
Time series scores for velocity/baselines

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| cluster_id | uuid | FK to trend_clusters |
| window | text | 1h/6h/24h/7d |
| mentions | integer | Count in window |
| velocity | float | Rate of change |
| engagement_p50 | float | Median engagement |
| creator_diversity | float | Unique creators ratio |
| score | float | Combined score |
| computed_at | timestamp | Computation time |

### 9) `cluster_lingo`
What people are saying + meaning

| Column | Type | Description |
|--------|------|-------------|
| cluster_id | uuid | PK/FK to trend_clusters |
| key_phrases | jsonb | Rising phrases |
| usage_notes | text | How to use |
| meaning | text | What it means |
| structure | jsonb | setup→pivot→punchline |
| brand_safety_flags | jsonb | Safety concerns |
| updated_at | timestamp | Last update |

### 10) `briefs`
The content-ready pack

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| workspace_id | uuid | FK to workspaces |
| cluster_id | uuid | FK to trend_clusters |
| platform_target | text | tiktok/ig/yt |
| tone | jsonb | based/clean/professional |
| hooks | jsonb | Hook options |
| caption_templates | jsonb | Caption templates |
| angles | jsonb | Content angles |
| shotlist | jsonb | B-roll slots, on-screen text |
| cta | jsonb | Call to action options |
| created_at | timestamp | Creation time |

### 11) `format_templates`
Remotion/Motion Canvas formats

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| name | text | Template name |
| engine | text | remotion/motion_canvas |
| schema | jsonb | Expected inputs |
| default_settings | jsonb | Default render settings |

### 12) `render_jobs`
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| workspace_id | uuid | FK to workspaces |
| brief_id | uuid | FK to briefs |
| format_template_id | uuid | FK to format_templates |
| engine | text | remotion/motion_canvas |
| status | text | queued/running/succeeded/failed |
| input_payload | jsonb | Full input data |
| output | jsonb | video_url, duration, resolution |
| error | text | Error message if failed |
| created_at | timestamp | Creation time |
| finished_at | timestamp | Completion time |

### 13) `webhook_subscriptions`
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| workspace_id | uuid | FK to workspaces |
| event | text | trend.emerging/brief.ready/render.done |
| target_url | text | Webhook URL |
| secret | text | Signing secret |
| is_enabled | boolean | Active status |

---

## Queue Workers

Using BullMQ (Redis) or similar job runner:

| Queue | Purpose |
|-------|---------|
| `q_ingest` | Pull new posts for each workspace_source |
| `q_enrich` | Fetch top comments, transcript, OCR |
| `q_embed` | Create embeddings for caption/comments/transcript |
| `q_cluster` | Incremental clustering (HDBSCAN-ish) |
| `q_score` | Compute velocity vs baseline windows |
| `q_lingo` | Extract phrases + summarize meaning/structure |
| `q_generate_brief` | Turn cluster → briefs |
| `q_render` | Send job to Remotion/Motion Canvas |
| `q_notify` | Fire webhooks + digest emails |

---

## API Endpoints (v1)

### Trends
```
GET  /v1/trends?niche=saas&platform=tiktok&status=emerging&window=24h
GET  /v1/trends/:clusterId
GET  /v1/trends/:clusterId/posts
```

### Briefs
```
POST /v1/briefs
     body: { cluster_id, platform_target, tone, brand_safe_mode, brand_voice_id? }
GET  /v1/briefs/:briefId
```

### Renders
```
POST /v1/renders
     body: { brief_id, format_template_id, overrides? }
GET  /v1/renders/:renderJobId
```

### Webhooks
```
POST   /v1/webhooks
DELETE /v1/webhooks/:id
```

### Formats
```
GET /v1/formats
GET /v1/formats/:id
```

---

## One-Click Flow

### `POST /v1/oneclick/render_from_trend`

**Request:**
```json
{
  "cluster_id": "tr_8f2a",
  "platform_target": "tiktok",
  "tone": "based_clean",
  "brand_safe_mode": true,
  "format_template_id": "fmt_explainer_v1",
  "overrides": {
    "duration_sec": 22,
    "aspect": "9:16",
    "cta_text": "comment TECH for the template"
  }
}
```

**Response:**
```json
{
  "brief_id": "br_1029",
  "render_job_id": "rj_55aa",
  "status": "queued"
}
```

---

## Remotion Service Contract

### `POST http://localhost:8686/render`

**Payload:**
```json
{
  "render_job_id": "rj_55aa",
  "format_template": {
    "id": "fmt_explainer_v1",
    "engine": "remotion"
  },
  "inputs": {
    "title": "Stop building before validating",
    "bullets": [
      "Run 5 pages at once",
      "Track attribution properly",
      "Rank by intent, not vibes"
    ],
    "on_screen_text": ["WAITLIST LAB", "VALIDATE FIRST"],
    "voiceover_script": "...",
    "broll": [
      {"type": "stock_video", "query": "typing laptop night"},
      {"type": "icon", "name": "chart_up"}
    ],
    "music": {"ref": "lofi_01", "ducking": true},
    "settings": {"duration_sec": 22, "fps": 30, "resolution": "1080x1920"}
  },
  "callback_url": "http://localhost:5555/api/v1/renders/callback"
}
```

**Callback Response:**
```json
{
  "render_job_id": "rj_55aa",
  "status": "succeeded",
  "video_url": "https://storage/.../rj_55aa.mp4",
  "metadata": {"duration_sec": 22, "fps": 30, "size_bytes": 48200321}
}
```

---

## Advanced Query Library

### 1) Niche Radar Queries

#### A) Top 50 Hashtags in Niche (daily)
- **Input:** seed keywords
- **Output:** top hashtags + trend_score + saturation + examples

#### B) Rising Topics (not just hashtags)
- **Output:** "Top 10 angles emerging" with hook patterns

#### C) Explore-Section Drift
- **Output:** "What the algorithm is favoring today"

### 2) Creator Discovery Queries

#### D) Creator Leaderboard by Niche
- **Output:** "Top 25 creators to study" + winning formats

#### E) Creators Like Me (lookalike)
- **Output:** similar creators + differentiators

#### F) Collab Opportunity Finder
- **Output:** "10 collabs that make sense" + concepts

### 3) Content Brief Queries

#### G) Trend → Content Brief Generator
- **Output:** hooks, script outline, format rec, must-include phrases, differentiation twist

#### H) Hook Leaderboard
- **Output:** top hook templates with examples

#### I) Carousel Blueprint Extractor
- **Output:** 5 reusable carousel structures

### 4) Audio + Format Queries

#### J) Rising Audio Tracker
- **Output:** top audios + best content type for each

#### K) Format Shift Detector
- **Output:** "Format trend: shift to X" + proof posts

### 5) Timing Queries

#### L) Best Posting Windows
- **Output:** recommended windows + confidence

#### M) Content Half-Life
- **Output:** when to repost + remix timing

### 6) Competitive Gap Queries

#### N) Content Gap Finder
- **Output:** "Top 10 gaps" with angles

#### O) Overserved vs Underserved Tags
- **Output:** small tags that overperform

### 7) Experiment Queries

#### P) Experiment Backlog Generator
- **Output:** 2-week experiment plan

#### Q) Post-Mortem Explainer
- **Output:** "3 reasons it worked / 3 fixes"

---

## MVP Build Order

1. **Unify schema** (posts_raw, workspace_sources)
2. **Ingest + scoring** (simple clustering first)
3. **Lingo/context extraction** → cluster_lingo
4. **Brief generator** → briefs
5. **Format templates** + render_jobs
6. **Remotion endpoint** + callback + storage upload
7. **Webhooks** + daily digest

---

## Implementation Phases

### Phase 1: Database Foundation
- Create all core tables
- Set up migrations
- Add indexes for performance

### Phase 2: Trend Pipeline
- Ingest workers
- Embedding generation
- Clustering logic
- Scoring system

### Phase 3: Brief Generation
- Lingo extraction
- Brief templates
- API endpoints

### Phase 4: Render Integration
- Format templates
- Remotion contract
- Job queue

### Phase 5: One-Click Flow
- Convenience endpoint
- Webhooks
- Dashboard integration

---

## Notes

- All scraper APIs (RapidAPI, etc.) should be server-side only
- Never expose API keys in client code
- Prefer official Graph APIs for production scale
- Scrapers are great for prototyping, risky for dependable production
