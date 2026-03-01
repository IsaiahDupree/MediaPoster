"""
ACTP Monitoring Module
=======================
Health checks, structured logging, cost tracking, latency measurement,
error rate tracking, and dead letter queue management.
"""

import logging
import os
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ─── Health Check ────────────────────────────────────────

class HealthChecker:
    """Pipeline health check — DB, external APIs, queue depth."""

    def __init__(self, db_client=None):
        self.db = db_client

    async def check(self) -> Dict[str, Any]:
        """Run all health checks and return aggregated status."""
        checks = {}

        # Database connectivity
        checks["database"] = await self._check_database()

        # External API availability
        checks["providers"] = self._check_providers()

        # Pipeline status
        checks["pipeline"] = await self._check_pipeline_status()

        # Overall
        all_ok = all(
            c.get("status") == "ok"
            for c in checks.values()
            if isinstance(c, dict) and "status" in c
        )

        return {
            "status": "ok" if all_ok else "degraded",
            "version": os.getenv("ACTP_VERSION", "1.0.0"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }

    async def _check_database(self) -> Dict[str, Any]:
        if not self.db:
            return {"status": "unconfigured", "message": "No DB client"}
        try:
            start = time.time()
            result = await self.db.table("actp_campaigns").select("id").limit(1).execute()
            latency_ms = round((time.time() - start) * 1000, 1)
            return {"status": "ok", "latency_ms": latency_ms}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_providers(self) -> Dict[str, Any]:
        from .security import SecretsValidator
        avail = SecretsValidator.get_provider_availability()
        configured = sum(1 for v in avail.values() if v)
        return {
            "status": "ok" if configured > 0 else "warning",
            "configured_count": configured,
            "providers": avail,
        }

    async def _check_pipeline_status(self) -> Dict[str, Any]:
        if not self.db:
            return {"status": "unconfigured"}
        try:
            active = await self.db.table("actp_campaigns").select("id").not_.in_(
                "status", ["draft", "completed", "failed", "paused"]
            ).execute()
            stale = await self.db.table("actp_rounds").select("id").eq(
                "status", "waiting"
            ).execute()
            return {
                "status": "ok",
                "active_campaigns": len(active.data or []),
                "waiting_rounds": len(stale.data or []),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ─── Structured Logging with Correlation IDs ─────────────

class CorrelationLogger:
    """Structured logger that attaches correlation IDs to log entries."""

    @staticmethod
    def get_correlation_id() -> str:
        return str(uuid.uuid4())[:8]

    @staticmethod
    def log(level: str, module: str, message: str, correlation_id: str = "",
            extra: Optional[Dict[str, Any]] = None):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "module": f"ACTP:{module}",
            "msg": message,
            "cid": correlation_id,
        }
        if extra:
            entry.update(extra)
        getattr(logger, level.lower(), logger.info)(str(entry))


# ─── Request Logging Middleware ──────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests with method, path, status, duration, request ID."""

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/actp"):
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        # Attach request ID to state
        request.state.request_id = request_id

        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 1)

        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"[ACTP:API] {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms}ms) "
            f"[rid={request_id} ip={client_ip}]"
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response


# ─── Latency Tracking ───────────────────────────────────

class LatencyTracker:
    """Track execution time per pipeline step."""

    def __init__(self):
        self._timings: Dict[str, List[float]] = defaultdict(list)

    @asynccontextmanager
    async def track(self, step_name: str):
        """Context manager to track step latency."""
        start = time.time()
        try:
            yield
        finally:
            elapsed_ms = (time.time() - start) * 1000
            self._timings[step_name].append(elapsed_ms)
            if elapsed_ms > 5000:
                logger.warning(f"[ACTP:Latency] Slow step '{step_name}': {elapsed_ms:.0f}ms")

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get latency statistics per step."""
        stats = {}
        for step, times in self._timings.items():
            if not times:
                continue
            sorted_t = sorted(times)
            n = len(sorted_t)
            stats[step] = {
                "count": n,
                "avg_ms": round(sum(sorted_t) / n, 1),
                "min_ms": round(sorted_t[0], 1),
                "max_ms": round(sorted_t[-1], 1),
                "p95_ms": round(sorted_t[int(n * 0.95)] if n > 1 else sorted_t[0], 1),
            }
        return stats

    def reset(self):
        self._timings.clear()


# ─── Error Rate Tracking ────────────────────────────────

class ErrorTracker:
    """Track error counts per module for alerting."""

    def __init__(self):
        self._errors: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._counts: Dict[str, int] = defaultdict(int)

    def record_error(self, module: str, error: Exception, context: str = ""):
        self._counts[module] += 1
        self._errors[module].append({
            "error": str(error),
            "type": type(error).__name__,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep only last 100 errors per module
        if len(self._errors[module]) > 100:
            self._errors[module] = self._errors[module][-100:]

    def get_error_rates(self) -> Dict[str, Any]:
        return {
            "total_errors": sum(self._counts.values()),
            "by_module": dict(self._counts),
            "recent_errors": {
                mod: errs[-5:] for mod, errs in self._errors.items()
            },
        }

    def reset(self):
        self._errors.clear()
        self._counts.clear()


# ─── Cost Tracking ───────────────────────────────────────

class CostTracker:
    """Track API and ad spend costs per campaign."""

    # Estimated costs per API call (in cents)
    COST_PER_CALL = {
        "openai_gpt4o": 5,       # ~$0.05 per brief generation
        "sora_generation": 100,   # ~$1.00 per video
        "veo3_generation": 50,    # ~$0.50 per video
        "nano_banana": 25,        # ~$0.25 per video
        "remotion_render": 10,    # ~$0.10 per render
        "tts_generation": 5,      # ~$0.05 per voiceover
    }

    def __init__(self, db_client=None):
        self.db = db_client
        self._session_costs: Dict[str, int] = defaultdict(int)  # campaign_id → cents

    def estimate_generation_cost(
        self, provider: str, count: int, include_brief: bool = True
    ) -> Dict[str, Any]:
        """Estimate the cost of generating creatives before execution."""
        gen_cost = self.COST_PER_CALL.get(f"{provider}_generation", 0) * count
        brief_cost = self.COST_PER_CALL["openai_gpt4o"] * count if include_brief else 0
        total = gen_cost + brief_cost

        return {
            "provider": provider,
            "count": count,
            "generation_cost_cents": gen_cost,
            "brief_cost_cents": brief_cost,
            "total_estimated_cents": total,
            "total_estimated_usd": round(total / 100, 2),
        }

    def record_cost(self, campaign_id: str, cost_type: str, amount_cents: int):
        """Record a cost event."""
        self._session_costs[campaign_id] += amount_cents
        logger.info(
            f"[ACTP:Cost] {cost_type}: {amount_cents}¢ for campaign {campaign_id} "
            f"(session total: {self._session_costs[campaign_id]}¢)"
        )

    async def get_campaign_cost_breakdown(self, campaign_id: str) -> Dict[str, Any]:
        """Get full cost breakdown for a campaign."""
        if not self.db:
            return {"campaign_id": campaign_id, "total_cents": 0}

        # Ad spend
        ads = await self.db.table("actp_ad_deployments").select(
            "spend_cents, platform"
        ).eq("round_id", campaign_id).execute()

        ad_spend = sum(a.get("spend_cents", 0) for a in (ads.data or []))
        by_platform = defaultdict(int)
        for a in (ads.data or []):
            by_platform[a.get("platform", "unknown")] += a.get("spend_cents", 0)

        # Generation costs (estimated from creative count)
        creatives = await self.db.table("actp_creatives").select(
            "generation_source"
        ).eq("campaign_id", campaign_id).execute()

        gen_cost = 0
        for c in (creatives.data or []):
            source = c.get("generation_source", "remotion")
            gen_cost += self.COST_PER_CALL.get(f"{source}_generation", 10)

        session = self._session_costs.get(campaign_id, 0)

        return {
            "campaign_id": campaign_id,
            "ad_spend_cents": ad_spend,
            "generation_cost_cents": gen_cost,
            "session_cost_cents": session,
            "total_cents": ad_spend + gen_cost + session,
            "total_usd": round((ad_spend + gen_cost + session) / 100, 2),
            "by_platform": dict(by_platform),
            "creative_count": len(creatives.data or []),
        }


# ─── Dead Letter Queue ──────────────────────────────────

class DeadLetterQueue:
    """Manage permanently failed jobs for manual review."""

    def __init__(self, db_client=None):
        self.db = db_client

    async def push(
        self, job_type: str, payload: Dict[str, Any], error: str, max_retries: int = 3
    ):
        """Push a failed job to the dead letter queue."""
        if self.db:
            await self.db.table("actp_dead_letter_queue").insert({
                "job_type": job_type,
                "payload": payload,
                "error": error,
                "max_retries": max_retries,
            }).execute()
        logger.warning(f"[ACTP:DLQ] Job pushed: {job_type} — {error}")

    async def list_pending(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List pending DLQ items."""
        if not self.db:
            return []
        result = await self.db.table("actp_dead_letter_queue").select("*").lt(
            "retry_count", 3
        ).order("created_at", desc=True).limit(limit).execute()
        return result.data or []

    async def retry_job(self, dlq_id: str) -> bool:
        """Retry a job from the dead letter queue."""
        if not self.db:
            return False

        result = await self.db.table("actp_dead_letter_queue").select("*").eq(
            "id", dlq_id
        ).single().execute()

        if not result.data:
            return False

        job = result.data
        if job["retry_count"] >= job["max_retries"]:
            logger.warning(f"[ACTP:DLQ] Max retries exceeded for {dlq_id}")
            return False

        # Increment retry count
        await self.db.table("actp_dead_letter_queue").update({
            "retry_count": job["retry_count"] + 1,
            "last_attempted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", dlq_id).execute()

        return True


# ─── Stale Campaign Detection ───────────────────────────

class StaleCampaignDetector:
    """Detect campaigns stuck without progress."""

    def __init__(self, db_client=None, stale_hours: int = 72):
        self.db = db_client
        self.stale_hours = stale_hours

    async def detect_stale(self) -> List[Dict[str, Any]]:
        """Find campaigns that haven't progressed within the threshold."""
        if not self.db:
            return []

        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=self.stale_hours)).isoformat()

        result = await self.db.table("actp_campaigns").select("id, name, status, updated_at").not_.in_(
            "status", ["draft", "completed", "failed"]
        ).lt("updated_at", cutoff).execute()

        stale = result.data or []
        if stale:
            logger.warning(f"[ACTP:Monitor] {len(stale)} stale campaigns detected")

        return stale


# ─── Singleton Instances ─────────────────────────────────

_latency_tracker = LatencyTracker()
_error_tracker = ErrorTracker()


def get_latency_tracker() -> LatencyTracker:
    return _latency_tracker


def get_error_tracker() -> ErrorTracker:
    return _error_tracker


# ─── Uptime Tracking ──────────────────────────────────────

class UptimeTracker:
    """Track pipeline uptime and availability."""

    _start_time: Optional[datetime] = None
    _downtime_events: List[Dict[str, Any]] = []

    @classmethod
    def mark_start(cls):
        cls._start_time = datetime.now(timezone.utc)
        cls._downtime_events = []

    @classmethod
    def record_downtime(cls, reason: str, duration_seconds: float):
        cls._downtime_events.append({
            "reason": reason,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @classmethod
    def get_uptime(cls) -> Dict[str, Any]:
        if not cls._start_time:
            return {"uptime_seconds": 0, "uptime_pct": 100}

        total = (datetime.now(timezone.utc) - cls._start_time).total_seconds()
        downtime = sum(e["duration_seconds"] for e in cls._downtime_events)
        uptime_pct = ((total - downtime) / max(total, 1)) * 100

        return {
            "started_at": cls._start_time.isoformat(),
            "uptime_seconds": round(total - downtime),
            "total_seconds": round(total),
            "downtime_seconds": round(downtime),
            "uptime_pct": round(uptime_pct, 2),
            "downtime_events": len(cls._downtime_events),
        }


# ─── Queue Depth Monitoring ───────────────────────────────

class QueueDepthMonitor:
    """Monitor pending task queue depth."""

    def __init__(self, db_client=None):
        self.db = db_client

    async def get_queue_depth(self) -> Dict[str, Any]:
        if not self.db:
            return {"total_pending": 0}

        result = await self.db.table("actp_scheduled_tasks").select(
            "task_type, status"
        ).eq("status", "pending").execute()

        tasks = result.data or []
        by_type: Dict[str, int] = {}
        for t in tasks:
            tt = t.get("task_type", "unknown")
            by_type[tt] = by_type.get(tt, 0) + 1

        return {
            "total_pending": len(tasks),
            "by_type": by_type,
        }

    async def get_dlq_depth(self) -> Dict[str, Any]:
        if not self.db:
            return {"total": 0}

        result = await self.db.table("actp_dead_letter_queue").select(
            "job_type"
        ).lt("retry_count", 3).execute()

        items = result.data or []
        by_type: Dict[str, int] = {}
        for i in items:
            jt = i.get("job_type", "unknown")
            by_type[jt] = by_type.get(jt, 0) + 1

        return {"total": len(items), "by_type": by_type}


# ─── Deployment Tracking ──────────────────────────────────

class DeploymentTracker:
    """Track code and configuration deployments."""

    _deployments: List[Dict[str, Any]] = []

    @classmethod
    def record_deployment(cls, version: str, description: str, migration: Optional[str] = None):
        cls._deployments.append({
            "version": version,
            "description": description,
            "migration": migration,
            "deployed_at": datetime.now(timezone.utc).isoformat(),
        })

    @classmethod
    def get_deployments(cls, limit: int = 20) -> List[Dict[str, Any]]:
        return cls._deployments[-limit:]

    @classmethod
    def get_current_version(cls) -> Optional[str]:
        if cls._deployments:
            return cls._deployments[-1]["version"]
        return None
