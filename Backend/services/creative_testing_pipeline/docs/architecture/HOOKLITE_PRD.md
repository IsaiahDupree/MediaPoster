# HookLite — Webhook Receiver Service

## Product Requirements Document

### Problem
ACTP needs to receive inbound webhooks from Meta Ads, TikTok Ads, Stripe, WaitlistLab, and MPLite. These platforms POST to a public HTTPS URL when events occur (ad status changes, payments, offer conversions, publish completions). The local MediaPoster backend has no public URL, so all webhook-driven features are currently broken.

### Solution
A lightweight Next.js + Supabase service deployed on Vercel that:
1. Exposes public webhook endpoints per source platform
2. Validates webhook signatures (HMAC, shared secrets)
3. Writes validated events to `actp_webhooks` in Supabase
4. Optionally triggers downstream actions (update ad status, record payment, sync MPLite completion)
5. Provides a dashboard to view/replay/debug webhook events

### Architecture
```
Meta Ads ──POST──→ hooklite.vercel.app/api/hooks/meta
TikTok   ──POST──→ hooklite.vercel.app/api/hooks/tiktok
Stripe   ──POST──→ hooklite.vercel.app/api/hooks/stripe
WaitlistLab──POST→ hooklite.vercel.app/api/hooks/waitlistlab
MPLite   ──POST──→ hooklite.vercel.app/api/hooks/mplite
                          │
                          ▼
                    Validate signature
                    Parse + normalize payload
                    Write to actp_webhooks
                    Trigger downstream action
                          │
                          ▼
                  Supabase (actp_webhooks table)
```

### Tech Stack
- **Framework:** Next.js 16 (App Router)
- **Database:** Supabase (shared ACTP project)
- **Hosting:** Vercel (serverless functions, 30s max duration)
- **Auth:** Per-source signature validation + master API key for dashboard

### Supabase Tables

#### `actp_webhooks`
```sql
CREATE TABLE actp_webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,          -- 'meta_ads', 'tiktok_ads', 'stripe', 'waitlistlab', 'mplite'
  event_type TEXT NOT NULL,      -- 'ad_status_update', 'payment.succeeded', etc.
  payload JSONB NOT NULL,        -- raw webhook body
  headers JSONB,                 -- selected request headers
  signature_valid BOOLEAN DEFAULT TRUE,
  handled BOOLEAN DEFAULT FALSE,
  handler_result JSONB,
  ip_address TEXT,
  received_at TIMESTAMPTZ DEFAULT NOW(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX idx_webhooks_source ON actp_webhooks(source, event_type);
CREATE INDEX idx_webhooks_received ON actp_webhooks(received_at DESC);
```

### API Routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/hooks/meta` | Receive Meta Ads webhooks (ad status, spend alerts) |
| POST | `/api/hooks/tiktok` | Receive TikTok Ads webhooks (ad status) |
| POST | `/api/hooks/stripe` | Receive Stripe webhooks (payment events) |
| POST | `/api/hooks/waitlistlab` | Receive WaitlistLab webhooks (offer conversions) |
| POST | `/api/hooks/mplite` | Receive MPLite webhooks (publish complete/failed) |
| POST | `/api/hooks/generic` | Generic webhook endpoint (custom integrations) |
| GET | `/api/hooks/health` | Health check |
| GET | `/api/events` | List recent webhook events (dashboard) |
| GET | `/api/events/:id` | Get specific event details |
| POST | `/api/events/:id/replay` | Re-process an event |
| GET | `/api/stats` | Webhook event statistics |

### Webhook Handlers

#### Meta Ads (`/api/hooks/meta`)
- **Validates:** HMAC-SHA256 signature using `META_APP_SECRET`
- **Events:**
  - `ad_status_update` → Update `actp_ad_deployments.status`
  - `spend_threshold` → Log spend alert
  - `campaign_paused` → Update campaign status
- **Verification:** Supports Meta's GET verification challenge for webhook registration

#### TikTok Ads (`/api/hooks/tiktok`)
- **Validates:** Signature using `TIKTOK_APP_SECRET`
- **Events:**
  - `ad_status_update` → Update `actp_ad_deployments.status`
  - `budget_exhausted` → Log + alert

#### Stripe (`/api/hooks/stripe`)
- **Validates:** `stripe.webhooks.constructEvent()` with `STRIPE_WEBHOOK_SECRET`
- **Events:**
  - `payment_intent.succeeded` → Record payment for creative
  - `charge.refunded` → Update records

#### WaitlistLab (`/api/hooks/waitlistlab`)
- **Validates:** Bearer token match
- **Events:**
  - `offer.converted` → Link conversion to creative
  - `campaign.updated` → Sync offer data

#### MPLite (`/api/hooks/mplite`)
- **Validates:** Bearer token match against `MPLITE_WEBHOOK_SECRET`
- **Events:**
  - `item.published` → Write OrganicPost to `actp_organic_posts` via MPLiteBridge logic
  - `item.failed` → Record failure

### Dashboard Pages

| Page | Path | Purpose |
|------|------|---------|
| Events | `/` | Live feed of recent webhook events with status indicators |
| Event Detail | `/events/[id]` | Full payload, headers, handler result, replay button |
| Sources | `/sources` | Per-source stats: event counts, success rates, latency |
| Settings | `/settings` | API key management, source configuration |

### Environment Variables
```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

HOOKLITE_MASTER_KEY=hlk_...              # Dashboard auth
META_APP_SECRET=...                       # Meta webhook signature verification
TIKTOK_APP_SECRET=...                     # TikTok webhook signature verification
STRIPE_WEBHOOK_SECRET=whsec_...           # Stripe webhook verification
WAITLISTLAB_WEBHOOK_SECRET=wlh_...        # WaitlistLab webhook verification
MPLITE_WEBHOOK_SECRET=mwh_...             # MPLite webhook verification
```

### CLI Commands
```bash
hooklite health              # Check service health
hooklite events              # List recent events
hooklite events <id>         # View event detail
hooklite events <id> replay  # Replay an event
hooklite stats               # Event statistics
hooklite sources             # List configured sources
```

### File Structure
```
hooklite/
├── app/
│   ├── api/
│   │   ├── hooks/
│   │   │   ├── meta/route.ts
│   │   │   ├── tiktok/route.ts
│   │   │   ├── stripe/route.ts
│   │   │   ├── waitlistlab/route.ts
│   │   │   ├── mplite/route.ts
│   │   │   └── generic/route.ts
│   │   ├── events/
│   │   │   ├── route.ts
│   │   │   └── [id]/
│   │   │       ├── route.ts
│   │   │       └── replay/route.ts
│   │   ├── stats/route.ts
│   │   └── health/route.ts
│   ├── events/
│   │   └── [id]/page.tsx
│   ├── sources/page.tsx
│   ├── settings/page.tsx
│   ├── layout.tsx
│   └── page.tsx
├── cli/hooklite.js
├── lib/
│   ├── supabase.ts
│   ├── api-helpers.ts
│   ├── schemas.ts
│   ├── validators/
│   │   ├── meta.ts
│   │   ├── tiktok.ts
│   │   ├── stripe.ts
│   │   └── common.ts
│   └── handlers/
│       ├── meta-handler.ts
│       ├── tiktok-handler.ts
│       ├── stripe-handler.ts
│       ├── waitlistlab-handler.ts
│       └── mplite-handler.ts
├── package.json
├── vercel.json
└── README.md
```

### Success Criteria
1. Meta Ads webhook registration succeeds with HookLite URL
2. Stripe test webhooks received and validated correctly
3. MPLite publish completion events create OrganicPost records
4. Dashboard shows live event feed with < 2s latency
5. Failed signature validations are logged but rejected (401)
6. Event replay re-triggers the handler and updates the record
