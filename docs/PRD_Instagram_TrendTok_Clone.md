# PRD: Instagram TrendTok-Style Analytics & Trend Discovery Platform

**Version:** 1.0  
**Date:** December 25, 2024  
**Status:** Phase Planning  
**Owner:** MediaPoster Team

---

## Executive Summary

Build a TrendTok-style analytics and trend discovery platform for Instagram, enabling creators to:
- Discover trending content formats, sounds, and hashtags
- Analyze their own content performance
- Get AI-powered recommendations for optimal posting
- Schedule content at best times based on audience insights

**Key Differentiator:** Multi-provider architecture with official Instagram Graph API + RapidAPI scrapers for comprehensive trend data.

---

## 1. Problem Statement

Instagram creators lack:
1. **Trend Discovery**: No official API for global trending sounds/hashtags like TikTok
2. **Content Intelligence**: Limited insights into what formats are working beyond their own account
3. **Posting Optimization**: No clear "best time to post" based on follower activity
4. **Format Templates**: No library of proven content structures to replicate

**Current Solution Gaps:**
- Meta's official API only shows user-owned account data
- Third-party tools are either expensive or unreliable
- Trend data requires manual research across multiple sources

---

## 2. Product Vision

### Core Features (TrendTok Parity)

**A. Trends Feed**
- Regional trending content (USA, Canada, etc.)
- Trending sounds/audio tracks
- Trending hashtags with velocity metrics
- Format templates ("Text-Hook Short-Form", "Overhead Grab POV", etc.)

**B. Content Analyzer**
- Upload video → AI analysis
- Extract: transcript, hook type, pacing, on-screen text density
- Match against trend card templates
- Return "do this next" suggestions

**C. Best Time to Post**
- Based on official Instagram Insights (follower online activity)
- Historical engagement pattern analysis
- Platform-specific recommendations

**D. Hashtag Generator**
- From trend cards + related tags + user niche
- Velocity-based ranking
- Competitive analysis

---

## 3. Technical Architecture

### 3.1 Multi-Provider Adapter Pattern

**Design Principle:** Don't couple to one data source. Build provider-agnostic adapters.

```typescript
interface ProviderAdapter {
  getProfile(handle: string): Promise<Profile>;
  getMedia(handle: string, cursor?: string): Promise<MediaPage>;
  getHashtag(tag: string): Promise<HashtagData>;
  getMediaInsights(mediaId: string): Promise<Insights>; // Official only
  search(query: string): Promise<SearchResults>;
}
```

**Provider Implementations:**

1. **InstagramGraphAdapter** (Official - Best for user accounts)
   - Auth: OAuth 2.0 with Facebook Page connection
   - Endpoints: Graph API v18.0+
   - Permissions: `instagram_manage_insights`, `pages_read_engagement`
   - Data: User media, insights, follower activity, publishing

2. **RapidApiInstagramAdapter** (Scraper - Best for trend discovery)
   - Auth: `X-RapidAPI-Key`, `X-RapidAPI-Host` headers
   - Base URL: `https://<provider>.p.rapidapi.com/v1/`
   - Endpoints: `/info`, `/reels`, `/hashtag`, `/search`
   - Identifier: `username_or_id_or_url` param (flexible)

### 3.2 Database Schema (Supabase)

```sql
-- Core entities
CREATE TABLE ig_profiles (
  id UUID PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  full_name TEXT,
  bio TEXT,
  followers_count INTEGER,
  following_count INTEGER,
  media_count INTEGER,
  is_verified BOOLEAN,
  profile_pic_url TEXT,
  provider TEXT, -- 'official' | 'rapidapi'
  last_fetched_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ig_media (
  id UUID PRIMARY KEY,
  ig_media_id TEXT UNIQUE NOT NULL,
  profile_id UUID REFERENCES ig_profiles(id),
  media_type TEXT, -- 'REEL' | 'IMAGE' | 'CAROUSEL'
  caption TEXT,
  permalink TEXT,
  thumbnail_url TEXT,
  like_count INTEGER,
  comment_count INTEGER,
  play_count INTEGER,
  timestamp TIMESTAMPTZ,
  audio_id UUID REFERENCES ig_audio(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ig_audio (
  id UUID PRIMARY KEY,
  audio_id TEXT UNIQUE NOT NULL,
  title TEXT,
  artist TEXT,
  duration_ms INTEGER,
  usage_count INTEGER DEFAULT 0,
  velocity_7d FLOAT, -- Growth rate over 7 days
  trending_score FLOAT,
  first_seen_at TIMESTAMPTZ,
  last_updated_at TIMESTAMPTZ
);

CREATE TABLE ig_hashtags (
  id UUID PRIMARY KEY,
  tag TEXT UNIQUE NOT NULL,
  media_count INTEGER,
  velocity_7d FLOAT,
  trending_score FLOAT,
  category TEXT,
  last_updated_at TIMESTAMPTZ
);

CREATE TABLE trend_cards (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL, -- "Text-Hook Short-Form", "Overhead Grab POV"
  description TEXT,
  format_type TEXT, -- 'hook_style' | 'pov' | 'tutorial' | 'storytelling'
  example_media_ids UUID[],
  velocity_7d FLOAT,
  trending_score FLOAT,
  region TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trend_observations (
  id UUID PRIMARY KEY,
  entity_type TEXT, -- 'audio' | 'hashtag' | 'format'
  entity_id UUID,
  observation_date DATE,
  usage_count INTEGER,
  engagement_rate FLOAT,
  region TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE analysis_jobs (
  id UUID PRIMARY KEY,
  video_id UUID REFERENCES videos(id),
  status TEXT, -- 'pending' | 'processing' | 'completed' | 'failed'
  transcript TEXT,
  hook_type TEXT,
  pacing TEXT,
  text_density FLOAT,
  matched_trend_cards UUID[],
  recommendations JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);
```

### 3.3 Request Normalization Layer

```typescript
type FetchSpec = {
  kind: "profile" | "media" | "hashtag" | "audio";
  query: string;          // username, url, hashtag, etc.
  cursor?: string | null; // provider pagination token
  region?: string;        // if supported
};

class ProviderRouter {
  async fetch(spec: FetchSpec): Promise<NormalizedResponse> {
    // 1. Try official API first (if user connected)
    if (this.hasOfficialAuth(spec.query)) {
      return await this.officialAdapter.fetch(spec);
    }
    
    // 2. Fallback to RapidAPI
    return await this.rapidApiAdapter.fetch(spec);
  }
}
```

---

## 4. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Basic adapter infrastructure + data ingestion

**Deliverables:**
- [ ] `InstagramGraphAdapter` implementation
  - OAuth flow for user account connection
  - Profile + media fetch
  - Insights retrieval
- [ ] `RapidApiInstagramAdapter` implementation
  - Provider selection (instagram-looter2 or instagram-scraper-api2)
  - Profile + media fetch
  - Hashtag search
- [ ] Database schema setup (Supabase migrations)
- [ ] `ProviderRouter` with fallback logic
- [ ] Basic ingestion worker (cron job to fetch trending data)

**Success Metrics:**
- Successfully fetch profile data from both providers
- Store normalized data in Supabase
- Handle pagination for media lists

---

### Phase 2: Trend Discovery (Weeks 3-4)
**Goal:** Build trend detection and ranking system

**Deliverables:**
- [ ] Trend crawler service
  - Monitor seed set of 50-100 high-engagement accounts
  - Extract audio usage, hashtag frequency, format patterns
  - Store in `trend_observations` table
- [ ] Velocity calculation engine
  - Daily aggregation of usage counts
  - 7-day growth rate calculation
  - Trending score algorithm (velocity × engagement × recency)
- [ ] Trend Cards library
  - Manual curation of 20-30 proven formats
  - Auto-detection of new emerging formats
  - Example media linking
- [ ] Trends API endpoints
  - `GET /api/trends/audio?region=USA&limit=50`
  - `GET /api/trends/hashtags?region=USA&limit=50`
  - `GET /api/trends/formats?region=USA&limit=50`

**Success Metrics:**
- Identify top 50 trending sounds per region
- Detect format velocity changes within 24 hours
- 90%+ accuracy on trend card classification

---

### Phase 3: Content Analyzer (Weeks 5-6)
**Goal:** AI-powered video analysis and recommendations

**Deliverables:**
- [ ] Video upload pipeline
  - Accept MP4/MOV uploads
  - Extract frames for visual analysis
  - Transcribe audio with Whisper
- [ ] AI analysis engine
  - Hook type detection (text-based, visual, audio)
  - Pacing analysis (cuts per minute, scene duration)
  - On-screen text density (OCR + positioning)
  - Sentiment analysis
- [ ] Trend matching algorithm
  - Compare video features against trend cards
  - Score similarity (0-100)
  - Generate "do this next" recommendations
- [ ] Analysis API
  - `POST /api/analyze/video` (upload)
  - `GET /api/analyze/{jobId}` (status)
  - `GET /api/analyze/{jobId}/recommendations` (results)

**Success Metrics:**
- Analyze video in < 30 seconds
- Match to trend cards with 80%+ accuracy
- Generate 5+ actionable recommendations per video

---

### Phase 4: Best Time to Post (Week 7)
**Goal:** Posting optimization based on audience insights

**Deliverables:**
- [ ] Official Insights integration
  - Fetch `online_followers` data (hourly breakdown)
  - Historical engagement by time-of-day
  - Day-of-week performance patterns
- [ ] Posting optimizer
  - Calculate optimal posting windows
  - Account for timezone differences
  - Factor in content type (Reel vs Image)
- [ ] Scheduling integration
  - Suggest best times when scheduling
  - Auto-schedule to optimal slots
  - A/B test different posting times
- [ ] Best Time API
  - `GET /api/insights/best-times?accountId={id}`
  - `GET /api/insights/performance-by-hour`

**Success Metrics:**
- Identify 3-5 optimal posting windows per day
- 20%+ engagement lift when posting at recommended times
- Support for multiple timezones

---

### Phase 5: Hashtag Generator (Week 8)
**Goal:** AI-powered hashtag recommendations

**Deliverables:**
- [ ] Hashtag intelligence engine
  - Analyze trending hashtags by niche
  - Calculate competition score (usage vs engagement)
  - Identify related/complementary tags
- [ ] Niche detection
  - Auto-detect user's niche from content
  - Build niche-specific hashtag sets
  - Track niche-specific trends
- [ ] Hashtag Generator API
  - `POST /api/hashtags/generate` (content + niche)
  - Returns 30 hashtags: 10 trending, 10 niche, 10 long-tail
  - Includes velocity + competition scores
- [ ] Frontend integration
  - Hashtag suggestions in post composer
  - Copy-to-clipboard functionality
  - Performance tracking per hashtag

**Success Metrics:**
- Generate 30 relevant hashtags in < 2 seconds
- 70%+ of suggested hashtags are actively trending
- 15%+ reach increase using generated hashtags

---

### Phase 6: Frontend Dashboard (Weeks 9-10)
**Goal:** TrendTok-style UI for all features

**Deliverables:**
- [ ] Trends Feed page
  - Trending sounds with usage stats
  - Trending hashtags with velocity charts
  - Format templates with examples
  - Regional filters (USA, Canada, UK, etc.)
- [ ] Content Analyzer page
  - Drag-and-drop video upload
  - Real-time analysis progress
  - Trend match results
  - Recommendations list
- [ ] Best Time to Post widget
  - Heatmap visualization
  - Optimal posting schedule
  - Historical performance overlay
- [ ] Hashtag Generator page
  - Content input (text/image)
  - Generated hashtag sets
  - Competition scores
  - Copy/export functionality

**Success Metrics:**
- < 3 second page load times
- Mobile-responsive design
- 90%+ feature discoverability

---

## 5. RapidAPI Provider Evaluation

### Recommended Providers

**Primary: instagram-looter2.p.rapidapi.com**
- ✅ Profile info with full metrics
- ✅ Media/Reels with engagement data
- ✅ Hashtag search
- ✅ Flexible `username_or_id_or_url` param
- ⚠️ Rate limit: 100 requests/month (free tier)

**Backup: instagram-scraper-api2.p.rapidapi.com**
- ✅ Similar endpoint coverage
- ❌ Known to return 401 "Blocked User" errors
- Use only as fallback

### Request/Response Examples

**Profile Info:**
```bash
GET https://instagram-looter2.p.rapidapi.com/v1/info?username_or_id_or_url=instagram
Headers:
  X-RapidAPI-Key: <your-key>
  X-RapidAPI-Host: instagram-looter2.p.rapidapi.com

Response:
{
  "data": {
    "username": "instagram",
    "full_name": "Instagram",
    "biography": "...",
    "follower_count": 123456789,
    "following_count": 123,
    "media_count": 456,
    "is_verified": true,
    "profile_pic_url": "https://..."
  }
}
```

**Media/Reels:**
```bash
GET https://instagram-looter2.p.rapidapi.com/v1/reels?username_or_id_or_url=instagram&cursor=<token>

Response:
{
  "data": {
    "items": [
      {
        "id": "123456789",
        "media_type": "REEL",
        "caption": "...",
        "like_count": 12345,
        "comment_count": 678,
        "play_count": 987654,
        "thumbnail_url": "https://...",
        "video_url": "https://...",
        "audio": {
          "id": "audio_123",
          "title": "Original Audio",
          "artist": "@username"
        }
      }
    ],
    "pagination_token": "next_cursor_token"
  }
}
```

---

## 6. Risk Mitigation

### Technical Risks

**Risk 1: RapidAPI Provider Instability**
- **Mitigation:** Multi-provider architecture with easy swapping
- **Fallback:** Official API for user accounts, manual trend curation

**Risk 2: Instagram ToS Violations**
- **Mitigation:** Use official API for all user-owned account operations
- **Scope:** Limit scraping to public trend discovery only

**Risk 3: Rate Limit Exhaustion**
- **Mitigation:** Implement request caching (1-hour TTL)
- **Monitoring:** Track API usage per provider
- **Upgrade Path:** Move to paid RapidAPI tiers as needed

### Business Risks

**Risk 1: Platform API Changes**
- **Mitigation:** Abstract all API calls behind adapters
- **Monitoring:** Automated health checks for all providers

**Risk 2: Competitive Landscape**
- **Differentiation:** Focus on Instagram (less saturated than TikTok)
- **Moat:** Proprietary trend detection algorithms + AI analysis

---

## 7. Success Metrics

### Phase 1-2 (Foundation + Trends)
- [ ] 50+ trending sounds identified per region
- [ ] 100+ trending hashtags tracked
- [ ] 30+ format templates cataloged
- [ ] < 5 minute data freshness

### Phase 3-4 (Analyzer + Posting)
- [ ] 1000+ videos analyzed
- [ ] 80%+ trend match accuracy
- [ ] 20%+ engagement lift from optimized posting times

### Phase 5-6 (Hashtags + Frontend)
- [ ] 10,000+ hashtags in database
- [ ] 100+ active users
- [ ] 90%+ user satisfaction (NPS)

---

## 8. Future Enhancements

**Post-MVP Features:**
- Multi-account management
- Competitor analysis
- Content calendar with auto-scheduling
- Collaboration tools for teams
- White-label version for agencies
- Cross-platform support (TikTok + Instagram)

---

## 9. Technical Stack

**Backend:**
- FastAPI (Python) - API server
- Supabase - PostgreSQL database
- Celery + Redis - Background jobs
- OpenAI GPT-4 - AI analysis
- Whisper - Audio transcription

**Frontend:**
- Next.js 14 - React framework
- TailwindCSS - Styling
- shadcn/ui - Component library
- Recharts - Data visualization

**Infrastructure:**
- Vercel - Frontend hosting
- Railway/Render - Backend hosting
- Supabase - Database + Auth
- Cloudflare R2 - Video storage

---

## 10. Appendix: Provider Adapter Interface

```typescript
// services/instagram/adapters/base.ts
export interface InstagramAdapter {
  name: string;
  type: 'official' | 'scraper';
  
  // Core methods
  getProfile(identifier: string): Promise<Profile>;
  getMedia(identifier: string, options?: MediaOptions): Promise<MediaPage>;
  getHashtag(tag: string): Promise<HashtagData>;
  search(query: string, type: SearchType): Promise<SearchResults>;
  
  // Official API only
  getInsights?(mediaId: string): Promise<Insights>;
  getFollowerActivity?(): Promise<ActivityData>;
  
  // Health check
  isHealthy(): Promise<boolean>;
}

// Normalized response types
export interface Profile {
  id: string;
  username: string;
  fullName: string;
  bio: string;
  followersCount: number;
  followingCount: number;
  mediaCount: number;
  isVerified: boolean;
  profilePicUrl: string;
  provider: string;
}

export interface MediaItem {
  id: string;
  mediaType: 'REEL' | 'IMAGE' | 'CAROUSEL';
  caption: string;
  permalink: string;
  thumbnailUrl: string;
  likeCount: number;
  commentCount: number;
  playCount?: number;
  timestamp: Date;
  audio?: AudioInfo;
}

export interface MediaPage {
  items: MediaItem[];
  cursor?: string;
  hasMore: boolean;
}
```

---

**End of PRD**

**Next Steps:**
1. Review and approve phases
2. Set up project tracking (GitHub Projects)
3. Begin Phase 1 implementation
4. Weekly progress reviews
