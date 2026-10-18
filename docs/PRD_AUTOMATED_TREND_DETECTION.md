# PRD: Automated Trend Detection

**Status:** Proposed
**Priority:** P2 — Game-Changer
**Effort:** ~7-10 days
**Impact:** Ride trending waves in real-time; 5-10x reach on trend-aligned content

---

## 1. Problem Statement

Trends on TikTok and Instagram move fast — a trending sound, topic, or format can explode for 24-72 hours then die. By the time a creator manually notices a trend, creates content, and posts it, the window has often closed. There's no automated system to detect emerging trends and generate content ideas that ride the wave.

## 2. Objective

Build an automated trend monitoring system that:
1. Continuously scans TikTok, Instagram, and Twitter for emerging trends (sounds, hashtags, topics, formats)
2. Filters for trends relevant to the creator's niche
3. Auto-generates content briefs and Sora prompts aligned to hot trends
4. Alerts the creator with a ready-to-produce brief within hours of trend detection

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Trend detection speed | Within 6 hours of trend emergence |
| Relevance accuracy | ≥ 70% of detected trends are niche-relevant |
| Trend-aligned content performance | ≥ 3x average engagement |
| Brief generation speed | < 5 minutes after trend detection |
| Actionable alerts per week | 3-5 high-confidence trend alerts |

## 4. Technical Design

### 4.1 Data Sources

| Source | Method | Signal |
|--------|--------|--------|
| **TikTok Trending** | RapidAPI (`tiktok-scraper`) | Trending hashtags, sounds, effects |
| **TikTok Discover** | RapidAPI | Rising topics in creator's niche |
| **Instagram Explore** | RapidAPI (`instagram-looter2`) | Trending Reels, hashtags |
| **Twitter/X Trending** | Twitter API v2 | Trending topics, conversations |
| **Google Trends** | `pytrends` library | Search interest spikes |
| **YouTube Trending** | YouTube Data API | Trending videos in category |

### 4.2 Architecture

```
┌─────────────────────────┐
│  Trend Scanners          │  ← Platform-specific scrapers (every 2 hours)
│  (TikTok, IG, Twitter)   │
└──────────┬──────────────┘
           │  Raw trend data
           ▼
┌─────────────────────────┐
│  Niche Relevance Filter  │  ← GPT classifies: relevant to creator's brand?
│  (AI + keyword matching)  │
└──────────┬──────────────┘
           │  Relevant trends only
           ▼
┌─────────────────────────┐
│  Trend Scorer            │  ← Velocity, volume, niche fit, competition
│  (composite ranking)      │
└──────────┬──────────────┘
           │  Top trends
           ▼
┌─────────────────────────┐
│  Brief Generator         │  ← GPT creates content brief + Sora prompt
│  (ties into Content       │
│   Intelligence PRD)       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Alert System            │  ← Push notification / macOS alert / webhook
│  (time-sensitive)         │
└─────────────────────────┘
```

### 4.3 Components

#### A. Trend Scanner (`services/trend_detection/scanners/`)

```python
class TikTokTrendScanner:
    async def scan_trending_hashtags(self) -> List[TrendSignal]:
        """Pull current trending hashtags via RapidAPI"""
    
    async def scan_trending_sounds(self) -> List[TrendSignal]:
        """Pull trending audio tracks"""
    
    async def scan_niche_creators(self, niche_accounts: List[str]) -> List[TrendSignal]:
        """Monitor what niche-relevant creators are posting about"""

class InstagramTrendScanner:
    async def scan_explore_reels(self) -> List[TrendSignal]:
        """Analyze Instagram Explore for trending formats/topics"""
    
    async def scan_hashtag_velocity(self, hashtags: List[str]) -> List[TrendSignal]:
        """Track hashtag post velocity for early trend detection"""

class TwitterTrendScanner:
    async def scan_trending_topics(self, location: str = "US") -> List[TrendSignal]:
        """Pull Twitter trending topics"""
    
    async def scan_niche_conversations(self, keywords: List[str]) -> List[TrendSignal]:
        """Monitor keyword volume spikes in niche conversations"""
```

#### B. Niche Relevance Filter

```python
class NicheRelevanceFilter:
    CREATOR_NICHE = {
        "primary_topics": ["relationships", "dating", "self-improvement", "masculinity", "motivation"],
        "secondary_topics": ["lifestyle", "fitness", "mental health", "entrepreneurship"],
        "brand_keywords": ["love", "dating tips", "relationship advice", "grow", "mindset"],
        "exclude_topics": ["politics", "religion", "explicit", "controversial"],
    }
    
    async def filter(self, trends: List[TrendSignal]) -> List[ScoredTrend]:
        """
        Two-stage filter:
        1. Keyword matching against niche topics (fast)
        2. GPT relevance scoring for ambiguous trends (accurate)
        
        Returns trends with relevance_score 0-1
        """
```

#### C. Trend Scorer

```python
class TrendScorer:
    def score(self, trend: TrendSignal) -> float:
        """
        Composite score:
        - velocity (how fast it's growing): 0.3
        - volume (current size): 0.2
        - niche_fit (relevance to brand): 0.3
        - competition (lower = better opportunity): 0.1
        - freshness (hours since emergence): 0.1
        """
```

### 4.4 Database Schema

```sql
CREATE TABLE detected_trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_platform VARCHAR(20) NOT NULL,
    trend_type VARCHAR(50),           -- hashtag, sound, topic, format
    trend_identifier VARCHAR(500),     -- #hashtag, sound URL, topic keyword
    trend_description TEXT,
    velocity_score FLOAT,
    volume_score FLOAT,
    niche_relevance FLOAT,
    composite_score FLOAT,
    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    peak_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'emerging',  -- emerging, hot, peaked, declining
    brief_generated BOOLEAN DEFAULT FALSE,
    alerted BOOLEAN DEFAULT FALSE
);

CREATE TABLE trend_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trend_id UUID REFERENCES detected_trends(id),
    content_brief_id UUID REFERENCES content_briefs(id),
    sora_prompt TEXT,
    suggested_caption TEXT,
    urgency VARCHAR(10),             -- high, medium, low
    window_hours INT,                -- estimated hours before trend peaks
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trends_score ON detected_trends(composite_score DESC, status);
CREATE INDEX idx_trends_status ON detected_trends(status, first_detected_at);
```

### 4.5 Alert System

```python
class TrendAlertSystem:
    async def alert(self, trend: ScoredTrend, brief: ContentBrief):
        """
        Multi-channel alert:
        1. macOS notification (osascript)
        2. Webhook (Discord/Slack)
        3. Dashboard push notification
        4. Optional: SMS for high-urgency trends
        
        Alert includes:
        - Trend name and description
        - Estimated time window
        - Ready-to-use Sora prompt
        - Suggested caption
        - "Create Now" deep link to dashboard
        """
```

## 5. Cron Schedule

| Job | Frequency | Description |
|-----|-----------|-------------|
| `scan_tiktok_trends` | Every 2 hours | Pull TikTok trending data |
| `scan_instagram_trends` | Every 4 hours | Pull Instagram trending data |
| `scan_twitter_trends` | Every 2 hours | Pull Twitter trending topics |
| `score_and_filter` | Every 2 hours | Score new trends, filter by niche |
| `generate_trend_briefs` | On high-score detection | Generate brief for hot trends |
| `alert_creator` | On brief generation | Push notification |
| `update_trend_status` | Every 6 hours | Mark trends as peaked/declining |

## 6. API Endpoints

```
GET  /api/trends                      — List detected trends (filter by status, score)
GET  /api/trends/:id                  — Trend details + generated brief
POST /api/trends/:id/generate-brief   — Manually trigger brief for a trend
GET  /api/trends/alerts               — Recent trend alerts
PUT  /api/trends/niche-config         — Update niche relevance keywords
GET  /api/trends/dashboard            — Trend radar visualization data
```

## 7. Rollout Plan

1. **Phase 1:** TikTok hashtag scanner + niche filter
2. **Phase 2:** Trend scoring + alert system
3. **Phase 3:** Brief generation integration
4. **Phase 4:** Instagram + Twitter scanners
5. **Phase 5:** Dashboard trend radar visualization
6. **Phase 6:** Auto-generate Sora prompts from trend briefs

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| RapidAPI rate limits | Stagger requests; cache results; 2hr scan intervals |
| False positive trends | Minimum score threshold; niche filter; human review option |
| Trend moves too fast | Alert within 30 min of detection; pre-generate Sora prompts |
| API costs | Budget cap per month; prioritize free data sources |
| Platform API changes | Abstract scanner interface; easy to swap implementations |

## 9. Cost Estimate

| Item | Monthly Cost |
|------|-------------|
| RapidAPI (TikTok + Instagram) | ~$30-50 |
| Twitter API v2 (Basic) | $100 |
| GPT-4o-mini for classification | ~$5 |
| Google Trends (pytrends) | Free |
| **Total** | **~$135-155/month** |

## 10. Out of Scope (v1)

- Trending sound integration (downloading/attaching sounds to Sora videos)
- Competitor trend analysis (what's working for similar creators)
- Predictive trend modeling (predicting before it trends)
- Automated content creation without human approval
