# PRD: Frontend Consistency & Design System

**Version:** 1.0  
**Date:** January 20, 2026  
**Status:** Audit Complete, Implementation Pending  
**Priority:** High  
**Estimated Effort:** 2-3 weeks

---

## Executive Summary

This PRD documents a comprehensive audit of the MediaPoster frontend (Next.js dashboard) and defines a unified design system to ensure visual and functional consistency across all 50+ pages. The goal is to establish reusable components, standardized patterns, and a cohesive user experience.

---

## Current State Audit

### Dashboard Structure

| Category | Count | Status |
|----------|-------|--------|
| **Total Pages** | 50+ | Many pages |
| **Shared Components** | 18 | Needs expansion |
| **Global CSS Classes** | 40+ | Well-defined |
| **Tailwind Usage** | Extensive | Inconsistent patterns |

### Pages Inventory

```
dashboard/app/(dashboard)/
├── accounts/              # Account management
├── agent-architecture/    # System architecture view
├── agent-panel/           # Agent control panel
├── ai-chat/               # AI conversation interface
├── ai-generations/        # AI-generated content
├── analytics/             # Analytics dashboard
├── analytics-compare/     # Compare analytics
├── api-usage/             # API usage metrics
├── approval-queue/        # Content approval
├── automation/            # Automation center
├── blotato/               # Blotato integration
├── briefs/                # Content briefs
├── carousel-creator/      # Carousel builder
├── channel-analyzer/      # Channel analysis
├── coaching/              # Creator coaching
├── comment-automation/    # Comment automation
├── comments/              # Comment management
├── competitors/           # Competitor research
├── content-calendar/      # Calendar view
├── content-growth/        # Growth metrics
├── content-ops/           # Content operations
├── content-performance/   # Performance metrics
├── content-pipeline/      # Pipeline status
├── content-planner/       # Content planning
├── curate/                # Content curation
├── derivatives/           # Derivative content
├── experiments/           # A/B experiments
├── followers/             # Follower analytics
├── formats/               # Content formats
├── goals/                 # Goals tracking
├── ... (20+ more pages)
└── page.tsx               # Dashboard home
```

### Existing Components

| Component | Location | Purpose | Reused |
|-----------|----------|---------|--------|
| `Sidebar` | `components/Sidebar.tsx` | Navigation | ✅ All pages |
| `VideoThumbnail` | `components/VideoThumbnail.tsx` | Video preview | ✅ Many |
| `MediaThumbnail` | `components/MediaThumbnail.tsx` | Media preview | ✅ Many |
| `ContentGrowthCard` | `components/ContentGrowthCard.tsx` | Metrics card | ⚠️ Some |
| `ProcessingStatus` | `components/ProcessingStatus.tsx` | Status indicator | ⚠️ Some |
| `AnalysisTerminal` | `components/AnalysisTerminal.tsx` | Log display | ⚠️ Few |
| `BackendStatus` | `components/BackendStatus.tsx` | API status | ⚠️ Few |
| `SleepStatus` | `components/SleepStatus.tsx` | Sleep mode | ⚠️ Few |
| `ToastNotifications` | `components/ToastNotifications.tsx` | Alerts | ⚠️ Few |
| `LineChart` | `components/LineChart.tsx` | Charts | ⚠️ Few |

---

## Identified Inconsistencies

### 1. Color Usage

**Issue:** Different shades of zinc/gray used inconsistently across pages.

```tsx
// Page A: Uses bg-zinc-900
<div className="bg-zinc-900 rounded-xl p-4">

// Page B: Uses bg-zinc-800
<div className="bg-zinc-800 rounded-lg p-6">

// Page C: Uses bg-gray-900
<div className="bg-gray-900 rounded-2xl p-5">
```

**Recommendation:** Standardize to zinc palette with defined levels:
- `bg-zinc-950` - Page background
- `bg-zinc-900` - Card background
- `bg-zinc-800` - Elevated elements
- `bg-zinc-700` - Hover states
- `border-zinc-800` - Borders

### 2. Border Radius

**Issue:** Inconsistent border radius values.

```tsx
// Various pages use:
rounded-lg    // 8px
rounded-xl    // 12px
rounded-2xl   // 16px
rounded-md    // 6px
```

**Recommendation:** Standardize:
- `rounded-lg` (8px) - Small elements (buttons, badges)
- `rounded-xl` (12px) - Cards, modals
- `rounded-2xl` (16px) - Large containers only

### 3. Spacing & Padding

**Issue:** Inconsistent padding in cards and containers.

```tsx
// Various values used:
p-4, p-5, p-6, p-8, px-4, py-3, etc.
```

**Recommendation:** Standardize card padding:
- Small cards: `p-4`
- Medium cards: `p-6`
- Large sections: `p-8`

### 4. Typography

**Issue:** Font sizes and weights vary without pattern.

**Recommendation:**
- Page titles: `text-2xl font-bold`
- Section headers: `text-lg font-semibold`
- Card titles: `text-base font-medium`
- Body text: `text-sm text-zinc-400`
- Labels: `text-xs text-zinc-500`

### 5. Button Styles

**Issue:** Buttons styled inline differently across pages.

**Recommendation:** Create button component variants:

```tsx
// Primary action
<Button variant="primary">Save</Button>
// bg-violet-600 hover:bg-violet-700

// Secondary action  
<Button variant="secondary">Cancel</Button>
// bg-zinc-800 hover:bg-zinc-700

// Destructive action
<Button variant="danger">Delete</Button>
// bg-red-600 hover:bg-red-700

// Ghost/subtle
<Button variant="ghost">More</Button>
// hover:bg-zinc-800
```

### 6. Status Indicators

**Issue:** Status shown with different colors/icons across pages.

```tsx
// Page A
<span className="text-green-500">✓ Active</span>

// Page B
<div className="bg-green-500/20 text-green-400 px-2 py-1 rounded">Active</div>

// Page C
<span className="text-emerald-400">● Online</span>
```

**Recommendation:** Create `StatusBadge` component:

```tsx
<StatusBadge status="success">Active</StatusBadge>
<StatusBadge status="warning">Pending</StatusBadge>
<StatusBadge status="error">Failed</StatusBadge>
<StatusBadge status="info">Processing</StatusBadge>
```

### 7. Platform Icons/Colors

**Issue:** Platform icons defined in multiple places.

```tsx
// analytics/page.tsx
const platformConfig = {
  youtube: { icon: '▶️', color: 'bg-red-500' },
  instagram: { icon: '📸', color: 'bg-gradient-to-r from-purple-500 to-pink-500' },
  ...
};

// schedule/page.tsx
const platformColors = {
  tiktok: 'bg-pink-500',
  instagram: 'bg-purple-500',
  youtube: 'bg-red-500',
};
```

**Recommendation:** Centralize in `lib/constants/platforms.ts`:

```tsx
export const PLATFORMS = {
  youtube: {
    name: 'YouTube',
    icon: Youtube, // Lucide icon
    emoji: '▶️',
    color: 'bg-red-500',
    textColor: 'text-red-500',
    gradient: 'from-red-500 to-red-600'
  },
  // ... all platforms
};
```

### 8. Loading States

**Issue:** Different loading indicators used.

```tsx
// Some pages
{loading && <p>Loading...</p>}

// Other pages
{loading && <div className="animate-spin">⟳</div>}

// Others
{loading && <Spinner />}
```

**Recommendation:** Create unified `LoadingState` component:

```tsx
<LoadingState>Loading analytics...</LoadingState>
<LoadingState variant="skeleton" count={3} />
<LoadingState variant="spinner" size="lg" />
```

### 9. Empty States

**Issue:** Empty states handled differently.

**Recommendation:** Create `EmptyState` component:

```tsx
<EmptyState
  icon={<VideoIcon />}
  title="No videos yet"
  description="Upload your first video to get started"
  action={<Button>Upload Video</Button>}
/>
```

### 10. Error States

**Issue:** Errors displayed inconsistently.

**Recommendation:** Create `ErrorState` component:

```tsx
<ErrorState
  title="Failed to load data"
  message={error.message}
  onRetry={() => refetch()}
/>
```

---

## Design System Specification

### Color Palette

```css
/* Background Levels */
--bg-base: #09090b;        /* zinc-950 - page bg */
--bg-elevated: #18181b;    /* zinc-900 - cards */
--bg-hover: #27272a;       /* zinc-800 - hover */
--bg-active: #3f3f46;      /* zinc-700 - active */

/* Text Colors */
--text-primary: #fafafa;   /* zinc-50 */
--text-secondary: #a1a1aa; /* zinc-400 */
--text-muted: #71717a;     /* zinc-500 */

/* Brand Colors */
--brand-primary: #8b5cf6;  /* violet-500 */
--brand-secondary: #6366f1; /* indigo-500 */

/* Status Colors */
--status-success: #22c55e; /* green-500 */
--status-warning: #f59e0b; /* amber-500 */
--status-error: #ef4444;   /* red-500 */
--status-info: #3b82f6;    /* blue-500 */

/* Platform Colors */
--platform-youtube: #ef4444;
--platform-instagram: #e879f9;
--platform-tiktok: #000000;
--platform-twitter: #3f3f46;
--platform-threads: #27272a;
--platform-linkedin: #2563eb;
--platform-pinterest: #dc2626;
```

### Typography Scale

```css
/* Headings */
.text-page-title { @apply text-2xl font-bold text-white; }
.text-section-title { @apply text-lg font-semibold text-white; }
.text-card-title { @apply text-base font-medium text-white; }

/* Body */
.text-body { @apply text-sm text-zinc-300; }
.text-body-secondary { @apply text-sm text-zinc-400; }

/* Labels & Captions */
.text-label { @apply text-xs font-medium text-zinc-400 uppercase tracking-wide; }
.text-caption { @apply text-xs text-zinc-500; }
```

### Spacing System

```css
/* Consistent spacing */
--space-page: 2rem;        /* 32px - page padding */
--space-section: 1.5rem;   /* 24px - between sections */
--space-card: 1rem;        /* 16px - inside cards */
--space-element: 0.5rem;   /* 8px - between elements */
```

### Component Library

#### Required New Components

| Component | Purpose | Priority |
|-----------|---------|----------|
| `Button` | Standardized buttons with variants | High |
| `Card` | Consistent card container | High |
| `StatusBadge` | Status indicators | High |
| `LoadingState` | Loading placeholders | High |
| `EmptyState` | Empty data states | High |
| `ErrorState` | Error displays | High |
| `PageHeader` | Consistent page headers | High |
| `DataTable` | Standardized tables | Medium |
| `Modal` | Modal dialogs | Medium |
| `Dropdown` | Dropdown menus | Medium |
| `Tabs` | Tab navigation | Medium |
| `Input` | Form inputs | Medium |
| `Select` | Form selects | Medium |
| `Tooltip` | Tooltips | Low |
| `Avatar` | User/account avatars | Low |
| `Progress` | Progress bars | Low |

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

#### Day 1-2: Create Core Components

```
dashboard/components/ui/
├── Button.tsx
├── Card.tsx
├── StatusBadge.tsx
├── LoadingState.tsx
├── EmptyState.tsx
├── ErrorState.tsx
└── index.ts
```

#### Day 3: Create Constants

```
dashboard/lib/constants/
├── platforms.ts     # Platform configs
├── colors.ts        # Color tokens
└── typography.ts    # Text styles
```

#### Day 4-5: Create Page Layout Components

```
dashboard/components/layout/
├── PageHeader.tsx
├── PageContainer.tsx
├── Section.tsx
└── SectionHeader.tsx
```

### Phase 2: Migration (Week 2)

#### Priority Pages (High Traffic)

1. **Dashboard Home** (`/`)
2. **Analytics** (`/analytics`)
3. **Media Library** (`/media`)
4. **Schedule** (`/schedule`)
5. **Automation** (`/automation`)

#### Secondary Pages

6-15. Migrate remaining high-value pages

### Phase 3: Completion (Week 3)

#### Remaining Pages

16-50. Migrate all remaining pages

#### Documentation

- Component storybook or documentation
- Usage guidelines
- Code examples

---

## Component Specifications

### Button Component

```tsx
// dashboard/components/ui/Button.tsx

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
  onClick?: () => void;
}

const variants = {
  primary: 'bg-violet-600 hover:bg-violet-700 text-white',
  secondary: 'bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border border-zinc-700',
  danger: 'bg-red-600 hover:bg-red-700 text-white',
  ghost: 'hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100'
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base'
};
```

### Card Component

```tsx
// dashboard/components/ui/Card.tsx

interface CardProps {
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  padding?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

export function Card({ title, subtitle, action, padding = 'md', children }: CardProps) {
  const paddingClasses = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  };
  
  return (
    <div className={`bg-zinc-900 border border-zinc-800 rounded-xl ${paddingClasses[padding]}`}>
      {(title || action) && (
        <div className="flex items-center justify-between mb-4">
          <div>
            {title && <h3 className="text-base font-medium text-white">{title}</h3>}
            {subtitle && <p className="text-sm text-zinc-400 mt-1">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
```

### PageHeader Component

```tsx
// dashboard/components/layout/PageHeader.tsx

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumbs?: { label: string; href?: string }[];
}

export function PageHeader({ title, description, actions, breadcrumbs }: PageHeaderProps) {
  return (
    <div className="mb-8">
      {breadcrumbs && (
        <nav className="text-sm text-zinc-500 mb-2">
          {breadcrumbs.map((crumb, i) => (
            <span key={i}>
              {crumb.href ? <Link href={crumb.href}>{crumb.label}</Link> : crumb.label}
              {i < breadcrumbs.length - 1 && ' / '}
            </span>
          ))}
        </nav>
      )}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          {description && <p className="text-zinc-400 mt-1">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
```

### StatusBadge Component

```tsx
// dashboard/components/ui/StatusBadge.tsx

type Status = 'success' | 'warning' | 'error' | 'info' | 'neutral';

interface StatusBadgeProps {
  status: Status;
  children: React.ReactNode;
  dot?: boolean;
}

const statusStyles = {
  success: 'bg-green-500/20 text-green-400 border-green-500/30',
  warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  error: 'bg-red-500/20 text-red-400 border-red-500/30',
  info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  neutral: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
};

export function StatusBadge({ status, children, dot = true }: StatusBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium border ${statusStyles[status]}`}>
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
```

---

## Page Template

All pages should follow this structure:

```tsx
'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

export default function ExamplePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Data fetching...

  if (loading) return <LoadingState>Loading data...</LoadingState>;
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No data" />;

  return (
    <div className="p-6">
      <PageHeader 
        title="Page Title"
        description="Brief description of this page"
        actions={<Button variant="primary">Action</Button>}
      />
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card title="Section 1">
          {/* Content */}
        </Card>
        <Card title="Section 2">
          {/* Content */}
        </Card>
      </div>
    </div>
  );
}
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Component reuse rate | > 80% of UI elements from shared components |
| Style consistency | 0 inline color/spacing overrides |
| Page load time | < 2s for all pages |
| Accessibility | WCAG 2.1 AA compliance |
| Mobile responsiveness | All pages functional on 375px+ |

---

## Testing Checklist

### Visual Consistency

- [ ] All pages use same background color
- [ ] All cards have consistent border radius
- [ ] All buttons use Button component
- [ ] All status indicators use StatusBadge
- [ ] Platform colors are consistent
- [ ] Typography follows scale

### Functional Consistency

- [ ] Loading states shown appropriately
- [ ] Error states handled with retry option
- [ ] Empty states have clear messaging
- [ ] Navigation is consistent

### Accessibility

- [ ] Focus states visible
- [ ] Color contrast meets standards
- [ ] Touch targets ≥ 44px
- [ ] Screen reader compatible

---

**Document Owner:** Frontend Team  
**Last Updated:** January 20, 2026
