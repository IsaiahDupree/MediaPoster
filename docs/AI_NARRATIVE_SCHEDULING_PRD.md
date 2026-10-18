# AI Narrative Scheduling System - Product Requirements Document

## Executive Summary

This document outlines the requirements for an AI-powered content scheduling system that strategically selects and schedules UGC (User Generated Content) videos based on narrative goals, content pillars, and platform constraints. The system operates in weekly cycles with built-in learning and reflection periods to continuously optimize content strategy.

---

## 1. System Overview

### 1.1 Core Concept

The AI Narrative Scheduling System transforms raw video content into a strategic 7-day posting schedule by:

1. **Understanding** the creator's narrative goals and brand pillars
2. **Analyzing** available video content against those goals
3. **Reasoning** through selection decisions with full transparency
4. **Scheduling** optimized content across platforms
5. **Learning** from post-performance feedback
6. **Iterating** on strategy for continuous improvement

### 1.2 Weekly Cycle

```
Week N                                    Week N+1
┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐
│ Day 1-7: EXECUTION PHASE            │   │ Day 1-7: EXECUTION PHASE            │
│ • Posts go live per schedule        │   │ • New schedule executes             │
│ • Real-time metrics collection      │   │ • Incorporates learnings            │
│ • Performance monitoring            │   │ • Updated content selection         │
└─────────────────┬───────────────────┘   └─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Day 7+: REFLECTION PHASE            │
│ • Aggregate performance metrics     │
│ • Compare to narrative goals        │
│ • Identify what worked/didn't       │
│ • Generate learnings                │
│ • Create next week's plan           │
└─────────────────────────────────────┘
```

---

## 2. Narrative Goals System

### 2.1 Goal Definition

A Narrative Goal defines the overarching story the creator wants to tell through their content.

#### Schema: `narrative_goals`

```sql
CREATE TABLE narrative_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id),
    
    -- Core Goal Definition
    goal_statement TEXT NOT NULL,
    primary_cta TEXT NOT NULL,
    target_audience TEXT,
    
    -- Time Horizon
    time_horizon TEXT DEFAULT 'next_7_days',
    start_date DATE,
    end_date DATE,
    
    -- Success Metrics
    target_followers INTEGER,
    target_engagement_rate FLOAT,
    target_conversions INTEGER,
    
    -- Status
    status TEXT DEFAULT 'active',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 Test Templates - Narrative Goals

| Template ID | Name | Goal Statement | Primary CTA |
|-------------|------|----------------|-------------|
| `goal_tech_educator` | Tech Educator | Position myself as the go-to expert for DIY electronics | Waitlist |
| `goal_lifestyle_brand` | Lifestyle Brand | Build authentic lifestyle brand for young professionals | Follow |
| `goal_product_launch` | Product Launch | Generate buzz and pre-orders for product launch | Purchase |

---

## 3. Narrative Pillars System

### 3.1 Pillar Definition

Narrative Pillars are content themes that support the overall narrative goal.

#### Schema: `narrative_pillars`

```sql
CREATE TABLE narrative_pillars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES narrative_goals(id),
    
    name TEXT NOT NULL,
    description TEXT,
    color TEXT,
    pillar_type TEXT NOT NULL,  -- 'value', 'proof', 'cta'
    keywords TEXT[],
    
    target_percentage FLOAT,
    min_posts_per_week INTEGER,
    max_posts_per_week INTEGER,
    priority INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 Default Pillars

| Pillar | Type | Target % | Description |
|--------|------|----------|-------------|
| Pain Points | Value | 20% | Address audience struggles |
| Social Proof | Proof | 15% | Testimonials, results |
| Process/How-To | Value | 25% | Educational content |
| Personality | Value | 15% | Behind-the-scenes |
| Product/Service | CTA | 10% | Direct showcases |
| Promotion/CTA | CTA | 10% | Calls-to-action |
| Education | Value | 5% | Industry knowledge |

### 3.3 Content Mix Targets

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTENT MIX TARGET                        │
├─────────────────────────────────────────────────────────────┤
│  ████████████████████████████████████░░░░░░░░░░░░░░░░░░░░░  │
│  │         60% VALUE          │  20% PROOF  │  20% CTA   │  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Constraints System

### 4.1 Constraint Definition

```sql
CREATE TABLE scheduling_constraints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES narrative_goals(id),
    
    enabled_platforms TEXT[] DEFAULT ARRAY['tiktok', 'instagram'],
    max_posts_per_day INTEGER DEFAULT 3,
    min_posts_per_day INTEGER DEFAULT 1,
    posting_windows JSONB,
    blackout_dates DATE[],
    timezone TEXT DEFAULT 'America/New_York',
    
    min_pre_social_score INTEGER DEFAULT 60,
    require_analysis BOOLEAN DEFAULT TRUE,
    max_same_pillar_consecutive INTEGER DEFAULT 2,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. AI Reasoning Engine

### 5.1 Reasoning Phases

#### Phase 1: Context Gathering
```json
{
  "phase": "context_gathering",
  "inputs": {
    "narrative_goal": "Position myself as DIY electronics expert",
    "primary_cta": "Waitlist",
    "target_audience": "Beginner makers aged 25-45",
    "active_pillars": ["Pain Points", "Social Proof", "Process/How-To"],
    "constraints": {
      "platforms": ["tiktok", "instagram"],
      "max_posts_per_day": 3,
      "min_score": 60
    },
    "previous_week_performance": {
      "total_views": 15000,
      "avg_engagement": 4.2,
      "top_performing_pillar": "Process/How-To",
      "underperforming_pillar": "Pain Points"
    }
  }
}
```

#### Phase 2: Content Analysis
```json
{
  "phase": "content_analysis",
  "available_videos": 400,
  "analyzed_videos": 122,
  "high_performers": 45,
  "categorization": {
    "by_pillar": {
      "Pain Points": 12,
      "Social Proof": 8,
      "Process/How-To": 35,
      "Personality": 15,
      "Education": 10
    },
    "by_score_range": {
      "90-100": 5,
      "80-89": 18,
      "70-79": 42,
      "60-69": 57
    }
  }
}
```

#### Phase 3: Selection Reasoning
```json
{
  "phase": "selection_reasoning",
  "reasoning_chain": [
    {
      "step": 1,
      "thought": "Goal is to drive waitlist signups. Need content that establishes authority and creates desire.",
      "action": "Prioritize Process/How-To (establishes expertise) and Pain Points (creates urgency)"
    },
    {
      "step": 2,
      "thought": "Last week's Pain Points underperformed (2.1% engagement vs 4.2% avg). Review those videos.",
      "action": "Select higher-scoring Pain Points videos (80+ only) and reduce allocation to 15%"
    },
    {
      "step": 3,
      "thought": "Process/How-To was top performer. Double down but vary sub-topics to avoid fatigue.",
      "action": "Increase Process/How-To to 35%, ensure topic diversity"
    },
    {
      "step": 4,
      "thought": "Need 14 posts for 7 days (2/day). Mix: 5 Process, 3 Pain Points, 3 Social Proof, 3 Personality",
      "action": "Begin video selection from highest scores in each category"
    }
  ]
}
```

#### Phase 4: Video Selection
```json
{
  "phase": "video_selection",
  "selected_videos": [
    {
      "video_id": "abc123",
      "title": "How to Solder Like a Pro",
      "pillar": "Process/How-To",
      "score": 92,
      "selection_reason": "Top scorer in Process pillar, matches target audience interest in electronics basics",
      "assigned_platform": "tiktok",
      "assigned_date": "2025-12-23",
      "assigned_time": "12:00"
    }
  ],
  "rejection_log": [
    {
      "video_id": "xyz789",
      "title": "Random Vlog",
      "rejection_reason": "Does not align with any active pillar",
      "score": 45
    }
  ]
}
```

#### Phase 5: Schedule Generation
```json
{
  "phase": "schedule_generation",
  "schedule": {
    "2025-12-23": [
      {"platform": "tiktok", "time": "12:00", "video_id": "abc123", "pillar": "Process/How-To"},
      {"platform": "instagram", "time": "18:00", "video_id": "def456", "pillar": "Pain Points"}
    ],
    "2025-12-24": [
      {"platform": "youtube", "time": "14:00", "video_id": "ghi789", "pillar": "Social Proof"},
      {"platform": "tiktok", "time": "19:00", "video_id": "jkl012", "pillar": "Personality"}
    ]
  },
  "justification": {
    "pillar_distribution": {
      "Process/How-To": "5 posts (36%) - Increased due to last week's success",
      "Pain Points": "3 posts (21%) - High-quality only, reduced from 25%",
      "Social Proof": "3 posts (21%) - Maintains credibility",
      "Personality": "3 posts (21%) - Builds connection"
    },
    "platform_distribution": {
      "tiktok": "6 posts - Primary discovery platform",
      "instagram": "5 posts - Engagement-focused",
      "youtube": "3 posts - Long-term authority building"
    }
  }
}
```

---

## 6. Learning & Reflection System

### 6.1 Performance Tracking Schema

```sql
CREATE TABLE schedule_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES weekly_schedules(id),
    
    -- Execution Period
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    
    -- Aggregate Metrics
    total_posts INTEGER,
    total_views INTEGER,
    total_likes INTEGER,
    total_comments INTEGER,
    total_shares INTEGER,
    avg_engagement_rate FLOAT,
    
    -- Goal Progress
    followers_gained INTEGER,
    conversions INTEGER,
    goal_progress_pct FLOAT,
    
    -- Pillar Performance
    pillar_performance JSONB,
    
    -- AI Analysis
    learnings JSONB,
    recommendations JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.2 Reflection Process

```json
{
  "reflection": {
    "period": "2025-12-23 to 2025-12-29",
    "goal_assessment": {
      "goal": "Drive waitlist signups",
      "target": 50,
      "achieved": 32,
      "progress": "64%",
      "on_track": false
    },
    "pillar_analysis": [
      {
        "pillar": "Process/How-To",
        "posts": 5,
        "avg_views": 12500,
        "avg_engagement": 5.8,
        "verdict": "EXCEEDED - Continue this strategy",
        "insight": "Step-by-step tutorials with clear outcomes performed best"
      },
      {
        "pillar": "Pain Points",
        "posts": 3,
        "avg_views": 4200,
        "avg_engagement": 2.1,
        "verdict": "UNDERPERFORMED - Needs adjustment",
        "insight": "Problem-focused content without solutions didn't resonate"
      }
    ],
    "learnings": [
      {
        "id": "L001",
        "type": "content_format",
        "learning": "Videos under 30 seconds outperformed longer content by 2.3x",
        "confidence": 0.85,
        "action": "Prioritize shorter clips in next week's selection"
      },
      {
        "id": "L002",
        "type": "pillar_performance",
        "learning": "Pain Points need solution component to convert",
        "confidence": 0.72,
        "action": "Pair Pain Points with quick-fix tutorials"
      }
    ],
    "next_week_adjustments": [
      "Reduce Pain Points to 15%, increase Process/How-To to 40%",
      "Add 'quick tip' format to each Pain Points video",
      "Schedule TikTok posts at 12:00 PM instead of 9:00 AM (higher engagement observed)",
      "Include stronger CTA in video descriptions"
    ]
  }
}
```

---

## 7. API Endpoints

### 7.1 Narrative Goals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/narrative/goals` | List all goals |
| POST | `/api/narrative/goals` | Create new goal |
| GET | `/api/narrative/goals/{id}` | Get goal details |
| PUT | `/api/narrative/goals/{id}` | Update goal |
| DELETE | `/api/narrative/goals/{id}` | Delete goal |

### 7.2 AI Scheduling

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/narrative/generate-plan` | Generate 7-day plan with AI reasoning |
| GET | `/api/narrative/plan/{id}/reasoning` | Get AI reasoning chain |
| POST | `/api/narrative/plan/{id}/approve` | Approve and schedule plan |
| POST | `/api/narrative/plan/{id}/regenerate` | Regenerate with adjustments |

### 7.3 Learning & Reflection

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/narrative/performance/{week}` | Get week's performance |
| POST | `/api/narrative/reflect` | Trigger reflection analysis |
| GET | `/api/narrative/learnings` | Get accumulated learnings |

---

## 8. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create database schemas for goals, pillars, constraints
- [ ] Implement CRUD APIs for narrative goals
- [ ] Build test templates system
- [ ] Create UI for goal configuration

### Phase 2: AI Reasoning (Week 2)
- [ ] Implement content analysis against pillars
- [ ] Build reasoning chain generator
- [ ] Create video selection algorithm
- [ ] Develop schedule optimization

### Phase 3: Execution & Tracking (Week 3)
- [ ] Connect to existing scheduling system
- [ ] Implement performance metric collection
- [ ] Build real-time monitoring dashboard
- [ ] Create alert system for underperformance

### Phase 4: Learning System (Week 4)
- [ ] Build reflection engine
- [ ] Implement learnings database
- [ ] Create next-week plan generator
- [ ] Develop A/B testing capabilities

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Schedule Adoption | 80% of generated plans approved | Plans approved / Plans generated |
| Goal Achievement | 70% of goals hit target | Goals achieved / Total goals |
| Engagement Improvement | 15% week-over-week | Avg engagement W(n+1) / W(n) |
| AI Accuracy | 85% pillar classification | Correct classifications / Total |
| Learning Application | 90% learnings applied | Learnings used / Total learnings |

---

## 10. Test Scenarios

### Scenario 1: New Creator Setup
```
Given: Creator with 100 analyzed videos, no posting history
When: They set up a "Build Authority" goal with 3 pillars
Then: AI generates 7-day plan with balanced pillar distribution
And: Reasoning explains selection based on video analysis scores
```

### Scenario 2: Underperforming Pillar
```
Given: Week 1 data shows "Pain Points" at 50% below average engagement
When: Reflection runs after Week 1
Then: System generates learning about Pain Points performance
And: Week 2 plan reduces Pain Points allocation
And: Reasoning references Week 1 data in justification
```

### Scenario 3: Goal Achievement
```
Given: Goal is "500 new followers in 7 days"
When: Day 4 shows only 150 followers gained
Then: System alerts creator about off-track goal
And: Suggests schedule adjustments (more viral-potential content)
And: Offers to regenerate remaining days
```

---

## Appendix A: AI Prompt Templates

### Content Classification Prompt
```
Analyze this video and classify it into one of these narrative pillars:
- Pain Points: Addresses audience struggles
- Social Proof: Shows results, testimonials
- Process/How-To: Educational, teaches something
- Personality: Behind-the-scenes, authentic moments
- Product/Service: Showcases offerings
- Promotion/CTA: Direct calls-to-action
- Education: Industry knowledge

Video Analysis:
{video_analysis}

Respond with:
1. Primary pillar (most relevant)
2. Secondary pillar (if applicable)
3. Confidence score (0-100)
4. Reasoning (1-2 sentences)
```

### Schedule Justification Prompt
```
You are a content strategist. Given:

NARRATIVE GOAL: {goal_statement}
TARGET AUDIENCE: {target_audience}
PRIMARY CTA: {primary_cta}
ACTIVE PILLARS: {pillars_with_targets}
CONSTRAINTS: {constraints}
PREVIOUS WEEK PERFORMANCE: {last_week_data}
AVAILABLE CONTENT: {content_summary}

Generate a 7-day content schedule that:
1. Aligns with the narrative goal
2. Respects pillar distribution targets
3. Optimizes for the primary CTA
4. Applies learnings from previous week
5. Respects all constraints

For each selection, provide:
- Why this video was chosen
- Which pillar it serves
- Expected contribution to goal
- Platform/time assignment reasoning
```

---

*Document Version: 1.0*
*Created: December 23, 2025*
*Author: MediaPoster AI System*
