# PRD: Link-in-Bio / Start Page

**Version:** 1.0  
**Date:** January 19, 2026  
**Status:** Proposed  
**Priority:** High  
**Estimated Effort:** 2 weeks

---

## Executive Summary

MediaPoster needs a Link-in-Bio feature to compete with Buffer's Start Page and Later's Linkin.bio. This feature allows creators to create a single, customizable landing page that consolidates all their important links, integrates with scheduled content, and provides click analytics.

---

## Problem Statement

### Current State
- Users must use third-party tools (Linktree, Beacons, etc.) for link-in-bio
- No integration between scheduled posts and bio links
- No click tracking or analytics for bio links
- Users manage multiple tools instead of one unified platform

### Competitive Gap

| Competitor | Feature | MediaPoster |
|------------|---------|-------------|
| Buffer | Start Page with custom domains | ❌ None |
| Later | Linkin.bio with shoppable posts | ❌ None |
| Linktree | Dedicated link-in-bio tool | ❌ None |

### User Pain Points
1. Managing separate link-in-bio tools
2. No analytics on which links perform best
3. Manual updates when content changes
4. No connection between posts and landing pages

---

## Goals & Success Metrics

### Goals
1. Provide native link-in-bio functionality within MediaPoster
2. Integrate bio links with scheduled content
3. Offer click analytics and conversion tracking
4. Enable custom branding and themes

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User adoption | 60% of active users | % users with active Start Page |
| Click-through rate | > 5% | Total clicks / Total page views |
| Link additions | 5+ links per page | Average links per Start Page |
| Page views | 1000+ per active page/month | Analytics tracking |

---

## Features

### Phase 1: Core Start Page (Week 1)

#### 1.1 Page Builder
- **Drag-and-drop link ordering**
- **Link types:**
  - Standard URL link
  - Social profile links (auto-icon detection)
  - Email link
  - Phone link
  - Embedded content (YouTube, Spotify)
- **Link customization:**
  - Custom title
  - Description (optional)
  - Thumbnail/icon
  - Scheduled visibility (show/hide at specific times)

#### 1.2 Themes & Branding
- **Pre-built themes:** 10+ modern templates
- **Custom branding:**
  - Profile photo/logo
  - Bio text (160 chars)
  - Background color/gradient/image
  - Button styles (rounded, square, pill)
  - Font selection (5 options)
  - Custom CSS (pro feature)

#### 1.3 URL Structure
- **Default:** `mediaposter.app/u/{username}`
- **Custom subdomain:** `{username}.mediaposter.app` (Pro)
- **Custom domain:** `links.yourdomain.com` (Business)

### Phase 2: Analytics & Integration (Week 2)

#### 2.1 Click Analytics
- **Per-link metrics:**
  - Total clicks
  - Unique clicks
  - Click-through rate
  - Traffic sources (referrer)
  - Geographic distribution
  - Device breakdown (mobile/desktop)
- **Time-based views:**
  - Hourly heatmap
  - Daily/weekly/monthly trends
  - Best performing times

#### 2.2 UTM Parameter Management
- **Auto-generated UTMs:**
  - `utm_source=mediaposter`
  - `utm_medium=linkinbio`
  - `utm_campaign={link_name}`
- **Custom UTM override per link**
- **UTM templates for consistent tracking**

#### 2.3 Post Integration
- **Recent posts widget:** Show latest 3-6 scheduled/published posts
- **Clickable post thumbnails:** Link to original content
- **Auto-update:** Syncs with publishing calendar
- **Shoppable posts:** Link posts to product pages (Later-style)

#### 2.4 Social Proof Widgets
- **Follower counts:** Display across platforms
- **Latest engagement stats**
- **Testimonials/quotes section**

---

## Technical Architecture

### Database Schema

```sql
-- Start Page table
CREATE TABLE start_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(100),
    bio TEXT,
    profile_image_url TEXT,
    theme_id UUID REFERENCES start_page_themes(id),
    custom_css TEXT,
    custom_domain VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Links table
CREATE TABLE start_page_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES start_pages(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    icon_url TEXT,
    link_type VARCHAR(20) DEFAULT 'url', -- url, social, email, phone, embed
    position INTEGER NOT NULL,
    is_visible BOOLEAN DEFAULT true,
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Click tracking table
CREATE TABLE start_page_clicks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    link_id UUID REFERENCES start_page_links(id) ON DELETE CASCADE,
    page_id UUID REFERENCES start_pages(id) ON DELETE CASCADE,
    clicked_at TIMESTAMPTZ DEFAULT NOW(),
    referrer TEXT,
    user_agent TEXT,
    ip_hash VARCHAR(64), -- Hashed for privacy
    country VARCHAR(2),
    city VARCHAR(100),
    device_type VARCHAR(20), -- mobile, desktop, tablet
    is_unique BOOLEAN DEFAULT true
);

-- Page views table
CREATE TABLE start_page_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES start_pages(id) ON DELETE CASCADE,
    viewed_at TIMESTAMPTZ DEFAULT NOW(),
    referrer TEXT,
    user_agent TEXT,
    ip_hash VARCHAR(64),
    country VARCHAR(2),
    device_type VARCHAR(20)
);

-- Themes table
CREATE TABLE start_page_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    preview_url TEXT,
    background_type VARCHAR(20), -- color, gradient, image
    background_value TEXT,
    button_style VARCHAR(20), -- rounded, square, pill
    font_family VARCHAR(50),
    primary_color VARCHAR(7),
    secondary_color VARCHAR(7),
    is_premium BOOLEAN DEFAULT false
);
```

### API Endpoints

```
# Page Management
POST   /api/start-page                    # Create new Start Page
GET    /api/start-page/{username}         # Get page by username (public)
GET    /api/start-page/me                 # Get current user's page
PUT    /api/start-page/me                 # Update page settings
DELETE /api/start-page/me                 # Delete page

# Link Management
POST   /api/start-page/links              # Add new link
GET    /api/start-page/links              # List all links
PUT    /api/start-page/links/{id}         # Update link
DELETE /api/start-page/links/{id}         # Delete link
PUT    /api/start-page/links/reorder      # Reorder links

# Analytics
GET    /api/start-page/analytics/overview # Overview stats
GET    /api/start-page/analytics/clicks   # Click details
GET    /api/start-page/analytics/views    # Page view details
GET    /api/start-page/analytics/links/{id} # Per-link stats

# Themes
GET    /api/start-page/themes             # List available themes
POST   /api/start-page/themes/preview     # Preview theme

# Public (no auth)
GET    /u/{username}                      # Render public page
POST   /api/start-page/track/click        # Track click (fire-and-forget)
POST   /api/start-page/track/view         # Track page view
```

### File Structure

```
Backend/
├── services/
│   └── start_page/
│       ├── __init__.py
│       ├── page_service.py          # Page CRUD operations
│       ├── link_service.py          # Link management
│       ├── analytics_service.py     # Click/view tracking
│       ├── theme_service.py         # Theme management
│       └── utm_generator.py         # UTM parameter generation
├── api/
│   └── endpoints/
│       └── start_page_api.py        # API routes

dashboard/
├── app/
│   └── (dashboard)/
│       └── start-page/
│           ├── page.tsx             # Main editor
│           ├── analytics/
│           │   └── page.tsx         # Analytics dashboard
│           └── preview/
│               └── page.tsx         # Live preview
├── components/
│   └── start-page/
│       ├── LinkEditor.tsx           # Link form component
│       ├── ThemeSelector.tsx        # Theme picker
│       ├── LinkList.tsx             # Draggable link list
│       ├── AnalyticsCard.tsx        # Stats display
│       └── PagePreview.tsx          # Live preview component
```

---

## User Interface

### Page Editor (Dashboard)
```
┌─────────────────────────────────────────────────────────────┐
│  Start Page Editor                              [Preview] [Save] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌────────────────────────────────┐   │
│  │                  │  │  Profile                        │   │
│  │   Live Preview   │  │  ┌─────┐                        │   │
│  │                  │  │  │ IMG │  @username              │   │
│  │   ┌─────────┐    │  │  └─────┘  Your bio text here... │   │
│  │   │  Photo  │    │  │                                  │   │
│  │   └─────────┘    │  ├────────────────────────────────┤   │
│  │   @username      │  │  Links                          │   │
│  │   Bio text...    │  │  ☰ My Website        [Edit] [×] │   │
│  │                  │  │  ☰ Latest Video      [Edit] [×] │   │
│  │  ┌────────────┐  │  │  ☰ Shop My Products  [Edit] [×] │   │
│  │  │ My Website │  │  │                                  │   │
│  │  └────────────┘  │  │  [+ Add New Link]               │   │
│  │  ┌────────────┐  │  │                                  │   │
│  │  │Latest Video│  │  ├────────────────────────────────┤   │
│  │  └────────────┘  │  │  Theme                          │   │
│  │                  │  │  [Minimal] [Dark] [Gradient]... │   │
│  └──────────────────┘  └────────────────────────────────┘   │
│                                                               │
│  Your URL: mediaposter.app/u/username    [Copy] [QR Code]    │
└─────────────────────────────────────────────────────────────┘
```

### Analytics Dashboard
```
┌─────────────────────────────────────────────────────────────┐
│  Start Page Analytics                    Last 30 days [▼]    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Views   │  │  Clicks  │  │   CTR    │  │ Unique   │     │
│  │  12,450  │  │   1,847  │  │  14.8%   │  │  8,230   │     │
│  │  +23%    │  │  +18%    │  │  +2.1%   │  │  +15%    │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Click Trends                                        │    │
│  │  📈 [Line chart showing clicks over time]            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  Top Performing Links                                        │
│  ┌────────────────────────────────────────────────────┐     │
│  │  1. Shop My Products    │  847 clicks  │  45.8%   │     │
│  │  2. Latest Video        │  523 clicks  │  28.3%   │     │
│  │  3. My Website          │  312 clicks  │  16.9%   │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Timeline

### Week 1: Core Functionality
| Day | Task |
|-----|------|
| 1 | Database migrations, service scaffolding |
| 2 | Page CRUD API endpoints |
| 3 | Link management API endpoints |
| 4 | Frontend page editor UI |
| 5 | Theme system and preview |

### Week 2: Analytics & Polish
| Day | Task |
|-----|------|
| 6 | Click/view tracking implementation |
| 7 | Analytics API and dashboard |
| 8 | UTM generation and post integration |
| 9 | Public page rendering (SSR) |
| 10 | Testing, bug fixes, documentation |

---

## Dependencies

- **Supabase:** Database and real-time subscriptions
- **Next.js:** SSR for public pages (SEO)
- **dnd-kit:** Drag-and-drop for link reordering
- **QR Code library:** Generate shareable QR codes
- **GeoIP service:** Country detection for analytics

---

## Future Enhancements (Post-MVP)

1. **Custom domains:** Full CNAME support
2. **E-commerce integration:** Stripe checkout links
3. **Email capture:** Newsletter signup forms
4. **A/B testing:** Test different link orders/titles
5. **Scheduling:** Time-based link visibility
6. **Team pages:** Multi-user organization pages

---

## Appendix: Competitor Feature Comparison

| Feature | Buffer Start Page | Later Linkin.bio | MediaPoster (Proposed) |
|---------|-------------------|------------------|------------------------|
| Custom URL | ✅ | ✅ | ✅ |
| Custom domain | ✅ Pro | ✅ Pro | ✅ Business |
| Click analytics | ✅ | ✅ | ✅ |
| Themes | ✅ 10+ | ✅ 15+ | ✅ 10+ |
| Post integration | ❌ | ✅ Shoppable | ✅ Recent posts |
| UTM tracking | ✅ | ✅ | ✅ |
| QR codes | ❌ | ✅ | ✅ |
| Scheduling | ❌ | ❌ | ✅ |
| Custom CSS | ❌ | ❌ | ✅ Pro |

---

**Document Owner:** Product Team  
**Last Updated:** January 19, 2026  
**Next Review:** February 2026
