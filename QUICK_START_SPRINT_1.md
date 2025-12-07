# 🚀 Quick Start: Sprint 1 Implementation Guide

**Timeline**: 2 weeks (10 working days)  
**Goal**: Build core EverReach workflows with real data

---

## 📋 Sprint 1 Overview

### Three Core Features

1. **Dashboard Widgets** - Show meaningful metrics at a glance
2. **Video → Clip Workflow** - Create clips from videos seamlessly  
3. **Analytics Intelligence** - Add engagement rates and comparisons

---

## 📅 Day-by-Day Plan

### Day 1-2: Dashboard Widgets Backend

**Goal**: Create API endpoints to power dashboard widgets

**Files to Create/Modify**:
- `Backend/api/endpoints/dashboard.py`
- `Backend/main.py` (register router)

#### Create `dashboard.py`:

```python
from fastapi import APIRouter, Depends
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db

router = APIRouter()

@router.get("/widgets")
async def get_dashboard_widgets(db: AsyncSession = Depends(get_db)):
    """Get all dashboard widget data in one call"""
    
    # Recent top-performing content
    recent_content_query = """
        SELECT 
            ci.id,
            ci.title,
            ci.thumbnail_url,
            ci.created_at,
            cr.total_views_organic + cr.total_views_paid as total_views,
            cr.total_likes_organic + cr.total_likes_paid as total_likes,
            ((cr.total_likes_organic + cr.total_likes_paid + 
              cr.total_comments_organic + cr.total_comments_paid) / 
             NULLIF(cr.total_views_organic + cr.total_views_paid, 0)) * 100 as engagement_rate
        FROM content_items ci
        JOIN content_rollups cr ON ci.id = cr.content_id
        WHERE ci.created_at >= NOW() - INTERVAL '7 days'
        ORDER BY engagement_rate DESC
        LIMIT 5
    """
    
    # Upcoming scheduled posts (from calendar table if exists, or mock)
    upcoming_query = """
        SELECT 
            id,
            title,
            scheduled_time,
            platform,
            status
        FROM scheduled_posts  -- If this table exists
        WHERE scheduled_time >= NOW()
        AND scheduled_time <= NOW() + INTERVAL '7 days'
        ORDER BY scheduled_time ASC
        LIMIT 10
    """
    
    # Segment summary
    segments_query = """
        SELECT 
            s.id,
            s.name,
            COUNT(sm.person_id) as member_count,
            si.activity_rate_organic,
            si.top_platform
        FROM segments s
        LEFT JOIN segment_members sm ON s.id = sm.segment_id
        LEFT JOIN segment_insights si ON s.id = si.segment_id
        GROUP BY s.id, si.activity_rate_organic, si.top_platform
        LIMIT 5
    """
    
    # AI Alerts/Insights (from existing recommendations or create new)
    ai_alerts = [
        {
            "type": "opportunity",
            "title": "LinkedIn engagement up 35%",
            "action": "Post more to LinkedIn this week",
            "priority": "high"
        },
        {
            "type": "warning  ",
            "title": "TikTok views declining",
            "action": "Review recent TikTok content strategy",
            "priority": "medium"
        },
        {
            "type": "insight",
            "title": "Founders segment highly active",
            "action": "Generate content brief for this group",
            "priority": "low"
        }
    ]
    
    return {
        "recent_content": await db.execute(recent_content_query).fetchall(),
        "upcoming_posts": [],  # Implement when calendar ready
        "segments": await db.execute(segments_query).fetchall(),
        "ai_alerts": ai_alerts
    }


@router.get("/north-star")
async def get_north_star_metrics(db: AsyncSession = Depends(get_db)):
    """Get North Star metrics for dashboard"""
    
    # Weekly Engaged Reach
    engaged_reach_query = """
        SELECT COUNT(DISTINCT person_id) as reach
        FROM person_events
        WHERE occurred_at >= NOW() - INTERVAL '7 days'
        AND event_type IN ('comment', 'like', 'share', 'click')
    """
    
    # Content Leverage Score (variants per content item)
    leverage_query = """
        SELECT AVG(variant_count) as leverage_score
        FROM (
            SELECT content_id, COUNT(*) as variant_count
            FROM content_variants
            GROUP BY content_id
        ) as counts
    """
    
    # Warm Lead Flow
    warm_leads_query = """
        SELECT COUNT(*) as warm_leads
        FROM person_insights
        WHERE warmth_score >= 70
        AND last_active_at >= NOW() - INTERVAL '7 days'
    """
    
    return {
        "weekly_engaged_reach": (await db.execute(engaged_reach_query)).scalar() or 0,
        "content_leverage_score": (await db.execute(leverage_query)).scalar() or 0,
        "warm_lead_flow": (await db.execute(warm_leads_query)).scalar() or 0
    }
```

#### Register in `main.py`:

```python
# Dashboard
from api.endpoints import dashboard
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
```

**Test**: `curl http://localhost:5555/api/dashboard/widgets`

---

### Day 3-4: Dashboard Widgets Frontend

**Goal**: Create React components and integrate with API

**Files to Create**:
- `Frontend/src/components/dashboard/RecentContentWidget.tsx`
- `Frontend/src/components/dashboard/UpcomingPostsWidget.tsx`
- `Frontend/src/components/dashboard/SegmentsSummaryWidget.tsx`
- `Frontend/src/components/dashboard/AIAlertsWidget.tsx`

#### Create `RecentContentWidget.tsx`:

```typescript
"use client"

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { TrendingUp } from "lucide-react"
import Link from "next/link"
import { useEffect, useState } from "react"

interface ContentItem {
  id: string
  title: string
  thumbnail_url: string
  total_views: number
  engagement_rate: number
}

export function RecentContentWidget() {
  const [content, setContent] = useState<ContentItem[]>([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    fetchContent()
  }, [])
  
  const fetchContent = async () => {
    try {
      const res = await fetch('http://localhost:5555/api/dashboard/widgets')
      const data = await res.json()
      setContent(data.recent_content.slice(0, 3))
    } catch (error) {
      console.error("Failed to fetch content", error)
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Top Performing Content</CardTitle>
            <CardDescription>Last 7 days</CardDescription>
          </div>
          <Link href="/analytics/content" className="text-sm text-primary hover:underline">
            View All →
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-gray-200 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {content.map((item, idx) => (
              <Link 
                key={item.id} 
                href={`/content/${item.id}`}
                className="flex items-center gap-3 p-2 rounded hover:bg-accent transition-colors"
              >
                <img 
                  src={item.thumbnail_url || '/placeholder.jpg'} 
                  alt={item.title}
                  className="w-16 h-16 object-cover rounded"
                />
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{item.title}</div>
                  <div className="text-sm text-muted-foreground">
                    {item.total_views.toLocaleString()} views · {item.engagement_rate.toFixed(1)}% engagement
                  </div>
                </div>
                <TrendingUp className="h-4 w-4 text-green-500" />
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

#### Update `dashboard/page.tsx`:

```typescript
import { RecentContentWidget } from "@/components/dashboard/RecentContentWidget"
import { UpcomingPostsWidget } from "@/components/dashboard/UpcomingPostsWidget"
import { SegmentsSummaryWidget } from "@/components/dashboard/SegmentsSummaryWidget"
import { AIAlertsWidget } from "@/components/dashboard/AIAlertsWidget"

// Add after the North Star Metrics grid:

{/* Dashboard Widgets Grid */}
<div className="grid gap-4 md:grid-cols-2">
  <RecentContentWidget />
  <UpcomingPostsWidget />
  <SegmentsSummaryWidget />
  <AIAlertsWidget />
</div>
```

---

### Day 5-6: Video → Clip Workflow Backend

**Goal**: Add clip creation endpoints

**Files to Modify**:
- `Backend/api/endpoints/videos.py`

#### Add to `videos.py`:

```python
@router.get("/{video_id}/summary")
async def get_video_summary(video_id: str, db: AsyncSession = Depends(get_db)):
    """Get video summary including clip count and performance"""
    
    # Count clips created from this video
    clip_count_query = """
        SELECT COUNT(*) 
        FROM clips
        WHERE source_video_id = :video_id
    """
    
    # Get performance across platforms (if published)
    performance_query = """
        SELECT 
            SUM(cm.views) as total_views,
            SUM(cm.likes + cm.comments + cm.shares) as total_engagement,
            ARRAY_AGG(DISTINCT cv.platform) as platforms
        FROM content_items ci
        JOIN content_variants cv ON ci.id = cv.content_id
        JOIN content_metrics cm ON cv.id = cm.variant_id
        WHERE ci.source_video_id = :video_id
    """
    
    clip_count = await db.execute(clip_count_query, {"video_id": video_id}).scalar() or 0
    performance = await db.execute(performance_query, {"video_id": video_id}).first()
    
    return {
        "video_id": video_id,
        "clip_count": clip_count,
        "total_views": performance.total_views if performance else 0,
        "total_engagement": performance.total_engagement if performance else 0,
        "platforms": performance.platforms if performance else [],
        "engagement_rate": (
            (performance.total_engagement / performance.total_views * 100)
            if performance and performance.total_views > 0 else 0
        )
    }


@router.post("/{video_id}/create-clip")
async def create_clip_from_video(
    video_id: str,
    start_time: float,
    end_time: float,
    title: str,
    db: AsyncSession = Depends(get_db)
):
    """Create a clip from a video"""
    
    # Create clip record
    clip = await db.execute("""
        INSERT INTO clips (source_video_id, start_time, end_time, title, status)
        VALUES (:video_id, :start, :end, :title, 'processing')
        RETURNING id
    """, {
        "video_id": video_id,
        "start": start_time,
        "end": end_time,
        "title": title
    })
    
    clip_id = clip.scalar()
    
    # Trigger background job to actually create the clip file
    # (Implementation depends on your video processing setup)
    
    return {
        "clip_id": clip_id,
        "status": "processing",
        "message": "Clip creation started"
    }
```

---

### Day 7-8: Video → Clip Workflow Frontend

**Goal**: Add UI for clip creation

**Files to Modify**:
- `Frontend/src/app/video-library/page.tsx`
- Create: `Frontend/src/components/modals/CreateClipModal.tsx`

#### Update Video Card in `video-library/page.tsx`:

```typescript
import { Scissors, BarChart3 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

// In your VideoCard component, add:
const [summary, setSummary] = useState(null)

useEffect(() => {
  fetchVideoSummary(video.id)
}, [video.id])

const fetchVideoSummary = async (id: string) => {
  const res = await fetch(`http://localhost:5555/api/videos/${id}/summary`)
  const data = await res.json()
  setSummary(data)
}

// In the card JSX:
<div className="flex items-center justify-between mt-2">
  <div className="flex items-center gap-2">
    {summary?.clip_count > 0 && (
      <Badge variant="secondary">
        <Scissors className="mr-1 h-3 w-3" />
        {summary.clip_count} clips
      </Badge>
    )}
    {summary?.total_views > 0 && (
      <Badge variant="outline">
        <BarChart3 className="mr-1 h-3 w-3" />
        {summary.total_views.toLocaleString()} views
      </Badge>
    )}
  </div>
  <Button 
    variant="outline" 
    size="sm"
    onClick={() => openClipCreator(video)}
  >
    <Scissors className="mr-2 h-4 w-4" />
    Create Clip
  </Button>
</div>
```

---

### Day 9-10: Analytics Enhancements

**Goal**: Add engagement rate calculations and comparison feature

**Files to Modify**:
- `Frontend/src/app/analytics/content/page.tsx`

#### Add Engagement Rate Display:

```typescript
// For each content item, calculate and show engagement rate
const calculateEngagementRate = (item: any) => {
  const totalEngagement = (item.total_likes || 0) + 
                          (item.total_comments || 0) + 
                          (item.total_shares || 0)
  const totalViews = (item.total_views || 0)
  
  return totalViews > 0 ? (totalEngagement / totalViews * 100) : 0
}

// In the content card:
<div className="text-sm">
  <div className="flex items-center justify-between">
    <span className="text-muted-foreground">Engagement Rate:</span>
    <span className={`font-semibold ${
      engagementRate > 5 ? 'text-green-500' : 
      engagementRate > 2 ? 'text-yellow-500' : 
      'text-red-500'
    }`}>
      {engagementRate.toFixed(2)}%
    </span>
  </div>
  <div className="flex items-center justify-between">
    <span className="text-muted-foreground">Total Reach:</span>
    <span className="font-semibold">
      {(item.total_views || 0).toLocaleString()}
    </span>
  </div>
</div>
```

#### Add Comparison Feature:

```typescript
const [selectedItems, setSelectedItems] = useState<string[]>([])

// Add checkboxes to content cards
<Checkbox 
  checked={selectedItems.includes(item.id)}
  onCheckedChange={(checked) => {
    if (checked) {
      setSelectedItems([...selectedItems, item.id])
    } else {
      setSelectedItems(selectedItems.filter(id => id !== item.id))
    }
  }}
/>

// Add compare button
{selectedItems.length >= 2 && (
  <Button onClick={() => router.push(`/analytics/compare?ids=${selectedItems.join(',')}`)}>
    Compare {selectedItems.length} Items
  </Button>
)}
```

---

## ✅ Sprint 1 Testing Checklist

### Dashboard
- [ ] Dashboard loads in < 2 seconds
- [ ] Recent content shows top 5 from last 7 days
- [ ] North Star metrics display real numbers
- [ ] All widgets link to relevant pages
- [ ] Widgets refresh when "Refresh Data" clicked

### Video → Clip
- [ ] Video library shows clip count badges
- [ ] Performance indicators visible
- [ ] "Create Clip" button opens modal
- [ ] Clip creation succeeds
- [ ] New clips appear in Clip Studio

### Analytics
- [ ] Engagement rates calculated correctly
- [ ] Reach/views display properly
- [ ] Comparison works for 2+ items
- [ ] Filters and search still work

---

## 🎯 Success Criteria

**Sprint 1 is complete when**:
1. Dashboard shows 4 working widgets with real data
2. Users can create clips from videos via UI
3. Analytics shows engagement rates for all content
4. All features tested and working on mobile

---

## 🚀 Quick Commands

```bash
# Start Backend
cd Backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# Start Frontend  
cd Frontend
npm run dev

# Test API
curl http://localhost:5555/api/dashboard/widgets
curl http://localhost:5555/api/dashboard/north-star
curl http://localhost:5555/api/videos/{id}/summary
```

---

## 📖 Next Steps

After Sprint 1, move to Sprint 2 (Intelligence Layer):
- Enhance People detail pages
- Add topic analysis to Content Intelligence
- Categorize Recommendations
- Build Segment creator

---

**Ready to Start**: Begin with Day 1-2 (Dashboard Backend) and work through sequentially! 🎯
