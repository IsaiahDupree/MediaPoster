# PRD: Trend Flash Video System

**Version:** 1.0  
**Date:** January 26, 2026  
**Status:** Implementation Ready  
**Priority:** High

---

## Executive Summary

A real-time trend detection → video generation pipeline that detects trending topics, scores them, generates video content, and ships within the same attention window (30-60 minutes).

### Core Philosophy
```
Detect → Angle → Ship Video (within same attention window)
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TREND FLASH PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DETECT (15-60min)          DECIDE              GENERATE (10-30min)     │
│  ┌────────────┐           ┌────────────┐        ┌────────────┐          │
│  │ Scrape     │───────────▶│ Score     │────────▶│ Remotion   │          │
│  │ Comments   │           │ Topics    │        │ Fast Ship  │          │
│  └────────────┘           └────────────┘        └────────────┘          │
│        │                        │                     │                  │
│        ▼                        ▼                     ▼                  │
│  ┌────────────┐           ┌────────────┐        ┌────────────┐          │
│  │ Cluster    │           │ Select    │        │ Sora       │          │
│  │ Topics     │           │ Top 1-3   │        │ Hero       │          │
│  └────────────┘           └────────────┘        └────────────┘          │
│        │                        │                     │                  │
│        ▼                        ▼                     ▼                  │
│  ┌────────────┐           ┌────────────┐        ┌────────────┐          │
│  │ Track      │           │ Generate  │        │ Post +     │          │
│  │ Velocity   │           │ Script    │        │ Capture    │          │
│  └────────────┘           └────────────┘        └────────────┘          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Requirements

### TF-001: Trend Detection
**Priority:** P0 (Critical)

Detect trending topics every 15-60 minutes.

#### Data Sources
| Source | Method | Data |
|--------|--------|------|
| Instagram Comments | Platform connector | Post comments |
| TikTok Comments | Platform connector | Video comments |
| Twitter Mentions | Platform connector | Mentions, replies |
| Competitor Posts | Scraper | Topic patterns |
| Hashtag Trends | API | Rising hashtags |

#### Clustering
- Use embeddings (OpenAI text-embedding-3-small)
- Simple K-means or DBSCAN clustering
- Group similar topics across platforms

#### Velocity Tracking
```python
velocity = mentions_per_hour
unique_authors = distinct_commenters
cross_platform_count = len(platforms_with_topic)
```

---

### TF-002: Trend Scoring
**Priority:** P0 (Critical)

Auto-score topics to pick 1-3 to ship.

#### Scoring Formula
```python
trend_score = velocity * cross_platform_multiplier * intent_multiplier

# Multipliers
cross_platform_multiplier:
  - 1 platform: 1.0
  - 2 platforms: 1.3 (+30%)
  - 3+ platforms: 1.6 (+60%)

intent_multiplier:
  - No intent signals: 1.0
  - Contains "how do i", "what tool", "tutorial", "template": 1.5 (+50%)
  - Multiple intent signals: 1.8 (+80%)
```

#### Intent Keywords
```python
INTENT_KEYWORDS = [
    "how do i", "how to", "what tool", "which app",
    "tutorial", "template", "workflow", "step by step",
    "show me", "teach me", "help me", "guide",
    "what's the best", "recommend", "tips for"
]
```

---

### TF-003: Content Generation
**Priority:** P0 (Critical)

Generate video content from trend clusters.

#### Output Per Trend
1. **1 short video script** (trend flash template)
2. **3 title options** (platform-specific)
3. **On-screen captions** (short, punchy overlays)
4. **10 comment replies** (addressing top questions)
5. **Follow-up prompt** ("want part 2 on ___?")

#### Trend Flash Script Template
```
HOOK (0-2s):
"everyone's talking about [trend] today — here's the part they're missing."

CONTEXT (2-7s):
"it's popping up on [platform1], [platform2], and the comments are all saying [top question]."

TAKE (7-20s):
"the real move is [one rule]."

ACTION (20-35s):
"do this: step 1, step 2, step 3."

CTA (last 3s):
"comment [keyword] and i'll send the exact workflow."
```

#### Script Variants
1. **Educational**: Clear, helpful, actionable
2. **Contrarian**: "everyone's wrong about..."
3. **Meme-leaning**: Lighter, more casual, trend-aware

---

### TF-004: Video Production
**Priority:** P0 (Critical)

Two video production paths:

#### Remotion "Fast Ship" (Primary)
- **Turnaround:** 10-30 minutes
- **Format:** 30-45s vertical video
- **Components:** Text overlays + B-roll + voice (or clone)
- **Use case:** All detected trends

#### Sora "Hero" (Secondary)
- **Turnaround:** 1-2 hours
- **Format:** Cinematic @isaiahdupree character
- **Use case:** High-score trends, evergreen spikes only
- **Trigger:** trend_score > 80

---

### TF-005: Multi-Platform Posting
**Priority:** P1 (High)

Post to each platform with platform-specific optimization.

#### Platform Captions
| Platform | Style | Hashtags | CTA |
|----------|-------|----------|-----|
| TikTok | Casual, emoji | 3-5 trending | Comment keyword |
| Instagram | Clean, hooks | 5-10 niche | Comment keyword |
| YouTube Shorts | SEO-focused | Description | Subscribe CTA |
| Twitter | Punchy, no hashtags | None | Reply thread |

#### Cross-Platform Mention
```
"i'm seeing this on ig + tiktok today…"
```
This line boosts perceived relevance (recency + consensus).

---

### TF-006: Learning Loop
**Priority:** P1 (High)

Feed performance back into scoring.

#### Performance Metrics
| Metric | Weight | Signal |
|--------|--------|--------|
| Saves | 30% | High intent |
| Shares | 25% | Viral potential |
| Profile Taps | 20% | Interest in creator |
| Comments with purchase intent | 25% | Conversion signal |

#### Purchase Intent Keywords
```python
PURCHASE_INTENT = [
    "link", "where", "how much", "price",
    "dm me", "send me", "want this", "need this",
    "sign up", "join", "course", "coaching"
]
```

---

## Database Schema

```sql
-- Detected trend clusters
CREATE TABLE trend_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Topic info
    topic TEXT NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    summary TEXT,
    
    -- Velocity metrics
    velocity FLOAT DEFAULT 0,
    mentions_count INTEGER DEFAULT 0,
    unique_authors INTEGER DEFAULT 0,
    
    -- Cross-platform
    platforms TEXT[] DEFAULT '{}',
    platform_count INTEGER DEFAULT 1,
    
    -- Intent signals
    top_questions TEXT[] DEFAULT '{}',
    intent_keywords_found TEXT[] DEFAULT '{}',
    intent_score FLOAT DEFAULT 1.0,
    
    -- Scoring
    trend_score FLOAT DEFAULT 0,
    cross_platform_multiplier FLOAT DEFAULT 1.0,
    intent_multiplier FLOAT DEFAULT 1.0,
    
    -- Status
    status TEXT DEFAULT 'detected', -- detected, selected, generating, shipped, archived
    shipped_at TIMESTAMP,
    
    -- Timestamps
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Generated content from trends
CREATE TABLE trend_flash_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID REFERENCES trend_clusters(id),
    
    -- Script
    script_hook TEXT,
    script_context TEXT,
    script_take TEXT,
    script_action TEXT,
    script_cta TEXT,
    script_variant TEXT DEFAULT 'educational', -- educational, contrarian, meme
    
    -- Titles (platform-specific)
    title_tiktok TEXT,
    title_instagram TEXT,
    title_youtube TEXT,
    title_twitter TEXT,
    
    -- Captions
    captions JSONB DEFAULT '[]', -- [{time: 0, text: "..."}, ...]
    
    -- Comment replies
    comment_replies TEXT[] DEFAULT '{}',
    follow_up_prompt TEXT,
    
    -- Video
    video_type TEXT DEFAULT 'remotion', -- remotion, sora
    video_path TEXT,
    video_url TEXT,
    
    -- Status
    status TEXT DEFAULT 'pending', -- pending, generating, ready, posted
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Performance tracking
CREATE TABLE trend_flash_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES trend_flash_content(id),
    platform TEXT NOT NULL,
    
    -- Metrics
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    profile_taps INTEGER DEFAULT 0,
    
    -- Intent signals
    purchase_intent_comments INTEGER DEFAULT 0,
    keyword_comments INTEGER DEFAULT 0,
    
    -- Calculated
    engagement_rate FLOAT DEFAULT 0,
    intent_score FLOAT DEFAULT 0,
    
    captured_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

```
# Detection
POST   /api/trend-flash/detect              # Run detection cycle
GET    /api/trend-flash/clusters            # Get detected clusters
GET    /api/trend-flash/clusters/{id}       # Get cluster details
GET    /api/trend-flash/top                 # Get top-scored clusters

# Generation
POST   /api/trend-flash/generate/{id}       # Generate content for cluster
GET    /api/trend-flash/content             # List generated content
GET    /api/trend-flash/content/{id}        # Get content details
POST   /api/trend-flash/content/{id}/render # Render video

# Posting
POST   /api/trend-flash/content/{id}/post   # Post to platforms
GET    /api/trend-flash/content/{id}/performance # Get performance

# Settings
GET    /api/trend-flash/settings            # Get detection settings
PUT    /api/trend-flash/settings            # Update settings
```

---

## File Structure

```
Backend/services/trend_flash/
├── __init__.py
├── trend_radar.py           # Detection + clustering
├── trend_scorer.py          # Scoring formula
├── flash_generator.py       # Script + content generation
├── remotion_shipper.py      # Remotion video production
├── platform_poster.py       # Multi-platform posting
└── performance_tracker.py   # Learning loop

Backend/api/endpoints/
└── trend_flash.py           # API endpoints

dashboard/app/(dashboard)/trend-flash/
└── page.tsx                 # Trend radar dashboard
```

---

## Trend Cluster Object Schema

```json
{
  "id": "uuid",
  "topic": "using AI to automate content",
  "keywords": ["ai content", "automation", "scheduling"],
  "summary": "People asking how to use AI tools for content creation",
  
  "velocity": 45.2,
  "mentions_count": 127,
  "unique_authors": 89,
  
  "platforms": ["instagram", "tiktok", "twitter"],
  "platform_count": 3,
  
  "top_questions": [
    "what tool do you use?",
    "how do you automate this?",
    "is there a template?"
  ],
  
  "intent_keywords_found": ["what tool", "how do you", "template"],
  "intent_score": 1.8,
  
  "trend_score": 130.5,
  "cross_platform_multiplier": 1.6,
  "intent_multiplier": 1.8,
  
  "status": "selected",
  "first_seen_at": "2026-01-26T22:00:00Z",
  "last_seen_at": "2026-01-26T22:45:00Z"
}
```

---

## Scoring Formula (Exact)

```python
def calculate_trend_score(cluster: TrendCluster) -> float:
    # Base velocity (mentions per hour)
    velocity = cluster.velocity
    
    # Cross-platform multiplier
    if cluster.platform_count >= 3:
        cross_multiplier = 1.6  # +60%
    elif cluster.platform_count == 2:
        cross_multiplier = 1.3  # +30%
    else:
        cross_multiplier = 1.0
    
    # Intent multiplier
    intent_count = len(cluster.intent_keywords_found)
    if intent_count >= 3:
        intent_multiplier = 1.8  # +80%
    elif intent_count >= 1:
        intent_multiplier = 1.5  # +50%
    else:
        intent_multiplier = 1.0
    
    # Final score
    trend_score = velocity * cross_multiplier * intent_multiplier
    
    return trend_score
```

---

## Script Variants

### 1. Educational (Default)
```
HOOK: "everyone's talking about [trend] today — here's the part they're missing."
CONTEXT: "it's popping up on [platforms], and the comments are all saying [question]."
TAKE: "the real move is [one rule]."
ACTION: "do this: [step 1], [step 2], [step 3]."
CTA: "comment [keyword] and i'll send the exact workflow."
```

### 2. Contrarian
```
HOOK: "everyone's wrong about [trend] — here's what actually works."
CONTEXT: "i've seen 100+ comments this week getting this backwards."
TAKE: "forget [common advice]. instead, [contrarian take]."
ACTION: "here's the real play: [step 1], [step 2]."
CTA: "comment [keyword] if you want the full breakdown."
```

### 3. Meme-Leaning
```
HOOK: "[trend] is everywhere rn and honestly? same."
CONTEXT: "my timeline is just [relatable observation]."
TAKE: "but real talk, here's what actually matters:"
ACTION: "[casual step 1], [casual step 2]."
CTA: "drop a [emoji] if you feel this."
```

---

## Safety Guardrails

### Rate Limiting
- **Scraping:** Max 100 requests/hour per platform
- **Commenting:** Max 20 comments/hour per account
- **Posting:** Max 10 posts/day per account

### Comment Quality
- Rotate templates (never repeat exact text)
- Reference the specific post/video
- Prefer replies to existing conversations
- Avoid link spam (use keyword CTAs)

### Platform Compliance
- Vary timing between actions
- Use human-like delays (3-10 seconds)
- Monitor for rate limit warnings
- Auto-pause if flagged
