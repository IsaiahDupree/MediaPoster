"""
YTP-015: Error Monitoring & Alerts
Monitors the YouTube pipeline for errors and sends alerts.
"""
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class PipelineError:
    """A recorded pipeline error."""
    error_id: str
    pipeline_stage: str
    error_type: str
    message: str
    video_id: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: str = "error"  # warning, error, critical
    resolved: bool = False
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AlertConfig:
    """Configuration for an alert channel."""
    channel: str  # email, slack, webhook
    endpoint: str
    severity_threshold: str = "error"
    enabled: bool = True


class PipelineMonitor:
    """
    Monitors pipeline health and sends alerts on errors.

    Features:
    - Error tracking with severity levels
    - Configurable alert channels
    - Error rate monitoring
    - Health check endpoints
    """

    def __init__(self, max_history: int = 1000):
        self._errors: deque = deque(maxlen=max_history)
        self._alert_configs: List[AlertConfig] = []
        self._alert_callbacks: List[Callable] = []
        self._error_counts: Dict[str, int] = {}

    def record_error(
        self,
        pipeline_stage: str,
        error_type: str,
        message: str,
        video_id: Optional[str] = None,
        severity: str = "error",
        stack_trace: Optional[str] = None,
    ) -> PipelineError:
        """
        Record a pipeline error.

        Args:
            pipeline_stage: Stage where error occurred
            error_type: Type of error
            message: Error message
            video_id: Related video ID
            severity: warning, error, or critical
            stack_trace: Optional stack trace

        Returns:
            PipelineError record
        """
        from uuid import uuid4

        error = PipelineError(
            error_id=str(uuid4()),
            pipeline_stage=pipeline_stage,
            error_type=error_type,
            message=message,
            video_id=video_id,
            severity=severity,
            stack_trace=stack_trace,
        )

        self._errors.append(error)
        self._error_counts[pipeline_stage] = self._error_counts.get(pipeline_stage, 0) + 1

        logger.log(
            logging.CRITICAL if severity == "critical" else logging.ERROR,
            "Pipeline error [%s] in %s: %s",
            severity,
            pipeline_stage,
            message,
        )

        # Trigger alerts
        for callback in self._alert_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.warning("Alert callback failed: %s", e)

        return error

    def add_alert_config(self, config: AlertConfig) -> None:
        """Add an alert channel configuration."""
        self._alert_configs.append(config)

    def on_alert(self, callback: Callable) -> None:
        """Register an alert callback function."""
        self._alert_callbacks.append(callback)

    def get_recent_errors(
        self,
        limit: int = 50,
        severity: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> List[PipelineError]:
        """Get recent errors with optional filtering."""
        errors = list(self._errors)
        if severity:
            errors = [e for e in errors if e.severity == severity]
        if stage:
            errors = [e for e in errors if e.pipeline_stage == stage]
        return errors[-limit:]

    def get_error_rate(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Get error rate over a time window."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        cutoff_str = cutoff.isoformat()

        recent = [e for e in self._errors if e.occurred_at >= cutoff_str]

        by_stage: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for e in recent:
            by_stage[e.pipeline_stage] = by_stage.get(e.pipeline_stage, 0) + 1
            by_severity[e.severity] = by_severity.get(e.severity, 0) + 1

        return {
            "total_errors": len(recent),
            "window_minutes": window_minutes,
            "by_stage": by_stage,
            "by_severity": by_severity,
            "errors_per_minute": len(recent) / max(1, window_minutes),
        }

    def get_health(self) -> Dict[str, Any]:
        """Get overall pipeline health status."""
        error_rate = self.get_error_rate(window_minutes=15)
        critical_count = error_rate["by_severity"].get("critical", 0)

        if critical_count > 0:
            status = "critical"
        elif error_rate["total_errors"] > 10:
            status = "degraded"
        elif error_rate["total_errors"] > 0:
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "recent_errors": error_rate["total_errors"],
            "critical_errors": critical_count,
            "total_errors_recorded": len(self._errors),
            "error_counts_by_stage": dict(self._error_counts),
        }
