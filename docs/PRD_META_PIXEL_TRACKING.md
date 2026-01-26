# PRD: Meta Pixel & CAPI Integration for MediaPoster

**Status:** Active  
**Created:** 2026-01-25  
**Priority:** P1

## Overview

Implement Facebook Meta Pixel and Conversions API for MediaPoster to optimize content creator sign-ups, platform connections, and subscriptions.

## Standard Events Mapping

| MediaPoster Event | Meta Standard Event | Parameters |
|-------------------|---------------------|------------|
| `landing_view` | `PageView` | - |
| `demo_requested` | `Lead` | `content_name: 'demo'` |
| `signup_complete` | `CompleteRegistration` | `content_name`, `status` |
| `first_platform_connected` | `AddToCart` | `content_type: 'platform'` |
| `post_created` | `ViewContent` | `content_type: 'post'` |
| `post_published` | `ViewContent` | `content_type: 'published'` |
| `video_generated` | `ViewContent` | `content_type: 'video'` |
| `checkout_started` | `InitiateCheckout` | `value`, `currency` |
| `purchase_completed` | `Purchase` | `value`, `currency`, `content_ids` |
| `subscription_started` | `Subscribe` | `value`, `currency`, `predicted_ltv` |

## Advanced Features

### Custom Conversions for Engagement
```typescript
// Track high-value engagement actions
fbq('trackCustom', 'PlatformConnected', { platform: 'instagram' });
fbq('trackCustom', 'AutoPostEnabled', { platform: 'twitter' });
fbq('trackCustom', 'TrendDiscovered', { category: 'viral' });
```

### Lookalike Audiences
- Power users (10+ posts/week)
- Multi-platform users (3+ platforms)
- Auto-engagement users

## Features

| ID | Name | Priority |
|----|------|----------|
| META-001 | Meta Pixel Installation | P1 |
| META-002 | PageView Tracking | P1 |
| META-003 | Standard Events Mapping | P1 |
| META-004 | CAPI Server-Side Events | P1 |
| META-005 | Event Deduplication | P1 |
| META-006 | User Data Hashing (PII) | P1 |
| META-007 | Custom Audiences Setup | P2 |
| META-008 | Conversion Optimization | P2 |
| META-009 | Platform Connection Tracking | P2 |
| META-010 | Engagement Optimization | P2 |
