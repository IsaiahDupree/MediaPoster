# PRD: Schedule Page Enhancements
## Mimic Opus Clips Scheduling Experience

**Version:** 1.0  
**Date:** December 21, 2025  
**Status:** In Development

---

## Executive Summary

Enhance the MediaPoster schedule page to match the user experience of Opus Clips' scheduling interface. This includes clickable post cards, an edit modal with video playback, inline date picker, scrollable day cells, and delete confirmation flows.

---

## Current State

The schedule page currently has:
- ✅ Month, Week, Day calendar views
- ✅ Drag and drop to reschedule
- ✅ Backend persistence for changes
- ✅ Media selector modal for adding new posts
- ✅ 24-hour format toggle
- ✅ Time input controls
- ✅ Past date validation

## Gap Analysis (vs Opus Clips)

| Feature | Opus Clips | MediaPoster | Gap |
|---------|-----------|-------------|-----|
| Plus button on empty days | ✅ Centered + icon | ❌ Text only | Missing |
| Scrollable day cells | ✅ Vertical scroll | ❌ Overflow hidden | Missing |
| Click post to edit | ✅ Opens modal | ❌ No click handler | Missing |
| Video player in modal | ✅ With duration overlay | ❌ Not implemented | Missing |
| Editable title field | ✅ Inline edit | ❌ Not implemented | Missing |
| Editable caption | ✅ With hashtag support | ❌ Not implemented | Missing |
| Visibility selector | ✅ Public/Private dropdown | ❌ Not implemented | Missing |
| Inline date picker | ✅ Calendar popup | ❌ Not implemented | Missing |
| Delete with confirmation | ✅ Confirm modal | ❌ Not implemented | Missing |
| Save button | ✅ Updates schedule | ❌ Not implemented | Missing |
| Post card design | ✅ Thumbnail + metadata | ⚠️ Basic design | Needs improvement |

---

## Feature Requirements

### 1. Plus Button on Day Cells
**Priority:** High  
**Effort:** Small

- Show a centered `+` icon button on hover for empty days
- Show a smaller `+` button at the top of days that already have posts
- Clicking opens the media selector modal with the date pre-filled
- Style: Semi-transparent circle with + icon, appears on hover

### 2. Scrollable Day Cells
**Priority:** High  
**Effort:** Small

- Add vertical scrollbar to day cells in Month and Week views
- Maximum height: 200px for Month view cells, 300px for Week view columns
- Scrollbar should blend with dark theme (thin, zinc-colored)
- Use `overflow-y-auto` with custom scrollbar styling

### 3. Post Card Design (Opus Clips Style)
**Priority:** High  
**Effort:** Medium

Each scheduled post card should display:
- **Thumbnail**: Video thumbnail (9:16 aspect ratio, rounded corners)
- **Account avatar**: Small circular avatar with platform icon
- **Account name**: Username text
- **Status badge**: "Posted" (green) or "Scheduled" (purple)
- **Time**: Clock icon + scheduled time
- **Title**: Truncated post title

Layout:
```
┌─────────────────────┐
│  [Thumbnail]        │
│                     │
│  👤 username  •Scheduled
│  🕐 12:00 AM        │
│  Post title here... │
└─────────────────────┘
```

### 4. Edit Scheduled Post Modal
**Priority:** Critical  
**Effort:** Large

Modal that opens when clicking a scheduled post:

#### 4.1 Header
- Title: "Edit scheduled post"
- Close button (X) in top-right

#### 4.2 Video Player Section (Left Side)
- Video player with poster image
- Duration overlay (e.g., "00:00 / 00:22")
- Play button overlay
- Click to play/pause
- Rounded corners

#### 4.3 Content Section (Right Side)
- **Account selector**: Avatar + username dropdown
- **Title field**: Editable text input
- **Caption field**: Multi-line textarea with hashtag highlighting
- **Action buttons**: Image, Hashtag (#), Mention (@) icons
- **Visibility dropdown**: Public / Private / Unlisted

#### 4.4 Footer
- **Delete button**: Red outline, left-aligned
- **Date/time display**: Shows full date + time + timezone
- **Save button**: Primary button, right-aligned

### 5. Inline Date Picker
**Priority:** High  
**Effort:** Medium

When clicking the date/time in the edit modal:
- Calendar popup appears
- Current date highlighted
- Navigation arrows for month
- Days grid (Su-Sa)
- Past dates grayed out
- 24-hour format toggle
- Time input field
- Timezone display (e.g., "GMT-05")

### 6. Delete Confirmation Modal
**Priority:** Medium  
**Effort:** Small

When clicking Delete:
- Overlay modal appears
- Title: "Delete post"
- Message: "Are you sure you want to delete this scheduled post?"
- Cancel button (dismiss)
- Confirm button (red, executes delete)

---

## Implementation Phases

### Phase 1: UI Polish (Day 1)
**Scope:** Plus button, scrollable cells, improved post cards

1. Add `+` button to empty day cells (centered)
2. Add `+` button to top of populated day cells
3. Add `overflow-y-auto` and `max-height` to day cells
4. Style scrollbar with Tailwind/CSS
5. Redesign post cards to match Opus Clips layout

**Files Modified:**
- `dashboard/app/(dashboard)/schedule/page.tsx`

**Acceptance Criteria:**
- [ ] Plus button visible on hover for all day cells
- [ ] Scrollbar appears when posts exceed cell height
- [ ] Post cards show thumbnail, account, status, time, title

---

### Phase 2: Edit Modal Structure (Day 2)
**Scope:** Basic edit modal with video player

1. Create `EditScheduledPostModal` component
2. Add click handler to post cards to open modal
3. Implement video player with poster and controls
4. Add duration overlay to video
5. Add basic layout (left: video, right: form)

**Files Modified:**
- `dashboard/app/(dashboard)/schedule/page.tsx`
- `dashboard/app/components/EditScheduledPostModal.tsx` (new)

**Acceptance Criteria:**
- [ ] Clicking post opens edit modal
- [ ] Video plays with native controls
- [ ] Duration shows as overlay
- [ ] Modal closes on X or outside click

---

### Phase 3: Edit Form Fields (Day 3)
**Scope:** Title, caption, visibility, account selector

1. Add account selector dropdown
2. Add editable title input
3. Add caption textarea with auto-resize
4. Add hashtag/mention action buttons
5. Add visibility dropdown (Public/Private)
6. Implement Save button with API call

**API Endpoints Needed:**
- `PUT /api/schedule/:id` - Update scheduled post

**Acceptance Criteria:**
- [ ] Can edit title and caption
- [ ] Changes persist on Save
- [ ] Visibility can be changed
- [ ] Form validates required fields

---

### Phase 4: Date Picker & Delete (Day 4)
**Scope:** Inline calendar, delete confirmation

1. Create date picker popup component
2. Implement calendar grid with navigation
3. Add 24-hour toggle and time input
4. Add timezone display
5. Create delete confirmation modal
6. Implement delete API call

**API Endpoints Needed:**
- `DELETE /api/schedule/:id` - Delete scheduled post

**Acceptance Criteria:**
- [ ] Date picker opens when clicking date
- [ ] Can select new date and time
- [ ] 24-hour toggle works
- [ ] Delete shows confirmation
- [ ] Post removed after confirming delete

---

## Technical Specifications

### State Management
```typescript
interface EditModalState {
  isOpen: boolean;
  post: ScheduledPost | null;
  isLoading: boolean;
  showDatePicker: boolean;
  showDeleteConfirm: boolean;
}

interface EditFormData {
  title: string;
  caption: string;
  visibility: 'public' | 'private' | 'unlisted';
  scheduledAt: string;
  accountId: string;
}
```

### API Contracts

#### Update Schedule
```
PUT /api/schedule/:id
Body: {
  title?: string,
  caption?: string,
  scheduled_at?: string,
  visibility?: string,
  account_id?: string
}
Response: { success: true, post: ScheduledPost }
```

#### Delete Schedule
```
DELETE /api/schedule/:id
Response: { success: true }
```

### Styling Guidelines
- Background: `bg-zinc-900`
- Border: `border-zinc-700`
- Text: `text-white` (primary), `text-zinc-400` (secondary)
- Accent: `bg-violet-500` (buttons), `text-green-400` (Posted badge)
- Scrollbar: Thin, `bg-zinc-700`, rounded

---

## Success Metrics

1. **Usability**: Users can edit scheduled posts in <3 clicks
2. **Feature parity**: Match 90% of Opus Clips scheduling features
3. **Performance**: Modal opens in <200ms
4. **Reliability**: All edits persist correctly to backend

---

## Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1 | 1 day | Day 1 | Day 1 |
| Phase 2 | 1 day | Day 2 | Day 2 |
| Phase 3 | 1 day | Day 3 | Day 3 |
| Phase 4 | 1 day | Day 4 | Day 4 |
| **Total** | **4 days** | | |

---

## Appendix: Opus Clips Reference Screenshots

### Screenshot 1: Week View Calendar
- Shows 7-day week with posts
- Each post has thumbnail, account, status badge, time, title
- Empty days have centered + button
- Posted (green) vs Scheduled (purple) badges

### Screenshot 2: Edit Modal
- Video player on left with play button overlay
- Duration shown (00:00 / 00:22)
- Account name and avatar
- Editable title
- Caption with hashtags
- Visibility dropdown
- Delete and Save buttons

### Screenshot 3: Date Picker
- Calendar popup overlay
- Month navigation arrows
- Day grid with current date highlighted
- 24-hour format toggle
- Time input
- Timezone display

### Screenshot 4: Delete Confirmation
- Modal overlay
- "Delete post" title
- Confirmation message
- Cancel and Confirm buttons
