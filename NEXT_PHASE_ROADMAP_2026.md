# MediaPoster Next Phase Roadmap
**Planning Date:** February 2, 2026
**Last ARCH Completion:** January 26, 2026

---

## Roadmap Overview

After completing System Architecture Integration (ARCH-001 to ARCH-008), MediaPoster is positioned for 6 next major features covering the next 12-16 weeks.

### Timeline

```
Feb 2 ──── Feb 23  |  Feb 23 ──── Apr 6  |  Apr 6 ──── Apr 27  |  Apr 27 ──── May 25
 INBOX (3w)  | REPURPOSING (4-6w) | DESIGN SYSTEM (2-3w) | E2E TESTS (2w)
    ↓             ↓                   ↓                    ↓
Community    Content Repurposing   Design System       E2E Testing
Inbox        Engine                Components          Framework
Features: 5  Features: 8           Features: 16        Features: 5
```

---

## 🎯 PRIORITY 1: Community Inbox (3 weeks)

**Effort:** 3 weeks | **Complexity:** Medium | **Business Value:** High
**Status:** ⏳ Not Started
**Blocked By:** ✅ ARCH-001 to ARCH-008 (complete)

### Overview

Unified inbox for comments, DMs, and mentions across all platforms with AI-powered reply suggestions.

**Competitors:** HubSpot, Later, Buffer

### Features (5 items)

| Feature | Description | Effort | Priority |
|---------|-------------|--------|----------|
| **INBOX-001** | Unified Comments/DMs Fetcher | 2 days | P0 |
| **INBOX-002** | Conversation Threading | 1.5 days | P0 |
| **INBOX-003** | AI Reply Suggestions | 2 days | P0 |
| **INBOX-004** | Priority Filtering & Classification | 1.5 days | P1 |
| **INBOX-005** | Bulk Actions & Templating | 1 day | P1 |

### Technical Details

#### INBOX-001: Unified Comments/DMs Fetcher
- **Goal:** Aggregate comments and DMs from all platforms
- **Implementation:**
  - Fetch from: Twitter/X, Instagram, TikTok, YouTube, LinkedIn, Threads
  - De-duplicate across platforms
  - Store in `community_inbox_messages` table
  - Real-time sync (polling + webhooks)
- **Database Schema:**
  ```sql
  CREATE TABLE community_inbox_messages (
    id UUID PRIMARY KEY,
    platform TEXT,
    message_id TEXT UNIQUE,
    content TEXT,
    author_id TEXT,
    author_name TEXT,
    author_profile_url TEXT,
    parent_id TEXT,  -- For threading
    created_at TIMESTAMP,
    fetched_at TIMESTAMP,
    status TEXT  -- unread, replied, archived
  );
  ```

#### INBOX-002: Conversation Threading
- **Goal:** Group related messages into conversations
- **Implementation:**
  - Detect reply chains
  - Group by author + topic
  - Show conversation context
  - Timeline view
- **Key Methods:**
  - `get_conversation(message_id)` → List[Message]
  - `start_conversation(platform, author_id)` → Conversation
  - `reply_to_message(message_id, reply_text)` → Message

#### INBOX-003: AI Reply Suggestions
- **Goal:** Suggest smart replies using OpenAI
- **Implementation:**
  - Analyze message intent (question, compliment, complaint, etc.)
  - Generate 3 response options
  - User selects/edits before sending
  - Log for training
- **Triggers:**
  - User opens message
  - Batch generation (daily)
- **Prompting:**
  ```
  You are a social media assistant. Suggest 3 brief, authentic replies to:
  Message: "{message_content}"
  Context: Author is "{author_profile}", this is a {intent} comment
  Brand voice: professional, helpful, engaging

  Format:
  1. [Option 1]
  2. [Option 2]
  3. [Option 3]
  ```

#### INBOX-004: Priority Filtering
- **Goal:** Surface important messages first
- **Classification:**
  - **Hot:** Questions about offers, objections, leads
  - **Warm:** Compliments, engagement, curiosity
  - **Cold:** Spam, off-topic, automated
  - **Action Required:** Unanswered, platform-flagged, waiting for reply
- **Scoring:**
  - Author influence (followers) +1 to +5
  - Message type (question > compliment > comment) +1 to +3
  - Mention of product/offer +2
  - Negative sentiment +3
  - Platform signal (reply rate, etc.) +1

#### INBOX-005: Bulk Actions
- **Goal:** Manage many messages efficiently
- **Features:**
  - Archive messages (keep unread count accurate)
  - Bulk reply (same message to multiple)
  - Mass-mark as read
  - Snooze (remind later)
  - Template responses (brand standards)

### API Endpoints

```
GET    /api/inbox/messages             - List all messages (paginated, filtered)
GET    /api/inbox/messages/:id         - Get single message + thread
GET    /api/inbox/conversations/:id    - Get full conversation
POST   /api/inbox/messages/:id/reply   - Send reply
POST   /api/inbox/suggestions/:id      - Get AI suggestions
GET    /api/inbox/stats                - Unread count, platform breakdown
PUT    /api/inbox/messages/:id/status  - Mark read, archive, snooze
POST   /api/inbox/templates            - Save reply template
GET    /api/inbox/templates            - List templates
POST   /api/inbox/bulk-actions         - Archive, mark read, etc.
```

### Database Tables

```sql
CREATE TABLE community_inbox_messages (
  id UUID PRIMARY KEY,
  platform TEXT,  -- twitter, instagram, tiktok, youtube, linkedin, threads
  message_id TEXT UNIQUE,
  content TEXT,
  author_id TEXT,
  author_name TEXT,
  author_followers INT,
  author_profile_url TEXT,
  parent_id UUID,  -- For threading
  created_at TIMESTAMP,
  fetched_at TIMESTAMP,
  status TEXT,  -- unread, read, replied, archived
  priority TEXT,  -- hot, warm, cold, action_required
  priority_score INT,
  intent TEXT,  -- question, compliment, complaint, spam, etc.
  is_mentioned BOOLEAN
);

CREATE TABLE community_inbox_replies (
  id UUID PRIMARY KEY,
  message_id UUID REFERENCES community_inbox_messages,
  reply_text TEXT,
  created_at TIMESTAMP,
  platform_url TEXT,  -- Link to posted reply
  platform_status TEXT  -- posted, draft, failed
);

CREATE TABLE reply_templates (
  id UUID PRIMARY KEY,
  name TEXT,
  content TEXT,
  category TEXT,  -- greeting, question_answer, objection, thank_you
  created_at TIMESTAMP
);
```

### Test Cases

- [ ] Fetch messages from all 6 platforms
- [ ] Thread detection (same author, replies)
- [ ] AI suggestion generation
- [ ] Priority filtering accuracy
- [ ] Bulk action execution
- [ ] Real-time updates

### Success Metrics

- Inbox fully populated (0-lag sync)
- 95%+ thread accuracy
- AI suggestions helpful (user clicks > 60%)
- 10+ built-in templates

---

## 🎯 PRIORITY 2: Content Repurposing Engine (4-6 weeks)

**Effort:** 4-6 weeks | **Complexity:** High | **Business Value:** Very High
**Status:** ⏳ Not Started
**Blocked By:** ✅ ARCH-001 to ARCH-008 (complete)

### Overview

Automatically convert long-form videos into 15-60 second shorts optimized for TikTok, Instagram Reels, YouTube Shorts.

**Competitors:** Opus Clip, Descript, Runway

### Features (8 items)

| Feature | Description | Effort | Priority |
|---------|-------------|--------|----------|
| **REUSE-001** | Video Scene Detection | 2 days | P0 |
| **REUSE-002** | Hook/Retention Segment Extraction | 2 days | P0 |
| **REUSE-003** | Automatic Clip Generation | 2 days | P0 |
| **REUSE-004** | Caption & Text Overlay Generation | 2 days | P0 |
| **REUSE-005** | Platform-Specific Optimization | 2 days | P1 |
| **REUSE-006** | Music Synchronization | 1.5 days | P1 |
| **REUSE-007** | Quality Grading & Selection | 1.5 days | P1 |
| **REUSE-008** | Batch Publishing to Platforms | 1 day | P1 |

### Technical Details

#### REUSE-001: Video Scene Detection
- **Goal:** Identify scene changes, cuts, transitions
- **Implementation:**
  - Use OpenCV for frame-by-frame analysis
  - Detect shot boundaries (color histogram changes)
  - Identify people/faces for B-roll clips
  - Track motion intensity
- **Output:** List of scene segments with timestamps

#### REUSE-002: Hook/Retention Extraction
- **Goal:** Find the most engaging moments
- **Implementation:**
  - Audio: Transcribe with Whisper → identify questions, surprising statements
  - Visual: Detect quick cuts, B-roll, graphics (high engagement signals)
  - Combine: Score segments by (words + visual intensity + audio spike)
  - Select: Top 10% of segments (likely hooks)
- **Scoring Formula:**
  ```
  hook_score =
    (transcript_sentiment_surprise × 0.3) +
    (visual_cut_frequency × 0.3) +
    (audio_volume_spike × 0.2) +
    (motion_intensity × 0.2)
  ```

#### REUSE-003: Automatic Clip Generation
- **Goal:** Create 15, 30, 60-second shorts from long video
- **Implementation:**
  - Start with hook (0-5s)
  - Add 1-2 supporting segments
  - End with CTA or call-to-action
  - Auto-trim silence, pauses
  - Extract audio, video, sync
- **Formats:**
  - 15s TikTok
  - 30s Instagram Reel
  - 60s YouTube Short
- **Database:**
  ```sql
  CREATE TABLE clip_candidates (
    id UUID PRIMARY KEY,
    source_video_id UUID,
    start_time FLOAT,
    end_time FLOAT,
    duration_seconds INT,
    hook_score FLOAT,
    retention_score FLOAT,
    format TEXT,  -- 15s, 30s, 60s
    status TEXT,  -- extracted, graded, published
    output_path TEXT
  );
  ```

#### REUSE-004: Caption & Text Overlay
- **Goal:** Add captions and text overlays
- **Implementation:**
  - Transcribe video with Whisper
  - Split into 2-5 word chunks
  - Time-sync captions to video
  - AI-generate on-screen text highlights (key phrases)
  - Suggest emoji overlays
  - Apply brand fonts/colors
- **Tools:** Remotion for text rendering

#### REUSE-005: Platform-Specific Optimization
- **Goal:** Adapt clips for each platform's requirements
- **TikTok:**
  - Aspect ratio: 9:16
  - Hook in first 2 seconds
  - Fast cuts, trending sounds
  - Hashtag/sound recommendations
- **Instagram Reels:**
  - Aspect ratio: 9:16 or 1:1
  - Caption text overlay (stickers)
  - Music via Instagram library
  - 15-90 seconds
- **YouTube Shorts:**
  - Aspect ratio: 9:16
  - Auto-generated captions
  - Vertical orientation
  - 15-60 seconds
  - Channel branding

#### REUSE-006: Music Synchronization
- **Goal:** Match music to clip mood/tempo
- **Implementation:**
  - Detect video mood (Whisper sentiment)
  - Recommend trending sounds per platform
  - Sync beat-cuts to music BPM
  - Use existing brand music library
  - License checking
- **Sources:** Epidemic Sound, AudioJungle, platform native sounds

#### REUSE-007: Quality Grading
- **Goal:** Score clips for publishability
- **Metrics:**
  - Hook strength (1-10)
  - Visual quality (resolution, lighting, focus)
  - Audio clarity (no background noise)
  - Caption accuracy
  - CTA clarity
- **Auto-publish if:** score > 8 AND hook_strength > 7

#### REUSE-008: Batch Publishing
- **Goal:** Multi-platform posting
- **Implementation:**
  - Use existing Blotato service (ARCH-003)
  - Generate platform-specific metadata (titles, hashtags, captions)
  - Schedule posts (stagger 2-4 hours apart)
  - Track performance
- **Output:** Published URLs per platform

### API Endpoints

```
POST   /api/repurpose/process-video          - Queue long-form video for processing
GET    /api/repurpose/job/:id                - Status of repurposing job
GET    /api/repurpose/video/:id/clips        - List extracted clips
POST   /api/repurpose/clip/:id/publish       - Publish clip to platforms
GET    /api/repurpose/clip/:id/preview       - Preview clip + captions
PUT    /api/repurpose/clip/:id/metadata      - Edit title, description, captions
GET    /api/repurpose/stats                  - Platform performance of repurposed clips
```

### Workflow

```
Long-Form Video (uploaded)
    ↓
[Scene Detection] → Identify cuts, transitions
    ↓
[Hook/Retention Analysis] → Score segments
    ↓
[Clip Extraction] → 15s, 30s, 60s formats
    ↓
[Transcription & Captions] → Whisper → Sync timing
    ↓
[Platform Optimization] → Aspect ratio, metadata, sounds
    ↓
[Quality Grading] → Hook strength, clarity, CTA
    ↓
[Publish] → TikTok, Instagram, YouTube, Twitter (if vertical)
    ↓
[Track Performance] → Engagement, reach, audience growth
```

### Success Metrics

- Extract 5-10 publishable clips per 30-minute video
- Hook detection accuracy > 80%
- Average clip quality score > 7/10
- 50%+ of clips auto-publishable (score > 8)
- Platform engagement up 2-3x vs single-format posts

---

## 🎯 PRIORITY 3: Design System & Frontend Consistency (2-3 weeks)

**Effort:** 2-3 weeks | **Complexity:** Medium | **Business Value:** Medium
**Status:** ⏳ Not Started (16 P0 components failing)
**Blocked By:** None

### Overview

Complete React component library with consistent styling, spacing, colors for all dashboard UIs.

### Components (16 items)

| Component | Variations | Tests | Priority |
|-----------|-----------|-------|----------|
| **DS-001** | Button | primary, secondary, danger, disabled | P0 |
| **DS-002** | Card | elevated, flat, outlined | P0 |
| **DS-003** | StatusBadge | success, warning, error, info | P0 |
| **DS-004** | LoadingState | spinner, skeleton, progress | P0 |
| **DS-005** | EmptyState | message + illustration | P0 |
| **DS-006** | ErrorState | error message + action | P0 |
| **DS-007** | PageHeader | title, breadcrumbs, actions | P0 |
| **DS-008** | PageContainer | layout wrapper with sidebar | P1 |
| **DS-009** | Platform Constants | Brand colors, spacing, shadows | P0 |
| **DS-010** | Color Tokens | Palette with semantic meanings | P0 |
| **DS-011** | Typography Scale | Font sizes, weights, line heights | P1 |
| **DS-012** | DataTable | Sorting, filtering, pagination | P1 |
| **DS-013** | Modal | With overlay, dismiss actions | P1 |
| **DS-014** | Dropdown | Select, multiselect, searchable | P1 |
| **DS-015** | Tabs | Tabbed content panels | P1 |
| **DS-016** | Input | Text, email, number, password | P1 |
| **DS-017** | Select | Dropdown select, multiselect | P1 |

### File Structure

```
dashboard/
└── components/
    ├── ds/                          # Design System
    │   ├── Button.tsx
    │   ├── Card.tsx
    │   ├── StatusBadge.tsx
    │   ├── LoadingState.tsx
    │   ├── EmptyState.tsx
    │   ├── ErrorState.tsx
    │   ├── PageHeader.tsx
    │   ├── PageContainer.tsx
    │   ├── DataTable.tsx
    │   ├── Modal.tsx
    │   ├── Dropdown.tsx
    │   ├── Tabs.tsx
    │   ├── Input.tsx
    │   ├── Select.tsx
    │   └── __tests__/               # Component tests (Vitest)
    │
    └── tokens/                      # Design tokens
        ├── colors.ts
        ├── spacing.ts
        ├── typography.ts
        ├── shadows.ts
        └── constants.ts
```

### Key Token System

```typescript
// colors.ts
export const colors = {
  primary: '#0066FF',
  success: '#00AA44',
  warning: '#FFAA00',
  error: '#FF3333',

  neutral: {
    0: '#FFFFFF',
    50: '#F8F9FA',
    100: '#F0F2F5',
    200: '#E4E8ED',
    300: '#D0D8E0',
    400: '#B8C3D0',
    500: '#9CA8B8',
    600: '#7B8FA0',
    700: '#596475',
    800: '#3A4555',
    900: '#1A2535',
  }
};

// spacing.ts
export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
  xxl: '32px',
};

// typography.ts
export const typography = {
  h1: { size: '32px', weight: 700, lineHeight: '40px' },
  h2: { size: '24px', weight: 600, lineHeight: '32px' },
  body: { size: '14px', weight: 400, lineHeight: '20px' },
  small: { size: '12px', weight: 400, lineHeight: '16px' },
};
```

### Component Example: Button

```typescript
// Button.tsx
import { ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  children: ReactNode;
  fullWidth?: boolean;
}

export const Button = ({
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  children,
  fullWidth = false,
}: ButtonProps) => {
  const baseStyles = 'font-semibold rounded transition';

  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]}
                   ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                   ${fullWidth ? 'w-full' : ''}`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading ? '...' : children}
    </button>
  );
};
```

### Success Criteria

- All 16 components built and tested
- TypeScript strict mode enabled
- 100% test coverage per component
- Storybook documentation
- Usage in all existing dashboard pages

---

## 🎯 PRIORITY 4: E2E Testing Framework (2 weeks)

**Effort:** 2 weeks | **Complexity:** Medium | **Business Value:** High
**Status:** ⏳ Not Started (E2E-005 failing)

### Overview

Playwright E2E tests covering critical user journeys with structured logging for debugging.

### Test Scenarios (5+ items)

| Scenario | Steps | Coverage | Priority |
|----------|-------|----------|----------|
| **E2E-001** | Login & Dashboard | User auth, landing, navigation | P0 |
| **E2E-002** | Create & Schedule Post | Post creation, platform selection, scheduling | P0 |
| **E2E-003** | Publishing E2E | Full ARCH workflow (orchestrator) | P0 |
| **E2E-004** | Engagement Loop | Comment fetch → reply suggestion → publish | P1 |
| **E2E-005** | Content Repurposing | Upload long-form → extract clips → publish | P1 |

### Setup

```bash
# Install Playwright
npm install -D @playwright/test

# Create test directory
mkdir tests/e2e

# Initialize playwright.config.ts
npx playwright init
```

### Example Test: Login

```typescript
// tests/e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should login successfully', async ({ page }) => {
    // Navigate to login
    await page.goto('http://localhost:5557');

    // Fill credentials
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');

    // Submit
    await page.click('button[type="submit"]');

    // Verify redirect to dashboard
    await page.waitForURL('**/dashboard');
    expect(page.url()).toContain('/dashboard');
  });

  test('should handle invalid credentials', async ({ page }) => {
    await page.goto('http://localhost:5557');

    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Expect error message
    const error = page.locator('[role="alert"]');
    await expect(error).toContainText('Invalid credentials');
  });
});
```

### Success Metrics

- 15+ critical user journeys covered
- All tests passing on every commit
- Average test run time < 5 minutes
- Clear failure messages for debugging

---

## 🎯 PRIORITY 5: Modal Voice Cloning (1-2 weeks)

**Effort:** 1-2 weeks | **Complexity:** Medium | **Business Value:** Medium
**Status:** ⏳ Not Started

### Overview

AI voice cloning for personalized video voiceovers via Modal GPU.

### Features (3 items)

| Feature | Description | Effort |
|---------|-------------|--------|
| **VOICE-001** | Voice Recording & Training | 3 days |
| **VOICE-002** | Voice Cloning via Modal API | 3 days |
| **VOICE-003** | TTS Integration | 2 days |

---

## 🎯 PRIORITY 6: Media Asset Discovery (2-3 weeks)

**Effort:** 2-3 weeks | **Complexity:** Medium | **Business Value:** High
**Status:** ⏳ Not Started

### Overview

Unified search for images, videos, GIFs across Giphy, Pexels, Unsplash.

### Features (4 items)

| Feature | Description |
|---------|-------------|
| **ASSET-001** | Giphy GIF Search Integration |
| **ASSET-002** | Pexels Video Integration |
| **ASSET-003** | Unsplash Image Integration |
| **ASSET-004** | Unified Asset Search UI |

---

## Implementation Order

### Week 1-3: Community Inbox
**Feb 2 → Feb 23**

1. Create database schema (orchestrator_inbox_messages)
2. Build unified message fetcher (all 6 platforms)
3. Implement conversation threading
4. Add AI reply suggestions
5. Build UI and integrate with dashboard
6. Test and deploy

### Week 4-9: Content Repurposing Engine
**Feb 23 → Apr 6**

1. Video scene detection (OpenCV)
2. Hook/retention analysis
3. Clip extraction and formatting
4. Caption generation (Whisper)
5. Platform-specific optimization
6. Music sync and quality grading
7. Batch publishing
8. Test and deploy

### Week 10-12: Design System
**Apr 6 → Apr 27**

1. Define color palette and tokens
2. Build Button, Card, StatusBadge
3. Build inputs and selects
4. Build DataTable, Modal, Tabs
5. Complete Storybook documentation
6. Update all dashboard pages to use components
7. Test and deploy

### Week 13-14: E2E Testing
**Apr 27 → May 11**

1. Setup Playwright
2. Write login tests
3. Write post creation tests
4. Write ARCH orchestrator tests
5. Write engagement loop tests
6. Setup CI/CD integration
7. Test and deploy

### Week 15-16: Voice Cloning & Asset Discovery
**May 11 → May 25**

1. Modal API integration
2. Voice training pipeline
3. Media asset search UI
4. Batch processing
5. Test and deploy

---

## Success Metrics

### Overall Goals
- 100% test coverage for all new features
- 0 critical bugs before production
- Performance: <2s API response time
- Uptime: 99.9%

### Per-Feature Goals

**Community Inbox:**
- Inbox fully synced (0-lag)
- AI suggestions helpful (>60% click rate)
- 10+ built-in templates

**Content Repurposing:**
- 5-10 clips per 30-min video
- 80%+ hook accuracy
- 50%+ auto-publishable

**Design System:**
- 16/16 components complete
- 100% test coverage
- Used in 100% of dashboard pages

**E2E Testing:**
- 15+ critical journeys
- 100% passing on main branch
- <5 min test suite

---

## Resource Allocation

| Phase | Developer Time | Priority | Status |
|-------|---|----------|--------|
| Community Inbox | 3 weeks | 🔴 High | Ready to start |
| Content Repurposing | 4-6 weeks | 🔴 High | Depends on Inbox |
| Design System | 2-3 weeks | 🟡 Medium | Can start parallel |
| E2E Testing | 2 weeks | 🟡 Medium | Can start after Repurposing |
| Voice Cloning | 1-2 weeks | 🟢 Low | Start Week 10+ |
| Asset Discovery | 2-3 weeks | 🟢 Low | Start Week 10+ |

---

## Questions & Decisions

### Q1: Community Inbox vs Dashboard Refresh first?
**Decision:** Community Inbox first (business value: 3 weeks vs 2-3 weeks effort)

### Q2: Build Media Asset Discovery now or later?
**Decision:** Later (Week 15+) - lower priority than Repurposing

### Q3: E2E tests on every commit or nightly?
**Decision:** Every commit to main (catch bugs early), nightly full suite on staging

---

## References

### PRDs
- `docs/PRD_COMMUNITY_INBOX.md` - Community Inbox spec
- `docs/PRD_COMMUNITY_INBOX_DETAILED.md` - Detailed version
- `docs/PRD_CONTENT_REPURPOSING_ENGINE.md` - Repurposing spec
- `docs/PRD_CONTENT_REPURPOSING_DETAILED.md` - Detailed version
- `docs/PRD_E2E_TESTING_DEBUG_FRAMEWORK.md` - Testing spec
- `docs/PRD_MODAL_VOICE_CLONING.md` - Voice cloning spec
- `docs/PRD_MEDIA_ASSET_DISCOVERY.md` - Asset discovery spec

### ARCH Foundation
- `Backend/docs/PRD_SYSTEM_ARCHITECTURE_INTEGRATION.md`
- `ARCH_COMPLETION_REPORT.md`

### Completed Features
- `feature_list.json` - 502/538 features (93.3%)

---

**Roadmap Version:** 1.0
**Last Updated:** February 2, 2026
**Next Review:** March 2, 2026
