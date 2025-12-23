# Narrative Builder & Experiments Architecture PRD

> **Version**: 1.0  
> **Date**: December 22, 2025  
> **Status**: Planning  

---

## Executive Summary

This document defines the architecture for two complementary decision systems:

| System | Purpose | Account Scope |
|--------|---------|---------------|
| **Narrative Builder** | Mainline production system for primary brand accounts | `MAINLINE` |
| **Experiments** | Research sandbox using sister accounts for A/B testing | `EXPERIMENT_ARM` |

**Key Principle**: Two brains, one body. Both systems share the same hydration model and execution pipeline, but have separate goals, policies, and decision logic.

---

## 1. Core Architecture

### 1.1 Shared Foundation

```
┌─────────────────────────────────────────────────────────────────┐
│                     SHARED FOUNDATION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  Hydration Model │    │  Decision Engine │                   │
│  │  (State Layer)   │───▶│   Interface      │                   │
│  └──────────────────┘    └────────┬─────────┘                   │
│                                   │                              │
│              ┌────────────────────┼────────────────────┐        │
│              ▼                    ▼                    ▼        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Narrative Policy │  │ Experiments      │  │ Future       │  │
│  │ (MAINLINE)       │  │ Policy (EXP_ARM) │  │ Policies...  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────────┘  │
│           │                     │                               │
│           └──────────┬──────────┘                               │
│                      ▼                                          │
│           ┌──────────────────┐                                  │
│           │ Scheduler/       │                                  │
│           │ Publisher        │                                  │
│           │ (Single Pipe)    │                                  │
│           └──────────────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Responsibilities

#### A) Hydration Model (Source of Truth)

A unified "state" layer computed from:
- **Content Library**: assets, transcripts, tags, variants, fatigue history
- **Platform Metrics**: views, retention, saves, comments, follows
- **Audience Signals**: sentiment, reply velocity, topic resonance
- **Operational Signals**: posting failures, rate limits, API lag

Produces feature vectors and "current state" snapshots for decision engines.

#### B) Decision Engine Interface (Pluggable)

Both Narrative and Experiments are policy modules that implement:

```typescript
interface DecisionEngine {
  choose_next_actions(
    state: HydrationSnapshot,
    goals: Goal[],
    constraints: Constraint[]
  ): ScheduledAction[];
}
```

#### C) Scheduler/Publisher (Single Execution Pipe)

One pipeline handles:
- Schedule creation
- Publish via 3rd-party (Blotato)
- Post ID reconciliation
- Metrics polling / webhooks
- State updates back into hydration

---

## 2. Account Roles & Grouping

### 2.1 Data Model

```
Workspace
└── AccountGroup (e.g., "Isaiah Main Brand")
    ├── SocialAccount (IG @the_isaiah_dupree)
    │   └── AccountRole: MAINLINE
    ├── SocialAccount (TikTok @the_isaiah_dupree)
    │   └── AccountRole: MAINLINE
    ├── SocialAccount (IG @isaiah_experiments)
    │   └── AccountRole: EXPERIMENT_ARM
    └── SocialAccount (TikTok @test_account)
        └── AccountRole: EXPERIMENT_ARM
```

### 2.2 Account Roles

| Role | Description | Controlled By |
|------|-------------|---------------|
| `MAINLINE` | Primary brand accounts | Narrative Builder |
| `EXPERIMENT_ARM` | Sister accounts for testing | Experiments |
| `ARCHIVE` | Retired/paused accounts | Manual only |
| `SEED` | New accounts being grown | Either |

### 2.3 Guardrails

**Critical Rule**: 
- Narrative Builder **only** controls `MAINLINE` accounts
- Experiments **only** controls `EXPERIMENT_ARM` accounts
- Cross-posting blocked at scheduler validation

---

## 3. Narrative Builder Policy (Mainline)

### 3.1 Goal
Maximize long-term brand outcome: coherence + growth + offer conversion.

### 3.2 Inputs
- Hydration state (content performance + fatigue + topic coverage)
- Narrative goal graph (campaign, series, funnel stage)
- Constraints (cadence, platform mix, "don't repeat topic within N days")
- **Knowledge Base rules** (learnings from Experiments)

### 3.3 Output
- Content sequence + next post choices for `MAINLINE`
- Scheduling decisions optimized for:
  - Storyline progression
  - Topic rotation + novelty
  - Sustained engagement (not just spikes)

### 3.4 Objective Function
```
maximize: brand_progress_score
subject to:
  - fatigue_constraints
  - cadence_limits
  - platform_coverage_targets
```

### 3.5 UI Features
- Goal/story stage visualization
- Recommended next posts
- "Powered by learnings from experiments" indicator
- 7-day lookahead plan

---

## 4. Experiments Policy (Sister Accounts)

### 4.1 Goal
Discover causal rules and best practices fast.

### 4.2 Inputs
- Hydration state (filtered for experiment arms + test periods)
- Experiment plan (hypotheses, variables, sample size, success metric)
- Constraints (fairness controls: same time buckets, similar topics)

### 4.3 Output
- Variant schedules for `EXPERIMENT_ARM` accounts
- Decisions optimized for:
  - Isolating variables (A/B/C)
  - Speed to signal
  - Statistical confidence thresholds

### 4.4 Objective Function
```
maximize: information_gain + lift_on_metric
subject to:
  - fair_exposure
  - cooldown_periods
  - anti_cannibalization
```

### 4.5 UI Features
- Active tests dashboard
- Sister account assignment
- Fairness controls visualization
- Learnings produced (rules)
- Confidence meters

---

## 5. Three-Layer Metrics Architecture

### 5.1 Layer 1: Raw Metrics (Per Account, Per Post)
**Never merge these across accounts.**

```typescript
interface RawMetrics {
  post_id: string;
  account_id: string;
  platform: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  retention_curve: number[];
  timestamp: Date;
}
```

### 5.2 Layer 2: Normalized Signals (Per Platform)
Comparable measures across accounts:

```typescript
interface NormalizedSignals {
  account_id: string;
  platform: string;
  saves_per_1k_views: number;
  comments_per_1k_views: number;
  retention_normalized: number[];
  early_velocity_score: number; // first 30-120 min
  engagement_rate: number;
}
```

### 5.3 Layer 3: Learnings (Global Knowledge Base)
What experiments produce and narrative consumes:

```typescript
interface Learning {
  id: string;
  rule_type: 'hook' | 'format' | 'timing' | 'caption' | 'cta';
  conditions: {
    platform?: string;
    niche?: string;
    format?: string;
    length_range?: [number, number];
  };
  recommendation: string;
  expected_lift: number;
  confidence: number;
  sample_size: number;
  last_validated: Date;
  source_experiment_ids: string[];
}
```

### 5.4 Guardrail
- **Narrative decisions never optimize on sister-account vanity totals**
- They optimize on learned rules + main account data

---

## 6. Knowledge Base Contract

Experiments produce "policies as data" for Narrative Builder to consume.

### 6.1 Rule Objects

```typescript
interface Rule {
  id: string;
  conditions: {
    platform: string[];
    niche: string[];
    format: string[];
    hook_type?: string;
    length_range?: [number, number];
  };
  recommendation: string;
  expected_lift: number;
  confidence: number;
  last_validated: Date;
  experiment_id: string;
}
```

### 6.2 Template Objects

```typescript
interface Template {
  id: string;
  type: 'hook' | 'caption' | 'cta';
  content: string;
  variables: string[];
  performance_score: number;
  usage_count: number;
}
```

### 6.3 Constraint Objects

```typescript
interface Constraint {
  id: string;
  type: 'fatigue' | 'cooldown' | 'frequency';
  scope: 'platform' | 'topic' | 'format';
  threshold: number;
  window_days: number;
}
```

### 6.4 Playbook Objects

```typescript
interface Playbook {
  id: string;
  name: string;
  description: string;
  rules: Rule[];
  templates: Template[];
  constraints: Constraint[];
  use_case: 'launch_week' | 'evergreen' | 'viral_response';
}
```

---

## 7. Scheduling Model

### 7.1 Unified Schedule Table

```typescript
interface ScheduledAction {
  id: string;
  
  // Origin tracking
  origin: 'NARRATIVE' | 'EXPERIMENT' | 'MANUAL';
  policy_id: string;
  goal_id: string;
  
  // Account targeting
  account_id: string;
  account_role: 'MAINLINE' | 'EXPERIMENT_ARM';
  platform: string;
  
  // Content
  asset_id: string;
  variant_id?: string;
  caption?: string;
  
  // Timing
  scheduled_at: Date;
  timezone: string;
  
  // Status tracking
  status: 'draft' | 'scheduled' | 'dispatched' | 'posted' | 'failed';
  provider_post_id?: string;
  platform_post_id?: string;
  
  // Experiment tracking (if applicable)
  experiment_id?: string;
  experiment_arm?: string;
  
  // Correlation
  correlation_id: string;
  idempotency_key: string;
}
```

### 7.2 Validation Rules

```python
def validate_schedule_item(item: ScheduledAction) -> bool:
    # Enforce origin/role alignment
    if item.origin == 'NARRATIVE' and item.account_role != 'MAINLINE':
        raise ValidationError("Narrative can only schedule to MAINLINE")
    
    if item.origin == 'EXPERIMENT' and item.account_role != 'EXPERIMENT_ARM':
        raise ValidationError("Experiments can only schedule to EXPERIMENT_ARM")
    
    return True
```

---

## 8. Event-Driven Topic Taxonomy

Using existing MediaPoster EventBus with Redis Streams.

### 8.1 Naming Convention

```
mp.<domain>.<type>.<name>
```

- `type`: `evt` (event/fact) or `cmd` (command/request)

### 8.2 Core Topics

#### Hydration / State
| Topic | Description |
|-------|-------------|
| `mp.hydration.evt.snapshot_ready` | Fresh hydrated state available |
| `mp.hydration.evt.features_ready` | Derived features computed |

#### Scheduler
| Topic | Description |
|-------|-------------|
| `mp.scheduler.cmd.create_items` | Request to create schedule items |
| `mp.scheduler.cmd.update_item` | Request to update item |
| `mp.scheduler.cmd.cancel_item` | Request to cancel item |
| `mp.scheduler.evt.item_scheduled` | Item successfully scheduled |
| `mp.scheduler.evt.item_due` | Scheduled time reached |
| `mp.scheduler.evt.item_canceled` | Item canceled |

#### Publishing
| Topic | Description |
|-------|-------------|
| `mp.publish.cmd.dispatch` | Request to publish post |
| `mp.publish.evt.dispatched` | Sent to provider |
| `mp.publish.evt.posted` | Confirmed live |
| `mp.publish.evt.failed` | Provider failure |
| `mp.publish.evt.duplicate` | Duplicate detected |

#### Metrics
| Topic | Description |
|-------|-------------|
| `mp.metrics.cmd.poll` | Request metrics poll |
| `mp.metrics.evt.snapshot` | Metrics snapshot ready |
| `mp.metrics.evt.rollup_ready` | Platform rollup computed |

#### Experiments
| Topic | Description |
|-------|-------------|
| `mp.experiments.cmd.plan_run` | Start experiment run |
| `mp.experiments.evt.run_started` | Run began |
| `mp.experiments.evt.variant_created` | Variant scheduled |
| `mp.experiments.evt.run_completed` | Run finished |

#### Knowledge Base
| Topic | Description |
|-------|-------------|
| `mp.rules.evt.rule_created` | New rule from experiment |
| `mp.rules.evt.rule_updated` | Rule confidence updated |
| `mp.rules.evt.rule_deprecated` | Rule no longer valid |

#### UI / Realtime
| Topic | Description |
|-------|-------------|
| `mp.ui.evt.toast` | Show notification |
| `mp.ui.evt.invalidate` | Cache invalidation |
| `mp.ui.evt.activity` | Activity feed item |

### 8.3 Message Envelope

```typescript
interface EventEnvelope {
  event_id: string;
  type: string;  // e.g., "mp.hydration.evt.snapshot_ready"
  ts: string;    // ISO 8601
  workspace_id: string;
  account_group_id?: string;
  origin: 'NARRATIVE' | 'EXPERIMENT' | 'SYSTEM' | 'USER';
  account_role?: 'MAINLINE' | 'EXPERIMENT_ARM';
  correlation_id: string;
  idempotency_key: string;
  payload: Record<string, any>;
}
```

---

## 9. Service Architecture

### 9.1 Service Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                        SERVICES                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Hydration   │  │  Metrics     │  │  Rule        │          │
│  │  Service     │  │  Ingest      │  │  Learner     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              EVENT BUS (Redis Streams)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│         ▲                 ▲                 ▲                   │
│         │                 │                 │                   │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐          │
│  │  Narrative   │  │  Experiments │  │  Scheduler   │          │
│  │  Builder     │  │  Planner     │  │  Service     │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│                                             │                   │
│                                      ┌──────┴───────┐          │
│                                      │  Publisher   │          │
│                                      │  Service     │          │
│                                      └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Service Definitions

#### Hydration Service
- **Subscribes**: `mp.metrics.evt.*`, `mp.publish.evt.posted`
- **Publishes**: `mp.hydration.evt.snapshot_ready`, `mp.hydration.evt.features_ready`

#### Narrative Builder Service
- **Subscribes**: `mp.hydration.evt.snapshot_ready`, `mp.rules.evt.*`
- **Publishes**: `mp.scheduler.cmd.create_items`
- **Scope**: `account_role=MAINLINE`

#### Experiments Planner Service
- **Subscribes**: `mp.hydration.evt.snapshot_ready`, `mp.experiments.cmd.*`
- **Publishes**: `mp.scheduler.cmd.create_items`, `mp.experiments.evt.*`
- **Scope**: `account_role=EXPERIMENT_ARM`

#### Scheduler Service
- **Subscribes**: `mp.scheduler.cmd.*`
- **Publishes**: `mp.scheduler.evt.*`

#### Publisher Service
- **Subscribes**: `mp.scheduler.evt.item_due`
- **Publishes**: `mp.publish.evt.*`

#### Metrics Ingest Service
- **Subscribes**: `mp.publish.evt.posted`, `mp.metrics.cmd.poll`
- **Publishes**: `mp.metrics.evt.snapshot`

#### Rule Learner Service
- **Subscribes**: `mp.experiments.evt.run_completed`
- **Publishes**: `mp.rules.evt.*`

---

## 10. End-to-End Data Flows

### 10.1 Mainline Flow (Narrative Builder)

```
1. HydrationService → mp.hydration.evt.snapshot_ready
2. NarrativeBuilder consumes snapshot + rules
3. NarrativeBuilder → mp.scheduler.cmd.create_items (MAINLINE)
4. Scheduler validates & → mp.scheduler.evt.item_scheduled
5. At scheduled time: Scheduler → mp.scheduler.evt.item_due
6. Publisher → mp.publish.evt.posted
7. MetricsIngest → mp.metrics.evt.snapshot
8. HydrationService updates state (loop)
```

### 10.2 Experiments Flow

```
1. User triggers → mp.experiments.cmd.plan_run
2. ExperimentsPlanner creates variants
3. ExperimentsPlanner → mp.scheduler.cmd.create_items (EXPERIMENT_ARM)
4. Posts go out via Publisher
5. Metrics collected over test period
6. ExperimentsPlanner → mp.experiments.evt.run_completed
7. RuleLearner → mp.rules.evt.rule_created
8. NarrativeBuilder consumes new rules for mainline decisions
```

---

## 11. UI Reflection

### 11.1 Calendar View
- Toggle: **Mainline / Experiments / All**
- Color-coded by origin
- Clear account role indicators

### 11.2 Experiments Page
- Sister accounts as test arms
- Active tests + fairness controls
- Learnings produced (rules)
- Confidence visualization

### 11.3 Narrative Builder Page
- Goal/story stage
- Recommended next posts
- "Powered by learnings from experiments"
- 7-day lookahead
- Topic rotation calendar

---

## 12. Pitfalls to Avoid

### 12.1 Cross-Account Audience Mismatch
Sister accounts may have different audiences.

**Solution**: Only promote rules with:
- Stable lift across multiple arms
- Matching audience signals
- Minimum sample size thresholds

### 12.2 Platform Throttling & Shadow Effects
Running many experiments can change distribution behavior.

**Solution**:
- Rate-limits per account
- Staggered schedules
- "Cooldown between tests" policy
- Monitor for shadow-ban indicators

### 12.3 Overfitting to Sister Account Performance
Don't let mainline optimize on experiment account vanity metrics.

**Solution**:
- Strict Layer 3 only consumption
- Rules require confidence thresholds
- Time decay on old learnings

---

## 13. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Add `account_role` to social_accounts table
- [ ] Create `knowledge_base` tables (rules, templates, constraints)
- [ ] Extend EventBus with new topics
- [ ] Add origin/role to scheduled_actions

### Phase 2: Experiments Enhancement (Week 3-4)
- [ ] Update Experiments page to use EXPERIMENT_ARM accounts
- [ ] Add variant scheduling with fairness controls
- [ ] Implement Rule Learner service
- [ ] Add confidence calculations

### Phase 3: Narrative Builder (Week 5-6)
- [ ] Build Narrative Builder page UI
- [ ] Implement goal/story graph
- [ ] Add 7-day lookahead planning
- [ ] Consume rules from Knowledge Base

### Phase 4: Integration (Week 7-8)
- [ ] Calendar toggle (Mainline/Experiments/All)
- [ ] Cross-system guardrails validation
- [ ] End-to-end flow testing
- [ ] Performance optimization

---

## 14. Database Schema Additions

### 14.1 Account Roles

```sql
ALTER TABLE social_accounts 
ADD COLUMN account_role VARCHAR(20) DEFAULT 'MAINLINE' 
CHECK (account_role IN ('MAINLINE', 'EXPERIMENT_ARM', 'ARCHIVE', 'SEED'));

CREATE INDEX idx_social_accounts_role ON social_accounts(account_role);
```

### 14.2 Knowledge Base Tables

```sql
CREATE TABLE kb_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id),
  rule_type VARCHAR(50) NOT NULL,
  conditions JSONB NOT NULL DEFAULT '{}',
  recommendation TEXT NOT NULL,
  expected_lift DECIMAL(5,2),
  confidence DECIMAL(3,2),
  sample_size INTEGER,
  last_validated TIMESTAMPTZ,
  source_experiment_id UUID REFERENCES experiments(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE kb_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id),
  template_type VARCHAR(50) NOT NULL,
  name VARCHAR(255) NOT NULL,
  content TEXT NOT NULL,
  variables JSONB DEFAULT '[]',
  performance_score DECIMAL(5,2),
  usage_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE kb_playbooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  use_case VARCHAR(50),
  rule_ids UUID[] DEFAULT '{}',
  template_ids UUID[] DEFAULT '{}',
  constraints JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 14.3 Schedule Origin Tracking

```sql
ALTER TABLE scheduled_actions
ADD COLUMN origin VARCHAR(20) DEFAULT 'MANUAL' 
CHECK (origin IN ('NARRATIVE', 'EXPERIMENT', 'MANUAL')),
ADD COLUMN policy_id UUID,
ADD COLUMN goal_id UUID,
ADD COLUMN experiment_arm VARCHAR(50);
```

---

## 15. API Endpoints (New)

### Narrative Builder
- `GET /api/narrative/goals` - Get narrative goals
- `POST /api/narrative/goals` - Create goal
- `GET /api/narrative/plan` - Get 7-day lookahead
- `POST /api/narrative/generate` - Generate next posts
- `GET /api/narrative/rules` - Get applicable rules

### Knowledge Base
- `GET /api/kb/rules` - List rules
- `GET /api/kb/rules/{id}` - Get rule details
- `POST /api/kb/rules` - Create rule (from experiment)
- `GET /api/kb/templates` - List templates
- `GET /api/kb/playbooks` - List playbooks

### Account Roles
- `GET /api/accounts/by-role?role=MAINLINE` - Filter by role
- `PATCH /api/accounts/{id}/role` - Update account role

---

## Appendix A: Existing EventBus Integration

The current EventBus in `Backend/services/event_bus/` supports:
- In-memory and Redis Streams backends
- Consumer groups with acknowledgment
- Dead-letter queue
- Wildcard subscriptions

New topics will follow existing patterns in `topics.py`.

---

## Appendix B: Related Documents

- `MASTER_ARCHITECTURE.md` - Overall system architecture
- `COMPREHENSIVE_SOCIAL_ANALYTICS_SCHEMA.md` - Metrics schema
- `ENGAGEMENT_TRACKING_CAPABILITIES.md` - Platform metrics
