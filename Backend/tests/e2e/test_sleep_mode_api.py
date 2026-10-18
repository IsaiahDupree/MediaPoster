"""
Sleep Mode API E2E Tests
=========================
End-to-end tests for Sleep Mode REST API endpoints.

Test Coverage:
- SLEEP-009: Sleep Mode Status API
- GET /api/sleep/status
- POST /api/sleep/enter
- POST /api/sleep/wake
- POST /api/sleep/schedule-wake
- DELETE /api/sleep/wake/{trigger_id}
- GET /api/sleep/health
- GET /api/sleep/wake-events

Tests validate:
- API responses match expected schema
- State transitions work correctly
- Wake scheduling and cancellation
- Error handling for invalid requests
- Wake event logging
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from main import app
from services.sleep_mode_service import SleepModeService, SleepState, WakeTriggerType


@pytest_asyncio.fixture
async def client():
    """Create test client"""
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def sleep_service():
    """Get sleep service instance and reset state"""
    service = SleepModeService.get_instance()

    # Ensure service is awake at start of each test
    if service.state == SleepState.SLEEPING:
        await service.wake(WakeTriggerType.MANUAL)

    # Clear wake triggers
    service.wake_triggers.clear()

    yield service

    # Cleanup after test
    if service.state == SleepState.SLEEPING:
        await service.wake(WakeTriggerType.MANUAL)
    service.wake_triggers.clear()


@pytest.mark.asyncio
@pytest.mark.e2e
class TestSleepStatusAPI:
    """Tests for GET /api/sleep/status"""

    async def test_get_status_when_awake(self, client, sleep_service):
        """
        SLEEP-009: GET /api/sleep/status returns awake state
        """
        response = client.get("/api/sleep/status")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data

        status = data["data"]
        assert status["state"] == "awake"
        assert "metrics" in status
        assert "wake_count" in status["metrics"]
        assert "sleep_count" in status["metrics"]
        assert "total_sleep_seconds" in status["metrics"]
        assert "upcoming_wakes" in status
        assert "next_wake_time" in status


    async def test_get_status_when_sleeping(self, client, sleep_service):
        """
        SLEEP-009: GET /api/sleep/status returns sleeping state
        """
        # Enter sleep mode
        await sleep_service.enter_sleep()

        response = client.get("/api/sleep/status")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        status = data["data"]
        assert status["state"] == "sleeping"
        assert "sleep_entered_at" in status


    async def test_status_includes_upcoming_wake_triggers(self, client, sleep_service):
        """
        SLEEP-009: Status includes scheduled wake triggers
        """
        # Schedule a wake trigger
        wake_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        sleep_service.schedule_wake(
            wake_time=wake_time,
            trigger_type=WakeTriggerType.SCHEDULED_POST,
            metadata={"post_id": "test123"}
        )

        response = client.get("/api/sleep/status")

        assert response.status_code == 200

        data = response.json()
        status = data["data"]

        assert len(status["upcoming_wakes"]) == 1
        trigger = status["upcoming_wakes"][0]
        assert trigger["trigger_type"] == "scheduled_post"
        assert "wake_time" in trigger
        assert "metadata" in trigger


@pytest.mark.asyncio
@pytest.mark.e2e
class TestSleepEnterAPI:
    """Tests for POST /api/sleep/enter"""

    async def test_enter_sleep_mode(self, client, sleep_service):
        """
        SLEEP-009: POST /api/sleep/enter successfully enters sleep mode
        """
        response = client.post("/api/sleep/enter")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Entered sleep mode"
        assert data["data"]["state"] == "sleeping"

        # Verify service state changed
        assert sleep_service.state == SleepState.SLEEPING


    async def test_cannot_enter_sleep_when_already_sleeping(self, client, sleep_service):
        """
        SLEEP-009: Entering sleep when already sleeping returns informative response
        """
        # Enter sleep first
        await sleep_service.enter_sleep()

        response = client.post("/api/sleep/enter")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Already in sleep mode"
        assert data["data"]["state"] == "sleeping"


@pytest.mark.asyncio
@pytest.mark.e2e
class TestWakeAPI:
    """Tests for POST /api/sleep/wake"""

    async def test_wake_from_sleep(self, client, sleep_service):
        """
        SLEEP-009: POST /api/sleep/wake successfully wakes from sleep
        """
        # Enter sleep first
        await sleep_service.enter_sleep()

        response = client.post(
            "/api/sleep/wake",
            json={"metadata": {"reason": "manual wake"}}
        )

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Woke from sleep"
        assert data["data"]["state"] == "awake"

        # Verify service state changed
        assert sleep_service.state == SleepState.AWAKE


    async def test_cannot_wake_when_already_awake(self, client, sleep_service):
        """
        SLEEP-009: Waking when already awake returns informative response
        """
        response = client.post("/api/sleep/wake")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Already awake"
        assert data["data"]["state"] == "awake"


    async def test_wake_with_metadata(self, client, sleep_service):
        """
        SLEEP-009: Wake accepts metadata in request
        """
        await sleep_service.enter_sleep()

        metadata = {"user": "test_user", "reason": "debugging"}
        response = client.post(
            "/api/sleep/wake",
            json={"metadata": metadata}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
@pytest.mark.e2e
class TestScheduleWakeAPI:
    """Tests for POST /api/sleep/schedule-wake"""

    async def test_schedule_wake_trigger(self, client, sleep_service):
        """
        SLEEP-009: POST /api/sleep/schedule-wake creates wake trigger
        """
        wake_time = datetime.now(timezone.utc) + timedelta(minutes=5)

        response = client.post(
            "/api/sleep/schedule-wake",
            json={
                "wake_time": wake_time.isoformat(),
                "trigger_type": "scheduled_post",
                "metadata": {"post_id": "abc123"}
            }
        )

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Wake scheduled"

        result = data["data"]
        assert "trigger_id" in result
        assert result["trigger_type"] == "scheduled_post"
        assert "seconds_until_wake" in result

        # Verify trigger was created
        assert len(sleep_service.wake_triggers) == 1


    async def test_schedule_wake_with_all_trigger_types(self, client, sleep_service):
        """
        SLEEP-009: Can schedule wake with all trigger types
        """
        trigger_types = [
            "scheduled_post",
            "safari_automation",
            "checkback_period",
            "user_access",
            "post_creation",
            "manual"
        ]

        for trigger_type in trigger_types:
            wake_time = datetime.now(timezone.utc) + timedelta(minutes=5)

            response = client.post(
                "/api/sleep/schedule-wake",
                json={
                    "wake_time": wake_time.isoformat(),
                    "trigger_type": trigger_type
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["trigger_type"] == trigger_type

            # Clean up
            sleep_service.wake_triggers.clear()


    async def test_schedule_wake_rejects_past_time(self, client, sleep_service):
        """
        SLEEP-009: Cannot schedule wake in the past
        """
        past_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        response = client.post(
            "/api/sleep/schedule-wake",
            json={
                "wake_time": past_time.isoformat(),
                "trigger_type": "manual"
            }
        )

        assert response.status_code == 400

        data = response.json()
        assert "wake_time must be in the future" in data["detail"]


    async def test_schedule_wake_rejects_invalid_trigger_type(self, client, sleep_service):
        """
        SLEEP-009: Rejects invalid trigger types
        """
        wake_time = datetime.now(timezone.utc) + timedelta(minutes=5)

        response = client.post(
            "/api/sleep/schedule-wake",
            json={
                "wake_time": wake_time.isoformat(),
                "trigger_type": "invalid_trigger_type"
            }
        )

        assert response.status_code == 400

        data = response.json()
        assert "Invalid trigger_type" in data["detail"]


@pytest.mark.asyncio
@pytest.mark.e2e
class TestCancelWakeAPI:
    """Tests for DELETE /api/sleep/wake/{trigger_id}"""

    async def test_cancel_wake_trigger(self, client, sleep_service):
        """
        SLEEP-009: DELETE /api/sleep/wake/{trigger_id} cancels trigger
        """
        # Create a wake trigger
        wake_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        trigger_id = sleep_service.schedule_wake(
            wake_time=wake_time,
            trigger_type=WakeTriggerType.MANUAL
        )

        # Cancel it
        response = client.delete(f"/api/sleep/wake/{trigger_id}")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Wake cancelled"
        assert data["data"]["trigger_id"] == trigger_id

        # Verify trigger was removed
        assert len(sleep_service.wake_triggers) == 0


    async def test_cancel_nonexistent_trigger(self, client, sleep_service):
        """
        SLEEP-009: Cancelling non-existent trigger returns 404
        """
        fake_trigger_id = str(uuid4())

        response = client.delete(f"/api/sleep/wake/{fake_trigger_id}")

        assert response.status_code == 404

        data = response.json()
        assert f"Wake trigger not found: {fake_trigger_id}" in data["detail"]


@pytest.mark.asyncio
@pytest.mark.e2e
class TestHealthAPI:
    """Tests for GET /api/sleep/health"""

    async def test_health_check(self, client, sleep_service):
        """
        SLEEP-009: GET /api/sleep/health returns service health
        """
        response = client.get("/api/sleep/health")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        health = data["data"]
        assert "is_running" in health
        assert "state" in health
        assert "wake_triggers_count" in health


@pytest.mark.asyncio
@pytest.mark.e2e
class TestWakeEventsAPI:
    """Tests for GET /api/sleep/wake-events (SLEEP-012)"""

    async def test_get_wake_events(self, client, sleep_service):
        """
        SLEEP-012: GET /api/sleep/wake-events returns wake event log
        """
        response = client.get("/api/sleep/wake-events")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        result = data["data"]
        assert "wake_events" in result
        assert "count" in result
        assert "total_wake_count" in result
        assert isinstance(result["wake_events"], list)


    async def test_wake_events_includes_recent_wakes(self, client, sleep_service):
        """
        SLEEP-012: Wake events log includes recent wake events
        """
        # Perform sleep/wake cycle
        await sleep_service.enter_sleep()
        await sleep_service.wake(WakeTriggerType.MANUAL, metadata={"test": "wake1"})

        response = client.get("/api/sleep/wake-events")

        assert response.status_code == 200

        data = response.json()
        result = data["data"]

        assert result["count"] >= 1
        assert result["total_wake_count"] >= 1

        # Check that wake events have expected structure
        if result["wake_events"]:
            event = result["wake_events"][0]
            assert "timestamp" in event
            assert "trigger_type" in event
            assert "sleep_duration_seconds" in event
            assert "metadata" in event


    async def test_wake_events_respects_limit(self, client, sleep_service):
        """
        SLEEP-012: Wake events API respects limit parameter
        """
        # Perform multiple sleep/wake cycles
        for i in range(5):
            await sleep_service.enter_sleep()
            await sleep_service.wake(WakeTriggerType.MANUAL)

        # Request with limit
        response = client.get("/api/sleep/wake-events?limit=3")

        assert response.status_code == 200

        data = response.json()
        result = data["data"]

        # Should return at most 3 events
        assert len(result["wake_events"]) <= 3


@pytest.mark.asyncio
@pytest.mark.e2e
class TestFullSleepWakeCycle:
    """Integration tests for full sleep/wake cycles via API"""

    async def test_full_manual_sleep_wake_cycle(self, client, sleep_service):
        """
        SLEEP-009: Complete cycle: check status → sleep → check status → wake → check status
        """
        # 1. Check initial status (awake)
        response = client.get("/api/sleep/status")
        assert response.status_code == 200
        assert response.json()["data"]["state"] == "awake"

        # 2. Enter sleep
        response = client.post("/api/sleep/enter")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 3. Check status (sleeping)
        response = client.get("/api/sleep/status")
        assert response.status_code == 200
        assert response.json()["data"]["state"] == "sleeping"

        # 4. Wake up
        response = client.post("/api/sleep/wake", json={"metadata": {"reason": "test"}})
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 5. Check final status (awake)
        response = client.get("/api/sleep/status")
        assert response.status_code == 200
        assert response.json()["data"]["state"] == "awake"


    async def test_schedule_wake_and_cancel(self, client, sleep_service):
        """
        SLEEP-009: Schedule wake trigger then cancel it
        """
        wake_time = datetime.now(timezone.utc) + timedelta(minutes=15)

        # 1. Schedule wake
        response = client.post(
            "/api/sleep/schedule-wake",
            json={
                "wake_time": wake_time.isoformat(),
                "trigger_type": "manual",
                "metadata": {"test": "cancel_test"}
            }
        )

        assert response.status_code == 200
        trigger_id = response.json()["data"]["trigger_id"]

        # 2. Verify it appears in status
        response = client.get("/api/sleep/status")
        status = response.json()["data"]
        assert len(status["upcoming_wakes"]) == 1

        # 3. Cancel the trigger
        response = client.delete(f"/api/sleep/wake/{trigger_id}")
        assert response.status_code == 200

        # 4. Verify it's gone from status
        response = client.get("/api/sleep/status")
        status = response.json()["data"]
        assert len(status["upcoming_wakes"]) == 0


    async def test_multiple_wake_triggers(self, client, sleep_service):
        """
        SLEEP-009: Can schedule multiple wake triggers
        """
        base_time = datetime.now(timezone.utc)
        trigger_ids = []

        # Schedule 3 wake triggers at different times
        for i in range(3):
            wake_time = base_time + timedelta(minutes=5 * (i + 1))

            response = client.post(
                "/api/sleep/schedule-wake",
                json={
                    "wake_time": wake_time.isoformat(),
                    "trigger_type": "manual",
                    "metadata": {"index": i}
                }
            )

            assert response.status_code == 200
            trigger_ids.append(response.json()["data"]["trigger_id"])

        # Verify all 3 appear in status
        response = client.get("/api/sleep/status")
        status = response.json()["data"]
        assert len(status["upcoming_wakes"]) == 3

        # Clean up
        for trigger_id in trigger_ids:
            client.delete(f"/api/sleep/wake/{trigger_id}")
