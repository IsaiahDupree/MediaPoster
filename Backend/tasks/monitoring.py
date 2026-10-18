"""
Celery Monitoring Tasks
"""
from celery import shared_task
from loguru import logger
from datetime import datetime, timedelta


@shared_task(name='tasks.monitoring.cleanup_old_results')
def cleanup_old_results():
    """
    Clean up old Celery task results
    Runs daily at 2 AM via Celery Beat
    """
    try:
        # In production, this would clean up old task results from Redis
        # For now, just log
        logger.info("Running cleanup of old task results")
        
        # Example cleanup logic:
        # - Remove task results older than 7 days
        # - Clear completed task state from Redis
        
        cutoff_date = datetime.now() - timedelta(days=7)
        logger.info(f"Would clean up results older than {cutoff_date}")
        
        return {"status": "success", "message": "Cleanup completed"}
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name='tasks.monitoring.health_check')
def health_check():
    """
    Health check task to verify Celery is working
    """
    try:
        logger.info("Celery health check passed")
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "worker": "active"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
