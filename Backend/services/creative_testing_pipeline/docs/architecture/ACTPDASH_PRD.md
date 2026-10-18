# ACTPDash — Campaign Management Dashboard

## Product Requirements Document

### Problem
Managing ACTP campaigns currently requires terminal access to the local MediaPoster backend — running Python scripts, querying Supabase manually, or hitting API endpoints via curl. There's no visual overview of campaign progress, creative performance, or system health. Non-technical stakeholders can't interact with the pipeline at all.

### Solution
A Next.js dashboard deployed on Vercel that provides full campaign lifecycle management through a modern web UI. It reads/writes to the shared Supabase database and orchestrates actions through the other Lite services (MPLite, GenLite, AdLite, MetricsLite, HookLite).

### Architecture
```
Browser
   │
   ▼
ACTPDash (Vercel)
   │
   ├── Direct Supabase reads (campaigns, creatives, metrics, logs)
   ├── MPLite API calls (publish queue management)
   ├── GenLite API calls (video generation jobs)
   ├── AdLite API calls (ad deployment + budget controls)
   ├── MetricsLite API calls (collection status, alerts)
   └── HookLite API calls (webhook event viewer)
```

### Tech Stack
- **Framework:** Next.js 16 (App Router)
- **Database:** Supabase (shared ACTP project)
- **Hosting:** Vercel
- **UI:** Tailwind CSS, shadcn/ui, Recharts (for metric charts)
- **Auth:** Supabase Auth (email/password or magic link)

### Dashboard Pages

#### Campaign Management
| Page | Path | Purpose |
|------|------|---------|
| Campaigns | `/` | All campaigns with status, round count, winner count, total spend |
| Campaign Detail | `/campaigns/[id]` | Full campaign view: rounds, creatives, metrics, spend, timeline |
| Create Campaign | `/campaigns/new` | Campaign creation wizard (offer, platforms, budget, schedule) |
| Campaign Settings | `/campaigns/[id]/settings` | Edit campaign config, pause/resume, set budget rules |

#### Creative Gallery
| Page | Path | Purpose |
|------|------|---------|
| Creatives | `/creatives` | Grid view of all creatives with thumbnails, scores, status |
| Creative Detail | `/creatives/[id]` | Video preview, metrics breakdown, organic + ad performance |
| Generate | `/creatives/generate` | Submit generation jobs to GenLite (model, prompt, brief) |

#### Publishing
| Page | Path | Purpose |
|------|------|---------|
| Publish Queue | `/publish` | MPLite queue view: pending, claimed, completed, failed |
| Publish History | `/publish/history` | All published organic posts with metrics |
| Schedule | `/publish/schedule` | Calendar view of scheduled posts |

#### Ads & Budget
| Page | Path | Purpose |
|------|------|---------|
| Ad Deployments | `/ads` | All active ads: platform, spend, CTR, CPA, status |
| Ad Detail | `/ads/[id]` | Spend timeline, metric charts, budget history, actions log |
| Budget Rules | `/ads/rules` | Configure auto-scale, spend caps, fatigue rules |
| Spend Overview | `/ads/spend` | Daily/weekly spend aggregations by campaign and platform |

#### Analytics
| Page | Path | Purpose |
|------|------|---------|
| Performance | `/analytics` | Cross-creative comparison charts (views, engagement, CTR) |
| Winners | `/analytics/winners` | Winner selection history with reasoning |
| Trends | `/analytics/trends` | Platform-level trend analysis (best posting times, formats) |
| Alerts | `/analytics/alerts` | MetricsLite alerts feed with acknowledge controls |

#### System Health
| Page | Path | Purpose |
|------|------|---------|
| System Status | `/system` | Service health for all Lite services + worker heartbeat |
| Webhooks | `/system/webhooks` | HookLite event feed (recent webhooks, failure rates) |
| Cron Runs | `/system/crons` | MetricsLite + AdLite cron execution history |
| Worker | `/system/worker` | actp-worker heartbeat, active jobs, local machine status |
| Logs | `/system/logs` | Unified log viewer across all services |

### Key UI Components

#### Campaign Card
```
┌─────────────────────────────────────────┐
│ 🎯 Summer Hook Test                     │
│ Status: Round 3 of 5  ●  Active         │
│                                          │
│ Creatives: 12  Winners: 2  Spend: $23   │
│ Platforms: TikTok, YouTube, Instagram    │
│                                          │
│ Best CTR: 3.2% (creative-007)           │
│ ████████████████░░░░ 68% complete       │
└─────────────────────────────────────────┘
```

#### Creative Card (Grid View)
```
┌──────────────┐
│  [thumbnail] │
│              │
│ hook-v3-ugc  │
│ Score: 87/100│
│ 12.4K views  │
│ CTR: 2.8%    │
│ ● Winner     │
└──────────────┘
```

#### Service Health Bar
```
┌─────────────────────────────────────────────────┐
│ MPLite ● │ GenLite ● │ AdLite ● │ Metrics ● │ Hooks ● │ Worker ● │
│  healthy  │  healthy  │ healthy  │  healthy  │ healthy │  online  │
└─────────────────────────────────────────────────┘
```

### API Routes (BFF — Backend for Frontend)

ACTPDash API routes aggregate data from Supabase and proxy to other Lite services:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/campaigns` | List campaigns with summary stats |
| GET | `/api/campaigns/:id` | Campaign detail with rounds, creatives |
| POST | `/api/campaigns` | Create campaign |
| PUT | `/api/campaigns/:id` | Update campaign |
| POST | `/api/campaigns/:id/pause` | Pause campaign |
| POST | `/api/campaigns/:id/resume` | Resume campaign |
| GET | `/api/creatives` | List creatives with metrics |
| GET | `/api/creatives/:id` | Creative detail |
| POST | `/api/creatives/generate` | Proxy to GenLite: submit generation job |
| POST | `/api/creatives/:id/publish` | Proxy to MPLite: enqueue organic post |
| POST | `/api/creatives/:id/deploy-ad` | Proxy to AdLite: deploy as paid ad |
| GET | `/api/analytics/overview` | Aggregated performance metrics |
| GET | `/api/analytics/winners` | Winner selection history |
| GET | `/api/analytics/alerts` | Proxy to MetricsLite: active alerts |
| GET | `/api/system/health` | Aggregate health from all Lite services |
| GET | `/api/system/webhooks` | Proxy to HookLite: recent events |
| GET | `/api/system/worker` | Worker heartbeat status from Supabase |

### Real-Time Features
- **Supabase Realtime** subscriptions on:
  - `actp_creatives` — live status updates in creative gallery
  - `actp_organic_posts` — publish completion notifications
  - `actp_performance_logs` — live metric updates on detail pages
  - `actp_metric_alerts` — toast notifications for new alerts
  - `actp_worker_heartbeats` — worker online/offline indicator

### Auth & Access Control
- Supabase Auth with email/password (single-user initially)
- API routes protected by session cookie
- Future: role-based access (viewer, operator, admin)

### Environment Variables
```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

MPLITE_URL=https://mediaposter-lite-...vercel.app
MPLITE_KEY=mpl_...
GENLITE_URL=https://genlite-...vercel.app
GENLITE_KEY=gl_...
ADLITE_URL=https://adlite-...vercel.app
ADLITE_KEY=alk_...
METRICSLITE_URL=https://metricslite-...vercel.app
METRICSLITE_KEY=mlk_...
HOOKLITE_URL=https://hooklite-...vercel.app
HOOKLITE_KEY=hlk_...
```

### File Structure
```
actpdash/
├── app/
│   ├── api/
│   │   ├── campaigns/...
│   │   ├── creatives/...
│   │   ├── analytics/...
│   │   └── system/...
│   ├── campaigns/
│   │   ├── page.tsx
│   │   ├── new/page.tsx
│   │   └── [id]/
│   │       ├── page.tsx
│   │       └── settings/page.tsx
│   ├── creatives/
│   │   ├── page.tsx
│   │   ├── generate/page.tsx
│   │   └── [id]/page.tsx
│   ├── publish/
│   │   ├── page.tsx
│   │   ├── history/page.tsx
│   │   └── schedule/page.tsx
│   ├── ads/
│   │   ├── page.tsx
│   │   ├── rules/page.tsx
│   │   ├── spend/page.tsx
│   │   └── [id]/page.tsx
│   ├── analytics/
│   │   ├── page.tsx
│   │   ├── winners/page.tsx
│   │   ├── trends/page.tsx
│   │   └── alerts/page.tsx
│   ├── system/
│   │   ├── page.tsx
│   │   ├── webhooks/page.tsx
│   │   ├── crons/page.tsx
│   │   ├── worker/page.tsx
│   │   └── logs/page.tsx
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── ui/ (shadcn)
│   ├── campaign-card.tsx
│   ├── creative-card.tsx
│   ├── metric-chart.tsx
│   ├── service-health-bar.tsx
│   ├── alert-toast.tsx
│   └── nav-sidebar.tsx
├── lib/
│   ├── supabase.ts
│   ├── service-clients.ts
│   └── utils.ts
├── package.json
├── vercel.json
└── README.md
```

### Success Criteria
1. Full campaign CRUD without terminal access
2. Creative gallery with video thumbnails and metric overlays
3. Real-time status updates via Supabase Realtime
4. Service health visible at a glance from any page
5. Winner approval workflow (review → approve → deploy ad)
6. Responsive design — usable on mobile for quick checks
