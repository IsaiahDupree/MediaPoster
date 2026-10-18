# Automation Center + Agent Panels PRD

## Overview

Unified Automation Center with Agent Panels for Narrative Builder + Experiments Scheduler, wired to a shared "runs + events" system so everything can run in the background and stream progress live.

---

## 1. Product UI Map (Routes)

### Core Routes

| Route | Page | Description |
|-------|------|-------------|
| `/automation` | Automation Center (home) | Two primary tabs: Narrative Builder \| Experiments. Global status bar, queue depth, upcoming/running/recent runs |
| `/automation/narrative` | Narrative Builder Control Room | Active goal + constraints, weekly cycle status, next run schedule, runs table filtered to agent_type=narrative |
| `/automation/experiments` | Experiments Control Room | Active experiments + hypotheses, test accounts inventory, runs table, winner pipeline |
| `/runs/[runId]` | Run Detail (Agent Panel) | Steps sidebar, timeline stream, artifacts drawer, controls (pause/cancel/retry) |

### Supporting Routes

| Route | Page | Description |
|-------|------|-------------|
| `/narrative/goals` | Goals list | Create from template |
| `/narrative/goals/[goalId]` | Goal editor | Statement, CTA, audience, targets |
| `/narrative/goals/[goalId]/pillars` | Pillars editor | Targets, min/max posts, priority |
| `/narrative/goals/[goalId]/constraints` | Constraints editor | Platforms, posting windows, blackout dates |
| `/experiments` | Experiments list | All experiments |
| `/experiments/[experimentId]` | Experiment detail | Hypotheses table, status, results, learnings |
| `/topics` | Pub/Sub inspector | Topics list, last events, consumer lag |
| `/services` | Service health | Workers, versions, last heartbeat |

---

## 2. UI Components (shadcn)

### Automation Center Components

| Component | Description |
|-----------|-------------|
| `AgentTypeTabs` | Narrative, Experiments tab switcher |
| `SystemHealthBar` | Worker heartbeat, queue depth, last tick, last failure |
| `ScheduleCard` | Cadence, next run time, toggle enabled, "Run now" |
| `RunsTable` | Status badge, progress, started, duration, last event, "Open panel" |
| `QueueDepthWidget` | Visual queue depth indicator |
| `FailuresWidget` | Latest errors grouped by service/topic |

### Run Detail (Agent Panel) Components

| Component | Description |
|-----------|-------------|
| `StepsSidebar` | Step name, status, duration, progress |
| `TimelineStream` | Virtualized list, grouped by step, filter chips |
| `EventRow` | Timestamp, topic badge, service badge, expandable payload |
| `ArtifactsDrawer` | Plan JSON, Rejection Log, Reflection Report, Winners Report |
| `RunControls` | Pause/cancel/retry + copy debug bundle |

### Pub/Sub Inspector Components

| Component | Description |
|-----------|-------------|
| `TopicList` | List of all topics |
| `TopicEventFeed` | Live event feed for a topic |
| `ServiceConsumerTable` | Topic, consumer group, lag, last ack time |

---

## 3. Database Schema (Universal Run Layer)

### agent_schedules

```sql
CREATE TABLE agent_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id),
    agent_type VARCHAR(50) NOT NULL, -- 'narrative' | 'experiments'
    topic VARCHAR(100) NOT NULL,     -- e.g. narrative.weekly.generate_plan
    cron_expr VARCHAR(50),
    interval_seconds INTEGER,
    enabled BOOLEAN DEFAULT TRUE,
    next_run_at TIMESTAMPTZ,
    config_json JSONB DEFAULT '{}',  -- goal_id, experiment_id, account_ids
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### agent_runs

```sql
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,
    agent_type VARCHAR(50) NOT NULL,
    schedule_id UUID REFERENCES agent_schedules(id),
    status VARCHAR(20) DEFAULT 'queued', -- queued|running|succeeded|failed|canceled|paused
    progress_current INTEGER DEFAULT 0,
    progress_total INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    last_heartbeat_at TIMESTAMPTZ,
    root_context_json JSONB DEFAULT '{}', -- goal_id/week range OR experiment/hypothesis ids
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### agent_steps

```sql
CREATE TABLE agent_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_key VARCHAR(50) NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending|running|completed|failed|skipped
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    summary TEXT,
    input_refs JSONB DEFAULT '[]',
    output_refs JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### agent_events (append-only timeline)

```sql
CREATE TABLE agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_id UUID REFERENCES agent_steps(id),
    ts TIMESTAMPTZ DEFAULT NOW(),
    topic VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) DEFAULT 'info', -- debug|info|warning|error
    source_service VARCHAR(50),
    message TEXT,
    payload_json JSONB DEFAULT '{}'
);
```

### agent_artifacts

```sql
CREATE TABLE agent_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    kind VARCHAR(50) NOT NULL, -- schedule_json|rejection_log|reflection_report|winners_report
    uri TEXT,                  -- Supabase storage path or DB ref
    metadata_json JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Pub/Sub Framework

### Message Envelope (Standard)

```typescript
interface AgentMessage {
    topic: string;
    run_id: string;
    step_key: string;
    source_service: string;
    severity: 'debug' | 'info' | 'warning' | 'error';
    payload: Record<string, any>;
}
```

### Topic Naming Convention

```
{domain}.{scope}.{action}
```

### Topics

#### Narrative Domain
- `narrative.weekly.generate_plan`
- `narrative.daily.execute_schedule`
- `narrative.weekly.reflect`
- `narrative.metrics.ingest`

#### Experiments Domain
- `experiments.weekly.plan_experiments`
- `experiments.daily.execute_variants`
- `experiments.daily.analyze_results`
- `experiments.winner.detect`
- `experiments.winner.promote`

#### Shared
- `shared.metrics.ingest`
- `shared.tools.call`
- `shared.run.failed`
- `shared.run.completed`

### Services (Consumers)

#### Narrative Services
| Service | Responsibility |
|---------|---------------|
| `NarrativePlannerService` | Generates 7-day plan + reasoning chain |
| `NarrativeExecutorService` | Schedules posts + monitors execution |
| `NarrativeReflectionService` | Aggregates metrics + produces learnings |

#### Experiments Services
| Service | Responsibility |
|---------|---------------|
| `ExperimentsPlannerService` | Creates experiments/hypotheses |
| `VariantsBuilderService` | Produces variants (hook/music/caption changes) |
| `ExperimentsExecutorService` | Schedules variants + tagging |
| `WinnerDetectionService` | Pass/fail + winner candidates + promotion |
| `PatternsService` | content_patterns + framework generation |

#### Shared Services
| Service | Responsibility |
|---------|---------------|
| `SchedulerService` | Due schedules → publishes run requests |
| `RunManagerService` | Creates run records + enqueues execution |
| `MetricsIngestService` | Platform metrics → normalized events |
| `ToolRunnerService` | Tool calls (trim, subtitles, remix, caption) |
| `NotificationService` | Alerts |

---

## 5. Step Taxonomy

### Narrative Builder Steps

| step_key | Label | Description |
|----------|-------|-------------|
| `context_gathering` | Context Gathering | Load goals, pillars, constraints, performance history |
| `content_analysis` | Content Analysis | Analyze available videos, scores, themes |
| `selection_reasoning` | Selection Reasoning | Apply AI reasoning to select content |
| `video_selection` | Video Selection | Final video selection with justifications |
| `schedule_generation` | Schedule Generation | Create 7-day schedule with times/platforms |
| `execution_phase` | Execution (Day 1-7) | Daily posting and monitoring |
| `reflection_phase` | Reflection (Day 7+) | Performance analysis and learnings |

### Experiments Steps

| step_key | Label | Description |
|----------|-------|-------------|
| `plan_experiments` | Plan Experiments | Identify experiment opportunities |
| `create_hypotheses` | Create Hypotheses | Generate testable hypotheses |
| `select_content` | Select Content | Choose content for testing |
| `generate_variants` | Build Variants | Create control/variant pairs |
| `schedule_variants` | Schedule Variants | Schedule tagged posts |
| `monitor_metrics` | Monitor Metrics | Collect performance data |
| `analyze_results` | Analyze Results | Statistical analysis |
| `winner_detection` | Winner Detection | Identify winners (p-value, lift) |
| `promote_to_narrative` | Promotion Pipeline | Promote winners to narrative |
| `update_patterns` | Patterns & Frameworks | Update learned patterns |

---

## 6. Event Types

| Event Type | Description |
|------------|-------------|
| `run.queued` | Run added to queue |
| `run.started` | Run execution started |
| `run.completed` | Run finished successfully |
| `run.failed` | Run failed with error |
| `step.started` | Step execution started |
| `step.completed` | Step finished |
| `thought.summary` | Short rationale/reasoning |
| `decision` | Chosen path + why |
| `action.performed` | What changed (selected/scheduled/tagged/promoted) |
| `tool.call.requested` | Tool invocation started |
| `tool.call.completed` | Tool invocation finished |
| `artifact.created` | Artifact generated |
| `metrics.snapshot` | Metrics captured |
| `warning` | Non-fatal issue |
| `error` | Error occurred |
| `retry.scheduled` | Retry scheduled |

---

## 7. Realtime Updates

On `/runs/[runId]`, the client subscribes to:
- `agent_runs` row changes (status/progress)
- `agent_steps` changes (step statuses)
- `agent_events` inserts (timeline stream)

This makes the UI a live "console" for both Narrative and Experiments systems.

---

## 8. Implementation Phases

### Phase 1: Database Schema
- Create agent_schedules, agent_runs, agent_steps, agent_events, agent_artifacts tables
- Add indexes for efficient querying
- Add foreign key relationships

### Phase 2: Topic & Step Registry
- Create topic registry JSON
- Create step registry JSON
- Update existing services to emit standardized events

### Phase 3: Backend Services
- Refactor NarrativePlannerService with step taxonomy
- Refactor ExperimentsScheduler with step taxonomy
- Add RunManagerService
- Add SchedulerService for cron-based execution

### Phase 4: Automation Center UI
- `/automation` route with tabs
- `/automation/narrative` control room
- `/automation/experiments` control room
- SystemHealthBar, RunsTable, ScheduleCard components

### Phase 5: Run Detail UI
- `/runs/[runId]` route
- StepsSidebar component
- TimelineStream component
- ArtifactsDrawer component
- Realtime subscriptions

### Phase 6: Integration
- Connect existing autonomous planners to new run system
- Migrate existing events to new schema
- Add Pub/Sub inspector page

---

## 9. Success Metrics

- [ ] Both agents run autonomously on schedule
- [ ] Live event streaming in UI (<1s latency)
- [ ] Step progress visible in real-time
- [ ] Artifacts downloadable from UI
- [ ] Pause/cancel/retry controls functional
- [ ] Service health visible at a glance
