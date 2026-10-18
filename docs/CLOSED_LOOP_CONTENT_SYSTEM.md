# Closed-Loop Content System

## Architecture Overview

```
Publish → Measure (checkback periods) → Review → Extract Patterns → Update Playbook → Generate → Repeat
```

This system transforms random content creation into **measurable iteration** by treating each video as a time series with multiple review windows, not a single data point.

---

## Core Components

### 1. Database Schema

**Location**: `@/Backend/migrations/closed_loop_content_system.sql`

#### Tables Created:

| Table | Purpose |
|-------|---------|
| `content_items` | Creative assets with DNA (source type, format, hook, CTA) |
| `creative_features` | Structured tags (emotion, POV, proof type, editing style) |
| `postings` | Same creative posted to multiple platforms/accounts |
| `metric_snapshots` | Time series metrics per posting |
| `derived_metrics` | Computed velocity, engagement rates per window |
| `review_windows` | Checkback periods per platform (1h, 6h, 24h, etc.) |
| `reviews` | Labels (winner/loser) + failure reasons + next actions |
| `trend_items` | Sounds, hooks, topics, formats discovered |
| `trend_recommendations` | Filtered trends with fit scores |
| `prompt_templates` | Reusable prompts for generation |
| `prompt_runs` | Log of every AI generation |
| `playbook_rules` | "What works" library with confidence scores |
| `content_slots` | Daily mix planning (UGC/AI slots) |
| `insights` | Extracted learnings with recommended actions |
| `hook_patterns` | Library of hook templates |

---

### 2. Review Windows (Checkback Periods)

Platform-specific measurement windows:

#### TikTok (Fast Burn)
| Window | Hours | Primary Weights |
|--------|-------|-----------------|
| 1h | 0-1 | Velocity 50%, Engagement 30%, Shares 20% |
| 6h | 1-6 | Velocity 40%, Engagement 30%, Shares 20%, Retention 10% |
| 24h | 6-24 | Velocity 30%, Engagement 30%, Shares 20%, Retention 20% |
| 72h | 24-72 | Velocity 20%, Engagement 30%, Shares 25%, Retention 25% |

#### Instagram Reels (Slower Discovery)
| Window | Hours | Primary Weights |
|--------|-------|-----------------|
| 24h | 0-24 | Velocity 35%, Engagement 30%, Saves 20%, Retention 15% |
| 72h | 24-72 | Velocity 25%, Engagement 30%, Saves 25%, Retention 20% |
| 7d | 72-168 | Velocity 20%, Engagement 30%, Saves 25%, Retention 25% |

#### YouTube Shorts (Long Tail)
| Window | Hours | Primary Weights |
|--------|-------|-----------------|
| 24h | 0-24 | Velocity 30%, Engagement 25%, Retention 30%, CTR 15% |
| 7d | 24-168 | Velocity 20%, Engagement 25%, Retention 35%, CTR 20% |
| 14d | 168-336 | Velocity 15%, Engagement 25%, Retention 40%, CTR 20% |

---

### 3. Scoring System

#### Normalized Score (0-100)
Relative to:
- Platform baseline
- Account baseline
- Format baseline
- Time window baseline

#### Labels
| Label | Score Range | Action |
|-------|-------------|--------|
| `winner` | 70+ | Scale variations |
| `needs_iteration` | 40-69 | Iterate hook/edit/caption |
| `loser` | <40 | Kill concept or analyze further |

#### Failure Reasons
- `weak_hook` - First 3 seconds not engaging
- `bad_pacing` - Too slow or too fast
- `wrong_audience` - Mismatch with ICP
- `unclear_offer` - CTA not obvious
- `low_energy` - Lack of enthusiasm
- `poor_audio` - Audio quality issues
- `too_long` / `too_short`
- `wrong_timing` - Posted at wrong time
- `saturated_topic` - Overdone topic
- `weak_cta` - No clear call to action

---

### 4. API Endpoints

**Base**: `/api/content-loop`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/content-items` | GET/POST | List/create content items |
| `/postings` | GET/POST | List/create postings |
| `/postings/{id}/status` | PATCH | Update posting status |
| `/postings/{id}/metrics` | GET | Get metric time series |
| `/metrics/snapshot` | POST | Record new snapshot |
| `/review-windows` | GET | List review windows |
| `/review-windows/{platform}/due` | GET | Get due reviews |
| `/reviews` | GET/POST | List/create reviews |
| `/reviews/auto-score/{posting_id}` | POST | Auto-score a posting |
| `/playbook` | GET/POST | List/create playbook rules |
| `/slots` | GET/POST | List/create content slots |
| `/slots/{id}/assign` | POST | Assign content to slot |
| `/insights` | GET | Get extracted insights |
| `/dashboard` | GET | Full dashboard summary |

---

### 5. Insight Extraction Job

**Location**: `@/Backend/scripts/insight_extraction_job.py`

**Run**: Nightly (or on-demand)

```bash
cd Backend && source venv/bin/activate
python scripts/insight_extraction_job.py
```

#### What It Does:
1. Fetches reviews from last 14 days
2. Segments by performance (winners/losers)
3. Extracts patterns (source types, formats, hooks, durations)
4. Updates playbook rules with new learnings
5. Generates insights with AI analysis
6. Stores recommended actions

---

### 6. Content Slots

Plan your daily mix:

| Slot Type | Description |
|-----------|-------------|
| `UGC` | User-generated content (talking head, vlogs) |
| `SORA` | AI-generated video (Sora, Runway) |
| `AI_EDIT` | AI-assisted editing |
| `BROLL` | B-roll footage |
| `REMIX` | Remixed/repurposed content |

| Objective | Description |
|-----------|-------------|
| `reach` | Maximize views |
| `nurture` | Build relationship |
| `convert` | Drive action |
| `engage` | Maximize comments/shares |
| `experiment` | Test new approaches |

---

### 7. Frontend UI

**Location**: `@/dashboard/app/(dashboard)/review/page.tsx`

**Tabs**:
1. **Performance** - UGC vs AI category comparison, video cards with scores
2. **Review Windows** - Checkback periods per platform
3. **Playbook** - Rules with confidence scores
4. **Content Slots** - Daily mix planning
5. **Insights** - Extracted learnings with recommended actions

---

## Workflow

### Daily Loop

1. **Morning**: Check due reviews at each window
2. **Auto-triage**: System flags potential winners/problems
3. **Label + reason**: Human confirms label, adds failure reasons
4. **Update playbook**: Rules automatically extracted

### Nightly Job

1. Look at top winners by platform + format
2. Extract patterns (hooks, pacing, CTAs, sounds)
3. Write to `playbook_rules`
4. Update prompt context for next generation

### Generation Context Pack (RAG-style)

When generating new content, retrieve:
- Top 5 winners (last 14 days, same platform + format)
- Top 3 playbook rules (highest confidence)
- Top 3 trend recommendations (best fit score)
- ICP pain points + transformations
- Offer + CTA constraints
- "Do not do" list (common failure tags)

---

## Setup

### 1. Run Migration

```bash
cd Backend
psql $DATABASE_URL < migrations/closed_loop_content_system.sql
```

### 2. Start Backend

```bash
cd Backend && source venv/bin/activate
python main.py
```

### 3. Access UI

Navigate to **Improve → Performance Review** in the sidebar, or visit:
```
http://localhost:5557/review
```

### 4. Schedule Nightly Job

Add to crontab:
```bash
0 3 * * * cd /path/to/MediaPoster/Backend && source venv/bin/activate && python scripts/insight_extraction_job.py
```

---

## Files

| File | Purpose |
|------|---------|
| `Backend/migrations/closed_loop_content_system.sql` | Complete DDL |
| `Backend/api/endpoints/content_loop.py` | API endpoints |
| `Backend/api/endpoints/review.py` | Performance review API |
| `Backend/scripts/insight_extraction_job.py` | Nightly extraction |
| `Backend/scripts/youtube_performance_review.py` | YouTube analysis |
| `dashboard/app/(dashboard)/review/page.tsx` | Frontend UI |
| `docs/CLOSED_LOOP_CONTENT_SYSTEM.md` | This document |

---

## What You Get

✅ Answer: "What *exactly* makes our winners win?"
✅ Answer: "Which hooks are consistently failing and why?"
✅ Generate content with grounded context (your winners, niche trends, ICP)
✅ Enforce daily mix (UGC/AI/B-roll) via content slots
✅ Compound learning: system gets better every week

**No more "pulling it out of the air." It becomes data → decision → generation.**

---

*Version: 1.0*
*Created: January 2026*
