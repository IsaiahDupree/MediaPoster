"""
Event Topics
============
Standardized topic names for all pub/sub events.

Topic Naming Convention:
    {domain}.{entity}.{action}
    
Examples:
    - media.ingested
    - media.analysis.started
    - publish.completed
"""


class Topics:
    """
    Centralized topic registry for all events.
    
    Usage:
        from services.event_bus import Topics
        
        await bus.publish(Topics.MEDIA_INGESTED, {...})
        bus.subscribe(Topics.ANALYSIS_COMPLETED, handler)
    """
    
    # =========================================================================
    # MEDIA LIFECYCLE
    # =========================================================================
    MEDIA_INGESTED = "media.ingested"           # New video added to library
    MEDIA_UPDATED = "media.updated"             # Video metadata updated
    MEDIA_DELETED = "media.deleted"             # Video removed from library
    MEDIA_THUMBNAIL_READY = "media.thumbnail.ready"  # Thumbnail generated
    
    # =========================================================================
    # ANALYSIS PIPELINE
    # =========================================================================
    ANALYSIS_REQUESTED = "media.analysis.requested"   # User/system requests analysis
    ANALYSIS_STARTED = "media.analysis.started"       # Analysis worker picked up job
    ANALYSIS_PROGRESS = "media.analysis.progress"     # Progress update (% complete)
    ANALYSIS_STEP_COMPLETED = "media.analysis.step.completed"  # Individual step done
    ANALYSIS_COMPLETED = "media.analysis.completed"   # Full analysis finished
    ANALYSIS_FAILED = "media.analysis.failed"         # Analysis error
    
    # Analysis sub-steps
    TRANSCRIPT_STARTED = "media.analysis.transcript.started"
    TRANSCRIPT_COMPLETED = "media.analysis.transcript.completed"
    VISUAL_STARTED = "media.analysis.visual.started"
    VISUAL_COMPLETED = "media.analysis.visual.completed"
    AI_ANALYSIS_STARTED = "media.analysis.ai.started"
    AI_ANALYSIS_COMPLETED = "media.analysis.ai.completed"
    CAPTIONS_GENERATED = "media.analysis.captions.generated"
    
    # =========================================================================
    # PUBLISHING PIPELINE
    # =========================================================================
    PUBLISH_REQUESTED = "publish.requested"           # Publish job created
    PUBLISH_QUEUED = "publish.queued"                 # Added to publish queue
    PUBLISH_STARTED = "publish.started"               # Worker picked up job
    PUBLISH_UPLOADING = "publish.uploading"           # Uploading to cloud/blotato
    PUBLISH_UPLOAD_COMPLETED = "publish.upload.completed"  # Upload done
    PUBLISH_SUBMITTED = "publish.submitted"           # Sent to platform
    PUBLISH_POLLING = "publish.polling"               # Waiting for platform URL
    PUBLISH_COMPLETED = "publish.completed"           # URL obtained, success
    PUBLISH_FAILED = "publish.failed"                 # Publish error
    PUBLISH_RETRYING = "publish.retrying"             # Retry scheduled
    
    # =========================================================================
    # SCHEDULING
    # =========================================================================
    SCHEDULE_CREATED = "schedule.created"             # New scheduled post
    SCHEDULE_UPDATED = "schedule.updated"             # Schedule modified
    SCHEDULE_CANCELLED = "schedule.cancelled"         # Schedule cancelled
    SCHEDULE_DUE = "schedule.due"                     # Post is due for publishing
    SCHEDULER_TICK = "scheduler.tick"                 # Periodic scheduler heartbeat
    SCHEDULER_STARTED = "scheduler.started"           # Scheduler service started
    SCHEDULER_STOPPED = "scheduler.stopped"           # Scheduler service stopped
    
    # =========================================================================
    # METRICS & ANALYTICS
    # =========================================================================
    METRICS_FETCH_REQUESTED = "metrics.fetch.requested"   # Request to fetch metrics
    METRICS_FETCH_STARTED = "metrics.fetch.started"       # Fetching from platform
    METRICS_FETCH_COMPLETED = "metrics.fetch.completed"   # Metrics fetched
    METRICS_UPDATED = "metrics.updated"                   # New metrics available
    METRICS_AGGREGATED = "metrics.aggregated"             # Aggregation complete
    
    # =========================================================================
    # AI GENERATION
    # =========================================================================
    AI_GENERATION_REQUESTED = "ai.generation.requested"   # AI video generation request
    AI_GENERATION_STARTED = "ai.generation.started"       # Generation in progress
    AI_GENERATION_PROGRESS = "ai.generation.progress"     # Progress update
    AI_GENERATION_COMPLETED = "ai.generation.completed"   # Generation done
    AI_GENERATION_FAILED = "ai.generation.failed"         # Generation error
    
    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    NOTIFICATION_CREATED = "notification.created"         # New notification
    NOTIFICATION_SENT = "notification.sent"               # Notification delivered
    
    # =========================================================================
    # HYDRATION (State Management)
    # =========================================================================
    HYDRATION_SNAPSHOT_READY = "mp.hydration.evt.snapshot_ready"  # Fresh state available
    HYDRATION_FEATURES_READY = "mp.hydration.evt.features_ready"  # Derived features computed
    
    # =========================================================================
    # NARRATIVE BUILDER (Mainline Brain)
    # =========================================================================
    NARRATIVE_PLAN_REQUESTED = "mp.narrative.cmd.plan"            # Request new plan
    NARRATIVE_PLAN_GENERATED = "mp.narrative.evt.plan_generated"  # Plan ready
    NARRATIVE_GOAL_UPDATED = "mp.narrative.evt.goal_updated"      # Goal progress changed
    
    # =========================================================================
    # EXPERIMENTS (Research Brain)
    # =========================================================================
    EXPERIMENT_PLAN_RUN = "mp.experiments.cmd.plan_run"           # Start experiment
    EXPERIMENT_RUN_STARTED = "mp.experiments.evt.run_started"     # Run began
    EXPERIMENT_VARIANT_CREATED = "mp.experiments.evt.variant_created"  # Variant scheduled
    EXPERIMENT_RUN_COMPLETED = "mp.experiments.evt.run_completed" # Run finished
    EXPERIMENT_METRICS_READY = "mp.experiments.evt.metrics_ready" # Metrics collected
    
    # =========================================================================
    # KNOWLEDGE BASE (Rules & Learnings)
    # =========================================================================
    RULE_CREATED = "mp.rules.evt.rule_created"                    # New rule from experiment
    RULE_UPDATED = "mp.rules.evt.rule_updated"                    # Rule confidence updated
    RULE_DEPRECATED = "mp.rules.evt.rule_deprecated"              # Rule no longer valid
    TEMPLATE_CREATED = "mp.rules.evt.template_created"            # New template
    PLAYBOOK_ACTIVATED = "mp.rules.evt.playbook_activated"        # Playbook in use
    
    # =========================================================================
    # SCHEDULER (Execution)
    # =========================================================================
    SCHEDULER_CREATE_ITEMS = "mp.scheduler.cmd.create_items"      # Create schedule items
    SCHEDULER_UPDATE_ITEM = "mp.scheduler.cmd.update_item"        # Update item
    SCHEDULER_CANCEL_ITEM = "mp.scheduler.cmd.cancel_item"        # Cancel item
    SCHEDULER_ITEM_SCHEDULED = "mp.scheduler.evt.item_scheduled"  # Item scheduled
    SCHEDULER_ITEM_DUE = "mp.scheduler.evt.item_due"              # Time reached
    SCHEDULER_ITEM_CANCELED = "mp.scheduler.evt.item_canceled"    # Item canceled
    
    # =========================================================================
    # UI / REALTIME
    # =========================================================================
    UI_TOAST = "mp.ui.evt.toast"                                  # Show notification
    UI_INVALIDATE_CACHE = "mp.ui.evt.invalidate"                  # Cache invalidation
    UI_ACTIVITY_FEED = "mp.ui.evt.activity"                       # Activity feed item
    
    # =========================================================================
    # SYSTEM
    # =========================================================================
    SYSTEM_STARTUP = "system.startup"                     # Backend started
    SYSTEM_SHUTDOWN = "system.shutdown"                   # Backend stopping
    SYSTEM_HEALTH_CHECK = "system.health.check"           # Health check event
    WORKER_STARTED = "worker.started"                     # Worker came online
    WORKER_STOPPED = "worker.stopped"                     # Worker went offline
    
    @classmethod
    def all_topics(cls) -> list:
        """Return list of all defined topics."""
        return [
            value for name, value in vars(cls).items()
            if isinstance(value, str) and not name.startswith('_')
        ]
    
    @classmethod
    def get_domain(cls, topic: str) -> str:
        """Extract domain from topic (first segment)."""
        return topic.split('.')[0] if '.' in topic else topic
    
    @classmethod
    def matches_pattern(cls, pattern: str, topic: str) -> bool:
        """
        Check if topic matches pattern with wildcard support.
        
        Patterns:
            - "media.*" matches "media.ingested", "media.analysis.completed"
            - "*.completed" matches "publish.completed", "analysis.completed"
            - "*" matches everything
        """
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return pattern == topic
        
        # Convert glob pattern to regex-like matching
        pattern_parts = pattern.split('.')
        topic_parts = topic.split('.')
        
        # Handle "prefix.*" patterns
        if pattern.endswith('.*'):
            prefix = pattern[:-2]
            return topic.startswith(prefix + '.')
        
        # Handle "*.suffix" patterns
        if pattern.startswith('*.'):
            suffix = pattern[2:]
            return topic.endswith('.' + suffix) or topic == suffix
        
        return False
