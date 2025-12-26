# PRD: Trending Keywords & Video Analysis Enhancements

## Overview

Enhance the Instagram Trends dashboard with trending keywords and improve video analysis recommendations for better content optimization.

## Current State

From the dashboard screenshots:
- **Trending Audio**: ✅ Working (showing songs with usage counts)
- **Trending Hashtags**: ❌ Empty ("No trending hashtags yet. Run the trend crawler to populate data")
- **Trending Niches**: ✅ Working (showing categories with growth percentages)
- **Trending Keywords**: ❌ Missing feature

## Goals

1. **Populate Trending Hashtags** - Run trend crawler to fetch real hashtag data
2. **Add Trending Keywords** - New widget showing viral phrases and hooks
3. **Improve Video Analysis** - Better recommendations for content optimization
4. **Add Comprehensive Tests** - Test coverage for all features

---

## Phase 1: Trending Keywords Feature

### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| TK-001 | Extract keywords from competitor captions | P0 |
| TK-002 | Track keyword frequency over time | P0 |
| TK-003 | Calculate keyword velocity (growth rate) | P0 |
| TK-004 | Display top trending keywords in dashboard | P0 |
| TK-005 | Filter keywords by niche/category | P1 |
| TK-006 | Show keyword engagement correlation | P1 |

### Keyword Types

1. **Hook Phrases** - Opening lines that grab attention
   - "POV: you're the..."
   - "3 things I wish I knew..."
   - "Nobody talks about this..."
   - "Hot take:"

2. **Engagement Phrases** - CTAs and interaction triggers
   - "Drop a 🔥 if you agree"
   - "Save this for later"
   - "Tag someone who needs this"

3. **Trending Topics** - Current viral subjects
   - Extracted from captions using NLP
   - N-gram analysis (2-5 word phrases)

### API Endpoints

```
GET  /api/trends/keywords                    # List trending keywords
GET  /api/trends/keywords/{keyword}          # Keyword details
POST /api/trends/keywords/extract            # Extract from content
GET  /api/trends/keywords/velocity           # Keywords with velocity scores
```

### Database Schema

```sql
CREATE TABLE trending_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL,
    keyword_type TEXT,  -- 'hook', 'cta', 'topic', 'phrase'
    niche TEXT,
    
    -- Metrics
    occurrence_count INTEGER DEFAULT 0,
    daily_occurrences JSONB DEFAULT '{}',
    avg_engagement NUMERIC,
    
    -- Velocity
    velocity_24h NUMERIC,
    velocity_7d NUMERIC,
    trend_score NUMERIC,
    
    -- Timestamps
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trending_keywords_score ON trending_keywords(trend_score DESC);
CREATE INDEX idx_trending_keywords_type ON trending_keywords(keyword_type);
```

---

## Phase 2: Video Analysis Improvements

### Current Recommendations

The video analysis currently provides these recommendations:
- **Duration**: "Combine multiple videos to reach 5+ minutes total"
- **Content**: "Focus on videos with clear spoken content"
- **Quality**: "Record in quieter environments with better microphones"
- **Transcript**: "Re-run with --transcript flag for better analysis"

### Enhanced Analysis Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| VA-001 | Auto-detect video duration and provide specific recommendations | P0 |
| VA-002 | Analyze audio quality (noise, clarity, volume) | P0 |
| VA-003 | Extract and analyze transcript automatically | P0 |
| VA-004 | Detect content type (talking head, b-roll, text cards) | P1 |
| VA-005 | Identify hook presence in first 3 seconds | P1 |
| VA-006 | Calculate engagement prediction score | P1 |

### Video Quality Metrics

```python
class VideoAnalysisResult:
    duration_seconds: float
    audio_quality_score: float  # 0-100
    speech_clarity_score: float  # 0-100
    background_noise_level: float  # dB
    content_type: str  # 'talking_head', 'broll', 'text_cards', 'mixed'
    has_hook: bool
    hook_strength_score: float  # 0-100
    transcript: Optional[str]
    detected_topics: List[str]
    engagement_prediction: float  # 0-100
    recommendations: List[str]
```

### Recommendation Engine

```python
def generate_recommendations(analysis: VideoAnalysisResult) -> List[str]:
    recommendations = []
    
    # Duration recommendations
    if analysis.duration_seconds < 15:
        recommendations.append("⚡ Very short video - perfect for Reels/Shorts")
    elif analysis.duration_seconds < 60:
        recommendations.append("📱 Ideal length for short-form content")
    elif analysis.duration_seconds > 300:
        recommendations.append("📺 Long-form - consider for YouTube")
    
    # Audio quality
    if analysis.audio_quality_score < 50:
        recommendations.append("🎙️ Audio quality is low - use external mic")
    if analysis.background_noise_level > -20:
        recommendations.append("🔇 High background noise - record in quieter space")
    
    # Content structure
    if not analysis.has_hook:
        recommendations.append("🎣 Add a strong hook in first 3 seconds")
    if analysis.content_type == 'talking_head' and analysis.duration_seconds > 30:
        recommendations.append("🎬 Add B-roll to maintain engagement")
    
    return recommendations
```

---

## Phase 3: Trend Crawler Data Population

### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| TC-001 | Automated hashtag discovery from niches | P0 |
| TC-002 | Fetch hashtag metrics (post count, velocity) | P0 |
| TC-003 | Store time-series data for trend analysis | P0 |
| TC-004 | Run crawler on schedule (every 6 hours) | P1 |
| TC-005 | Deduplicate and merge hashtag data | P1 |

### Crawler Pipeline

```
[Seed Keywords] → [RapidAPI Search] → [Hashtag Candidates]
       ↓                                      ↓
[Niche Config]                    [Hashtag Posts/Reels]
       ↓                                      ↓
[Tracked Hashtags] ←─────────── [Media Items with Metrics]
                                              ↓
                                    [Velocity Calculation]
                                              ↓
                                    [Dashboard Display]
```

### API Endpoints for Crawler

```
POST /api/trends/crawler/run          # Trigger crawler
GET  /api/trends/crawler/status       # Crawler status
POST /api/trends/crawler/discover     # Discover new hashtags
GET  /api/trends/hashtags/populate    # Populate from competitor data
```

---

## Phase 4: Testing

### Test Categories

1. **Unit Tests**
   - Keyword extraction accuracy
   - Velocity calculation
   - Video analysis scoring

2. **Integration Tests**
   - API endpoint responses
   - Database persistence
   - Crawler pipeline

3. **E2E Tests**
   - Dashboard data display
   - Trend crawler execution
   - Analysis workflow

### Test Files

```
Backend/tests/
├── test_trending_keywords.py
├── test_video_analysis.py
├── test_trend_crawler.py
└── test_trends_api.py
```

---

## Implementation Timeline

| Phase | Description | Duration |
|-------|-------------|----------|
| Phase 1 | Trending Keywords | 1 day |
| Phase 2 | Video Analysis | 1 day |
| Phase 3 | Trend Crawler | 1 day |
| Phase 4 | Testing | 1 day |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Trending keywords displayed | 20+ |
| Hashtag data populated | 100+ hashtags |
| Video analysis accuracy | > 85% |
| Test coverage | > 80% |
| Crawler success rate | > 95% |

---

## API Response Examples

### Trending Keywords

```json
{
  "keywords": [
    {
      "keyword": "POV: you're the",
      "type": "hook",
      "occurrences": 1250,
      "velocity_7d": 2.5,
      "trend_score": 85,
      "avg_engagement": 15000
    },
    {
      "keyword": "3 things I wish",
      "type": "hook", 
      "occurrences": 890,
      "velocity_7d": 1.8,
      "trend_score": 72,
      "avg_engagement": 12000
    }
  ]
}
```

### Video Analysis

```json
{
  "video_id": "abc123",
  "duration_seconds": 45,
  "audio_quality_score": 78,
  "content_type": "talking_head",
  "has_hook": true,
  "hook_strength": 65,
  "engagement_prediction": 72,
  "recommendations": [
    "📱 Ideal length for short-form content",
    "🎬 Add B-roll to maintain engagement",
    "🔥 Strong hook detected in first 2 seconds"
  ]
}
```
