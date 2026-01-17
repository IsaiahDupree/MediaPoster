# PRD: Content Ops Controller - Test Specification

**Companion to:** `PRD_CONTENT_OPS_CONTROLLER.md`, `PRD_CONTENT_OPS_TECHNICAL.md`  
**Version:** 1.0 | **Updated:** 2026-01-16

---

## 1. Test Philosophy

### 1.1 Principles

- **No Skips:** Every test must pass or fail with a clear error - never silently skip
- **Real AI Calls:** Use actual OpenAI API for generation tests (not mocks)
- **Attribution Integrity:** Every touchpoint must trace back to prompt/template/offer
- **Regression Prevention:** New templates must not break existing winners

### 1.2 Test Pyramid

```
                    ┌─────────────┐
                    │   E2E Tests │  (5%)
                    │  Full loops │
                    └──────┬──────┘
                  ┌────────┴────────┐
                  │ Integration Tests│ (25%)
                  │ Service + DB + API│
                  └────────┬─────────┘
            ┌──────────────┴──────────────┐
            │       Unit Tests             │ (70%)
            │ Functions, Classes, Logic    │
            └──────────────────────────────┘
```

---

## 2. Unit Tests

### 2.1 FATE Scoring Tests

**File:** `tests/unit/test_fate_scoring.py`

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| `test_detect_focus_hook` | "Most founders fail because..." | F score > 0.5 |
| `test_detect_authority_proof` | "I've helped 127 founders..." | A score > 0.6 |
| `test_detect_tribe_identity` | "If you're a bootstrapper..." | T score > 0.5 |
| `test_detect_emotion_story` | "I was broke, desperate..." | E score > 0.6 |
| `test_combined_fate_score` | Full FATE-aligned post | All scores balanced |
| `test_missing_authority` | Post with no proof | A score < 0.3 |
| `test_weak_hook` | Generic opener | F score < 0.3 |

```python
class TestFATEScoring:
    def test_detect_focus_hook(self):
        text = "Most founders fail at validation because they ask the wrong question."
        score = fate_scorer.score_focus(text)
        assert score > 0.5, f"Focus score {score} should be > 0.5"
    
    def test_combined_fate_balanced(self):
        text = """Most founders fail at validation because they ask the wrong question.
        After helping 127 founders, I found the real pattern.
        If you're bootstrapping, you've felt this pain.
        I wasted 6 months before I learned this."""
        scores = fate_scorer.score_all(text)
        assert all(s > 0.4 for s in scores.values()), "All FATE elements should be present"
```

---

### 2.2 Awareness Level Classification Tests

**File:** `tests/unit/test_awareness_classifier.py`

| Test Case | Input | Expected Level |
|-----------|-------|----------------|
| `test_classify_unaware` | Educational content, no product | `unaware` |
| `test_classify_problem_aware` | Pain-focused, no solution | `problem_aware` |
| `test_classify_solution_aware` | Comparison content | `solution_aware` |
| `test_classify_product_aware` | Feature/benefit focused | `product_aware` |
| `test_classify_most_aware` | Direct CTA, urgency | `most_aware` |

```python
class TestAwarenessClassifier:
    def test_classify_problem_aware(self):
        text = "Tired of spending hours on validation? Here's why it keeps failing..."
        level = awareness_classifier.classify(text)
        assert level == "problem_aware"
    
    def test_classify_product_aware(self):
        text = "KeywordRadar shows you exactly which keywords have demand. Here's how it works..."
        level = awareness_classifier.classify(text)
        assert level == "product_aware"
```

---

### 2.3 Template Validation Tests

**File:** `tests/unit/test_template_validation.py`

| Test Case | Description |
|-----------|-------------|
| `test_template_has_required_variables` | All variables in prompt_text exist in schema |
| `test_template_fate_weights_sum` | FATE weights are valid (0-1 range) |
| `test_template_awareness_valid` | Awareness level is valid enum |
| `test_template_cta_strength_valid` | CTA strength is none/soft/direct |
| `test_template_no_banned_phrases` | No blocklist phrases in template |

```python
class TestTemplateValidation:
    def test_template_has_required_variables(self):
        template = Template(prompt_text="Write about {topic} for {audience}")
        missing = template.get_missing_variables({"topic": "x"})
        assert "audience" in missing
    
    def test_fate_weights_valid(self):
        template = Template(fate_weights={"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2})
        assert template.validate_fate_weights()
```

---

### 2.4 Scoring Function Tests

**File:** `tests/unit/test_scoring.py`

| Test Case | Description |
|-----------|-------------|
| `test_rate_calculation` | Rates computed correctly from raw metrics |
| `test_z_score_normalization` | Z-scores computed against baseline |
| `test_reward_function` | Weighted score computed correctly |
| `test_winner_label_threshold` | Winners labeled correctly |
| `test_loser_label_threshold` | Losers labeled correctly |
| `test_zero_impressions_handling` | No division by zero |

```python
class TestScoring:
    def test_rate_calculation(self):
        metrics = {"likes": 50, "impressions": 1000}
        rate = scorer.compute_like_rate(metrics)
        assert rate == 0.05
    
    def test_zero_impressions_handling(self):
        metrics = {"likes": 50, "impressions": 0}
        rate = scorer.compute_like_rate(metrics)
        assert rate == 0.0  # Not error
```

---

### 2.5 Shortlink Attribution Tests

**File:** `tests/unit/test_attribution.py`

| Test Case | Description |
|-----------|-------------|
| `test_shortlink_encodes_all_ids` | UTM contains touchpoint, offer, template, icp |
| `test_shortlink_decodes_correctly` | IDs extracted from click log |
| `test_utm_format_valid` | UTM params follow spec |
| `test_click_maps_to_touchpoint` | Click event linked to correct touchpoint |

```python
class TestAttribution:
    def test_shortlink_encodes_all_ids(self):
        link = shortlink_service.create(
            destination="https://keywordradar.app",
            touchpoint_id="tp_123",
            offer_id="offer_456",
            template_id="tpl_789",
            icp_id="icp_abc"
        )
        assert "tp_123" in link.utm_id
        assert link.url.startswith("https://r.yourdomain.com/")
```

---

## 3. Integration Tests

### 3.1 Generation Pipeline Tests

**File:** `tests/integration/test_generation_pipeline.py`

| Test Case | Description |
|-----------|-------------|
| `test_slot_to_draft_pipeline` | Slot → Template selection → Generation → Draft |
| `test_generation_uses_correct_template` | Selected template matches slot awareness |
| `test_generation_includes_offer_context` | Offer details injected correctly |
| `test_generation_respects_voice_rules` | No banned phrases in output |
| `test_generation_creates_prompt_run` | PromptRun record created with full context |
| `test_multiple_variants_generated` | Requested variant count produced |

```python
class TestGenerationPipeline:
    async def test_slot_to_draft_pipeline(self):
        slot = Slot(
            awareness_level="solution_aware",
            target_offer_id="offer_keywordradar",
            target_icp_id="icp_indies"
        )
        drafts = await generation_service.generate_from_slot(slot, variants=3)
        
        assert len(drafts) == 3
        for draft in drafts:
            assert draft.prompt_run_id is not None
            assert draft.offer_id == "offer_keywordradar"
```

---

### 3.2 QA Gate Tests

**File:** `tests/integration/test_qa_gate.py`

| Test Case | Description |
|-----------|-------------|
| `test_qa_passes_clean_draft` | Valid draft passes QA |
| `test_qa_blocks_banned_phrases` | Draft with banned phrase blocked |
| `test_qa_blocks_spam_patterns` | Too many CTAs blocked |
| `test_qa_blocks_unverified_claims` | Claims without proof flagged |
| `test_qa_routes_to_approval_queue` | Uncertain drafts queued for review |
| `test_qa_auto_publishes_safe_content` | Safe content auto-approved |

```python
class TestQAGate:
    async def test_qa_blocks_banned_phrases(self):
        draft = Draft(text="This is a GUARANTEED way to make money fast!")
        result = await qa_service.check(draft)
        
        assert result.decision == "blocked"
        assert "banned_phrase" in result.reasons
    
    async def test_qa_routes_to_approval(self):
        draft = Draft(text="I made $50,000 in 30 days with this method...")
        result = await qa_service.check(draft)
        
        assert result.decision == "needs_approval"
        assert "unverified_claim" in result.reasons
```

---

### 3.3 Publishing Pipeline Tests

**File:** `tests/integration/test_publishing_pipeline.py`

| Test Case | Description |
|-----------|-------------|
| `test_publish_creates_touchpoint` | Touchpoint record created |
| `test_publish_stores_platform_id` | Platform object ID saved |
| `test_publish_creates_shortlink` | Shortlink generated for CTA |
| `test_publish_respects_rate_limit` | Rate limited requests queued |
| `test_publish_handles_api_error` | API errors logged and retried |

```python
class TestPublishingPipeline:
    async def test_publish_creates_touchpoint(self):
        draft = await create_test_draft()
        result = await publisher_service.publish(draft)
        
        touchpoint = await db.get_touchpoint(result.touchpoint_id)
        assert touchpoint is not None
        assert touchpoint.platform_object_id is not None
        assert touchpoint.prompt_run_id == draft.prompt_run_id
```

---

### 3.4 Metrics Collection Tests

**File:** `tests/integration/test_metrics_collection.py`

| Test Case | Description |
|-----------|-------------|
| `test_metrics_snapshot_at_intervals` | Snapshots at 1h, 6h, 24h, 72h, 7d |
| `test_metrics_stores_all_fields` | All metric fields captured |
| `test_metrics_merges_shortlink_clicks` | Platform + shortlink clicks merged |
| `test_metrics_handles_api_unavailable` | Graceful handling of API errors |
| `test_metrics_triggers_scoring` | Score recompute triggered after snapshot |

```python
class TestMetricsCollection:
    async def test_metrics_snapshot_at_intervals(self):
        post = await create_published_post()
        
        # Simulate 1h snapshot
        await metrics_service.snapshot(post.touchpoint_id, window="1h")
        snapshot = await db.get_latest_snapshot(post.touchpoint_id)
        
        assert snapshot is not None
        assert snapshot.metrics.get("impressions") is not None
```

---

### 3.5 Scoring & Learning Tests

**File:** `tests/integration/test_scoring_learning.py`

| Test Case | Description |
|-----------|-------------|
| `test_score_computed_from_metrics` | Score calculated correctly |
| `test_winner_updates_leaderboard` | Winner template score increases |
| `test_loser_reduces_allocation` | Loser template allocation decreases |
| `test_template_fork_created` | Winner fork created for A/B test |
| `test_leaderboard_by_offer` | Leaderboard filtered by offer |
| `test_leaderboard_by_icp` | Leaderboard filtered by ICP |

```python
class TestScoringLearning:
    async def test_winner_updates_leaderboard(self):
        # Create high-performing post
        post = await create_post_with_metrics(
            likes=200, replies=50, impressions=5000, clicks=150
        )
        
        await scorer_service.compute(post.touchpoint_id)
        
        leaderboard = await learner_service.get_template_leaderboard()
        template_stats = leaderboard.get(post.template_id)
        
        assert template_stats.avg_score_24h > 1.0  # Above average
```

---

### 3.6 Inbound Handling Tests

**File:** `tests/integration/test_inbound_handling.py`

| Test Case | Description |
|-----------|-------------|
| `test_comment_ingested_as_touchpoint` | Comment creates touchpoint |
| `test_dm_ingested_with_context` | DM includes source post reference |
| `test_keyword_dm_triggers_flow` | "RADAR" keyword starts DM flow |
| `test_response_uses_correct_template` | Response matches intent classification |
| `test_dm_permission_gate_enforced` | No links before consent |

```python
class TestInboundHandling:
    async def test_keyword_dm_triggers_flow(self):
        inbound = InboundItem(
            channel="dm",
            text="RADAR",
            author_handle="@someone",
            context={"source_post_id": "post_123"}
        )
        
        await inbound_service.ingest(inbound)
        response = await responder_service.get_pending_response(inbound.touchpoint_id)
        
        assert response is not None
        assert "checklist" in response.text.lower() or "sending" in response.text.lower()
```

---

## 4. End-to-End Tests

### 4.1 Full Feedback Loop Test

**File:** `tests/e2e/test_full_loop.py`

```python
class TestFullFeedbackLoop:
    async def test_complete_loop_plan_to_learn(self):
        """
        Full loop: Plan → Generate → Publish → Metrics → Score → Learn
        """
        # 1. Generate weekly plan
        plan = await planner_service.generate(
            week_start="2026-01-20",
            goal_mode="leads",
            channels=["x"]
        )
        assert len(plan.slots) > 0
        
        # 2. Execute first slot
        slot = plan.slots[0]
        drafts = await generation_service.generate_from_slot(slot, variants=3)
        assert len(drafts) == 3
        
        # 3. QA check
        qa_result = await qa_service.check(drafts[0])
        assert qa_result.decision in ["auto_publish", "needs_approval"]
        
        # 4. Publish (mock platform for E2E)
        if qa_result.decision == "auto_publish":
            publish_result = await publisher_service.publish(drafts[0])
            assert publish_result.touchpoint_id is not None
            
            # 5. Simulate metrics (mock)
            await mock_metrics_service.inject_metrics(
                publish_result.touchpoint_id,
                impressions=5000, likes=100, replies=20, clicks=50
            )
            
            # 6. Score
            await scorer_service.compute(publish_result.touchpoint_id)
            score = await db.get_score(publish_result.touchpoint_id)
            assert score.score_24h > 0
            
            # 7. Learn
            await learner_service.run()
            leaderboard = await learner_service.get_template_leaderboard()
            assert slot.template_id in leaderboard
```

---

### 4.2 Multi-Platform Post Test

**File:** `tests/e2e/test_multi_platform.py`

```python
class TestMultiPlatform:
    async def test_same_content_across_platforms(self):
        """
        Generate once, adapt and publish to multiple platforms
        """
        platforms = ["x", "threads", "linkedin"]
        
        for platform in platforms:
            slot = Slot(
                platform=platform,
                awareness_level="solution_aware",
                target_offer_id="offer_keywordradar"
            )
            
            drafts = await generation_service.generate_from_slot(slot, variants=1)
            assert len(drafts) == 1
            
            # Verify platform-specific adaptations
            if platform == "x":
                assert len(drafts[0].text) <= 280
            elif platform == "linkedin":
                assert len(drafts[0].text) <= 3000
```

---

### 4.3 DM Conversation Flow Test

**File:** `tests/e2e/test_dm_flow.py`

```python
class TestDMFlow:
    async def test_keyword_to_email_capture(self):
        """
        Full DM flow: Keyword → Resource → Qualification → Email capture
        """
        # 1. User sends keyword
        inbound1 = InboundItem(channel="dm", text="RADAR", author_handle="@testuser")
        await inbound_service.ingest(inbound1)
        
        # 2. System responds with resource
        response1 = await responder_service.process_next()
        assert "sending" in response1.text.lower() or "here" in response1.text.lower()
        assert "http" not in response1.text  # No link yet (permission gate)
        
        # 3. User confirms interest
        inbound2 = InboundItem(channel="dm", text="Yes please!", author_handle="@testuser")
        await inbound_service.ingest(inbound2)
        
        # 4. System sends resource with link
        response2 = await responder_service.process_next()
        assert "http" in response2.text  # Link now allowed
        
        # 5. User provides email
        inbound3 = InboundItem(channel="dm", text="test@example.com", author_handle="@testuser")
        await inbound_service.ingest(inbound3)
        
        # 6. Verify email captured
        contact = await db.get_contact_by_handle("@testuser")
        assert contact.email == "test@example.com"
```

---

## 5. Platform Adapter Tests

### 5.1 X/Twitter Adapter Tests

**File:** `tests/adapters/test_x_adapter.py`

| Test Case | Description |
|-----------|-------------|
| `test_publish_post` | Post published successfully |
| `test_publish_thread` | Multi-tweet thread published |
| `test_reply_to_post` | Reply published correctly |
| `test_fetch_metrics` | Metrics retrieved correctly |
| `test_fetch_inbound_comments` | Comments fetched |
| `test_send_dm` | DM sent successfully |
| `test_rate_limit_handling` | 429 handled with backoff |
| `test_auth_refresh` | Token refreshed before expiry |

---

### 5.2 Instagram Adapter Tests

**File:** `tests/adapters/test_instagram_adapter.py`

| Test Case | Description |
|-----------|-------------|
| `test_publish_via_api` | Post via Graph API |
| `test_dm_via_safari` | DM via Safari automation |
| `test_get_notifications` | Notifications retrieved |
| `test_get_conversations` | DM list retrieved |
| `test_read_messages` | Messages read from conversation |
| `test_login_check` | Login status verified |

---

### 5.3 TikTok Adapter Tests

**File:** `tests/adapters/test_tiktok_adapter.py`

| Test Case | Description |
|-----------|-------------|
| `test_publish_video_api` | Video published via API |
| `test_dm_via_safari` | DM via Safari automation |
| `test_get_notifications` | Notifications retrieved |
| `test_engagement_like` | Like action works |

---

## 6. Safety & Edge Case Tests

### 6.1 Rate Limiting Tests

**File:** `tests/safety/test_rate_limiting.py`

| Test Case | Description |
|-----------|-------------|
| `test_platform_rate_limit_respected` | Global limit not exceeded |
| `test_account_rate_limit_respected` | Per-account limit not exceeded |
| `test_dm_user_cooldown` | Per-user DM cooldown enforced |
| `test_offer_fatigue_limit` | Max CTAs per offer/day enforced |
| `test_backoff_on_429` | Exponential backoff on rate limit |

---

### 6.2 Permission Gate Tests

**File:** `tests/safety/test_permission_gates.py`

| Test Case | Description |
|-----------|-------------|
| `test_no_dm_link_without_consent` | Links blocked until consent |
| `test_stop_command_honored` | "stop" marks contact as do-not-message |
| `test_blocked_user_excluded` | Blocked users not messaged |
| `test_spam_pattern_blocked` | Spammy messages blocked |

---

### 6.3 Error Handling Tests

**File:** `tests/safety/test_error_handling.py`

| Test Case | Description |
|-----------|-------------|
| `test_api_timeout_retried` | Timeouts trigger retry |
| `test_api_error_logged` | Errors logged with context |
| `test_dead_letter_queue` | Failed jobs go to DLQ |
| `test_partial_failure_recovery` | Batch continues after single failure |
| `test_no_silent_skips` | Every failure raises error |

---

## 7. Performance Tests

### 7.1 Throughput Tests

**File:** `tests/performance/test_throughput.py`

| Test Case | Target |
|-----------|--------|
| `test_generation_latency` | < 5s per draft |
| `test_publish_latency` | < 2s per post |
| `test_metrics_collection_latency` | < 10s per batch |
| `test_scoring_latency` | < 1s per post |
| `test_concurrent_generations` | 10 concurrent without degradation |

---

### 7.2 Load Tests

**File:** `tests/performance/test_load.py`

| Test Case | Target |
|-----------|--------|
| `test_weekly_plan_generation` | 200 slots in < 30s |
| `test_daily_execution_load` | 50 posts/day without issues |
| `test_metrics_batch_size` | 1000 snapshots in < 5min |
| `test_leaderboard_query` | < 100ms with 10K templates |

---

## 8. Test Fixtures & Mocks

### 8.1 Test Fixtures

```python
# tests/fixtures.py

@pytest.fixture
def sample_template():
    return Template(
        template_id="tpl_test",
        awareness_level="solution_aware",
        fate_weights={"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2},
        prompt_text="Write about {topic} for {audience}..."
    )

@pytest.fixture
def sample_offer():
    return Offer(
        offer_id="offer_test",
        brand_id="brand_test",
        name="Test Product",
        promise="Solve your problem fast",
        landing_url="https://test.com"
    )

@pytest.fixture
def sample_icp():
    return ICP(
        icp_id="icp_test",
        offer_id="offer_test",
        name="Indie Founders",
        pains=["validation takes too long", "no feedback"],
        desired_outcomes=["launch faster", "real data"]
    )
```

### 8.2 Mock Services

```python
# tests/mocks.py

class MockPlatformAdapter:
    async def publishPost(self, input):
        return PublishResult(
            platform_object_id=f"mock_{uuid.uuid4()}",
            published_at=datetime.utcnow().isoformat()
        )
    
    async def fetchMetrics(self, params):
        return MetricsResult(
            impressions=random.randint(1000, 10000),
            likes=random.randint(10, 200),
            replies=random.randint(1, 50)
        )

class MockOpenAIService:
    async def generate(self, prompt, **kwargs):
        # Use real API (user preference: no mocks for AI)
        return await real_openai_service.generate(prompt, **kwargs)
```

---

## 9. CI/CD Integration

### 9.1 Test Commands

```bash
# Run all tests
pytest tests/ -v

# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v --tb=short

# E2E tests (slow, requires services)
pytest tests/e2e/ -v --tb=long

# Platform adapter tests
pytest tests/adapters/ -v

# Safety tests
pytest tests/safety/ -v

# Performance tests
pytest tests/performance/ -v --benchmark
```

### 9.2 CI Pipeline Stages

```yaml
stages:
  - lint
  - unit-tests
  - integration-tests
  - e2e-tests
  - deploy

unit-tests:
  script:
    - pytest tests/unit/ -v --cov=services --cov-report=xml
  coverage:
    minimum: 80%

integration-tests:
  services:
    - postgres:14
    - redis:7
  script:
    - pytest tests/integration/ -v

e2e-tests:
  when: manual
  script:
    - pytest tests/e2e/ -v
```

---

## 10. Test Coverage Requirements

| Component | Minimum Coverage |
|-----------|------------------|
| FATE Scoring | 90% |
| Awareness Classifier | 90% |
| Template Validation | 95% |
| Scoring Functions | 95% |
| Attribution/Shortlinks | 95% |
| Generation Pipeline | 85% |
| QA Gate | 90% |
| Publishing Pipeline | 80% |
| Platform Adapters | 75% |
| Safety Gates | 95% |

---

## 11. Test Data Management

### 11.1 Seed Data

```python
# tests/seed_data.py

SEED_TEMPLATES = [
    {"template_id": "tpl_001", "awareness_level": "unaware", ...},
    {"template_id": "tpl_002", "awareness_level": "problem_aware", ...},
    # ... 25 templates
]

SEED_OFFERS = [
    {"offer_id": "offer_everreach", "brand_id": "brand_everreach", ...},
    {"offer_id": "offer_keywordradar", "brand_id": "brand_keywordradar", ...},
    # ... all offers
]

SEED_ICPS = [
    {"icp_id": "icp_indies", "offer_id": "offer_keywordradar", ...},
    # ... all ICPs
]
```

### 11.2 Test Database

```bash
# Setup test database
docker-compose -f docker-compose.test.yml up -d

# Run migrations
supabase db push --db-url postgresql://postgres:postgres@localhost:54322/postgres

# Seed test data
python tests/seed_data.py
```

---

## 12. Acceptance Criteria Summary

| Feature | Acceptance Criteria |
|---------|---------------------|
| **Generation** | 3 variants per slot, all with valid FATE scores |
| **QA Gate** | 100% of banned phrases blocked, 0% false positives on clean content |
| **Publishing** | 99% success rate, all touchpoints attributed |
| **Metrics** | 5 snapshot windows, all fields captured |
| **Scoring** | Winners identified within 24h, leaderboard updated |
| **Learning** | Top templates get 70% allocation, losers < 5% |
| **DMs** | Permission gate 100% enforced, "stop" honored |
| **Rate Limits** | 0 platform violations, graceful degradation |
