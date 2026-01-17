# PRD: Autonomous Content Ops Controller
## AI-Generated Self-Improving Feedback Loop Agent

**Version:** 1.0 | **Updated:** 2026-01-16 | **Status:** Build-Ready

---

## 1. Executive Summary

Build an autonomous agent that:
- **Generates** posts/threads aligned to Awareness × FATE frameworks
- **Publishes** with full attribution (post → prompt → template → offer → ICP)
- **Collects** engagement signals (impressions, likes, replies, clicks)
- **Scores** posts and identifies winners/losers
- **Optimizes** via template leaderboard + creative iterations
- **Directs** readers toward purchasing while preserving quality

---

## 2. Persuasion Frameworks

### 2.1 FATE Stack (Chase Hughes - SRS #253)

| Element | Description | Script Tactics |
|---------|-------------|----------------|
| **F — Focus** | Capture attention/novelty | Pattern interrupt + curiosity gap + stakes |
| **A — Authority** | Credibility, proof | Numbers, receipts, mechanism ("Here's how…") |
| **T — Tribe** | Identity + us-vs-them | "People like us" + shared enemy/friction |
| **E — Emotion** | Visceral buy-in | Story beats, contrast, loss aversion, hope |

**FATE Script Skeleton:**
```
1. Focus: 1–2 line hook (specific, disruptive)
2. Authority: 1 proof + 1 mechanism line
3. Tribe: "If you're [identity], you've seen [frustration]…"
4. Emotion: quick story/contrast + payoff
5. Close: single CTA
```

### 2.2 Eugene Schwartz's 5 Awareness Levels

| Level | Mindset | Your Job | Best CTA |
|-------|---------|----------|----------|
| **1. Unaware** | "I'm fine" | Surface symptom, story | Quiz, "see if applies" |
| **2. Problem-Aware** | "This hurts" | Mirror pain, clarify cause | Checklist, guide |
| **3. Solution-Aware** | "What options?" | Educate, compare approaches | Demo, case study |
| **4. Product-Aware** | "Is this best?" | Differentiate, handle objections | Trial, pricing |
| **5. Most-Aware** | "Just need nudge" | Offer + urgency + friction removal | Buy now |

**Copy Shift Pattern:**
```
Story + problem framing → Mechanism + comparisons → Offer + urgency
```

---

## 3. Core Loop

```
Plan (weekly slots) → Generate (AI) → Publish → Attribute → Collect Metrics
         ↑                                                           ↓
    Update Plan ← Learn ← Score ← Metrics (1h/6h/24h/72h/7d)
```

---

## 4. Key Entities

- **CreatorProfile**: Voice rules, banned phrases, tone
- **Brand**: Positioning, allowed/disallowed topics
- **Offer**: Promise, CTAs, landing URL, who it's for/not for
- **ICP**: Pains, outcomes, objections, language patterns
- **Template**: Awareness level, FATE weights, format, CTA strength
- **Slot**: Scheduled time, awareness target, offer/ICP routing
- **PromptRun**: Template + inputs + model → generated text
- **Touchpoint**: Unified record (post/comment/DM/email)
- **Score**: Rates-based reward + labels (winner/loser)

---

## 5. Scoring Model

**Rates (not raw counts):**
```
like_rate = likes / impressions
reply_rate = replies / impressions
click_rate = link_clicks / impressions
```

**Reward Function:**
```
score = 1.0 * z(click_rate) + 0.8 * z(reply_rate) + 0.6 * z(repost_rate) + 0.4 * z(like_rate)
```

**Snapshot Timings:** 1h, 6h, 24h, 72h, 7d

---

## 6. Template Allocation (Bandit Policy)

- **70%** → Top performers (exploit)
- **20%** → Promising but under-tested (explore)
- **10%** → Experiments (new hooks/angles)

**Weekly Grid:**
- 40% Problem/Solution-aware value posts
- 30% Authority posts (proof, mechanisms)
- 20% Tribe/Identity posts
- 10% Direct offer posts

---

## 7. Multi-Channel Extensions

| Channel | Goal | Key Signals |
|---------|------|-------------|
| **Posts** | Build awareness + trust | Impressions, replies, clicks |
| **Comments** | Public helpfulness | Reply depth, profile clicks |
| **DMs** | Qualify + convert | Reply rate, progression, booking |
| **Email** | Nurture + sell | Opens, clicks, replies, conversions |

---

## 8. Autonomous Operations

| Frequency | Jobs |
|-----------|------|
| **Real-time** | Inbound listener, Responder, Attribution logger |
| **Daily** | Slot executor, Early performance check |
| **Weekly** | Planner, Template evolution, Forks |

**Safety Gates:**
- DM permission gate (consent before links)
- Per-user cooldown + max DM/day
- Per-offer fatigue limits
- Human review queue for uncertain content

---

## 9. Platform Adapters

| Platform | Publish | Comments | DMs | Metrics |
|----------|---------|----------|-----|---------|
| X/Twitter | ✅ | ✅ | ✅ | ✅ |
| Instagram | ✅ API | ⚠️ | ✅ Safari | ⚠️ |
| TikTok | ✅ API | ⚠️ | ✅ Safari | ⚠️ |
| YouTube | ✅ | ✅ | ❌ | ✅ |
| Threads | ✅ Safari | ✅ Safari | ✅ Safari | ⚠️ |

---

## 10. Implementation Stack

- **DB:** Postgres (Supabase)
- **Queue:** Redis + BullMQ
- **Orchestrator:** n8n or custom cron
- **Analytics:** PostHog
- **Shortlinks:** Custom redirect service
- **Gen:** OpenAI API

**See:** `PRD_CONTENT_OPS_TECHNICAL.md` for API endpoints, event schemas, and TypeScript contracts.
