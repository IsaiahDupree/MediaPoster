# Comprehensive Testing Plan

## 1. Environments & Principles

### Environments
*   **Local Dev:** Fast feedback, seeds with small example datasets.
*   **Staging:** Mirrors prod schemas, connected to sandbox platform APIs (or mocked gateways).
*   **Production:** Real users, feature flags ON/OFF.

### Core Principles
*   **Coverage:** Every critical flow (Upload -> Scheduled Post -> Analytics) must have Unit, Integration, and E2E coverage.
*   **Data-Driven:** Tests simulate multiple clips, platforms, and checkback times.

---

## 2. Backend Testing Plan

### 2.1 Unit Tests
*   **Ingestion:**
    *   Parse transcript → words[] with correct timestamps.
    *   Map words to segments (hook/body/CTA).
    *   Handle edge cases (missing timestamps, overlaps).
*   **Frame Analysis:**
    *   Verify frame sampling intervals.
    *   Test metadata extraction (face presence, shot type, OCR).
*   **Metrics & Checkbacks:**
    *   Calculate rates (like_rate, share_rate, CTA_response_rate).
    *   Verify NSM calculations (Engaged Reach, Content Leverage Score).
*   **Insight Engine:**
    *   Verify rule logic (e.g., "pain hook + identity" -> correct insight).
    *   Ensure idempotency.
*   **Publishing:**
    *   Test scheduling logic (no past dates).
    *   Verify payload construction for platforms.

### 2.2 Integration Tests
*   **Ingest Pipeline:** Upload Video → Metadata → Transcript → Words/Segments → Frames.
*   **Clip Generation:** Video + Segments → Highlight Selection → Clip Configs (1 clip -> 1 row).
*   **Schedule & Publish:** Create Post → Schedule → Job Runner → Mock API (Queued -> Published).
*   **Checkback Jobs:** Cron Job → Fetch Metrics → Write `post_checkbacks` → Verify Aggregations.
*   **Analytics:** New Metrics → Recompute NSMs → Run Insight Engine.

### 2.3 Performance Tests
*   **Ingestion:** Concurrent uploads with long transcripts.
*   **Analytics:** Query latency under load (many posts/checkbacks).

---

## 3. Frontend Testing Plan

### 3.1 Component Unit Tests
*   **Highlight Selector:** Timeline rendering, drag handles, transcript selection.
*   **Captions/Headline:** Toggle settings, style presets, preview updates.
*   **AI Buttons:** Generate/Regenerate calls, variant selection.
*   **Calendar:** Month/Week views, drag & drop rescheduling, status displays.
*   **Analytics:** NSM cards, charts, Post Performance view (retention curve hover).

### 3.2 Integration Flows (Cypress/Playwright)
1.  **Create Clip:** Select Video → Pick Range → Configure Overlays → Preview → Save.
2.  **Prepare Post:** Select Clip → Open Editor → Generate Title/Caption → Save Variant.
3.  **Schedule:** Clip List → Schedule → Pick Platform/Time → Verify on Calendar.
4.  **Analytics:** Dashboard → Click Post → View Performance → Trigger Insight Action.

### 3.3 Visual & UX
*   **Responsive:** Desktop vs. Laptop/Tablet.
*   **Regression:** Overlay positions, calendar cards, chart rendering.
*   **Accessibility:** Keyboard nav, color contrast.

---

## 4. End-to-End (E2E) Flows
*Run against Staging with stable test accounts.*

1.  **Video → Clips → Scheduled Posts:**
    *   Upload Video -> Create Clips -> Configure Overlays -> AI Generate Metadata -> Schedule -> Verify Mock API receipt.
2.  **Published Posts → Analytics → Insight:**
    *   Seed Mock Metrics -> Check Overview NSMs -> Check Post Performance -> Verify Insight generation.
3.  **Experiment Loop:**
    *   Use Insight -> Generate new hook -> Schedule new post -> Verify baseline comparison.

---

## 5. AI & Analytics Specifics
*   **AI Golden Dataset:** Maintain clips with known "good" outputs to regression test AI generation.
*   **Analytics Fixtures:** Tiny datasets with hand-calculated metrics to verify backend math.
*   **Alignment Tests:** Verify retention drops line up exactly with specific words/frames in test videos.

---

## 6. Automation Strategy
*   **CI (Automated):** Backend Unit/Integration, Frontend Unit/Integration, Happy-path E2E, Basic Performance.
*   **Manual QA:** Visual checks for styles, AI tone sanity checks, Real-world cross-platform posting.
