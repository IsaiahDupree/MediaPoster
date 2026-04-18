# PRD 06 — Agent Orchestration Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `services/master_orchestrator.py` — Master pipeline coordinator (Sora→Stitch→Analyze→Publish)
- `services/agent_framework/` — EventBus, dispatcher, run_manager, background_scheduler
- `services/agent_scheduler.py` — Cron/interval agent scheduling
- `services/agent_event_service.py` — Agent event persistence
- `services/narrative_scheduler/` — Narrative planning scheduler
- `services/narrative_goals_service.py` — Narrative goal tracking
- `services/experiments_scheduler/` — A/B experiment scheduler + agent
- `services/event_bus/` — Pub/sub event bus
- `models/agent_event.py` — AgentEvent model
- `api/endpoints/orchestrator.py` — Pipeline API (start/status/cancel)
- `api/endpoints/agent_panel.py` — Agent status/timeline/control API
- `api/endpoints/agent_events.py` — Agent events streaming API
- `migrations/agent_schedules_runs_steps.sql`
- `migrations/agent_budget_memory_schema.sql`

## Current State
- MasterOrchestrator takes `theme` + `PipelineConfig` → runs full pipeline
- AgentScheduler supports cron + interval with DB persistence
- EventBus coordinates subsystems via pub/sub
- Agent panel exposes timeline of thoughts/actions for all agents
- Celery used for some async task execution

## Features to Build

### F1 — GoalDecompositionAgent
**The most Polsia-like feature.** Accept a high-level natural language goal, use GPT-4o to decompose it into a sequence of `PipelineConfig` objects, schedule them via `AgentScheduler`.

Input: `{ "goal": "Grow @the_isaiah_dupree to 100K followers in 60 days", "platforms": ["tiktok", "instagram"] }`

GPT-4o call: decompose goal → 30/60/90-day milestones → weekly content themes → individual pipeline runs.

Output: list of scheduled pipeline configs with dates.

Add `POST /api/orchestrator/goals/decompose` endpoint.
Add `GET /api/orchestrator/goals/{goal_id}/status` showing milestone progress vs actuals.

### F2 — Cross-Pipeline Learning Service
After every completed pipeline, store: theme, FATE scores, awareness level, platform, published_count, engagement_at_24h.
Add `CrossPipelineLearningService` that:
1. Queries last 30 days of pipeline results
2. Identifies top-performing themes/hooks/formats
3. Generates a "what's working" context blob
4. Injects it into the next pipeline's content generation prompt

Add `GET /api/orchestrator/learnings` returning the current context blob.

### F3 — Parallel Strategy Variants
Add `StrategyVariantRunner` that spins up N parallel `MasterOrchestrator` instances with variant configs (different themes/awareness levels), waits for pre_social_score from content analysis, promotes the winner.

Add `POST /api/orchestrator/pipeline/variants` accepting `base_config + variants: list`.

### F4 — Agent Budget Enforcement
Use `agent_budget_memory_schema.sql` tables. Before each agent run, check remaining budget.
If OpenAI spend for the day exceeds `$budget_daily_limit` (from env), pause non-critical agents.
Emit `agent_budget_warning` event at 80% and `agent_budget_halt` at 100%.

### F5 — Live Agent Feed SSE Endpoint
Add `GET /api/agents/feed` as a Server-Sent Events stream.
Push all new `agent_events` in real-time as they're inserted to DB.
Format: `data: { "agent": "narrative", "type": "thought", "text": "...", "ts": "..." }`
This powers a Polsia-style live activity feed in the dashboard.

## Success Criteria
- GoalDecompositionAgent uses real GPT-4o call, returns executable schedule
- CrossPipelineLearning improves prompt quality measurably over 5+ runs
- Budget enforcement halts agents before overspending
- SSE feed streams events with <1s latency
