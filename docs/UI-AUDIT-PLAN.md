# UI Clarity & Cleanliness Audit Plan
## "Clarity without losing detail"

---

# Component Checklist with Pass/Fail Criteria

## HEADER COMPONENT

### Current State Assessment
| Element | Exists | Competing? | Action |
|---------|--------|------------|--------|
| Add Content button | ✓ | - | Keep |
| Navigation (←Today→) | ✓ | - | Keep |
| Month/Year display | ✓ | - | Keep |
| View toggle (M/W/D) | ✓ | Medium | Compact to icons |
| Density toggle | ✓ | High | Move to Options |
| Filter button | ✓ | Medium | Keep, add badge |
| Timezone selector | ✓ | High | Move to Options |
| Legend row | ✓ | High | Move to Options |

### Pass/Fail Criteria
| Criterion | Pass | Fail | Current |
|-----------|------|------|---------|
| ≤5 visible controls in header | ✓ | ✗ | ❌ (~10) |
| View toggle is compact (icons or 1-letter) | ✓ | ✗ | ❌ (full words) |
| Timezone is not prominent | Hidden/subtle | Prominent | ❌ |
| Legend consolidated or hidden | Dropdown/hover | Full row | ❌ |
| Today button is instantly findable | ✓ | ✗ | ✓ |

### Before → After Spec
```
BEFORE:
[←] [Today] [→]  [December 2025]  [Month] [Week] [Day]  [≡] [☰]  [⚙]  [🌍 Eastern]
[Legend: ● Scheduled ● Posted | ● TikTok ● Instagram ● YouTube]

AFTER:
[←] [Today] [→]  December 2025  [M][W][D]  [Options ▾]
                                            └─ Density: Compact/Comfortable
                                            └─ Timezone: Eastern ▾
                                            └─ Legend: [status dots] [platform dots]
                                            └─ Filters: Platform, Status
```

---

## CALENDAR GRID COMPONENT

### Current State Assessment
| Element | Month | Week | Day | Consistent? |
|---------|-------|------|-----|-------------|
| Day number display | ✓ | ✓ | ✓ | ✓ |
| Today highlight | ✓ | ✓ | ✓ | ⚠️ (varies) |
| Post count badge | ✓ | ✓ | - | ⚠️ |
| Grid borders | ✓ | ✓ | ✓ | ⚠️ (too strong) |
| + button | ✓ | ✓ | ✓ | ✓ |
| Overflow handling | None | Scroll | Scroll | ⚠️ |

### Pass/Fail Criteria
| Criterion | Pass | Fail | Current |
|-----------|------|------|---------|
| Today is instantly recognizable | Within 1 sec | >1 sec | ⚠️ |
| Day labels contrast with grid | 2:1 minimum | <2:1 | ⚠️ |
| Grid lines are subtle | zinc-800/30 | zinc-700+ | ❌ |
| Overflow pattern is consistent | Same everywhere | Mixed | ❌ |
| + button appears on hover only | Hover reveal | Always visible | ❌ |

### Before → After Spec
```
BEFORE (Day Header):
┌─────────────────────────────────────┐
│ SUN                                 │
│ 21 [5]  ← count badge prominent     │
│ ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔ │
│ [+ Schedule] ← always visible       │

AFTER (Day Header):
┌─────────────────────────────────────┐
│ Sun 21        ← combined, cleaner   │
│ ───────────── ← subtle separator    │
│               ← + appears on hover  │
```

---

## CARD COMPONENT

### Current State Assessment
| Element | Visible | Priority | Action |
|---------|---------|----------|--------|
| Thumbnail | ✓ | Medium | Keep |
| Platform badge | ✓ | Low | Demote to hover |
| Duration badge | ✓ | Low | Keep subtle |
| Status pill + text | ✓ | Medium | Remove text, keep color line |
| Title | ✓ | **HIGH** | Make hero |
| Time | ✓ | **HIGH** | Keep prominent |
| Caption preview | ✓ | Low | Hide, show on hover |
| Edit icon | Hover | Low | Keep hover |
| Retry button | Conditional | High | Keep for failed |

### Pass/Fail Criteria
| Criterion | Pass | Fail | Current |
|-----------|------|------|---------|
| Title is largest text on card | ✓ | ✗ | ⚠️ |
| Time visible without hover | ✓ | ✗ | ✓ |
| Status shown via color, not text | Color only | Text + color | ❌ |
| Platform shown once (not 2x) | 1 indicator | 2+ | ❌ |
| Hover reveals additional info | ✓ | ✗ | ⚠️ |
| Card has max 4 visible elements | ≤4 | >4 | ❌ (~6) |

### Before → After Spec
```
BEFORE (Card - Comfortable):
┌─────────────────────┐
│ [Thumbnail]     🎵  │ ← platform icon
│ ▔▔▔ violet ▔▔▔▔▔▔▔  │ ← status line
├─────────────────────┤
│ Title text here     │
│ ⏱ Scheduled • 9:00  │ ← status text redundant
│ Caption preview...  │ ← visible by default
└─────────────────────┘

AFTER (Card - Comfortable):
┌─────────────────────┐
│ [Thumbnail]   00:27 │ ← duration only
│ ▔▔▔ violet ▔▔▔▔▔▔▔  │ ← status = color line only
├─────────────────────┤
│ Title text here     │ ← HERO (font-medium)
│ 9:00 AM             │ ← time only, muted
└─────────────────────┘

AFTER (Card - Hover reveals):
┌─────────────────────┐
│ [Thumbnail]   00:27 │
│ 🎵            [✏️]  │ ← platform + edit on hover
│ ▔▔▔ violet ▔▔▔▔▔▔▔  │
├─────────────────────┤
│ Title text here     │
│ 9:00 AM • TikTok    │ ← platform name on hover
│ Caption preview...  │ ← caption on hover
└─────────────────────┘

AFTER (Card - Compact):
┌─────────────────────┐
│ [Thumb] Title...    │ ← inline thumb + title
│ ▔▔▔ 9:00 AM ▔▔▔▔▔  │ ← time in status line
└─────────────────────┘
```

### Density Mode Rules
| Element | Comfortable | Compact | Ultra-Compact |
|---------|-------------|---------|---------------|
| Thumbnail | h-20 | h-12 | Hidden |
| Title | Full | Truncate 1 line | Truncate 1 line |
| Time | Below title | Inline | Inline |
| Caption | On hover | Hidden | Hidden |
| Platform | On hover | Hidden | Hidden |
| Status | Color line | Color line | Dot only |

---

## EDIT MODAL COMPONENT

### Current State Assessment
| Element | Position | Priority | Action |
|---------|----------|----------|--------|
| Video player | Left | High | Keep |
| Title input | Right | **HIGH** | Keep, single line |
| Caption textarea | Right | High | Keep |
| Account selector | Right top | Medium | Keep |
| Visibility dropdown | Right | Low | Simplify |
| Action buttons (🖼️#@) | Right | Low | Remove if non-functional |
| Schedule bar | Top | High | Keep |
| Delete button | Bottom left | Low | Keep quiet |
| Save button | Bottom right | **HIGH** | Keep primary |

### Pass/Fail Criteria
| Criterion | Pass | Fail | Current |
|-----------|------|------|---------|
| Left = media, Right = form | ✓ | Mixed | ✓ |
| Title input is single line | ✓ | Multi | ✓ |
| Unsaved indicator present | ✓ | ✗ | ✓ |
| Delete is quiet (outline/text) | ✓ | Prominent | ✓ |
| Save is primary (filled) | ✓ | Outline | ✓ |
| Footer is sticky | ✓ | Scrolls | ✓ |
| No non-functional buttons | ✓ | Decorative | ❌ |

### Before → After Spec
```
BEFORE (Action row):
[🖼️] [#] [@]                    [Visibility ▾]
 ↑ unclear purpose

AFTER (Action row):
[Visibility: Public ▾]     ← single control, no icons
```

---

## MEDIA SELECTOR MODAL

### Pass/Fail Criteria
| Criterion | Pass | Fail | Current |
|-----------|------|------|---------|
| Grid uses real scheduled counts | Real API data | Random/fake | ❌ |
| Detail view shows real grades | From analysis | Hardcoded | ❌ |
| Search/filter within modal | ✓ | ✗ | ⚠️ (filters only) |
| Exit confirmation works | ✓ | ✗ | ✓ |
| Select Clip is primary CTA | ✓ | ✗ | ✓ |
| Back navigation is clear | ✓ | ✗ | ✓ |

---

## DATE PICKER COMPONENT

### Pass/Fail Criteria
| Criterion | Pass | Fail | Current |
|-----------|------|------|---------|
| Today is highlighted | ✓ | ✗ | ✓ |
| Selected date is highlighted | ✓ | ✗ | ✓ |
| Past dates are muted | ✓ | ✗ | ⚠️ |
| Time picker is inline | ✓ | Separate modal | ✓ |
| Timezone shown | ✓ | ✗ | ✓ |

---

# Visual System Tokens

## Typography Scale (Standardized)
| Token | Size | Weight | Use |
|-------|------|--------|-----|
| `--text-hero` | text-lg | font-semibold | Modal titles |
| `--text-title` | text-sm | font-medium | Card titles |
| `--text-body` | text-sm | normal | Body text |
| `--text-meta` | text-xs | normal | Timestamps, counts |
| `--text-muted` | text-xs | normal | Hints, placeholders |

## Spacing Scale (Standardized)
| Token | Value | Use |
|-------|-------|-----|
| `--space-xs` | 4px | Icon gaps |
| `--space-sm` | 8px | Card internal |
| `--space-md` | 12px | Card padding |
| `--space-lg` | 16px | Section gaps |
| `--space-xl` | 24px | Page padding |
| `--space-2xl` | 32px | Modal padding |

## Color Palette (Standardized)
| Token | Value | Use |
|-------|-------|-----|
| `--bg-page` | zinc-950 | Page background |
| `--bg-card` | zinc-900 | Card background |
| `--bg-elevated` | zinc-800 | Inputs, dropdowns |
| `--bg-hover` | zinc-800 | Hover states |
| `--border-default` | zinc-800/50 | Default borders |
| `--border-hover` | zinc-700 | Hover borders |
| `--text-primary` | white | Primary text |
| `--text-secondary` | zinc-400 | Secondary text |
| `--text-muted` | zinc-500 | Muted text |
| `--accent-primary` | violet-500 | Primary actions |
| `--accent-success` | emerald-500 | Success states |
| `--accent-danger` | red-500 | Danger states |
| `--accent-warning` | amber-500 | Warning states |

## Border Radius Scale
| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | 6px | Buttons, badges |
| `--radius-md` | 8px | Cards, inputs |
| `--radius-lg` | 12px | Modals, panels |
| `--radius-xl` | 16px | Large modals |
| `--radius-full` | 9999px | Pills, avatars |

## Shadow Scale
| Token | Value | Use |
|-------|-------|-----|
| `--shadow-sm` | 0 1px 2px | Subtle elevation |
| `--shadow-md` | 0 4px 6px | Cards |
| `--shadow-lg` | 0 10px 15px | Dropdowns |
| `--shadow-xl` | 0 20px 25px | Modals |

---

# Interaction Standards

## Hover States
| Element | Hover Effect |
|---------|--------------|
| Card | bg brighten + border lighten + subtle lift (-translate-y-0.5) |
| Button (primary) | Darken 10% |
| Button (secondary) | bg-zinc-700 |
| Icon button | bg-zinc-800 |
| Link | Underline |

## Focus States
| Element | Focus Effect |
|---------|--------------|
| All interactive | ring-2 ring-violet-500/50 ring-offset-2 ring-offset-zinc-900 |

## Loading States
| Context | Loading Pattern |
|---------|-----------------|
| Grid | Skeleton cards (8 placeholders) |
| Modal content | Centered spinner |
| Button | Spinner replaces text |
| Save action | Button disabled + "Saving..." |

## Error States
| Context | Error Pattern |
|---------|---------------|
| Form validation | Red border + inline error text |
| Save failure | Inline error above footer + Retry button |
| Network error | Toast + Retry option |

---

# Progressive Disclosure Rules

## Card Default State
- Thumbnail
- Title (hero)
- Time
- Status (color line only)

## Card Hover State (add)
- Platform badge
- Edit icon
- Caption preview (1 line)
- Platform name in meta

## Card Click State
- Opens edit modal with full details

---

# Overflow Strategy

## Chosen Pattern: "+N more" expander

### Month View
- Show max 3 cards per day
- "+N more" button at bottom
- Click expands to show all (inline)

### Week View  
- Scroll within column
- Max height: 450px
- Subtle scrollbar

### Day View
- Full timeline scroll
- No card limit per hour

---

# Quick Wins Checklist

## Highest ROI (Do First)
- [ ] Implement proper density toggle (Comfortable shows caption, Compact hides)
- [ ] Re-weight card typography (Title = font-medium text-sm, Time = text-xs text-zinc-500)
- [ ] Remove status text from cards (keep color line only)
- [ ] Consolidate legend into Options dropdown
- [ ] Strengthen Today highlight (filled circle, column tint)

## Medium Priority
- [ ] Move timezone to Options menu
- [ ] Compact view toggle to icons [M][W][D]
- [ ] Soften grid borders to zinc-800/30
- [ ] Hide + button until hover
- [ ] Remove non-functional action buttons from edit modal

## Polish
- [ ] Standardize all spacing to token scale
- [ ] Standardize all typography to token scale
- [ ] Add focus-visible rings to all interactive
- [ ] Consistent transition-all duration-200

---

# Validation Tests

## 3-Second Test Questions
1. What day/week are we looking at?
2. How many posts are scheduled today?
3. What's the next post and when?
4. Which platform has the most posts?

## Metrics to Instrument
| Metric | Target |
|--------|--------|
| Time to schedule (click + → save) | < 30 seconds |
| Time to edit existing post | < 20 seconds |
| Density toggle usage | > 20% of users try |
| Hover-to-modal ratio | > 50% |

---

## Audit Principles

### Core Goals
1. **Clarity** - Information hierarchy is immediately obvious
2. **Cleanliness** - Remove visual noise without losing data
3. **Data Fidelity** - Same information, better presentation
4. **Consistency** - Unified design language across all views

### Design Philosophy
- **Progressive disclosure** - Show essential info first, details on demand
- **Whitespace as design** - Strategic spacing creates hierarchy
- **Color restraint** - Limit accent colors to meaningful indicators
- **Typography hierarchy** - Clear distinction between levels

---

## 1. Schedule Page Header Audit

### Current Issues
| Issue | Severity | Description |
|-------|----------|-------------|
| Control density | Medium | Too many buttons in header row |
| Filter redundancy | Low | Filters in header AND expandable panel |
| Timezone prominence | Low | Takes too much visual weight |
| View toggle size | Low | Could be more compact |

### Recommendations
| Priority | Change | Impact |
|----------|--------|--------|
| P1 | Consolidate filters into single expandable panel | Cleaner header |
| P1 | Move timezone to settings or subtle dropdown | Less clutter |
| P2 | Reduce view toggle to icon-only with tooltip | More compact |
| P2 | Combine density + filter into single "Options" menu | Fewer buttons |
| P3 | Add keyboard shortcuts indicator | Power user efficiency |

### Proposed Header Layout
```
[← Today →]  [Month Year]  [M W D]  [⚙️ Options]
```

---

## 2. Calendar Grid Audit

### Current Issues
| Issue | Severity | Description |
|-------|----------|-------------|
| Card information density | Medium | Status, time, title, caption all compete |
| Today highlight | Low | Could be more subtle yet clear |
| Empty day messaging | Low | "+Schedule" button slightly busy |
| Grid borders | Low | Too many visible borders |

### Recommendations
| Priority | Change | Impact |
|----------|--------|--------|
| P1 | Hero title, muted metadata | Clear hierarchy |
| P1 | Single status indicator (color line) | Less visual noise |
| P2 | Remove duplicate status text | Cleaner cards |
| P2 | Softer grid borders (zinc-800/30) | Less harsh |
| P3 | Subtle empty state (just "+") | Cleaner grid |

### Card Hierarchy (Proposed)
```
┌─────────────────────┐
│ [Thumbnail]         │
│ ▔▔▔ (status line)   │
├─────────────────────┤
│ Title (hero)        │
│ 9:00 AM • TikTok    │  ← muted, single line
└─────────────────────┘
```

---

## 3. Legend & Stats Audit

### Current Issues
| Issue | Severity | Description |
|-------|----------|-------------|
| Legend takes full row | Medium | Could be inline with header |
| Platform colors redundant | Low | Shown on cards already |
| Click-to-filter unclear | Low | Not obvious it's interactive |

### Recommendations
| Priority | Change | Impact |
|----------|--------|--------|
| P1 | Move legend into Options dropdown | Less clutter |
| P2 | Show counts only on hover/demand | Cleaner default |
| P3 | Add filter indicator badge to Options button | Clear state |

---

## 4. Media Selector Modal Audit

### Current Issues
| Issue | Severity | Description |
|-------|----------|-------------|
| Grid + Detail have different footer | Medium | Inconsistent layout |
| Scheduled badge randomized | Low | Should show real data |
| Grade badges hardcoded | Low | Should use real scores |
| Tab bar (Projects/Likes) unused | Low | Visual noise if not functional |

### Recommendations
| Priority | Change | Impact |
|----------|--------|--------|
| P1 | Real scheduled count from API | Data accuracy |
| P1 | Real grade scores from analysis | Data accuracy |
| P2 | Sticky footer across all states | Consistent layout |
| P2 | Remove non-functional tabs | Less confusion |
| P3 | Add search within modal | Findability |

### Detail View Hierarchy (Proposed)
```
┌───────────────────────────────────────────────┐
│ [Video]     │  Score: 85/100                  │
│             │  ┌─A─┐┌─B+┐┌─A-┐┌─B─┐           │
│             │  │Hook││Flow││Eng││Trend│       │
│             │  └───┘└───┘└───┘└───┘           │
│             │                                 │
│             │  Hook: "The opening line..."    │
│             │                                 │
│             │  Topics: [tag] [tag] [tag]      │
└───────────────────────────────────────────────┘
```

---

## 5. Edit Post Modal Audit

### Current Issues
| Issue | Severity | Description |
|-------|----------|-------------|
| Schedule summary bar | Low | Good but could be cleaner |
| Action buttons row | Low | Unclear purpose (🖼️ # @) |
| Visibility dropdown | Low | Emoji in dropdown clutters |
| Form labels uppercase | Low | Consider sentence case |

### Recommendations
| Priority | Change | Impact |
|----------|--------|--------|
| P2 | Remove action buttons if non-functional | Less confusion |
| P2 | Remove emoji from visibility dropdown | Cleaner |
| P3 | Sentence case labels | Softer appearance |
| P3 | Combine date/time into single picker | Fewer controls |

---

## 6. Typography Audit

### Current Inconsistencies
| Location | Issue |
|----------|-------|
| Headers | Mix of text-lg, text-xl, text-2xl |
| Labels | Mix of uppercase/sentence case |
| Body | Mix of text-sm, text-xs |
| Muted | Mix of text-zinc-400, text-zinc-500 |

### Proposed Typography Scale
| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Page title | text-2xl | font-bold | text-white |
| Section header | text-lg | font-semibold | text-white |
| Card title | text-sm | font-medium | text-white |
| Body text | text-sm | normal | text-zinc-300 |
| Caption/meta | text-xs | normal | text-zinc-500 |
| Label | text-xs | font-medium | text-zinc-500 |

---

## 7. Spacing Audit

### Current Inconsistencies
| Location | Issue |
|----------|-------|
| Card padding | Mix of p-2, p-2.5, p-3 |
| Section gaps | Mix of gap-2, gap-3, gap-4, gap-6 |
| Modal padding | Mix of p-4, p-6, px-6 py-4 |

### Proposed Spacing Scale
| Element | Spacing |
|---------|---------|
| Page padding | p-6 |
| Section gap | gap-6 |
| Card padding | p-3 |
| Card internal gap | gap-2 |
| Button padding | px-4 py-2 |
| Small button | px-3 py-1.5 |
| Modal padding | p-6 |
| Modal header/footer | px-6 py-4 |

---

## 8. Color Audit

### Current Palette
| Use | Color | Notes |
|-----|-------|-------|
| Background | zinc-900, zinc-950 | Good |
| Card bg | zinc-800, zinc-850 | Inconsistent |
| Border | zinc-700, zinc-800 | Inconsistent |
| Primary | violet-500 | Good |
| Success | emerald-500, green-500 | Inconsistent |
| Danger | red-500 | Good |
| Warning | amber-500 | Good |

### Proposed Standardization
| Use | Color |
|-----|-------|
| Page bg | zinc-950 |
| Card bg | zinc-900 |
| Elevated bg | zinc-800 |
| Border default | zinc-800 |
| Border subtle | zinc-800/50 |
| Border hover | zinc-700 |
| Primary | violet-500 |
| Success | emerald-500 |
| Danger | red-500 |
| Warning | amber-500 |
| Info | blue-500 |

---

## 9. Interaction Audit

### Current Issues
| Issue | Severity | Description |
|-------|----------|-------------|
| Hover states inconsistent | Medium | Some lift, some brighten, some do both |
| Click feedback | Low | No visual click confirmation |
| Focus states | Medium | Inconsistent focus rings |
| Drag states | Low | Opacity change only |

### Recommendations
| Priority | Change | Impact |
|----------|--------|--------|
| P1 | Standardize hover: brighten bg + subtle border | Consistency |
| P2 | Add focus-visible ring to all interactive | Accessibility |
| P2 | Consistent transition-all duration-200 | Smooth feel |
| P3 | Add subtle scale on active/click | Tactile feedback |

---

## 10. Implementation Priority Matrix

### Phase 1: Quick Wins (1-2 days)
- [ ] Standardize typography scale
- [ ] Standardize spacing scale  
- [ ] Standardize color palette
- [ ] Fix inconsistent hover states

### Phase 2: Header Cleanup (1 day)
- [ ] Consolidate filters into Options menu
- [ ] Move timezone to subtle position
- [ ] Compact view toggle

### Phase 3: Card Refinement (1 day)
- [ ] Simplify card layout (title hero, muted meta)
- [ ] Single status indicator (color line only)
- [ ] Softer grid borders

### Phase 4: Modal Polish (1-2 days)
- [ ] Real data in media selector (scheduled count, grades)
- [ ] Remove non-functional elements
- [ ] Consistent footer across states
- [ ] Add search functionality

### Phase 5: Final Polish (1 day)
- [ ] Transition consistency
- [ ] Focus state audit
- [ ] Empty state refinement
- [ ] Keyboard shortcut indicators

---

## Metrics to Track

| Metric | Current | Target |
|--------|---------|--------|
| Unique font sizes used | ~8 | ≤4 |
| Unique spacing values | ~12 | ≤6 |
| Unique gray shades | ~6 | ≤4 |
| Controls in header | ~10 | ≤5 |
| Clicks to schedule post | 4 | ≤3 |

---

## Next Steps

1. **Review this audit** with stakeholders
2. **Prioritize** which phases to tackle first
3. **Create tickets** for each phase
4. **Implement** with before/after screenshots
5. **Validate** changes don't break functionality

---

*Last updated: December 21, 2025*
