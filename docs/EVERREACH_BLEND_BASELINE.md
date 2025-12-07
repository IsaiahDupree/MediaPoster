# EverReach Experimental & Blend: Project Baseline

## 1. High-Level Vision
This project builds a multi-app growth and relationship engine with two main pillars that share a common data foundation:

1.  **EverReach Experimental (People Brain):** A unified person graph that tracks relationships across email and social channels, building a "lens" for each person (interests, tone, preferences) to power a hyper-personalized messaging engine.
2.  **Blend (Content Brain):** A cross-platform content analytics engine that ties a single "Content ID" to multiple platform variants (IG, YT, TikTok, etc.), aggregating metrics and sentiment to generate segment-aware content briefs.

**Key Philosophy:**
*   **Modular & Env-Driven:** One codebase, multiple "editions" (Meta-only, Blotato-only, Full Stack) enabled by environment variables.
*   **Privacy-First:** No unauthorized scraping. Relies on official APIs, user consent, and owned data.
*   **Relationship-Centric:** Focuses on deepening relationships with existing audiences, not mass cold scraping.

---

## 2. Core Data Models

### 2.1 People Graph (EverReach)
*   **`people`:** Unique human entities (ID, Name, Primary Email, Company, Role).
*   **`identities`:** Links people to channels (Email, Instagram, LinkedIn, Twitter, etc.) with handles and metadata.
*   **`person_events`:** Unified stream of interactions (Commented, Liked, Opened Email, Clicked Link).
    *   *Fields:* `channel`, `event_type`, `traffic_type` (organic/paid), `sentiment`, `metadata`.
*   **`person_insights`:** Computed "lens" for each person.
    *   *Fields:* `interests`, `tone_preferences`, `channel_preferences`, `activity_state`, `warmth_score`.
*   **`segments`:** Dynamic groups of people based on insights and behavior.

### 2.2 Content Graph (Blend)
*   **`content_items`:** Canonical content assets (Video, Article) with a global ID.
*   **`content_variants`:** Platform-specific executions of a content item.
    *   *Fields:* `platform` (IG, YT, TikTok, etc.), `platform_post_id`, `title`, `thumbnail`, `is_paid`.
*   **`content_metrics`:** Time-series snapshots of performance.
    *   *Fields:* `views`, `likes`, `comments`, `watch_time`, `sentiment_score`.
*   **`content_rollups`:** Aggregated performance per Content ID (Global Sentiment, Best Platform).

---

## 3. Connectors & Ingestion
The system uses a modular "Source Adapter" pattern. Connectors are enabled/disabled based on available credentials.

### 3.1 MetaCoach Graph API (Meta Surfaces)
*   **Role:** Ingests data for Facebook, Instagram, and Threads.
*   **Data:** Posts, Comments, Reactions, Insights.
*   **Status:** Existing dedicated app.

### 3.2 Blotato Integration (Multi-Platform Hub)
*   **Role:** Publishing dispatcher and metrics fallback for up to 9 platforms.
*   **Function:** Publishes `content_variants`, retrieves platform IDs, ingests basic metrics.
*   **Editions:** Critical for "Blotato-only" mode.

### 3.3 Native Connectors (High-Fidelity)
*   **YouTube:** Uses Google Cloud Console secrets (Data API) for deep analytics.
*   **TikTok:** Uses TikTok API for performance data.
*   **LinkedIn:** Modular connector.
    *   *API Mode:* Official API for company pages/ads.
    *   *Scraper Mode:* Local-only, user-consented scraping (optional/advanced).

### 3.4 Local Scrapers (On-Prem)
*   **Role:** Fills gaps where APIs are limited.
*   **Constraint:** Locally hosted, open-source, never exposed as a public SaaS service. Runs on user's infrastructure.

### 3.5 Enrichment & Email
*   **RapidAPI:** Cross-references Social Handles ↔ Emails.
    *   *Constraint:* Feature-flagged, requires specific API keys.
*   **Custom ESP (Email Service Provider):**
    *   Sends personalized emails via EverReach engine.
    *   Ingests webhooks (Open, Click, Bounce) as `person_events`.

---

## 4. App Modes & Editions
The application behavior adapts to the environment (`APP_MODE`).

| Mode | Target User | Required Creds | Enabled Connectors |
| :--- | :--- | :--- | :--- |
| **Meta-Only** | MetaCoach Users | Meta App ID, Page Token | Meta Graph API |
| **Blotato-Only** | Blotato Users | Blotato API Key | Blotato (Publishing/Metrics) |
| **Full Stack** | Power Users | Meta, Google, TikTok, Blotato | All Native APIs + Blotato |
| **Local Lite** | No-Code / Basic | None | Local CSV Import, Manual Entry |

---

## 5. Key Features

### 5.1 Segment-Aware Content Briefs
Generates strategic briefs for Organic and Paid content.
*   **Inputs:** Segment Insights (Top topics, formats, times), Past Performance.
*   **Outputs:**
    *   *Organic:* Hook ideas, platform recommendations, engagement style.
    *   *Paid:* Audience targeting, creative matrix, budget guidance.

### 5.2 Cross-Platform Analytics
*   **Unified Dashboard:** View one piece of content across all platforms.
*   **Experimentation:** Track A/B tests (e.g., Title A on IG vs Title B on TikTok).
*   **Sentiment Analysis:** Aggregate sentiment from comments across all channels.

### 5.3 Message Engine
*   **Input:** Person Context (Lens) + Brand Context + Goal.
*   **Output:** Hyper-personalized Email/DM copy.
*   **Feedback:** Success feeds back into the Person Lens.

---

## 6. MVP Slice (Baseline Scope)
1.  **Core Schema:** Implement People, Content, and Event tables in Supabase.
2.  **Connector Interface:** Define the standard `SourceAdapter` interface.
3.  **Meta + Blotato:** Implement these two primary connectors first.
4.  **Basic Person Lens:** Compute `activity_state` and `top_topics`.
5.  **Content Single View:** Dashboard showing 1 Content ID -> N Variants.
6.  **Organic Brief Generator:** V1 implementation using LLM.

---

## 7. Implementation Roadmap

### Phase 1: Database Foundation (Week 1-2)
*   Create Supabase migrations for all tables
*   Set up Row Level Security (RLS) policies
*   Create performance indexes
*   Seed with test data

**Deliverables:**
*   ✅ Complete database schema (see [`EVERREACH_BLEND_DATABASE_SCHEMA.md`](./EVERREACH_BLEND_DATABASE_SCHEMA.md))

### Phase 2: Connector Architecture (Week 2-3)
*   Define TypeScript `SourceAdapter` interface
*   Build `AdapterRegistry` pattern
*   Implement Meta, Blotato adapters
*   Add health checks and feature flags

**Deliverables:**
*   ✅ Connector interface spec (see [`EVERREACH_CONNECTOR_INTERFACE.md`](./EVERREACH_CONNECTOR_INTERFACE.md))

### Phase 3: EverReach People Graph (Week 3-5)
*   Build Meta OAuth flow
*   Implement person/identity ingestion
*   Create `person_events` pipeline
*   Build sentiment analysis
*   Compute `person_insights`

**Deliverables:**
*   Working Instagram/Facebook data ingestion
*   Person "lens" computation

### Phase 4: Blend Content System (Week 5-7)
*   Create `content_items` UI
*   Build `content_variants` generator
*   Integrate Blotato publishing
*   Implement metrics polling
*   Build "Content Single" dashboard

**Deliverables:**
*   Cross-platform content publishing
*   Unified analytics view

### Phase 5: Segments & Briefs (Week 7-9)
*   Build segment creation UI
*   Implement `segment_insights` computation
*   Create message engine V1
*   Build content brief generator

**Deliverables:**
*   Working segment-aware content briefs
*   Basic message personalization

### Phase 6: App Modes & Polish (Week 9-10)
*   Create `.env.example` for each mode
*   Write mode-specific READMEs
*   Implement feature flags UI
*   Final testing and documentation

**Deliverables:**
*   Meta-Only, Blotato-Only, Full Stack editions
*   Complete user documentation

---

## 8. Reference Documentation
*   **Database Schema:** [`EVERREACH_BLEND_DATABASE_SCHEMA.md`](./EVERREACH_BLEND_DATABASE_SCHEMA.md)
*   **Connector Interface:** [`EVERREACH_CONNECTOR_INTERFACE.md`](./EVERREACH_CONNECTOR_INTERFACE.md)
*   **Testing Plan:** [`COMPREHENSIVE_TESTING_PLAN.md`](./COMPREHENSIVE_TESTING_PLAN.md)
*   **AI News Pipeline:** [`AI_NEWS_MEME_PIPELINE.md`](./AI_NEWS_MEME_PIPELINE.md)
