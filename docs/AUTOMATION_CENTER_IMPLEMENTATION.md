# Automation Center Implementation Guide

## Overview

Implementation-ready specification for Next.js App Router + Supabase providing:
- Scheduled background runs for Narrative + Experiments
- Pub/Sub topics (services + topics)
- Agent Panels with live timeline of events + thought summaries + actions
- Automation Center UI + Run Detail UI with realtime streaming

---

## 1. Next.js Route Tree + Page Layouts (App Router)

```
app/
  (authed)/
    layout.tsx
    automation/
      page.tsx                      # Automation Center (tabs)
      narrative/
        page.tsx                    # Narrative Control Room
      experiments/
        page.tsx                    # Experiments Control Room
    runs/
      [runId]/
        page.tsx                    # Run Detail (Agent Panel)
    topics/
      page.tsx                      # Topic Inspector
    services/
      page.tsx                      # Service Health
  api/
    scheduler/
      tick/route.ts                 # cron calls this
    runs/
      [runId]/
        retry/route.ts
        cancel/route.ts
        pause/route.ts
        resume/route.ts
    schedules/
      [scheduleId]/
        run-now/route.ts
lib/
  supabase/
    client.ts                       # browser client
    server.ts                       # server client
  agents/
    topic-registry.ts               # typed topic list
    step-registry.ts                # typed step list
  hooks/
    useRunStream.ts                 # realtime hook
components/
  automation/
    AutomationCenter.tsx
    ControlRoomHeader.tsx
    ScheduleCard.tsx
    RunsTable.tsx
  runs/
    RunDetailPanel.tsx
    StepsSidebar.tsx
    TimelineStream.tsx
    EventRow.tsx
    ArtifactsDrawer.tsx
    RunControls.tsx
  topics/
    TopicInspector.tsx
```

### Minimal Page Stubs

```tsx
// app/(authed)/automation/page.tsx
import AutomationCenter from "@/components/automation/AutomationCenter";

export default function Page() {
  return <AutomationCenter />;
}

// app/(authed)/runs/[runId]/page.tsx
import RunDetailPanel from "@/components/runs/RunDetailPanel";

export default async function Page({ params }: { params: { runId: string } }) {
  return <RunDetailPanel runId={params.runId} />;
}
```

---

## 2. SQL DDL for agent_* Tables + Indexes + Basic RLS

```sql
-- =========================
-- ENUMS
-- =========================
DO $$ BEGIN
  CREATE TYPE agent_type AS ENUM ('narrative', 'experiments');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE run_status AS ENUM ('queued','running','succeeded','failed','canceled','paused');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE step_status AS ENUM ('queued','running','succeeded','failed','skipped');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =========================
-- SCHEDULES
-- =========================
CREATE TABLE IF NOT EXISTS agent_schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id),

  agent_type agent_type NOT NULL,
  topic text NOT NULL,                          -- e.g. narrative.weekly.generate_plan
  enabled boolean NOT NULL DEFAULT true,

  cron_expr text,                               -- optional
  interval_seconds int,                         -- optional
  next_run_at timestamptz,

  config_json jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT schedule_has_timing CHECK (
    (cron_expr IS NOT NULL)::int + (interval_seconds IS NOT NULL)::int >= 1
  )
);

CREATE INDEX IF NOT EXISTS idx_agent_schedules_due
  ON agent_schedules (enabled, next_run_at);

CREATE INDEX IF NOT EXISTS idx_agent_schedules_workspace
  ON agent_schedules (workspace_id, agent_type);

-- =========================
-- RUNS
-- =========================
CREATE TABLE IF NOT EXISTS agent_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id),
  schedule_id uuid REFERENCES agent_schedules(id),

  agent_type agent_type NOT NULL,
  status run_status NOT NULL DEFAULT 'queued',

  progress_current int NOT NULL DEFAULT 0,
  progress_total int NOT NULL DEFAULT 0,

  started_at timestamptz,
  finished_at timestamptz,
  last_heartbeat_at timestamptz,

  root_context_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_json jsonb,

  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_workspace_created
  ON agent_runs (workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_runs_status
  ON agent_runs (status, created_at DESC);

-- =========================
-- STEPS
-- =========================
CREATE TABLE IF NOT EXISTS agent_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,

  step_key text NOT NULL,
  step_name text NOT NULL,
  status step_status NOT NULL DEFAULT 'queued',

  started_at timestamptz,
  finished_at timestamptz,

  summary text,
  input_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  output_refs jsonb NOT NULL DEFAULT '[]'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT uniq_step_per_run UNIQUE (run_id, step_key)
);

CREATE INDEX IF NOT EXISTS idx_agent_steps_run
  ON agent_steps (run_id, created_at ASC);

-- =========================
-- EVENTS (TIMELINE)
-- =========================
CREATE TABLE IF NOT EXISTS agent_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  step_id uuid REFERENCES agent_steps(id) ON DELETE SET NULL,

  ts timestamptz NOT NULL DEFAULT now(),

  topic text NOT NULL,
  event_type text NOT NULL,
  severity text NOT NULL DEFAULT 'info',
  source_service text NOT NULL,

  message text NOT NULL,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_agent_events_run_ts
  ON agent_events (run_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_agent_events_topic_ts
  ON agent_events (topic, ts DESC);

-- =========================
-- ARTIFACTS
-- =========================
CREATE TABLE IF NOT EXISTS agent_artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,

  kind text NOT NULL,
  uri text NOT NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_artifacts_run
  ON agent_artifacts (run_id, created_at DESC);

-- =========================
-- UPDATED_AT trigger helper
-- =========================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_agent_schedules_updated_at ON agent_schedules;
CREATE TRIGGER trg_agent_schedules_updated_at
BEFORE UPDATE ON agent_schedules
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================
-- BASIC RLS
-- =========================
ALTER TABLE agent_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_artifacts ENABLE ROW LEVEL SECURITY;
```

---

## 3. Topic Registry + Step Registry (TypeScript)

### Topic Registry

```typescript
// lib/agents/topic-registry.ts

export const TOPICS = {
  // Shared
  RUN_REQUESTED: "shared.run.requested",
  RUN_QUEUED: "shared.run.queued",
  RUN_STARTED: "shared.run.started",
  RUN_COMPLETED: "shared.run.completed",
  RUN_FAILED: "shared.run.failed",

  STEP_STARTED: "shared.step.started",
  STEP_COMPLETED: "shared.step.completed",

  THOUGHT_SUMMARY: "shared.thought.summary",
  DECISION: "shared.decision",
  ACTION_PERFORMED: "shared.action.performed",

  TOOL_CALL_REQUESTED: "shared.tool.call.requested",
  TOOL_CALL_COMPLETED: "shared.tool.call.completed",

  METRICS_SNAPSHOT: "shared.metrics.snapshot",
  ARTIFACT_CREATED: "shared.artifact.created",

  // Narrative PRD
  NARRATIVE_WEEKLY_GENERATE_PLAN: "narrative.weekly.generate_plan",
  NARRATIVE_DAILY_EXECUTE_SCHEDULE: "narrative.daily.execute_schedule",
  NARRATIVE_WEEKLY_REFLECT: "narrative.weekly.reflect",

  // Experiments PRD
  EXPERIMENTS_WEEKLY_PLAN: "experiments.weekly.plan_experiments",
  EXPERIMENTS_DAILY_EXECUTE_VARIANTS: "experiments.daily.execute_variants",
  EXPERIMENTS_DAILY_ANALYZE_RESULTS: "experiments.daily.analyze_results",
  EXPERIMENTS_WINNER_DETECTION: "experiments.weekly.winner_detection",
  EXPERIMENTS_PROMOTE_TO_NARRATIVE: "experiments.weekly.promote_to_narrative",
} as const;

export type Topic = typeof TOPICS[keyof typeof TOPICS];

export const EVENT_TYPES = [
  "run.queued",
  "run.started",
  "run.completed",
  "run.failed",
  "step.started",
  "step.completed",
  "thought.summary",
  "decision",
  "action.performed",
  "tool.call.requested",
  "tool.call.completed",
  "metrics.snapshot",
  "artifact.created",
  "warning",
  "error",
  "retry.scheduled",
] as const;

export type EventType = typeof EVENT_TYPES[number];
```

### Step Registry

```typescript
// lib/agents/step-registry.ts

export const NARRATIVE_STEPS = [
  { key: "context_gathering", name: "Context Gathering" },
  { key: "content_analysis", name: "Content Analysis" },
  { key: "selection_reasoning", name: "Selection Reasoning" },
  { key: "video_selection", name: "Video Selection" },
  { key: "schedule_generation", name: "Schedule Generation" },
  { key: "execution_phase", name: "Execution (Day 1–7)" },
  { key: "reflection_phase", name: "Reflection (Day 7+)" },
] as const;

export const EXPERIMENTS_STEPS = [
  { key: "plan_experiments", name: "Plan Experiments" },
  { key: "create_hypotheses", name: "Create Hypotheses" },
  { key: "select_content", name: "Select Content" },
  { key: "generate_variants", name: "Build Variants" },
  { key: "schedule_variants", name: "Schedule Variants" },
  { key: "monitor_metrics", name: "Monitor Metrics" },
  { key: "analyze_results", name: "Analyze Results" },
  { key: "winner_detection", name: "Winner Detection" },
  { key: "promote_to_narrative", name: "Promotion Pipeline" },
  { key: "update_patterns", name: "Patterns & Frameworks" },
] as const;

export type NarrativeStepKey = typeof NARRATIVE_STEPS[number]["key"];
export type ExperimentsStepKey = typeof EXPERIMENTS_STEPS[number]["key"];
```

---

## 4. Realtime Hook: useRunStream(runId)

```typescript
// lib/hooks/useRunStream.ts
"use client";

import { useEffect, useMemo, useState } from "react";
import { supabaseBrowser } from "@/lib/supabase/client";

type AgentRun = {
  id: string;
  status: string;
  progress_current: number;
  progress_total: number;
  started_at: string | null;
  finished_at: string | null;
  last_heartbeat_at: string | null;
  agent_type: "narrative" | "experiments";
  root_context_json: any;
};

type AgentStep = {
  id: string;
  run_id: string;
  step_key: string;
  step_name: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  summary: string | null;
};

type AgentEvent = {
  id: string;
  run_id: string;
  step_id: string | null;
  ts: string;
  topic: string;
  event_type: string;
  severity: string;
  source_service: string;
  message: string;
  payload_json: any;
};

export function useRunStream(runId: string) {
  const supabase = useMemo(() => supabaseBrowser(), []);

  const [run, setRun] = useState<AgentRun | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function bootstrap() {
      setLoading(true);

      const [{ data: runRow }, { data: stepRows }, { data: eventRows }] =
        await Promise.all([
          supabase.from("agent_runs").select("*").eq("id", runId).single(),
          supabase.from("agent_steps").select("*").eq("run_id", runId).order("created_at", { ascending: true }),
          supabase.from("agent_events").select("*").eq("run_id", runId).order("ts", { ascending: false }).limit(250),
        ]);

      if (!isMounted) return;

      setRun(runRow ?? null);
      setSteps(stepRows ?? []);
      setEvents(eventRows ?? []);
      setLoading(false);
    }

    bootstrap();

    const channel = supabase
      .channel(`run-stream:${runId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "agent_runs", filter: `id=eq.${runId}` },
        (payload) => {
          const next = payload.new as AgentRun;
          setRun(next);
        }
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "agent_steps", filter: `run_id=eq.${runId}` },
        (payload) => {
          const next = payload.new as AgentStep;
          setSteps((prev) => {
            const idx = prev.findIndex((s) => s.id === next.id);
            if (idx === -1) return [...prev, next];
            const copy = [...prev];
            copy[idx] = next;
            return copy;
          });
        }
      )
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "agent_events", filter: `run_id=eq.${runId}` },
        (payload) => {
          const next = payload.new as AgentEvent;
          setEvents((prev) => [next, ...prev]);
        }
      )
      .subscribe();

    return () => {
      isMounted = false;
      supabase.removeChannel(channel);
    };
  }, [runId, supabase]);

  return { run, steps, events, loading };
}
```

---

## 5. Run Detail UI (Agent Panel)

See `/dashboard/app/(dashboard)/runs/[runId]/page.tsx` for full implementation including:
- StepsSidebar with step status and summaries
- TimelineStream with event filtering (thoughts, actions, tools, errors)
- EventRow with expandable payload
- RunControls (pause/cancel/retry)
- ArtifactsDrawer

---

## 6. Automation Center UI

See `/dashboard/app/(dashboard)/automation/page.tsx` for full implementation including:
- Agent type tabs (Narrative | Experiments)
- System health bar
- Schedule cards with enable/disable and run-now
- Runs table with status, progress, duration
- Links to run detail panels

---

## 7. API Route Handlers

### Scheduler Tick (Cron)

```typescript
// app/api/scheduler/tick/route.ts
import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

export async function POST() {
  const supabase = createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  // Find due schedules
  const { data: dueSchedules } = await supabase
    .from("agent_schedules")
    .select("*")
    .eq("enabled", true)
    .lte("next_run_at", new Date().toISOString());

  for (const schedule of dueSchedules ?? []) {
    // Create run
    await supabase.from("agent_runs").insert({
      workspace_id: schedule.workspace_id,
      schedule_id: schedule.id,
      agent_type: schedule.agent_type,
      status: "queued",
      root_context_json: schedule.config_json,
    });

    // Update next_run_at
    const nextRun = new Date(Date.now() + (schedule.interval_seconds ?? 3600) * 1000);
    await supabase
      .from("agent_schedules")
      .update({ next_run_at: nextRun.toISOString() })
      .eq("id", schedule.id);
  }

  return NextResponse.json({ processed: dueSchedules?.length ?? 0 });
}
```

### Run Control Routes

```typescript
// app/api/runs/[runId]/pause/route.ts
export async function POST(req: Request, { params }: { params: { runId: string } }) {
  // Update run status to 'paused'
}

// app/api/runs/[runId]/resume/route.ts
export async function POST(req: Request, { params }: { params: { runId: string } }) {
  // Update run status to 'running'
}

// app/api/runs/[runId]/cancel/route.ts
export async function POST(req: Request, { params }: { params: { runId: string } }) {
  // Update run status to 'canceled', set finished_at
}

// app/api/runs/[runId]/retry/route.ts
export async function POST(req: Request, { params }: { params: { runId: string } }) {
  // Create new run with same context
}
```

### Schedule Run Now

```typescript
// app/api/schedules/[scheduleId]/run-now/route.ts
export async function POST(req: Request, { params }: { params: { scheduleId: string } }) {
  // Create immediate run from schedule config
}
```

---

## 8. Implementation Phases

### Phase 1: Database & Registries ✅
- SQL schema with enums, tables, indexes
- Topic registry TypeScript
- Step registry TypeScript

### Phase 2: Backend Services
- RunManager service
- Event emission helpers
- Artifact storage

### Phase 3: API Routes
- Scheduler tick endpoint
- Run control endpoints (pause/resume/cancel/retry)
- Schedule run-now endpoint

### Phase 4: Realtime Hook
- useRunStream with Supabase realtime
- Run/steps/events streaming

### Phase 5: UI Components
- Automation Center page
- Run Detail (Agent Panel) page
- StepsSidebar, TimelineStream, EventRow
- RunControls, ArtifactsDrawer

### Phase 6: Integration
- Connect to existing autonomous planners
- Wire up services to emit events
- Add realtime subscriptions to UI

---

## Success Criteria

- [ ] Schedules trigger runs automatically
- [ ] Runs stream progress in real-time
- [ ] Steps show status and summaries
- [ ] Events filterable by type (thoughts/actions/tools/errors)
- [ ] Artifacts viewable/downloadable
- [ ] Pause/cancel/retry controls work
- [ ] Both Narrative and Experiments agents integrated
