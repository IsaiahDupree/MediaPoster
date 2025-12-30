# PRD: ReelTrends Instagram Analytics Suite
## TubeLab-Style Creator Tools for Instagram/Reels

**Version:** 1.0  
**Date:** December 30, 2025  
**Status:** Ready for Implementation

---

## Executive Summary

ReelTrends is a suite of 6 AI-powered creator tools designed to help Instagram/Reels creators optimize their content strategy:

1. **Best Time To Post** - Traffic curve + countdown + push reminders
2. **AI Script Generator** - Topic → 3-beat script with time budgets
3. **AI Captions Generator** - Topic → caption variants + hashtags
4. **AI Carousel Generator** - Topic → slide copy + image inspiration
5. **Viral Forecaster** - Topic → audience size/demo + viral potential
6. **Sound Analytics** - Sound → metrics + trend chart + AI prediction

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Strategy](#2-data-strategy)
3. [Feature Specifications](#3-feature-specifications)
4. [Database Schema](#4-database-schema)
5. [API Contracts](#5-api-contracts)
6. [AI Prompt Schemas](#6-ai-prompt-schemas)
7. [Implementation Phases](#7-implementation-phases)

---

## 1. Architecture Overview

### 1.1 Tech Stack

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND                                │
│  React Native (Expo) - iOS/Android                          │
│  Push: Expo Notifications / OneSignal                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND                                 │
│  FastAPI (Python) / Next.js API Routes                      │
│  Postgres (Supabase)                                        │
│  Background Jobs: BullMQ / Cloud Tasks                      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  analytics-   │   │   trends-     │   │   gen-ai-     │
│   service     │   │   service     │   │   service     │
│               │   │               │   │               │
│ • Best Time   │   │ • Sounds      │   │ • Scripts     │
│ • Post Review │   │ • Hashtags    │   │ • Captions    │
│ • Forecaster  │   │ • Global Trends│  │ • Carousels   │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 1.2 Core Services

| Service | Purpose | Dependencies |
|---------|---------|--------------|
| `analytics-service` | Best time, post analyzer, engagement forecasts | User's connected IG account |
| `trends-service` | Sounds, hashtags, global trend signals | Public data + providers |
| `gen-ai-service` | Scripts, captions, carousels | OpenAI API |

---

## 2. Data Strategy

### 2.1 Two Data Modes

The app succeeds by blending **Personalized** and **Global** data:

#### A) Personalized Data (Requires User Connection)
- Best time to post for their specific account
- Post analyzer scores (Hook/Body/Visual)
- Viral forecast for their niche
- **Source:** Instagram Insights API (Creator/Business accounts)

#### B) Global Data (No Account Access Needed)
- Trending sounds by category
- Hashtag suggestions by niche
- "Sound of the day"
- Global sound trend charts
- **Source:** Licensed providers, curated lists, user submissions

### 2.2 Data Sources

| Data Type | Source | Reliability |
|-----------|--------|-------------|
| User's follower activity | Instagram Insights API | High (official) |
| User's post history | Instagram Graph API | High (official) |
| Trending sounds | TikTok Creative Center / RapidAPI | Medium |
| Hashtag popularity | Public page sampling | Medium |
| Sound metrics | 3rd-party providers / crowd-sourced | Variable |

### 2.3 Critical Principle

> **Don't make your product depend on scraping Instagram for:**
> - Trending sounds at scale
> - Sound metrics globally  
> - Audience demographics at scale
>
> **Instead:**
> - Personalization = user's connected insights
> - Global trends = reliably accessible sources
> - Blend them in UI so it feels like one brain

---

## 3. Feature Specifications

### 3.1 Best Time To Post

**Purpose:** Show optimal posting times with traffic curve + countdown

#### Algorithm

```python
def compute_best_time(user_id: str) -> BestTimeResult:
    """
    Combines follower activity with historical post performance.
    
    score(hour) = 0.6 * normalized_follower_activity 
                + 0.4 * normalized_historical_performance
    """
    # Get follower activity by hour (from IG Insights if available)
    follower_activity = get_follower_activity_by_hour(user_id)
    
    # Get user's last 30-90 posts
    posts = get_user_posts(user_id, limit=90)
    
    # Calculate engagement rate vs hour posted
    hourly_performance = defaultdict(list)
    for post in posts:
        hour = post.published_at.hour
        er = (post.likes + post.comments) / post.reach
        hourly_performance[hour].append(er)
    
    # Compute scores for each hour
    scores = {}
    for hour in range(24):
        activity_score = normalize(follower_activity.get(hour, 0))
        perf_score = normalize(median(hourly_performance.get(hour, [0])))
        scores[hour] = 0.6 * activity_score + 0.4 * perf_score
    
    # Smooth via moving average
    smoothed = moving_average(scores, window=3)
    
    # Find peak
    peak_hour = max(smoothed, key=smoothed.get)
    
    return BestTimeResult(
        hourly_scores=smoothed,
        peak_hour=peak_hour,
        peak_score=smoothed[peak_hour],
        current_score=smoothed[current_hour()],
        should_wait=smoothed[current_hour()] < smoothed[peak_hour] * 0.8,
        countdown_to_peak=hours_until(peak_hour)
    )
```

#### UI Components
- **Traffic Curve:** 24-hour chart showing posting quality by hour
- **Peak Time Badge:** "Best time today: 12PM"
- **Countdown Timer:** "Post in 2h 34m" or "Don't post yet"
- **Push Notification:** "Your peak posting time is in 15 minutes!"

#### Data Required
- User's follower activity by hour (IG Insights)
- User's historical posts with timestamps + metrics
- Current time + timezone

---

### 3.2 AI Script Generator

**Purpose:** Generate 3-beat video scripts with time budgets

#### Timing Budgets by Length

| Length | Build-up | Punchline | CTA | Total |
|--------|----------|-----------|-----|-------|
| Short | 8s | 8s | 6s | 22s |
| Medium | 15s | 15s | 15s | 45s |
| Long | 25s | 25s | 15s | 65s |

#### Input Schema

```typescript
interface ScriptRequest {
  topic: string;           // "How to grow on Instagram"
  tone: "casual" | "professional" | "funny" | "urgent";
  length: "short" | "medium" | "long";
  format: "reel" | "short" | "talking_head" | "voiceover";
  niche?: string;          // "marketing", "fitness", etc.
  hook_style?: "question" | "bold_claim" | "controversy" | "story";
}
```

#### Output Schema

```typescript
interface ScriptResult {
  beats: [
    {
      name: "build_up",
      duration_seconds: number,
      script: string,
      visual_notes: string,
      word_count: number
    },
    {
      name: "punchline", 
      duration_seconds: number,
      script: string,
      visual_notes: string,
      word_count: number
    },
    {
      name: "cta",
      duration_seconds: number,
      script: string,
      visual_notes: string,
      word_count: number
    }
  ],
  total_duration: number,
  estimated_word_count: number,
  hooks: string[],  // 3 alternative hook options
  hashtag_suggestions: string[]
}
```

---

### 3.3 AI Captions Generator

**Purpose:** Generate caption variants + bucketed hashtags

#### Caption Styles (Always Generate All 3)

| Style | Description | Example Tone |
|-------|-------------|--------------|
| Clean + Credible | No hype, professional | "Here's what I learned..." |
| Punchy + Meme-y | Viral energy, bold | "POV: You finally get it 🔥" |
| Teach-Mode | Micro-thread, educational | "1/ The secret to..." |

#### Hashtag Buckets

| Bucket | Count | Purpose |
|--------|-------|---------|
| Niche Tags | 5 | Target your specific audience |
| Format Tags | 3 | Content type (#reels, #tutorial) |
| Discovery Tags | 2 | Broad reach (#viral, #trending) |

#### Output Schema

```typescript
interface CaptionsResult {
  captions: [
    {
      style: "clean",
      caption: string,
      emoji_usage: "minimal" | "moderate" | "heavy"
    },
    {
      style: "punchy", 
      caption: string,
      emoji_usage: "heavy"
    },
    {
      style: "teach_mode",
      caption: string,
      emoji_usage: "moderate"
    }
  ],
  hashtags: {
    niche: string[],      // 5 tags
    format: string[],     // 3 tags
    discovery: string[]   // 2 tags
  },
  total_hashtag_count: 10,
  cta_suggestions: string[]
}
```

---

### 3.4 AI Carousel Generator

**Purpose:** Generate slide copy + image inspiration for carousels

#### Slide Structure (3-5 slides)

| Slide | Purpose | Content Type |
|-------|---------|--------------|
| 1 | Hook | Question or bold claim |
| 2-3 | Value | Steps, framework, examples |
| 4-5 | CTA | Takeaway + action |

#### Output Schema

```typescript
interface CarouselResult {
  title: string,
  slides: [
    {
      slide_number: number,
      purpose: "hook" | "value" | "cta",
      headline: string,           // Big text
      body_text: string,          // Supporting copy
      image_inspo: string,        // Visual suggestion
      color_suggestion: string,   // Hex color
      layout: "text_only" | "text_image" | "quote"
    }
  ],
  cover_text: string,             // For the first slide thumbnail
  design_style: "minimal" | "bold" | "gradient" | "photo_overlay"
}
```

---

### 3.5 Viral Forecaster

**Purpose:** Predict viral potential + estimate audience demographics

#### Scoring Model

```python
def forecast_viral_potential(user_id: str, content: ContentDraft) -> ForecastResult:
    """
    Forecast = probability of outperforming user's baseline.
    """
    # User's baseline
    baseline = get_user_baseline(user_id)  # median views/ER of last N posts
    
    # Feature extraction
    features = {
        "topic_similarity": cosine_sim(content.topic, user.past_winners),
        "hook_strength": llm_rubric_score(content.hook),  # 1-10
        "format_fit": format_match_score(content.format, user.best_formats),
        "sound_quality": sound_trend_score(content.sound_id) if content.sound_id else 0.5,
        "post_time_score": best_time_score(user_id, content.planned_time)
    }
    
    # Weighted score
    weights = {
        "topic_similarity": 0.25,
        "hook_strength": 0.30,
        "format_fit": 0.20,
        "sound_quality": 0.15,
        "post_time_score": 0.10
    }
    
    raw_score = sum(features[k] * weights[k] for k in weights)
    
    # Convert to potential level
    if raw_score >= 0.75:
        potential = "high"
        engagement_range = (baseline.er * 1.5, baseline.er * 3.0)
    elif raw_score >= 0.50:
        potential = "medium"
        engagement_range = (baseline.er * 0.8, baseline.er * 1.5)
    else:
        potential = "low"
        engagement_range = (baseline.er * 0.3, baseline.er * 0.8)
    
    return ForecastResult(
        viral_potential=potential,
        confidence=raw_score,
        feature_scores=features,
        estimated_engagement_range=engagement_range,
        audience_demo=user.audience_insights,  # From IG Insights
        improvement_suggestions=generate_suggestions(features)
    )
```

#### Output Schema

```typescript
interface ForecastResult {
  viral_potential: "low" | "medium" | "high";
  confidence: number;  // 0-1
  
  // Audience estimates (from user's own audience insights)
  audience: {
    estimated_reach: { min: number, max: number },
    age_breakdown: Record<string, number>,  // "18-24": 35%
    gender_split: { male: number, female: number, other: number },
    top_countries: string[]
  },
  
  // Engagement predictions
  engagement: {
    likes_range: [number, number],
    comments_range: [number, number],
    saves_range: [number, number],
    shares_range: [number, number],
    er_range: [number, number]  // e.g., [4, 6] for 4-6%
  },
  
  // What's driving the score
  feature_scores: {
    hook_strength: number,
    topic_relevance: number,
    format_fit: number,
    timing_score: number,
    sound_quality: number
  },
  
  // How to improve
  suggestions: string[]
}
```

---

### 3.6 Sound Analytics

**Purpose:** Show sound metrics + trend chart + AI prediction

#### Data Model for Sounds

```python
@dataclass
class SoundMetrics:
    sound_id: str
    platform: str  # "instagram" | "tiktok"
    title: str
    artist: str
    duration_seconds: int
    
    # Current metrics
    total_uses: int
    total_views: int
    total_likes: int
    total_comments: int
    engagement_rate: float
    
    # Trend data (last 30 days)
    daily_uses: List[int]          # [day1, day2, ...]
    daily_views: List[int]
    
    # Forecast (next 14 days)
    forecast_uses: List[int]
    forecast_confidence: float
    
    # Geographic distribution
    top_countries: List[Tuple[str, float]]  # [("US", 0.45), ("UK", 0.12)]
    
    # Classification
    trend_status: str  # "rising" | "peak" | "declining" | "stable"
    category: str      # "trending" | "evergreen" | "niche"
    genres: List[str]
```

#### Trend Forecasting

```python
from prophet import Prophet
import pandas as pd

def forecast_sound_trend(sound_id: str, days_ahead: int = 14) -> SoundForecast:
    """
    Forecast sound usage using Prophet/ARIMA/exponential smoothing.
    """
    # Get historical data
    timeseries = get_sound_timeseries(sound_id, days=60)
    
    # Prepare for Prophet
    df = pd.DataFrame({
        'ds': timeseries.dates,
        'y': timeseries.uses
    })
    
    # Fit model
    model = Prophet(
        changepoint_prior_scale=0.05,
        seasonality_mode='multiplicative'
    )
    model.fit(df)
    
    # Forecast
    future = model.make_future_dataframe(periods=days_ahead)
    forecast = model.predict(future)
    
    return SoundForecast(
        observed=timeseries.uses,
        predicted=forecast['yhat'].tail(days_ahead).tolist(),
        lower_bound=forecast['yhat_lower'].tail(days_ahead).tolist(),
        upper_bound=forecast['yhat_upper'].tail(days_ahead).tolist(),
        trend_direction="rising" if forecast['trend'].iloc[-1] > forecast['trend'].iloc[-days_ahead] else "declining"
    )
```

#### UI Components
- **Metrics Card:** Uses, Views, Likes, Comments, ER%
- **Trend Chart:** 
  - Solid line = observed data
  - Dotted line = AI forecast
  - Shaded area = confidence interval
- **Geographic Map:** Top countries using the sound
- **Save Button:** Add to user's saved sounds
- **Similar Sounds:** Recommendations

---

## 4. Database Schema

```sql
-- =====================================================
-- USERS & ACCOUNTS
-- =====================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ig_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ig_user_id VARCHAR(50) NOT NULL,
    username VARCHAR(50) NOT NULL,
    account_type VARCHAR(20),  -- 'creator' | 'business'
    access_token TEXT,
    token_expires_at TIMESTAMPTZ,
    permissions_scope TEXT[],
    follower_count INT,
    following_count INT,
    media_count INT,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, ig_user_id)
);

-- =====================================================
-- USER'S POST DATA
-- =====================================================

CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ig_account_id UUID REFERENCES ig_accounts(id) ON DELETE CASCADE,
    ig_media_id VARCHAR(50) NOT NULL,
    media_type VARCHAR(20),  -- 'IMAGE' | 'VIDEO' | 'CAROUSEL'
    media_url TEXT,
    thumbnail_url TEXT,
    caption TEXT,
    permalink TEXT,
    
    -- Timing
    published_at TIMESTAMPTZ NOT NULL,
    hour_of_day INT,  -- 0-23
    day_of_week INT,  -- 0-6
    
    -- Metrics snapshot
    reach INT,
    impressions INT,
    likes INT,
    comments INT,
    saves INT,
    shares INT,
    engagement_rate DECIMAL(5,2),
    
    -- Computed scores
    hook_score DECIMAL(3,1),
    body_score DECIMAL(3,1),
    visual_score DECIMAL(3,1),
    overall_score DECIMAL(3,1),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ig_account_id, ig_media_id)
);

CREATE INDEX idx_posts_account_time ON posts(ig_account_id, published_at DESC);
CREATE INDEX idx_posts_hour ON posts(ig_account_id, hour_of_day);

-- =====================================================
-- BEST TIME DATA
-- =====================================================

CREATE TABLE hourly_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ig_account_id UUID REFERENCES ig_accounts(id) ON DELETE CASCADE,
    day_of_week INT NOT NULL,  -- 0=Sunday, 6=Saturday
    hour INT NOT NULL,         -- 0-23
    activity_score DECIMAL(5,2),  -- Normalized 0-1
    post_count INT DEFAULT 0,
    avg_engagement_rate DECIMAL(5,2),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ig_account_id, day_of_week, hour)
);

CREATE TABLE best_time_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ig_account_id UUID REFERENCES ig_accounts(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    hourly_scores JSONB,  -- {"0": 0.45, "1": 0.32, ...}
    peak_hour INT,
    peak_score DECIMAL(5,2),
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ig_account_id, date)
);

-- =====================================================
-- SOUNDS & TRENDS
-- =====================================================

CREATE TABLE sounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(20) NOT NULL,  -- 'instagram' | 'tiktok'
    sound_id VARCHAR(100) NOT NULL,
    title VARCHAR(500),
    artist VARCHAR(255),
    duration_seconds INT,
    cover_url TEXT,
    
    -- Current metrics
    total_uses BIGINT DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    total_likes BIGINT DEFAULT 0,
    total_comments BIGINT DEFAULT 0,
    engagement_rate DECIMAL(5,2),
    
    -- Classification
    trend_status VARCHAR(20),  -- 'rising' | 'peak' | 'declining' | 'stable'
    category VARCHAR(50),
    genres TEXT[],
    
    -- Geographic
    top_countries JSONB,  -- [{"country": "US", "share": 0.45}, ...]
    
    first_seen_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, sound_id)
);

CREATE TABLE sound_timeseries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sound_id UUID REFERENCES sounds(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    uses INT DEFAULT 0,
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    engagement_rate DECIMAL(5,2),
    UNIQUE(sound_id, date)
);

CREATE INDEX idx_sound_ts ON sound_timeseries(sound_id, date DESC);

CREATE TABLE sound_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sound_id UUID REFERENCES sounds(id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    predicted_uses INT,
    lower_bound INT,
    upper_bound INT,
    confidence DECIMAL(3,2),
    model_version VARCHAR(20),
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sound_id, forecast_date)
);

CREATE TABLE saved_sounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    sound_id UUID REFERENCES sounds(id) ON DELETE CASCADE,
    saved_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    UNIQUE(user_id, sound_id)
);

-- =====================================================
-- AI GENERATED CONTENT
-- =====================================================

CREATE TABLE generated_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(20) NOT NULL,  -- 'script' | 'caption' | 'carousel'
    
    -- Input
    input_topic TEXT NOT NULL,
    input_params JSONB,  -- {tone, length, format, niche, ...}
    
    -- Output
    output_json JSONB NOT NULL,
    
    -- Metadata
    model_used VARCHAR(50),
    tokens_used INT,
    generation_time_ms INT,
    
    -- User feedback
    rating INT,  -- 1-5
    was_used BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_generated_user ON generated_content(user_id, created_at DESC);
CREATE INDEX idx_generated_type ON generated_content(content_type);

-- =====================================================
-- POST REVIEWS / ANALYZER
-- =====================================================

CREATE TABLE post_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Input (can be uploaded or from their feed)
    source VARCHAR(20),  -- 'upload' | 'ig_post'
    ig_media_id VARCHAR(50),
    video_url TEXT,
    caption TEXT,
    
    -- Scores (1-10)
    hook_score DECIMAL(3,1),
    body_score DECIMAL(3,1),
    visual_score DECIMAL(3,1),
    audio_score DECIMAL(3,1),
    pacing_score DECIMAL(3,1),
    cta_score DECIMAL(3,1),
    overall_score DECIMAL(3,1),
    
    -- Detailed feedback
    scores_breakdown JSONB,
    suggestions JSONB,
    strengths TEXT[],
    weaknesses TEXT[],
    
    -- AI analysis
    detected_hooks TEXT[],
    detected_cta TEXT,
    transcript TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- VIRAL FORECASTS
-- =====================================================

CREATE TABLE viral_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Content being forecasted
    content_draft JSONB,  -- {topic, hook, format, sound_id, planned_time}
    
    -- Predictions
    viral_potential VARCHAR(20),  -- 'low' | 'medium' | 'high'
    confidence DECIMAL(3,2),
    
    -- Feature scores
    feature_scores JSONB,  -- {hook_strength, topic_relevance, ...}
    
    -- Estimates
    estimated_reach JSONB,      -- {min, max}
    estimated_engagement JSONB, -- {likes, comments, saves, shares, er}
    
    -- Audience
    audience_demo JSONB,  -- {age, gender, countries}
    
    -- Suggestions
    suggestions TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- HASHTAGS
-- =====================================================

CREATE TABLE hashtags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag VARCHAR(100) NOT NULL UNIQUE,
    
    -- Metrics
    total_posts BIGINT,
    avg_engagement_rate DECIMAL(5,2),
    
    -- Classification
    category VARCHAR(50),  -- 'niche' | 'format' | 'discovery'
    niches TEXT[],
    
    -- Trend
    trend_status VARCHAR(20),
    velocity DECIMAL(8,2),  -- posts/day change
    
    last_updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE hashtag_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche VARCHAR(100) NOT NULL,
    bucket VARCHAR(20) NOT NULL,  -- 'niche' | 'format' | 'discovery'
    hashtags TEXT[] NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(niche, bucket)
);
```

---

## 5. API Contracts

### 5.1 Best Time To Post

```typescript
// GET /api/best-time/{ig_account_id}
interface BestTimeResponse {
  success: boolean;
  data: {
    hourly_scores: Record<number, number>;  // 0-23 -> 0-1 score
    peak_hour: number;
    peak_score: number;
    current_hour: number;
    current_score: number;
    should_wait: boolean;
    countdown_minutes: number;
    next_peak: string;  // ISO timestamp
    chart_data: {
      labels: string[];  // ["12AM", "1AM", ...]
      values: number[];
    };
  };
  computed_at: string;
}

// POST /api/best-time/notify
interface BestTimeNotifyRequest {
  ig_account_id: string;
  minutes_before: number;  // 15, 30, 60
}
```

### 5.2 AI Script Generator

```typescript
// POST /api/generate/script
interface ScriptRequest {
  topic: string;
  tone: "casual" | "professional" | "funny" | "urgent";
  length: "short" | "medium" | "long";
  format: "reel" | "short" | "talking_head" | "voiceover";
  niche?: string;
  hook_style?: "question" | "bold_claim" | "controversy" | "story";
}

interface ScriptResponse {
  success: boolean;
  data: {
    beats: Array<{
      name: string;
      duration_seconds: number;
      script: string;
      visual_notes: string;
      word_count: number;
    }>;
    total_duration: number;
    hooks: string[];
    hashtag_suggestions: string[];
  };
  generation_id: string;
}
```

### 5.3 AI Captions Generator

```typescript
// POST /api/generate/captions
interface CaptionsRequest {
  topic: string;
  tone?: string;
  niche?: string;
  include_hashtags: boolean;
  emoji_level?: "minimal" | "moderate" | "heavy";
}

interface CaptionsResponse {
  success: boolean;
  data: {
    captions: Array<{
      style: string;
      caption: string;
      character_count: number;
    }>;
    hashtags: {
      niche: string[];
      format: string[];
      discovery: string[];
    };
    cta_suggestions: string[];
  };
}
```

### 5.4 AI Carousel Generator

```typescript
// POST /api/generate/carousel
interface CarouselRequest {
  topic: string;
  slide_count: 3 | 4 | 5;
  style?: "minimal" | "bold" | "gradient";
  niche?: string;
}

interface CarouselResponse {
  success: boolean;
  data: {
    title: string;
    slides: Array<{
      slide_number: number;
      purpose: string;
      headline: string;
      body_text: string;
      image_inspo: string;
      color_suggestion: string;
    }>;
    cover_text: string;
    design_style: string;
  };
}
```

### 5.5 Viral Forecaster

```typescript
// POST /api/forecast/viral
interface ViralForecastRequest {
  ig_account_id: string;
  content: {
    topic: string;
    hook?: string;
    format: string;
    sound_id?: string;
    planned_time?: string;  // ISO timestamp
  };
}

interface ViralForecastResponse {
  success: boolean;
  data: {
    viral_potential: "low" | "medium" | "high";
    confidence: number;
    audience: {
      estimated_reach: { min: number; max: number };
      age_breakdown: Record<string, number>;
      gender_split: { male: number; female: number };
      top_countries: string[];
    };
    engagement: {
      likes_range: [number, number];
      comments_range: [number, number];
      er_range: [number, number];
    };
    feature_scores: Record<string, number>;
    suggestions: string[];
  };
}
```

### 5.6 Sound Analytics

```typescript
// GET /api/sounds/{sound_id}
interface SoundResponse {
  success: boolean;
  data: {
    sound_id: string;
    title: string;
    artist: string;
    duration_seconds: number;
    cover_url: string;
    
    metrics: {
      total_uses: number;
      total_views: number;
      total_likes: number;
      engagement_rate: number;
    };
    
    trend: {
      status: "rising" | "peak" | "declining" | "stable";
      velocity: number;  // % change per day
      chart_data: {
        dates: string[];
        observed: number[];
        forecast: number[];
        forecast_lower: number[];
        forecast_upper: number[];
      };
    };
    
    geography: {
      top_countries: Array<{ country: string; share: number }>;
    };
    
    similar_sounds: Array<{
      sound_id: string;
      title: string;
      similarity: number;
    }>;
  };
}

// POST /api/sounds/save
interface SaveSoundRequest {
  user_id: string;
  sound_id: string;
  notes?: string;
}

// GET /api/sounds/trending?category={category}
interface TrendingSoundsResponse {
  success: boolean;
  data: {
    category: string;
    sounds: Array<{
      sound_id: string;
      title: string;
      artist: string;
      uses_today: number;
      trend_status: string;
      engagement_rate: number;
    }>;
    sound_of_the_day: {
      sound_id: string;
      title: string;
      reason: string;
    };
  };
}
```

---

## 6. AI Prompt Schemas

### 6.1 Script Generator Prompt

```python
SCRIPT_SYSTEM_PROMPT = """You are an expert short-form video scriptwriter.
Generate scripts that are engaging, authentic, and optimized for Reels/TikTok.

Output format: JSON only, no markdown.
"""

def generate_script_prompt(request: ScriptRequest) -> str:
    timing = {
        "short": {"buildup": 8, "punchline": 8, "cta": 6},
        "medium": {"buildup": 15, "punchline": 15, "cta": 15},
        "long": {"buildup": 25, "punchline": 25, "cta": 15}
    }[request.length]
    
    return f"""Create a {request.length} video script about: {request.topic}

Tone: {request.tone}
Format: {request.format}
Hook style: {request.hook_style or "question"}

Timing budget:
- Build-up: {timing['buildup']} seconds
- Punchline: {timing['punchline']} seconds  
- CTA: {timing['cta']} seconds

Output JSON:
{{
  "beats": [
    {{
      "name": "build_up",
      "duration_seconds": {timing['buildup']},
      "script": "The actual script text...",
      "visual_notes": "What to show on screen",
      "word_count": <number>
    }},
    {{
      "name": "punchline",
      "duration_seconds": {timing['punchline']},
      "script": "...",
      "visual_notes": "...",
      "word_count": <number>
    }},
    {{
      "name": "cta",
      "duration_seconds": {timing['cta']},
      "script": "...",
      "visual_notes": "...",
      "word_count": <number>
    }}
  ],
  "hooks": ["Alternative hook 1", "Alternative hook 2", "Alternative hook 3"],
  "hashtag_suggestions": ["#tag1", "#tag2", ...]
}}

Rules:
- ~2.5 words per second speaking pace
- Hook must grab attention in first 2 seconds
- End with clear CTA
- Be conversational, not salesy
"""
```

### 6.2 Captions Generator Prompt

```python
CAPTIONS_SYSTEM_PROMPT = """You are a social media caption expert.
Generate 3 caption variants: Clean/Credible, Punchy/Meme-y, Teach-Mode.

Output format: JSON only.
"""

def generate_captions_prompt(request: CaptionsRequest) -> str:
    return f"""Create 3 Instagram captions for content about: {request.topic}

Niche: {request.niche or "general"}
Emoji level: {request.emoji_level or "moderate"}

Output JSON:
{{
  "captions": [
    {{
      "style": "clean",
      "caption": "Professional, no hype, credible...",
      "character_count": <number>
    }},
    {{
      "style": "punchy",
      "caption": "Bold, viral energy, meme-y...",
      "character_count": <number>
    }},
    {{
      "style": "teach_mode",
      "caption": "Educational micro-thread style...",
      "character_count": <number>
    }}
  ],
  "hashtags": {{
    "niche": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
    "format": ["#reels", "#tutorial", "#tips"],
    "discovery": ["#viral", "#trending"]
  }},
  "cta_suggestions": [
    "Save this for later 📌",
    "Drop a 🔥 if this helped",
    "Tag someone who needs this"
  ]
}}

Rules:
- Clean: No excessive emojis, professional tone
- Punchy: Bold claims, trending phrases, heavy emojis
- Teach-Mode: Numbered points or mini-thread format
- Each caption should work standalone
- Max 2200 characters per caption
"""
```

### 6.3 Carousel Generator Prompt

```python
CAROUSEL_SYSTEM_PROMPT = """You are a carousel content strategist.
Create slide-by-slide content with headlines, body text, and visual suggestions.

Output format: JSON only.
"""

def generate_carousel_prompt(request: CarouselRequest) -> str:
    return f"""Create a {request.slide_count}-slide carousel about: {request.topic}

Style: {request.style or "minimal"}
Niche: {request.niche or "general"}

Output JSON:
{{
  "title": "Carousel title",
  "slides": [
    {{
      "slide_number": 1,
      "purpose": "hook",
      "headline": "Big bold text",
      "body_text": "Supporting copy",
      "image_inspo": "Visual suggestion for this slide",
      "color_suggestion": "#HEXCODE"
    }},
    // ... more slides
  ],
  "cover_text": "Text for the cover/thumbnail",
  "design_style": "{request.style or 'minimal'}"
}}

Structure:
- Slide 1: Hook (question or bold claim)
- Slides 2-{request.slide_count - 1}: Value (steps, framework, examples)
- Slide {request.slide_count}: CTA (takeaway + action)

Rules:
- Headlines: 3-6 words max
- Body text: 1-2 sentences
- Each slide should be scannable in 2 seconds
- Use contrast colors for readability
"""
```

### 6.4 Post Analyzer Prompt

```python
POST_ANALYZER_PROMPT = """You are a video content analyst.
Score the video on multiple dimensions and provide actionable feedback.

Output format: JSON only.
"""

def generate_analysis_prompt(transcript: str, caption: str) -> str:
    return f"""Analyze this video content:

TRANSCRIPT:
{transcript}

CAPTION:
{caption}

Output JSON:
{{
  "scores": {{
    "hook": <1-10>,
    "body": <1-10>,
    "visual": <1-10>,
    "audio": <1-10>,
    "pacing": <1-10>,
    "cta": <1-10>,
    "overall": <1-10>
  }},
  "breakdown": {{
    "hook": {{
      "score": <1-10>,
      "reason": "Why this score",
      "detected_hook": "The hook phrase used"
    }},
    // ... for each category
  }},
  "strengths": ["Strength 1", "Strength 2"],
  "weaknesses": ["Weakness 1", "Weakness 2"],
  "suggestions": [
    "Specific improvement suggestion 1",
    "Specific improvement suggestion 2"
  ]
}}

Scoring criteria:
- Hook (1-10): Does it grab attention in first 3 seconds?
- Body (1-10): Is the content valuable and engaging?
- Visual (1-10): Are visuals compelling and well-composed?
- Audio (1-10): Is audio clear with good pacing?
- Pacing (1-10): Does it maintain attention throughout?
- CTA (1-10): Is there a clear call to action?
"""
```

---

## 7. Implementation Phases

### Phase 1: MVP (Week 1-2)
*Fastest path to "feels real"*

| Feature | Priority | Complexity |
|---------|----------|------------|
| AI Script Generator | P0 | Low |
| AI Captions Generator | P0 | Low |
| AI Carousel Generator | P0 | Low |
| Hashtag Recommender | P0 | Low |
| Best Time (post history only) | P1 | Medium |

**Deliverables:**
- 4 working AI generators
- Basic best time using user's past post timestamps + performance
- No Instagram connection required yet

### Phase 2: Smart Features (Week 3-4)
*Makes it feel intelligent*

| Feature | Priority | Complexity |
|---------|----------|------------|
| Post Analyzer | P0 | Medium |
| Instagram Account Connection | P0 | Medium |
| Enhanced Best Time (with IG Insights) | P1 | Medium |
| Push Notifications | P1 | Low |

**Deliverables:**
- Upload video → get scored feedback
- Connect IG Creator/Business account
- Notifications for peak posting times

### Phase 3: Flex Features (Week 5-6)
*Differentiators*

| Feature | Priority | Complexity |
|---------|----------|------------|
| Sound Analytics | P0 | High |
| Sound Trend Forecasting | P1 | High |
| Viral Forecaster | P1 | Medium |
| Category Browsing | P2 | Medium |

**Deliverables:**
- Sound metrics + trend charts
- AI-powered viral potential predictions
- Browse by category (Technology, Barbers, etc.)

### Phase 4: Growth (Week 7+)
*Network effects*

| Feature | Priority | Complexity |
|---------|----------|------------|
| Personalized "For You" Feed | P1 | High |
| Saved Sounds Library | P1 | Low |
| User-submitted Trend Signals | P2 | Medium |
| Chrome Extension | P2 | Medium |

---

## 8. Success Metrics

### Engagement Metrics
- **DAU/MAU Ratio:** Target >30%
- **Features Used Per Session:** Target >2
- **Script/Caption Generations Per User:** Target 5/week

### Quality Metrics
- **Best Time Accuracy:** Post within suggested window correlates with +20% ER
- **Forecast Accuracy:** Viral predictions match outcomes >60% of time
- **Content Used Rate:** >40% of generated content gets posted

### Growth Metrics
- **Account Connection Rate:** >50% of users connect IG
- **Sound Saves Per User:** 10+ per month
- **Notification CTR:** >15%

---

## 9. Risk Mitigation

### Data Access Risks
| Risk | Mitigation |
|------|------------|
| IG API rate limits | Cache aggressively, batch requests |
| Sound data availability | Multiple sources + crowd-sourcing fallback |
| User doesn't connect IG | Core features work without connection |

### Technical Risks
| Risk | Mitigation |
|------|------------|
| AI hallucinations | Structured output schemas + validation |
| Forecast accuracy | Confidence intervals + clear disclaimers |
| Scale issues | Start with daily batch processing |

### Business Risks
| Risk | Mitigation |
|------|------------|
| Platform ToS changes | Don't depend on scraping |
| Competition | Focus on UX quality + speed |
| User churn | Push notifications + value reminders |

---

## 10. Appendix

### A. Instagram Permissions Needed

| Permission | Purpose |
|------------|---------|
| `instagram_basic` | Profile info |
| `instagram_content_publish` | Not needed for analytics |
| `instagram_manage_insights` | Best time, post metrics |
| `pages_read_engagement` | For connected FB Page |

### B. Third-Party Services

| Service | Purpose | Cost |
|---------|---------|------|
| OpenAI GPT-4 | Content generation | $0.03/1K tokens |
| Supabase | Database + Auth | Free tier |
| OneSignal | Push notifications | Free tier |
| RapidAPI | Sound/hashtag data | Variable |

### C. Competitive Landscape

| Competitor | Strengths | Weaknesses |
|------------|-----------|------------|
| TubeLab | Sound analytics | Complex UI |
| Planoly | Scheduling | Limited AI |
| Later | Multi-platform | No sound trends |
| Flick | Hashtags | Single focus |

---

*Document Version: 1.0*  
*Last Updated: December 30, 2025*  
*Author: MediaPoster AI System*
