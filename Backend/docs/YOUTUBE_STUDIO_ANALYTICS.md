# YouTube Studio Analytics Reference

## Overview Tab

### Key Metrics Cards (Top Row)
| Metric | Description | Format |
|--------|-------------|--------|
| **Views** | Total video views in period | `3.2K` with comparison |
| **Watch time (hours)** | Total watch time | `23.9` hours |
| **Subscribers** | Net subscriber change | `+5` or `-5` |

### Performance Chart
- Line chart showing views over time (28 days default)
- Date range selector: Last 28 days, 7 days, 90 days, 365 days, Lifetime

### Realtime Panel (Right Sidebar)
- **Subscribers**: Total count with "See live count" button
- **Views**: Last 48 hours with sparkline
- **Top content**: Mini thumbnails with view counts

### Your Top Content Table
| Column | Description |
|--------|-------------|
| Thumbnail | 120x68px video thumbnail |
| Title | Video title with "Recent upload" badge |
| Date | Upload date |
| Avg view duration | `0:50 (97.3%)` - duration and % of total |
| Views | View count |

---

## Content Tab

### Filter Pills
- All | Videos | Shorts | Playlists

### Metric Cards (3 columns)
| Card | Shows |
|------|-------|
| New viewers | Shorts: 1.3K, Videos: 395 |
| Regular viewers | Shorts: 1, Videos: 0 |
| Subscribers | Shorts: 0, Videos: +1 |

### Views Breakdown
- Shorts: `2.7K (85.2%)`
- Videos: `470 (14.8%)`
- Visual progress bars with percentages

### Published Content
- Content type with count (e.g., "Shorts: 2")

### Typical Views (First 28 days)
- Shorts: `4-160`
- Videos: `2-20`
- Shows range for benchmarking

### Viewers Across Formats
- Stacked bar: Shorts only | Watching both | Videos only
- Percentages: 54% | 13% | 33%

---

## Videos Sub-Tab (Content > Videos)

### Top Metrics Row
| Metric | Value | Comparison |
|--------|-------|------------|
| Views | 470 | vs previous period |
| Impressions | 5.1K | -19% |
| Impressions CTR | 5.2% | - |
| Avg view duration | 1:29 | - |

### Performance Chart
- Views over time with date axis
- Hover shows individual video performance

### Key Moments for Audience Retention
**Tabs**: Intro | Top moments | Spikes | Dips

| Section | Videos | Retention |
|---------|--------|-----------|
| Above typical intros | Video titles list | 55%, 45% |
| Below typical intros | Video titles list | 31%, 30% |

---

## Audience Tab

### Top Metrics
| Metric | Value |
|--------|-------|
| Monthly audience | 1.7K |
| Subscribers | -5 |

### Audience Growth Chart
- Line chart showing growth over time
- Y-axis: 0 to 2,250

### Audience by Watch Behavior
**Monthly audience breakdown:**
| Type | Percentage |
|------|------------|
| New viewers | 97.8% |
| Casual viewers | 2.7% |
| Regular viewers | < 0.1% |

### Popular with Different Audiences
**Tabs**: New | Casual | Regular

| Thumbnail | Title | Views Bar |
|-----------|-------|-----------|
| [img] | Posted via MediaPoster | ████████ 906 |
| [img] | Posted via MediaPoster | ██████ 638 |
| [img] | New radio for the 2005 Toyota 4 runner | █████ 516 |

---

## Advanced Mode

### Views by Content Table

| Column | Description |
|--------|-------------|
| Checkbox | Multi-select |
| Thumbnail | 80x45px thumbnail |
| Title | Video title |
| Views | With % of total |
| Watch time (hours) | With % of total |
| Subscribers | +/- count |
| Estimated revenue | If monetized |
| Impressions | Total |
| Impressions CTR | Click-through rate |

### Example Row:
```
☑️ [thumb] Posted via MediaPoster | 910 28.6% | 6.9 29.8% | -5 0% | -- | 21 | 4.9%
```

### Chart Features
- Line chart with multiple series (one per video)
- Hover shows video performance
- Toggle: Show chart | Line chart | Daily
- Date range filter

---

## UI Design Patterns

### Color Scheme
- Background: White (#FFFFFF)
- Text: Dark gray (#202124)
- Secondary text: Gray (#5F6368)
- Accent: Red (#FF0000) for YouTube brand
- Chart colors: Blue (#1A73E8), Purple (#9334E9)

### Cards
- White background
- Subtle shadow/border
- 16px padding
- 8px border radius

### Progress Bars
- Purple (#9334E9) for primary metrics
- Height: 8px
- Border radius: 4px

### Thumbnails
- Standard: 120x68px (16:9)
- Mini: 80x45px
- Border radius: 4px

### Typography
- Titles: 14px medium
- Metrics: 24-32px bold
- Labels: 12px regular gray

### Layout
- 3-column grid for metric cards
- Right sidebar for realtime (280px)
- Content table full width
- Responsive breakpoints

---

## API Data Mapping

### Profile Metrics → YouTube Studio
| API Field | Studio Display |
|-----------|----------------|
| `views` | Views |
| `likes` | Likes (not shown in overview) |
| `comments` | Comments |
| `watch_time_seconds` | Watch time (convert to hours) |
| `avg_view_duration` | Avg view duration |
| `impressions` | Impressions |
| `clicks / impressions` | Impressions CTR |
| `follower_count` | Subscribers |

### Post Metrics → Content Table
| API Field | Table Column |
|-----------|--------------|
| `title` | Title |
| `thumbnail_url` | Thumbnail |
| `posted_at` | Date |
| `views` | Views |
| `watch_time_seconds / 3600` | Watch time (hours) |
| `avg_view_duration` | Avg view duration |
| `avg_percent_viewed` | % completion |

---

*Reference: YouTube Studio (studio.youtube.com) - December 2024*
