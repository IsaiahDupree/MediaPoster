# PRD: Trend Discovery Platform

**Version:** 1.0 | **Date:** Dec 26, 2025

---

## 1. Executive Summary

A trend discovery platform helping creators identify and act on emerging trends across Instagram/TikTok. Aggregates content, clusters into "trends," generates AI insights.

---

## 2. Frontend Architecture

### Bottom Tab Navigation

| Tab | Purpose | Key Components |
|-----|---------|----------------|
| **Today** | Dashboard - new trends by country | Top cards: Sounds, Hashtags, Trends, Keywords |
| **Inspiration** | Idea feed | Hooks, scripts, shotlists, CTA variants, "remix this" |
| **Tools** | Content creation | Caption gen, hashtag packs, hook gen, shoot planner |
| **Analyzer** | URL analysis | Paste Reel/TikTok → trend match, recommendations |
| **Settings** | Configuration | Countries, niches, alerts, accounts, data sources |

### Drill-Down Pages

1. **Country Pack** (`/trends/usa`) - Tabs: Sounds | Hashtags | Trends | Keywords
2. **Trend Detail** (`/trend/:id`) - Summary, metrics, content ideas, format, examples
3. **Sound Detail** (`/sound/:id`) - Metadata, top videos, niches, velocity chart
4. **Hashtag Detail** (`/hashtag/:id`) - Volume, top posts, related tags, accounts
5. **Keyword Detail** (`/keyword/:id`) - Clusters, phrases, related hashtags
6. **Account Detail** (`/account/:id`) - Overview, top posts, sounds used, similar creators
7. **Saved/Favorites** (`/saved`) - Collections, export to Notion/CSV

---

## 3. Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DISCOVERY LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  Explore Sampling    │  Hashtag Sampling  │  Seed Accounts  │
│  (general trends)    │  (niche trends)    │  (creator feed) │
└──────────┬───────────┴─────────┬──────────┴────────┬────────┘
           │                     │                   │
           ▼                     ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   INGESTION LAYER                           │
├─────────────────────────────────────────────────────────────┤
│  Normalize: media_id, created_at, plays, likes, comments    │
│  Extract: caption, hashtags[], keywords[], music_id         │
│  Enrich: music_title, artist, user profile                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  Clustering: Group by sound + caption pattern + vibe        │
│  Scoring: Velocity, adoption, efficiency, saturation        │
│  Ranking: Top sounds, hashtags, keywords per country/niche  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI SUMMARIZATION                          │
├─────────────────────────────────────────────────────────────┤
│  Trend summary + Format bullets + Content ideas             │
│  Input: Top 30 captions + stats from cluster                │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Database Schema

### Core Tables

```sql
-- Entities (sounds, hashtags, keywords, users)
CREATE TABLE trend_entities (
  id UUID PRIMARY KEY,
  type TEXT NOT NULL, -- 'sound' | 'hashtag' | 'keyword' | 'user'
  external_id TEXT,
  name TEXT NOT NULL,
  country TEXT,
  niche TEXT,
  first_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw media ingested
CREATE TABLE trend_media (
  media_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL, -- 'instagram' | 'tiktok'
  author_id TEXT,
  author_username TEXT,
  caption TEXT,
  hashtags TEXT[],
  music_id TEXT,
  music_title TEXT,
  play_count INT,
  like_count INT,
  comment_count INT,
  share_count INT,
  created_at TIMESTAMPTZ,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily metrics snapshots
CREATE TABLE trend_metrics_daily (
  id UUID PRIMARY KEY,
  entity_id UUID REFERENCES trend_entities(id),
  date DATE NOT NULL,
  adoption_count INT, -- unique creators using it
  total_posts INT,
  median_plays INT,
  velocity_score FLOAT,
  saturation_score FLOAT,
  UNIQUE(entity_id, date)
);

-- Trend clusters (grouped content)
CREATE TABLE trend_clusters (
  id UUID PRIMARY KEY,
  name TEXT,
  description TEXT,
  format_bullets JSONB,
  content_ideas JSONB,
  primary_sound_id UUID,
  country TEXT,
  niche TEXT,
  velocity_score FLOAT,
  saturation_score FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cluster members
CREATE TABLE trend_cluster_media (
  cluster_id UUID REFERENCES trend_clusters(id),
  media_id TEXT REFERENCES trend_media(media_id),
  PRIMARY KEY (cluster_id, media_id)
);

-- User saved items
CREATE TABLE user_saved (
  id UUID PRIMARY KEY,
  user_id UUID,
  entity_type TEXT, -- 'sound' | 'hashtag' | 'trend' | 'cluster'
  entity_id UUID,
  collection_name TEXT DEFAULT 'default',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. API Contracts

### Trend List

```
GET /api/trends?country=US&niche=fitness&tab=sounds&limit=50

Response:
{
  "trends": [
    {
      "id": "uuid",
      "type": "sound",
      "name": "Original Sound - Artist",
      "velocity_score": 87,
      "saturation_score": 23,
      "adoption_24h": 1240,
      "adoption_delta": "+340%",
      "top_niches": ["fitness", "lifestyle"],
      "preview_url": "https://..."
    }
  ],
  "meta": { "total": 234, "page": 1 }
}
```

### Trend Detail

```
GET /api/trends/:id

Response:
{
  "id": "uuid",
  "type": "sound",
  "name": "Original Sound - Artist",
  "summary": "A high-energy dance trend where creators...",
  "format": [
    "Hook: 3-second attention grab with text overlay",
    "Build: Quick cuts showing transformation",
    "Payoff: Final reveal with emoji reaction"
  ],
  "content_ideas": [
    "Show a before/after fitness transformation",
    "Use for product unboxing reveals",
    "Remix as a 'day in my life' montage"
  ],
  "metrics": {
    "velocity_score": 87,
    "saturation_score": 23,
    "adoption_24h": 1240,
    "decay_estimate_days": 12
  },
  "top_examples": [
    { "media_id": "...", "thumbnail": "...", "plays": 2400000 }
  ],
  "geo_distribution": { "US": 45, "UK": 20, "BR": 15 }
}
```

---

## 6. Scoring Algorithms

### Velocity Score (0-100)
```python
velocity = (adoption_24h / max(1, adoption_7d_avg)) * 100
velocity_score = min(100, velocity * weight_factor)
```

### Saturation Score (0-100)
```python
saturation = total_posts / saturation_threshold
saturation_score = min(100, saturation * 100)
```

### Trend Score (composite)
```python
trend_score = (velocity_score * 0.6) + ((100 - saturation_score) * 0.3) + (efficiency * 0.1)
```

### Efficiency (engagement quality)
```python
efficiency = median_engagement_rate / baseline_engagement_rate
```

---

## 7. Phased Rollout

| Phase | Timeline | Deliverables |
|-------|----------|--------------|
| **1: Foundation** | Week 1-2 | DB schema, ingestion pipeline, basic API |
| **2: Discovery** | Week 3-4 | Explore/hashtag sampling, entity extraction |
| **3: Scoring** | Week 5-6 | Velocity/saturation metrics, daily snapshots |
| **4: Clustering** | Week 7-8 | Trend grouping, AI summarization |
| **5: Frontend** | Week 9-12 | All pages: Today, Inspiration, Tools, Analyzer |
| **6: Polish** | Week 13-14 | Export, saved collections, alerts |

---

## 8. Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TailwindCSS, shadcn/ui |
| Backend | Python FastAPI, Celery workers |
| Database | PostgreSQL (Supabase) |
| Cache | Redis |
| AI | OpenAI GPT-4 for summarization |
| Data Sources | Instagram Looter API (RapidAPI), TikTok unofficial |
| Hosting | Vercel (frontend), Railway/Render (backend) |

---

## 9. Security Notes

⚠️ **CRITICAL**: Never expose API keys in client-side code
- All RapidAPI calls must go through server-side route handlers
- Rotate any keys visible in screenshots immediately
- Store keys in `.env.local` (never commit to git)
