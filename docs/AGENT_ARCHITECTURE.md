# AI Agent Architecture

## Current Implementation vs Ideal Blueprint

This document maps our current agent framework against the ideal "Control Plane + Data Plane" architecture.

---

## ✅ What We Have

### 1. Control Plane (Agent Runtime)

| Component | Status | Implementation |
|-----------|--------|----------------|
| **Orchestrator/Workflow Engine** | ✅ Done | `run_manager.py` - manages runs, steps, progress |
| **Planner/Router (Brain)** | ✅ Done | `dispatcher.py` - routes topics to service handlers |
| **Policy/Permissions Gate** | ⚠️ Partial | Human approval steps exist, needs budget/limits |

**Files:**
- `Backend/services/agent_framework/run_manager.py` - Run lifecycle management
- `Backend/services/agent_framework/dispatcher.py` - Topic routing
- `Backend/services/agent_framework/background_scheduler.py` - Scheduled tasks

### 2. Communication Layer (Pub/Sub)

| Component | Status | Implementation |
|-----------|--------|----------------|
| **Message Bus (Pub/Sub)** | ✅ Done | `event_bus.py` - in-memory + DB persistence |
| **Topic Routing** | ✅ Done | Topics like `narrative.*`, `experiments.*`, `content_mix.*` |
| **Event Types** | ✅ Done | Thoughts, Actions, Decisions, Milestones |

**Topics Implemented:**
```
shared.run.requested
shared.run.queued
shared.run.started
shared.run.completed
shared.run.failed

narrative.weekly.generate_plan
narrative.daily.execute_schedule
narrative.weekly.reflect

experiments.weekly.plan_experiments
experiments.daily.execute_variants
experiments.daily.analyze_results
experiments.weekly.winner_detection
experiments.weekly.promote_to_narrative

content_mix.generate_plan
content_mix.assign_content
content_mix.approve_plan
content_mix.create_content
```

### 3. Shared State Layer (Blackboard)

| Component | Status | Implementation |
|-----------|--------|----------------|
| **Operational State DB** | ✅ Done | `agent_runs`, `run_steps`, `run_events`, `run_artifacts` |
| **Semantic Memory (Vector)** | ⚠️ Partial | Video embeddings exist, needs agent memory |
| **Short-term Cache** | ❌ Missing | Should add Redis for locks, rate limits |
| **Audit Log/Trace Store** | ✅ Done | `agent_events` table, full replay capability |

**Database Tables:**
```sql
agent_runs          -- Run lifecycle: id, status, progress, context
run_steps           -- Step progression: key, status, started/ended
run_events          -- Event stream: thoughts, actions, decisions
run_artifacts       -- Outputs: plans, schedules, reports
agent_events        -- Global event log for replay
```

### 4. Data Plane (Tools & Services)

| Service | Status | Description |
|---------|--------|-------------|
| **NarrativePlannerService** | ✅ Done | 7-day content planning with AI |
| **ExperimentsService** | ✅ Done | A/B testing and winner detection |
| **ContentMixService** | ✅ Done | Long-term scheduling (2mo-1yr) |
| **BlotatoAPI** | ✅ Done | Social posting to 10+ platforms |
| **TrendCrawler** | ✅ Done | Instagram trend discovery |
| **VideoAnalyzer** | ✅ Done | AI content analysis |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CONTROL PLANE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐ │
│  │   Run Manager    │    │    Dispatcher    │    │   Scheduler    │ │
│  │  (Orchestrator)  │───▶│    (Router)      │───▶│  (Background)  │ │
│  └────────┬─────────┘    └────────┬─────────┘    └───────┬────────┘ │
│           │                       │                       │          │
│           ▼                       ▼                       ▼          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      EVENT BUS (Pub/Sub)                        │ │
│  │  Topics: narrative.* | experiments.* | content_mix.* | shared.* │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SHARED STATE (Blackboard)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ agent_runs  │  │ run_steps   │  │ run_events  │  │ artifacts  │ │
│  │ (lifecycle) │  │ (progress)  │  │ (thoughts)  │  │ (outputs)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │           PostgreSQL (Supabase) - Single Source of Truth        ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA PLANE (Services)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │
│  │   Narrative    │  │  Experiments   │  │    Content Mix         │ │
│  │   Planner      │  │    Runner      │  │     Planner            │ │
│  │                │  │                │  │                        │ │
│  │ • Generate     │  │ • Plan A/B     │  │ • Generate 2mo-1yr     │ │
│  │ • Execute      │  │ • Analyze      │  │ • Assign content       │ │
│  │ • Reflect      │  │ • Promote      │  │ • Create AI/animated   │ │
│  └────────────────┘  └────────────────┘  └────────────────────────┘ │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │
│  │    Blotato     │  │  Trend Crawler │  │   Video Analyzer       │ │
│  │    (Posting)   │  │  (Discovery)   │  │   (AI Analysis)        │ │
│  └────────────────┘  └────────────────┘  └────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Loop: Plan → Act → Observe → Repeat

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT EXECUTION LOOP                         │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │   PLAN   │────▶│   ACT    │────▶│ OBSERVE  │────▶│  REPEAT  │
  └──────────┘     └──────────┘     └──────────┘     └──────────┘
       │                │                │                │
       ▼                ▼                ▼                ▼
  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │ Emit:    │     │ Emit:    │     │ Emit:    │     │ Update:  │
  │ THOUGHT  │     │ ACTION   │     │ RESULT   │     │ STATE    │
  │ DECISION │     │ STARTED  │     │ METRICS  │     │ PROGRESS │
  └──────────┘     └──────────┘     └──────────┘     └──────────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │   EVENT BUS      │
                    │  (Persisted to   │
                    │   agent_events)  │
                    └──────────────────┘
```

---

## Event Types & What They Mean

| Event Type | When Emitted | UI Representation |
|------------|--------------|-------------------|
| `thought` | Agent reasoning | 💭 "Thinking..." bubble |
| `decision` | Choice made + justification | ⚖️ Decision card |
| `action.started` | Beginning work | ▶️ In progress |
| `action.completed` | Work done | ✅ Completed |
| `artifact.created` | Output generated | 📄 Downloadable |
| `waiting_approval` | Needs human | 🔔 Notification |
| `error` | Something failed | ❌ Error alert |

---

## Service → Topic → Handler Mapping

| Service | Publishes | Subscribes | Handler |
|---------|-----------|------------|---------|
| **NarrativePlannerService** | `narrative.weekly.generate_plan` | `shared.run.*` | `run_narrative_generate_plan()` |
| **ExperimentsService** | `experiments.weekly.plan_experiments` | `shared.run.*` | `run_experiments_plan()` |
| **ContentMixService** | `content_mix.generate_plan` | `shared.run.*` | `run_content_mix_generate_plan()` |

---

## Database Tables for Agent State

```sql
-- Runs (parent container)
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY,
    agent_type VARCHAR(50),
    schedule_id UUID,
    status VARCHAR(20),  -- queued, running, succeeded, failed
    progress_current INT DEFAULT 0,
    progress_total INT DEFAULT 0,
    root_context_json JSONB,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Steps within a run
CREATE TABLE run_steps (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(id),
    step_key VARCHAR(50),
    status VARCHAR(20),  -- pending, running, completed, failed
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    output_summary TEXT
);

-- Events (thoughts, actions, decisions)
CREATE TABLE run_events (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(id),
    step_id UUID REFERENCES run_steps(id),
    event_type VARCHAR(50),
    severity VARCHAR(20),
    message TEXT,
    payload JSONB,
    source_service VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Artifacts (outputs)
CREATE TABLE run_artifacts (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(id),
    step_id UUID REFERENCES run_steps(id),
    kind VARCHAR(50),  -- schedule_json, reasoning_chain, report
    name VARCHAR(255),
    content_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## What's Missing (Gaps)

| Gap | Priority | Solution |
|-----|----------|----------|
| **Redis Cache** | Medium | Add for rate limits, locks, fast context |
| **Budget Tracking** | High | Add API call counting, cost limits |
| **Agent Memory (Vector)** | Medium | Store agent learnings as embeddings |
| **Human Approval UI** | Done ✅ | Agent Panel shows waiting items |
| **Run Replay** | Done ✅ | Events stored, can replay |

---

## How to Add a New Agent

1. **Create service handler** in `services/agent_framework/services/`
2. **Add topics** to `dispatcher.py` TOPICS dict
3. **Add dynamic handler** in `_get_dynamic_handler()`
4. **Export** from `services/__init__.py`
5. **Add step registry** (optional) for UI progress tracking

Example:
```python
# 1. Create handler
async def run_my_agent_task(run_id: str, payload: Dict):
    rm = get_run_manager()
    rm.start_step(run_id, "my_step", "Doing something")
    rm.emit_thought(run_id, step_id, "Thinking about this...")
    # ... do work ...
    rm.complete_step(run_id, "my_step", "Done!")

# 2. Add topic
TOPICS["MY_AGENT_TASK"] = "my_agent.do_task"

# 3. Add handler lookup
if topic == TOPICS["MY_AGENT_TASK"]:
    from .services.my_service import run_my_agent_task
    return run_my_agent_task
```

---

## Visualization (Agent Panel)

The Agent Panel at `/agent-panel` shows:
- **Active Runs** - What's currently executing
- **Run Timeline** - Events as they happen
- **Thoughts/Decisions** - AI reasoning visible
- **Artifacts** - Generated outputs
- **Approval Queue** - Items needing human review

---

## Next Steps

1. Add Redis for caching and rate limiting
2. Implement budget tracking per agent
3. Add vector memory for agent learnings
4. Create "specialist agent" pattern for delegation
