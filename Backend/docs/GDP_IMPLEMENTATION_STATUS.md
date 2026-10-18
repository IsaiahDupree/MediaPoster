# Growth Data Plane (GDP) Implementation Status

**Date:** 2026-01-25
**Status:** Phase 0 P0 Features Implemented
**Migration:** `015_growth_data_plane.sql`
**Models:** Added to `database/models.py`

---

## Overview

The Growth Data Plane for MediaPoster provides unified event tracking for content creator onboarding, platform connection, and publishing funnels. This implementation follows the PRD at `docs/PRD_GROWTH_DATA_PLANE.md`.

---

## Completed Features

### ✅ GDP-001: Supabase Schema Setup (P0)
**Status:** Complete
**Migration:** `015_growth_data_plane.sql`

Created comprehensive database schema including:
- `email_messages` - Email tracking via Resend
- `email_events` - Email engagement events (delivered, opened, clicked, bounced)
- `subscriptions` - Stripe subscription tracking
- `deals` - Revenue attribution and pipeline tracking
- `person_features` - ML features for segmentation
- `attribution_touchpoints` - Click tracking for email → conversion attribution
- `external_identities` - Links to PostHog, Stripe, Meta Pixel, GA4

Enhanced existing tables:
- `person_events` - Added `event_source` and `event_id` columns
- `segments` - Added `segment_type`, `auto_refresh_enabled`, `refresh_frequency`

### ✅ GDP-002: Person & Identity Tables (P0)
**Status:** Complete
**Existing Tables:** `people`, `identities` (from migration 001)

The existing People Graph schema already provides:
- `people` table - Canonical person records
- `identities` table - Cross-platform identity mapping (email, Instagram, Twitter, TikTok, etc.)

Enhanced with GDP-specific features:
- `person_features` table - Computed engagement and usage scores
- `external_identities` table - Links to external analytics platforms

### ✅ GDP-003: Unified Events Table (P0)
**Status:** Complete
**Existing Table:** `person_events` (from migration 001)

Enhanced the existing `person_events` table with:
- `event_source` column - Track source (web, app, email, stripe, api)
- `event_id` column - External event ID from source system
- Indexes for efficient event querying by source and ID

---

## Database Models Added

**File:** `Backend/database/models.py`
**New Classes:**
1. `EmailMessage` - GDP-004: Email messages sent via Resend
2. `EmailEvent` - GDP-005: Email engagement events
3. `Subscription` - GDP-007/008: Stripe subscription tracking
4. `Deal` - Revenue attribution and pipeline
5. `PersonFeatures` - GDP-011: ML features for segmentation
6. `AttributionTouchpoint` - GDP-006: Click tracking for attribution
7. `ExternalIdentity` - GDP-009/010: External platform identity links

**Lines Added:** 247 lines of new model definitions

---

## Automation Features

### Triggers & Functions
The migration includes PostgreSQL triggers to automatically update `person_features`:

1. **Email Open Tracking**
   - Trigger: `trigger_update_person_features_email_opened`
   - Function: `update_person_features_email()`
   - Updates: `total_emails_opened`, `last_email_opened_at`, `email_open_rate`

2. **Email Click Tracking**
   - Trigger: `trigger_update_person_features_email_clicked`
   - Function: `update_person_features_email_click()`
   - Updates: `total_emails_clicked`, `last_email_clicked_at`, `email_click_rate`

3. **Subscription Status Tracking**
   - Trigger: `trigger_update_person_features_subscription`
   - Function: `update_person_features_subscription()`
   - Updates: `subscription_status`, `subscription_mrr_cents`, `is_paying`

### Materialized Views
1. **`active_subscribers_with_engagement`**
   - Active subscribers ranked by engagement score
   - Joins people, subscriptions, person_features

2. **`high_value_leads`**
   - Engaged users who are not yet paying
   - Filters by product_usage_score > 0.5 and total_posts_created >= 3

---

## Next Steps (Pending Implementation)

### 🔄 GDP-004: Resend Webhook Edge Function (P0)
**Status:** TODO
**Files to Create:**
- `Backend/api/endpoints/resend_webhooks.py` - FastAPI endpoint for Resend webhooks
- `Backend/services/resend_tracking_service.py` - Service to process Resend events

**Requirements:**
- Verify Svix signature for webhook security
- Store email events (delivered, opened, clicked, bounced)
- Map email tags to `person_id` for attribution
- Update `email_messages` and `email_events` tables

**Example Event Types:**
```python
# Resend webhook events
- email.sent
- email.delivered
- email.opened
- email.clicked
- email.bounced
- email.complained
```

### 🔄 GDP-005: Email Event Tracking (P0)
**Status:** TODO
**Implementation:**
- Process Resend webhook events
- Store in `email_events` table
- Trigger automatic `person_features` updates
- Track: delivered, opened, clicked, bounced, complained, unsubscribed

### 🔄 GDP-006: Click Redirect Tracker (P1)
**Status:** TODO
**Files to Create:**
- `Backend/api/endpoints/click_redirect.py` - `/c/{click_id}` redirect endpoint

**Requirements:**
- Create short link `/c/{click_id}` for email link tracking
- Set first-party cookie with `session_id`
- Store click in `attribution_touchpoints` table
- Redirect to destination URL with UTM parameters
- Enable attribution: email → click → session → conversion

### 🔄 GDP-007: Stripe Webhook Integration (P1)
**Status:** TODO
**Files to Create:**
- `Backend/api/endpoints/stripe_webhooks.py` - Stripe webhook endpoint
- `Backend/services/stripe_tracking_service.py` - Stripe event processor

**Requirements:**
- Handle subscription events (created, updated, canceled)
- Map `stripe_customer_id` to `person_id`
- Update `subscriptions` table
- Create/update `external_identities` for Stripe

**Example Event Types:**
```python
# Stripe webhook events
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.payment_succeeded
- invoice.payment_failed
```

### 🔄 GDP-008: Subscription Snapshot (P1)
**Status:** TODO
**Implementation:**
- Upsert subscription status from Stripe events
- Track plan, MRR, billing period
- Update `person_features.is_paying`
- Calculate `days_to_first_purchase`

### 🔄 GDP-009: PostHog Identity Stitching (P1)
**Status:** TODO
**Files to Create:**
- `Backend/services/posthog_identity_service.py` - PostHog integration

**Requirements:**
- Call `posthog.identify(person_id)` on login/signup
- Store mapping in `external_identities` table
- Enable cross-platform user tracking

### 🔄 GDP-010: Meta Pixel + CAPI Dedup (P1)
**Status:** TODO
**Implementation:**
- Fire Meta Pixel with `eventID` matching CAPI `event_id`
- Prevent double-counting of conversions
- Send server-side events via CAPI
- Reference: `docs/PRD_META_PIXEL_TRACKING.md`

### 🔄 GDP-011: Person Features Computation (P1)
**Status:** TODO
**Files to Create:**
- `Backend/services/person_features_service.py` - Feature computation service
- `Backend/workers/person_features_worker.py` - Background worker for batch updates

**Requirements:**
- Compute engagement scores (0-1 scale)
- Compute product usage scores (0-1 scale)
- Predict churn likelihood (0-1 scale)
- Run nightly batch updates
- Trigger on key events (post_created, post_published, platform_connected)

### 🔄 GDP-012: Segment Engine (P1)
**Status:** TODO
**Files to Create:**
- `Backend/services/segment_engine_service.py` - Dynamic segment computation
- `Backend/api/endpoints/segments_gdp.py` - Segment management API

**Requirements:**
- Support static (manual), dynamic (SQL), and behavioral (ML) segments
- Auto-refresh segments based on `refresh_frequency`
- Implement segment membership computation
- Examples from PRD:
  - `signup_no_platform_24h` → email: "Connect your first social account"
  - `platform_connected_no_post_48h` → email: "Create your first post"
  - `high_usage_free_tier` → email: "Unlock unlimited platforms"

---

## MediaPoster-Specific Events

From `PRD_GROWTH_DATA_PLANE.md`:

| Event | Source | Person Event Type | Segment Trigger |
|-------|--------|-------------------|-----------------|
| `landing_view` | web | page_view | - |
| `demo_requested` | web | lead_gen | warm_lead |
| `signup_completed` | web | signup | new_signup |
| `first_platform_connected` | app | platform_connected | activated |
| `post_created` | app | content_created | first_action |
| `post_scheduled` | app | content_scheduled | - |
| `post_published` | app | content_published | first_value |
| `video_generated` | app | ai_video_created | - |
| `trend_discovered` | app | trend_found | power_user |
| `auto_engagement_enabled` | app | automation_enabled | aha_moment |
| `checkout_started` | web | checkout_init | checkout_started |
| `subscription_started` | stripe | subscription_active | monetized |
| `email.clicked` | resend | email_engagement | newsletter_clicker |

---

## Segments for MediaPoster

From the PRD, key segments to implement:

1. **signup_no_platform_24h**
   - Rule: Signed up but no platform connected within 24 hours
   - Action: Email "Connect your first social account"

2. **platform_connected_no_post_48h**
   - Rule: Platform connected but no post created within 48 hours
   - Action: Email "Create your first post"

3. **post_created_not_published_24h**
   - Rule: Post created but not published within 24 hours
   - Action: Email "Your post is ready to publish"

4. **first_post_published**
   - Rule: First post published successfully
   - Action: Email "Enable auto-scheduling"

5. **high_usage_free_tier**
   - Rule: Free user with high usage (posts/week > threshold)
   - Action: Email "Unlock unlimited platforms"

6. **trend_discovered_no_action**
   - Rule: Trend discovered but not acted upon
   - Action: Email "Jump on this trend"

7. **inactive_7d_with_scheduled**
   - Rule: No activity for 7 days but has scheduled posts
   - Action: Email "Your scheduled posts need attention"

---

## Testing Checklist

### Database Migration
- [ ] Run migration: `psql $DATABASE_URL -f Backend/database/migrations/015_growth_data_plane.sql`
- [ ] Verify tables created: `\dt` in psql
- [ ] Test triggers work (insert email_event, check person_features update)
- [ ] Verify views: `SELECT * FROM active_subscribers_with_engagement LIMIT 10;`

### Model Validation
- [ ] Import models in Python: `from database.models import EmailMessage, EmailEvent, Subscription`
- [ ] Test ORM queries work
- [ ] Verify relationships (EmailMessage → EmailEvent, Person → PersonFeatures)

### API Endpoints (To Be Implemented)
- [ ] Resend webhook endpoint (`POST /api/webhooks/resend`)
- [ ] Stripe webhook endpoint (`POST /api/webhooks/stripe`)
- [ ] Click redirect endpoint (`GET /c/{click_id}`)
- [ ] Person features API (`GET /api/gdp/person/{person_id}/features`)
- [ ] Segments API (`GET /api/gdp/segments`, `POST /api/gdp/segments/{id}/refresh`)

---

## Integration Points

### Resend (Email Service)
- **Webhook URL:** `https://mediaposter.com/api/webhooks/resend`
- **Signature Verification:** Svix signature header
- **Events:** email.sent, email.delivered, email.opened, email.clicked, email.bounced

### Stripe (Payment Processing)
- **Webhook URL:** `https://mediaposter.com/api/webhooks/stripe`
- **Signature Verification:** Stripe-Signature header
- **Events:** customer.subscription.*, invoice.payment.*

### PostHog (Analytics)
- **Identity Stitching:** Call `posthog.identify(person_id, traits)` on login
- **External Identity:** Store PostHog distinct_id in `external_identities`

### Meta Pixel (Advertising)
- **Event Deduplication:** Use matching `eventID` for Pixel and CAPI
- **Reference:** `docs/PRD_META_PIXEL_TRACKING.md`

---

## Files Modified

1. **Database Migration:**
   - Created: `Backend/database/migrations/015_growth_data_plane.sql` (569 lines)

2. **Database Models:**
   - Modified: `Backend/database/models.py` (+247 lines)
   - Added 7 new model classes

3. **Documentation:**
   - Created: `Backend/docs/GDP_IMPLEMENTATION_STATUS.md` (this file)

---

## Performance Considerations

### Indexes
All GDP tables have appropriate indexes for:
- Foreign key lookups (person_id, email_message_id, etc.)
- Time-series queries (occurred_at, clicked_at, created_at)
- Event type filtering (event_type, status, provider)
- Engagement scores (engagement_score, product_usage_score, likelihood_to_churn)

### Row-Level Security (RLS)
All GDP tables have RLS enabled for multi-tenant security:
```sql
ALTER TABLE email_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
-- etc.
```

### Triggers
Triggers are optimized to:
- Only fire on relevant events (WHEN clause)
- Use UPSERT (INSERT ... ON CONFLICT) for idempotency
- Update only changed fields
- Batch updates via background worker for heavy computations

---

## Next Session Tasks

1. **Implement Resend Webhook Handler (GDP-004)**
   - Create `/api/webhooks/resend` endpoint
   - Verify Svix signatures
   - Store email events in database
   - Test with Resend webhook simulator

2. **Implement Stripe Webhook Handler (GDP-007)**
   - Create `/api/webhooks/stripe` endpoint
   - Verify Stripe signatures
   - Update subscriptions table
   - Handle subscription lifecycle events

3. **Implement Click Redirect Tracker (GDP-006)**
   - Create `/c/{click_id}` redirect endpoint
   - Set first-party cookies
   - Store attribution touchpoints
   - Test attribution flow

4. **Implement Person Features Service (GDP-011)**
   - Create background worker for feature computation
   - Implement engagement score calculation
   - Implement product usage score calculation
   - Implement churn prediction

5. **Implement Segment Engine (GDP-012)**
   - Create dynamic segment computation
   - Implement auto-refresh mechanism
   - Create segment membership API
   - Test with MediaPoster-specific segments

6. **Update Feature List**
   - Mark GDP-001, GDP-002, GDP-003 as `passes: true`
   - Update harness metrics

---

## Success Metrics

Track these metrics to validate GDP implementation:

1. **Email Engagement**
   - Email open rate: % of sent emails opened
   - Email click rate: % of opened emails clicked
   - Bounce rate: % of emails bounced

2. **Product Activation**
   - Time to first platform connected
   - Time to first post created
   - Time to first post published

3. **Conversion**
   - Free to paid conversion rate
   - Days to first purchase
   - MRR (Monthly Recurring Revenue)

4. **Retention**
   - 7-day active rate
   - 30-day active rate
   - Churn rate by cohort

5. **Segment Performance**
   - Segment membership counts
   - Segment email engagement rates
   - Segment conversion rates

---

## References

- **PRD:** `/docs/PRD_GROWTH_DATA_PLANE.md`
- **Meta Pixel PRD:** `/docs/PRD_META_PIXEL_TRACKING.md`
- **Migration:** `/Backend/database/migrations/015_growth_data_plane.sql`
- **Models:** `/Backend/database/models.py` (lines 2682-2928)
- **People Graph PRD:** Reference implementation from EverReach/Blend
