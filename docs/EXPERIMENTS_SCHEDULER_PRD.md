# Experiments Scheduler PRD
## AI-Powered Content Experimentation & Learning System

**Version:** 1.0  
**Date:** December 23, 2025  
**Status:** Draft

---

## Executive Summary

The Experiments Scheduler is an autonomous AI agent that conducts systematic content experiments to discover winning strategies, formats, and approaches. Unlike the Narrative Builder (which maintains brand consistency for the main account), the Experiments Scheduler operates "outside the box" - testing hypotheses, trying new formats, and learning from results to continuously improve content performance.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTENT SCHEDULING SYSTEM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────┐ │
│  │  NARRATIVE       │    │  EXPERIMENTS     │    │   USER    │ │
│  │  BUILDER         │◄───│  SCHEDULER       │    │ SCHEDULED │ │
│  │                  │    │                  │    │           │ │
│  │  • Main Account  │    │  • Test Accounts │    │  • Manual │ │
│  │  • Brand Safe    │    │  • Hypothesis    │    │  • Direct │ │
│  │  • Vetted Content│    │  • Risk-Taking   │    │           │ │
│  └────────┬─────────┘    └────────┬─────────┘    └─────┬─────┘ │
│           │                       │                     │       │
│           ▼                       ▼                     ▼       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              UNIFIED POST TRACKING SYSTEM                 │  │
│  │   origin: 'narrative' | 'experiments' | 'user'           │  │
│  │   experiment_id: uuid (if experiments)                    │  │
│  │   hypothesis_id: uuid (if experiments)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              METRICS & ANALYTICS ENGINE                   │  │
│  │   • Views, Engagement, Retention                         │  │
│  │   • Attribution by Origin                                │  │
│  │   • A/B Test Results                                     │  │
│  │   • Winner Detection                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LEARNING & FRAMEWORKS ENGINE                 │  │
│  │   • Pattern Recognition                                  │  │
│  │   • Best Practices Database                              │  │
│  │   • Hypothesis Refinement                                │  │
│  │   • Winner → Narrative Pipeline                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Experiment Agent

The Experiment Agent is an AI-powered decision maker that:

- **Plans experiments** with clear hypotheses and success criteria
- **Selects resources** from available tools and content
- **Executes tests** by scheduling content with proper tagging
- **Analyzes results** to determine pass/fail
- **Learns patterns** to build frameworks over time
- **Identifies winners** to promote to Narrative Builder

#### Agent Capabilities (AI Actions)

```python
class ExperimentAgentActions:
    """Tools available to the Experiment Agent"""
    
    # Content Discovery
    BROWSE_UGC_LIBRARY = "browse_ugc_library"
    SEARCH_BY_TOPIC = "search_by_topic"
    FILTER_BY_SCORE = "filter_by_score"
    
    # Content Analysis
    ANALYZE_VIDEO_HOOKS = "analyze_video_hooks"
    ANALYZE_PACING = "analyze_pacing"
    ANALYZE_AUDIO = "analyze_audio"
    DETECT_TRENDS = "detect_trends"
    
    # Content Editing
    TRIM_CLIP = "trim_clip"
    ADD_HOOK = "add_hook"
    CHANGE_MUSIC = "change_music"
    ADD_SUBTITLES = "add_subtitles"
    ADJUST_PACING = "adjust_pacing"
    CREATE_THUMBNAIL = "create_thumbnail"
    
    # AI Content Creation
    GENERATE_SCRIPT = "generate_script"
    GENERATE_VOICEOVER = "generate_voiceover"
    GENERATE_B_ROLL = "generate_b_roll"
    REMIX_CONTENT = "remix_content"
    
    # Scheduling
    SCHEDULE_POST = "schedule_post"
    SET_CAPTION = "set_caption"
    SET_HASHTAGS = "set_hashtags"
    TARGET_TIME_SLOT = "target_time_slot"
    
    # Experiment Management
    CREATE_HYPOTHESIS = "create_hypothesis"
    DEFINE_SUCCESS_CRITERIA = "define_success_criteria"
    TAG_EXPERIMENT = "tag_experiment"
    COMPARE_VARIANTS = "compare_variants"
```

### 2. Hypothesis Framework

```python
@dataclass
class Hypothesis:
    """A testable hypothesis for content experimentation"""
    id: str
    experiment_id: str
    
    # The hypothesis statement
    statement: str  # e.g., "Videos with questions in first 2 seconds get 40% more views"
    
    # Variables being tested
    independent_variable: str  # What we're changing
    dependent_variable: str    # What we're measuring
    control_description: str   # Baseline approach
    variant_description: str   # Test approach
    
    # Success criteria
    success_metric: str        # e.g., "view_count", "engagement_rate"
    success_threshold: float   # e.g., 1.4 (40% improvement)
    min_sample_size: int       # Minimum posts before conclusion
    
    # Results
    status: str  # 'pending', 'running', 'passed', 'failed', 'inconclusive'
    confidence_level: float
    actual_improvement: float
    learnings: str
```

### 3. Post Tagging System

Every scheduled post is tagged with origin information:

```python
@dataclass
class PostOrigin:
    """Origin tracking for all scheduled posts"""
    origin_type: str  # 'narrative' | 'experiments' | 'user'
    
    # Narrative Builder fields
    narrative_goal_id: Optional[str]
    pillar: Optional[str]
    
    # Experiments fields
    experiment_id: Optional[str]
    hypothesis_id: Optional[str]
    variant: Optional[str]  # 'control' | 'variant_a' | 'variant_b'
    
    # User fields
    user_id: Optional[str]
    manual_reason: Optional[str]
    
    # Common
    scheduled_at: datetime
    scheduled_by: str  # 'ai_narrative' | 'ai_experiments' | 'user'
```

---

## Experiment Types

### 1. Hook Experiments
- Test different opening styles
- Question vs statement vs visual hook
- Duration of hook (1s, 2s, 3s)

### 2. Format Experiments
- Talking head vs B-roll heavy
- Text overlay styles
- Aspect ratios (9:16 vs 1:1)

### 3. Timing Experiments
- Post time optimization
- Day of week testing
- Frequency testing

### 4. Caption Experiments
- Emoji usage
- CTA placement
- Hashtag strategies

### 5. Audio Experiments
- Music genres
- Voiceover styles
- Sound effects impact

### 6. Content Angle Experiments
- Same topic, different angles
- Emotional vs educational
- Controversial vs safe

---

## Winner Detection & Promotion

### Criteria for "Winner of Winners"

```python
class WinnerCriteria:
    """Criteria for promoting experiment winners to Narrative Builder"""
    
    # Performance thresholds
    min_views: int = 10000
    min_engagement_rate: float = 0.05  # 5%
    min_watch_time_pct: float = 0.50   # 50% average
    
    # Consistency requirements  
    min_successful_tests: int = 3
    max_performance_variance: float = 0.20
    
    # Brand safety
    brand_safe_score: float = 0.90
    narrative_alignment: float = 0.70
    
    # Recency
    within_days: int = 30
```

### Promotion Pipeline

1. **Detection**: Agent identifies consistent performers
2. **Validation**: Human review (optional) or AI brand check
3. **Tagging**: Mark as "winner_candidate"
4. **Narrative Review**: Check alignment with current goals
5. **Scheduling**: Add to Narrative Builder queue
6. **Attribution**: Track original experiment source

---

## Metrics & Attribution

### Per-Origin Analytics

```sql
-- Views by origin
SELECT 
    origin_type,
    COUNT(*) as posts,
    SUM(views) as total_views,
    AVG(engagement_rate) as avg_engagement
FROM posts
WHERE posted_at > NOW() - INTERVAL '30 days'
GROUP BY origin_type;

-- Results: 
-- narrative:    45 posts, 234K views, 4.2% engagement
-- experiments: 120 posts,  89K views, 3.8% engagement
-- user:         12 posts,  15K views, 5.1% engagement
```

### Experiment Results Dashboard

| Experiment | Hypothesis | Variant | Control | Lift | Status |
|------------|------------|---------|---------|------|--------|
| Hook Test #12 | Question openers | 12.3% | 8.1% | +52% | ✅ Passed |
| Music Test #8 | Trending audio | 9.8% | 10.2% | -4% | ❌ Failed |
| Time Test #3 | 6PM posting | 15.1% | 11.3% | +34% | ✅ Passed |

---

## Learning System

### Pattern Database

The agent builds a knowledge base of learnings:

```python
@dataclass
class ContentPattern:
    """A learned pattern from experiments"""
    id: str
    pattern_type: str  # 'hook', 'format', 'timing', etc.
    
    # The pattern
    description: str
    success_rate: float
    avg_improvement: float
    
    # Evidence
    supporting_experiments: List[str]
    sample_size: int
    confidence: float
    
    # Application
    when_to_use: str
    when_to_avoid: str
    
    # Evolution
    first_discovered: datetime
    last_validated: datetime
    times_applied: int
```

### Framework Generation

Over time, the agent develops content frameworks:

```python
class ContentFramework:
    """A proven framework for content creation"""
    name: str  # e.g., "The Question Hook Framework"
    
    structure: List[str]  # Step-by-step approach
    # 1. Open with provocative question
    # 2. Pause for 1 second
    # 3. Deliver surprising answer
    # 4. Provide evidence
    # 5. End with CTA
    
    best_for: List[str]  # Content types
    avg_performance_lift: float
    times_validated: int
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Create post origin tagging system
- [ ] Add origin field to scheduled_posts table
- [ ] Create experiments table schema
- [ ] Create hypotheses table schema
- [ ] Build basic experiment agent service

### Phase 2: Agent Actions (Week 3-4)
- [ ] Define and implement agent action interfaces
- [ ] Integrate with clip extraction tools
- [ ] Integrate with AI content generation
- [ ] Integrate with scheduling system
- [ ] Build action execution engine

### Phase 3: Hypothesis Testing (Week 5-6)
- [ ] Implement hypothesis creation workflow
- [ ] Build A/B variant scheduling
- [ ] Create results collection pipeline
- [ ] Implement pass/fail determination
- [ ] Build confidence calculation

### Phase 4: Learning System (Week 7-8)
- [ ] Create pattern detection algorithms
- [ ] Build pattern database
- [ ] Implement framework generation
- [ ] Create winner detection system
- [ ] Build narrative promotion pipeline

### Phase 5: Analytics & Dashboard (Week 9-10)
- [ ] Build origin-based analytics
- [ ] Create experiment results dashboard
- [ ] Implement learnings visualization
- [ ] Add winner tracking
- [ ] Create recommendation engine

---

## Database Schema

```sql
-- Post origin tracking
ALTER TABLE scheduled_posts ADD COLUMN origin_type VARCHAR(20) DEFAULT 'user';
ALTER TABLE scheduled_posts ADD COLUMN experiment_id UUID;
ALTER TABLE scheduled_posts ADD COLUMN hypothesis_id UUID;
ALTER TABLE scheduled_posts ADD COLUMN variant VARCHAR(20);

-- Experiments
CREATE TABLE experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    success_criteria JSONB,
    results JSONB,
    learnings TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Hypotheses
CREATE TABLE hypotheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    statement TEXT NOT NULL,
    independent_variable VARCHAR(255),
    dependent_variable VARCHAR(255),
    control_description TEXT,
    variant_description TEXT,
    success_metric VARCHAR(100),
    success_threshold FLOAT,
    min_sample_size INT DEFAULT 10,
    status VARCHAR(20) DEFAULT 'pending',
    confidence_level FLOAT,
    actual_improvement FLOAT,
    learnings TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Content patterns (learnings)
CREATE TABLE content_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(50),
    description TEXT,
    success_rate FLOAT,
    avg_improvement FLOAT,
    supporting_experiments UUID[],
    sample_size INT,
    confidence FLOAT,
    when_to_use TEXT,
    when_to_avoid TEXT,
    first_discovered TIMESTAMP DEFAULT NOW(),
    last_validated TIMESTAMP,
    times_applied INT DEFAULT 0
);

-- Winners (promoted to narrative)
CREATE TABLE experiment_winners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    post_id UUID,
    video_id UUID,
    performance_metrics JSONB,
    promoted_to_narrative BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMP,
    narrative_performance JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

```
# Experiments
POST   /api/experiments                    Create experiment
GET    /api/experiments                    List experiments
GET    /api/experiments/{id}               Get experiment details
PUT    /api/experiments/{id}               Update experiment
POST   /api/experiments/{id}/start         Start experiment
POST   /api/experiments/{id}/analyze       Analyze results

# Hypotheses
POST   /api/experiments/{id}/hypotheses    Add hypothesis
GET    /api/experiments/{id}/hypotheses    List hypotheses
PUT    /api/hypotheses/{id}                Update hypothesis
POST   /api/hypotheses/{id}/test           Run hypothesis test

# Agent Actions
POST   /api/experiments/agent/plan         Agent plans experiment
POST   /api/experiments/agent/execute      Agent executes action
GET    /api/experiments/agent/actions      List available actions

# Analytics
GET    /api/analytics/by-origin            View counts by origin
GET    /api/analytics/experiments          Experiment performance
GET    /api/analytics/winners              Winner leaderboard

# Patterns & Learnings
GET    /api/patterns                       List learned patterns
GET    /api/patterns/{type}                Patterns by type
GET    /api/frameworks                     Content frameworks
```

---

## Success Metrics

### System KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Experiments per week | 10+ | Count of new experiments |
| Hypothesis pass rate | 30%+ | Successful tests / total |
| Winners promoted | 5/month | To narrative builder |
| Framework accuracy | 80%+ | Predicted vs actual lift |
| Attribution accuracy | 95%+ | Correct origin tagging |

### Business KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Main account growth | +20%/month | From narrative winners |
| Content efficiency | +30% | Better content faster |
| Engagement lift | +25% | From learned patterns |

---

## Integration Points

### With Narrative Builder
- Winner candidates API
- Brand safety check
- Goal alignment verification
- Scheduled content handoff

### With Clip Extraction
- UGC library access
- Segment analysis
- Smart cropping
- Subtitle generation

### With Analytics
- Metrics collection
- Origin attribution
- A/B comparison
- Performance tracking

---

*Document Version: 1.0*  
*Last Updated: December 23, 2025*  
*Author: AI Assistant*
