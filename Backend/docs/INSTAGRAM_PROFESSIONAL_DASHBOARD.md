# Instagram Professional Dashboard Reference

## Overview

Instagram's Professional Dashboard provides analytics for business and creator accounts, accessible via the mobile app or web at instagram.com.

---

## Account Insights Section

### Views Card
| Metric | Description | Example |
|--------|-------------|---------|
| **Views** | Total content views | `1,885` |
| **Followers %** | Views from followers | `8.3%` |
| **Non-followers %** | Views from non-followers | `91.7%` |
| **Accounts reached** | Unique accounts | `283` |

### By Content Type (Views)
| Content Type | Bar | Percentage |
|--------------|-----|------------|
| Posts | ████████████ | 61.3% |
| Reels | ███████ | 34.5% |
| Stories | █ | 4.2% |

### Top Content Based on Views
- Thumbnail grid of top performing content
- View count overlay on each thumbnail
- Date posted (e.g., "Dec 13")
- "See all" link to full list

---

## Interactions Section

### Interactions Card
| Metric | Description | Example |
|--------|-------------|---------|
| **Interactions** | Total interactions | `35` |
| **Followers %** | From followers | `22.9%` |
| **Non-followers %** | From non-followers | `77.1%` |

### By Content Interactions
| Content Type | Bar | Percentage |
|--------------|-----|------------|
| Reels | ██████████ | 51.4% |
| Posts | ████████ | 42.9% |
| Stories | █ | 5.7% |

### Top Content Based on Interactions
- Thumbnail with interaction count
- "See all" link

---

## Profile Section

### Profile Activity
| Metric | Value |
|--------|-------|
| Profile visits | `637` |
| External link taps | `9` |
| **Total profile activity** | `646` |

---

## Followers Section

### Followers Overview
| Metric | Value |
|--------|-------|
| Total followers | `830` |

### Most Active Times
Hourly breakdown showing when followers are most active:

```
Hour    | Followers Online
--------|------------------
12a     | 119
3a      | 151
6a      | 189
9a      | 205 (peak morning)
12p     | 194
3p      | 165
6p      | 154
9p      | 127
```

Visual: Bar chart with hours on X-axis, follower count on Y-axis

---

## Manage Ads Section

### Ad Cards Display
Each ad shows:
| Field | Example |
|-------|---------|
| Status | `Paused`, `Completed` |
| Thumbnail | Post image |
| Views | `29.3K` |
| Profile visits | `1,798` |
| Spend | `$412.89` |
| Audience | `People you choose through targeting` |
| Date | `Jun 2, 2025` |

### Ad Actions
- **View Insights** - Detailed ad analytics
- **Delete** - Remove ad
- **Resume/Boost again** - Reactivate

### Create Your Next Ad
- Suggested content: "This reel is getting likes"
- "+ Create ad" button
- Available funds display: `$100.00`

---

## UI Design Patterns

### Color Scheme
- Background: White (#FFFFFF)
- Text: Black (#262626)
- Secondary text: Gray (#8E8E8E)
- Accent: Blue (#0095F6) for links/buttons
- Progress bars: Blue (#0095F6)

### Cards
- White background
- No border (or very subtle)
- Section headers in bold
- Generous padding

### Progress Bars
- Blue (#0095F6) fill
- Gray (#DBDBDB) background
- Height: 8px
- Border radius: 4px

### Thumbnails
- Square aspect ratio (1:1) for grid
- Border radius: 8px
- Overlay text in white with shadow

### Typography
- Section headers: 16px semibold
- Metrics: 24-32px bold
- Labels: 14px regular gray
- Font: -apple-system, system-ui

### Layout
- Single column main content
- Right sidebar for ads/suggestions
- Card-based sections
- Tabs: Insights | Ad tools

---

## Filter Options

### Date Range Selector
- Last 7 days
- Last 14 days
- Last 30 days (default)
- Last 90 days
- Custom range

### Audience Filter Tabs
- All
- Followers
- Non-followers

---

## API Data Mapping

### Profile Metrics → Instagram Dashboard
| API Field | Dashboard Display |
|-----------|-------------------|
| `edge_followed_by.count` | Total followers |
| `edge_owner_to_timeline_media.count` | Posts count |
| Profile visits (not in public API) | Profile visits |
| External link taps (not in public API) | External link taps |

### Post Metrics → Content Cards
| API Field | Dashboard Display |
|-----------|-------------------|
| `edge_liked_by.count` | Likes |
| `edge_media_to_comment.count` | Comments |
| `video_view_count` | Views (for videos/reels) |
| `shortcode` | Post identifier |
| `thumbnail_src` | Thumbnail image |
| `taken_at_timestamp` | Date posted |

### Calculated Metrics
```python
# Engagement rate
engagement_rate = (likes + comments) / followers * 100

# Reach rate (if available)
reach_rate = accounts_reached / followers * 100

# Non-follower reach
non_follower_pct = (views - follower_views) / views * 100
```

---

## Insights Not Available via Public API

These metrics require Instagram Business API with proper permissions:

| Metric | Requires |
|--------|----------|
| Accounts reached | Instagram Graph API |
| Profile visits | Instagram Graph API |
| External link taps | Instagram Graph API |
| Follower demographics | Instagram Graph API |
| Most active times | Instagram Graph API |
| Story insights | Instagram Graph API |
| Reel insights | Instagram Graph API |

### Available via RapidAPI Scrapers
| Metric | Available |
|--------|-----------|
| Follower count | ✅ |
| Following count | ✅ |
| Post count | ✅ |
| Post likes | ✅ |
| Post comments | ✅ |
| Video views | ✅ |
| Engagement rate (calculated) | ✅ |

---

## Content Type Breakdown

### Posts (Feed Posts)
- Static images
- Carousels
- Regular video posts

### Reels
- Short-form video (up to 90 seconds)
- Full-screen vertical format
- Higher reach potential

### Stories
- 24-hour ephemeral content
- Can be saved to Highlights
- Interactive elements (polls, questions)

---

## Recommended MediaPoster Implementation

### Dashboard Cards to Replicate
1. **Views Card** - Total views with follower/non-follower split
2. **By Content Type** - Horizontal progress bars
3. **Top Content Grid** - Thumbnail grid with view counts
4. **Interactions Card** - Total with breakdown
5. **Profile Activity** - Visits and link taps
6. **Followers** - Total with growth indicator

### Data Sources
- Use `instagram-looter2` API for profile stats
- Use `instagram-statistics-api` for engagement metrics
- Calculate follower/non-follower split (estimate based on typical ratios)

---

*Reference: Instagram Professional Dashboard (instagram.com) - December 2024*
