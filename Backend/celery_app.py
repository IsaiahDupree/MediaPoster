"""
Celery Configuration for MediaPoster
Background task processing for scheduled publishing, metrics collection, and more
"""
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue
import os

# Import settings
from config import settings

# Create Celery app
celery_app = Celery('mediaposter')

# Configuration
celery_app.conf.update(
    # Broker and Result Backend
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    
    # Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task Configuration
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=300,  # 5 minutes soft limit
    
    # Worker Configuration
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    
    # Result Configuration
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,
    
    # Task Routing
    task_routes={
        'tasks.scheduled_publishing.*': {'queue': 'publishing'},
        'tasks.metrics.*': {'queue': 'metrics'},
        'tasks.monitoring.*': {'queue': 'monitoring'},
    },
    
    # Queues
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('publishing', Exchange('publishing'), routing_key='publishing', priority=10),
        Queue('metrics', Exchange('metrics'), routing_key='metrics', priority=5),
        Queue('monitoring', Exchange('monitoring'), routing_key='monitoring', priority=1),
    ),
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Beat Schedule (Periodic Tasks)
    beat_schedule={
        # Check for scheduled posts every minute
        'check-scheduled-posts': {
            'task': 'tasks.scheduled_publishing.check_scheduled_posts',
            'schedule': 60.0,  # 60 seconds
            'options': {'queue': 'publishing', 'priority': 10}
        },
        # Collect metrics every 15 minutes
        'collect-post-metrics': {
            'task': 'tasks.scheduled_publishing.collect_post_metrics',
            'schedule': 900.0,  # 15 minutes
            'options': {'queue': 'metrics', 'priority': 5}
        },
        # Retry failed posts every hour
        'retry-failed-posts': {
            'task': 'tasks.scheduled_publishing.retry_failed_posts',
            'schedule': 3600.0,  # 1 hour
            'options': {'queue': 'publishing', 'priority': 7}
        },
        # Clean  up old completed tasks (daily at 2 AM)
        'cleanup-old-task-results': {
            'task': 'tasks.monitoring.cleanup_old_results',
            'schedule': crontab(hour=2, minute=0),
            'options': {'queue': 'monitoring', 'priority': 1}
        },
    },
    
    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['tasks'])

if __name__ == '__main__':
    celery_app.start()
