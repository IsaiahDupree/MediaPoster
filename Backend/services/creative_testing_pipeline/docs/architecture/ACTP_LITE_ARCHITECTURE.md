# ACTP Lite Architecture — Distributed Service Mesh

## Overview

ACTP (Ad Creative Testing Pipeline) is an automated loop that generates video ads, tests them organically, identifies winners, deploys micro-budget paid ads, and iterates. Today it runs entirely as a local Python backend. This architecture distributes ACTP across **6 cloud services on Vercel** + **1 local worker daemon**, connected via a shared **Supabase** database.

### Design Principle

> **Cloud queue + dashboard → Local worker executes**

Every service follows the same pattern established by **MediaPoster Lite (MPLite)**:
- Next.js 16 + Supabase deployed on Vercel
- REST API with Bearer token auth
- Optional CLI for scripting
- Dashboard UI for monitoring
- Local machine polls for jobs that require macOS-native execution

### Why Distribute?

| Problem Today | Solution |
|---|---|
| Webhooks from Meta/TikTok/Stripe can't reach local machine | **HookLite** — public Vercel URL receives webhooks |
| Metrics stop collecting when Mac sleeps | **MetricsLite** — Vercel cron runs 24/7 |
| Video gen blocks the pipeline (Sora: 2-5min, Veo3: 10min) | **GenLite** — fire-and-forget cloud job queue |
| Ad budget adjustments don't happen at 3am | **AdLite** — always-on ad management queue |
| No way to trigger Blotato from cloud | **MPLite** + local worker polls → calls Blotato local API |
| Campaign management requires terminal access | **ACTPDash** — web UI for full pipeline control |

---

## Service Map

```
┌─────────────────────────────────────────────────────────────┐
│                    VERCEL (always-on)                         │
│                                                               │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐      │
│  │  MPLite   │ │  GenLite  │ │  AdLite  │ │ HookLite │      │
│  │ publish   │ │ video gen │ │ ad mgmt  │ │ webhooks │      │
│  │ queue     │ │ job queue │ │ queue    │ │ receiver │      │
│  └─────┬─────┘ └─────┬─────┘ └────┬─────┘ └────┬─────┘     │
│        │              │             │             │           │
│  ┌─────┴──────────────┴─────────────┴─────────────┴───┐      │
│  │              Supabase (shared database)             │      │
│  │   actp_campaigns, actp_creatives, actp_organic_     │      │
│  │   posts, actp_ad_deployments, actp_performance_     │      │
│  │   logs, actp_webhooks, actp_gen_jobs, ...           │      │
│  └─────┬──────────────┬─────────────────────────┬─────┘      │
│        │              │                         │             │
│  ┌─────┴──────┐ ┌─────┴──────┐                  │            │
│  │MetricsLite │ │  ACTPDash  │                  │            │
│  │ cron       │ │ campaign   │                  │            │
│  │ polling    │ │ mgmt UI    │                  │            │
│  └────────────┘ └────────────┘                  │            │
└─────────────────────────────────────────────────┼────────────┘
                                                  │
              poll / report via REST API          │
                                                  │
┌─────────────────────────────────────────────────┼────────────┐
│              LOCAL MAC (actp-worker)             │            │
│                                                  │            │
│  ┌───────────────────────────────────────────────┴──┐        │
│  │              actp-worker daemon                    │        │
│  │  • polls MPLite    → Safari/Blotato upload        │        │
│  │  • polls GenLite   → Remotion local render        │        │
│  │  • polls AdLite    → (future local ad tasks)      │        │
│  │  • reports results → Supabase + service APIs      │        │
│  └──────────────────────────────────────────────────┘        │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐      │
│  │  Safari   │ │ Blotato  │ │ Remotion  │ │  ffmpeg  │      │
│  │  browser  │ │  app     │ │ renderer  │ │          │      │
│  └──────────┘ └──────────┘ └───────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Services

### 1. MPLite (MediaPoster Lite) ✅ DONE
- **Status:** Deployed to Vercel
- **URL:** https://mediaposter-lite-isaiahduprees-projects.vercel.app
- **Repo:** `/Users/isaiahdupree/Documents/Software/mediaposter-lite`
- **Purpose:** Organic publishing queue. ACTP enqueues video posts → local machine polls, claims, uploads via Safari/Blotato, reports completion.
- **Supabase tables:** `mplite_queue`, `mplite_config`, `mplite_api_keys`, `mplite_activity_log`

### 2. HookLite — Priority 1
- **Purpose:** Public webhook receiver for Meta Ads, TikTok Ads, Stripe, WaitlistLab, and MPLite completion events.
- **Why cloud:** Meta/TikTok/Stripe require a publicly reachable HTTPS URL for webhook delivery.
- **Key feature:** Receives → validates signature → writes to Supabase → optionally triggers downstream actions.
- **PRD:** `docs/architecture/HOOKLITE_PRD.md`

### 3. MetricsLite — Priority 2
- **Purpose:** 24/7 analytics polling. Vercel cron fetches YouTube/TikTok/Instagram metrics every 30 minutes.
- **Why cloud:** Metrics must be collected even when the Mac is asleep. Platform APIs are rate-limited so we need consistent scheduling.
- **Key feature:** Cron-triggered, writes to `actp_performance_logs`, detects threshold crossings.
- **PRD:** `docs/architecture/METRICSLITE_PRD.md`

### 4. GenLite — Priority 3
- **Purpose:** Video generation job queue. Submits briefs to Sora/Veo3/Nano Banana, polls for completion, stores output URLs.
- **Why cloud:** AI video APIs are cloud services — no local resources needed. Long-running (2-10 min) so should be fire-and-forget.
- **Key feature:** Remotion renders are tagged `local_only` and picked up by actp-worker instead.
- **PRD:** `docs/architecture/GENLITE_PRD.md`

### 5. AdLite — Priority 4
- **Purpose:** Ad deployment and budget management queue. Creates campaigns, adjusts budgets, detects fatigue, pauses underperformers.
- **Why cloud:** Ad platforms need 24/7 budget monitoring. A spend alert at 3am can't wait for your Mac to wake up.
- **Key feature:** Auto-scales budgets for winners, kills fatigued ads, enforces daily spend caps.
- **PRD:** `docs/architecture/ADLITE_PRD.md`

### 6. ACTPDash — Priority 5
- **Purpose:** Campaign management dashboard. Create/monitor campaigns, view creative galleries, approve winners, control budgets.
- **Why cloud:** Web-accessible from any device, no terminal required.
- **Key feature:** Full CRUD for campaigns + real-time status across all Lite services.
- **PRD:** `docs/architecture/ACTPDASH_PRD.md`

### 7. actp-worker (Local Daemon) — Priority 6
- **Purpose:** Unified local worker that polls all cloud queues and executes tasks requiring macOS.
- **Why local:** Safari browser, Blotato app, Remotion renderer, ffmpeg, and filesystem access are macOS-only.
- **Key feature:** Single Python process, polls MPLite + GenLite, routes to Safari/Blotato/Remotion.
- **PRD:** `docs/architecture/ACTP_WORKER_PRD.md`

---

## Shared Infrastructure

### Supabase (Single Project)
All services connect to the **same Supabase project**. This eliminates cross-service API calls for data — every service reads/writes the same tables.

**Existing tables:** `actp_campaigns`, `actp_rounds`, `actp_creatives`, `actp_organic_posts`, `actp_ad_deployments`, `actp_performance_logs`, `actp_winner_selections`

**New tables needed:**
- `actp_webhooks` — inbound webhook events (HookLite)
- `actp_gen_jobs` — video generation job queue (GenLite)
- `actp_ad_actions` — ad deployment action queue (AdLite)
- `actp_cron_runs` — cron execution log (MetricsLite)
- `actp_worker_heartbeats` — local worker status (actp-worker)

### Auth Pattern
Each service uses the same auth model as MPLite:
- `Authorization: Bearer <api_key>` header
- API keys stored in Supabase with scopes (read/write/admin)
- Master key for inter-service communication
- Vercel environment variables for secrets

### Blotato Integration
Blotato is a macOS-native app with a **local-only HTTP API** (typically `http://localhost:PORT`). The cloud cannot reach it directly.

**Solution:** MPLite already handles this. The publishing flow is:
1. Cloud service (ACTP/MPLite) enqueues a publish job with `executor: "blotato"`
2. Local `actp-worker` daemon polls MPLite → sees the job
3. Worker calls Blotato's local API (`http://localhost:PORT/api/upload`)
4. Worker reports completion back to MPLite → MPLiteBridge records OrganicPost

No separate "BloLite" service needed — MPLite queue items carry an `executor` field that tells the local worker whether to use Safari or Blotato.

---

## Implementation Order

| # | Service | Stack | Est. Effort | Blocks |
|---|---------|-------|-------------|--------|
| 1 | HookLite | Next.js + Supabase + Vercel | 1-2 days | Ad status updates, payment tracking |
| 2 | MetricsLite | Next.js + Supabase + Vercel Cron | 1-2 days | Winner selection accuracy |
| 3 | GenLite | Next.js + Supabase + Vercel | 2-3 days | Pipeline throughput |
| 4 | AdLite | Next.js + Supabase + Vercel | 2-3 days | 24/7 ad management |
| 5 | ACTPDash | Next.js + Supabase + Vercel | 3-5 days | Usability |
| 6 | actp-worker | Python daemon | 1-2 days | Local execution |

Each service follows the MPLite template: `create-next-app` → add Supabase client → add API routes → add CLI → deploy to Vercel.

---

## Environment Variables (per service)

All services share:
```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

Service-specific:
```
# HookLite
HOOKLITE_MASTER_KEY=hlk_...
META_APP_SECRET=...           # for webhook signature verification
TIKTOK_APP_SECRET=...
STRIPE_WEBHOOK_SECRET=whsec_...

# MetricsLite
YOUTUBE_API_KEY=...
TIKTOK_ACCESS_TOKEN=...
RAPIDAPI_KEY=...              # for Instagram metrics

# GenLite
OPENAI_API_KEY=...            # Sora
GOOGLE_API_KEY=...            # Veo3
NANO_BANANA_API_KEY=...

# AdLite
META_ACCESS_TOKEN=...
TIKTOK_ADS_ACCESS_TOKEN=...
TIKTOK_ADVERTISER_ID=...

# actp-worker (local .env)
MPLITE_URL=https://mediaposter-lite-...vercel.app
MPLITE_KEY=mpl_...
GENLITE_URL=https://genlite-...vercel.app
GENLITE_KEY=gl_...
BLOTATO_LOCAL_URL=http://localhost:PORT
```
