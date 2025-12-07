from celery import shared_task
from sqlalchemy.orm import Session
from database.connection import async_session_maker
from services.ai_recommendation_service import AIRecommendationService
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)

@shared_task(name="generate_daily_recommendations")
def generate_daily_recommendations_task(user_id: str):
    """
    Celery task to generate daily recommendations for a user.
    """
    async def _generate(uid: uuid.UUID):
        async with async_session_maker() as session:
            service = AIRecommendationService(session)
            await service.generate_daily_recommendations(uid)

    try:
        uid = uuid.UUID(user_id)
        # Run async function in sync Celery task
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_generate(uid))
        logger.info(f"Successfully generated recommendations for user {user_id}")
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {e}")
        raise
