# PRD: Content Ops Controller - Technical Specification

**Companion to:** `PRD_CONTENT_OPS_CONTROLLER.md`

---

## 1. Data Model

### 1.1 Unified Touchpoint Schema

```json
{
  "touchpoint_id": "tp_uuid",
  "platform": "x|instagram|tiktok|youtube|linkedin|threads|email",
  "channel": "post|comment|dm|email",
  "platform_object_id": "platform_native_id",
  "actor": "creator|user",
  "text": "content",
  "source_touchpoint_id": "parent_id_if_reply",
  "brand_id": "brand_uuid",
  "offer_id": "offer_uuid",
  "icp_id": "icp_uuid",
  "template_id": "tpl_uuid",
  "prompt_run_id": "run_uuid",
  "shortlink_id": "sl_uuid",
  "utm_id": "utm_string",
  "created_at": "ISO8601"
}
```

### 1.2 Prompt Run Record

```json
{
  "prompt_run_id": "run_2026_01_16_00123",
  "template_id": "tpl_018",
  "inputs": {
    "topic": "demand radar for existing apps",
    "audience": "indie founders",
    "offer": "KeywordRadar.app"
  },
  "model": { "name": "gpt-4o", "temperature": 0.7 },
  "output_text": "generated content..."
}
```

### 1.3 Metrics Snapshot

```json
{
  "post_id": "1879912345678901234",
  "pulled_at": "2026-01-17T15:05:00Z",
  "x_metrics": {
    "public_metrics": { "like_count": 91, "reply_count": 14, "repost_count": 9 },
    "impression_count": 18200,
    "url_link_clicks": 240
  },
  "link_metrics": { "shortlink_clicks": 240, "landing_conversions": 7 }
}
```

---

## 2. API Endpoints

### 2.1 Configuration

```
GET  /v1/creator
PUT  /v1/creator

GET  /v1/brands
POST /v1/brands
PUT  /v1/brands/{brand_id}

GET  /v1/offers?brand_id=
POST /v1/offers
PUT  /v1/offers/{offer_id}

GET  /v1/icps?offer_id=
POST /v1/icps
PUT  /v1/icps/{icp_id}

GET  /v1/templates?channel=&awareness=
POST /v1/templates
PUT  /v1/templates/{template_id}
POST /v1/templates/{template_id}/fork
```

### 2.2 Planning

```
POST /v1/plans/generate
  body: { week_start, goal_mode, channels[], constraints? }

GET  /v1/plans/{plan_id}
POST /v1/plans/{plan_id}/slots/{slot_id}/execute
POST /v1/plans/{plan_id}/replan
```

### 2.3 Generation + QA + Publishing

```
POST /v1/generate
  body: { slot_id, template_id?, offer_id, icp_id, channel, platform, variants: 3 }

POST /v1/qa/check
  body: { draft_id }

POST /v1/publish
  body: { draft_id }

GET  /v1/approvals?status=pending
POST /v1/approvals/{approval_id}/approve
POST /v1/approvals/{approval_id}/reject
```

### 2.4 Inbound + Response

```
POST /v1/inbound/ingest
  body: { platform, channel, external_event_id, payload }

POST /v1/respond
  body: { inbound_touchpoint_id, strategy: "public_reply"|"dm_flow"|"email_reply" }
```

### 2.5 Attribution + Metrics

```
POST /v1/shortlinks
  body: { destination_url, touchpoint_id, offer_id, icp_id, template_id }

GET  /v1/metrics/pull?touchpoint_id=&window=1h|6h|24h|72h|7d
POST /v1/scores/recompute?touchpoint_id=
POST /v1/learn/run?date=YYYY-MM-DD
GET  /v1/leaderboard/templates?channel=&offer_id=&icp_id=
```

---

## 3. Event Bus Topics

```
plan.generate.requested
slot.execute.requested
draft.generate.requested
draft.qa.requested
draft.publish.requested
inbound.received
inbound.respond.requested
metrics.snapshot.requested
metrics.snapshot.completed
score.compute.requested
learn.update.requested
approval.required
alert.raised
```

### Event Envelope

```json
{
  "event_id": "evt_123",
  "event_type": "draft.generate.requested",
  "timestamp": "2026-01-16T23:59:59Z",
  "trace_id": "trace_abc",
  "idempotency_key": "slot_001:draftgen:v1",
  "payload": {}
}
```

### Slot Execution Payload

```json
{
  "slot_id": "slot_mon_am",
  "plan_id": "plan_2026_01_19",
  "platform": "x",
  "channel": "post",
  "awareness_level": "solution_aware",
  "fate_target": { "F": 0.3, "A": 0.6, "T": 0.0, "E": 0.1 },
  "cta_strength": "soft",
  "target_offer_id": "offer_keywordradar",
  "target_icp_id": "icp_indies",
  "template_hint_ids": ["tpl_09", "tpl_11"]
}
```

---

## 4. Worker Contracts

| Worker | Consumes | Emits |
|--------|----------|-------|
| planner-worker | `plan.generate.requested` | ContentPlan + Slots |
| executor-worker | `slot.execute.requested` | `draft.generate.requested` |
| generator-worker | `draft.generate.requested` | PromptRun + Drafts |
| qa-worker | `draft.qa.requested` | `draft.publish.requested` or `approval.required` |
| publisher-worker | `draft.publish.requested` | Touchpoint status |
| inbound-worker | platform webhooks | `inbound.respond.requested` |
| responder-worker | `inbound.respond.requested` | Response → QA → publish |
| metrics-worker | cron | MetricsSnapshots |
| scorer-worker | `score.compute.requested` | Scores + labels |
| learner-worker | `learn.update.requested` | Leaderboard updates + forks |

---

## 5. TypeScript Interfaces

```typescript
export type Platform = "x" | "instagram" | "tiktok" | "youtube" | "linkedin" | "threads" | "email";
export type Channel = "post" | "comment" | "dm" | "email";

export interface PublishResult {
  platform_object_id: string;
  platform_url?: string;
  published_at: string;
}

export interface MetricsResult {
  impressions?: number;
  likes?: number;
  replies?: number;
  reposts?: number;
  profile_clicks?: number;
  link_clicks?: number;
}

export interface InboundItem {
  external_event_id: string;
  channel: Channel;
  author_handle: string;
  text: string;
  context: Record<string, unknown>;
  received_at: string;
}

export interface AdapterAuthState {
  status: "valid" | "expiring" | "invalid";
  expires_at?: string;
}

export interface PlatformAdapter {
  platform: Platform;
  getAuthState(): Promise<AdapterAuthState>;
  refreshAuth(): Promise<void>;
  publishPost(input: { text: string; media_urls?: string[] }): Promise<PublishResult>;
  replyToComment(input: { parent_id: string; text: string }): Promise<PublishResult>;
  sendDM(input: { recipient: string; text: string }): Promise<PublishResult>;
  fetchInbound(params: { since?: string }): Promise<InboundItem[]>;
  fetchMetrics(params: { id: string; window: string }): Promise<MetricsResult>;
}
```

---

## 6. Rate Limiting

**Three layers:**
1. Platform limit (global per app)
2. Account limit (per connected account)
3. User limit (per recipient in DMs)

**Implementation:**
- Token bucket per (platform, account, endpoint)
- Hard pacing for DMs: max N/day per recipient + cooldown
- Exponential backoff with jitter
- Dead-letter queue: `dlq.*`

---

## 7. Safety Gates

- **DM Permission Gate:** Links only after consent or promised asset delivery
- **Per-user cooldown:** Max DM/day per recipient
- **Per-offer fatigue:** Max direct CTA/day per offer
- **Blocklist phrases + spam heuristics**
- **Human review queue** for uncertain content
- **"Stop" detection:** Mark contact as do-not-message

---

## 8. Recommended Stack

| Component | Tool |
|-----------|------|
| Database | Postgres (Supabase) |
| Queue | Redis + BullMQ |
| Orchestrator | n8n |
| Analytics | PostHog |
| Shortlinks | Custom redirect microservice |
| Gen | OpenAI API |
| Dashboard | Next.js admin |

---

## 9. Build Order

1. **X (posts) + Email loop** end-to-end (cleanest APIs)
2. **Add comments** ingestion + replies
3. **Add DM routing** with permission gate
4. **Expand adapters** to other platforms one by one
