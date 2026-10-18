# PRD 08 — CRM & Outreach Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `services/relationship_crm.py` — Core CRM: contact tracking, interaction history
- `services/relationship_cadence.py` — Outreach cadence scheduler
- `services/relationship_metrics.py` — Relationship health scoring
- `services/relationship_fit_signals.py` — ICP fit detection from social signals
- `services/relationship_ai.py` — AI-powered relationship suggestions
- `services/dm_outreach/` — DM outreach campaigns
- `services/dm_warmth_system.py` — Warm/cold classification + escalation
- `services/dm_fetcher_service.py` — Fetch DMs from platforms
- `services/dm_permission_service.py` — DM permission gating
- `services/email_sequence_service.py` — Email drip sequences
- `services/email_service.py` — Email sending
- `services/touchpoint_service.py` — Touchpoint tracking (view, like, comment, DM)
- `services/lead_discovery_service.py` — Lead discovery from social followers/engagers
- `services/lead_form_service.py` — Lead form capture + routing
- `services/person_lens.py` — Person-level analytics lens

## Features to Build

### F1 — Lead Scoring Pipeline
Build `LeadScorer` that takes a person (follower/engager) and scores them 0–100 on ICP fit.
Signals: engages with content regularly (+20), matches job title keywords (+15),
follows competitors (+10), has commented multiple times (+25), has replied to DM (+30).
Store score in `relationship_crm.py` contact record.
Add `GET /api/crm/contacts?min_score=70&limit=50` returning ranked lead list.

### F2 — Outreach Sequence Automator
Build `OutreachSequenceRunner` using `relationship_cadence.py`.
Sequence steps: Day 0 → like post, Day 2 → comment, Day 5 → DM (warm intro), Day 10 → DM (offer).
Each step dispatches to `safari_queue_manager` for browser execution.
Add `POST /api/crm/sequences/start` accepting `{ contact_id, sequence_id }`.
Block if contact has already been DM'd in last 14 days.

### F3 — DM Reply Intelligence
When a new DM reply is received (via `dm_fetcher_service.py`), use GPT-4o to:
1. Classify intent: `interested`, `not_interested`, `question`, `objection`
2. Generate 3 suggested reply options
3. Route `interested` contacts to human approval queue
Store in `touchpoint_service.py` as touchpoint type `dm_reply`.
Add `GET /api/crm/contacts/{contact_id}/suggested-replies` endpoint.

### F4 — Warmth Score Tracker
`dm_warmth_system.py` classifies contacts as cold/warm/hot.
Add automatic re-classification every 7 days based on recent engagement.
Emit `agent_event` type `lead_went_hot` when a contact crosses warm→hot threshold.
Add `GET /api/crm/warmth-changes?days=7` returning all recent status transitions.

### F5 — Email Sequence Trigger from Social Signal
When a lead submits a lead form OR replies positively to DM, automatically enroll them
in the matching email sequence from `email_sequence_service.py`.
Map `offer_id` → `sequence_id` in config.
Add `POST /api/crm/contacts/{contact_id}/enroll-sequence` with auto-select logic.

## Success Criteria
- Lead scoring runs on all contacts with social engagement data
- Outreach sequence dispatches to Safari queue (no manual steps)
- DM reply classification uses real GPT-4o call
- Warmth transitions emit agent events in real-time
- Email enrollment triggers automatically within 60s of qualifying signal
