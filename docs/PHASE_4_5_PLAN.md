# Phase 4 & 5: Enhanced Publishing & Analytics UI

## Phase 4: Publishing & Scheduling (Upgraded)

### Goal
Transform the publishing system into a "creator cockpit" with smart calendar, AI-powered content optimization, and visual workflow management.

---

## Component 1: Smart Calendar View

### 4.1 Calendar Navigation & Views

**Three View Modes:**

#### Month View
- High-level overview grid
- Tiny clip thumbnails in each day
- Platform icons (TikTok, IG, YT badges)
- Post count indicators
- Color-coded performance halos (post-publish)

#### Week View
- Time-slot based (Morning/Afternoon/Evening)
- Larger post cards with more detail
- Hourly scheduling precision
- Platform-specific optimal times highlighted

#### List View
- Table format for bulk operations
- Sortable by date, platform, status, performance
- Quick filters (Draft, Scheduled, Published)
- Bulk selection checkboxes

### 4.2 Post Cards (Calendar Items)

**Card Display:**
- Clip thumbnail (60x60 or 80x80)
- Platform icon badges
- Status pill: `Draft` | `Scheduled` | `Published` | `Needs Fix`
- Scheduled time
- Quick actions menu (⋮)

**Performance Overlays (Post-Publish):**
- Color-coded halo:
  - 🟢 Green: Above average
  - 🟡 Yellow: Average
  - 🔴 Red: Underperforming
- Hover tooltip shows:
  - Views, Avg watch %, Saves/Shares
  - Top CTA response count
  - Link to full analytics

### 4.3 Drag & Drop Rescheduling

**Functionality:**
- Drag post card from one day to another
- Time picker modal on drop (if Week view)
- Auto-save with optimistic UI update
- Conflict detection (too many posts on one day)
- Platform-specific optimal time suggestions

**Implementation:**
```typescript
// React DnD or react-beautiful-dnd
onDrop(postId, newDate, newTime?) {
  // Update schedule
  // Check platform best times
  // Show confirmation
}
```

---

## Component 2: Publishing Dashboard

### 2.1 Account Connection Manager

**Features:**
- Connect/disconnect accounts per platform
- OAuth flow integration
- Status indicators:
  - ✅ `Connected` (green)
  - ⚠️ `Needs Reauth` (yellow)
  - ⛔ `Rate Limited` (red)
  - ❌ `Disconnected` (gray)
- Test post button (verify connection)
- Last successful post timestamp

### 2.2 Queue Overview

**Upcoming Posts Table:**
| Thumbnail | Platform | Title | Schedule | Status | Actions |
|-----------|----------|-------|----------|--------|---------|
| 🎬 | TT IG YT | "How to..." | Today 3PM | Scheduled | ⋮ |

**Bulk Actions:**
- Select multiple posts:
  - Reschedule (date picker modal)
  - Change caption template
  - Duplicate to another platform
  - Delete/Archive
  - Change status

### 2.3 Publishing Health Dashboard

**Metrics:**
- Posts this week: 12
- Success rate: 95%
- Avg engagement: +23%
- Account health scores

---

## Component 3: Post Editor with AI Assist

### 3.1 Editor Layout

**Left Panel: Preview**
- Video player with clip
- Platform-specific preview (TikTok frame, IG reel UI, etc.)
- Character count warnings

**Right Panel: Metadata**

#### Title / Hook Line
```
┌─────────────────────────────────┐
│ If you're a tired creator...    │
├─────────────────────────────────┤
│ [Generate]  [Punchier]  [Shorter]
│ [Educational] [Storytelling]     │
└─────────────────────────────────┘
```

**AI Buttons:**
- `Generate from clip` - Create from transcript
- `Punchier hook` - Make more engaging
- `Shorter` - Cut to essentials
- `More educational` - Add teaching angle
- `More storytelling` - Narrative style

#### Description / Caption
```
┌─────────────────────────────────┐
│ Here's the automation setup     │
│ that changed everything...      │
│                                  │
├─────────────────────────────────┤
│ [Generate] [Regenerate] [Expand] │
│ [Shorten] [Add CTA] [Platform]   │
└─────────────────────────────────┘
```

**AI Buttons:**
- `Generate caption` - Auto-create from video
- `Regenerate` - New variation
- `Expand` - Add more context
- `Shorten` - TikTok-style brevity
- `Add CTA` - Append call-to-action
- `Platform optimize` - TikTok vs IG vs YT style

#### Hashtags / Keywords
```
┌─────────────────────────────────┐
│ #automation #productivity       │
│ #tech #solopreneur              │
├─────────────────────────────────┤
│ [Suggest] [Regenerate]           │
│ [Optimize Reach] [Optimize Niche]│
└─────────────────────────────────┘
```

**AI Buttons:**
- `Suggest hashtags` - Based on transcript + platform
- `Regenerate hashtags` - New set
- `Optimize for reach` - Popular tags
- `Optimize for niche` - Targeted tags

### 3.2 Variant Management

**Save Multiple Versions:**
- Keep last 3-5 AI-generated variants
- Version selector: A | B | C | D
- "Use this" button per version
- Flag for A/B testing per platform
- Compare side-by-side

**Example:**
```
Version A (Selected for TikTok):
"Stop using Notion wrong"

Version B (Selected for IG):
"Your Notion setup is backwards - here's why"

Version C:
"The #1 Notion mistake creators make"
```

---

## Component 4: Content Calendar AI Helpers

### 4.1 Auto-Generate Posting Plan

**Workflow:**
1. Select multiple clips from library
2. Click `Auto-Schedule Week`
3. System proposes:
   - Best days/times per platform (from past performance)
   - Fills calendar with default captions & titles
   - Distributes content for variety
4. User reviews & edits
5. Bulk confirm

### 4.2 Per-Slot Suggestions

**Empty Day Click:**
- `Suggest clip for this slot`
- System picks based on:
  - Topic variety (avoid repetition)
  - Performance history
  - "Not posted yet" filter
  - Platform best practices

### 4.3 One-Click Metadata Refresh

**On Scheduled Post:**
- `Refresh metadata` button
- Reruns AI suggestions using:
  - Latest transcript analysis
  - Recent performance insights
  - Updated trending hashtags

---

## Phase 5: Analytics Dashboard (Complete)

### 5.1 Overview Dashboard

**Summary Cards:**
- Total Videos
- Total Clips Generated
- Total Posts Published
- Processing Queue
- Failed Jobs

**Charts & Graphs:**

#### Performance Over Time (Line Chart)
- X-axis: Date
- Y-axis: Views / Engagement
- Multiple lines: Per platform
- Filters: Last 7d, 30d, 90d, All time

#### Platform Distribution (Pie Chart)
- Posts per platform
- Color-coded by platform
- Click to filter

#### Top Performing Content (Bar Chart)
- Top 10 videos by views
- Click to see details

### 5.2 Post Performance Detailed View

**Individual Post Analytics:**

**Header:**
- Thumbnail + Title
- Platform + Post date
- Overall score: 🟢 Above avg | 🟡 Avg | 🔴 Below avg

**Metrics Grid:**
```
┌─────────────┬─────────────┬─────────────┐
│ 12.5K       │ 87%         │ 8.2%        │
│ Views       │ Avg Watch % │ Engagement  │
└─────────────┴─────────────┴─────────────┘
┌─────────────┬─────────────┬─────────────┐
│ 1,024       │ 342         │ 156         │
│ Likes       │ Comments    │ Shares      │
└─────────────┴─────────────┴─────────────┘
```

**Retention Curve:**
- Graph showing viewer drop-off
- Annotated with transcript moments
- Highlights: Hook, Peak, Drop points

**Comment Sentiment:**
- Overall sentiment: 😊 Positive (78%)
- Top themes: ["Need templates", "This is me fr"]
- Top questions extracted

**Performance Timeline:**
- 1h checkback: 500 views
- 6h checkback: 3.2K views
- 24h checkback: 8.1K views
- 7d checkback: 12.5K views

### 5.3 Insights & Recommendations Widget

**AI-Generated Insights:**

**Pattern Detection:**
- "Videos with hooks about 'automation' perform 34% better"
- "Your best posting time is Tuesday 2-4PM"
- "Shorter captions (< 100 chars) get 2x more shares"

**Recommendations:**
- 💡 "Try more question-style hooks"
- 💡 "Add CTAs to underperforming posts"
- 💡 "Post more on Instagram - your growth platform"

**Content Gaps:**
- "No posts about [topic] in 2 weeks"
- "Your audience wants more tutorials vs rants"

**Optimization Tips:**
- "Boost this video: [Title] - it's trending"
- "Repost this clip to YouTube - it fits their algorithm"

---

## Implementation Details

### Frontend Stack (Next.js)

**New Dependencies:**
```json
{
  "react-beautiful-dnd": "^13.1.1",  // Drag & drop
  "react-big-calendar": "^1.8.5",    // Calendar view
  "recharts": "^2.8.0",              // Charts
  "date-fns": "^2.30.0"              // Date utilities
}
```

**Component Tree:**
```
Phase 4:
src/components/publishing/
├── CalendarView/
│   ├── MonthView.tsx
│   ├── WeekView.tsx
│   ├── ListView.tsx
│   ├── PostCard.tsx
│   └── PerformanceOverlay.tsx
├── PublishingDashboard/
│   ├── AccountManager.tsx
│   ├── QueueTable.tsx
│   └── BulkActions.tsx
├── PostEditor/
│   ├── EditorLayout.tsx
│   ├── AITitleGenerator.tsx
│   ├── AICaptionGenerator.tsx
│   ├── AIHashtagGenerator.tsx
│   └── VariantManager.tsx
└── AIHelpers/
    ├── AutoScheduler.tsx
    ├── ClipSuggester.tsx
    └── MetadataRefresher.tsx

Phase 5:
src/components/analytics/
├── OverviewDashboard.tsx (already exists)
├── PostPerformanceView.tsx
├── InsightsWidget.tsx
├── PerformanceChart.tsx
└── RetentionCurve.tsx
```

### Backend API Endpoints

**Phase 4:**
```
POST   /api/publishing/schedule          # Create/update schedule
PUT    /api/publishing/posts/:id/reschedule
POST   /api/publishing/posts/:id/regenerate
  body: { type: 'title' | 'caption' | 'hashtags', style: '...' }
GET    /api/publishing/calendar/:year/:month
POST   /api/publishing/auto-schedule
  body: { clipIds: [...], platform: '...', startDate: '...' }
```

**Phase 5:**
```
GET    /api/analytics/overview
GET    /api/analytics/posts/:id/performance
GET    /api/analytics/posts/:id/retention
GET    /api/analytics/insights
```

---

## Next Steps

1. Complete Phase 5 analytics components
2. Build calendar view components
3. Implement AI generation backend
4. Create post editor UI
5. Add drag-drop functionality
6. Build insights engine
