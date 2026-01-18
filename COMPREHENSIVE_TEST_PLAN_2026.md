# MediaPoster Comprehensive Test Plan 2026

Generated: January 13, 2026

## Executive Summary

This document outlines a comprehensive testing strategy for MediaPoster, identifying gaps in current coverage and providing specific test cases to implement. The codebase currently has **~7,600+ test functions** across **331 test files**, but significant gaps exist in frontend testing, service unit tests, and API contract coverage.

---

## Current State Analysis

### Existing Test Infrastructure

| Layer | Framework | Files | Approx Tests | Coverage |
|-------|-----------|-------|--------------|----------|
| Backend Unit/Integration | pytest | 200+ | ~7,000 | Good |
| Backend E2E | pytest | 20+ | ~200 | Moderate |
| Frontend E2E | Playwright | 45 | ~300 | Good |
| Dashboard Unit | Vitest | 6 | ~50 | **Poor** |
| Automation | pytest | 22 | ~100 | Moderate |

### Gap Summary

| Area | Current | Needed | Priority |
|------|---------|--------|----------|
| Dashboard service tests | 0 | 15+ | **HIGH** |
| Dashboard hook tests | 0 | 6 | **HIGH** |
| Dashboard component tests | 6 | 60+ | **HIGH** |
| API contract tests | ~40 | 140+ | **MEDIUM** |
| Service unit tests | ~60% | 90%+ | **MEDIUM** |
| Security tests | 5 | 20+ | **HIGH** |
| Load/stress tests | 2 | 10+ | **LOW** |

---

## Part 1: Dashboard/Frontend Tests (HIGH PRIORITY)

### 1.1 Service Layer Tests (`dashboard/lib/services/__tests__/`)

These services have **zero tests** - each needs unit tests:

#### `api-client.test.ts`
```typescript
// Tests needed:
- test_api_client_get_request_success
- test_api_client_post_request_success
- test_api_client_handles_network_error
- test_api_client_handles_401_unauthorized
- test_api_client_handles_500_server_error
- test_api_client_retries_on_failure
- test_api_client_timeout_handling
- test_api_client_request_cancellation
```

#### `schedule-service.test.ts`
```typescript
// Tests needed:
- test_get_scheduled_posts_returns_array
- test_create_scheduled_post_validates_input
- test_update_scheduled_post_success
- test_delete_scheduled_post_success
- test_get_schedule_by_date_range
- test_schedule_conflict_detection
- test_bulk_schedule_operations
```

#### `media-service.test.ts`
```typescript
// Tests needed:
- test_fetch_media_library_paginated
- test_upload_media_file
- test_delete_media_file
- test_get_media_by_id
- test_filter_media_by_type
- test_search_media_by_keyword
- test_media_thumbnail_generation
```

#### `curation-service.test.ts`
```typescript
// Tests needed:
- test_get_curated_content
- test_save_curation_preferences
- test_auto_curate_by_score
- test_manual_curation_override
- test_curation_persistence
- test_batch_curation_operations
```

#### `blotato-service.test.ts`
```typescript
// Tests needed:
- test_get_connected_accounts
- test_publish_to_platform
- test_schedule_via_blotato
- test_handle_rate_limits
- test_oauth_refresh_flow
```

#### `instagram-trends-service.test.ts`
```typescript
// Tests needed:
- test_fetch_trending_audio
- test_fetch_trending_hashtags
- test_trend_velocity_calculation
- test_trend_cache_expiration
- test_multi_region_trends
```

### 1.2 Hook Tests (`dashboard/lib/hooks/__tests__/`)

#### `useApi.test.ts`
```typescript
// Tests needed:
- test_useApi_initial_loading_state
- test_useApi_successful_fetch
- test_useApi_error_handling
- test_useApi_refetch_functionality
- test_useApi_cache_behavior
```

#### `useBackendConnection.test.ts`
```typescript
// Tests needed:
- test_connection_status_connected
- test_connection_status_disconnected
- test_auto_reconnect_on_disconnect
- test_connection_health_check_interval
- test_fallback_when_backend_down
```

#### `useEventBus.test.ts`
```typescript
// Tests needed:
- test_subscribe_to_event
- test_unsubscribe_on_unmount
- test_publish_event
- test_event_filtering
- test_multiple_subscribers
- test_event_replay
```

#### `usePaginatedFetch.test.ts`
```typescript
// Tests needed:
- test_initial_page_load
- test_next_page_fetch
- test_previous_page_fetch
- test_page_size_change
- test_total_count_tracking
- test_loading_states
```

### 1.3 Page Component Tests

Each of the **60+ dashboard pages** needs at least smoke tests. Priority pages:

| Page | File | Tests Needed |
|------|------|--------------|
| Schedule | `schedule/page.tsx` | 10 |
| Media Library | `media/page.tsx` | 8 |
| Posted Content | `posted-content/page.tsx` | 8 |
| Analytics | `analytics/page.tsx` | 6 |
| Narrative Builder | `narrative-builder/page.tsx` | 10 |
| Competitors | `competitors/page.tsx` | 6 |
| Comment Automation | `comment-automation/page.tsx` | 8 |
| Settings | `settings/page.tsx` | 5 |
| Import (iOS/Android) | `import/*/page.tsx` | 6 |
| Trends | `trends/page.tsx` | 6 |

---

## Part 2: Backend API Contract Tests (MEDIUM PRIORITY)

### 2.1 Missing Endpoint Contract Tests

Create `Backend/tests/contract/` tests for these endpoints:

#### Critical Endpoints (Must Have)

| Endpoint | File | Test File Needed |
|----------|------|------------------|
| `/api/schedule/*` | `schedule.py` | `test_schedule_contract.py` |
| `/api/publish/*` | `publishing.py` | `test_publish_contract.py` |
| `/api/blotato/*` | `blotato_router.py` | `test_blotato_contract.py` |
| `/api/media/*` | `videos.py` | `test_media_contract.py` |
| `/api/analytics/*` | `social_analytics.py` | `test_analytics_contract.py` |
| `/api/automation/*` | `automation.py` | `test_automation_contract.py` |

#### Test Cases per Endpoint Contract

```python
# Example: test_schedule_contract.py
class TestScheduleAPIContract:
    def test_get_schedule_returns_correct_schema(self):
        """Response must match ScheduleResponse schema"""
        
    def test_create_schedule_validates_required_fields(self):
        """Must reject missing platform, content_id, scheduled_time"""
        
    def test_create_schedule_validates_future_time(self):
        """Must reject past scheduled times"""
        
    def test_update_schedule_partial_update(self):
        """PATCH should allow partial updates"""
        
    def test_delete_schedule_returns_204(self):
        """DELETE should return 204 No Content"""
        
    def test_bulk_schedule_max_limit(self):
        """Bulk operations capped at 100 items"""
        
    def test_schedule_conflict_error_code(self):
        """Conflicting times return 409 Conflict"""
```

### 2.2 API Endpoints Needing Tests (140 total)

High priority (40 endpoints without dedicated tests):

| Category | Endpoints | Priority |
|----------|-----------|----------|
| Narrative Builder | 8 | HIGH |
| Video Generation | 12 | HIGH |
| Trend Intelligence | 10 | MEDIUM |
| Competitor Audit | 8 | MEDIUM |
| Content Pipeline | 10 | MEDIUM |
| SFX Library | 6 | LOW |
| Voice Cloning | 4 | LOW |

---

## Part 3: Backend Service Unit Tests (MEDIUM PRIORITY)

### 3.1 Services Needing Unit Tests

| Service File | Current Tests | Needed Tests | Priority |
|--------------|---------------|--------------|----------|
| `post_scheduler.py` | 27 | 40 | HIGH |
| `publish_service.py` | 15 | 30 | HIGH |
| `blotato_api.py` | 10 | 25 | HIGH |
| `safari_app_controller.py` | 0 | 20 | HIGH |
| `transcription_adapter.py` | 5 | 15 | MEDIUM |
| `webhooks.py` | 0 | 12 | MEDIUM |
| `email_service.py` | 0 | 10 | LOW |
| `oauth_manager.py` | 3 | 15 | MEDIUM |
| `variant_generator.py` | 0 | 8 | LOW |

### 3.2 Specific Test Cases for Critical Services

#### `test_post_scheduler_unit.py` (New Tests)
```python
# Tests to add:
- test_scheduler_respects_platform_rate_limits
- test_scheduler_handles_timezone_correctly
- test_scheduler_retries_failed_posts
- test_scheduler_marks_expired_posts
- test_scheduler_handles_account_disconnection
- test_scheduler_concurrent_post_limit
- test_scheduler_gap_between_posts
- test_scheduler_priority_queue_ordering
```

#### `test_safari_app_controller.py` (New File)
```python
# Tests to add:
- test_safari_launches_successfully
- test_safari_navigates_to_url
- test_safari_javascript_injection
- test_safari_cookie_management
- test_safari_handles_timeout
- test_safari_session_persistence
- test_safari_element_click
- test_safari_form_fill
- test_safari_screenshot_capture
```

#### `test_webhooks_unit.py` (New File)
```python
# Tests to add:
- test_webhook_signature_validation
- test_webhook_retry_on_failure
- test_webhook_timeout_handling
- test_webhook_payload_serialization
- test_webhook_rate_limiting
- test_webhook_event_filtering
```

---

## Part 4: Security Tests (HIGH PRIORITY)

### 4.1 Authentication Tests

```python
# Backend/tests/security/test_auth.py
class TestAuthentication:
    def test_unauthenticated_request_returns_401(self):
        pass
    def test_expired_token_returns_401(self):
        pass
    def test_invalid_token_format_returns_401(self):
        pass
    def test_token_refresh_before_expiry(self):
        pass
    def test_logout_invalidates_token(self):
        pass
```

### 4.2 Authorization Tests

```python
# Backend/tests/security/test_authorization.py
class TestAuthorization:
    def test_user_cannot_access_other_user_content(self):
        pass
    def test_admin_can_access_all_content(self):
        pass
    def test_api_key_scope_restrictions(self):
        pass
    def test_rate_limit_per_user(self):
        pass
```

### 4.3 Input Validation Tests

```python
# Backend/tests/security/test_input_validation.py
class TestInputValidation:
    def test_sql_injection_prevention(self):
        pass
    def test_xss_prevention_in_content(self):
        pass
    def test_path_traversal_prevention(self):
        pass
    def test_file_upload_type_validation(self):
        pass
    def test_max_payload_size_enforcement(self):
        pass
```

### 4.4 API Key Security

```python
# Backend/tests/security/test_api_keys.py
class TestAPIKeySecurity:
    def test_api_key_not_logged(self):
        pass
    def test_api_key_rotation(self):
        pass
    def test_revoked_key_rejected(self):
        pass
    def test_key_scope_enforcement(self):
        pass
```

---

## Part 5: Integration & E2E Tests

### 5.1 Critical User Flows (E2E)

| Flow | Current | Needed | File |
|------|---------|--------|------|
| Upload → Analyze → Schedule → Publish | Partial | Complete | `test_full_pipeline_e2e.py` |
| Import from iPhone → Library | Partial | Complete | `test_ios_import_e2e.py` |
| Competitor Research → Brief | None | New | `test_competitor_to_brief_e2e.py` |
| Trend Discovery → Content Creation | None | New | `test_trend_to_content_e2e.py` |
| Narrative Builder full flow | Partial | Complete | `test_narrative_e2e.py` |

### 5.2 Cross-Platform Publishing Tests

```python
# Backend/tests/e2e/test_multi_platform_publish.py
class TestMultiPlatformPublish:
    def test_publish_to_tiktok_instagram_simultaneously(self):
        pass
    def test_platform_specific_formatting(self):
        pass
    def test_failed_platform_doesnt_block_others(self):
        pass
    def test_metrics_collection_after_publish(self):
        pass
```

---

## Part 6: Performance & Load Tests

### 6.1 API Performance Benchmarks

| Endpoint | Target | Current | Test |
|----------|--------|---------|------|
| GET /api/media | <200ms | Unknown | `test_media_list_performance.py` |
| GET /api/schedule | <100ms | Unknown | `test_schedule_performance.py` |
| POST /api/analyze | <5s | Unknown | `test_analyze_performance.py` |
| GET /api/analytics | <500ms | Unknown | `test_analytics_performance.py` |

### 6.2 Load Tests (Locust)

```python
# Backend/tests/load/locustfile.py
class MediaPosterUser(HttpUser):
    @task(3)
    def view_media_library(self):
        self.client.get("/api/media?page=1&limit=50")
    
    @task(2)
    def view_schedule(self):
        self.client.get("/api/schedule")
    
    @task(1)
    def create_scheduled_post(self):
        self.client.post("/api/schedule", json={...})
```

---

## Part 7: Automation Layer Tests

### 7.1 Safari Controller Tests

```python
# Backend/automation/tests/test_safari_controller.py
class TestSafariController:
    def test_safari_initialization(self):
        pass
    def test_navigation_with_wait(self):
        pass
    def test_element_interaction(self):
        pass
    def test_cookie_persistence(self):
        pass
    def test_error_recovery(self):
        pass
```

### 7.2 TikTok Automation Tests

```python
# Backend/automation/tests/test_tiktok_automation.py
class TestTikTokAutomation:
    def test_login_flow_with_session(self):
        pass
    def test_comment_posting(self):
        pass
    def test_dm_sending(self):
        pass
    def test_rate_limit_handling(self):
        pass
    def test_captcha_detection(self):
        pass
```

---

## Implementation Priority

### Phase 1: Critical (Week 1-2)
1. Dashboard service tests (15 test files)
2. Dashboard hook tests (6 test files)
3. Security tests (4 test files)
4. API contract tests for schedule/publish (2 test files)

### Phase 2: Important (Week 3-4)
1. Page component tests (20 priority pages)
2. Remaining API contract tests
3. Safari controller tests
4. E2E critical flows

### Phase 3: Enhancement (Week 5-6)
1. Performance benchmarks
2. Load testing setup
3. Remaining service unit tests
4. Visual regression tests

---

## Test Commands Reference

```bash
# Backend
cd Backend

# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/unit -v
pytest tests/integration -v
pytest tests/security -v
pytest tests/contract -v

# Run with coverage
pytest tests/ --cov=services --cov=api --cov-report=html

# Run marked tests
pytest -m "not slow" tests/
pytest -m "security" tests/

# Dashboard
cd dashboard

# Run Vitest unit tests
npm run test

# Run with coverage
npm run test -- --coverage

# Playwright E2E
cd ..  # root
npx playwright test
npx playwright test --ui  # interactive mode
```

---

## Files to Create

### Immediate (10 files)
1. `dashboard/lib/services/__tests__/api-client.test.ts`
2. `dashboard/lib/services/__tests__/schedule-service.test.ts`
3. `dashboard/lib/services/__tests__/media-service.test.ts`
4. `dashboard/lib/hooks/__tests__/useApi.test.ts`
5. `dashboard/lib/hooks/__tests__/useEventBus.test.ts`
6. `Backend/tests/contract/test_schedule_contract.py`
7. `Backend/tests/contract/test_publish_contract.py`
8. `Backend/tests/security/test_auth.py`
9. `Backend/tests/security/test_input_validation.py`
10. `Backend/automation/tests/test_safari_controller.py`

### Short-term (20 more files)
- Remaining dashboard service tests
- Remaining hook tests
- API contract tests for all critical endpoints
- Page component smoke tests

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Backend test count | ~7,600 | 9,000+ |
| Frontend test count | ~350 | 800+ |
| Code coverage (Backend) | ~60% | 80%+ |
| Code coverage (Frontend) | ~20% | 70%+ |
| Critical path E2E coverage | 50% | 100% |
| Security test coverage | 30% | 90%+ |

---

## Next Steps

1. **Start with Phase 1** - Create the 10 immediate test files
2. **Set up CI/CD test gates** - Require tests to pass before merge
3. **Add coverage reporting** - Track progress over time
4. **Create test fixtures** - Reusable test data and mocks
5. **Document testing patterns** - Ensure consistency across team

