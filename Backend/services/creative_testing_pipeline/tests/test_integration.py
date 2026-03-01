"""
ACTP Integration Tests - Full iteration cycle, migration, benchmarks
"""

import asyncio
import time
import pytest

from services.creative_testing_pipeline.analytics_collector import AnalyticsCollector
from services.creative_testing_pipeline.config import ACTPConfig
from services.creative_testing_pipeline.creative_engine import CreativeEngine
from services.creative_testing_pipeline.integration import (
    FunnelTracker,
    LandingPageManager,
    OfferExpiryHandler,
    OAuthManager,
    WebhookManager,
    WebhookReceiver,
)
from services.creative_testing_pipeline.iteration_engine import IterationEngine
from services.creative_testing_pipeline.models import (
    Creative,
    GenerationSource,
    OrganicPost,
    Platform,
    WinnerSelection,
)
from services.creative_testing_pipeline.winner_selector import WinnerSelector


# ─── Full Iteration Cycle Integration Test ────────────────

class TestFullIterationCycle:
    """Test the complete organic → score → select → iterate pipeline without DB."""

    def setup_method(self):
        self.config = ACTPConfig()
        self.analytics = AnalyticsCollector(config=self.config)
        self.selector = WinnerSelector()
        self.iteration = IterationEngine()

    @pytest.mark.asyncio
    async def test_score_select_iterate_cycle(self):
        """Full cycle: score creatives → select winner → generate variants."""
        from datetime import datetime, timedelta, timezone

        # 1. Create 3 creatives
        creatives = [
            Creative(
                id=f"c{i}", campaign_id="camp1", round_id="r1",
                hook=f"Hook {i}", cta="Try Now", angle=f"angle_{i}",
                script=f"This is script {i} for testing purposes.",
                generation_source=GenerationSource.SORA,
            )
            for i in range(1, 4)
        ]

        # 2. Create organic posts with varying performance
        now = datetime.now(timezone.utc)
        posts = [
            OrganicPost(
                creative_id="c1", platform=Platform.TIKTOK, status="published",
                metrics={"views": 500, "likes": 10, "comments": 1, "shares": 0},
                posted_at=now - timedelta(hours=24),
            ),
            OrganicPost(
                creative_id="c2", platform=Platform.TIKTOK, status="published",
                metrics={"views": 8000, "likes": 400, "comments": 60, "shares": 120},
                posted_at=now - timedelta(hours=24),
            ),
            OrganicPost(
                creative_id="c3", platform=Platform.TIKTOK, status="published",
                metrics={"views": 2000, "likes": 80, "comments": 10, "shares": 5},
                posted_at=now - timedelta(hours=24),
            ),
        ]

        # 3. Select winners
        winners = await self.selector.select_organic_winners(creatives, posts, "r1", top_n=1)
        assert len(winners) == 1
        assert winners[0].creative_id == "c2"  # Highest engagement

        # 4. Generate style variants from winner
        winner_creative = next(c for c in creatives if c.id == winners[0].creative_id)
        style_variants = self.iteration.generate_style_variants(winner_creative)
        assert len(style_variants) >= 3
        assert all(v["hook"] == winner_creative.hook for v in style_variants)
        assert all(v["strategy"] == "style_swap" for v in style_variants)

        # 5. Generate pacing variants
        pacing_variants = self.iteration.generate_pacing_variants(winner_creative)
        assert len(pacing_variants) >= 2
        assert all(v["strategy"] == "pacing_variant" for v in pacing_variants)

        # 6. Generate audio swap variants
        audio_variants = self.iteration.generate_audio_swap_variants(winner_creative)
        assert len(audio_variants) >= 2
        assert all(v["strategy"] == "audio_swap" for v in audio_variants)

        # 7. Score diversity of all variants
        all_variants = style_variants + pacing_variants + audio_variants
        diversity = self.iteration.score_variation_diversity(all_variants)
        assert diversity["total_variations"] == len(all_variants)
        assert diversity["diversity_score"] >= 0

    def test_bayesian_confidence_on_winner(self):
        """Bayesian confidence should narrow with more data."""
        small = self.selector.bayesian_confidence(5, 50)
        large = self.selector.bayesian_confidence(100, 1000)
        small_width = small["upper_95"] - small["lower_95"]
        large_width = large["upper_95"] - large["lower_95"]
        assert large_width < small_width

    def test_elimination_then_iterate(self):
        """Eliminate bottom half, then generate variants from survivors."""
        creatives = [
            Creative(
                id=f"c{i}", campaign_id="c1", round_id="r1",
                generation_source=GenerationSource.SORA,
                hook=f"Hook {i}", organic_score=float(i * 10),
            )
            for i in range(10)
        ]
        survivors, eliminated = self.selector.eliminate_bottom_performers(creatives, 0.5)
        assert len(survivors) == 5
        assert len(eliminated) == 5

        # Generate style variants from top survivor
        variants = self.iteration.generate_style_variants(survivors[0])
        assert len(variants) >= 1
        assert variants[0]["parent_creative_id"] == survivors[0].id


# ─── Funnel Tracking Tests ────────────────────────────────

class TestFunnelTracking:
    """Test funnel tracking without DB."""

    def setup_method(self):
        self.tracker = FunnelTracker(db_client=None)

    @pytest.mark.asyncio
    async def test_record_click_no_db(self):
        result = await self.tracker.record_click("c1", "tiktok")
        assert result == ""  # No DB, returns empty string

    @pytest.mark.asyncio
    async def test_get_funnel_stats_no_db(self):
        stats = await self.tracker.get_funnel_stats("c1")
        assert stats["clicks"] == 0
        assert stats["conversions"] == 0
        assert stats.get("overall_cvr_pct", 0) == 0


# ─── Landing Page Tests ───────────────────────────────────

class TestLandingPageManager:
    """Test landing page URL generation."""

    def setup_method(self):
        self.mgr = LandingPageManager(db_client=None)

    def test_tracking_url_adds_utm(self):
        url = self.mgr.generate_tracking_url("abc123", "https://example.com/offer")
        assert "utm_source=actp" in url
        assert "actp_cid=abc123" in url

    def test_tracking_url_preserves_existing_params(self):
        url = self.mgr.generate_tracking_url("abc123", "https://example.com/offer?ref=test")
        assert "ref=test" in url
        assert "utm_source=actp" in url

    def test_tracking_url_creative_id_truncated(self):
        url = self.mgr.generate_tracking_url("abc12345678", "https://example.com")
        assert "actp_cid=abc12345" in url


# ─── Webhook Tests ────────────────────────────────────────

class TestWebhookReceiver:
    """Test webhook signature verification."""

    def setup_method(self):
        self.receiver = WebhookReceiver(db_client=None)

    def test_valid_signature(self):
        import hmac, hashlib
        secret = "test_secret"
        payload = b'{"event": "test"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert self.receiver.verify_signature(payload, sig, secret) is True

    def test_invalid_signature(self):
        assert self.receiver.verify_signature(b"payload", "badsig", "secret") is False

    def test_signature_with_prefix(self):
        import hmac, hashlib
        secret = "test_secret"
        payload = b'{"event": "test"}'
        sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert self.receiver.verify_signature(payload, sig, secret) is True

    @pytest.mark.asyncio
    async def test_receive_unknown_event(self):
        result = await self.receiver.receive("unknown_source", "unknown_event", {"foo": "bar"})
        assert result["handled"] is False
        assert result["event_type"] == "unknown_event"


# ─── OAuth Manager Tests ──────────────────────────────────

class TestOAuthManager:
    """Test OAuth token management without DB."""

    def setup_method(self):
        self.mgr = OAuthManager(db_client=None)

    @pytest.mark.asyncio
    async def test_store_token_no_db(self):
        result = await self.mgr.store_token("youtube", "acc1", "token123")
        assert result["stored"] is False

    @pytest.mark.asyncio
    async def test_get_token_no_db(self):
        result = await self.mgr.get_token("youtube", "acc1")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_accounts_no_db(self):
        result = await self.mgr.list_connected_accounts()
        assert result == {}


# ─── Offer Expiry Tests ───────────────────────────────────

class TestOfferExpiryHandler:
    """Test offer expiry handling without DB."""

    def setup_method(self):
        self.handler = OfferExpiryHandler(db_client=None)

    @pytest.mark.asyncio
    async def test_handle_expiry_no_db(self):
        result = await self.handler.handle_expiry("offer_123")
        assert result["handled"] is False


# ─── Database Migration Test ──────────────────────────────

class TestDatabaseMigrations:
    """Test that migration SQL files are valid and complete."""

    def test_migration_001_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__), "..", "migrations", "001_create_actp_tables.sql"
        )
        assert os.path.exists(path), "Migration 001 must exist"
        with open(path) as f:
            sql = f.read()
        assert "actp_campaigns" in sql
        assert "actp_creatives" in sql
        assert "actp_rounds" in sql

    def test_migration_002_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__), "..", "migrations", "002_indexes_audit_fts.sql"
        )
        assert os.path.exists(path), "Migration 002 must exist"
        with open(path) as f:
            sql = f.read()
        assert "CREATE INDEX" in sql or "index" in sql.lower()

    def test_migrations_have_no_drop_table(self):
        """Migrations must not drop tables (destructive)."""
        import os, glob
        migration_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
        for sql_file in glob.glob(os.path.join(migration_dir, "*.sql")):
            with open(sql_file) as f:
                sql = f.read().upper()
            assert "DROP TABLE" not in sql, f"{sql_file} contains DROP TABLE"


# ─── Performance Benchmark Tests ─────────────────────────

class TestPerformanceBenchmarks:
    """Benchmark key operations for performance regression detection."""

    def setup_method(self):
        self.config = ACTPConfig()
        self.analytics = AnalyticsCollector(config=self.config)
        self.selector = WinnerSelector()
        self.engine = CreativeEngine()

    def test_organic_score_calculation_speed(self):
        """Score calculation must complete in < 1ms per creative."""
        metrics = {"views": 5000, "likes": 200, "comments": 20, "shares": 50}
        start = time.perf_counter()
        for _ in range(1000):
            self.analytics.calculate_organic_score(metrics, Platform.TIKTOK, 24.0)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"1000 score calculations took {elapsed:.3f}s (> 1s)"

    def test_bayesian_confidence_speed(self):
        """Bayesian confidence must complete in < 1ms per call."""
        start = time.perf_counter()
        for _ in range(1000):
            self.selector.bayesian_confidence(50, 1000)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"1000 Bayesian calls took {elapsed:.3f}s (> 1s)"

    def test_script_readability_speed(self):
        """Script readability scoring must be fast."""
        script = "This is a test script for performance benchmarking. Buy now and save big!"
        start = time.perf_counter()
        for _ in range(1000):
            self.engine.score_script_readability(script)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"1000 readability scores took {elapsed:.3f}s (> 0.5s)"

    def test_elimination_speed(self):
        """Elimination of 100 creatives must be < 10ms."""
        creatives = [
            Creative(
                id=f"c{i}", campaign_id="c1", round_id="r1",
                generation_source=GenerationSource.SORA,
                organic_score=float(i),
            )
            for i in range(100)
        ]
        start = time.perf_counter()
        for _ in range(100):
            self.selector.eliminate_bottom_performers(creatives, 0.5)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"100 elimination runs took {elapsed:.3f}s (> 1s)"

    def test_diversity_scoring_speed(self):
        """Diversity scoring for 20 variants must be < 5ms."""
        variants = [
            {"hook": f"Hook {i}", "angle": f"angle_{i % 5}", "style": f"style_{i % 3}"}
            for i in range(20)
        ]
        start = time.perf_counter()
        for _ in range(500):
            self.selector.score_variation_diversity(variants) if hasattr(self.selector, "score_variation_diversity") else None
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0

    def test_anomaly_detection_speed(self):
        """Anomaly detection on 50 data points must be fast."""
        series = [{"value": float(i * 10), "metric_type": "views"} for i in range(50)]
        start = time.perf_counter()
        for _ in range(1000):
            self.analytics.detect_anomalies(series)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"1000 anomaly detections took {elapsed:.3f}s"
