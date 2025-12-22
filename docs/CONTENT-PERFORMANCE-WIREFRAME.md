# Content Performance Page Wireframe Spec
## "Clarity without losing detail"

---

# The 3 Questions (in order)

| Priority | Question | Current | Proposed Solution |
|----------|----------|---------|-------------------|
| 1 | What's happening overall? | ✓ KPI tiles exist | Add deltas + normalization |
| 2 | What's driving it? | ⚠️ Charts compete | Single hero chart + drivers panel |
| 3 | What should I do next? | ⚠️ Decision labels exist | Add auto-generated insights |

---

# Mode Toggle (Top-Right)

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Content Performance                    [Overview ▾]      │
│ Understand what's working and why          │ Overview       │
│                                             │ Diagnose       │
│                                             │ Compare        │
└─────────────────────────────────────────────────────────────┘
```

| Mode | Purpose | Components Shown |
|------|---------|------------------|
| **Overview** | Quick health check | KPI cards, Hero chart, Top 5, Insights |
| **Diagnose** | Deep analysis | + Cumulative, Scatter, Retention metrics |
| **Compare** | A/B analysis | Platform vs Platform, Period vs Period |

---

# Component Spec: Overview Mode

## 1. Filter Bar (Compact Single Row)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Last 30 days ▾]  [All Platforms ▾]  [All Traffic ▾]  │ Last updated 2m ago 🔄 │
└─────────────────────────────────────────────────────────────────────────┘
```

| Element | Current | Change |
|---------|---------|--------|
| Date range | Dropdown | Keep |
| Platform | Dropdown | Keep |
| Traffic type | Button group | Move to dropdown |
| Refresh | "Refresh Metrics" button | "Last updated Xm ago" + icon |
| Post count | Right side | Keep |

---

## 2. KPI Cards (Top Row)

### Card Layout
```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  Views        │  Engagement    │  Avg/Post     │  Posts        │  Shares/Saves      │
│  ▶️ 125.4K    │  💬 2.8%       │  📊 8.4K      │  📝 15        │  🔄 1.2K           │
│  +12% ↑       │  -0.3% ↓       │  +18% ↑       │  +3 ↑         │  +45% ↑            │
│  vs prev 30d  │  vs prev 30d   │  vs prev 30d  │  vs prev 30d  │  vs prev 30d       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Card Spec
| Field | Current | Change |
|-------|---------|--------|
| Icon | ✓ | Keep |
| Value | ✓ | Keep |
| Label | ✓ | Keep |
| Delta | ❌ Missing | **Add % change vs previous period** |
| Context | ❌ Missing | **Add "vs prev 30d" label** |

### Recommended Cards (5)
1. **Views** (total) + % change
2. **Engagement Rate** (weighted) + delta
3. **Avg per Post** (views/post) + delta
4. **Posting Volume** (posts) + delta
5. **Shares/Saves** (high-intent) + delta

### Delta Calculation
```typescript
const previousPeriod = getPreviousPeriodData(dateRange);
const delta = ((current - previous) / previous * 100).toFixed(1);
```

---

## 3. Hero Chart (Single Focus)

### Before
```
┌────────────────────────────┐ ┌────────────────────────────┐
│ 📈 Performance Over Time   │ │ 📱 Platform Breakdown      │
│ [Area chart: views+likes]  │ │ [Bar chart: views by plat] │
└────────────────────────────┘ └────────────────────────────┘
```

### After
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📈 Daily Performance                              [Views ▾] [Posts ▾]   │
│                                                                          │
│     ┌─ Views (line)                                                      │
│  ▲  │    ╱╲                                                              │
│  │  │   ╱  ╲    ╱╲                                                       │
│  │  │  ╱    ╲  ╱  ╲                                                      │
│  │  │ ╱      ╲╱    ╲                                                     │
│  │  └─────────────────────────────────────────────────────────────────   │
│     ├─┤├─┤├─┤├─┤├─┤├─┤├─┤  ← Posts (bars)                                │
│     Mon Tue Wed Thu Fri Sat Sun                                          │
│                                                                          │
│  [Views] [Likes] [Comments] [Engagement Rate]  ← Metric toggle tabs      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Chart Spec
| Element | Type | Purpose |
|---------|------|---------|
| Primary Line | Views (or selected metric) | Show performance trend |
| Secondary Bars | Posts per day | Explain volume vs quality |
| Metric Tabs | Toggle | Switch whole chart metric |
| Tooltip | Composite | Show all metrics for day |

### Metric Toggle Behavior
- Switching metric changes: line data, KPI highlight, table sort
- "Engagement Rate" = (likes + comments + shares) / views * 100

---

## 4. Drivers Panel (4 Cards Max)

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ 🎯 What's Driving Performance                                                          │
├─────────────────────┬─────────────────────┬─────────────────────┬─────────────────────┤
│ By Platform         │ By Time Window      │ Top 5 Posts         │ Content Type        │
│ ┌─────────────────┐ │ ┌─────────────────┐ │ ┌─────────────────┐ │ ┌─────────────────┐ │
│ │ TikTok   ████ 78%│ │ │ Morning   ██ 22%│ │ │ 1. Video #3     │ │ │ Video    ████ 92%│
│ │ Insta    ██ 18%  │ │ │ Afternoon █ 15% │ │ │ 2. Video #7     │ │ │ Photo    █ 8%    │
│ │ YouTube  █ 4%    │ │ │ Evening ███ 45% │ │ │ 3. Video #1     │ │ │                   │
│ │                   │ │ │ Night   ██ 18%  │ │ │ 4. Video #12    │ │ │                   │
│ └─────────────────┘ │ └─────────────────┘ │ │ 5. Video #5     │ │ └─────────────────┘ │
│                     │                     │ └─────────────────┘ │                     │
└─────────────────────┴─────────────────────┴─────────────────────┴─────────────────────┘
```

### Driver Card Spec
| Card | Data Source | Display |
|------|-------------|---------|
| **By Platform** | Group by platform | Horizontal bar + % |
| **By Time Window** | Group by posted hour | Morning/Afternoon/Evening/Night |
| **Top 5 Posts** | Sort by selected metric | Ranked list with sparkline |
| **Content Type** | video/photo/text | Bar chart |

### Time Window Definition
| Window | Hours |
|--------|-------|
| Morning | 5am - 12pm |
| Afternoon | 12pm - 5pm |
| Evening | 5pm - 9pm |
| Night | 9pm - 5am |

---

## 5. Insights Callouts (Auto-Generated)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 💡 Insights                                                              │
│                                                                          │
│  • TikTok drove 78% of views this week                                   │
│  • Posts after 6pm have +22% higher engagement rate                      │
│  • Top post contributed 54% of total views                               │
│  • Engagement rate is down 12% — consider more hooks in first 3 seconds  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Insight Generation Rules
```typescript
const insights = [];

// Platform concentration
const topPlatform = platformData.sort((a, b) => b.views - a.views)[0];
const topPlatformPercent = (topPlatform.views / aggregates.views * 100).toFixed(0);
if (topPlatformPercent > 50) {
  insights.push(`${topPlatform.platform} drove ${topPlatformPercent}% of views this period`);
}

// Top post concentration
const topPost = filteredPosts.sort((a, b) => b.views - a.views)[0];
const topPostPercent = (topPost.views / aggregates.views * 100).toFixed(0);
if (topPostPercent > 30) {
  insights.push(`Top post contributed ${topPostPercent}% of total views`);
}

// Best posting time
const bestTimeWindow = timeWindowData.sort((a, b) => b.engagement - a.engagement)[0];
insights.push(`Posts in ${bestTimeWindow.name} have highest engagement`);

// Delta warning
if (aggregates.engagementDelta < -10) {
  insights.push(`Engagement rate is down ${Math.abs(aggregates.engagementDelta)}% — consider stronger hooks`);
}
```

---

## 6. Top Posts Table (Decision Columns First)

### Before
Current table shows raw metrics without clear decision flow.

### After
```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🏆 Top Posts                                              Sort by: [Views ▾]  [Expand All]      │
├──────────────────────────┬──────────┬────────────┬────────┬─────────────┬───────────┬──────────┤
│ Post                     │ Platform │ Date/Time  │ Views  │ Eng. Rate   │ Shares    │ Decision │
├──────────────────────────┼──────────┼────────────┼────────┼─────────────┼───────────┼──────────┤
│ [Thumb] Video Title...   │ 🎵 TikTok│ Dec 15 6pm │ 45.2K  │ 4.2%        │ 892       │ ✅ Scale │
│ └─ Caption: "Check out..." │        │            │        │ ↑ 0.8%      │ ↑ 45%     │          │
│    Tags: #viral #fyp      │        │            │        │             │           │          │
├──────────────────────────┼──────────┼────────────┼────────┼─────────────┼───────────┼──────────┤
│ [Thumb] Another Post...  │ 📸 Insta │ Dec 14 2pm │ 12.1K  │ 2.1%        │ 124       │ ♻️ Iterate│
├──────────────────────────┼──────────┼────────────┼────────┼─────────────┼───────────┼──────────┤
│ [Thumb] Third Post...    │ 🎵 TikTok│ Dec 13 8pm │ 8.4K   │ 1.8%        │ 45        │ 🛑 Pause │
└──────────────────────────┴──────────┴────────────┴────────┴─────────────┴───────────┴──────────┘
```

### Column Spec
| Column | Purpose | Priority |
|--------|---------|----------|
| **Post** | Thumb + title | Decision |
| **Platform** | Icon + name | Decision |
| **Date/Time** | When posted | Decision |
| **Views** | Volume | Decision |
| **Eng. Rate** | Quality + delta | Decision |
| **Shares** | High-intent signal | Decision |
| **Decision** | Action label | Decision |

### Row Expand (on click)
| Field | Purpose |
|-------|---------|
| Caption | Full text |
| Hashtags | Tags used |
| Media ID | Internal reference |
| Link | Platform URL |
| All metrics | Likes, comments, saves, etc. |

---

# Component Spec: Diagnose Mode

Additional components shown in Diagnose mode:

## 1. Cumulative Growth Chart (Secondary)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📊 Cumulative Growth                                                     │
│                                                                          │
│  ▲                                            ╱                          │
│  │                                       ╱───╱                           │
│  │                                  ╱───╱                                │
│  │                             ╱───╱                                     │
│  │                        ╱───╱                                          │
│  │                   ╱───╱                                               │
│  │              ╱───╱                                                    │
│  └───────────────────────────────────────────────────────────────────    │
│     Week 1    Week 2    Week 3    Week 4                                 │
│                                                                          │
│  ━━ Total Views  ━━ Total Engagement                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Viral Engine Scatter Plot

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🎯 Viral Engine Analysis                                                 │
│ (Avg % Viewed vs Share Rate — top-right = viral potential)              │
│                                                                          │
│  Share Rate ▲                                                            │
│             │           ●  (Video #3)                                    │
│             │       ●                                                    │
│             │   ●       ●                                                │
│             │                                                            │
│             │ ●   ●                                                      │
│             │         ●                                                  │
│             └──────────────────────────────────────────────► Avg Viewed  │
│                                                                          │
│  Quadrant Guide:                                                         │
│  Top-Right: Viral winners (scale these)                                  │
│  Top-Left: Hook problem (good shares, low completion)                    │
│  Bottom-Right: Retention hero (good watch, low shares)                   │
│  Bottom-Left: Needs work (pause or iterate)                              │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. Engagement per 1K Views (Normalized)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📊 Engagement per 1,000 Views (Normalized Comparison)                    │
│                                                                          │
│  Post #1  ████████████████████ 42 likes/1K                               │
│  Post #2  ████████████████ 34 likes/1K                                   │
│  Post #3  ██████████████ 28 likes/1K                                     │
│  Post #4  ████████████ 24 likes/1K                                       │
│  Post #5  ██████████ 20 likes/1K                                         │
│                                                                          │
│  [Likes/1K] [Comments/1K] [Shares/1K] [Saves/1K]                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# Component Spec: Compare Mode

## 1. Platform Comparison

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔄 Platform Comparison                                                   │
│                                                                          │
│  [TikTok ▾]  vs  [Instagram ▾]                                           │
│                                                                          │
│  ┌───────────────────────┬───────────────────────┐                       │
│  │ TikTok                │ Instagram             │                       │
│  ├───────────────────────┼───────────────────────┤                       │
│  │ Views: 98.2K          │ Views: 27.4K          │                       │
│  │ Eng Rate: 3.4%        │ Eng Rate: 4.1%        │                       │
│  │ Avg/Post: 12.3K       │ Avg/Post: 4.6K        │                       │
│  │ Posts: 8              │ Posts: 6              │                       │
│  │ Best Time: 6pm        │ Best Time: 2pm        │                       │
│  └───────────────────────┴───────────────────────┘                       │
│                                                                          │
│  Insight: TikTok has 3.6x more views but Instagram has +0.7% higher      │
│  engagement rate. Consider cross-posting top TikTok content to Instagram.│
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Period Comparison

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📅 Period Comparison                                                     │
│                                                                          │
│  [Dec 1-15]  vs  [Dec 16-31]                                             │
│                                                                          │
│                    Period 1        Period 2        Change                │
│  Views            45.2K           80.0K           +77% ↑                 │
│  Engagement       2.8%            3.2%            +0.4% ↑                │
│  Posts            7               8               +1 ↑                   │
│  Shares           234             456             +95% ↑                 │
│                                                                          │
│  Insight: Views nearly doubled while only posting 1 more video.          │
│  Content quality improved significantly.                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# Metric Definitions

| Metric | Formula | Platforms |
|--------|---------|-----------|
| **Views** | Raw view count | All |
| **Engagement Rate** | (likes + comments + shares) / views × 100 | All |
| **Hook Rate** | % viewers past 3 seconds | TikTok, Reels, Shorts |
| **Completion Rate** | % viewers who watched to end | TikTok, Reels, Shorts |
| **Avg % Viewed** | Average watch percentage | All video |
| **Share Rate** | shares / views × 100 | All |
| **Save Rate** | saves / views × 100 | Instagram, TikTok |
| **Likes per 1K** | likes / (views / 1000) | All |
| **CTR** | clicks / impressions × 100 | All (if tracking) |

---

# Implementation Priority

## Phase 1: Quick Wins (Day 1)
- [ ] Add deltas to KPI cards
- [ ] Add "Last updated" instead of button
- [ ] Combine charts into single hero chart with toggle

## Phase 2: Drivers (Day 2)  
- [ ] Add Drivers panel (4 cards)
- [ ] Add Time Window breakdown
- [ ] Add auto-generated Insights

## Phase 3: Table Improvements (Day 3)
- [ ] Reorder columns (decision first)
- [ ] Add row expand
- [ ] Add delta badges to table cells

## Phase 4: Modes (Day 4-5)
- [ ] Add Performance Mode toggle
- [ ] Implement Compare mode
- [ ] Move cumulative to Diagnose mode

---

# Success Metrics

| Metric | Target |
|--------|--------|
| Time to understand overall performance | < 5 seconds |
| Time to identify top content | < 10 seconds |
| Time to find actionable insight | < 15 seconds |
| Number of competing charts on screen | ≤ 1 hero |
| KPI cards with deltas | 100% |

---

*Last updated: December 21, 2025*
