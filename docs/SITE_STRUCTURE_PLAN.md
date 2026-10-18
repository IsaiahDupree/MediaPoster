# Site Structure Plan: EverReach Blend Platform

> **Priority Focus**: Media Publishing & Cross-Platform Analytics

## Executive Summary

**One Big Brain** split into specialized sub-systems:
- **Blend**: Content graph (publishing, analytics, experiments)
- **EverReach Experimental**: People graph (relationships, insights, messaging)
- **MetaCoach**: Meta Graph API integration
- **Connectors**: Platform adapters (Meta, Blotato, YouTube, TikTok, LinkedIn)
- **ESP**: Email service provider layer
- **Enrichment**: RapidAPI identity resolution
- **Scrapers**: On-prem data collection (owned/consented only)

---

## Phase 1: Media Publishing & Analytics (PRIORITY)

### 1.1 Core Publishing Features

#### Content Publishing Dashboard
**Route**: `/studio/publish`

**Features**:
- Single content upload → 9 platform variants
- Platform-specific customization:
  - Titles (character limits per platform)
  - Thumbnails (aspect ratios: 16:9, 9:16, 1:1, 4:5)
  - Descriptions/captions
  - Hashtags
  - Platform-specific fields (YT chapters, TikTok sounds, etc.)
- Bulk scheduling across platforms
- Traffic type tagging (organic vs paid)

**API Endpoints**:
```
POST   /api/content/create
POST   /api/content/{id}/variants
POST   /api/content/{id}/publish
GET    /api/content/{id}/status
```

#### Cross-Platform Analytics
**Route**: `/analytics/overview`

**Features**:
- Unified metrics dashboard:
  - Views, Engagement Rate, CTR, Watch Time
  - Platform comparison charts
  - Time-series visualizations
- Filters:
  - Date range
  - Platform selection
  - Traffic type (organic/paid)
  - Content type (video/image/text)
- Export capabilities (CSV, PDF reports)

**Route**: `/analytics/content/{contentId}`

**Single Content View**:
- All 9 platform variants side-by-side
- Per-variant metrics:
  - Platform-specific KPIs
  - Sentiment analysis
  - Comments/reactions breakdown
- Performance comparison matrix
- A/B/APINK test results

### 1.2 Connector System (Publishing Focus)

#### Meta Connector (Priority 1)
- **Platforms**: Facebook, Instagram, Threads
- **Capabilities**:
  - Publish posts/stories/reels
  - Fetch metrics (reach, engagement, saves)
  - Ingest comments → people graph
- **Requirements**: Meta app with Graph API access

#### Blotato Connector (Priority 2)
- **Platforms**: All 9 platforms via Blotato API
- **Capabilities**:
  - Unified publishing interface
  - Platform post ID/URL storage
  - Pull metrics where available
- **Use Case**: Users without native API access

#### YouTube Connector (Priority 3)
- **Platform**: YouTube
- **Capabilities**:
  - Upload videos
  - Fetch analytics (views, watch time, CTR, retention)
  - Comments → people graph
- **Requirements**: Google Cloud project + YouTube Data API v3

#### TikTok Connector (Priority 4)
- **Platform**: TikTok
- **Capabilities**:
  - Publish videos
  - Fetch metrics (views, likes, shares, completion rate)
- **Requirements**: TikTok developer app

#### LinkedIn Connector (Priority 5)
- **Platform**: LinkedIn
- **Modes**: API-only | On-prem | Disabled
- **Capabilities**:
  - Publish posts (personal/company)
  - Fetch engagement metrics
- **Requirements**: LinkedIn app credentials

### 1.3 Database Schema (Publishing & Analytics)

#### Core Tables
```sql
-- Content management
content_items (id, user_id, title, description, type, created_at)
content_variants (id, content_id, platform, title, thumbnail_url, platform_post_id)
content_metrics (variant_id, date, views, engagement_rate, ctr, traffic_type)
content_rollups (content_id, total_views, total_engagement, best_platform)

-- Experiments
content_experiments (id, name, hypothesis, platforms, start_date, end_date)
experiment_variants (experiment_id, variant_id, test_group)
experiment_results (experiment_id, winner_variant_id, confidence_score)
```

---

## Phase 2: People Graph & Relationship Intelligence

### 2.1 EverReach Experimental Features

#### Unified Person Profile
**Route**: `/people/{personId}`

**Features**:
- Identity consolidation (email + IG + FB + LI + X + TikTok)
- Activity timeline across all channels
- Warmth score & engagement trends
- Interests & tone preferences
- Platform activity heatmap

#### Person Insights & Segments
**Route**: `/people/segments`

**Features**:
- Auto-segmentation based on:
  - Engagement level (hot, warm, cold)
  - Interests/topics
  - Platform preferences
  - Activity state (active, dormant, churned)
- Manual segment creation
- Segment analytics dashboard

#### Message Engine
**Route**: `/messaging/compose`

**Features**:
- AI-powered message generation:
  - Input: person context + brand context + goal
  - Output: personalized email/DM drafts
- Multi-channel messaging (email, IG DM, FB Messenger, LinkedIn)
- Tracking: opens, clicks, replies
- A/B testing for message variants

### 2.2 Database Schema (People Graph)

```sql
-- People & identities
people (id, primary_email, warmth_score, activity_state, created_at)
identities (id, person_id, platform, handle, verified, linked_at)
person_events (id, person_id, event_type, platform, content_id, traffic_type)

-- Insights
person_insights (person_id, interests, tone_prefs, channel_prefs, seasonality)
segments (id, name, criteria, auto_update)
segment_members (segment_id, person_id, added_at)
segment_insights (segment_id, size, growth_rate, engagement_avg)

-- Messaging
outbound_messages (id, person_id, channel, content, sent_at, opened_at, replied)
```

---

## Marketing Site Structure

### Public Pages

#### 1. Home / Landing
**Route**: `/`

**Story**: "One brain for your relationships and your content."

**CTAs**:
- "For Meta Coaches & Creators" → `/metacoach`
- "For Developers & Power Users" → `/docs`
- "Start Publishing" → `/studio`

#### 2. Blend: Cross-Platform Analytics
**Route**: `/blend`

**Content**:
- Explain the Content ID concept
- Show unified analytics dashboard mockup
- Highlight:
  - Single upload → 9 platforms
  - Unified metrics + sentiment
  - A/B/APINK testing
  - Content briefs generation

#### 3. EverReach Experimental
**Route**: `/everreach`

**Content**:
- Unified person graph across platforms
- Lenses: interests, tone, platform preferences
- Warmth scores & activity states
- Message engine demo
- Person timelines

#### 4. For Meta Coaches
**Route**: `/metacoach`

**Content**:
- MetaCoach Graph API integration
- FB + IG + Threads analytics
- Segment-based content briefs
- Optional Blotato upgrade path

**Requirements Card**:
- Meta app access
- Optional: Blotato for full 9-platform

#### 5. For Creators & Agencies
**Route**: `/creators`

**Content**:
- Cross-platform experiments
- Organic vs paid separation
- Per-segment briefs
- Editions overview

#### 6. Pricing & Editions
**Route**: `/pricing`

**App Modes**:
1. **Meta-Only Edition**
   - MetaCoach Graph API only
   - FB + IG + Threads
   - Required: Meta app credentials

2. **Blotato Edition**
   - Blotato API only
   - All 9 platforms via Blotato
   - Required: Blotato API key

3. **Full Stack Edition**
   - All native APIs + Blotato
   - Maximum control & data
   - Required: All platform credentials

4. **Local Lite Edition**
   - No external APIs
   - CSV uploads / manual entry
   - Offline analytics & briefs

#### 7. Security, Privacy & Compliance
**Route**: `/security`

**What We DON'T Do**:
- ❌ Username/password scraping
- ❌ Public profile spying
- ❌ Mass scraping without consent

**What We DO**:
- ✅ Official APIs (Meta, YouTube, TikTok)
- ✅ On-prem scrapers (owned data only)
- ✅ Optional RapidAPI enrichment (with consent)
- ✅ GDPR/CCPA compliant data handling

---

## Docs Site Structure

### 1. Getting Started

#### 1.1 System Architecture Overview
- High-level diagram
- Component interaction flow
- Data flow: collection → storage → analysis → insights

#### 1.2 Editions & App Modes
- `APP_MODE` environment variable
- Connector matrix by edition
- Example `.env` files

### 2. Core Concepts

#### 2.1 Content Graph
- Content Items (canonical content)
- Content Variants (platform-specific)
- Content Metrics (unified measurement)
- Content Rollups (aggregated insights)
- Content Experiments (A/B/APINK testing)

#### 2.2 People Graph
- People (unified identities)
- Identities (platform handles)
- Person Events (interactions)
- Person Insights (AI-derived attributes)
- Segments (behavioral groupings)

#### 2.3 Organic vs Paid Traffic
- `traffic_type` field on events & metrics
- Separate tracking & analysis
- Side-by-side reporting
- ROI attribution

### 3. Connectors & Integrations

#### 3.1 Connector Interface
```typescript
interface SourceAdapter {
  isEnabled(): boolean;
  listSupportedPlatforms(): Platform[];
  fetchMetricsForVariant(variantId: string): Promise<Metrics>;
  publishVariant(variant: ContentVariant): Promise<PublishResult>;
}
```

#### 3.2 MetaCoach Graph API Connector
- Required scopes/permissions
- Data mapping:
  - Posts/comments → content graph
  - Commenters/reactors → people graph
- Rate limits & quotas

#### 3.3 Blotato Connector
- Publishing workflow
- Platform post ID storage
- Metrics retrieval (where available)
- Blotato-only edition setup

#### 3.4 YouTube Connector
- Google Cloud Console setup
- OAuth 2.0 flow
- Metrics: views, watch time, CTR, retention
- Comments ingestion

#### 3.5 TikTok Connector
- TikTok Developer Portal setup
- Required app keys
- Available metrics
- Rate limits

#### 3.6 LinkedIn Connector
- API-only mode
- On-prem mode (optional)
- Company vs personal posts
- Engagement metrics

#### 3.7 Scrapers (Local-Only)
- On-prem deployment only
- Use cases: owned data, consented sources
- Compliance notes
- Data normalization

#### 3.8 Email ESP Layer
- Supported ESPs (SendGrid, Mailgun, AWS SES)
- Webhook configuration
- Event mapping to person_events
- Bounce/unsubscribe handling

#### 3.9 RapidAPI Enrichment
- Supported providers
- Input formats (email, handle)
- Output: cross-platform identities
- Privacy & consent requirements
- Rate limits & costs

### 4. Intelligence & AI

#### 4.1 Sentiment & Topic Analysis
- Sentiment scoring (-1 to +1)
- Topic extraction
- Application to:
  - Comments/replies
  - Content performance
  - Person interests

#### 4.2 Person "Lens" & Message Engine
**Input**:
```json
{
  "person_context": { "warmth_score": 0.8, "interests": ["AI", "marketing"] },
  "brand_context": { "tone": "professional", "products": [...] },
  "message_goal": "re-engagement"
}
```

**Output**:
```json
{
  "subject": "...",
  "body": "...",
  "cta": "...",
  "channel": "email"
}
```

#### 4.3 Segment-Based Content Briefs

**Organic Brief**:
- Segment snapshot (size, engagement, interests)
- Platform recommendations
- Format suggestions
- Angle ideas & hooks
- Expected engagement metrics

**Paid Brief**:
- Audience definition & objectives
- Creative patterns (proven performers)
- Budget allocation
- Test matrix (variants × audiences)
- Expected CTR/CPC benchmarks

#### 4.4 Content Experiments & APINK Testing
- Experiment setup
- Variant assignment
- Platform distribution
- Statistical significance calculation
- Winner determination

### 5. Setup Guides

#### 5.1 Meta-Only Edition Setup
1. Create Meta App
2. Request required permissions
3. Connect Pages/IG accounts
4. Configure `.env`
5. Verify connection
6. Start publishing

#### 5.2 Blotato-Only Edition Setup
1. Sign up for Blotato
2. Get API key
3. Connect platforms in Blotato
4. Configure `.env`
5. Test publishing workflow

#### 5.3 Full Stack Edition Setup
**Checklist**:
- [ ] Meta app credentials
- [ ] Google Cloud project (YouTube)
- [ ] TikTok developer app
- [ ] LinkedIn app (optional)
- [ ] Blotato API key
- [ ] RapidAPI key
- [ ] ESP credentials (SendGrid/Mailgun)

**Recommended Order**:
1. Meta (most common)
2. YouTube (high-value analytics)
3. Blotato (easy multi-platform)
4. TikTok (if relevant to audience)
5. LinkedIn (B2B use cases)
6. ESP (messaging capabilities)
7. RapidAPI (enrichment layer)

#### 5.4 Local Lite Edition Setup
- No external APIs required
- CSV upload format
- Manual metric entry
- Limitations & workarounds

### 6. Dev Reference

#### 6.1 Database Schema Reference
- Full ERD diagrams
- Table descriptions
- Relationships & foreign keys
- Indexes & performance notes

#### 6.2 API Reference
```
# Content Management
POST   /api/content/create
GET    /api/content/{id}
PUT    /api/content/{id}
DELETE /api/content/{id}
POST   /api/content/{id}/variants
POST   /api/content/{id}/publish

# Analytics
GET    /api/analytics/overview
GET    /api/analytics/content/{id}
GET    /api/analytics/platforms
GET    /api/analytics/export

# People & Segments
GET    /api/people/{id}
GET    /api/people/{id}/timeline
POST   /api/segments/create
GET    /api/segments/{id}/members
POST   /api/segments/{id}/insights

# Messaging
POST   /api/messages/generate
POST   /api/messages/send
GET    /api/messages/{id}/status

# Experiments
POST   /api/experiments/create
POST   /api/experiments/{id}/variants
GET    /api/experiments/{id}/results
```

---

## Implementation Priority

### Sprint 1: Core Publishing (Weeks 1-2)
- [ ] Content upload UI
- [ ] Platform variant creator
- [ ] Meta connector (publish)
- [ ] Basic analytics dashboard

### Sprint 2: Multi-Platform (Weeks 3-4)
- [ ] Blotato connector
- [ ] YouTube connector
- [ ] Unified metrics aggregation
- [ ] Traffic type tagging

### Sprint 3: Advanced Analytics (Weeks 5-6)
- [ ] Single content view
- [ ] Platform comparison charts
- [ ] Sentiment analysis
- [ ] Export capabilities

### Sprint 4: People Graph (Weeks 7-8)
- [ ] Person profile consolidation
- [ ] Event ingestion pipeline
- [ ] Warmth score calculation
- [ ] Segmentation UI

### Sprint 5: Intelligence Layer (Weeks 9-10)
- [ ] Message engine
- [ ] Content briefs generation
- [ ] Experiments framework
- [ ] AI-powered insights

---

## Technical Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **UI**: TailwindCSS + Radix UI
- **State**: Zustand
- **Data Fetching**: TanStack Query
- **Charts**: Recharts / Chart.js
- **Forms**: React Hook Form + Zod

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (Supabase)
- **ORM**: SQLAlchemy 2.0 (async)
- **Cache**: Redis
- **Queue**: Celery + Redis
- **AI**: OpenAI API / Anthropic Claude

### Infrastructure
- **Hosting**: Vercel (frontend) + Railway (backend)
- **Database**: Supabase
- **Storage**: Supabase Storage / AWS S3
- **CDN**: Cloudflare
- **Monitoring**: Sentry + PostHog

---

## Next Steps

1. **Resolve Database Connection** (immediate blocker)
   - Install PostgreSQL OR
   - Configure Supabase OR
   - Add SQLite fallback

2. **Build Publishing MVP**
   - Content upload form
   - Meta connector integration
   - Basic analytics dashboard

3. **Expand Platform Support**
   - Blotato connector
   - YouTube connector
   - Unified metrics

4. **Add Intelligence Layer**
   - Sentiment analysis
   - Content briefs
   - Message generation

5. **Complete People Graph**
   - Identity consolidation
   - Segmentation
   - Warmth scoring
