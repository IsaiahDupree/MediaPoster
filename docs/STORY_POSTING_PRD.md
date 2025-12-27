# Story Posting & Scheduling Feature PRD

## Executive Summary

This PRD defines the implementation of Story posting and scheduling capabilities for Instagram (and future TikTok support when available). The feature will integrate with the existing scheduling panel and make **Reels the default** posting option for Instagram accounts, with Stories as an explicit selection.

---

## Research Findings

### Blotato API Capabilities

#### Instagram Stories ✅ SUPPORTED
- **API Parameter**: `mediaType: 'story'` in the Instagram target object
- **Default**: `'reel'` (Reels are the default)
- **Media Support**: Both images and videos can be posted as Stories
- **Limitations**: 
  - Stories cannot include collaborators
  - Alt text may not be supported for Stories
  - Stories expire after 24 hours (platform limitation)

```javascript
// Example Instagram Story payload
{
  "post": {
    "accountId": "instagram_account_id",
    "content": {
      "text": "Check out my story!",
      "mediaUrls": ["https://example.com/video.mp4"],
      "platform": "instagram"
    },
    "target": {
      "targetType": "instagram",
      "mediaType": "story"  // 'reel' | 'story'
    }
  }
}
```

#### TikTok Stories ❌ NOT SUPPORTED
- Blotato API does **NOT** currently support TikTok Stories
- Only regular TikTok posts are supported
- **Future consideration**: Monitor Blotato API updates for TikTok Story support

#### Facebook Stories - Needs Investigation
- Facebook target has `mediaType: 'video' | 'reel'`
- No explicit Story support documented
- May require separate research

---

## Feature Requirements

### Core Requirements

1. **Instagram Media Type Selection**
   - Add media type selector when Instagram account is selected
   - Options: `Reel` (default), `Story`
   - Visual indicator showing selected type

2. **Default to Reels**
   - When Instagram account is selected, automatically set `mediaType: 'reel'`
   - User can override to Story if desired

3. **Story-Specific UI Considerations**
   - Show "24h expiry" warning for Stories
   - Disable collaborator field for Stories
   - Show Story aspect ratio recommendations (9:16)

4. **Database Schema Updates**
   - Add `media_type` field to `scheduled_posts` table
   - Store 'reel' | 'story' | 'post' | null

5. **Scheduling Integration**
   - Stories can be scheduled like any other post
   - Calendar view shows Story indicator icon

---

## Architecture

### Database Changes

```sql
-- Add media_type column to scheduled_posts
ALTER TABLE scheduled_posts 
ADD COLUMN IF NOT EXISTS media_type TEXT DEFAULT 'reel';

-- Add constraint for valid values
ALTER TABLE scheduled_posts 
ADD CONSTRAINT valid_media_type 
CHECK (media_type IN ('reel', 'story', 'post', 'video', NULL));
```

### Backend Changes

1. **Update `InstagramTarget`** in `blotato_api.py`
   - Already supports `media_type` parameter ✅

2. **Update Publishing Flow**
   - Read `media_type` from scheduled_post
   - Pass to Blotato API when publishing

3. **Update Schedule API**
   - Accept `media_type` in POST/PUT requests
   - Return `media_type` in GET responses

### Frontend Changes

1. **Schedule Page**
   - Add media type selector in post creation panel
   - Show when Instagram account is selected

2. **Calendar View**
   - Show Story vs Reel indicator on scheduled posts

3. **Post Details Modal**
   - Display media type
   - Allow editing media type

---

## Implementation Phases

### Phase 1: Backend Infrastructure (Day 1)
- [ ] Add `media_type` column to `scheduled_posts` table
- [ ] Update schedule API endpoints to handle media_type
- [ ] Update publishing flow to pass media_type to Blotato
- [ ] Add validation for Instagram media types

### Phase 2: Frontend - Schedule Panel (Day 2)
- [ ] Add media type selector component
- [ ] Show selector when Instagram account selected
- [ ] Default to 'reel' for Instagram
- [ ] Save media_type with scheduled post

### Phase 3: Frontend - Calendar & Display (Day 3)
- [ ] Add Story/Reel indicators in calendar view
- [ ] Update post details modal
- [ ] Add Story expiry warning
- [ ] Update filters to include media type

### Phase 4: Testing & Polish (Day 4)
- [ ] Integration tests for Story posting
- [ ] E2E tests for scheduling flow
- [ ] UI polish and edge cases
- [ ] Documentation

---

## API Specification

### Schedule Post Request (Updated)

```typescript
interface SchedulePostRequest {
  content_id: string;
  account_ids: string[];
  scheduled_time: string;  // ISO 8601
  caption?: string;
  
  // NEW: Media type for Instagram
  media_type?: 'reel' | 'story' | 'post' | 'video';
  
  // Existing fields
  hashtags?: string[];
  first_comment?: string;
}
```

### Schedule Post Response (Updated)

```typescript
interface ScheduledPost {
  id: string;
  content_id: string;
  account_id: string;
  scheduled_time: string;
  status: 'pending' | 'published' | 'failed';
  
  // NEW
  media_type: 'reel' | 'story' | 'post' | 'video' | null;
  
  // Existing fields
  platform: string;
  caption: string;
}
```

---

## UI/UX Design

### Media Type Selector (When Instagram Selected)

```
┌─────────────────────────────────────────┐
│ Post Type                               │
│ ┌─────────────┐ ┌─────────────┐         │
│ │  📹 Reel   │ │  📖 Story  │         │
│ │  (default) │ │  (24h)     │         │
│ └─────────────┘ └─────────────┘         │
└─────────────────────────────────────────┘
```

### Calendar Post Indicator

```
┌──────────────────────────┐
│ 3:00 PM                  │
│ ┌──────────────────────┐ │
│ │ 📹 Product Launch    │ │  ← Reel indicator
│ │ @the_isaiah_dupree   │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │ 📖 Behind Scenes     │ │  ← Story indicator
│ │ @dupree_isaiah_      │ │
│ └──────────────────────┘ │
└──────────────────────────┘
```

---

## Future Considerations

1. **TikTok Stories**: Monitor Blotato API for Story support
2. **Facebook Stories**: Research and add if supported
3. **Story Highlights**: Allow marking Stories for Highlights
4. **Story Analytics**: Track Story views/engagement separately
5. **Story Templates**: Pre-designed Story layouts

---

## Success Metrics

- [ ] Stories can be scheduled via the scheduling panel
- [ ] Reels are the default for Instagram accounts
- [ ] Users can switch between Reel/Story easily
- [ ] Scheduled Stories publish successfully via Blotato
- [ ] Calendar view clearly distinguishes Story vs Reel posts

---

## Technical Notes

### Existing Code References

- **Blotato API**: `Backend/services/blotato_api.py`
  - `InstagramTarget` already has `media_type` field
  - Supports `Literal["reel", "story"]`

- **Schedule Page**: `dashboard/app/(dashboard)/schedule/page.tsx`
  - Needs media type selector integration

- **Publishing Flow**: `Backend/api/endpoints/schedule.py`
  - Needs to read and pass media_type

### Dependencies

- No new dependencies required
- Uses existing Blotato API integration
- Uses existing scheduling infrastructure

---

*Created: December 27, 2024*
*Author: MediaPoster Development*
*Status: Ready for Implementation*
