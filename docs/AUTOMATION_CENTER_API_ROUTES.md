# Automation Center API Routes Implementation

## Overview

API route implementations + dispatcher for end-to-end Scheduler → Topics → Services → Agent Panels loop.

**Stack:**
- Next.js App Router
- Supabase (server client with service role)
- DB-backed queue (can swap to pgmq later)

---

## 1. Server Supabase Client (Service Role)

```typescript
// lib/supabase/server.ts
import { createClient } from "@supabase/supabase-js";

export function supabaseService() {
  // Service role ONLY on server (never expose to client)
  return createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } }
  );
}
```

### Environment Variables

```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

---

## 2. Queue Table (Simple DB Queue)

### SQL Schema

```sql
CREATE TABLE IF NOT EXISTS agent_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id),

  topic text NOT NULL,
  run_id uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,

  status text NOT NULL DEFAULT 'queued', -- queued|processing|done|failed
  attempts int NOT NULL DEFAULT 0,

  available_at timestamptz NOT NULL DEFAULT now(),
  locked_at timestamptz,
  locked_by text,
  last_error text,

  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_queue_available
  ON agent_queue (status, available_at);

CREATE INDEX IF NOT EXISTS idx_agent_queue_topic
  ON agent_queue (topic, created_at DESC);
```

### Queue Helper

```typescript
// lib/agents/queue.ts
import { supabaseService } from "@/lib/supabase/server";

export async function enqueueRun({
  workspaceId,
  runId,
  topic,
  payload,
}: {
  workspaceId: string;
  runId: string;
  topic: string;
  payload?: any;
}) {
  const supabase = supabaseService();
  const { error } = await supabase.from("agent_queue").insert({
    workspace_id: workspaceId,
    run_id: runId,
    topic,
    payload_json: payload ?? {},
  });
  if (error) throw error;
}
```

---

## 3. Event Writer (Single Function for All Services)

```typescript
// lib/agents/events.ts
import { supabaseService } from "@/lib/supabase/server";

export async function emitEvent({
  runId,
  stepId,
  topic,
  eventType,
  severity = "info",
  sourceService,
  message,
  payload,
}: {
  runId: string;
  stepId?: string | null;
  topic: string;
  eventType: string;
  severity?: "info" | "warn" | "error";
  sourceService: string;
  message: string;
  payload?: any;
}) {
  const supabase = supabaseService();
  const { error } = await supabase.from("agent_events").insert({
    run_id: runId,
    step_id: stepId ?? null,
    topic,
    event_type: eventType,
    severity,
    source_service: sourceService,
    message,
    payload_json: payload ?? {},
  });
  if (error) throw error;
}

export async function setRunStatus(runId: string, patch: any) {
  const supabase = supabaseService();
  const { error } = await supabase.from("agent_runs").update(patch).eq("id", runId);
  if (error) throw error;
}

export async function upsertStep({
  runId,
  stepKey,
  stepName,
  status,
  summary,
}: {
  runId: string;
  stepKey: string;
  stepName: string;
  status: string;
  summary?: string | null;
}) {
  const supabase = supabaseService();
  const { data, error } = await supabase
    .from("agent_steps")
    .upsert(
      {
        run_id: runId,
        step_key: stepKey,
        step_name: stepName,
        status,
        ...(summary ? { summary } : {}),
        ...(status === "running" ? { started_at: new Date().toISOString() } : {}),
        ...(status === "succeeded" || status === "failed" ? { finished_at: new Date().toISOString() } : {}),
      },
      { onConflict: "run_id,step_key" }
    )
    .select("*")
    .single();

  if (error) throw error;
  return data;
}
```

---

## 4. Scheduler Tick Endpoint (Cron Calls This)

```typescript
// app/api/scheduler/tick/route.ts
import { NextResponse } from "next/server";
import { supabaseService } from "@/lib/supabase/server";
import { enqueueRun } from "@/lib/agents/queue";
import { emitEvent } from "@/lib/agents/events";
import { TOPICS } from "@/lib/agents/topic-registry";

export const runtime = "nodejs";

export async function POST() {
  const supabase = supabaseService();

  // 1) Find due schedules
  const nowIso = new Date().toISOString();
  const { data: schedules, error } = await supabase
    .from("agent_schedules")
    .select("*")
    .eq("enabled", true)
    .lte("next_run_at", nowIso)
    .limit(50);

  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  if (!schedules || schedules.length === 0) return NextResponse.json({ ok: true, created: 0 });

  let created = 0;

  for (const s of schedules) {
    // 2) Create run
    const { data: run, error: runErr } = await supabase
      .from("agent_runs")
      .insert({
        workspace_id: s.workspace_id,
        schedule_id: s.id,
        agent_type: s.agent_type,
        status: "queued",
        progress_current: 0,
        progress_total: 100,
        root_context_json: s.config_json ?? {},
      })
      .select("*")
      .single();

    if (runErr) continue;
    created++;

    // 3) Emit queued event
    await emitEvent({
      runId: run.id,
      topic: TOPICS.RUN_QUEUED,
      eventType: "run.queued",
      sourceService: "SchedulerService",
      message: `Run queued for topic: ${s.topic}`,
      payload: { schedule_id: s.id, trigger_topic: s.topic },
    });

    // 4) Enqueue to queue
    await enqueueRun({
      workspaceId: s.workspace_id,
      runId: run.id,
      topic: s.topic,
      payload: { schedule_id: s.id, config: s.config_json ?? {} },
    });

    // 5) Update next_run_at
    if (s.interval_seconds) {
      const next = new Date(Date.now() + s.interval_seconds * 1000).toISOString();
      await supabase.from("agent_schedules").update({ next_run_at: next }).eq("id", s.id);
    }
  }

  return NextResponse.json({ ok: true, created });
}
```

---

## 5. Worker Process Endpoint

```typescript
// app/api/worker/process/route.ts
import { NextResponse } from "next/server";
import { supabaseService } from "@/lib/supabase/server";
import { dispatchTopic } from "@/lib/agents/dispatcher";
import { emitEvent, setRunStatus } from "@/lib/agents/events";
import { TOPICS } from "@/lib/agents/topic-registry";

export const runtime = "nodejs";

export async function POST() {
  const supabase = supabaseService();

  // 1) Pull queued jobs
  const { data: jobs, error } = await supabase
    .from("agent_queue")
    .select("*")
    .eq("status", "queued")
    .lte("available_at", new Date().toISOString())
    .order("created_at", { ascending: true })
    .limit(5);

  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
  if (!jobs || jobs.length === 0) return NextResponse.json({ ok: true, processed: 0 });

  let processed = 0;

  for (const job of jobs) {
    // 2) Lock job
    const { error: lockErr } = await supabase
      .from("agent_queue")
      .update({ status: "processing", locked_at: new Date().toISOString(), locked_by: "api_worker" })
      .eq("id", job.id)
      .eq("status", "queued");

    if (lockErr) continue;
    processed++;

    // 3) Mark run started
    await setRunStatus(job.run_id, { 
      status: "running", 
      started_at: new Date().toISOString(), 
      last_heartbeat_at: new Date().toISOString() 
    });
    
    await emitEvent({
      runId: job.run_id,
      topic: TOPICS.RUN_STARTED,
      eventType: "run.started",
      sourceService: "RunManagerService",
      message: `Run started for topic: ${job.topic}`,
      payload: { job_id: job.id },
    });

    try {
      // 4) Dispatch to service
      await dispatchTopic({
        topic: job.topic,
        runId: job.run_id,
        payload: job.payload_json ?? {},
      });

      // 5) Complete
      await supabase.from("agent_queue").update({ status: "done" }).eq("id", job.id);
      await setRunStatus(job.run_id, { status: "succeeded", finished_at: new Date().toISOString() });
      
      await emitEvent({
        runId: job.run_id,
        topic: TOPICS.RUN_COMPLETED,
        eventType: "run.completed",
        sourceService: "RunManagerService",
        message: "Run completed successfully",
      });
    } catch (e: any) {
      await supabase.from("agent_queue").update({ 
        status: "failed", 
        last_error: String(e?.message ?? e) 
      }).eq("id", job.id);
      
      await setRunStatus(job.run_id, { 
        status: "failed", 
        finished_at: new Date().toISOString(), 
        error_json: { message: String(e?.message ?? e) } 
      });

      await emitEvent({
        runId: job.run_id,
        topic: TOPICS.RUN_FAILED,
        eventType: "run.failed",
        severity: "error",
        sourceService: "RunManagerService",
        message: "Run failed",
        payload: { error: String(e?.message ?? e) },
      });
    }
  }

  return NextResponse.json({ ok: true, processed });
}
```

---

## 6. Dispatcher + Service Handlers

### Dispatcher

```typescript
// lib/agents/dispatcher.ts
import { TOPICS } from "@/lib/agents/topic-registry";
import { runNarrativeGeneratePlan, runNarrativeReflect } from "@/lib/agents/services/narrative";
import { runExperimentsPlan, runExperimentsAnalyze, runExperimentsPromote } from "@/lib/agents/services/experiments";

export async function dispatchTopic({
  topic,
  runId,
  payload,
}: {
  topic: string;
  runId: string;
  payload: any;
}) {
  switch (topic) {
    // Narrative PRD
    case TOPICS.NARRATIVE_WEEKLY_GENERATE_PLAN:
      return runNarrativeGeneratePlan(runId, payload);

    case TOPICS.NARRATIVE_WEEKLY_REFLECT:
      return runNarrativeReflect(runId, payload);

    // Experiments PRD
    case TOPICS.EXPERIMENTS_WEEKLY_PLAN:
      return runExperimentsPlan(runId, payload);

    case TOPICS.EXPERIMENTS_DAILY_ANALYZE_RESULTS:
      return runExperimentsAnalyze(runId, payload);

    case TOPICS.EXPERIMENTS_PROMOTE_TO_NARRATIVE:
      return runExperimentsPromote(runId, payload);

    default:
      throw new Error(`No handler for topic: ${topic}`);
  }
}
```

### Narrative Service Handler

```typescript
// lib/agents/services/narrative.ts
import { TOPICS } from "@/lib/agents/topic-registry";
import { emitEvent, upsertStep, setRunStatus } from "@/lib/agents/events";

export async function runNarrativeGeneratePlan(runId: string, payload: any) {
  const svc = "NarrativePlannerService";

  // Step 1: Context Gathering
  const s1 = await upsertStep({ runId, stepKey: "context_gathering", stepName: "Context Gathering", status: "running" });
  await emitEvent({
    runId,
    stepId: s1.id,
    topic: TOPICS.THOUGHT_SUMMARY,
    eventType: "thought.summary",
    sourceService: svc,
    message: "Goal is to optimize for the primary CTA while keeping pillar mix within constraints.",
  });
  await upsertStep({ runId, stepKey: "context_gathering", stepName: "Context Gathering", status: "succeeded", summary: "Context loaded." });

  // Step 2: Content Analysis
  const s2 = await upsertStep({ runId, stepKey: "content_analysis", stepName: "Content Analysis", status: "running" });
  await emitEvent({
    runId,
    stepId: s2.id,
    topic: TOPICS.ACTION_PERFORMED,
    eventType: "action.performed",
    sourceService: svc,
    message: "Analyzing available videos against pillars and score thresholds",
    payload: { analyzed_videos: 122, available_videos: 400 },
  });
  await upsertStep({ runId, stepKey: "content_analysis", stepName: "Content Analysis", status: "succeeded", summary: "Content analyzed." });

  // Step 3: Selection Reasoning
  const s3 = await upsertStep({ runId, stepKey: "selection_reasoning", stepName: "Selection Reasoning", status: "running" });
  await emitEvent({
    runId,
    stepId: s3.id,
    topic: TOPICS.DECISION,
    eventType: "decision",
    sourceService: svc,
    message: "Increasing Process/How-To allocation; tightening Pain Points quality threshold.",
  });
  await upsertStep({ runId, stepKey: "selection_reasoning", stepName: "Selection Reasoning", status: "succeeded", summary: "Pillar mix adjusted." });

  // Step 4: Video Selection
  const s4 = await upsertStep({ runId, stepKey: "video_selection", stepName: "Video Selection", status: "running" });
  await emitEvent({
    runId,
    stepId: s4.id,
    topic: TOPICS.ACTION_PERFORMED,
    eventType: "action.performed",
    sourceService: svc,
    message: "Selected 14 videos (2/day)",
    payload: { selected: 14 },
  });
  await upsertStep({ runId, stepKey: "video_selection", stepName: "Video Selection", status: "succeeded", summary: "Videos selected." });

  // Step 5: Schedule Generation
  const s5 = await upsertStep({ runId, stepKey: "schedule_generation", stepName: "Schedule Generation", status: "running" });
  await emitEvent({
    runId,
    stepId: s5.id,
    topic: TOPICS.ARTIFACT_CREATED,
    eventType: "artifact.created",
    sourceService: svc,
    message: "Created weekly_schedule.json + rejection_log.json",
    payload: { artifacts: ["weekly_schedule.json", "rejection_log.json"] },
  });
  await upsertStep({ runId, stepKey: "schedule_generation", stepName: "Schedule Generation", status: "succeeded", summary: "Schedule generated." });

  await setRunStatus(runId, { progress_current: 100, last_heartbeat_at: new Date().toISOString() });
}

export async function runNarrativeReflect(runId: string, payload: any) {
  const svc = "NarrativeReflectionService";
  
  const s = await upsertStep({ runId, stepKey: "reflection_phase", stepName: "Reflection (Day 7+)", status: "running" });

  await emitEvent({
    runId,
    stepId: s.id,
    topic: TOPICS.METRICS_SNAPSHOT,
    eventType: "metrics.snapshot",
    sourceService: svc,
    message: "Aggregated performance for the week",
  });

  await emitEvent({
    runId,
    stepId: s.id,
    topic: TOPICS.DECISION,
    eventType: "decision",
    sourceService: svc,
    message: "Applying learnings: shorter clips prioritized",
  });

  await upsertStep({ runId, stepKey: "reflection_phase", stepName: "Reflection (Day 7+)", status: "succeeded", summary: "Reflection complete." });
  await setRunStatus(runId, { progress_current: 100, last_heartbeat_at: new Date().toISOString() });
}
```

### Experiments Service Handler

```typescript
// lib/agents/services/experiments.ts
import { TOPICS } from "@/lib/agents/topic-registry";
import { emitEvent, upsertStep, setRunStatus } from "@/lib/agents/events";

export async function runExperimentsPlan(runId: string, payload: any) {
  const svc = "ExperimentsPlannerService";

  const s1 = await upsertStep({ runId, stepKey: "plan_experiments", stepName: "Plan Experiments", status: "running" });
  await emitEvent({
    runId,
    stepId: s1.id,
    topic: TOPICS.THOUGHT_SUMMARY,
    eventType: "thought.summary",
    sourceService: svc,
    message: "Selecting hypotheses that test high-leverage variables (hook, timing, caption)",
  });
  await upsertStep({ runId, stepKey: "plan_experiments", stepName: "Plan Experiments", status: "succeeded", summary: "Experiment plan created." });

  const s2 = await upsertStep({ runId, stepKey: "create_hypotheses", stepName: "Create Hypotheses", status: "running" });
  await emitEvent({
    runId,
    stepId: s2.id,
    topic: TOPICS.ACTION_PERFORMED,
    eventType: "action.performed",
    sourceService: svc,
    message: "Created 3 hypotheses (question-hook, 6pm timing, CTA placement)",
    payload: { hypotheses_created: 3 },
  });
  await upsertStep({ runId, stepKey: "create_hypotheses", stepName: "Create Hypotheses", status: "succeeded", summary: "Hypotheses created." });

  const s3 = await upsertStep({ runId, stepKey: "generate_variants", stepName: "Build Variants", status: "running" });
  await emitEvent({
    runId,
    stepId: s3.id,
    topic: TOPICS.TOOL_CALL_REQUESTED,
    eventType: "tool.call.requested",
    sourceService: "VariantsBuilderService",
    message: "Generating hook variants and captions for A/B run",
  });
  await upsertStep({ runId, stepKey: "generate_variants", stepName: "Build Variants", status: "succeeded", summary: "Variants generated." });

  const s4 = await upsertStep({ runId, stepKey: "schedule_variants", stepName: "Schedule Variants", status: "running" });
  await emitEvent({
    runId,
    stepId: s4.id,
    topic: TOPICS.ACTION_PERFORMED,
    eventType: "action.performed",
    sourceService: "ExperimentsExecutorService",
    message: "Scheduled 10 posts (5 control, 5 variant_a) with origin tagging",
    payload: { posts: 10, variants: ["control", "variant_a"] },
  });
  await upsertStep({ runId, stepKey: "schedule_variants", stepName: "Schedule Variants", status: "succeeded", summary: "Variants scheduled." });

  await setRunStatus(runId, { progress_current: 100, last_heartbeat_at: new Date().toISOString() });
}

export async function runExperimentsAnalyze(runId: string, payload: any) {
  const svc = "ExperimentsAnalyzerService";
  
  const s = await upsertStep({ runId, stepKey: "analyze_results", stepName: "Analyze Results", status: "running" });

  await emitEvent({
    runId,
    stepId: s.id,
    topic: TOPICS.METRICS_SNAPSHOT,
    eventType: "metrics.snapshot",
    sourceService: svc,
    message: "Comparing control vs variant performance",
  });

  await emitEvent({
    runId,
    stepId: s.id,
    topic: TOPICS.DECISION,
    eventType: "decision",
    sourceService: svc,
    message: "Hypothesis passed: question-hook variant shows +52% lift; confidence 0.81.",
    payload: { lift: 0.52, confidence: 0.81, status: "passed" },
  });

  await upsertStep({ runId, stepKey: "analyze_results", stepName: "Analyze Results", status: "succeeded", summary: "Results computed." });
  await setRunStatus(runId, { progress_current: 100, last_heartbeat_at: new Date().toISOString() });
}

export async function runExperimentsPromote(runId: string, payload: any) {
  const svc = "WinnerDetectionService";
  
  const s = await upsertStep({ runId, stepKey: "promote_to_narrative", stepName: "Promotion Pipeline", status: "running" });

  await emitEvent({
    runId,
    stepId: s.id,
    topic: TOPICS.ACTION_PERFORMED,
    eventType: "action.performed",
    sourceService: svc,
    message: "Promoted winner_candidate to Narrative Builder queue",
    payload: { promoted_count: 1 },
  });

  await upsertStep({ runId, stepKey: "promote_to_narrative", stepName: "Promotion Pipeline", status: "succeeded", summary: "Promotion complete." });
  await setRunStatus(runId, { progress_current: 100, last_heartbeat_at: new Date().toISOString() });
}
```

---

## 7. Run Control Endpoints

### Pause

```typescript
// app/api/runs/[runId]/pause/route.ts
import { NextResponse } from "next/server";
import { supabaseService } from "@/lib/supabase/server";
import { emitEvent } from "@/lib/agents/events";
import { TOPICS } from "@/lib/agents/topic-registry";

export async function POST(_: Request, { params }: { params: { runId: string } }) {
  const supabase = supabaseService();
  await supabase.from("agent_runs").update({ status: "paused" }).eq("id", params.runId);

  await emitEvent({
    runId: params.runId,
    topic: TOPICS.DECISION,
    eventType: "decision",
    sourceService: "RunControl",
    message: "Run paused by user",
  });

  return NextResponse.json({ ok: true });
}
```

### Resume

```typescript
// app/api/runs/[runId]/resume/route.ts
export async function POST(_: Request, { params }: { params: { runId: string } }) {
  const supabase = supabaseService();
  await supabase.from("agent_runs").update({ 
    status: "running", 
    last_heartbeat_at: new Date().toISOString() 
  }).eq("id", params.runId);

  await emitEvent({
    runId: params.runId,
    topic: TOPICS.DECISION,
    eventType: "decision",
    sourceService: "RunControl",
    message: "Run resumed by user",
  });

  return NextResponse.json({ ok: true });
}
```

### Cancel

```typescript
// app/api/runs/[runId]/cancel/route.ts
export async function POST(_: Request, { params }: { params: { runId: string } }) {
  const supabase = supabaseService();
  await supabase.from("agent_runs").update({ 
    status: "canceled", 
    finished_at: new Date().toISOString() 
  }).eq("id", params.runId);

  await emitEvent({
    runId: params.runId,
    topic: TOPICS.RUN_FAILED,
    eventType: "run.failed",
    severity: "warn",
    sourceService: "RunControl",
    message: "Run canceled by user",
  });

  return NextResponse.json({ ok: true });
}
```

### Retry

```typescript
// app/api/runs/[runId]/retry/route.ts
export async function POST(_: Request, { params }: { params: { runId: string } }) {
  const supabase = supabaseService();

  const { data: run } = await supabase.from("agent_runs").select("*").eq("id", params.runId).single();
  if (!run) return NextResponse.json({ ok: false, error: "Run not found" }, { status: 404 });

  const { data: sched } = run.schedule_id
    ? await supabase.from("agent_schedules").select("*").eq("id", run.schedule_id).single()
    : { data: null };

  const topic = sched?.topic ?? run.root_context_json?.topic ?? TOPICS.RUN_REQUESTED;

  await supabase.from("agent_runs").update({ 
    status: "queued", 
    started_at: null, 
    finished_at: null, 
    error_json: null 
  }).eq("id", params.runId);

  await emitEvent({
    runId: params.runId,
    topic: TOPICS.RUN_QUEUED,
    eventType: "run.queued",
    sourceService: "RunControl",
    message: "Run retried by user",
    payload: { retry_topic: topic },
  });

  await enqueueRun({ 
    workspaceId: run.workspace_id, 
    runId: params.runId, 
    topic, 
    payload: run.root_context_json ?? {} 
  });

  return NextResponse.json({ ok: true });
}
```

---

## Summary

| Component | What It Does |
|-----------|--------------|
| Scheduler tick | Creates runs from due schedules |
| Worker process | Consumes queue, dispatches by topic |
| Dispatcher | Routes topics to service handlers |
| Services | Write step + event timeline entries |
| UI panels | Stream events live via polling/realtime |

---

## Cron Setup Options

### Vercel Cron
```json
// vercel.json
{
  "crons": [
    { "path": "/api/scheduler/tick", "schedule": "* * * * *" },
    { "path": "/api/worker/process", "schedule": "* * * * *" }
  ]
}
```

### Supabase Cron
```sql
SELECT cron.schedule('scheduler-tick', '* * * * *', $$
  SELECT net.http_post('https://your-app.vercel.app/api/scheduler/tick', '{}', '{"Content-Type": "application/json"}');
$$);
```
