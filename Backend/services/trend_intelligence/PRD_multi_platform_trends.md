# Multi-Platform Trend Discovery System PRD

## Overview

Build a **keyword-less trend discovery system** that discovers trends across TikTok, Instagram, YouTube, and Twitter/X by crawling account panels, detecting patterns via clustering, and scoring by breadth + velocity + uplift.

**Key Principle:** Sample reality first, then let math + clustering tell you what's repeating faster than normal.

---

## Platform-Specific Strategies

### 1. TikTok (Strongest Signals)

#### Data Sources
| Method | Endpoint | Use Case |
|--------|----------|----------|
| **User Posts** | `tiktok-scraper7.p.rapidapi.com/user/posts` | Panel crawl |
| **Sound/Music** | `music_info.id` from response | Sound trends |
| **Creative Center** | TikTok's trend surfaces | Candidate discovery |

#### Trend Types
1. **Sound Trends** (best signal) - `music_id` velocity + breadth
2. **Hook Trends** - First 3-8 words clustering
3. **Topic Clusters** - Semantic embedding of captions
4. **Hashtag Trends** - Cross-creator hashtag velocity

#### Feedback Loop
```
Crawl Panel → Extract Sounds/Hooks → Cluster → Score → Trending Now
     ↓
Generate Brief → Publish → Measure (views/shares) → Learn
```

---

### 2. Instagram (Caption + Transcript)

#### Data Sources
| Method | Endpoint | Use Case |
|--------|----------|----------|
| **Profile** | `instagram-looter2.p.rapidapi.com/profile` | Get user ID |
| **Reels** | `instagram-looter2.p.rapidapi.com/reels` | Reel metadata |
| **Video Download** | MP4 URL from response | For transcription |

#### Trend Types
1. **Hook Clusters** - First sentence/150 chars embedded + clustered
2. **Topic Clusters** - Full caption/transcript embeddings
3. **Angle Trends** - Contrarian, checklist, storytime, myth-busting
4. **CTA Patterns** - "comment ___", "save this", "DM me ___"
5. **Format Trends** - Carousel structure, text-only, talking head

#### Enhancement: Transcription Pipeline
```
Download Reel MP4 → Whisper ASR → Transcript → Embed → Cluster
```

#### Feedback Loop
```
Panel Crawl → Download Videos → Transcribe → Cluster Hooks/Topics
     ↓
Generate Brief → Publish → Measure (saves/shares) → Learn angles
```

---

### 3. YouTube (Multi-Collector)

#### Data Sources
| Method | Endpoint/Surface | Use Case |
|--------|------------------|----------|
| **Uploads Playlist** | `playlistItems.list` | Complete channel crawl |
| **Video Stats** | `videos.list` | Hydrate metadata |
| **RSS Feeds** | `/feeds/videos.xml?channel_id=X` | Fast delta detection |
| **Search API** | `search.list` | Discovery sampling |
| **Analytics API** | YouTube Analytics (owned channels) | CTR/retention |

#### Trend Types
1. **Title Template Trends** - "I tried X", "X explained", "Do THIS not THAT"
2. **Topic Clusters** - Title + description embeddings
3. **Entity Trends** - Tools, products, people rising across channels
4. **Format Trends** - Duration buckets, Shorts vs longform

#### Multi-Collector Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  RSS Collector  │    │ Uploads Crawler │    │ Search Sampler  │
│  (delta detect) │    │  (backfill)     │    │  (discovery)    │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │    Video Hydrator     │
                    │  (stats + metadata)   │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │    Trend Engine       │
                    │ (cluster + score)     │
                    └───────────────────────┘
```

#### Feedback Loop (Longer Checkpoints)
```
T+1h:  Early read (impressions, CTR)
T+6h:  Recommendation pickup (browse/suggested traffic)
T+24h: View velocity slope
T+48h: Long tail performance
```

---

### 4. Twitter/X (Fastest Loop)

#### Data Sources
| Method | Endpoint | Use Case |
|--------|----------|----------|
| **Recent Search** | X API v2 `tweets/search/recent` | Real-time sampling |
| **User Timeline** | `users/:id/tweets` | Panel crawl |
| **Mentions** | `users/:id/mentions` | Reaction tracking |

#### Trend Types
1. **Topic Clusters** - Tweet text embeddings
2. **Meme/Phrase Clusters** - "Hot take:", "Normalize...", "If you're doing X, stop"
3. **Link/Domain Clusters** - Viral article detection
4. **Conversation Clusters** - Thread/quote-tweet chains

#### Engagement Mix (X-Specific)
| Metric | Meaning |
|--------|---------|
| Like-heavy | Pleasant content |
| Reply-heavy | Controversial/discussion |
| Retweet-heavy | Shareable |
| Quote-heavy | Polarizing/commentary |

#### Feedback Loop (Minutes to Hours)
```
T+10m:  Early pickup (replies/retweets)
T+60m:  Distribution spread
T+6h:   Staying power
T+24h:  Long tail
```

---

## Universal Trend Scoring Model

### The Formula
```python
TrendScore = (
    0.45 * breadth_norm +      # Unique creators using it
    0.30 * velocity_norm +      # Mentions/day growth
    0.25 * uplift_norm          # Performance vs creator baseline
)
```

### Normalization (Critical)
For each creator, compute baselines:
- `median_views_30d`
- `median_like_rate`
- `median_comment_rate`

Then for each post:
```python
uplift = views / creator.median_views_30d
```

This prevents mega-channels from faking trends.

### Concentration Penalty
```python
creator_concentration = max_creator_posts / total_posts_in_cluster
if concentration > 0.35:
    downrank or label as "campaign"
```

---

## Implementation Phases

### Phase 1: YouTube Multi-Collector ✅ (Partially Done)
- [x] YouTube Data API integration
- [x] Video stats + metadata extraction
- [x] Topic clustering with OpenAI
- [ ] RSS feed delta detection
- [ ] Search API discovery sampling
- [ ] Channel baseline normalization

### Phase 2: Enhanced TikTok
- [ ] Sound-first trend detection
- [ ] Sound velocity tracking
- [ ] Cross-creator breadth scoring
- [ ] Creative Center integration (if available)

### Phase 3: Instagram Transcription
- [ ] Video download from reels
- [ ] Whisper transcription pipeline
- [ ] Transcript-based hook clustering
- [ ] Angle classification

### Phase 4: Twitter/X Crawler
- [ ] X API v2 integration
- [ ] Real-time search sampling
- [ ] Panel timeline crawling
- [ ] Engagement mix scoring

### Phase 5: Unified Feedback Loop
- [ ] Multi-checkpoint measurement (T+1h, T+6h, T+24h, T+48h)
- [ ] Per-cluster performance tracking
- [ ] Automatic brief optimization
- [ ] A/B variant learning

---

## Data Schemas

### Panel Schema
```python
class NichePanel:
    panel_id: str           # "finance_us_v1"
    niche: str              # "finance"
    platform: str           # "tiktok" | "instagram" | "youtube" | "twitter"
    accounts: List[Account]
    created_at: datetime
    updated_at: datetime
```

### Trend Candidate Schema
```python
class TrendCandidate:
    trend_id: str
    trend_type: str         # "sound" | "hook" | "topic" | "template" | "entity"
    platform: str
    identifier: str         # sound_id, cluster_label, template_name
    display_title: str
    status: str             # "emerging" | "rising" | "peak" | "declining"
    
    # Scoring
    breadth: int            # unique creators
    velocity: float         # mentions/day
    acceleration: float     # change in velocity
    uplift: float           # median performance vs baseline
    score: float            # combined score
    
    # Examples
    example_posts: List[dict]
    top_creators: List[str]
    
    # Metadata
    first_seen: datetime
    last_seen: datetime
```

### Feedback Checkpoint Schema
```python
class FeedbackCheckpoint:
    post_id: str
    trend_id: str
    platform: str
    checkpoint: str         # "T+1h" | "T+6h" | "T+24h" | "T+48h"
    
    # Metrics
    views: int
    likes: int
    comments: int
    shares: int
    
    # Computed
    ctr: float              # if available
    retention: float        # if available
    uplift: float           # vs account baseline
```

---

## API Endpoints

### Crawl Endpoints
```
POST /api/v1/crawl/youtube       # YouTube multi-collector
POST /api/v1/crawl/tiktok        # TikTok panel crawl
POST /api/v1/crawl/instagram     # Instagram with transcription
POST /api/v1/crawl/twitter       # Twitter/X real-time
POST /api/v1/crawl/all           # Run all platforms
```

### Panel Management
```
GET  /api/v1/panels              # List all panels
POST /api/v1/panels              # Create panel
PUT  /api/v1/panels/{id}         # Update panel
POST /api/v1/panels/{id}/expand  # Auto-expand panel
```

### Trend Discovery
```
GET  /api/v1/trends              # Get all trends
GET  /api/v1/trends/{platform}   # Platform-specific
GET  /api/v1/trends/{id}         # Single trend detail
POST /api/v1/trends/{id}/brief   # Generate brief
```

### Feedback Loop
```
POST /api/v1/feedback/checkpoint # Record checkpoint
GET  /api/v1/feedback/analysis   # Get learnings
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Trends discovered per day | 50+ across platforms |
| False positive rate (creator campaigns) | < 10% |
| Trend detection latency | < 6 hours from emergence |
| Brief generation quality | 80%+ usable without edits |
| Feedback loop insights | Clear winners/losers per cluster |

---

## Technical Requirements

### Dependencies
- OpenAI API (embeddings + clustering labels)
- Whisper (Instagram transcription)
- YouTube Data API v3
- Twitter/X API v2
- RapidAPI scrapers (TikTok, Instagram)

### Infrastructure
- Background job queue for crawlers
- Vector database for embeddings (optional)
- Time-series storage for velocity tracking
- Caching for API responses

---

## Next Steps

1. **Implement YouTube RSS + Search collectors** (enhance existing)
2. **Add channel baseline normalization** (critical for scoring)
3. **Build TikTok sound-first detection**
4. **Add Instagram transcription pipeline**
5. **Integrate Twitter/X API**
6. **Build unified feedback dashboard**
