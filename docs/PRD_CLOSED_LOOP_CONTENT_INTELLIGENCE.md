# PRD: Closed-Loop Content Intelligence

**Status:** Proposed
**Priority:** P2 — Game-Changer
**Effort:** ~10-14 days
**Impact:** Self-improving content system — every post makes the next one better

---

## 1. Problem Statement

Content creation today is a one-way street: create → publish → hope. There's no systematic feedback loop connecting what performs well back to what gets created next. The creator relies on gut feeling and manual analysis. With 22 accounts generating data across 9 platforms, there's a goldmine of performance signals that should directly inform Sora prompts, caption writing, topic selection, and posting strategy.

## 2. Objective

Build an automated intelligence loop that continuously:
1. **Tracks** what topics, hooks, formats, and styles drive engagement
2. **Analyzes** patterns across all accounts and platforms
3. **Generates** data-backed content briefs and Sora video prompts
4. **Feeds** those briefs into the existing content pipeline
5. **Measures** results and refines the model

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Average engagement per post | ≥ 30% increase over 90 days |
| Content planning time | Reduced by 80% (auto-generated briefs) |
| Brief-to-publish conversion | ≥ 90% of generated briefs get published |
| Top-performer hit rate | ≥ 40% of new posts in top quartile (vs 25% baseline) |

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FEEDBACK LOOP                         │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  Performance  │───▶│  Pattern     │───▶│  Brief     │ │
│  │  Tracker      │    │  Analyzer    │    │  Generator │ │
│  └──────────────┘    └──────────────┘    └─────┬──────┘ │
│         ▲                                       │        │
│         │                                       ▼        │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  Publish &    │◀───│  Content     │◀───│  Sora      │ │
│  │  Measure      │    │  Pipeline    │    │  Prompter  │ │
│  └──────────────┘    └──────────────┘    └────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 5. Components

### 5.1 Performance Tracker (`services/content_intelligence/performance_tracker.py`)

Collects and categorizes performance data:

```python
class PerformanceTracker:
    async def tag_post_attributes(self, post_id: UUID) -> PostAttributes:
        """
        AI-powered attribute extraction:
        - Topic category (relationships, motivation, humor, lifestyle, etc.)
        - Hook type (question, bold claim, story, controversy, listicle)
        - Emotional tone (inspirational, funny, provocative, educational)
        - Visual style (talking head, cinematic, text overlay, montage)
        - Caption structure (short punchy, long story, CTA-heavy)
        - Hashtag strategy (trending, niche, branded)
        """
    
    async def compute_performance_index(self, post_id: UUID) -> float:
        """
        Weighted score accounting for:
        - Platform-normalized engagement rate
        - Velocity (engagement in first 2 hours)
        - Virality coefficient (shares / views)
        - Comment quality (AI-assessed sentiment + depth)
        """
```

### 5.2 Pattern Analyzer (`services/content_intelligence/pattern_analyzer.py`)

Discovers what works:

```python
class PatternAnalyzer:
    async def analyze_winning_patterns(self, lookback_days: int = 90) -> ContentInsights:
        """
        Returns structured insights:
        {
            "top_topics": [
                {"topic": "relationship_advice", "avg_engagement": 5.2, "post_count": 15},
                {"topic": "self_improvement", "avg_engagement": 4.1, "post_count": 22},
            ],
            "top_hooks": [
                {"hook_type": "controversial_question", "avg_engagement": 6.1},
                {"hook_type": "bold_claim", "avg_engagement": 4.8},
            ],
            "top_visual_styles": [...],
            "underperforming": [...],      # Topics/styles to avoid
            "emerging_trends": [...],       # New patterns showing promise
            "platform_specific": {
                "tiktok": {"best_topic": "relationship_advice", "best_hook": "question"},
                "youtube": {"best_topic": "self_improvement", "best_hook": "story"},
            }
        }
        """
    
    async def generate_weekly_report(self) -> str:
        """AI-summarized weekly performance report with actionable recommendations"""
```

### 5.3 Brief Generator (`services/content_intelligence/brief_generator.py`)

Creates data-backed content briefs:

```python
class BriefGenerator:
    async def generate_briefs(self, count: int = 7) -> List[ContentBrief]:
        """
        Uses GPT + performance patterns to generate content briefs:
        
        ContentBrief:
            topic: str              # "Why 'I'm fine' is the most dangerous phrase in a relationship"
            hook: str               # "She said 'I'm fine' and he believed her. That was his first mistake."
            key_points: List[str]   # Talking points
            target_emotion: str     # "provocative"
            suggested_style: str    # "talking_head_with_text_overlay"
            sora_prompt: str        # Ready-to-use Sora video generation prompt
            caption_draft: str      # Draft caption
            hashtags: List[str]     # Suggested hashtags
            confidence: float       # How likely this will perform well (based on patterns)
            reasoning: str          # "Relationship advice + question hooks avg 6.1x engagement"
        """
    
    async def generate_sora_prompt(self, brief: ContentBrief) -> str:
        """
        Convert content brief into a Sora video generation prompt.
        Incorporates @character for consistent branding.
        """
```

### 5.4 Learning Store

```sql
CREATE TABLE content_attributes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL,
    media_id UUID,
    platform VARCHAR(20),
    topic_category VARCHAR(100),
    hook_type VARCHAR(50),
    emotional_tone VARCHAR(50),
    visual_style VARCHAR(50),
    caption_structure VARCHAR(50),
    ai_confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE content_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_type VARCHAR(50),       -- 'winning_pattern', 'underperformer', 'emerging_trend'
    platform VARCHAR(20),
    attribute_key VARCHAR(100),     -- 'topic:relationship_advice'
    attribute_value VARCHAR(255),
    avg_engagement FLOAT,
    sample_size INT,
    confidence FLOAT,
    period_start DATE,
    period_end DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE content_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    hook TEXT,
    key_points JSONB,
    target_emotion VARCHAR(50),
    suggested_style VARCHAR(50),
    sora_prompt TEXT,
    caption_draft TEXT,
    hashtags TEXT[],
    confidence FLOAT,
    reasoning TEXT,
    status VARCHAR(20) DEFAULT 'draft',  -- draft, approved, produced, published
    produced_media_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 6. Cron Jobs

| Job | Frequency | Description |
|-----|-----------|-------------|
| `tag_new_posts` | Every 6 hours | AI-tag attributes on newly posted content |
| `collect_metrics` | Every 6 hours | Pull latest engagement data |
| `analyze_patterns` | Weekly (Sunday 3am) | Run full pattern analysis |
| `generate_briefs` | Weekly (Sunday 5am) | Generate next week's content briefs |
| `weekly_report` | Weekly (Monday 8am) | Email/notify weekly intelligence report |

## 7. API Endpoints

```
GET  /api/intelligence/insights          — Latest content insights
GET  /api/intelligence/patterns          — Winning/losing patterns
GET  /api/intelligence/briefs            — Generated content briefs
POST /api/intelligence/briefs/generate   — Trigger brief generation
PUT  /api/intelligence/briefs/:id        — Approve/modify a brief
GET  /api/intelligence/report            — Weekly intelligence report
GET  /api/intelligence/attributes/:post  — View AI-tagged attributes for a post
```

## 8. Rollout Plan

1. **Phase 1:** Post attribute tagging + performance scoring
2. **Phase 2:** Pattern analyzer + weekly insights
3. **Phase 3:** Brief generator with Sora prompt output
4. **Phase 4:** Full loop — briefs → Sora → publish → measure → learn
5. **Phase 5:** Dashboard intelligence tab + weekly email reports

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Overfitting to one content type | Enforce diversity requirement (max 40% any single topic) |
| GPT attribute tagging inaccuracy | Validate with human review for first 50 posts; iterate prompts |
| Insufficient data for patterns | Require minimum 30 posts before generating insights |
| Briefs feel generic | Include specific examples from top performers; use creator voice samples |
| Feedback loop takes time to show results | Start with industry patterns, gradually shift to own data |

## 10. Out of Scope (v1)

- Automated Sora video generation (manual approval still required)
- Competitor content analysis feeding into briefs
- Real-time trend integration (see PRD_AUTOMATED_TREND_DETECTION)
- Multi-language content intelligence
