# Innovation Roadmap — MediaPoster

**Created:** Feb 8, 2026
**Last Updated:** Feb 8, 2026

---

## Overview

10 innovation PRDs organized by impact and effort. Build order is top-down — each tier unlocks value for the next.

---

## P0 — Immediate Impact (low effort, high value)

| # | Feature | PRD | Effort | Key Impact |
|---|---------|-----|--------|------------|
| 1 | **Auto-Subtitles/Captions** | [PRD_AUTO_SUBTITLES.md](PRD_AUTO_SUBTITLES.md) | 3-5 days | 40%+ watch time boost via Whisper + FFmpeg burn-in |
| 2 | **Smart Posting Times** | [PRD_SMART_POSTING_TIMES.md](PRD_SMART_POSTING_TIMES.md) | 3-4 days | 15-30% engagement boost from ML-optimized scheduling |
| 3 | **Content Recycling Engine** | [PRD_CONTENT_RECYCLING_ENGINE.md](PRD_CONTENT_RECYCLING_ENGINE.md) | 3-4 days | 2-3x content output without creating new videos |

## P1 — Medium-Term (1-2 weeks)

| # | Feature | PRD | Effort | Key Impact |
|---|---------|-----|--------|------------|
| 4 | **Cross-Platform Analytics** | [PRD_CROSS_PLATFORM_ANALYTICS_DASHBOARD.md](PRD_CROSS_PLATFORM_ANALYTICS_DASHBOARD.md) | 5-7 days | Unified view across all 22 accounts |
| 5 | **AI Caption Variants** | [PRD_AI_CAPTION_VARIANTS.md](PRD_AI_CAPTION_VARIANTS.md) | 2-3 days | Platform-native captions via GPT ($0.27/mo) |
| 6 | **A/B Testing Framework** | [PRD_AB_TESTING_FRAMEWORK.md](PRD_AB_TESTING_FRAMEWORK.md) | 5-7 days | Data-driven optimization across 4 TikTok + 4 IG accounts |

## P2 — Game-Changers (bigger lift, massive value)

| # | Feature | PRD | Effort | Key Impact |
|---|---------|-----|--------|------------|
| 7 | **Closed-Loop Content Intelligence** | [PRD_CLOSED_LOOP_CONTENT_INTELLIGENCE.md](PRD_CLOSED_LOOP_CONTENT_INTELLIGENCE.md) | 10-14 days | Self-improving content system; every post makes the next better |
| 8 | **Multi-Account Cascade** | [PRD_MULTI_ACCOUNT_CASCADE.md](PRD_MULTI_ACCOUNT_CASCADE.md) | 4-5 days | 3x reach via staggered cross-account publishing |
| 9 | **Automated Trend Detection** | [PRD_AUTOMATED_TREND_DETECTION.md](PRD_AUTOMATED_TREND_DETECTION.md) | 7-10 days | Ride trending waves within hours (~$150/mo) |
| 10 | **Engagement Autopilot** | [PRD_ENGAGEMENT_AUTOPILOT.md](PRD_ENGAGEMENT_AUTOPILOT.md) | 10-14 days | 2-5x follower growth via AI-powered engagement (~$40/mo) |

---

## Dependency Graph

```
Auto-Subtitles ──────────────────────────────────────────────┐
                                                              │
Smart Posting Times ──▶ Content Recycling Engine              │
        │                       │                             │
        ▼                       ▼                             │
Cross-Platform Analytics ──▶ A/B Testing Framework            │
        │                       │                             │
        ▼                       ▼                             ▼
Closed-Loop Content Intelligence ◀── AI Caption Variants ◀── Multi-Account Cascade
        │
        ▼
Automated Trend Detection
        │
        ▼
Engagement Autopilot
```

## Monthly Cost Summary

| Feature | Monthly Cost |
|---------|-------------|
| Auto-Subtitles (Whisper API) | ~$5-10 |
| Smart Posting Times | $0 (uses existing data) |
| Content Recycling | ~$2 (GPT for classification) |
| Analytics Dashboard | $0 |
| AI Caption Variants | ~$0.27 |
| A/B Testing | $0 |
| Content Intelligence | ~$10 |
| Multi-Account Cascade | $0 |
| Trend Detection | ~$150 |
| Engagement Autopilot | ~$40 |
| **Total (all features)** | **~$210/month** |

---

## Recommended Build Order

1. **Auto-Subtitles** — Standalone, no dependencies, massive watch-time impact
2. **AI Caption Variants** — Quick win, makes every post better immediately
3. **Smart Posting Times** — Foundation for recycling and cascade strategies
4. **Content Recycling Engine** — Multiplies existing content; uses smart times
5. **Multi-Account Cascade** — Uses caption variants + smart times
6. **Cross-Platform Analytics** — Needed for A/B testing and intelligence loop
7. **A/B Testing Framework** — Uses analytics data
8. **Closed-Loop Content Intelligence** — Uses all above data sources
9. **Automated Trend Detection** — Independent but enhanced by intelligence loop
10. **Engagement Autopilot** — Independent; builds on Safari automation scaffolding
