# Planoly Product Requirements Document (PRD)

**Comprehensive Product Analysis for Competitive Reference**

---

## 1. Product Overview

### 1.1 Product Vision
Planoly positions itself as "The first Instagram planning grid" with the tagline "Turn your 5 to 9 into your 9 to 5." The platform focuses on visual content planning for creators who want to build their personal brand and monetize their following.

### 1.2 Core Value Proposition
- **Visual-First:** Instagram grid preview and aesthetic planning
- **Creator Economy:** Built-in e-commerce via Creator Store
- **Simplicity:** Easy-to-use, creator-friendly interface
- **All-in-One:** Social planning + product selling

### 1.3 Product Lines
1. **Social Planner** - Content scheduling and visual planning
2. **Creator Store** - E-commerce and link-in-bio

---

## 2. Module Requirements

### 2.1 VISUAL PLANNING Module

#### FR-VIS-001: Instagram Grid Preview
- **Description:** Preview Instagram feed before posting
- **Acceptance Criteria:**
  - Show 9+ post grid preview
  - Real-time updates as posts added
  - Match actual Instagram grid layout
  - Display scheduled and draft posts

#### FR-VIS-002: Drag-and-Drop Rearrangement
- **Description:** Reorder posts by dragging
- **Acceptance Criteria:**
  - Drag posts to new positions
  - Visual feedback during drag
  - Auto-update preview
  - Work on calendar and grid views

#### FR-VIS-003: Multiple View Modes
- **Description:** Switch between viewing modes
- **View Types:**
  - List View: Linear content list
  - Grid View: Instagram-style grid
  - Gallery View: Visual content gallery
  - Calendar View: Monthly schedule
- **Acceptance Criteria:**
  - One-click view switching
  - Persist user preference
  - Responsive on all screen sizes

#### FR-VIS-004: Placeholders
- **Description:** Set content placeholders on calendar
- **Acceptance Criteria:**
  - Create recurring placeholders
  - Custom colors per placeholder type
  - Convert to draft when ready
  - Track content pillars

### 2.2 SCHEDULING Module

#### FR-SCH-001: Multi-Platform Auto-Post
- **Description:** Automatically publish to all platforms
- **Platforms:** Instagram, TikTok, Facebook, YouTube, Threads, X, LinkedIn, Pinterest, Amazon
- **Acceptance Criteria:**
  - Toggle auto-post per post
  - Support images, videos, carousels
  - Fallback to reminder for unsupported
  - Queue management

#### FR-SCH-002: Content Calendar
- **Description:** Visual monthly content calendar
- **Acceptance Criteria:**
  - Month/week view
  - Holiday integration
  - Weekly trends display
  - Calendar notes
  - Color customization
  - Drag scheduling

#### FR-SCH-003: Post Previews
- **Description:** Preview posts per channel
- **Acceptance Criteria:**
  - Show how post looks on each platform
  - Character count validation
  - Media preview
  - Caption preview

#### FR-SCH-004: Trends & Holidays
- **Description:** Show trending content and holidays
- **Acceptance Criteria:**
  - Display upcoming holidays
  - Weekly trend suggestions
  - Content ideas per trend
  - One-click add to calendar

### 2.3 CONTENT CREATION Module

#### FR-CRE-001: Media Library
- **Description:** Store and organize content
- **Acceptance Criteria:**
  - Upload images and videos
  - Organize with folders/tags
  - Search functionality
  - Drag to calendar

#### FR-CRE-002: Stock Imagery (Dupe)
- **Description:** Access curated stock photos
- **Acceptance Criteria:**
  - Browse by aesthetic category
  - Preview before adding
  - Video stock included
  - Creator-focused imagery

#### FR-CRE-003: Canva Integration
- **Description:** Edit with Canva in-app
- **Acceptance Criteria:**
  - Direct upload from Canva
  - Edit without leaving app
  - No download required
  - Full Canva tools access

#### FR-CRE-004: AI Caption Writer
- **Description:** Generate captions with AI
- **Acceptance Criteria:**
  - Multiple voice options
  - Brand voice matching
  - Customizable tone
  - Generate variations

#### FR-CRE-005: Image/Video Editing
- **Description:** Basic media editing
- **Acceptance Criteria:**
  - Crop and resize
  - Filters and adjustments
  - Text overlays
  - In-app editing

### 2.4 HASHTAG Module

#### FR-HASH-001: Hashtag Manager
- **Description:** Save and organize hashtags
- **Acceptance Criteria:**
  - Create hashtag groups
  - Name and categorize groups
  - One-click insert into posts
  - Track hashtag usage

#### FR-HASH-002: Hashtag Suggestions
- **Description:** AI-powered hashtag recommendations
- **Acceptance Criteria:**
  - Suggest relevant hashtags
  - Based on content
  - Trending tag inclusion
  - Platform-specific tags

### 2.5 INSTAGRAM FEATURES

#### FR-IG-001: Product Tagging
- **Description:** Tag products in Instagram posts
- **Acceptance Criteria:**
  - Connect to Instagram Shop
  - Tag multiple products
  - Shoppable post creation
  - Track product clicks

#### FR-IG-002: Location Tagging
- **Description:** Add location to posts
- **Acceptance Criteria:**
  - Search locations
  - Add to post
  - Location in preview
  - Increase discoverability

#### FR-IG-003: First Comment
- **Description:** Auto-post first comment
- **Acceptance Criteria:**
  - Add first comment with hashtags
  - Schedule with post
  - Keep caption clean
  - Auto-publish comment

### 2.6 CREATOR STORE Module

#### FR-CS-001: Storefront Builder
- **Description:** Build e-commerce storefront
- **Acceptance Criteria:**
  - No-code builder
  - Template selection
  - Custom branding
  - Custom domain support
  - Mobile-optimized

#### FR-CS-002: Product Management
- **Description:** Create and sell products
- **Product Types:**
  - Digital downloads
  - E-courses
  - 1:1 sessions
  - Physical merch (Printful)
  - Events
- **Acceptance Criteria:**
  - Unlimited products
  - Pricing flexibility
  - Product descriptions
  - Media uploads

#### FR-CS-003: Payment Processing
- **Description:** Accept payments
- **Acceptance Criteria:**
  - Stripe integration
  - PayPal integration
  - Zero transaction fees
  - Instant access to funds

#### FR-CS-004: Link in Bio
- **Description:** Customizable link page
- **Acceptance Criteria:**
  - Unlimited links
  - Custom design
  - Link shortener
  - Mobile-optimized

#### FR-CS-005: Email Marketing
- **Description:** Customer communication
- **Acceptance Criteria:**
  - Build email list
  - Segment contacts
  - Automated sequences
  - Campaign sends
  - CRM (Pro Plus)

### 2.7 ANALYTICS Module

#### FR-ANA-001: Post Analytics
- **Description:** Individual post performance
- **Acceptance Criteria:**
  - Engagement rate
  - Impressions
  - Video plays
  - Comments/likes

#### FR-ANA-002: Profile Analytics
- **Description:** Account-level metrics
- **Acceptance Criteria:**
  - Follower growth
  - Profile views
  - Demographics
  - Best posting times

### 2.8 TEAM Module

#### FR-TEAM-001: User Management
- **Description:** Add team members
- **Acceptance Criteria:**
  - Invite by email
  - Role assignment
  - Permission levels
  - Remove access

---

## 3. Non-Functional Requirements

### 3.1 Scalability

| Plan | Social Sets | Uploads | Users |
|------|-------------|---------|-------|
| Starter | 1 | 60/month | 1 |
| Growth | 1 | Unlimited | 3 |
| Pro | 2 | Unlimited | 6 |

### 3.2 Platform Support
- Web application
- iOS mobile app
- Android mobile app

---

## 4. User Flows

### 4.1 Plan Instagram Grid
```
1. User opens Grid View
2. User sees current scheduled posts
3. User drags media to grid
4. User rearranges for aesthetic
5. User previews final grid
6. User schedules posts
7. Posts appear in calendar
```

### 4.2 Auto-Post Content
```
1. User creates post
2. User selects platforms
3. User writes caption (or uses AI)
4. User sets date/time
5. User toggles auto-post ON
6. System publishes at scheduled time
```

### 4.3 Sell Digital Product
```
1. User opens Creator Store
2. User clicks "Add Product"
3. User selects product type
4. User uploads content/sets details
5. User sets price
6. User publishes to storefront
7. Customer purchases
8. Customer receives download
```

---

## 5. Pricing Model

### 5.1 Social Planner

| Plan | Monthly | Annual | Features |
|------|---------|--------|----------|
| Starter | $16 | $14/mo | 60 uploads, 1 user |
| Growth | $28 | $24/mo | Unlimited, 3 users |
| Pro | $43 | $37/mo | 2 social sets, 6 users |

### 5.2 Creator Store

| Plan | Monthly | Annual | Features |
|------|---------|--------|----------|
| Pro | $20 | $16/mo | Full store, automation |
| Pro Plus | $54 | $42/mo | CRM, unlimited emails |

---

## 6. Competitive Positioning

### 6.1 Key Differentiators
1. **First Instagram Grid Planner:** Pioneer in visual planning
2. **Creator Store Integration:** E-commerce built-in
3. **Aesthetic Stock Photos:** Dupe integration
4. **Zero Transaction Fees:** Keep 100% of revenue
5. **Printful Integration:** Merch without inventory

### 6.2 Target Segments

| Segment | Primary Need | Planoly Solution |
|---------|--------------|------------------|
| Instagram Creators | Grid aesthetics | Visual Planner |
| Side Hustlers | Monetization | Creator Store |
| Small Brands | Social presence | Auto-posting |
| Entrepreneurs | Product sales | E-commerce |

---

## 7. Limitations

### 7.1 Analytics
- No hashtag analytics
- No link-in-bio analytics
- Basic compared to Later

### 7.2 Social Listening
- No brand monitoring
- No sentiment analysis
- No competitor tracking

### 7.3 Advanced Features
- No AI video creation
- No predictive analytics
- Limited team features

---

**Document Version:** 1.0
**Last Updated:** December 8, 2025
