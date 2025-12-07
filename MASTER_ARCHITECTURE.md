# 🏗️ Master Architecture: EverReach Experimental + Blend + MetaCoach

## Vision Statement

Build a **unified growth & relationship intelligence platform** that combines:
1. **EverReach Experimental** - People/Relationship Brain across all platforms
2. **Blend** - Cross-platform content analytics & experimentation
3. **MetaCoach** - Meta-specific (Facebook/Instagram/Threads) edition
4. **Modular Connectors** - Support for 9+ social platforms

---

## 🎯 Two Core Systems

### 1. **EverReach Experimental** (People Brain)

**Purpose**: Unified person graph across email + all social platforms

**Core Concept**:
```
One Person → Multiple Identities → Unified Lens → Personalized Messages
```

**Schema**:
```sql
-- Core people table
people (id, full_name, primary_email, company, role)

-- Cross-platform identities
identities (
  person_id, 
  channel (email | instagram | facebook | threads | twitter | linkedin | tiktok),
  handle,
  profile_metadata
)

-- Unified event stream
person_events (
  person_id,
  channel,
  event_type (commented | liked | opened_email | clicked_link | dm_reply),
  traffic_type (organic | paid),
  platform_id,
  content_excerpt,
  sentiment,
  occurred_at
)

-- Person intelligence layer
person_insights (
  person_id,
  interests (topics),
  tone_preferences,
  channel_preferences,
  activity_state (active | warming | dormant),
  seasonality,
  warmth_score
)
```

**Message Engine**:
```
Input:
  - Person Context (from person_insights + recent events)
  - Your Context (brand, offers, voice)
  - Message Goal (invite, nurture, reactivate, sell)

Output:
  - Personalized email/DM
  - Optimal channel & timing
  - A/B variants
```

---

### 2. **Blend** (Content Brain)

**Purpose**: Single content ID → multiple platform variants → unified analytics

**Core Concept**:
```
1 Content → 9 Platform Variants → Different Titles/Thumbs/Descriptions → Unified Metrics
```

**Schema**:
```sql
-- Canonical content
content_items (
  id,  -- GLOBAL CONTENT ID
  slug,
  type (video | article | audio | image | carousel),
  source_url,
  title,
  description
)

-- Platform-specific variants
content_variants (
  content_id,
  platform (instagram | tiktok | youtube | facebook | threads | twitter | linkedin | pinterest | bluesky),
  platform_post_id,
  platform_post_url,
  title,  -- platform-specific
  description,  -- platform-specific
  thumbnail_url,  -- platform-specific
  published_at,
  is_paid (organic vs ad),
  experiment_id,
  variant_label
)

-- Metrics per variant
content_metrics (
  variant_id,
  snapshot_at,
  views, impressions, reach,
  likes, comments, shares, saves, clicks,
  watch_time_seconds,
  traffic_type (organic | paid),
  sentiment_score
)

-- Rollups per content
content_rollups (
  content_id,
  total_views,
  total_engagement,
  avg_sentiment,
  best_platform,
  organic_vs_paid_breakdown
)
```

**Content Brief Generator**:
```
Input:
  - Segment (bucketized audience)
  - Past performance data
  - Campaign goal

Output:
  - Who they are & what they care about
  - Best platforms & formats
  - Hook templates & angles
  - Expected engagement ranges
  - Posting time recommendations
```

---

## 🔌 Connector Architecture

### Modular Source Adapters

All platforms implement the same interface:

```typescript
interface SourceAdapter {
  id: string;  // 'meta', 'youtube', 'tiktok', 'blotato', etc.
  
  isEnabled(): boolean;  // checks env + config
  
  listSupportedPlatforms(): string[];
  
  fetchMetricsForVariant(variant): Promise<Metrics[]>;
  
  publishVariant?(variant): Promise<{ url, platformPostId }>;
}
```

---

## 📦 Connector Inventory

### 1. **MetaCoach Graph API** (Meta Platforms)
**Platforms**: Facebook, Instagram, Threads  
**Requirements**: Meta App ID, App Secret, Page/IG connection  
**Capabilities**:
- Fetch posts, comments, reactions, shares
- Pull insights (reach, impressions, saves)
- Get commenter/reactor identities
- Real-time metrics via checkbacks

**Data Flow**:
```
Meta API → content_variants + content_metrics (Content Brain)
         → identities + person_events (People Brain)
```

---

### 2. **Blotato Integration** (9-Platform Hub)
**Platforms**: All 9 supported by Blotato  
**Requirements**: Blotato API key  
**Capabilities**:
- Post to multiple platforms from single API
- Retrieve platform post IDs
- Fetch basic metrics where available

**Use Cases**:
- **Blotato-Only Edition**: Users without native API access
- **Full Stack**: Complement native APIs with Blotato posting

---

### 3. **YouTube Connector**
**Platform**: YouTube  
**Requirements**: Google Cloud Console secrets  
**Capabilities**:
- Upload videos
- Fetch analytics (views, watch time, CTR, demographics)
- Get comments & sentiment

---

### 4. **TikTok Connector**
**Platform**: TikTok  
**Requirements**: TikTok Developer app credentials  
**Capabilities**:
- Post videos
- Fetch video analytics
- Get comments

---

### 5. **LinkedIn Connector** (Modular)
**Platform**: LinkedIn  
**Requirements**: LinkedIn API access (strict approval process)  
**Modes**:
- **API-Only**: Use official APIs where approved
- **On-Prem Scraper**: Locally hosted for owned data only
- **Disabled**: No LinkedIn features

---

### 6. **Twitter/X Connector**
**Platform**: X (Twitter)  
**Requirements**: X API Pro tier (paid)  
**Capabilities**:
- Post tweets
- Fetch mentions, replies
- Get engagement metrics

---

### 7. **Local Scrapers** (On-Prem Only)
**Purpose**: Supplement APIs where limited  
**Critical Rules**:
- ✅ Only on self-hosted infrastructure
- ✅ Only for owned/consented data
- ✅ Never exposed as public service
- ✅ Must respect platform ToS

**Use Cases**:
- Fetch metrics when APIs are rate-limited
- Historical data backfill
- Public profile info enrichment

---

### 8. **Email Service Provider** (Custom ESP)
**Purpose**: Outbound messaging + event tracking  
**Capabilities**:
- Send personalized emails
- Track opens, clicks, bounces, unsubscribes
- Webhook receivers → person_events
- Template system with person/segment variables

**Integration**:
```
ESP → outbound_messages table
ESP webhooks → person_events (channel='email')
```

---

### 9. **RapidAPI Enrichment** (Optional)
**Purpose**: Cross-reference social handles ↔ emails  
**Requirements**: RapidAPI subscription  
**Services Used**:
- Social handle → email lookup
- Email → social profiles lookup

**Critical Rules**:
- ✅ Only for people you have legitimate relationship with
- ✅ Clear consent & GDPR/CCPA compliance
- ✅ Feature-flagged (optional)
- ✅ Not for mass "people finder" scraping

**Data Flow**:
```
RapidAPI → enriches identities table
         → updates people.primary_email
```

---

## 🎛️ App Modes & Editions

### One Codebase, Multiple Editions

Controlled by `APP_MODE` environment variable:

#### **1. MetaCoach Edition** (`APP_MODE=meta_only`)
**Target**: Meta coaches, Instagram/Facebook creators  
**Enabled Connectors**:
- ✅ MetaCoach Graph API
- ✅ Custom ESP
- ❌ YouTube, TikTok, LinkedIn
- ❌ Blotato (optional add-on)

**Features**:
- Facebook, Instagram, Threads analytics
- Meta-specific content briefs
- Segment analysis for Meta audiences

---

#### **2. Blotato Edition** (`APP_MODE=blotato_only`)
**Target**: Users with only Blotato access  
**Enabled Connectors**:
- ✅ Blotato
- ✅ Custom ESP
- ❌ Native platform APIs

**Features**:
- Post to 9 platforms via Blotato
- Basic metrics from Blotato
- Cross-platform content tracking

---

#### **3. Full Stack Edition** (`APP_MODE=full_stack`)
**Target**: Power users, agencies  
**Enabled Connectors**:
- ✅ MetaCoach Graph API
- ✅ Blotato
- ✅ YouTube
- ✅ TikTok  
- ✅ LinkedIn
- ✅ Twitter/X
- ✅ Custom ESP
- ✅ RapidAPI Enrichment
- ✅ Local Scrapers

**Features**:
- Everything
- Complete cross-platform intelligence
- All analysis tools

---

#### **4. Local Lite Edition** (`APP_MODE=local_lite`)
**Target**: Privacy-focused users, air-gapped setups  
**Enabled Connectors**:
- ✅ Custom ESP
- ✅ CSV/URL import
- ❌ All external APIs

**Features**:
- Manual metrics input
- Offline analysis
- Content briefs based on historical CSV data

---

## 📊 Key Features Breakdown

### **A. Segment Intelligence**

**What It Does**:
Bucketize your audience based on behavior, interests, engagement patterns

**Schema**:
```sql
segments (id, name, definition, created_at)

segment_members (segment_id, person_id)

segment_insights (
  segment_id,
  traffic_type (organic | paid),
  top_topics,
  top_platforms,
  top_formats,
  engagement_style,
  best_times,
  expected_reach_range,
  expected_engagement_rate
)
```

**Examples**:
- "IG Superfans who also open emails, interested in 'AI automation'"
- "Dormant LinkedIn contacts who engaged with pricing content last year"
- "New followers who commented positively in last 2 weeks"

---

### **B. Content Briefs (Organic vs Paid)**

**Organic Brief**:
```
Input: Segment + Goal + Past Performance
Output:
  - Who they are & pain points
  - Best platforms (IG feed vs Reels vs LinkedIn)
  - Format recommendations (60s Reels + 3-slide carousels)
  - Hook templates proven to work
  - Expected views/engagement range
  - Optimal posting times
```

**Paid Brief**:
```
Input: Segment + Budget + Past Ad Performance
Output:
  - Best audience targets
  - Creative patterns that worked (hooks, visuals)
  - Recommended budget & frequency
  - Testing matrix (hook vs offer vs creative)
  - Expected CTR, CPC, cost per result
```

**Kept Separate**: Organic & Paid insights stored separately, shown side-by-side

---

### **C. Cross-Platform Experiments**

**What It Does**:
A/B test different titles, thumbnails, descriptions across platforms

**Schema**:
```sql
content_experiments (
  id,
  content_id,
  name,
  hypothesis,
  primary_metric (ctr | watch_time | engagement_rate)
)
```

**Example**:
```
Experiment: "Test curiosity title vs direct title"
Variant A (IG + TikTok): "You're doing X wrong" + Thumb 1
Variant B (YouTube + LI): "How to do X correctly" + Thumb 2

Results:
  Variant A: CTR 1.8%, sentiment +0.2
  Variant B: CTR 3.1%, sentiment +0.6
  
Winner: Variant B for YouTube/LinkedIn audiences
```

---

### **D. Cross-Platform Content Page**

**URL**: `https://yoursite.com/content/<content_id>`

**What You See**:
```
┌─────────────────────────────────────────────────┐
│ "How to Automate Client Onboarding"            │
│ [Play Video] 📹 2:15                            │
├─────────────────────────────────────────────────┤
│ Platform │ Thumb │ Title │ Views │ Eng │ Sent  │
├─────────────────────────────────────────────────┤
│ Instagram│  🎨1  │ T1    │ 45k   │4.2% │+0.3   │
│ TikTok   │  🎨2  │ T2    │ 89k   │5.1% │+0.5   │
│ YouTube  │  🎨3  │ T3    │ 12k   │7.8% │+0.6   │
│ LinkedIn │  🎨1  │ T4    │  3k   │2.1% │+0.4   │
│ Facebook │  🎨2  │ T1    │ 21k   │3.5% │+0.2   │
├─────────────────────────────────────────────────┤
│ 📊 Overall: 170k views, 4.5% eng, +0.4 sent    │
│ 🏆 Best Platform: TikTok (5.1% engagement)     │
│ 💡 Insight: Curiosity titles outperform 2.3x   │
└─────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Examples

### **1. Instagram Comment → Person Event**
```
User @jane_doe comments "this workflow is 🔥" on your IG Reel

Flow:
1. MetaCoach Graph API fetches comment
2. Creates/updates identities:
   - person_id: <jane_uuid>
   - channel: 'instagram'
   - handle: '@jane_doe'
3. Creates person_events:
   - event_type: 'commented'
   - content_excerpt: "this workflow is 🔥"
   - sentiment: +0.8 (positive)
   - channel: 'instagram'
4. Updates person_insights:
   - interests += ['workflows', 'automation']
   - last_active_at = now()
   - activity_state = 'active'
```

---

### **2. Posting Content to 9 Platforms via Blotato**
```
You create video: "How I automate emails"

Flow:
1. Create content_items:
   - id: <content_uuid>
   - title: "How I automate emails"
   - source_url: "https://cdn.yoursite.com/video.mp4"

2. Create 9 content_variants:
   - IG: vertical crop, hooky caption, hashtags
   - TikTok: vertical, trending audio, short title
   - YouTube: landscape, SEO title, long description
   - (repeat for FB, LI, X, Threads, Pinterest, Bluesky)

3. For each variant:
   - Call Blotato API: POST /v2/posts
   - Store platform_post_id, platform_post_url

4. Schedule checkbacks:
   - 1h, 6h, 24h, 72h, 7d
   - Fetch metrics → content_metrics table

5. Nightly rollup:
   - Aggregate all variants → content_rollups
   - Calculate best_platform, global_sentiment
```

---

### **3. Generating Personalized Email**
```
Goal: Invite segment "Engaged IG Followers" to your course

Flow:
1. Query segment_insights:
   - top_topics: ['AI', 'automation', 'workflows']
   - tone_preferences: ['casual', 'practical']
   - channel_preferences: email=0.9, instagram_dm=0.7

2. For each person in segment:
   - Fetch person_insights
   - Fetch recent person_events (last 30 days)

3. Build AI prompt:
   ```
   Person: Alex
   Interests: AI automation, workflows
   Recent: Commented "so helpful" on your Reel
   Tone: Casual, practical
   
   Goal: Invite to course "Email Automation Mastery"
   Channel: Email
   ```

4. Generate email:
   - Subject: "Alex, your next workflow upgrade →"
   - Body: [personalized based on their lens]
   - CTA: "Get early access →"

5. Send via ESP → creates outbound_messages row

6. Track opens/clicks → person_events
```

---

## 🛡️ Privacy & Compliance Baseline

### What You DO
- ✅ Use official Platform APIs with OAuth
- ✅ Ingest data for accounts you own/control
- ✅ Pull engagement on your own content
- ✅ Enrich identities for people you have relationship with
- ✅ Clear consent flows for enrichment
- ✅ GDPR/CCPA compliance (data export, deletion, portability)

### What You DON'T DO
- ❌ Username/password credential harvesting
- ❌ Mass public profile scraping
- ❌ Unauthorized email harvesting
- ❌ Expose scrapers as public "stalking" service
- ❌ Mix ad-driven data with organic without clear labeling

### Platform ToS Compliance
- Meta: Only Graph API, no automated login
- LinkedIn: Official API only (where approved), strict on scrapers
- YouTube: Google Cloud APIs, respect quotas
- TikTok: Official TikTok Developer APIs
- Twitter/X: Paid API tier, respect rate limits

---

## 📐 MVP Scope (Baseline)

### **Phase 1: Core Foundation** (4-6 weeks)
**Database**:
- ✅ Implement all core tables (people, identities, events, insights, content, variants, metrics)
- ✅ Set up Supabase with proper indexes

**Connectors** (foundational):
- ✅ MetaCoach Graph API (Instagram + Facebook)
- ✅ Custom ESP (basic sending + webhooks)

**UI**:
- ✅ Dashboard showing people & content
- ✅ Single person view (timeline of events)
- ✅ Single content view (platform variants + metrics)

---

### **Phase 2: Intelligence Layer** (4-6 weeks)
**Analysis**:
- ✅ Sentiment analysis on comments/events
- ✅ Basic person_insights computation
- ✅ Segment creation & management

**Content Briefs**:
- ✅ V1 organic brief generator
- ✅ Show expected engagement ranges

**UI**:
- ✅ Segment explorer
- ✅ Content brief viewer
- ✅ Person lens view

---

### **Phase 3: Multi-Platform** (6-8 weeks)
**Connectors**:
- ✅ Blotato integration
- ✅ YouTube connector
- ✅ TikTok connector
- ✅ LinkedIn connector (API-only mode)

**Features**:
- ✅ Cross-platform posting workflow
- ✅ Cross-platform metrics dashboard
- ✅ A/B experiment tracking

---

### **Phase 4: Advanced Features** (ongoing)
- ✅ Paid brief generator
- ✅ RapidAPI enrichment (optional)
- ✅ Local scrapers for power users
- ✅ Advanced experiments & pattern detection
- ✅ Predictive analytics

---

## 🎨 Website Structure

### **Public Marketing Site**

#### Homepage
- Hero: "One Brain for Your Relationships and Content"
- Two pillars: EverReach (People) + Blend (Content)
- CTA: Choose your edition

#### For Meta Coaches
- MetaCoach + Blend Edition focus
- Facebook, Instagram, Threads features
- Content briefs for Meta platforms

#### For Creators & Agencies
- Full Stack features
- Cross-platform experiments
- Organic vs Paid separation

#### Pricing & Editions
- Meta-Only Edition
- Blotato Edition
- Full Stack Edition
- Local Lite Edition

#### Security & Privacy
- What we do / don't do
- Platform ToS compliance
- Data handling policies

---

### **Documentation Site**

#### Getting Started
- System architecture diagram
- Editions & app modes
- Quick start guides per edition

#### Core Concepts
- People Graph
- Content Graph & Content ID
- Organic vs Paid model
- Segments & Insights

#### Connectors
- MetaCoach Graph API
- Blotato
- YouTube
- TikTok
- LinkedIn (modular)
- Email ESP
- RapidAPI Enrichment
- Local Scrapers

#### Intelligence & AI
- Sentiment analysis
- Person lens & message engine
- Content briefs (organic + paid)
- Experiments

#### Setup Guides
- Per edition setup instructions
- Required API keys
- Environment configuration

#### API Reference
- Database schema
- REST/GraphQL APIs
- Webhook formats

---

## 🚀 Next Steps

### Immediate (This Week)
1. ✅ Finalize database schema in Supabase
2. ✅ Create connector interface contracts
3. ✅ Build MetaCoach Graph API connector (MVP)
4. ✅ Create single content page prototype

### Short Term (This Month)
1. Implement basic person_insights computation
2. Build segment creation UI
3. V1 organic content brief generator
4. Blotato connector

### Medium Term (This Quarter)
1. YouTube + TikTok connectors
2. LinkedIn connector (modular)
3. Full cross-platform experiment system
4. Paid brief generator

### Long Term (Next Quarter+)
1. RapidAPI enrichment
2. Advanced predictive analytics
3. Auto-optimization features
4. Public API for developers

---

## 📊 Success Metrics

### Platform Metrics
- Videos/content ingested per week
- Cross-platform posts created
- Segments actively used
- Content briefs generated
- Experiments run

### User Growth Metrics (North Stars)
- Weekly Engaged Reach trend
- Content Leverage Score improvement
- Warm Lead Flow growth
- Time from idea → published clip

---

**This is the complete architecture for your creator intelligence platform. Ready to build! 🚀**
