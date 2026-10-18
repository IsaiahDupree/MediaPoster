"""
Workflow Manager
================
Tracks multi-step workflows across events for visibility and debugging.

Provides:
    - Workflow state tracking via correlation IDs
    - Step progress tracking
    - Duration metrics
    - Workflow status API
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from services.event_bus import EventBus, Event, Topics

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """Represents a step in a workflow."""
    name: str
    status: str  # pending, in_progress, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


@dataclass
class Workflow:
    """Tracks the state of a multi-step workflow."""
    id: str  # correlation_id
    workflow_type: str
    status: str  # pending, in_progress, completed, failed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    steps: List[WorkflowStep] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    current_step: Optional[str] = None
    progress: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        return (self.updated_at - self.created_at).total_seconds() * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_type": self.workflow_type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "duration_ms": self.duration_ms,
            "current_step": self.current_step,
            "progress": self.progress,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                }
                for s in self.steps
            ],
            "event_count": len(self.events),
            "result": self.result,
            "error": self.error,
        }


class WorkflowManager:
    """
    Manages workflow tracking across events.
    
    Subscribes to all events and tracks workflow state based on
    correlation IDs. Provides visibility into long-running processes.
    
    Usage:
        manager = WorkflowManager.get_instance()
        
        # Get workflow status
        status = manager.get_workflow(correlation_id)
        
        # Get all active workflows
        active = manager.get_active_workflows()
    """
    
    _instance: Optional["WorkflowManager"] = None
    
    # Topic patterns that indicate workflow types
    WORKFLOW_PATTERNS = {
        "analysis": ["media.analysis.*"],
        "publish": ["publish.*"],
        "metrics": ["metrics.*"],
        "ai_generation": ["ai.generation.*"],
        "schedule": ["schedule.*"],
    }
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus.get_instance()
        self.workflows: Dict[str, Workflow] = {}
        self._max_workflows = 500  # Keep last 500 workflows
        
        # Subscribe to all events
        self.event_bus.subscribe("*", self._track_event)
        
        logger.info("📊 WorkflowManager initialized")
    
    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None) -> "WorkflowManager":
        """Get or create the singleton WorkflowManager instance."""
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None
    
    async def _track_event(self, event: Event) -> None:
        """Track workflow state based on received event."""
        cid = event.correlation_id
        
        # Get or create workflow
        if cid not in self.workflows:
            workflow_type = self._infer_workflow_type(event.topic)
            self.workflows[cid] = Workflow(
                id=cid,
                workflow_type=workflow_type,
                status="in_progress"
            )
        
        workflow = self.workflows[cid]
        workflow.events.append(event)
        workflow.updated_at = event.timestamp
        
        # Update workflow state based on event topic
        self._update_workflow_state(workflow, event)
        
        # Trim old workflows
        self._trim_workflows()
    
    def _infer_workflow_type(self, topic: str) -> str:
        """Infer workflow type from topic."""
        for wf_type, patterns in self.WORKFLOW_PATTERNS.items():
            for pattern in patterns:
                if Topics.matches_pattern(pattern, topic):
                    return wf_type
        return "unknown"
    
    def _update_workflow_state(self, workflow: Workflow, event: Event) -> None:
        """Update workflow state based on event."""
        topic = event.topic
        
        # Extract step name from topic
        step_name = self._extract_step_name(topic)
        
        # Update current step
        if ".started" in topic or ".progress" in topic:
            workflow.current_step = step_name
            workflow.status = "in_progress"
            
            # Add or update step
            step = self._get_or_create_step(workflow, step_name)
            step.status = "in_progress"
            step.started_at = event.timestamp
        
        elif ".completed" in topic:
            # Mark step as completed
            step = self._get_or_create_step(workflow, step_name)
            step.status = "completed"
            step.completed_at = event.timestamp
            
            # Check if this is the final completion
            if self._is_workflow_complete(topic):
                workflow.status = "completed"
                workflow.result = event.payload
        
        elif ".failed" in topic:
            workflow.status = "failed"
            workflow.error = event.payload.get("error", str(event.payload))
            
            step = self._get_or_create_step(workflow, step_name)
            step.status = "failed"
            step.error = workflow.error
        
        # Update progress from payload if present
        if "progress" in event.payload:
            workflow.progress = event.payload["progress"]
    
    def _extract_step_name(self, topic: str) -> str:
        """Extract step name from topic."""
        parts = topic.split('.')
        if len(parts) >= 2:
            # Remove action suffix (.started, .completed, etc.)
            if parts[-1] in ("started", "completed", "failed", "progress"):
                return '.'.join(parts[:-1])
        return topic
    
    def _get_or_create_step(self, workflow: Workflow, step_name: str) -> WorkflowStep:
        """Get existing step or create new one."""
        for step in workflow.steps:
            if step.name == step_name:
                return step
        
        step = WorkflowStep(name=step_name, status="pending")
        workflow.steps.append(step)
        return step
    
    def _is_workflow_complete(self, topic: str) -> bool:
        """Check if topic indicates workflow completion."""
        complete_topics = [
            Topics.ANALYSIS_COMPLETED,
            Topics.PUBLISH_COMPLETED,
            Topics.METRICS_FETCH_COMPLETED,
            Topics.AI_GENERATION_COMPLETED,
        ]
        return topic in complete_topics
    
    def _trim_workflows(self) -> None:
        """Remove old workflows to prevent memory growth."""
        if len(self.workflows) > self._max_workflows:
            # Sort by updated_at and keep newest
            sorted_ids = sorted(
                self.workflows.keys(),
                key=lambda k: self.workflows[k].updated_at,
                reverse=True
            )
            
            # Remove oldest
            for cid in sorted_ids[self._max_workflows:]:
                del self.workflows[cid]
    
    def get_workflow(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status by correlation ID."""
        workflow = self.workflows.get(correlation_id)
        if workflow:
            return workflow.to_dict()
        return None
    
    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active (in_progress) workflows."""
        return [
            wf.to_dict()
            for wf in self.workflows.values()
            if wf.status == "in_progress"
        ]
    
    def get_recent_workflows(
        self,
        limit: int = 20,
        workflow_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent workflows with optional filters."""
        workflows = list(self.workflows.values())
        
        if workflow_type:
            workflows = [wf for wf in workflows if wf.workflow_type == workflow_type]
        
        if status:
            workflows = [wf for wf in workflows if wf.status == status]
        
        # Sort by updated_at, newest first
        workflows.sort(key=lambda wf: wf.updated_at, reverse=True)
        
        return [wf.to_dict() for wf in workflows[:limit]]
    
    def get_workflow_events(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get all events for a workflow."""
        workflow = self.workflows.get(correlation_id)
        if workflow:
            return [e.to_dict() for e in workflow.events]
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workflow manager statistics."""
        status_counts = {}
        type_counts = {}
        
        for wf in self.workflows.values():
            status_counts[wf.status] = status_counts.get(wf.status, 0) + 1
            type_counts[wf.workflow_type] = type_counts.get(wf.workflow_type, 0) + 1
        
        return {
            "total_workflows": len(self.workflows),
            "status_counts": status_counts,
            "type_counts": type_counts,
            "max_workflows": self._max_workflows,
        }
