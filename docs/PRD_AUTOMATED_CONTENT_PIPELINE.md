# Product Requirements Document: Automated Content Pipeline

## Document Info
- **Version**: 1.0
- **Created**: December 9, 2025
- **Status**: Implementation Ready

---

## 1. Executive Summary

Build an end-to-end automated content pipeline that sources, analyzes, curates, and publishes content across multiple social media platforms with minimal human intervention. The system includes a "Tinder-like" swipe interface for quick content approval and intelligent scheduling.

---

## 2. Problem Statement

Content creators spend excessive time manually:
- Finding and organizing content
- Writing titles/descriptions for each platform
- Deciding which platforms suit which content
- Scheduling posts consistently
- Managing multiple accounts

---

## 3. Goals & Success Metrics

### Primary Goals
1. **Automate content sourcing** from local media library
2. **AI-powered content shaping** - generate platform-optimized titles, descriptions, hashtags
3. **Smart platform matching** based on niche, quality, and account focus
4. **Consistent posting schedule** - every 4 hours during daylight (6 AM - 10 PM)
5. **2-month content runway** - maintain 60+ pieces of approved content
6. **Quick approval workflow** - Tinder-style swipe interface
7. **Content reusability** - save alternate titles/descriptions for repurposing

### Success Metrics
| Metric | Target |
|--------|--------|
| Content approval time | < 5 seconds per piece |
| Platform match accuracy | > 85% |
| Posting consistency | > 95% on schedule |
| Content runway | 60+ days minimum |
| System uptime | > 99% |

---

## 4. Features & Requirements

### 4.1 Content Sourcing Engine

**Purpose**: Automatically discover and ingest content from configured sources.

| Requirement | Priority | Description |
|-------------|----------|-------------|
| CS-001 | P0 | Scan local media folders for new content |
| CS-002 | P0 | Auto-import images, videos, and clips |
| CS-003 | P1 | Detect duplicates and near-duplicates |
| CS-004 | P1 | Extract metadata (duration, resolution, format) |
| CS-005 | P2 | Support external sources (YouTube downloads, etc.) |

### 4.2 AI Content Analysis & Shaping

**Purpose**: Use AI to analyze content and generate platform-ready metadata.

| Requirement | Priority | Description |
|-------------|----------|-------------|
| AI-001 | P0 | Analyze visual content (scene, objects, people, mood) |
| AI-002 | P0 | Generate 3-5 title variations per content |
| AI-003 | P0 | Generate 3-5 description variations per content |
| AI-004 | P0 | Generate platform-specific hashtags |
| AI-005 | P1 | Suggest optimal posting time based on content type |
| AI-006 | P1 | Detect content niche (fitness, lifestyle, comedy, etc.) |
| AI-007 | P1 | Quality scoring (1-100) for each piece |
| AI-008 | P2 | Generate thumbnail suggestions |
| AI-009 | P2 | Caption/subtitle generation for videos |

### 4.3 Platform Matching Engine

**Purpose**: Intelligently match content to appropriate platforms and accounts.

| Requirement | Priority | Description |
|-------------|----------|-------------|
| PM-001 | P0 | Match content to platforms based on format compatibility |
| PM-002 | P0 | Match content to accounts based on niche alignment |
| PM-003 | P1 | Respect quality thresholds per platform |
| PM-004 | P1 | Balance post distribution across accounts |
| PM-005 | P2 | Learn from engagement data to improve matching |

**Platform Compatibility Matrix**:
| Platform | Image | Short Video (<60s) | Long Video | Carousel |
|----------|-------|-------------------|------------|----------|
| Instagram | ✓ | ✓ (Reels) | ✗ | ✓ |
| TikTok | ✗ | ✓ | ✓ (3 min) | ✗ |
| YouTube | ✓ | ✓ (Shorts) | ✓ | ✗ |
| Twitter/X | ✓ | ✓ | ✗ | ✗ |
| LinkedIn | ✓ | ✓ | ✓ | ✓ |
| Threads | ✓ | ✓ | ✗ | ✓ |

### 4.4 Swipe Approval Interface (Tinder-Style)

**Purpose**: Enable rapid content curation with intuitive gestures.

| Requirement | Priority | Description |
|-------------|----------|-------------|
| SA-001 | P0 | Display content card with preview and AI suggestions |
| SA-002 | P0 | Swipe right / → key = Approve for suggested platform(s) |
| SA-003 | P0 | Swipe left / ← key = Skip/Reject |
| SA-004 | P1 | Swipe up / ↑ key = Super approve (high priority) |
| SA-005 | P1 | Swipe down / ↓ key = Save for later |
| SA-006 | P1 | Click to edit title/description before approving |
| SA-007 | P1 | Show AI confidence score for suggestions |
| SA-008 | P2 | Undo last action |
| SA-009 | P2 | Bulk approve by filter (quality > 80, etc.) |

### 4.5 Smart Scheduling System

**Purpose**: Maintain consistent posting schedule with intelligent timing.

| Requirement | Priority | Description |
|-------------|----------|-------------|
| SS-001 | P0 | Post every 4 hours during daylight (6 AM - 10 PM) |
| SS-002 | P0 | Minimum 1 post per day per active account |
| SS-003 | P0 | Maximum configurable posts per day (default: 4) |
| SS-004 | P1 | Time zone aware scheduling |
| SS-005 | P1 | Avoid posting same content to same platform within 30 days |
| SS-006 | P1 | Priority queue for high-quality content |
| SS-007 | P2 | Optimal time suggestions based on audience analytics |

**Posting Windows** (Local Time):
- 6:00 AM - Morning content
- 10:00 AM - Mid-morning
- 2:00 PM - Afternoon  
- 6:00 PM - Evening
- 10:00 PM - Night (optional)

### 4.6 Content Reusability System

**Purpose**: Enable content repurposing with fresh metadata.

| Requirement | Priority | Description |
|-------------|----------|-------------|
| CR-001 | P0 | Store multiple title/description variations per content |
| CR-002 | P0 | Track which variations were used and when |
| CR-003 | P1 | Generate new variations on demand |
| CR-004 | P1 | Different thumbnails for same video |
| CR-005 | P2 | A/B testing framework for variations |

### 4.7 Content Runway Dashboard

**Purpose**: Visualize content pipeline health and capacity.

| Requirement | Priority | Description |
|-------------|----------|-------------|
| RD-001 | P0 | Show approved content count by platform |
| RD-002 | P0 | Display days of content remaining |
| RD-003 | P1 | Alert when runway drops below 14 days |
| RD-004 | P1 | Show pending approval queue size |
| RD-005 | P2 | Predictive analytics for content needs |

---

## 5. Technical Architecture

### 5.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONTENT PIPELINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Content    │───▶│     AI       │───▶│   Platform   │       │
│  │   Sourcer    │    │   Analyzer   │    │   Matcher    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                   Content Queue                       │       │
│  │  (pending_approval → approved → scheduled → posted)   │       │
│  └──────────────────────────────────────────────────────┘       │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Swipe      │───▶│   Scheduler  │───▶│   Publisher  │       │
│  │   Interface  │    │              │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Database Schema

```sql
-- Content with multiple variations
CREATE TABLE content_items (
    id UUID PRIMARY KEY,
    media_id UUID REFERENCES media,
    source_type VARCHAR(50),
    status VARCHAR(20), -- pending_analysis, pending_approval, approved, scheduled, posted, rejected
    quality_score INTEGER,
    niche VARCHAR(100),
    ai_analysis JSONB,
    created_at TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by VARCHAR(100)
);

-- Multiple title/description variations per content
CREATE TABLE content_variations (
    id UUID PRIMARY KEY,
    content_id UUID REFERENCES content_items,
    title VARCHAR(500),
    description TEXT,
    hashtags TEXT[],
    variation_index INTEGER,
    is_primary BOOLEAN,
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    platform_hint VARCHAR(50)
);

-- Scheduled posts
CREATE TABLE scheduled_posts (
    id UUID PRIMARY KEY,
    content_id UUID REFERENCES content_items,
    variation_id UUID REFERENCES content_variations,
    platform VARCHAR(50),
    account_id UUID,
    scheduled_time TIMESTAMP,
    status VARCHAR(20), -- pending, posted, failed, cancelled
    priority INTEGER DEFAULT 0,
    posted_at TIMESTAMP,
    platform_post_id VARCHAR(255),
    platform_url TEXT,
    error_message TEXT
);

-- Content assignment to platforms
CREATE TABLE content_platform_assignments (
    id UUID PRIMARY KEY,
    content_id UUID REFERENCES content_items,
    platform VARCHAR(50),
    account_id UUID,
    match_score FLOAT,
    match_reason TEXT,
    status VARCHAR(20), -- suggested, approved, rejected
    created_at TIMESTAMP
);
```

### 5.3 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/content-pipeline/queue | Get pending content for approval |
| POST | /api/content-pipeline/approve | Approve content with platform assignments |
| POST | /api/content-pipeline/reject | Reject content |
| POST | /api/content-pipeline/save-for-later | Save content for later review |
| GET | /api/content-pipeline/runway | Get content runway stats |
| POST | /api/content-pipeline/analyze | Trigger AI analysis on content |
| POST | /api/content-pipeline/generate-variations | Generate new title/desc variations |
| GET | /api/content-pipeline/schedule | Get scheduled posts |
| POST | /api/content-pipeline/schedule | Schedule a post |
| POST | /api/content-pipeline/publish | Manually trigger publish |
| GET | /api/content-pipeline/analytics | Get pipeline analytics |

---

## 6. User Interface Mockups

### 6.1 Swipe Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Content Approval Queue                    [23 pending]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌─────────────────────────────────────────┐              │
│    │                                         │              │
│    │         [Content Preview Image]         │              │
│    │                                         │              │
│    │             Quality: 87/100             │              │
│    │              Niche: Lifestyle           │              │
│    │                                         │              │
│    └─────────────────────────────────────────┘              │
│                                                             │
│    📝 Suggested Title:                                      │
│    "Living my best life in paradise 🌴"                     │
│                                                             │
│    📄 Suggested Description:                                │
│    "Sometimes you just need to escape..."                   │
│                                                             │
│    #️⃣ Hashtags: #lifestyle #travel #paradise               │
│                                                             │
│    📱 Suggested Platforms:                                  │
│    [✓] Instagram (@main_account) - 92% match               │
│    [✓] TikTok (@tiktok_account) - 85% match                │
│    [ ] YouTube Shorts - 45% match                          │
│                                                             │
│  ┌─────────┐              ┌─────────┐    ┌─────────┐       │
│  │   ←     │              │  EDIT   │    │    →    │       │
│  │  Skip   │              │         │    │ Approve │       │
│  └─────────┘              └─────────┘    └─────────┘       │
│                                                             │
│  ← Left Arrow = Skip    → Right Arrow = Approve            │
│  ↑ Up Arrow = Priority  ↓ Down Arrow = Save Later          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Content Runway Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Content Runway Dashboard                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ 67 days    │ │ 134        │ │ 23         │ │ 12       │ │
│  │ Runway     │ │ Approved   │ │ Pending    │ │ Today    │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│                                                             │
│  Content by Platform:                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Instagram ████████████████████░░░░░░  45 posts (34d) │  │
│  │ TikTok    ██████████████████████████  52 posts (39d) │  │
│  │ YouTube   ████████░░░░░░░░░░░░░░░░░░  18 posts (14d) │  │
│  │ Twitter   ████████████░░░░░░░░░░░░░░  25 posts (19d) │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Upcoming Posts (Next 24h):                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 6:00 AM  │ Instagram │ @main │ "Morning vibes..." │  │
│  │ 10:00 AM │ TikTok    │ @main │ "Check this out..." │  │
│  │ 2:00 PM  │ Instagram │ @alt  │ "Afternoon mood..." │  │
│  │ 6:00 PM  │ YouTube   │ @main │ "Evening routine.." │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Implementation Phases

### Phase 1: Core Pipeline (Week 1-2)
- [ ] Database schema setup
- [ ] Content sourcing from media library
- [ ] Basic AI analysis integration
- [ ] Title/description generation
- [ ] Content queue API

### Phase 2: Approval Interface (Week 2-3)
- [ ] Swipe interface UI
- [ ] Keyboard shortcuts
- [ ] Platform assignment UI
- [ ] Variation editing

### Phase 3: Scheduling System (Week 3-4)
- [ ] Scheduling engine
- [ ] Daylight hours logic
- [ ] 4-hour interval posting
- [ ] Queue management

### Phase 4: Publishing Integration (Week 4-5)
- [ ] Platform connectors
- [ ] Post tracking
- [ ] Error handling
- [ ] Retry logic

### Phase 5: Analytics & Optimization (Week 5-6)
- [ ] Runway dashboard
- [ ] Performance analytics
- [ ] A/B testing framework
- [ ] ML-based improvements

---

## 8. Testing Requirements

### Test Categories
1. **Unit Tests**: Individual component functions
2. **Integration Tests**: API endpoint testing
3. **E2E Tests**: Full pipeline flows
4. **Performance Tests**: Load and stress testing
5. **UI Tests**: Swipe interface interactions

### Test Coverage Target: 300 test cases
- Content Sourcing: 30 tests
- AI Analysis: 40 tests
- Platform Matching: 35 tests
- Swipe Interface: 50 tests
- Scheduling: 45 tests
- Publishing: 40 tests
- Variations: 25 tests
- Runway Dashboard: 20 tests
- Error Handling: 15 tests

---

## 9. Comment Automation System

### 9.1 Overview
Automated comment engagement system that analyzes top-performing content, generates contextual comments in the brand's tone, and posts them strategically across platforms to increase visibility and engagement.

### 9.2 Platform-Specific Features

#### TikTok
| Feature | Description |
|---------|-------------|
| **FYP Comment Scraping** | Scrape top comments from For You Page content |
| **Niche Video Discovery** | Search and analyze top niche videos |
| **Summary Comments** | AI-generated summary of top comments in brand tone |
| **Trend Targeting** | Focus on trending content within niche |

#### YouTube
| Feature | Description |
|---------|-------------|
| **Video Comment Analysis** | Analyze top comments on target videos |
| **Playlist Support** | Monitor and comment on playlist content |
| **Channel Targeting** | Focus on specific channels within niche |
| **Community Posts** | Engage with community tab content |

#### Instagram
| Feature | Description |
|---------|-------------|
| **Reel/Post Engagement** | Comment on niche-relevant content |
| **Story Replies** | Automated story engagement (where applicable) |
| **GitHub Repo Integration** | Custom implementation from user's repository |
| **Hashtag Discovery** | Find content via hashtag exploration |

### 9.3 Configuration Options

#### Comments Per Day Settings
```typescript
interface CommentConfig {
  daily_limit: number;          // Total comments per day (default: 50)
  per_niche_limit: number;      // Comments per niche (default: 10)
  per_platform_limit: number;   // Comments per platform (default: 20)
  min_interval_minutes: number; // Minimum time between comments (default: 15)
  max_interval_minutes: number; // Maximum time between comments (default: 60)
  jitter_percent: number;       // Random variance (default: 20%)
  active_hours: {               // Hours of operation
    start: number;              // Start hour (0-23)
    end: number;                // End hour (0-23)
  };
}
```

#### Niche-Specific Limits
```typescript
interface NicheConfig {
  niche: string;
  daily_limit: number;
  priority: 'high' | 'medium' | 'low';
  tone: string;                 // Brand tone for this niche
  keywords: string[];           // Target keywords
  exclude_keywords: string[];   // Avoid these topics
}
```

### 9.4 Automation Modes

| Mode | Description | Human Involvement |
|------|-------------|-------------------|
| **Full Auto** | Comments posted without review | None |
| **Semi-Auto** | AI generates, human approves batch | Review queue |
| **Manual Queue** | AI suggests, human edits & approves | Full control |

### 9.5 Approval System

#### Approval Queue Features
- **Bulk Approve/Reject** - Handle multiple comments at once
- **Edit Before Post** - Modify AI-generated text
- **Schedule Override** - Change posting time
- **Priority Boost** - Push important comments to front
- **Template Save** - Save effective comments as templates

#### Queue Status Flow
```
[Generated] → [Pending Review] → [Approved] → [Scheduled] → [Posted] → [Tracked]
                    ↓
              [Rejected]
                    ↓
            [Archive/Learn]
```

### 9.6 URL Link Tracking

| Tracking Feature | Description |
|------------------|-------------|
| **Source URL** | Original content URL being commented on |
| **Comment URL** | Permalink to posted comment (where available) |
| **Engagement Metrics** | Likes, replies on our comment |
| **Profile Clicks** | Traffic driven to our profile |
| **Conversion Tracking** | New followers attributed to comment |

### 9.7 Impact Analysis Dashboard

#### Metrics Tracked
| Metric | Description |
|--------|-------------|
| **Comments Posted** | Total successful comments |
| **Engagement Rate** | Likes/replies per comment |
| **Profile Visits** | Traffic driven by comments |
| **Follower Growth** | Correlated new followers |
| **Reach Expansion** | Estimated impressions |
| **Response Rate** | Replies received |
| **Sentiment Score** | Reception of our comments |

#### Analysis Views
- **Daily/Weekly/Monthly Trends** - Comment performance over time
- **Platform Comparison** - Which platform yields best results
- **Niche Performance** - Which niches respond best
- **Time of Day Analysis** - Optimal commenting windows
- **Content Type Correlation** - Best content types to engage with
- **ROI Calculation** - Effort vs. engagement gained

### 9.8 Safety & Compliance

| Safety Feature | Description |
|----------------|-------------|
| **Rate Limiting** | Respect platform limits |
| **Jitter/Randomization** | Avoid bot-like patterns |
| **Cooldown Periods** | Rest periods after heavy activity |
| **Duplicate Detection** | Never post same comment twice |
| **Spam Prevention** | Vary language and structure |
| **Account Rotation** | Distribute across accounts |
| **Blacklist Management** | Avoid problematic content |

---

## 10. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API rate limits | High | High | Queue management, backoff |
| AI hallucinations | Medium | Medium | Human review, templates |
| Platform API changes | Medium | High | Abstraction layer, monitoring |
| Content quality issues | Low | Medium | Quality scoring, thresholds |
| System downtime | Low | High | Redundancy, alerts |

---

## 10. Appendix

### A. Niche Categories
- Lifestyle, Fitness, Comedy, Education, Tech, Travel, Food, Fashion, Gaming, Music, Art, Business, Motivation, Entertainment

### B. Quality Scoring Factors
- Resolution, Lighting, Composition, Audio Quality, Content Clarity, Engagement Potential, Platform Fit

### C. Posting Schedule Template
| Time | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|------|-----|-----|-----|-----|-----|-----|-----|
| 6 AM | IG | TT | IG | TT | IG | IG | TT |
| 10 AM | TT | IG | TT | IG | TT | TT | IG |
| 2 PM | YT | TW | YT | TW | YT | IG | TT |
| 6 PM | IG | TT | IG | TT | IG | TT | IG |
| 10 PM | TT | IG | TT | IG | TT | IG | TT |

---

*Document End*
