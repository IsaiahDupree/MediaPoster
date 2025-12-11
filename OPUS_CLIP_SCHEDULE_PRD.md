# OpusClip Scheduling & Publishing - Product Requirements Document (PRD)

**Comprehensive Analysis of OpusClip's Scheduling Product for Competitive Reference**

---

## 1. Product Overview

### 1.1 Product Vision
OpusClip's scheduling system enables creators to transform long-form videos into viral short-form clips and automatically distribute them across all major social platforms with minimal effort.

### 1.2 Core Value Proposition
- **10x Faster Content Creation:** Turn 1 long video into 10 viral clips
- **One-Click Publishing:** Post to all platforms simultaneously
- **AI Automation:** Auto-generate captions, hashtags, and descriptions
- **Bulk Operations:** Schedule a month's content in 10 minutes

### 1.3 Target Users
| User Segment | Needs | OpusClip Solution |
|--------------|-------|-------------------|
| Solo Creators | Time savings, growth | AI clipping, bulk scheduling |
| Marketing Teams | Brand consistency, scale | Team workspace, brand templates |
| Agencies | Multi-client management | Business plans, API |
| Enterprises | Integration, security | Custom solutions, API |

---

## 2. Scheduling Module Requirements

### 2.1 Calendar View (FR-CAL)

#### FR-CAL-001: Visual Calendar
- **Description:** Display scheduled and past posts in monthly/weekly calendar view
- **Acceptance Criteria:**
  - Show posts on correct dates
  - Color-code by platform
  - Display post thumbnails
  - Show post status (scheduled, published, failed)

#### FR-CAL-002: Calendar Navigation
- **Description:** Navigate between months and view different time periods
- **Acceptance Criteria:**
  - Previous/next month buttons
  - Jump to specific date
  - Today shortcut
  - Week/month view toggle

#### FR-CAL-003: Post Management from Calendar
- **Description:** Manage posts directly from calendar interface
- **Acceptance Criteria:**
  - Click post to view details
  - Drag and drop to reschedule
  - Delete with confirmation
  - Edit post content

### 2.2 Single Post Scheduling (FR-SCH)

#### FR-SCH-001: Schedule from Results Page
- **Description:** Schedule individual clips directly after generation
- **Acceptance Criteria:**
  - Schedule button on each clip
  - Platform selection dropdown
  - Date/time picker
  - Caption editing before schedule

#### FR-SCH-002: Platform Selection
- **Description:** Choose target platforms for scheduled post
- **Acceptance Criteria:**
  - Multi-select platforms
  - Show connected accounts
  - Platform-specific preview
  - Character count validation

#### FR-SCH-003: Time Selection
- **Description:** Set posting date and time
- **Acceptance Criteria:**
  - Date picker (calendar widget)
  - Time picker (hour/minute)
  - Timezone display
  - Minimum 5-minute advance scheduling

### 2.3 Bulk Scheduling (FR-BULK)

#### FR-BULK-001: Multi-Clip Selection
- **Description:** Select multiple clips for bulk operations
- **Acceptance Criteria:**
  - Checkbox on each clip
  - Select all button
  - Selection counter display
  - Deselect all option

#### FR-BULK-002: Posting Order Configuration
- **Description:** Define the order clips will be posted
- **Acceptance Criteria:**
  - Manual order assignment (1, 2, 3...)
  - Drag and drop reordering
  - Random order option
  - Order preview

#### FR-BULK-003: Start Time Configuration
- **Description:** Set when the first post goes out
- **Acceptance Criteria:**
  - Date picker for first post
  - Time picker for first post
  - Timezone selection
  - Immediate start option

#### FR-BULK-004: Frequency Configuration
- **Description:** Define posting interval between clips
- **Acceptance Criteria:**
  - Interval options (hourly, daily, custom)
  - Custom hour interval input
  - Preview of all posting times
  - No weekend skip (exact intervals)

#### FR-BULK-005: AI Content Generation
- **Description:** Auto-generate captions and hashtags
- **Acceptance Criteria:**
  - AI-generated descriptions
  - AI-generated hashtags
  - Per-post editing capability
  - Platform-specific optimization

#### FR-BULK-006: Schedule Preview
- **Description:** Preview all scheduled posts before confirming
- **Acceptance Criteria:**
  - List of all posts with times
  - Platform indicators
  - Caption preview
  - Edit before confirm option

### 2.4 Post Cancellation (FR-CAN)

#### FR-CAN-001: Cancel Scheduled Post
- **Description:** Cancel individual scheduled posts
- **Acceptance Criteria:**
  - Cancel button on scheduled post
  - Confirmation dialog
  - Return to draft option
  - Bulk cancel support

#### FR-CAN-002: Edit Scheduled Post
- **Description:** Modify post before it goes live
- **Acceptance Criteria:**
  - Edit caption
  - Change posting time
  - Change platform
  - Preview changes

---

## 3. Publishing Module Requirements

### 3.1 Social Account Connection (FR-SOC)

#### FR-SOC-001: Account Management Dashboard
- **Description:** Central place to manage connected accounts
- **Acceptance Criteria:**
  - List all connected accounts
  - Connection status indicator
  - Disconnect option
  - Re-authenticate option

#### FR-SOC-002: Platform Connection Flows
| Platform | OAuth Flow | Special Requirements |
|----------|------------|---------------------|
| YouTube | Google OAuth | Channel selection |
| Instagram | Meta OAuth | Professional account |
| TikTok | TikTok OAuth | Standard account |
| Facebook | Meta OAuth | Page selection |
| LinkedIn | LinkedIn OAuth | Business page |
| X/Twitter | Twitter OAuth | Standard account |

#### FR-SOC-003: Account Health Monitoring
- **Description:** Monitor connected account status
- **Acceptance Criteria:**
  - Token expiration warnings
  - Re-auth prompts
  - Connection error alerts
  - Auto-reconnect attempts

### 3.2 Multi-Platform Publishing (FR-PUB)

#### FR-PUB-001: Simultaneous Publishing
- **Description:** Post to multiple platforms at once
- **Acceptance Criteria:**
  - Multi-select platforms
  - Single action to post
  - Per-platform status tracking
  - Partial failure handling

#### FR-PUB-002: Platform-Specific Optimization
- **Description:** Optimize content for each platform
- **Acceptance Criteria:**
  - Character limit enforcement
  - Hashtag optimization
  - Aspect ratio adjustment
  - Platform preview

#### FR-PUB-003: Publishing Status
- **Description:** Track publishing status
- **Acceptance Criteria:**
  - In-progress indicator
  - Success confirmation
  - Failure notification
  - Retry option

### 3.3 AI Content Generation (FR-AI)

#### FR-AI-001: Caption Generation
- **Description:** AI generates engaging captions
- **Acceptance Criteria:**
  - Context-aware captions
  - Platform-appropriate length
  - Call-to-action inclusion
  - Editable output

#### FR-AI-002: Hashtag Generation
- **Description:** AI suggests relevant hashtags
- **Acceptance Criteria:**
  - Trending hashtag inclusion
  - Niche-relevant tags
  - Platform-specific format
  - Configurable count

---

## 4. Local Video Upload Requirements

### 4.1 Upload Specifications (FR-UPL)

#### FR-UPL-001: File Upload
- **Description:** Upload local video files
- **Acceptance Criteria:**
  - MP4 format support
  - Up to 200MB file size
  - Progress indicator
  - Resume on failure

#### FR-UPL-002: Direct Schedule
- **Description:** Schedule uploaded videos without clipping
- **Acceptance Criteria:**
  - Upload to calendar directly
  - Set posting time
  - Add caption
  - Select platforms

---

## 5. Analytics Requirements

### 5.1 Post Analytics (FR-ANA)

#### FR-ANA-001: View Metrics
- **Description:** Track post viewership
- **Acceptance Criteria:**
  - View count per post
  - Platform breakdown
  - Time-based trends
  - Comparison views

#### FR-ANA-002: Engagement Metrics
- **Description:** Track post engagement
- **Acceptance Criteria:**
  - Likes/reactions count
  - Comments count
  - Shares/reposts count
  - Engagement rate calculation

#### FR-ANA-003: Unified Dashboard
- **Description:** Single view of all platform analytics
- **Acceptance Criteria:**
  - Cross-platform aggregation
  - Platform filtering
  - Date range selection
  - Export capability

---

## 6. Team Collaboration Requirements

### 6.1 Team Workspace (FR-TEAM)

#### FR-TEAM-001: Workspace Creation
- **Description:** Create team workspace
- **Acceptance Criteria:**
  - Workspace naming
  - Member invitation
  - Role assignment
  - Workspace settings

#### FR-TEAM-002: Member Management
- **Description:** Manage team members
- **Acceptance Criteria:**
  - Invite by email
  - Role assignment (admin, editor, viewer)
  - Remove members
  - Transfer ownership

#### FR-TEAM-003: Shared Projects
- **Description:** Team access to projects
- **Acceptance Criteria:**
  - All members see team projects
  - Collaborative editing
  - Version history
  - Activity log

### 6.2 Brand Templates (FR-BRAND)

#### FR-BRAND-001: Template Creation
- **Description:** Create brand templates
- **Acceptance Criteria:**
  - Up to 5 templates (Pro)
  - Custom fonts
  - Brand colors
  - Logo placement
  - Intro/outro

#### FR-BRAND-002: Template Application
- **Description:** Apply templates to clips
- **Acceptance Criteria:**
  - Template selection dropdown
  - Preview with template
  - Batch apply option
  - Override settings

---

## 7. API Requirements

### 7.1 API Endpoints (FR-API)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/projects` | POST | Create new project |
| `/projects/{id}/clips` | GET | Get generated clips |
| `/brand-templates` | GET | List brand templates |
| `/projects/{id}/share` | POST | Share project |
| `/censor` | POST | Create censor job |
| `/censor/{id}` | GET | Get censor status |

### 7.2 API Limits (NFR-API)

| Limit | Value |
|-------|-------|
| Rate Limit | 30 requests/minute |
| Max Video Duration | 10 hours |
| Max File Size | 30 GB |
| Concurrent Projects | 50 |

### 7.3 Webhook Support (FR-HOOK)

#### FR-HOOK-001: Event Notifications
- **Description:** Real-time event callbacks
- **Acceptance Criteria:**
  - Project completion events
  - Clip ready events
  - Error notifications
  - Retry on failure

---

## 8. Non-Functional Requirements

### 8.1 Performance (NFR-PERF)

| Metric | Target |
|--------|--------|
| Calendar Load Time | < 2 seconds |
| Post Schedule Time | < 1 second |
| Bulk Schedule (50 clips) | < 5 seconds |
| Platform Publish Time | < 30 seconds |

### 8.2 Reliability (NFR-REL)

| Metric | Target |
|--------|--------|
| Scheduled Post Success Rate | > 99% |
| Platform Connection Uptime | > 99.5% |
| API Availability | > 99.9% |
| Data Durability | > 99.99% |

### 8.3 Scalability (NFR-SCALE)

| Metric | Current Capacity |
|--------|------------------|
| Concurrent Users | 100K+ |
| Daily Posts | 1M+ |
| Stored Projects | 10M+ |
| API Requests/Day | 10M+ |

---

## 9. User Flows

### 9.1 Single Post Scheduling Flow
```
1. User generates clips from long video
2. User selects clip to schedule
3. User clicks "Schedule" button
4. User selects target platform(s)
5. User sets date and time
6. User reviews/edits caption
7. User confirms schedule
8. Post appears in calendar
9. System publishes at scheduled time
```

### 9.2 Bulk Scheduling Flow
```
1. User generates clips from long video
2. User clicks "Select" mode
3. User checks multiple clips (or Select All)
4. User clicks "Bulk Schedule"
5. User sets posting order
6. User sets start date/time
7. User sets posting frequency
8. AI generates captions/hashtags
9. User reviews schedule preview
10. User confirms bulk schedule
11. All posts appear in calendar
12. System publishes according to schedule
```

### 9.3 Calendar Management Flow
```
1. User opens Calendar view
2. User sees monthly overview of posts
3. User clicks on scheduled post
4. User can: View details, Edit, Reschedule, Delete
5. User drags post to new date (reschedule)
6. System updates schedule
```

---

## 10. Competitive Advantages

### 10.1 Key Differentiators
1. **AI-First Approach:** Every feature powered by AI
2. **End-to-End Solution:** Clip, edit, schedule, publish, analyze
3. **Bulk Operations:** Schedule months of content quickly
4. **ClipAnything:** Only AI that clips any video type
5. **12M+ Users:** Proven at scale

### 10.2 Market Position
- **#1 AI Video Clipping Tool**
- **Used by top creators** (Logan Paul, Mark Rober, etc.)
- **Enterprise-ready** (API, team features)

---

**Document Version:** 1.0
**Last Updated:** December 8, 2025
