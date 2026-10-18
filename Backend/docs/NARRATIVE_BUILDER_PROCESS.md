# Narrative Builder Process Documentation

## Overview

The Narrative Builder selects and schedules content based on AI analysis to create a cohesive narrative across social media platforms.

## Current Workflow

### 1. Content Selection Criteria

**Required for scheduling:**
- ✅ `pre_social_score` IS NOT NULL (has been analyzed)
- ✅ `curation_status = 'approved'` (human-reviewed and approved)
- ✅ Video file format (`.mov`, `.mp4`, `.m4v`, `.avi`)
- ✅ Not over-scheduled (`schedule_count < 5`)

**Excluded:**
- ❌ Images (`.jpg`, `.png`, `.heic`, etc.)
- ❌ Rejected content (`curation_status = 'rejected'`)
- ❌ Unanalyzed content (no `pre_social_score`)

### 2. AI Scoring Algorithm

Each video receives composite scores:

| Score | Weight | Description |
|-------|--------|-------------|
| Narrative Score | 30% | Alignment with goal pillars |
| Predicted Performance | 35% | Based on pre_social_score |
| Sentiment Fit | 15% | Freshness (less scheduled = higher) |
| Novelty Score | 20% | Never-posted content prioritized |

### 3. Scheduling Distribution

- **7 days** of content
- **3 time slots** per day: 10:00, 14:00, 19:00
- **6 platforms**: TikTok, Instagram, YouTube, Twitter, Bluesky, Threads
- **Result**: Up to 126 posts per week (7 videos × 18 slots)

## Process Improvements Implemented

### 1. Curation Gate ✅
- Added `curation_status = 'approved'` filter
- Prevents scheduling unapproved or rejected content
- Ensures human review before publishing

### 2. Video-Only Filter ✅
- Explicitly excludes image files
- Only schedules video content (`.mov`, `.mp4`, `.m4v`, `.avi`)

### 3. Rate Limit Exemption ✅
- `/api/schedule/create` exempt from rate limiting
- `/api/narrative-builder/` exempt from rate limiting
- Enables batch scheduling without 429 errors

### 4. Narrative Goal Integration ✅
- AI considers goal statement when scoring
- Pillars influence narrative alignment score
- Topics matched against pillars for relevance

## Recommended Future Improvements

### High Priority

1. **Transcript-Based Selection**
   - Use AI to analyze transcripts for narrative coherence
   - Group videos by theme/topic for better flow
   - Identify "hook" vs "value" vs "CTA" content types

2. **Visual Analysis Integration**
   - Use `visual_analysis` data for thumbnail selection
   - Match visual style across scheduled content
   - Identify branded vs casual content

3. **Platform-Specific Optimization**
   - Adjust content per platform (duration, format)
   - Different captions for different platforms
   - Platform-specific hashtag strategies

### Medium Priority

4. **Performance Feedback Loop**
   - Track actual performance vs predicted
   - Adjust scoring weights based on results
   - Learn which content types perform best

5. **Audience Time Optimization**
   - Use analytics to determine best posting times
   - Vary times by platform and audience
   - A/B test time slots

6. **Content Variety Enforcement**
   - Ensure topic diversity across week
   - Avoid scheduling similar content back-to-back
   - Balance content pillars

### Low Priority

7. **Duplicate Detection Integration**
   - Check for duplicate content before scheduling
   - Avoid re-scheduling same video too frequently
   - Track content freshness across platforms

8. **Trend Integration**
   - Match content to current trends
   - Prioritize trend-relevant content
   - Auto-adjust schedule for viral opportunities

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/narrative-builder/generate-recommendations` | POST | Get AI-scored content recommendations |
| `/api/narrative-builder/goals` | GET/POST | Manage narrative goals |
| `/api/narrative-builder/plan/7-day` | GET | Get 7-day content plan |
| `/api/schedule/create` | POST | Schedule a post |
| `/api/schedule/list` | GET | List scheduled posts |

## Usage Example

```python
# 1. Get AI recommendations
resp = requests.post("/api/narrative-builder/generate-recommendations", json={
    "goal": "Position as automation architect...",
    "cta_type": "follow",
    "pillars": ["AI Automation", "Content Systems", "Platform Founder"]
})
recommendations = resp.json()["recommendations"]

# 2. Schedule to platforms
for rec in recommendations[:7]:
    for platform in ["tiktok", "instagram", "youtube", "twitter", "bluesky", "threads"]:
        requests.post("/api/schedule/create", json={
            "content_id": rec["media"]["id"],
            "platform": platform,
            "scheduled_at": "2025-12-29T10:00:00",
            ...
        })
```

## Metrics

Current system status (as of last run):
- **Approved videos**: 225
- **Rejected videos**: 380
- **Scheduled posts**: 47
- **Platforms**: 6
- **Days covered**: 7
