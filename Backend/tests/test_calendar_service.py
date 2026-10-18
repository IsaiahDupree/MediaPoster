import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from services.calendar_service import CalendarService
from database.models import ScheduledPost

@pytest.mark.asyncio
async def test_schedule_post():
    mock_db = AsyncMock()
    service = CalendarService(mock_db)
    
    clip_id = uuid4()
    platform = "tiktok"
    scheduled_time = datetime.now() + timedelta(days=1)
    
    # Mock db.add and db.commit
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    result = await service.schedule_post(
        clip_id=clip_id,
        platform=platform,
        scheduled_time=scheduled_time
    )
    
    assert result.platform == platform
    assert result.scheduled_time == scheduled_time
    assert result.status == 'scheduled'
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_calendar_posts():
    mock_db = AsyncMock()
    service = CalendarService(mock_db)
    user_id = uuid4()
    
    # Mock execute result
    mock_result = MagicMock()
    mock_post = ScheduledPost(
        id=uuid4(),
        platform="tiktok",
        scheduled_time=datetime.now(),
        status="scheduled",
        created_at=datetime.now(),
        published_at=None
    )
    mock_result.scalars.return_value.all.return_value = [mock_post]
    mock_db.execute.return_value = mock_result
    
    posts = await service.get_calendar_posts(user_id)
    
    assert len(posts) == 1
    assert posts[0]['platform'] == "tiktok"

@pytest.mark.asyncio
async def test_reschedule_post():
    mock_db = AsyncMock()
    service = CalendarService(mock_db)
    post_id = uuid4()
    new_time = datetime.now() + timedelta(days=2)
    
    # Mock existing post
    mock_post = ScheduledPost(
        id=post_id,
        status="scheduled",
        scheduled_time=datetime.now() + timedelta(days=1)
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_post
    mock_db.execute.return_value = mock_result
    
    result = await service.reschedule_post(post_id, new_time)
    
    assert result.scheduled_time == new_time
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_scheduled_post():
    mock_db = AsyncMock()
    service = CalendarService(mock_db)
    post_id = uuid4()
    
    # Mock existing post
    mock_post = ScheduledPost(
        id=post_id,
        status="scheduled"
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_post
    mock_db.execute.return_value = mock_result
    
    result = await service.cancel_scheduled_post(post_id)
    
    assert result is True
    assert mock_post.status == 'cancelled'
    mock_db.commit.assert_called_once()
