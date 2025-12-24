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
    # CLIP EXTRACTION (Long-form to Short-form)
    # =========================================================================
    CLIP_EXTRACTION_REQUESTED = "clip.extraction.requested"     # Request to extract clips
    CLIP_EXTRACTION_STARTED = "clip.extraction.started"         # Worker picked up job
    CLIP_EXTRACTION_PROGRESS = "clip.extraction.progress"       # Progress update
    CLIP_TRANSCRIPT_COMPLETED = "clip.extraction.transcript"    # Transcript ready
    CLIP_SEGMENTS_IDENTIFIED = "clip.extraction.segments"       # AI found segments
    CLIP_RENDERING_STARTED = "clip.extraction.rendering"        # Rendering clips
    CLIP_SINGLE_COMPLETED = "clip.extraction.clip_done"         # One clip finished
    CLIP_EXTRACTION_COMPLETED = "clip.extraction.completed"     # All clips done
    CLIP_EXTRACTION_FAILED = "clip.extraction.failed"           # Extraction error
    
    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    NOTIFICATION_CREATED = "notification.created"         # New notification
    NOTIFICATION_SENT = "notification.sent"               # Notification delivered
    
    # =========================================================================
    # COMMENTS & ENGAGEMENT
    # =========================================================================
    COMMENT_RECEIVED = "comment.received"                 # New comment detected
    COMMENT_ANALYZED = "comment.analyzed"                 # Sentiment/intent analyzed
    COMMENT_REPLIED = "comment.replied"                   # Auto-reply sent
    COMMENT_FLAGGED = "comment.flagged"                   # Comment flagged for review
    FAN_IDENTIFIED = "fan.identified"                     # Top fan identified
    FAN_TIER_CHANGED = "fan.tier_changed"                 # Fan tier upgraded/downgraded
    TOP_FAN_ALERT = "fan.top_fan_alert"                   # Top fan activity alert
    
    # =========================================================================
    # WORKFLOWS
    # =========================================================================
    WORKFLOW_CREATED = "workflow.created"                 # New workflow created
    WORKFLOW_STARTED = "workflow.started"                 # Workflow execution started
    WORKFLOW_STEP_COMPLETED = "workflow.step.completed"   # Workflow step finished
    WORKFLOW_COMPLETED = "workflow.completed"             # Workflow finished
    WORKFLOW_FAILED = "workflow.failed"                   # Workflow error
    
    # =========================================================================
    # SOCIAL ACCOUNTS
    # =========================================================================
    ACCOUNT_CONNECTED = "account.connected"               # New account connected
    ACCOUNT_SYNCED = "account.synced"                     # Account data refreshed
    ACCOUNT_DISCONNECTED = "account.disconnected"         # Account removed
    ACCOUNT_METRICS_UPDATED = "account.metrics_updated"   # Account metrics refreshed
    
    # =========================================================================
    # EMAIL NOTIFICATIONS
    # =========================================================================
    EMAIL_QUEUED = "email.queued"                         # Email queued for sending
    EMAIL_SENT = "email.sent"                             # Email sent successfully
    EMAIL_FAILED = "email.failed"                         # Email send failed
    
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
    NARRATIVE_SIGNALS_UPDATED = "narrative.signals.updated"      # Signals refreshed
    
    # =========================================================================
    # GOALS
    # =========================================================================
    GOAL_CREATED = "goal.created"                                 # New goal created
    GOAL_UPDATED = "goal.updated"                                 # Goal progress updated
    GOAL_COMPLETED = "goal.completed"                             # Goal achieved
    
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
    # SCHEDULER (Execution) - DEPRECATED: Use schedule.* topics instead
    # These are kept for backwards compatibility but new code should use:
    #   - SCHEDULE_CREATED instead of SCHEDULER_CREATE_ITEMS
    #   - SCHEDULE_UPDATED instead of SCHEDULER_UPDATE_ITEM
    #   - SCHEDULE_CANCELLED instead of SCHEDULER_CANCEL_ITEM
    #   - SCHEDULE_DUE instead of SCHEDULER_ITEM_DUE
    # =========================================================================
    SCHEDULER_CREATE_ITEMS = "mp.scheduler.cmd.create_items"      # DEPRECATED: Use SCHEDULE_CREATED
    SCHEDULER_UPDATE_ITEM = "mp.scheduler.cmd.update_item"        # DEPRECATED: Use SCHEDULE_UPDATED
    SCHEDULER_CANCEL_ITEM = "mp.scheduler.cmd.cancel_item"        # DEPRECATED: Use SCHEDULE_CANCELLED
    SCHEDULER_ITEM_SCHEDULED = "mp.scheduler.evt.item_scheduled"  # DEPRECATED: Use SCHEDULE_CREATED
    SCHEDULER_ITEM_DUE = "mp.scheduler.evt.item_due"              # DEPRECATED: Use SCHEDULE_DUE
    SCHEDULER_ITEM_CANCELED = "mp.scheduler.evt.item_canceled"    # DEPRECATED: Use SCHEDULE_CANCELLED
    
    # =========================================================================
    # TRENDS (Opportunity Signals)
    # =========================================================================
    TREND_SYNC_PROVIDER = "mp.trends.cmd.sync_provider"           # Trigger provider pull
    TREND_RAW_INGESTED = "mp.trends.evt.raw_ingested"             # Raw payload stored
    TREND_NORMALIZED_READY = "mp.trends.evt.normalized_ready"     # Normalized items ready
    TREND_CLUSTER_READY = "mp.trends.evt.cluster_ready"           # Cluster computed
    TREND_OPPORTUNITY_READY = "mp.trends.evt.opportunity_ready"   # Scored opportunity
    TREND_ALERT = "mp.trends.evt.alert"                           # Big spike / time-sensitive
    TREND_BRIEF_READY = "mp.briefs.evt.trend_brief_ready"         # Brief generated
    TREND_ASSET_MATCHED = "mp.trends.evt.asset_matched"           # Assets matched to trend
    
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
