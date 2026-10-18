"""
Celery Tasks Module
"""
from celery import shared_task

# Import all tasks to register them with Celery
from tasks.scheduled_publishing import (
    check_scheduled_posts,
    publish_scheduled_post,
    retry_failed_posts,
    collect_post_metrics
)

from tasks.monitoring import (
    cleanup_old_results,
    health_check
)

__all__ = [
    'check_scheduled_posts',
    'publish_scheduled_post',
    'retry_failed_posts',
    'collect_post_metrics',
    'cleanup_old_results',
    'health_check',
]
