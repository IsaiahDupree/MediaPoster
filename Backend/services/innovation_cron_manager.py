"""
Innovation Cron Manager
========================
Manages periodic background tasks for all innovation features:

| Job                         | Interval     | Service                    |
|-----------------------------|-------------|----------------------------|
| trend_scan                  | Every 2h    | TrendDetectionService      |
| trend_status_update         | Every 6h    | TrendDetectionService      |
| content_tag_posts           | Every 4h    | ContentIntelligenceEngine  |
| content_analyze_patterns    | Daily 6am   | ContentIntelligenceEngine  |
| content_generate_briefs     | Daily 7am   | ContentIntelligenceEngine  |
| cascade_cycle               | Every 30min | CascadePublisher           |
| cascade_check_gates         | Every 1h    | CascadePublisher           |
| ab_test_collect_metrics     | Every 2h    | ABTestingService           |
| engagement_daily_stats      | Daily 11pm  | EngagementAutopilot        |

Usage:
    from services.innovation_cron_manager import InnovationCronManager
    
    manager = InnovationCronManager()
    await manager.start()
    # ... on shutdown:
    manager.stop()
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from loguru import logger


class InnovationCronManager:
    """Manages all innovation feature cron jobs."""

    _instance: Optional["InnovationCronManager"] = None

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False

    @classmethod
    def get_instance(cls) -> "InnovationCronManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self):
        """Start all cron jobs as background async tasks."""
        if self._running:
            logger.warning("[InnovationCron] Already running")
            return

        self._running = True
        logger.info("[InnovationCron] Starting all innovation cron jobs...")

        self._tasks["trend_scan"] = asyncio.create_task(
            self._loop("trend_scan", 7200, self._trend_scan)
        )
        self._tasks["trend_status"] = asyncio.create_task(
            self._loop("trend_status", 21600, self._trend_status_update)
        )
        self._tasks["content_tag"] = asyncio.create_task(
            self._loop("content_tag", 14400, self._content_tag_posts)
        )
        self._tasks["cascade_cycle"] = asyncio.create_task(
            self._loop("cascade_cycle", 1800, self._cascade_cycle)
        )
        self._tasks["cascade_gates"] = asyncio.create_task(
            self._loop("cascade_gates", 3600, self._cascade_check_gates)
        )
        self._tasks["ab_metrics"] = asyncio.create_task(
            self._loop("ab_metrics", 7200, self._ab_collect_metrics)
        )

        logger.success(f"[InnovationCron] ✓ Started {len(self._tasks)} cron jobs")

    def stop(self):
        """Stop all cron jobs."""
        self._running = False
        for name, task in self._tasks.items():
            task.cancel()
            logger.info(f"[InnovationCron] Cancelled {name}")
        self._tasks.clear()
        logger.info("[InnovationCron] All jobs stopped")

    def status(self) -> dict:
        """Get status of all cron jobs."""
        return {
            "running": self._running,
            "jobs": {
                name: {
                    "running": not task.done(),
                    "cancelled": task.cancelled(),
                }
                for name, task in self._tasks.items()
            },
        }

    # ─── Job Loop ────────────────────────────────────────────────────────

    async def _loop(self, name: str, interval_seconds: int, func):
        """Generic loop: run func, sleep interval, repeat."""
        # Initial delay to stagger startup
        await asyncio.sleep(10)
        while self._running:
            try:
                logger.debug(f"[InnovationCron] Running {name}...")
                await func()
            except Exception as e:
                logger.error(f"[InnovationCron] {name} failed: {e}")
            await asyncio.sleep(interval_seconds)

    # ─── Job Implementations ─────────────────────────────────────────────

    async def _trend_scan(self):
        from services.trend_detection import TrendDetectionService
        svc = TrendDetectionService()
        result = await svc.run_scan_cycle()
        logger.info(f"[Cron:trends] Scanned {result.get('scanned', 0)}, new: {result.get('new_stored', 0)}")

    async def _trend_status_update(self):
        from services.trend_detection import TrendDetectionService
        svc = TrendDetectionService()
        await svc._update_trend_statuses()
        logger.info("[Cron:trends] Status update complete")

    async def _content_tag_posts(self):
        from services.content_intelligence import ContentIntelligenceEngine
        svc = ContentIntelligenceEngine()
        result = await svc.tag_untagged_posts(limit=20)
        logger.info(f"[Cron:intelligence] Tagged {result.get('tagged', 0)} posts")

    async def _cascade_cycle(self):
        from services.cascade_publisher import CascadePublisher
        svc = CascadePublisher()
        result = await svc.run_cascade_cycle()
        logger.info(f"[Cron:cascade] Processed {result.get('processed', 0)} cascade posts")

    async def _cascade_check_gates(self):
        from services.cascade_publisher import CascadePublisher
        svc = CascadePublisher()
        result = await svc.check_performance_gates()
        logger.info(f"[Cron:cascade] Checked {result.get('checked', 0)} gates")

    async def _ab_collect_metrics(self):
        from services.ab_testing_service import ABTestingService
        svc = ABTestingService()
        tests = await svc.list_tests(status="active")
        collected = 0
        for test in tests:
            try:
                await svc.collect_metrics(test["id"])
                collected += 1
            except Exception as e:
                logger.debug(f"[Cron:ab] Metrics collection failed for {test['id']}: {e}")
        logger.info(f"[Cron:ab] Collected metrics for {collected} active tests")
