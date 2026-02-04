# PRD: Instagram Research Methodologies & Competitive Intelligence

**Version:** 1.0  
**Date:** February 4, 2026  
**Status:** Comprehensive Specification  
**Priority:** 🔴 Critical  
**Effort:** 8-12 weeks (phased implementation)

---

## Executive Summary

This PRD defines a comprehensive Instagram research system that enables end-users to:
1. **Track competitors** and analyze their content strategies
2. **Discover trends** (hashtags, sounds, formats) with velocity metrics
3. **Extract actionable insights** to improve their own content
4. **Benchmark performance** against industry standards
5. **Generate AI-powered content recommendations** based on what works

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              INSTAGRAM RESEARCH & COMPETITIVE INTELLIGENCE       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  DATA COLLECTION LAYER                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  RapidAPI   │ │  Instagram  │ │   Safari    │ │  oEmbed   │ │
│  │  Scrapers   │ │  Graph API  │ │ Automation  │ │   API     │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬─────┘ │
│         └────────────────┴───────────────┴─────────────┘        │
│                              │                                   │
│                              ▼                                   │
│  PROCESSING LAYER                                               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │   COMPETITOR    │ │   AI ANALYSIS   │ │     TREND       │   │
│  │    SERVICE      │ │    SERVICE      │ │  INTELLIGENCE   │   │
│  │ • Fetch data    │ │ • Hook extract  │ │ • Hashtag vel   │   │
│  │ • Sync 24h      │ │ • Format class  │ │ • Sound trend   │   │
│  │ • Download      │ │ • Theme ID      │ │ • Format detect │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  INSIGHTS LAYER                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │Benchmarks│ │ Content  │ │  Trend   │ │   Gap    │          │
│  │          │ │  Ideas   │ │  Alerts  │ │ Analysis │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Collection Methods

### Method 1: RapidAPI Instagram Scrapers (Primary)

| API | Host | Use Case |
|-----|------|----------|
| Instagram Looter 2 | `instagram-looter2.p.rapidapi.com` | Profile + posts |
| Instagram Scraper API 2 | `instagram-scraper-api2.p.rapidapi.com` | Analytics |
| Instagram Stable API | `instagram-scraper-stable-api.p.rapidapi.com` | Reels |

**Data Collected:**
- Profile: username, bio, followers, following, media_count, is_verified
- Content: media_id, shortcode, caption, play_count, like_count, comment_count
- Audio: audio_id, title, artist, is_original

### Method 2: Instagram Graph API (Business Accounts)

**Available Insights:**
- impressions, reach, engagement, saved, video_views, shares
- follower_demographics (age, gender, location)
- online_followers (best times to post)

### Method 3: Safari Automation (Scroll + Collect)

**Process:**
1. Open Safari → Instagram profile /reels/
2. Scroll and collect URLs (no clicking)
3. Download via RapidAPI

**Storage:** `/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/`

---

## Competitor Research Features

### Feature 1: Competitor Account Tracking

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPETITOR TRACKER                              [+ Add Account] │
├─────────────────────────────────────────────────────────────────┤
│  @personalbrandlaunch                            🔄 Sync  🗑️    │
│  Followers: 125.4K | Posts: 342 | Engagement: 4.2%             │
│  Top Hooks: Questions (35%), Bold statements (28%)             │
│  Top Formats: Talking head (45%), B-roll (30%)                 │
│  [View Analysis]  [Download Content]  [Generate Ideas]          │
└─────────────────────────────────────────────────────────────────┘
```

### Feature 2: AI Content Analysis

**Analysis Output (per post):**
```json
{
  "hook": "Stop scrolling if you want to 10x your productivity",
  "hook_type": "curiosity_gap",
  "format_type": "talking_head_with_broll",
  "content_themes": ["productivity", "self-improvement"],
  "target_audience": "Entrepreneurs aged 25-40",
  "emotional_triggers": ["fomo", "aspiration"],
  "cta_type": "follow_for_more",
  "why_it_works": "Strong curiosity hook + clear value promise",
  "replication_tips": ["Use bold statement", "Show before state first"]
}
```

### Feature 3: Account Learnings Report

Auto-generated Markdown report including:
- Top Performing Hooks (by type, count, %)
- Top Content Formats
- Content Themes
- Key Learnings
- Content Ideas to Try

---

## Trend Intelligence System

### Trending Hashtags with Velocity

```python
class HashtagTrend:
    tag: str              # #productivity
    media_count: int      # 1,234,567
    velocity_1d: float    # +15.3% (1-day growth)
    velocity_7d: float    # +82.1% (7-day growth)
    acceleration: float   # +4.2 (speeding up)
    trending_score: float # 847.3 (weighted composite)
```

**UI:**
```
🔥 HOT (velocity > 50%)
#aitools       📈 +127%/day   ⚡ 2.1M posts   Score: 982
#solopreneur   📈 +89%/day    ⚡ 456K posts   Score: 847

📈 RISING (velocity > 20%)
#sidehustle    📈 +45%/day    ⚡ 1.8M posts   Score: 645
```

### Trending Sounds & Formats

- Sound usage count + velocity
- Format patterns (text-on-screen, POV, etc.)
- Regional support (US, UK, EU, GLOBAL)

---

## Actionable Insights

### Content Gap Analysis

**Question:** What content are competitors posting that I'm NOT?

```
🎯 HIGH OPPORTUNITY GAPS

1. "Morning routines" - Competitors avg 45K views
   You: 0 posts | Opportunity Score: 94
   → Suggested: "My exact morning routine for productivity"

2. "Tool reviews" - Competitors avg 38K views
   You: 0 posts | Opportunity Score: 87
   → Suggested: "3 AI tools that changed my workflow"
```

### Performance Benchmarking

Compare your metrics vs competitors and industry:
- Engagement rate
- Posting frequency
- Follower growth
- Avg views per reel

### Hook Library

Curated hooks from competitor analysis:
- **Questions** (highest comment rate: +47%)
- **Bold Statements** (highest save rate: +38%)
- **Pain Points** (highest share rate: +52%)
- **Transformations** (highest follow rate: +29%)

### Weekly Strategy Report

Auto-generated every Monday:
- Performance summary
- Top performing content
- Trending recommendations
- Content ideas for the week
- Action items checklist

---

## Database Schema

```sql
-- Core tables
CREATE TABLE competitor_accounts (
    id UUID PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    followers_count INTEGER,
    last_synced_at TIMESTAMPTZ
);

CREATE TABLE competitor_content (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES competitor_accounts(id),
    media_id VARCHAR(100),
    caption TEXT,
    play_count INTEGER,
    like_count INTEGER,
    posted_at TIMESTAMPTZ
);

CREATE TABLE competitor_content_analysis (
    id UUID PRIMARY KEY,
    content_id UUID REFERENCES competitor_content(id),
    hook TEXT,
    hook_type VARCHAR(50),
    format_type VARCHAR(50),
    content_themes JSONB,
    replication_tips JSONB
);

CREATE TABLE trending_hashtags (
    id UUID PRIMARY KEY,
    tag VARCHAR(100),
    region VARCHAR(10),
    velocity_1d FLOAT,
    velocity_7d FLOAT,
    trending_score FLOAT
);
```

---

## API Endpoints

```yaml
# Competitor Management
POST   /api/competitors/accounts           # Add competitor
GET    /api/competitors/accounts           # List tracked
POST   /api/competitors/{user}/sync        # Full sync
POST   /api/competitors/{user}/analyze     # Run AI analysis
GET    /api/competitors/{user}/learnings   # Get learnings

# Trend Intelligence
GET    /api/instagram-trends/feed          # Complete trends
GET    /api/instagram-trends/hashtags      # Hashtags only
GET    /api/instagram-trends/sounds        # Sounds only
GET    /api/instagram-trends/search        # Search hashtags

# Insights
POST   /api/content-ideas/generate         # Generate ideas
GET    /api/gap-analysis/latest            # Content gaps
GET    /api/benchmark/me-vs-competitors    # Comparison
GET    /api/strategy-report/latest         # Weekly report
```

---

## Implementation Phases

| Phase | Tasks | Weeks |
|-------|-------|-------|
| **1. Data Collection** | RapidAPI integration, sync scheduler | 1-2 |
| **2. AI Analysis** | Content analysis, keyword extraction | 3-4 |
| **3. Trends** | Hashtag velocity, sound/format tracking | 5-6 |
| **4. Dashboard** | Competitor tracker, trends feed UI | 7-8 |
| **5. Ideas** | Content idea generation, hook library | 9-10 |
| **6. Polish** | Optimization, testing, documentation | 11-12 |

---

## Existing Code Reference

### Services
- `Backend/services/competitor_service.py` - Fetch profiles/reels
- `Backend/services/competitor_analysis_service.py` - AI analysis
- `Backend/services/competitor_sync_scheduler.py` - 24h sync
- `Backend/services/scrapers/instagram_scraper.py` - Multi-method scraper
- `Backend/services/competitor_audit/collector.py` - Multi-platform collector

### API Endpoints
- `Backend/api/endpoints/competitor_api.py` - Account management
- `Backend/api/endpoints/instagram_trends.py` - Trends feed
- `Backend/api/endpoints/trends_api.py` - Hashtag extraction

### Storage
- `/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/`
  - `reels/reels.json`
  - `posts/posts.json`
  - `analysis/learnings.json`
  - `analysis/learnings.md`
  - `download_manifest.json`

---

## Success Metrics

- [ ] Track 10+ competitors per user
- [ ] 24h auto-sync with <5% failure rate
- [ ] AI analysis completes in <30s per account
- [ ] Trend velocity accurate within ±10%
- [ ] Content ideas rated >4/5 usefulness
- [ ] Weekly report generation <2 minutes

---

*Document created: February 4, 2026*
