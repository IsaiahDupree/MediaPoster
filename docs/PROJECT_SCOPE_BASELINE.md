# Project Scope Baseline: EverReach Experimental & Blend

## 1. High-Level Vision
We are building a multi-app growth and relationship engine with two main pillars:

### A. EverReach Experimental (People Brain)
*   **Unified Graph:** A unified graph of people across email and social platforms.
*   **Person Lens:** Captures interests, tone, platform preferences, and activity state per person.
*   **Message Engine:** Generates email/DM copy based on `(person context + your context + goal)`.

### B. Blend / Cross-Platform Content Analytics (Content Brain)
*   **Global Content ID:** One canonical ID per piece of content.
*   **Platform Variants:** Up to 9 platform variants (IG, TikTok, YouTube, etc.) per content ID, each with unique titles, thumbnails, and descriptions.
*   **Unified Metrics:** Aggregated metrics and sentiment analysis across all variants.
*   **Content Briefs:** Segment-aware briefs guiding what to post, where, how, and expected performance.

Both pillars sit on the same underlying data model and share connectors.

---

## 2. Core Data Model (Baseline Schema)

### 2.1 People Graph
*   **`people`**: One row per human (`id`, `full_name`, `primary_email`, `company`, `role`, `created_at`).
*   **`identities`**: All ways we see them (`person_id` → `channel` [email, instagram, linkedin, etc.], `handle`, `profile_metadata`).
*   **`person_events`**: Interaction history (`person_id`, `channel`, `event_type` [commented, liked, opened_email], `traffic_type` [organic/paid], `platform_id`, `text_excerpt`, `sentiment`, `occurred_at`).

### 2.2 Person "Lens" / Insight Layer
*   **`person_insights`**: Cached features per person.
    *   Interests (topics)
    *   Tone preferences (e.g., casual, technical)
    *   Channel preferences (weights for email/IG/LI/X)
    *   Activity state (active, warming, dormant)
    *   Seasonality (time/day patterns)
    *   Warmth score
    *   Last active timestamp

### 2.3 Segments & Campaigns
*   **`segments`** & **`segment_members`**: Bucketized groups of people.
*   **`outbound_messages`**: Emails/DMs sent, tied to person + segment + goal.
*   **`segment_insights`**: Per-segment metrics split by `traffic_type` (organic vs paid), including top topics, platforms, formats, engagement style, and expected reach/engagement ranges.

---

## 3. Content Graph (Blend / Cross-Platform)

### 3.1 Canonical Content & Variants
*   **`content_items`**: Global content ID, slug, type (video, article), source URL (private/local), title, description, owner.
*   **`content_variants`**:
    *   `content_id`
    *   `platform` (instagram, tiktok, youtube, facebook, threads, etc.)
    *   `platform_post_id`, `platform_post_url`
    *   Platform-specific title, description, thumbnail_url
    *   `scheduled_at`, `published_at`
    *   `is_paid` (boolean)
    *   `experiment_id`, `variant_label`

### 3.2 Metrics & Rollups
*   **`content_metrics`**: Snapshots (`variant_id`, `snapshot_at`, views, impressions, likes, comments, shares, saves, clicks, watch time, `traffic_type`, `sentiment_score`).
*   **`content_rollups`**: Nightly aggregated per `content_id` (Organic totals, Paid totals, Global sentiment, Best platform).
*   **`content_experiments`**: Definitions for A/B/APINK tests across variants/platforms with hypothesis and primary metric.

---

## 4. Ingestion & Connectors
Everything downstream plugs into the core schema.

### 4.1 MetaCoach Graph API (Meta Surfaces)
*   **Target:** Meta-only users.
*   **Function:** Ingests Facebook Pages, Instagram Business/Creator, and Threads data via Meta Graph API.
*   **Output:** Writes `content_variants`, `content_metrics`, `identities`, and `person_events`.

### 4.2 Blotato Integration (9-Platform Hub)
*   **Function:** Multi-platform dispatcher. Publishes `content_variants` to up to 9 platforms.
*   **Blotato-Only Edition:** For users with only a Blotato account (no direct API keys). Publishes and tracks via Blotato; stores Blotato post IDs.

### 4.3 Native Connectors (YouTube, TikTok, etc.)
*   **Target:** Users with compatible API access (Google Cloud Console secrets, TikTok API).
*   **Function:** Polls metadata and analytics directly. Emits `content_metrics` and `person_events`.
*   **Fallback:** Users without secrets fall back to Blotato or "Local-Lite" mode.

### 4.4 Locally Hosted Scrapers (On-Prem Only)
*   **Target:** Advanced users/internal infra.
*   **Function:** Fetches metrics/public info where APIs are limited (compliant with ToS/User Consent). Never exposed as a public SaaS.

### 4.5 RapidAPI Social ↔ Email Enrichment
*   **Function:** Cross-references Social Handles ↔ Emails.
*   **Constraint:** Optional feature flag. Used only with permission/compliance.

### 4.6 Email Service Provider (ESP)
*   **Function:** Outbound templates/campaigns and inbound webhooks (opens, clicks, bounces).
*   **Integration:** Feeds `person_events` (channel='email') and connects to the Message Engine.

---

## 5. LinkedIn Integration (Modular)
*   **API-Only Mode:** Official LinkedIn APIs (Company pages, approved scopes).
*   **On-Prem Scraper Mode:** Runs locally behind user auth/consent (if used).
*   **Disabled Mode:** Hides LinkedIn features if no access.

---

## 6. App Modes / Editions
One core codebase, different modes based on `ENV` configuration.

### 6.1 Source Adapters Interface
Common interface for all connectors:
*   `isEnabled()`
*   `listSupportedPlatforms()`
*   `fetchMetricsForVariant(variant)`
*   `publishVariant(variant)` (optional)

### 6.2 Typical Modes
*   **`APP_MODE=meta_only`**: MetaCoach Graph adapter enabled. Target: MetaCoach users.
*   **`APP_MODE=blotato_only`**: Blotato adapter enabled. Target: Users with only Blotato.
*   **`APP_MODE=full_stack`**: All adapters enabled (Meta, Blotato, YouTube, TikTok, LinkedIn, ESP, Enrichment).
*   **`APP_MODE=local_lite`**: Local CSV/URL import + ESP. No external APIs.

---

## 7. Analytics, AI, and Briefs

### 7.1 Sentiment & Behavior
*   Sentiment analysis on comments, DMs, email replies.
*   Aggregates into `person_insights.last_sentiment`, `content_metrics.sentiment_score`, `content_rollups.global_sentiment`.

### 7.2 Segment-Driven Content Briefs
*   **Organic Brief:** Who they are, preferred formats/platforms, hooks that worked, expected engagement.
*   **Paid Brief:** Best audiences/objectives, top creatives, test matrix, expected CTR/CPC/CPL.

### 7.3 Single Content "Performance Brain"
*   **Cross-Platform View:** All 9 variants with metrics + sentiment.
*   **Experiment View:** A/B tests across platforms.
*   **Recommendations:** "Next time, lean into X on TikTok, Y on YouTube."

---

## 8. Privacy & Compliance (Baseline Constraints)
*   **ToS Compliance:** No credential harvesting. API usage within limits.
*   **Data Minimization:** Enrichment only for legitimate relationships.
*   **Separation of Concerns:** On-prem scrapers separate from public SaaS.

---

## 9. MVP Slice (Baseline Scope)
1.  **Core DB Schema & Adapters Layer:** Implement People/Content tables and Connector Interface.
2.  **Meta + Blotato Integration:** MetaCoach Graph connector + Blotato connector.
3.  **Basic Person Lens + Segments:** Simple activity state, topics, manual segments.
4.  **Single Content Page:** Canonical content + variants + metrics.
5.  **Organic Content Brief Generator (v1):** Plain-text brief from segment performance.
6.  **Email ESP Baseline:** Simple outbound + event tracking.
