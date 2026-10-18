# Narrative Builder & Experiments API Documentation

## Overview

The MediaPoster platform implements a **Two-Brain Architecture** for content strategy:

1. **Narrative Builder (Mainline Brain)** - Strategic content planning and scheduling
2. **Experiments (Scientist Brain)** - A/B testing and learning generation

Both systems share a **Knowledge Base** of rules, templates, and constraints.

---

## Base URL

```
http://localhost:5555
```

---

## Table of Contents

- [System Health](#system-health)
- [Narrative Builder](#narrative-builder)
- [Experiments](#experiments)
- [Knowledge Base](#knowledge-base)
- [Calendar](#calendar)
- [Trend Opportunities](#trend-opportunities)

---

## System Health

### GET /api/system/health

Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-22T19:00:00.000Z",
  "service": "MediaPoster Backend",
  "version": "2.0.0"
}
```

### GET /api/system/health/detailed

Detailed component-level health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-22T19:00:00.000Z",
  "components": {
    "api": { "status": "healthy", "message": "API responding" },
    "database": { "status": "healthy", "message": "Connected" },
    "narrative_builder": { "status": "healthy", "message": "3 goals" },
    "experiments": { "status": "healthy", "message": "5 experiments" },
    "calendar": { "status": "healthy", "message": "10 pending posts" }
  }
}
```

### GET /api/system/metrics/overview

Get comprehensive metrics for dashboard overview.

**Response:**
```json
{
  "timestamp": "2025-12-22T19:00:00.000Z",
  "metrics": {
    "narrative_builder": {
      "active_goals": 3,
      "scheduled_posts": 15,
      "kb_rules_applied": 7,
      "trend_opportunities": 4
    },
    "experiments": {
      "running": 2,
      "completed": 8,
      "total_learnings": 7,
      "avg_uplift": 25
    },
    "calendar": {
      "mainline_pending": 10,
      "experiment_pending": 5,
      "manual_pending": 2,
      "today_posts": 3
    },
    "content": {
      "total_videos": 150,
      "analyzed": 120,
      "high_performers": 25,
      "fresh": 30
    }
  }
}
```

---

## Narrative Builder

### GET /api/narrative-builder/goals

List all narrative goals.

**Response:**
```json
{
  "goals": [
    {
      "id": "uuid",
      "name": "Q1 Growth Campaign",
      "description": "Grow followers by 50%",
      "goal_type": "growth",
      "target_metric": "followers",
      "content_pillars": ["education", "proof", "pain"],
      "platform_mix": { "tiktok": 0.5, "instagram": 0.3, "youtube": 0.2 },
      "posting_cadence": { "min_per_day": 1, "max_per_day": 3 },
      "status": "active",
      "progress_percent": 33.3
    }
  ]
}
```

### POST /api/narrative-builder/goals

Create a new narrative goal.

**Request Body:**
```json
{
  "name": "Q1 Growth Campaign",
  "description": "Grow followers by 50%",
  "goal_type": "growth",
  "target_metric": "followers",
  "content_pillars": ["education", "proof", "pain"],
  "platform_mix": { "tiktok": 0.5, "instagram": 0.3, "youtube": 0.2 },
  "posting_cadence": { "min_per_day": 1, "max_per_day": 3 }
}
```

### GET /api/narrative-builder/plan/7-day

Generate an AI-optimized 7-day content plan.

**Query Parameters:**
- `goal_ids` (optional): Comma-separated goal IDs to apply

**Response:**
```json
{
  "plan": [
    {
      "date": "2025-12-23",
      "day_name": "Monday",
      "posts": [
        {
          "slot": 1,
          "content_id": "uuid",
          "content_title": "How to grow on TikTok",
          "content_score": 85,
          "platform": "tiktok",
          "suggested_time": "9:00 AM",
          "type": "mainline"
        }
      ],
      "total_posts": 2
    }
  ],
  "total_posts": 14,
  "goals_applied": [{ "id": "uuid", "name": "Q1 Growth" }],
  "rules_applied": 5,
  "trend_opportunities": 2
}
```

### GET /api/narrative-builder/applicable-rules

Get KB rules applicable to current content strategy.

**Response:**
```json
{
  "rules": [
    {
      "id": "uuid",
      "rule_type": "hook",
      "name": "Pain Point Cold Open",
      "recommendation": "Start with pain point question",
      "expected_lift": 34.0,
      "confidence": 0.95
    }
  ]
}
```

### GET /api/narrative-builder/trend-opportunities

Get active trend opportunities.

**Response:**
```json
{
  "opportunities": [
    {
      "id": "uuid",
      "title": "Viral Sound: POV you finally...",
      "opportunity_score": 92,
      "relevance_to_brand": 85,
      "content_fit": 90,
      "priority": "high",
      "window": { "start": "2025-12-22", "end": "2025-12-24" },
      "recommended_actions": ["Create tutorial using sound"]
    }
  ]
}
```

---

## Experiments

### GET /api/experiments/list

List all experiments.

**Response:**
```json
{
  "experiments": [
    {
      "id": "uuid",
      "name": "Hook Test - Pain Point vs Question",
      "hypothesis": "Pain point hooks increase hook rate by 20%",
      "type": "hook",
      "status": "running",
      "primary_metric": "hook_rate_3s",
      "variants": [
        {
          "id": "a",
          "name": "Control",
          "is_control": true,
          "views": 10000,
          "primary_metric_value": 65
        },
        {
          "id": "b",
          "name": "Pain Point",
          "is_control": false,
          "views": 10000,
          "primary_metric_value": 78
        }
      ]
    }
  ]
}
```

### POST /api/experiments/create

Create a new experiment.

**Request Body:**
```json
{
  "name": "Hook Test",
  "hypothesis": "Pain point hooks increase hook rate",
  "type": "hook",
  "primary_metric": "hook_rate_3s",
  "duration_days": 14,
  "variants": [
    { "name": "Control", "is_control": true },
    { "name": "Pain Point", "is_control": false }
  ]
}
```

### POST /api/experiments/{id}/calculate-confidence

Calculate statistical confidence for an experiment.

**Response:**
```json
{
  "experiment_id": "uuid",
  "confidence": 95.5,
  "is_significant": true,
  "winner": "b",
  "uplift": 20.0,
  "p_value": 0.001,
  "sample_size": 20000
}
```

### POST /api/experiments/{id}/declare-winner

Declare a winner for the experiment.

**Request Body:**
```json
{
  "variant_id": "b"
}
```

### POST /api/experiments/{id}/generate-rule

Generate a KB rule from the winning variant.

**Response:**
```json
{
  "rule_id": "uuid",
  "rule_type": "hook",
  "name": "Pain Point Hook Pattern",
  "recommendation": "Use pain point opening hooks",
  "expected_lift": 20.0,
  "confidence": 0.95,
  "message": "Rule created and added to Knowledge Base"
}
```

### POST /api/experiments/batch-generate-rules

Generate rules from all completed experiments.

**Response:**
```json
{
  "rules_generated": 3,
  "rules": [...]
}
```

### POST /api/experiments/schedule-variant

Schedule a variant for posting.

**Request Body:**
```json
{
  "experiment_id": "uuid",
  "variant_id": "b",
  "account_id": "uuid",
  "platform": "tiktok",
  "scheduled_at": "2025-12-23T09:00:00Z",
  "caption": "Testing pain point hook"
}
```

### GET /api/experiments/{id}/scheduled-variants

Get scheduled posts for an experiment.

**Response:**
```json
{
  "experiment_id": "uuid",
  "scheduled_posts": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "platform": "tiktok",
      "scheduled_at": "2025-12-23T09:00:00Z",
      "status": "scheduled",
      "variant_id": "b"
    }
  ],
  "count": 5
}
```

### GET /api/experiments/experiment-accounts

Get accounts with EXPERIMENT_ARM role.

**Response:**
```json
{
  "accounts": [
    {
      "id": "uuid",
      "platform": "tiktok",
      "handle": "@test_account",
      "account_role": "EXPERIMENT_ARM"
    }
  ]
}
```

---

## Knowledge Base

### GET /api/kb/rules

List all KB rules.

**Query Parameters:**
- `rule_type` (optional): Filter by type (hook, format, timing, caption, cta, thumbnail)
- `status` (optional): Filter by status (active, deprecated, testing)

**Response:**
```json
{
  "rules": [
    {
      "id": "uuid",
      "rule_type": "hook",
      "name": "Pain Point Cold Open",
      "conditions": { "platform": ["tiktok", "instagram"] },
      "recommendation": "Use pain point opening",
      "expected_lift": 34.0,
      "confidence": 0.95,
      "source_experiment_id": "uuid",
      "status": "active"
    }
  ]
}
```

### GET /api/kb/templates

List content templates.

### GET /api/kb/constraints

List content constraints (fatigue rules, frequency limits).

### GET /api/kb/playbooks

List content playbooks (pre-built strategies).

---

## Calendar

### GET /api/calendar/posts/by-origin

Get scheduled posts filtered by origin.

**Query Parameters:**
- `origin` (optional): NARRATIVE, EXPERIMENT, MANUAL
- `account_role` (optional): MAINLINE, EXPERIMENT_ARM

**Response:**
```json
{
  "posts": [
    {
      "id": "uuid",
      "title": "Educational Video",
      "platform": "tiktok",
      "scheduled_at": "2025-12-23T09:00:00Z",
      "status": "scheduled",
      "origin": "NARRATIVE",
      "account_role": "MAINLINE"
    }
  ],
  "count": 10,
  "origin_counts": {
    "NARRATIVE": 5,
    "EXPERIMENT": 3,
    "MANUAL": 2
  }
}
```

### GET /api/calendar/stats/by-origin

Get calendar statistics grouped by origin.

**Response:**
```json
{
  "by_origin": {
    "NARRATIVE": { "total": 10, "pending": 5, "posted": 5 },
    "EXPERIMENT": { "total": 8, "pending": 3, "posted": 5 },
    "MANUAL": { "total": 15, "pending": 10, "posted": 5 }
  }
}
```

---

## Trend Opportunities

### GET /api/trend-opportunities

List active trend opportunities.

**Response:**
```json
{
  "opportunities": [
    {
      "id": "uuid",
      "title": "Viral Sound",
      "description": "Trending in education niche",
      "opportunity_score": 92,
      "relevance_to_brand": 85,
      "content_fit": 90,
      "priority": "high",
      "window_start": "2025-12-22T00:00:00Z",
      "window_end": "2025-12-24T00:00:00Z",
      "recommended_actions": ["Create tutorial"],
      "status": "active"
    }
  ]
}
```

---

## Data Models

### Account Roles

| Role | Description |
|------|-------------|
| `MAINLINE` | Primary audience accounts (Narrative Builder posts here) |
| `EXPERIMENT_ARM` | Test accounts (Experiments post here) |
| `ARCHIVE` | Inactive accounts |
| `SEED` | Accounts for initial testing |

### Post Origins

| Origin | Description |
|--------|-------------|
| `NARRATIVE` | Posts from Narrative Builder / 7-Day Plan |
| `EXPERIMENT` | Posts from A/B experiments |
| `MANUAL` | Manually scheduled posts |
| `SYSTEM` | System-generated posts |

### Experiment Types

| Type | Description |
|------|-------------|
| `hook` | Test different hook approaches |
| `caption` | Test caption styles |
| `format` | Test video formats |
| `cta` | Test call-to-action variants |
| `timing` | Test posting times |
| `thumbnail` | Test thumbnail styles |

### Goal Types

| Type | Description |
|------|-------------|
| `campaign` | Time-bound marketing campaign |
| `series` | Content series with theme |
| `funnel_stage` | Target specific funnel stage |
| `growth` | General growth objective |

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message",
  "message": "Human-readable description",
  "detail": "Additional context (optional)"
}
```

HTTP Status Codes:
- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TWO-BRAIN ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────┐              ┌──────────────────────┐         │
│  │   NARRATIVE BUILDER  │              │     EXPERIMENTS      │         │
│  │   (Mainline Brain)   │              │   (Scientist Brain)  │         │
│  ├──────────────────────┤              ├──────────────────────┤         │
│  │ POST /goals          │              │ POST /create         │         │
│  │ GET /plan/7-day      │              │ POST /schedule-variant│        │
│  │ GET /applicable-rules│              │ POST /calculate-confidence     │
│  │ GET /trend-opportunities            │ POST /generate-rule  │         │
│  │                      │              │                      │         │
│  │ Posts to: MAINLINE   │              │ Posts to: EXPERIMENT_ARM       │
│  └──────────┬───────────┘              └──────────┬───────────┘         │
│             │                                     │                      │
│             └─────────────┬───────────────────────┘                      │
│                           ▼                                              │
│              ┌────────────────────────┐                                  │
│              │    KNOWLEDGE BASE      │                                  │
│              │  GET /kb/rules         │                                  │
│              │  GET /kb/templates     │                                  │
│              │  GET /kb/constraints   │                                  │
│              └────────────────────────┘                                  │
│                           │                                              │
│                           ▼                                              │
│              ┌────────────────────────┐                                  │
│              │       CALENDAR         │                                  │
│              │  GET /posts/by-origin  │                                  │
│              │  GET /stats/by-origin  │                                  │
│              └────────────────────────┘                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

1. **Set Goals**: `POST /api/narrative-builder/goals`
2. **Generate Plan**: `GET /api/narrative-builder/plan/7-day`
3. **Schedule Posts**: `POST /api/schedule/create` with `origin: "NARRATIVE"`
4. **Create Experiment**: `POST /api/experiments/create`
5. **Schedule Variants**: `POST /api/experiments/schedule-variant`
6. **Check Confidence**: `POST /api/experiments/{id}/calculate-confidence`
7. **Generate Learning**: `POST /api/experiments/{id}/generate-rule`
8. **View Calendar**: `GET /api/calendar/posts/by-origin`
