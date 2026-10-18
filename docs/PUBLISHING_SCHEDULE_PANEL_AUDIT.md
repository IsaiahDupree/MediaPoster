# Publishing & Schedule Panel PRD Audit

**Date:** December 27, 2025  
**Status:** In Progress  
**Priority:** High

## Executive Summary

This document audits all publishing and scheduling panels in MediaPoster to ensure consistent display of AI-generated content (titles, descriptions, hashtags) and proper thumbnail/media handling across all pages.

---

## Issues Identified

### 1. Post-Content Page (`/post-content/[id]/page.tsx`)
**Status:** 🔴 Needs Update

**Current Issues:**
- Schedule panel shows filename (`GIKH9663.MP4`) instead of AI-generated title
- Panel doesn't use consistent design pattern from schedule page
- Missing AI-generated title/description pre-population in schedule modal

**Required Changes:**
- Use AI-generated title from `deep_analysis.suggested_caption` or `platform_content[].title`
- Pre-populate schedule modal with AI content
- Add loading states and proper error handling

### 2. Schedule Page (`/schedule/page.tsx`)
**Status:** 🟡 Partially Working

**Current Issues:**
- Posts show with thumbnail after posting but title shows filename
- Edit modal (image 5) shows filename `TABL2182.MOV` instead of AI title
- Need to display AI-generated content in edit modal

**Required Changes:**
- Fetch AI-generated content when loading posts
- Display AI title instead of filename in all views
- Show proper caption in edit modal

### 3. Publishing Page (Post-in-progress flow)
**Status:** 🔴 Needs Update

**Current Issues:**
- No polling/real-time updates for publishing status
- Console logs not sent to frontend service
- Missing progress indicators

**Required Changes:**
- Add polling mechanism for publish status
- Route console logs through frontend service
- Add real-time status updates via WebSocket

### 4. Media Detail Page → Schedule Modal
**Status:** 🟡 Partially Working

**Current Issues:**
- Schedule modal shows filename instead of AI title
- Missing AI-generated description pre-fill

**Required Changes:**
- Pass AI content to schedule modal
- Pre-populate title, description, hashtags from analysis

---

## Component Inventory

### Panels That Display Content

| Component | Location | Shows AI Title | Shows AI Description | Shows Thumbnail |
|-----------|----------|---------------|---------------------|-----------------|
| Schedule Post Modal | `/post-content/[id]` | ❌ Shows filename | ❌ Missing | ✅ Yes |
| Schedule Page Cards | `/schedule` | ❌ Shows filename | ❌ Truncated | ✅ Yes |
| Edit Scheduled Post Modal | `/schedule` | ❌ Shows filename | ✅ Yes | ✅ Yes |
| Publishing Page | `/post-content/[id]` | ❌ Shows filename | ❌ Missing | ✅ Yes |
| Quick Curate Cards | `/curate` | N/A | N/A | ✅ Yes |

---

## Implementation Phases

### Phase 1: Fix Post-Content Schedule Modal
**Priority:** High  
**Effort:** 2 hours

1. Update schedule modal to use AI-generated title
2. Pre-populate description from `deep_analysis`
3. Add proper loading states
4. Test with existing analyzed content

### Phase 2: Fix Schedule Page Display
**Priority:** High  
**Effort:** 2 hours

1. Fetch AI title when loading scheduled posts
2. Update card display to show AI title
3. Update edit modal to use AI content
4. Ensure thumbnail displays properly

### Phase 3: Add Publishing Page Polling
**Priority:** Medium  
**Effort:** 3 hours

1. Create frontend service method for publish polling
2. Add WebSocket subscription for publish events
3. Add console logging for debugging
4. Add progress indicators

### Phase 4: Comprehensive Testing
**Priority:** High  
**Effort:** 1 hour

1. Test schedule flow from media detail → post-content → schedule
2. Test edit scheduled post flow
3. Test publishing status updates
4. Verify all panels show AI content

---

## API Endpoints Required

### Existing Endpoints (Working)
- `GET /api/media-db/detail/{id}` - Returns media with analysis
- `GET /api/media-db/analysis/{id}` - Returns full analysis with `deep_analysis`
- `GET /api/schedule/list` - Returns scheduled posts
- `POST /api/schedule/create` - Creates scheduled post
- `PUT /api/schedule/{id}` - Updates scheduled post

### Endpoints Needing Enhancement
- `GET /api/schedule/list` - Should include AI-generated title from analysis
- `GET /api/schedule/{id}` - Should return full AI content

---

## Data Flow

```
Media Detail Page
    ↓
GET /api/media-db/analysis/{id}
    ↓
Extract: deep_analysis.suggested_caption, suggested_hashtags
    ↓
Post Content Page (Schedule Modal)
    ↓
Pre-fill: title, description, hashtags
    ↓
POST /api/schedule/create
    ↓
Schedule Page
    ↓
Display: AI title (not filename), thumbnail, status
```

---

## Success Criteria

- [ ] Schedule modal shows AI-generated title (not filename)
- [ ] Schedule modal pre-fills AI description
- [ ] Schedule page cards show AI title
- [ ] Edit scheduled post modal shows AI content
- [ ] Publishing page has real-time status updates
- [ ] All changes pushed to GitHub with tests

---

## Files to Modify

1. `/dashboard/app/(dashboard)/post-content/[id]/page.tsx`
2. `/dashboard/app/(dashboard)/schedule/page.tsx`
3. `/dashboard/lib/services/schedule-service.ts`
4. `/Backend/api/schedule.py` (if needed for AI content enrichment)

---

## Test Cases

### TC1: Schedule from Post-Content
1. Navigate to `/media/{id}` for analyzed video
2. Click "Post Content"
3. Click "Configure & Schedule"
4. **Expected:** Modal shows AI title, not filename
5. **Expected:** Description pre-filled with AI caption

### TC2: View Scheduled Posts
1. Navigate to `/schedule`
2. View scheduled post cards
3. **Expected:** Cards show AI title, not filename
4. **Expected:** Thumbnails display correctly

### TC3: Edit Scheduled Post
1. Click on scheduled post to edit
2. **Expected:** Title field shows AI title
3. **Expected:** Caption shows AI description

### TC4: Publishing Status
1. Publish content
2. **Expected:** Real-time status updates
3. **Expected:** Console logs visible in frontend
