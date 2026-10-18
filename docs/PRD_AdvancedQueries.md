# PRD: Advanced Trend Query System

**Version:** 1.0 | **Date:** Dec 26, 2025 | **Priority:** P0

---

## Executive Summary

A query-driven system that transforms raw social data into **rankable ideas**, **repeatable experiments**, and **practical actions**. Built on Instagram Looter API + computed signals.

---

## Query Categories Overview

| Category | Queries | User Need |
|----------|---------|-----------|
| **Niche Radar** | A, B, C | "What should I talk about?" |
| **Creator Discovery** | D, E, F | "Who should I study/collab with?" |
| **Content Briefs** | G, H, I | "Turn trends into posts" |
| **Audio & Format** | J, K | "What's carrying reach?" |
| **Timing & Consistency** | L, M | "When should I post?" |
| **Competitive Gap** | N, O | "Where can I win?" |
| **Experiment System** | P, Q | "How do I test scientifically?" |

---

## 1. Niche Radar Queries

### Query A: Top 50 Hashtags in Niche (Daily)

**Input:**
```json
{
  "seed_keywords": ["nyc fitness", "meal prep"],
  "limit": 50
}
```

**Pipeline:**
1. Hashtag search → hashtag feeds → recent media metrics
2. Compute: `trend_score`, `trend_delta`, `saturation`

**Output:**
```json
{
  "hashtags": [
    {
      "tag": "#mealprep",
      "trend_score": 87,
      "trend_delta": "+42%",
      "saturation": "moderate",
      "why_hot": "Rising adoption with manageable competition",
      "example_posts": ["media_id_1", "media_id_2"]
    }
  ]
}
```

**Saturation Levels:**
- `hot_accessible` = rising velocity + moderate creator concentration
- `overcrowded` = huge volume but low velocity per post
- `emerging` = low volume but high velocity

---

### Query B: Rising Topics in Niche

**Input:**
```json
{
  "niche_keyword": "fitness",
  "timeframe": "7d"
}
```

**Pipeline:**
1. Top posts from hashtag feeds + captions
2. Compute: keyphrases rising week-over-week, hook patterns

**Output:**
```json
{
  "angles": [
    {
      "pattern": "3 mistakes people make with ___",
      "growth": "+180%",
      "example_captions": ["...", "..."]
    },
    {
      "pattern": "I tried ___ for 7 days and…",
      "growth": "+95%",
      "example_captions": ["...", "..."]
    }
  ]
}
```

---

### Query C: Explore Section Drift

**Input:**
```json
{
  "niche_filter": ["fitness", "lifestyle"]  // optional
}
```

**Pipeline:**
1. Explore sections list → section media
2. Compute: format ratios, hook density, audio reuse rate

**Output:**
```json
{
  "algorithm_favoring": {
    "format_breakdown": { "reel": 72, "carousel": 18, "static": 10 },
    "avg_hook_length_chars": 45,
    "top_audio_reuse_rate": 0.34,
    "insights": [
      "Reels with text overlays dominating (+15% vs last week)",
      "Carousel engagement up in educational niches"
    ],
    "example_posts": ["media_id_1", "media_id_2"]
  }
}
```

---

## 2. Creator Discovery Queries

### Query D: Creator Leaderboard by Niche

**Input:**
```json
{
  "niche_hashtags": ["#fitness", "#homeworkout"],
  "limit": 25
}
```

**Pipeline:**
1. Hashtag feed → authors of top posts
2. Compute: median velocity per creator, consistency score

**Output:**
```json
{
  "creators": [
    {
      "username": "fitcreator1",
      "user_id": "123",
      "median_velocity": 2400,
      "consistency_score": 0.85,
      "winning_formats": ["transformation reels", "quick tips"],
      "profile_url": "https://instagram.com/fitcreator1"
    }
  ]
}
```

---

### Query E: Creators Like Me (Lookalikes)

**Input:**
```json
{
  "target_user_id": "123456789"
}
```

**Pipeline:**
1. Target's posts + hashtags + audio used
2. Compute: similarity via hashtag/audio overlap + format matching

**Output:**
```json
{
  "lookalikes": [
    {
      "username": "similar_creator",
      "similarity_score": 0.78,
      "hashtag_overlap": 12,
      "audio_overlap": 5,
      "differentiator": "Uses more carousel content"
    }
  ]
}
```

---

### Query F: Collab Opportunity Finder

**Input:**
```json
{
  "your_niche": "fitness",
  "your_follower_tier": "10k-50k"
}
```

**Output:**
```json
{
  "collab_opportunities": [
    {
      "username": "potential_collab",
      "followers": 35000,
      "overlap_score": 0.65,
      "complementary_score": 0.82,
      "collab_concept": "Joint workout challenge series"
    }
  ]
}
```

---

## 3. Content Brief Queries (⭐ North Star Feature)

### Query G: Trend → Content Brief Generator

**Input:**
```json
{
  "trend_type": "hashtag",  // or "audio", "topic"
  "trend_id": "#mealprep"
}
```

**Pipeline:**
1. Top 20 posts using trend + captions + metrics
2. Compute: structure, hook templates, CTA patterns, length distribution

**Output:**
```json
{
  "brief": {
    "trend_name": "#mealprep",
    "trend_velocity": 87,
    
    "hook_options": [
      "Stop meal prepping like this (here's why)",
      "I meal prep 5 days in 2 hours—here's how",
      "The meal prep hack that changed everything"
    ],
    
    "script_outline": {
      "hook": "Pattern interrupt or bold claim (0-3s)",
      "problem": "Relatable struggle (3-8s)",
      "solution": "Your method/tip (8-20s)",
      "proof": "Quick result/demo (20-35s)",
      "cta": "Save this + follow for more"
    },
    
    "recommended_format": "reel",
    "optimal_length_sec": { "min": 25, "max": 45 },
    
    "must_include_phrases": [
      "meal prep Sunday",
      "week of meals",
      "save time"
    ],
    
    "differentiation_twist": "Focus on budget angle (under-covered)",
    
    "top_examples": [
      { "media_id": "...", "caption_preview": "...", "plays": 2400000 }
    ]
  }
}
```

---

### Query H: Hook Leaderboard

**Input:**
```json
{
  "niche_hashtags": ["#fitness"],
  "limit": 20
}
```

**Output:**
```json
{
  "hooks": [
    {
      "pattern": "Stop doing ___ (here's why)",
      "velocity_avg": 3200,
      "example": "Stop doing crunches for abs—here's why",
      "use_count": 47
    },
    {
      "pattern": "I did ___ for 30 days",
      "velocity_avg": 2800,
      "example": "I did 100 pushups for 30 days",
      "use_count": 38
    }
  ]
}
```

---

### Query I: Carousel Blueprint Extractor

**Input:**
```json
{
  "niche_hashtags": ["#marketingtips"],
  "limit": 10
}
```

**Output:**
```json
{
  "blueprints": [
    {
      "name": "Listicle (5-7 slides)",
      "structure": [
        "Slide 1: Bold title + hook question",
        "Slides 2-6: One tip per slide with icon",
        "Slide 7: CTA + 'Save for later'"
      ],
      "avg_saves": 450,
      "example_post": "media_id"
    }
  ]
}
```

---

## 4. Audio & Format Queries

### Query J: Rising Audio Tracker

**Input:**
```json
{
  "niche_creators": ["user_id_1", "user_id_2"],
  "include_explore": true
}
```

**Output:**
```json
{
  "audios": [
    {
      "music_id": "123",
      "title": "Original Sound - Artist",
      "velocity": 92,
      "freshness_days": 3,
      "reuse_rate": 0.28,
      "best_content_type": "transformation reveals",
      "preview_url": "https://..."
    }
  ]
}
```

---

### Query K: Format Shift Detector

**Input:**
```json
{
  "niche": "fitness"
}
```

**Output:**
```json
{
  "shift": {
    "this_week": { "reel": 68, "carousel": 22, "static": 10 },
    "last_week": { "reel": 55, "carousel": 30, "static": 15 },
    "trend": "Shift toward reels (+13%)",
    "recommendation": "Prioritize short-form video content",
    "proof_posts": ["media_id_1", "media_id_2"]
  }
}
```

---

## 5. Timing & Consistency Queries

### Query L: Best Posting Windows

**Input:**
```json
{
  "niche_creators": ["user_id_1", "user_id_2", "user_id_3"]
}
```

**Output:**
```json
{
  "windows": [
    { "day": "Tuesday", "hour_utc": 14, "velocity_index": 1.4, "confidence": 0.85 },
    { "day": "Saturday", "hour_utc": 10, "velocity_index": 1.3, "confidence": 0.78 }
  ],
  "avoid": [
    { "day": "Monday", "hour_utc": 6, "velocity_index": 0.6 }
  ]
}
```

---

### Query M: Content Half-Life

**Input:**
```json
{
  "media_ids": ["post_1", "post_2"]  // or niche sample
}
```

**Output:**
```json
{
  "half_life": {
    "median_days": 4.5,
    "decay_curve": "steep_then_plateau",
    "repost_window": "After 7+ days",
    "recommendation": "Remix content after 10 days for second push"
  }
}
```

---

## 6. Competitive Gap Queries

### Query N: Content Gap Finder

**Input:**
```json
{
  "niche": "fitness",
  "competitors": ["user_id_1", "user_id_2"]
}
```

**Output:**
```json
{
  "gaps": [
    {
      "topic": "Home workout for seniors",
      "competitor_coverage": 2,
      "trend_velocity": 78,
      "opportunity_score": 0.92,
      "suggested_angle": "5-minute chair exercises for mobility"
    }
  ]
}
```

---

### Query O: Overserved vs Underserved Tags

**Input:**
```json
{
  "hashtags": ["#fitness", "#homeworkout", "#corestrength"]
}
```

**Output:**
```json
{
  "analysis": [
    { "tag": "#fitness", "posts_day": 50000, "median_velocity": 120, "status": "overserved" },
    { "tag": "#corestrength", "posts_day": 800, "median_velocity": 890, "status": "underserved" }
  ]
}
```

---

## 7. Experiment System Queries

### Query P: Experiment Backlog Generator

**Input:**
```json
{
  "goals": ["followers", "saves"],
  "niche_trends": ["#mealprep", "#budgetmeals"]
}
```

**Output:**
```json
{
  "experiments": [
    {
      "week": 1,
      "variable": "hook_style",
      "control": "Statement hook",
      "variant": "Question hook",
      "success_metric": "save_rate",
      "sample_size": 4
    },
    {
      "week": 2,
      "variable": "length",
      "control": "30 seconds",
      "variant": "60 seconds",
      "success_metric": "completion_rate",
      "sample_size": 4
    }
  ]
}
```

---

### Query Q: Post-Mortem Explainer

**Input:**
```json
{
  "media_id": "your_post_123"
}
```

**Output:**
```json
{
  "analysis": {
    "performance": "above_baseline",
    "velocity_vs_avg": "+180%",
    
    "why_it_worked": [
      "Hook matched trending pattern (+40% lift)",
      "Audio was in rising phase (+25% lift)",
      "Posted in optimal window (+15% lift)"
    ],
    
    "improvements": [
      "CTA could be stronger (low save rate)",
      "Consider carousel format for this topic"
    ]
  }
}
```

---

## Frontend Pages (Influencer-Facing)

| Page | Queries Used | Key Features |
|------|-------------|--------------|
| **Niche Radar** | A, B, C | Trends, tags, topics by niche |
| **Creator Watchlist** | D, E, F | Leaderboard, lookalikes, collabs |
| **Content Briefs** | G, H, I | Trend→Brief generator, hook library |
| **Experiment Lab** | P, Q | A/B plans, post-mortems |
| **Timing & Cadence** | L, M | Best windows, half-life insights |

---

## Database Schema

```sql
-- Query results cache
CREATE TABLE query_cache (
  id UUID PRIMARY KEY,
  query_type TEXT NOT NULL,  -- 'hashtag_top50', 'content_brief', etc.
  input_hash TEXT NOT NULL,  -- Hash of input params
  result JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  UNIQUE(query_type, input_hash)
);

-- Niche definitions
CREATE TABLE niches (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  seed_hashtags TEXT[],
  seed_keywords TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tracked creators (for watchlist)
CREATE TABLE tracked_creators (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  username TEXT,
  niche_id UUID REFERENCES niches(id),
  follower_tier TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Content briefs generated
CREATE TABLE content_briefs (
  id UUID PRIMARY KEY,
  trend_type TEXT,
  trend_id TEXT,
  brief JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Experiments
CREATE TABLE experiments (
  id UUID PRIMARY KEY,
  user_id UUID,
  variable TEXT,
  control_desc TEXT,
  variant_desc TEXT,
  success_metric TEXT,
  status TEXT DEFAULT 'planned',
  results JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Implementation Priority

| Priority | Query | Reason |
|----------|-------|--------|
| **P0** | G: Trend→Brief | North star - converts data to action |
| **P0** | A: Top Hashtags | Foundation for all niche queries |
| **P1** | H: Hook Leaderboard | High value, reusable component |
| **P1** | J: Rising Audio | Core trend signal |
| **P2** | D: Creator Leaderboard | Discovery feature |
| **P2** | L: Posting Windows | Timing optimization |
| **P3** | Everything else | Build on foundation |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Data Source | Instagram Looter (RapidAPI) |
| Backend | Python FastAPI + Celery |
| Database | PostgreSQL (Supabase) |
| Cache | Redis (query results) |
| AI | OpenAI GPT-4 (brief generation) |
| Frontend | Next.js + TailwindCSS |
