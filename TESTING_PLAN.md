# 🧪 Comprehensive Testing Plan: EverReach Experimental + Blend

## 1. Environments & Principles

### Environments
- **Local Dev**: Fast feedback, seeded with small example datasets (mock connectors).
- **Staging**: Mirrors prod schemas, connected to sandbox platform APIs (or mocked gateways).
- **Production**: Real users, feature flags ON/OFF.

### Core Principles
- **Coverage**: Every critical flow (from "upload" → "analytics") must have Unit, Integration, and E2E coverage.
- **Data-Driven**: Tests should simulate multiple clips, platforms, and checkback times.
- **Isolation**: Connectors should be testable in isolation using the `SourceAdapter` interface.

---

## 2. Backend Testing Plan

### 2.1 Unit Tests (Pytest)
**Location**: `Backend/tests/unit/`

- **Connectors**:
    - Mock `SourceAdapter` responses for Meta, YouTube, etc.
    - Verify data mapping from platform JSON to `content_metrics` schema.
    - Test rate-limit handling and retry logic.
- **Ingestion Logic**:
    - Test `video_pipeline` parsing of transcripts to segments.
    - Test `person_insights` computation (e.g., "if 3 comments in 7 days -> active").
- **API Endpoints**:
    - Test FastAPI routes with `TestClient`.
    - Verify auth guards and permission checks.

### 2.2 Integration Tests
**Location**: `Backend/tests/integration/`

- **Ingestion Pipeline**:
    - Flow: Upload Video -> Store Metadata -> Mock Transcription -> Store Segments.
    - Verify DB rows created in `content_items`, `content_variants`.
- **Social Metrics Job**:
    - Flow: Trigger `social_metrics` job -> Fetch from Mock Connector -> Write to `content_metrics`.
    - Verify `content_rollups` are calculated correctly.
- **Database Constraints**:
    - Verify foreign key constraints and unique indexes (e.g., one identity per channel/handle).

### 2.3 Performance & Load Tests
**Tools**: `Locust` or `k6`

- **Ingestion Load**: Simulate 50 concurrent video uploads.
- **Analytics Queries**: Test `North Star Metrics` query latency with 1M+ events.
- **Goal**: Dashboard queries < 500ms.

---

## 3. Frontend Testing Plan

### 3.1 Unit Tests (Jest/Vitest)
**Location**: `Frontend/tests/unit/`

- **Components**:
    - Test `OverviewDashboard` rendering with empty/loading/error states.
    - Test `ContentSingle` metric formatting (e.g., "1.2k views").
- **Hooks**:
    - Test custom hooks for data fetching (`useNorthStarMetrics`).

### 3.2 E2E Tests (Playwright/Cypress)
**Location**: `Frontend/tests/e2e/`

- **Critical Flows**:
    - **Login**: User logs in -> Redirected to Dashboard.
    - **Connect Account**: User clicks "Connect Instagram" -> Mock OAuth flow -> Success toast.
    - **Create Content**: User uploads video -> Selects platforms -> Clicks "Publish" -> Verify "Scheduled" status.
    - **View Analytics**: User navigates to "Content Single" -> Verifies charts load.

### 3.3 Visual Regression Tests (Storybook/Percy)
- Capture snapshots of key components (`NorthStarMetricCard`, `ContentVariantRow`).
- Prevent UI regressions on layout changes.

---

## 4. AI & Analytics Verification

### 4.1 Insight Engine Verification
- **Scenario**: "Retention Drop"
    - Input: Retention curve drops at 3.2s.
    - Expected Insight: "Drop coincides with screen recording switch."
- **Scenario**: "High Engagement"
    - Input: 50 comments with "Tech" keyword.
    - Expected Insight: "CTA 'Comment Tech' performing 2x above average."

### 4.2 Content Brief Generation
- **Input**: Segment "IG Superfans".
- **Verify**: Output contains "IG Reels" as recommended format and "Pain Point" hook.

---

## 5. Automation Strategy
- **CI/CD**: Run Unit + Integration tests on every PR.
- **Nightly**: Run full E2E suite against Staging.
- **Monitoring**: Alert on `ingestion_failure_rate` > 1%.
