# UI Clarity & Cleanliness Audit Plan

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
