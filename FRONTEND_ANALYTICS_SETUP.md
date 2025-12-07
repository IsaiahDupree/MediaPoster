# 📊 Frontend Analytics Dashboard - Setup Guide

**Status**: ✅ **Ready to Deploy**  
**Date**: November 22, 2025

---

## 🎯 What's Been Created

### Backend API Endpoints (FastAPI)
**File**: `/Backend/routers/social_analytics.py`

#### Endpoints Available:

1. **`GET /api/social-analytics/overview`**
   - Top-level aggregated data across all platforms
   - Returns: Total followers, views, likes, platform breakdown

2. **`GET /api/social-analytics/accounts`**
   - List all social accounts with latest metrics
   - Query params: `platform`, `monitoring_only`

3. **`GET /api/social-analytics/platform/{platform}`**
   - Detailed analytics for specific platform
   - Query params: `days` (default: 30)
   - Returns: Accounts, trends, top posts

4. **`GET /api/social-analytics/content-mapping`**
   - Shows which content is posted to which platforms
   - Links video_id/clip_id to social posts
   - Query params: `has_video`, `has_clip`

5. **`GET /api/social-analytics/posts`**
   - All posts with content mappings
   - Query params: `platform`, `limit`, `has_video`, `has_clip`

6. **`GET /api/social-analytics/trends`**
   - Historical trends over time
   - Query params: `days`

7. **`GET /api/social-analytics/hashtags/top`**
   - Top performing hashtags
   - Query params: `limit`

### Frontend Components (React + TypeScript)

**File**: `/Frontend/src/pages/analytics/SocialAnalyticsDashboard.tsx`
- Main dashboard with top-level overview
- Platform breakdown cards
- Content mapping table
- Account list

**File**: `/Frontend/src/pages/analytics/PlatformDetailView.tsx`
- Detailed view for each platform
- Growth charts
- Engagement trends
- Top posts list

**File**: `/Frontend/src/components/PlatformIcon.tsx`
- Platform icons with proper colors
- Badge components

---

## 🚀 Setup Instructions

### Step 1: Register Backend Router

Add to your FastAPI app:

**File**: `/Backend/main.py`

```python
from routers import social_analytics

# Add this line with your other routers
app.include_router(social_analytics.router)
```

### Step 2: Install Frontend Dependencies

```bash
cd Frontend
npm install recharts lucide-react
```

(Most likely already installed with your existing setup)

### Step 3: Add Routes to Frontend

**File**: `/Frontend/src/App.tsx` or your router config:

```typescript
import SocialAnalyticsDashboard from '@/pages/analytics/SocialAnalyticsDashboard';
import PlatformDetailView from '@/pages/analytics/PlatformDetailView';

// Add these routes
{
  path: '/analytics',
  element: <SocialAnalyticsDashboard />
},
{
  path: '/analytics/platform/:platform',
  element: <PlatformDetailView />
}
```

### Step 4: Test Backend API

```bash
cd Backend
./venv/bin/python -m uvicorn main:app --reload --port 5555
```

Test endpoints:
```bash
# Overview
curl http://localhost:5555/api/social-analytics/overview

# Accounts
curl http://localhost:5555/api/social-analytics/accounts

# Content Mapping
curl http://localhost:5555/api/social-analytics/content-mapping
```

### Step 5: Start Frontend

```bash
cd Frontend
npm run dev
```

Navigate to: `http://localhost:5173/analytics`

---

## 📊 Dashboard Features

### Top-Level View (All Platforms)

**URL**: `/analytics`

**Displays**:
1. **Aggregate Stats Cards**
   - Total Followers across all platforms
   - Total Views
   - Total Likes
   - Total Comments

2. **Platform Breakdown Table**
   - Each platform's metrics
   - Account count per platform
   - Followers, views, engagement per platform

3. **Content Mapping Table**
   - Shows which videos/clips are posted where
   - Total posts per content
   - Total views/likes per content
   - Best performing platform for each content

4. **Account List**
   - All tracked accounts
   - Click to filter by platform
   - Latest metrics per account

### Platform Detail View

**URL**: `/analytics/platform/{platform}`  
**Example**: `/analytics/platform/tiktok`

**Displays**:
1. **Platform Stats Summary**
   - Total followers on this platform
   - Total views on this platform
   - Total likes
   - Average engagement rate

2. **Growth Trends Chart**
   - Followers over time
   - Views over time
   - Selectable time range (7, 30, 90 days)

3. **Engagement Trends Chart**
   - Likes over time
   - Engagement rate over time

4. **Accounts on Platform**
   - Each account's metrics
   - Growth numbers

5. **Top Performing Posts**
   - Best posts by views
   - Direct links to posts
   - Performance metrics

---

## 🎨 UI Components Breakdown

### StatCard
Shows a single metric with icon and optional change indicator.

### PlatformBreakdownCard
Table showing all platforms with their metrics.

### ContentMappingTable
Shows content (videos/clips) and which platforms they're on:
- Content title/ID
- Platform icons
- Total posts
- Performance metrics
- Best performing platform badge

### AccountList
List of all accounts with inline metrics, clickable to filter by platform.

### Charts (recharts)
- AreaChart for growth trends
- LineChart for engagement trends
- Responsive and interactive

---

## 💡 Usage Examples

### Example 1: View All Analytics

```typescript
// Navigate to dashboard
navigate('/analytics');

// See top-level overview
// - Total followers across all platforms
// - Platform breakdown
// - Content distribution
```

### Example 2: Filter by Platform

```typescript
// Click on TikTok account in the list
// Or use platform badge
// URL becomes: /analytics?platform=tiktok

// See only TikTok data
```

### Example 3: View Platform Details

```typescript
// Navigate to specific platform
navigate('/analytics/platform/tiktok');

// See:
// - TikTok-specific stats
// - Growth charts
// - Top TikTok posts
```

### Example 4: Track Content Performance

```typescript
// View Content Mapping table
// See which video/clip is performing best
// Identify best platform for each piece of content

// Example data:
{
  video_id: "uuid-123",
  video_title: "How to use MediaPoster",
  platforms: ["tiktok", "instagram", "youtube"],
  total_posts: 3,
  total_views: 50000,
  best_performing_platform: "tiktok"  // 40K of the 50K views
}
```

---

## 🔌 API Response Examples

### Overview Response

```json
{
  "total_platforms": 3,
  "total_accounts": 5,
  "total_followers": 15000,
  "total_posts": 120,
  "total_views": 500000,
  "total_likes": 45000,
  "total_comments": 1200,
  "avg_engagement_rate": 8.5,
  "platform_breakdown": [
    {
      "platform": "tiktok",
      "total_accounts": 2,
      "total_followers": 8000,
      "total_posts": 80,
      "total_views": 350000,
      "total_likes": 30000,
      "avg_engagement_rate": 9.2
    },
    {
      "platform": "instagram",
      "total_accounts": 2,
      "total_followers": 5000,
      "total_posts": 30,
      "total_views": 120000,
      "total_likes": 12000,
      "avg_engagement_rate": 7.8
    },
    {
      "platform": "youtube",
      "total_accounts": 1,
      "total_followers": 2000,
      "total_posts": 10,
      "total_views": 30000,
      "total_likes": 3000,
      "avg_engagement_rate": 8.0
    }
  ]
}
```

### Content Mapping Response

```json
[
  {
    "video_id": "uuid-123",
    "clip_id": null,
    "video_title": "How to use MediaPoster",
    "platforms": ["tiktok", "instagram", "youtube"],
    "total_posts": 3,
    "total_views": 50000,
    "total_likes": 4500,
    "total_comments": 120,
    "best_performing_platform": "tiktok"
  },
  {
    "video_id": null,
    "clip_id": "uuid-456",
    "video_title": null,
    "platforms": ["tiktok", "instagram"],
    "total_posts": 2,
    "total_views": 25000,
    "total_likes": 2200,
    "total_comments": 50,
    "best_performing_platform": "instagram"
  }
]
```

---

## 🎯 Key Features

### ✅ Top-Level Dashboard
- **Aggregate metrics** across all 9 platforms
- **Platform comparison** at a glance
- **Content distribution** view
- **Filterable** by platform

### ✅ Platform-Specific Views
- **Detailed metrics** per platform
- **Growth charts** with selectable time ranges
- **Top posts** identification
- **Account breakdown** on platform

### ✅ Content Mapping
- **Link social posts to videos/clips**
- See which content performs best where
- Identify optimal platforms for content types
- Track content across multiple platforms

### ✅ Interactive UI
- **Clickable elements** for drill-down
- **Responsive charts** with tooltips
- **Time range selectors**
- **Loading states**

### ✅ Real-Time Data
- Powered by your analytics database
- Updates as data is collected
- Cron jobs keep it fresh

---

## 🔧 Customization

### Add More Charts

```typescript
import { BarChart, Bar, PieChart, Pie } from 'recharts';

// Add to component
<ResponsiveContainer width="100%" height={300}>
  <BarChart data={yourData}>
    <Bar dataKey="followers" fill="#3b82f6" />
  </BarChart>
</ResponsiveContainer>
```

### Add Filters

```typescript
const [dateRange, setDateRange] = useState('30d');
const [contentType, setContentType] = useState('all');

// Use in query
const { data } = useQuery({
  queryKey: ['analytics', dateRange, contentType],
  queryFn: () => fetchData(dateRange, contentType)
});
```

### Add Export Functionality

```typescript
const exportToCSV = () => {
  const csv = accounts.map(a => 
    `${a.username},${a.followers},${a.views}`
  ).join('\n');
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'analytics.csv';
  a.click();
};
```

---

## 📱 Mobile Responsiveness

The dashboard is responsive and works on mobile:
- Grid layouts collapse on small screens
- Charts are responsive
- Tables scroll horizontally
- Touch-friendly interactions

---

## 🎉 Summary

**What You Have**:
- ✅ **7 API endpoints** for comprehensive analytics
- ✅ **2 main dashboard views** (overview + platform detail)
- ✅ **Content mapping** visualization
- ✅ **Interactive charts** for trends
- ✅ **Platform comparison** at a glance
- ✅ **Click-through** to details
- ✅ **Real-time data** from database

**To Deploy**:
1. Register router in FastAPI (`main.py`)
2. Add routes in React (`App.tsx`)
3. Start backend and frontend
4. Navigate to `/analytics`

**URLs**:
- Dashboard: `http://localhost:5173/analytics`
- Platform View: `http://localhost:5173/analytics/platform/tiktok`
- API Base: `http://localhost:5555/api/social-analytics`

🎊 **Your comprehensive social media analytics dashboard is ready!**
