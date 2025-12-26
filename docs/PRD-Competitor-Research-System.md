# PRD: Competitor Research & Influencer Analysis System

## Overview

A system to track, download, analyze, and learn from competitor and star influencer content on Instagram. This enables data-driven content strategy by studying proven viral content patterns.

## Goals

1. **Track Competitors** - Monitor specific Instagram accounts for content insights
2. **Download Content** - Fetch all reels, posts, and media with metrics
3. **Analyze Performance** - Study what makes content go viral
4. **Generate Learnings** - Create actionable documentation from analysis
5. **Apply Insights** - Use learnings to improve our own content

## Target Accounts (Initial)

- `@personalbrandlaunch` - Personal branding expert with viral content
- More accounts can be added via the system

---

## System Architecture

### Folder Structure

```
/Users/isaiahdupree/Documents/
├── IphoneImport/              # Our own content (existing)
├── CompetitorResearch/        # NEW: Competitor content
│   ├── accounts/
│   │   └── personalbrandlaunch/
│   │       ├── profile.json           # Account info
│   │       ├── reels/                 # Downloaded reels
│   │       │   ├── ABC123.mp4
│   │       │   └── ABC123.json        # Metrics + analysis
│   │       ├── posts/                 # Downloaded posts
│   │       └── analysis/              # AI-generated insights
│   │           ├── content_patterns.md
│   │           ├── viral_hooks.md
│   │           └── performance_summary.md
│   ├── learnings/             # Cross-account insights
│   │   ├── top_performing_hooks.md
│   │   ├── optimal_posting_times.md
│   │   └── content_formulas.md
│   └── config.json            # Tracked accounts config
```

### Database Tables

```sql
-- Tracked competitor accounts
CREATE TABLE competitor_accounts (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    user_id TEXT,
    full_name TEXT,
    bio TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    media_count INTEGER,
    is_verified BOOLEAN,
    profile_pic_url TEXT,
    category TEXT,
    priority INTEGER DEFAULT 1,  -- 1=high, 2=medium, 3=low
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Competitor content (reels, posts)
CREATE TABLE competitor_content (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES competitor_accounts(id),
    media_id TEXT UNIQUE NOT NULL,
    shortcode TEXT,
    media_type TEXT,  -- 'reel', 'post', 'carousel'
    caption TEXT,
    
    -- Metrics
    play_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    share_count INTEGER,
    save_count INTEGER,
    
    -- Engagement rates
    engagement_rate NUMERIC,
    viral_score NUMERIC,
    
    -- Media files
    video_url TEXT,
    thumbnail_url TEXT,
    local_video_path TEXT,
    local_thumbnail_path TEXT,
    
    -- Audio
    audio_id TEXT,
    audio_title TEXT,
    audio_artist TEXT,
    
    -- Timestamps
    posted_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT NOW(),
    analyzed_at TIMESTAMP,
    
    -- Analysis results
    detected_hooks JSONB,
    content_themes JSONB,
    visual_style JSONB,
    ai_analysis JSONB
);

-- Analysis learnings
CREATE TABLE competitor_learnings (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES competitor_accounts(id),
    learning_type TEXT,  -- 'hook', 'format', 'timing', 'topic'
    title TEXT,
    description TEXT,
    evidence JSONB,  -- References to content that supports this
    confidence_score NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Integration

### Instagram Scraper Stable API (RapidAPI)

**Host:** `instagram-scraper-stable-api.p.rapidapi.com`
**Content-Type:** `application/x-www-form-urlencoded`

#### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ig_get_fb_profile.php` | POST | Get user bio links |
| `/get_ig_user_stories.php` | POST | Get user stories |
| `/get_ig_user_reels.php` | POST | Get user reels with metrics |
| `/get_ig_user_posts.php` | POST | Get user posts |
| `/get_ig_account_data.php` | POST | Get account data |
| `/get_ig_user_about.php` | GET | Get user about info |
| `/get_ig_detailed_reel.php` | GET | Get detailed reel with play_count |
| `/get_ig_post_comments.php` | GET | Get post comments |

---

## Implementation Phases

### Phase 1: Infrastructure Setup (Day 1)
- [ ] Create folder structure at `/Users/isaiahdupree/Documents/CompetitorResearch/`
- [ ] Create database migration for new tables
- [ ] Update Instagram adapter with correct PHP endpoints
- [ ] Create `CompetitorService` class
- [ ] Add API endpoint to add/manage tracked accounts

### Phase 2: Content Fetching (Day 2)
- [ ] Implement account profile fetching
- [ ] Implement reels fetching with pagination
- [ ] Implement posts fetching with pagination
- [ ] Download and store media files locally
- [ ] Store metrics in database
- [ ] Create background job for periodic sync

### Phase 3: Analysis Engine (Day 3)
- [ ] Integrate with AI analysis (OpenAI)
- [ ] Detect hooks and patterns in captions
- [ ] Analyze visual styles and formats
- [ ] Calculate engagement rates and viral scores
- [ ] Generate content pattern reports

### Phase 4: Documentation & Learnings (Day 4)
- [ ] Generate markdown docs per account
- [ ] Cross-account pattern analysis
- [ ] Create "Top Hooks" compilation
- [ ] Create "Content Formulas" guide
- [ ] Dashboard UI for viewing insights

### Phase 5: Integration (Day 5)
- [ ] Link learnings to content creation workflow
- [ ] Suggest hooks based on competitor analysis
- [ ] Recommend posting times
- [ ] AI-powered content ideation from learnings

---

## Backend Services

### CompetitorService

```python
class CompetitorService:
    """Service for competitor research and analysis."""
    
    async def add_account(self, username: str, priority: int = 1)
    async def sync_account(self, username: str)
    async def fetch_reels(self, username: str, count: int = 50)
    async def fetch_posts(self, username: str, count: int = 50)
    async def download_media(self, content_id: str)
    async def analyze_content(self, content_id: str)
    async def generate_learnings(self, account_id: str)
    async def get_top_performing_content(self, username: str, limit: int = 10)
```

### API Endpoints

```
POST   /api/competitors/accounts          # Add tracked account
GET    /api/competitors/accounts          # List tracked accounts
POST   /api/competitors/accounts/{id}/sync  # Sync account content
GET    /api/competitors/accounts/{id}/content  # Get account content
GET    /api/competitors/accounts/{id}/analysis  # Get analysis
GET    /api/competitors/learnings         # Get cross-account learnings
```

---

## Frontend Pages

### Competitor Research Dashboard (`/competitors`)
- List of tracked accounts with sync status
- Add new account form
- Quick stats per account

### Account Detail Page (`/competitors/{username}`)
- Account profile and metrics
- Content grid with performance metrics
- Top performing content
- Generated learnings and patterns

### Learnings Library (`/competitors/learnings`)
- Cross-account insights
- Top hooks compilation
- Content formulas
- Exportable documentation

---

## Success Metrics

1. **Coverage** - Number of competitor accounts tracked
2. **Content Volume** - Total content pieces analyzed
3. **Insight Quality** - Actionable learnings generated
4. **Application Rate** - Learnings applied to our content
5. **Performance Lift** - Improvement in our content metrics

---

## Rate Limits & Considerations

- Instagram Scraper Stable API (PRO plan): Check rate limits
- Implement request throttling
- Cache API responses
- Batch operations where possible
- Store media locally to avoid re-fetching

---

## Security & Privacy

- Store API keys securely in environment variables
- Downloaded content is for research purposes only
- Don't republish competitor content
- Respect Instagram's terms of service
- Focus on public account data only

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1 | 1 day | Infrastructure, database, folder structure |
| Phase 2 | 1 day | Content fetching, media download |
| Phase 3 | 1 day | AI analysis, pattern detection |
| Phase 4 | 1 day | Documentation, learnings generation |
| Phase 5 | 1 day | Integration, dashboard UI |

**Total: 5 days to full implementation**

---

## Appendix: Initial Target Account

### @personalbrandlaunch
- **URL**: https://www.instagram.com/personalbrandlaunch/
- **Focus**: Personal branding, viral content strategies
- **Why**: Proven viral content creator with analyzable patterns
- **Priority**: 1 (High)
