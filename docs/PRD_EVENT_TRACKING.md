# PRD: Event Tracking System for MediaPoster

**Status:** Active  
**Created:** 2026-01-25  
**Based On:** BlankLogo Event Tracking Pattern

## Overview

Implement sophisticated user event tracking for MediaPoster to optimize content creation, scheduling, and publishing funnels across all social platforms.

## Event Categories

| Category | Events |
|----------|--------|
| **Acquisition** | `landing_view`, `cta_click`, `pricing_view`, `demo_requested` |
| **Activation** | `signup_start`, `login_success`, `activation_complete`, `first_platform_connected` |
| **Core Value** | `post_created`, `post_scheduled`, `post_published`, `media_uploaded`, `template_used`, `platform_connected`, `video_generated`, `trend_discovered` |
| **Monetization** | `checkout_started`, `purchase_completed`, `subscription_started`, `plan_upgraded` |
| **Retention** | `return_session`, `posts_this_week`, `platforms_active` |
| **Reliability** | `error_shown`, `publish_failed`, `upload_failed`, `generation_failed` |

## Core Value Event Properties

### post_created
```json
{
  "post_id": "string",
  "platform": "instagram | twitter | tiktok | youtube | linkedin",
  "content_type": "image | video | carousel | story | reel",
  "has_media": "boolean",
  "word_count": "number"
}
```

### post_published
```json
{
  "post_id": "string",
  "platform": "string",
  "scheduled_time": "ISO 8601",
  "actual_time": "ISO 8601",
  "automation_type": "manual | scheduled | auto"
}
```

### video_generated
```json
{
  "video_id": "string",
  "source": "sora | trend | upload",
  "duration_seconds": "number",
  "processing_time_ms": "number"
}
```

### trend_discovered
```json
{
  "trend_id": "string",
  "platform": "string",
  "category": "string",
  "virality_score": "number"
}
```

## 4 North Star Milestones

1. **Activated** = `first_platform_connected`
2. **First Value** = first `post_published`
3. **Aha Moment** = first scheduled post auto-publishes
4. **Monetized** = `purchase_completed`

## Integration with Latest PRDs

### From PRD_DM_AUTOMATION_SYSTEM.md (Jan 25)
- `dm_sent`, `dm_received`, `dm_auto_replied`
- `engagement_auto_liked`, `engagement_auto_commented`

### From PRD_Brand_Ops_Closed_Loop_System.md (Jan 25)
- `brand_voice_analyzed`, `content_optimized`, `performance_loop_triggered`

### From PRD_AUTO_ENGAGEMENT.md (Jan 25)
- `auto_engagement_started`, `auto_engagement_completed`, `engagement_metrics_updated`

## Features

| ID | Name | Priority |
|----|------|----------|
| TRACK-001 | Tracking SDK Integration | P1 |
| TRACK-002 | Acquisition Event Tracking | P1 |
| TRACK-003 | Activation Event Tracking | P1 |
| TRACK-004 | Core Value Event Tracking | P1 |
| TRACK-005 | Monetization Event Tracking | P1 |
| TRACK-006 | Retention Event Tracking | P2 |
| TRACK-007 | Error & Performance Tracking | P2 |
| TRACK-008 | User Identification | P1 |
| TRACK-009 | DM Automation Tracking | P2 |
| TRACK-010 | Auto Engagement Tracking | P2 |
| TRACK-011 | Trend Discovery Tracking | P2 |
| TRACK-012 | Video Generation Tracking | P2 |

## Success Metrics

- Track 100% of signup → first publish funnel
- Measure platform connection rate
- Measure posts per user per week
- Measure automation adoption rate
- Correlate engagement tracking with retention
