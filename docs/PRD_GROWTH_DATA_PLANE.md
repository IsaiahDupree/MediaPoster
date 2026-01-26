# PRD: Growth Data Plane for MediaPoster

**Status:** Active  
**Created:** 2026-01-25  
**Priority:** P0  
**Reference:** `autonomous-coding-dashboard/harness/prompts/PRD_GROWTH_DATA_PLANE.md`

## Overview

Implement the Growth Data Plane for MediaPoster: unified event tracking for content creator onboarding, platform connection, and publishing funnels.

## MediaPoster-Specific Events

| Event | Source | Segment Trigger |
|-------|--------|-----------------|
| `landing_view` | web | - |
| `demo_requested` | web | warm_lead |
| `signup_completed` | web | new_signup |
| `first_platform_connected` | app | activated |
| `post_created` | app | first_action |
| `post_scheduled` | app | - |
| `post_published` | app | first_value |
| `video_generated` | app | - |
| `trend_discovered` | app | power_user |
| `auto_engagement_enabled` | app | aha_moment |
| `checkout_started` | web | checkout_started |
| `subscription_started` | stripe | monetized |
| `email.clicked` | resend | newsletter_clicker |

## Segments for MediaPoster

1. **signup_no_platform_24h** → email: "Connect your first social account"
2. **platform_connected_no_post_48h** → email: "Create your first post"
3. **post_created_not_published_24h** → email: "Your post is ready to publish"
4. **first_post_published** → email: "Enable auto-scheduling"
5. **high_usage_free_tier** → email: "Unlock unlimited platforms"
6. **trend_discovered_no_action** → email: "Jump on this trend"
7. **inactive_7d_with_scheduled** → email: "Your scheduled posts need attention"

## Integration with Latest PRDs

### From PRD_DM_AUTOMATION_SYSTEM.md
- Track DM automations in segment engine
- `dm_sent`, `dm_auto_replied` as engagement events

### From PRD_Brand_Ops_Closed_Loop_System.md
- Brand voice events feed into person features
- Optimize segments based on brand performance

## Features

| ID | Name | Priority |
|----|------|----------|
| GDP-001 | Supabase Schema Setup | P0 |
| GDP-002 | Person & Identity Tables | P0 |
| GDP-003 | Unified Events Table | P0 |
| GDP-004 | Resend Webhook Edge Function | P0 |
| GDP-005 | Email Event Tracking | P0 |
| GDP-006 | Click Redirect Tracker | P1 |
| GDP-007 | Stripe Webhook Integration | P1 |
| GDP-008 | Subscription Snapshot | P1 |
| GDP-009 | PostHog Identity Stitching | P1 |
| GDP-010 | Meta Pixel + CAPI Dedup | P1 |
| GDP-011 | Person Features Computation | P1 |
| GDP-012 | Segment Engine | P1 |
| GDP-013 | DM Automation Tracking | P2 |
| GDP-014 | Brand Ops Integration | P2 |
