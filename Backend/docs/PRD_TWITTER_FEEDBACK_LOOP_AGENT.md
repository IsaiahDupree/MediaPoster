# PRD: X/Twitter Feedback-Loop Agent (AI-Generated + Self-Improving)

## 1) Purpose

Build an agent that:

1. **Generates** X posts/threads (AI) aligned to **Awareness × FATE**
2. **Publishes** (or exports) posts with perfect attribution (post → prompt → template → offer → ICP → content plan slot)
3. **Collects** engagement signals (impressions, likes, replies, reposts, profile clicks, URL clicks)
4. **Scores** posts and identifies winners/losers
5. **Optimizes** future posting via:
   - Template leaderboard (what structures win)
   - Offer routing (which offers/ICPs resonate)
   - Creative iterations (hook + CTA variants)
6. **Directs** readers down a funnel toward purchasing/signing up, while preserving content quality

---

## 2) Scope

### In-scope
- Interchangeable **Brands → Offers → ICPs** structure
- One **"Creator/Author"** voice (personal brand) used across brands/offers
- AI generation of posts/threads with configurable constraints
- URL generation + attribution (shortlinks + UTMs)
- Metrics ingestion (scheduled snapshots)
- Scoring + learning loop
- Weekly content plan generation + auto-adjustment
- Post library + prompt traceback viewer

### Out-of-scope (initially)
- Full paid ads optimization (this is organic-first, but can be extended)
- Automated comment replies (can be phase 2)
- Cross-platform posting (can be phase 2)

---

## 3) Users & Jobs-to-be-Done

### Primary User
Solo creator/founder (Isaiah) managing multiple products/brands.

### Jobs
- "Generate 30–70 high-quality posts/week without losing brand voice."
- "Know which prompts/templates/offers are actually working."
- "Route followers into my offers with minimal friction."
- "Continuously improve content performance based on engagement."

---

## 4) Key Concepts & Definitions

### Creator/Author (single)
Represents personal voice + credibility + consistent tone across all brands.

### Brand
A business identity (e.g., EverReach, MatrixLoop.app, KeywordRadar.app, BlankLogo).

### Offer
A sellable unit: waitlist, subscription, trial, course, service package, etc.

### ICP (Ideal Customer Profile)
An audience segment tied to an offer. Offers can have multiple ICPs.

### Awareness (Eugene Schwartz's 5 Levels)
1. **Unaware** - Don't realize they have a problem
2. **Problem-aware** - Feel the pain, unclear on solutions
3. **Solution-aware** - Know solutions exist, don't know your product
4. **Product-aware** - Know your product, not fully convinced
5. **Most-aware** - Know and want it, just need a nudge

### FATE (Influence Stack - Chase Hughes)
- **F — Focus** (capture attention / novelty)
- **A — Authority** (credibility, status, proof)
- **T — Tribe** (identity + us-vs-them group norms)
- **E — Emotion** (visceral feeling that drives buy-in)

### Content Slot
A planned post unit: date/time + Awareness + FATE + intent + offer/ICP targeting + CTA strength.

---

## 5) System Overview

### Core Loop
```
Plan (weekly slots)
    ↓
Generate (AI posts per slot)
    ↓
Publish (X API or export)
    ↓
Attribute (post_id + shortlink + prompt_run_id)
    ↓
Collect metrics (1h, 6h, 24h, 72h, 7d)
    ↓
Score (rates + weighted objective)
    ↓
Learn (template leaderboard + offer routing + creative forks)
    ↓
Update plan (next week improves)
    ↓
[repeat]
```

---

## 6) Requirements

### 6.1 Content Generation Requirements (AI)

**R1 — Template-driven generation**
AI must generate posts from structured templates tagged with:
- Awareness level
- FATE emphasis
- Post type (single, thread, quote-tweet, reply bait, story, teardown, etc.)
- CTA style (none, soft, direct)
- Offer routing policy (which offer/ICP to mention)

**R2 — Creator voice consistency**
Generation must follow a Creator Voice Profile:
- tone descriptors
- forbidden phrases
- formatting style
- typical hook style
- typical credibility style (proof/mechanism)
- typical CTA style

**R3 — "Interchangeable offers"**
At generation time, the agent can swap:
- brand
- offer
- ICP
- link/CTA

...without rewriting the entire strategy by hand.

**R4 — Quality controls**
Must pass content checks before publish:
- max length (single post vs thread)
- no banned words/phrases
- clarity score (heuristic)
- CTA relevance check
- "no hallucinated claims" flag

### 6.2 Attribution & Traceback Requirements

**R5 — Prompt Run Traceback**
Every generated post must store:
- `template_id`
- `prompt_run_id` (filled prompt + model + params)
- `content_plan_slot_id`
- `brand_id` / `offer_id` / `icp_id`
- `draft_text` + `final_text`
- publish metadata (`post_id`, `url`, `timestamp`)

**R6 — Link Attribution**
Every CTA link must be:
- shortlink that logs: `post_id`, `offer_id`, `template_id`, `icp_id`
- forwarded with UTMs:
  - `utm_source=x`
  - `utm_campaign=brand_offer`
  - `utm_content=template_id`
  - `utm_term=icp_id`
  - `utm_id=post_id`

### 6.3 Metrics Requirements

**R7 — Metrics snapshots**
Collect metrics at: 1 hour, 6 hours, 24 hours, 72 hours, 7 days

**R8 — Metrics captured (minimum)**
- impressions
- likes
- replies
- reposts
- quotes
- profile clicks (if available)
- URL clicks (prefer from shortlink logs)

### 6.4 Scoring & Learning Requirements

**R9 — Objective-based scoring**
Support scoring modes:
- **Follower Growth Mode**
- **Lead Mode**
- **Purchase Mode** (needs conversion events)

Default formulas are rate-based:
```
like_rate = likes / impressions
reply_rate = replies / impressions
repost_rate = reposts / impressions
click_rate = link_clicks / impressions
```

**R10 — Template Leaderboard**
Maintain stats per template:
- `avg_score_24h`, `avg_score_7d`
- `early_velocity` score (1h/6h)
- `stability` (variance)
- best performing offers/ICPs for that template

**R11 — Forking templates (safe evolution)**
Never overwrite a template that performs well. Instead:
- fork templates into versions (`tpl_018a`, `tpl_018b`)
- run controlled A/B allocation in future content plan

### 6.5 Weekly Content Plan Requirements

**R12 — Slot planner (Awareness × FATE grid)**
Each week:
- generate N slots/day (configurable)
- allocate by:
  - 70% → top performers (exploit)
  - 20% → "promising but under-tested" (explore)
  - 10% → weird experiments (new hooks, new angles)

**R13 — Offer routing rules**
The planner chooses which offers appear in which slots based on:
- ICP/offer fit to content type
- audience fatigue limits
- stage alignment

---

## 7) Data Model (MVP)

### Entities

```python
CreatorProfile:
    creator_id: str
    name: str
    voice_rules: dict  # json
    banned_phrases: list[str]
    tone_descriptors: list[str]
    proof_sources: list[str]  # optional

Brand:
    brand_id: str
    name: str
    positioning: str
    allowed_topics: list[str]
    disallowed_topics: list[str]
    style_overrides: dict  # optional

Offer:
    offer_id: str
    brand_id: str
    name: str
    offer_type: str  # trial/waitlist/subscription/service
    promise: str
    cta_primary: str
    cta_secondary: str
    landing_url: str
    shortlink_domain: str
    who_for: str
    who_not_for: str
    price: str  # optional

ICP:
    icp_id: str
    offer_id: str
    name: str
    pains: list[str]
    desired_outcomes: list[str]
    objections: list[str]
    awareness_distribution: dict  # optional
    language_to_use: list[str]
    language_to_avoid: list[str]
    example_hooks: list[str]

Template:
    template_id: str
    awareness_level: str  # unaware/problem/solution/product/most
    fate_weights: dict  # {F: 0.8, A: 0.6, T: 0.3, E: 0.5}
    format: str  # single/thread
    intent: str  # educate/story/teardown/contrast/myth
    cta_strength: str  # none/soft/direct
    prompt_text: str  # with {variables}

ContentPlan:
    content_plan_id: str
    week_start: date
    slots: list[Slot]

Slot:
    slot_id: str
    scheduled_time: datetime
    awareness_level: str
    fate_target: dict
    template_id: str  # optional
    target_offer_ids: list[str]
    target_icp_ids: list[str]
    constraints: dict

PromptRun:
    prompt_run_id: str
    template_id: str
    inputs: dict  # json
    model_info: dict
    generated_text: str
    quality_checks: dict
    created_at: datetime

Post:
    post_id: str
    post_url: str
    prompt_run_id: str
    published_at: datetime
    brand_id: str
    offer_id: str
    icp_id: str
    shortlink_id: str

MetricsSnapshot:
    snapshot_id: str
    post_id: str
    pulled_at: datetime
    metrics: dict  # json

Score:
    post_id: str
    score_6h: float
    score_24h: float
    score_7d: float
    labels: list[str]  # winner/loser/high_intent
    blame_notes: dict  # hook/cta/value_density
```

---

## 8) AI Generation Spec

### 8.1 Inputs required to generate a post
- `CreatorProfile.voice_rules`
- `Brand` positioning
- `Offer` details + landing URL
- `ICP` details (pains, outcomes, objections, language)
- `Slot` spec (awareness + FATE + intent + CTA strength)
- `Template` chosen

### 8.2 Output
- Draft post(s) (single or thread)
- Hook variant suggestions (optional)
- CTA variants (optional)
- Extracted structured fields:
  - `hook_type`
  - `cta_type`
  - `claims_used` (list)
  - `topics/tags`

---

## 9) Starter Template Library (25 templates)

Each template: **Awareness × FATE emphasis × Post format × CTA strength**

### Problem-Aware (8)
1. Symptom mirror + "why it keeps happening" (F+E, soft CTA)
2. Cost of doing nothing (E+A, soft CTA)
3. My mistake story → lesson (E+A, none/soft)
4. "If you've tried X and it failed…" mechanism reveal (A+F, soft)
5. Checklist: "You're in this bucket if…" (F, none/soft)
6. Myth: "Hard work isn't the fix" (A+F, soft)
7. Identity callout (people like us) (T+E, none/soft)
8. Quick diagnostic question (F, reply CTA)

### Solution-Aware (7)
9. 3 approaches comparison (pros/cons) (A+F, soft CTA)
10. Framework breakdown (steps) (A, soft)
11. Decision tree (A+F, soft)
12. Tool stack recommendation (A, soft)
13. "Do this before you buy anything" (A+F, none/soft)
14. Case study format without brand name (A+E, soft)
15. What "good" looks like (benchmarks) (A, soft)

### Product-Aware (6)
16. Why we built it differently (mechanism) (A, direct CTA)
17. Feature → outcome mapping (A+F, direct)
18. Objection handling ("you might think…") (A+E, direct)
19. Before/after flow (A+F, direct)
20. Demo-in-words / walkthrough (A, direct)
21. Competitive positioning without naming (A+F, direct)

### Most-Aware (4)
22. Offer reminder + fastest start steps (F, direct)
23. Limited bonus / deadline (F+E, direct)
24. Guarantee / risk reversal post (A, direct)
25. "Here's exactly what you get" (A+F, direct)

**Variables supported:** `{brand}`, `{offer}`, `{icp}`, `{pain}`, `{desired_outcome}`, `{objection}`, `{mechanism}`, `{cta_link}`, `{proof}`

---

## 10) Scoring Weights (3 modes)

### Mode A: Followers / Reach
```python
score = (
    1.0 * z(reply_rate) +
    0.8 * z(repost_rate) +
    0.6 * z(profile_click_rate) +
    0.4 * z(like_rate) +
    0.2 * z(click_rate)
)
```

### Mode B: Leads
```python
score = (
    1.0 * z(click_rate) +
    0.7 * z(reply_rate) +
    0.5 * z(profile_click_rate) +
    0.4 * z(repost_rate) +
    0.2 * z(like_rate)
)
```

### Mode C: Purchases
```python
score = (
    1.0 * z(conversion_rate) +
    0.7 * z(click_rate) +
    0.3 * z(reply_rate) +
    0.2 * z(profile_click_rate)
)
```

Where `z()` is a rolling z-score vs last N posts.

---

## 11) Weekly Content Plan Engine

### Default weekly mix (configurable)
- 40% Problem/Solution-aware value
- 30% Authority/mechanism posts
- 20% Tribe/identity posts
- 10% Direct offer posts

### Offer rotation rules
- No more than X direct CTAs per offer per day
- If offer fatigue detected (declining click_rate), reduce direct slots

### Learning integration
- Templates that win get more slots next week
- Losing templates get:
  - rewritten hooks
  - altered CTA
  - different ICP mapping
  - or retired

---

## 12) UX / Screens (MVP)

1. **Brands / Offers / ICP Manager**
   - create/edit offer, add multiple ICPs, define "for/not for"

2. **Content Plan Calendar**
   - weekly slots view; shows Awareness × FATE × offer mapping

3. **Generate Queue**
   - per slot: generate 3 variants → pick 1 or auto-pick

4. **Published Posts**
   - list of posts with metrics and score

5. **Traceback View**
   - click a post → see prompt_run, template, inputs, offer/ICP, link clicks

6. **Template Leaderboard**
   - performance by template + by offer + by ICP

7. **Insights**
   - "Hooks that win", "CTAs that win", "Best offer per ICP"

---

## 13) Integrations

### X/Twitter
- Publish (optional; can be export-only)
- Read metrics snapshots via API

### Shortlink / Redirect
- Internal shortlink service OR third-party
- Must log clicks with `post_id` + `offer_id` + `template_id` + `icp_id`

### Analytics / Conversions
- Web conversions via PostHog events, Stripe webhooks, signup forms
- Map conversions back to `utm_id=post_id`

---

## 14) Safety & Policy

- Avoid manipulative claims, deception, or impersonation
- If referencing "proof" (numbers/results), require:
  - a stored "proof source" note, or
  - generate a claim-free version

---

## 15) Milestones

### Phase 1 (MVP)
- [ ] Offer/ICP manager
- [ ] Template library
- [ ] Content plan generator
- [ ] AI generation + attribution IDs
- [ ] Export posts + shortlinks
- [ ] Metrics snapshots
- [ ] Scoring + leaderboard
- [ ] Traceback UI

### Phase 2
- [ ] Auto-A/B testing forks
- [ ] Auto-replies + comment handling
- [ ] Cross-platform expansion

---

## 16) Acceptance Criteria (MVP)

1. You can define multiple brands, each with multiple offers, each with multiple ICPs
2. You can generate a week plan with slots tagged by Awareness × FATE
3. Each published post can be clicked to show:
   - template used
   - exact filled prompt
   - offer + ICP
   - shortlink + clicks
   - metrics snapshots
   - scores and label (winner/loser)
4. Next week's plan changes based on winners/losers automatically

---

## 17) "Interchangeable Offer" Contract

Every offer must include:
```json
{
  "offer": {
    "promise": "...",
    "primaryCTA": "...",
    "landingURL": "...",
    "for_who": "...",
    "not_for": "...",
    "icps": [
      {
        "name": "...",
        "pains": ["...", "...", "..."],
        "outcomes": ["...", "...", "..."],
        "objections": ["...", "...", "..."],
        "language_to_use": ["...", "..."],
        "language_to_avoid": ["...", "..."]
      }
    ]
  }
}
```

---

## 18) JSON Schema

See: `Backend/models/feedback_loop_schema.json`

---

## 19) Related Documents

- `Backend/docs/TWITTER_DOM_SELECTORS.md` - Safari automation selectors
- `Backend/automation/safari_twitter_poster.py` - Post publishing automation
- `Backend/automation/safari_session_manager.py` - Multi-platform session management

---

*Last Updated: January 2026*
