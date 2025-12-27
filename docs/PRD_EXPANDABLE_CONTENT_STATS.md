# PRD: Expandable Content Cards with Inline Stats

**Date:** 2025-12-27  
**Status:** In Development  
**Priority:** High

---

## Overview

Enhance the Posted Content page to allow users to click on any content card and see an expanded inline view with stats, engagement graphs, and recent comments without leaving the page.

---

## User Story

> As a content creator, I want to quickly see performance stats for any posted content by clicking on it, so I can assess engagement without navigating away from my content overview.

---

## Current State

- Posted Content page shows a grid of content cards
- Each card shows thumbnail, title, date, and basic metrics (views, likes, comments)
- Clicking "View Post" opens the external platform URL
- No way to see detailed stats inline

---

## Proposed Solution

### Interaction Flow

1. **User clicks on a content card**
2. **Card expands** to take full width of the row
3. **Other cards in the same row shift** below the expanded card
4. **Expanded view shows:**
   - Larger thumbnail/video preview
   - Engagement line graph (views over time)
   - Recent comments (last 5)
   - Key metrics summary (views, likes, shares, comments)
   - Platform badges for all platforms this content was posted to
5. **"View Full Stats" button** navigates to `/media/[id]?tab=stats`
6. **Clicking elsewhere or X button** collapses the card

---

## UI Components

### 1. Collapsed Card (Current)
```
┌─────────────────────┐
│  [Thumbnail]        │
│  "3 posts" badge    │
│                     │
│  Title...           │
│  Platform • Date    │
│  👁 0  ♡ 0  💬 0   │
│  [Show 3 posts]     │
└─────────────────────┘
```

### 2. Expanded Card (New)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [X Close]                                                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐  Title of Content                                             │
│ │             │  Posted to: TikTok, Instagram, YouTube                        │
│ │  Thumbnail  │  ───────────────────────────────────────────                  │
│ │             │  📊 Engagement Over Time                                      │
│ │             │  [═══════════════ Line Graph ═══════════════]                 │
│ └─────────────┘  ───────────────────────────────────────────                  │
│                                                                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │
│  │ 👁 Views         │  │ ♡ Likes          │  │ 💬 Comments      │            │
│  │    12,456        │  │    1,234         │  │    89            │            │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘            │
│                                                                                │
│  💬 Recent Comments                                                           │
│  ├─ @user1: "Great content!" (2h ago)                                         │
│  ├─ @user2: "Love this!" (5h ago)                                             │
│  └─ @user3: "Amazing work" (1d ago)                                           │
│                                                                                │
│  [View Full Stats →]                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### Frontend Changes

**File:** `dashboard/app/(dashboard)/posted-content/page.tsx`

1. **Add state for expanded card:**
   ```typescript
   const [expandedCardId, setExpandedCardId] = useState<string | null>(null);
   ```

2. **Add stats data state:**
   ```typescript
   interface CardStats {
     views_over_time: { date: string; views: number }[];
     recent_comments: { user: string; text: string; timestamp: string }[];
     total_views: number;
     total_likes: number;
     total_comments: number;
     total_shares: number;
   }
   const [cardStats, setCardStats] = useState<Record<string, CardStats>>({});
   ```

3. **Fetch stats on expand:**
   ```typescript
   const handleCardClick = async (mediaId: string) => {
     if (expandedCardId === mediaId) {
       setExpandedCardId(null);
       return;
     }
     setExpandedCardId(mediaId);
     if (!cardStats[mediaId]) {
       const stats = await fetchCardStats(mediaId);
       setCardStats(prev => ({ ...prev, [mediaId]: stats }));
     }
   };
   ```

4. **Render expanded card:**
   - Use CSS grid with conditional full-width for expanded card
   - Animate expansion with CSS transitions
   - Show line chart using lightweight chart library (recharts)

### Backend API

**New Endpoint:** `GET /api/posted-content/stats/{media_id}`

Response:
```json
{
  "media_id": "uuid",
  "views_over_time": [
    { "date": "2025-12-20", "views": 100 },
    { "date": "2025-12-21", "views": 250 }
  ],
  "recent_comments": [
    { "user": "@username", "text": "Great!", "timestamp": "2025-12-27T10:00:00Z" }
  ],
  "totals": {
    "views": 12456,
    "likes": 1234,
    "comments": 89,
    "shares": 56
  },
  "platforms": ["tiktok", "instagram", "youtube"]
}
```

---

## Dependencies

- **recharts** - Already in project for charts
- No new dependencies required

---

## Success Metrics

- Users can view stats without page navigation
- Average time on Posted Content page increases
- Reduced clicks to view content performance

---

## Implementation Phases

### Phase 1: Basic Expansion (This PR)
- [x] Click to expand card
- [x] Show larger thumbnail
- [x] Show aggregated stats
- [x] View Full Stats link

### Phase 2: Charts & Comments (Next)
- [ ] Add engagement line graph
- [ ] Fetch and display recent comments
- [ ] Add platform breakdown

### Phase 3: Polish
- [ ] Smooth animations
- [ ] Keyboard navigation (Escape to close)
- [ ] Mobile responsive design

---

## Files to Modify

1. `dashboard/app/(dashboard)/posted-content/page.tsx` - Main implementation
2. `Backend/api/posted_content.py` - Add stats endpoint
3. `dashboard/package.json` - Verify recharts is installed

---

## Acceptance Criteria

- [ ] Clicking a content card expands it to full row width
- [ ] Other cards in the row shift below
- [ ] Expanded view shows key metrics (views, likes, comments, shares)
- [ ] Expanded view shows platforms where content was posted
- [ ] "View Full Stats" navigates to `/media/[id]?tab=stats`
- [ ] Clicking X or outside collapses the card
- [ ] No page refresh required
