"""
Autonomous Slot Executor API
============================
API endpoints for monitoring and controlling the autonomous slot executor.

AUTO-006: Autonomous Slot Executor
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from loguru import logger

from workers.slot_executor import get_autonomous_slot_executor


router = APIRouter(prefix="/api/autonomous-executor", tags=["Autonomous Executor"])


@router.get("/status")
async def get_executor_status() -> Dict[str, Any]:
    """
    Get autonomous executor status and statistics.

    Returns:
        Execution status including:
        - is_running: Whether executor is active
        - executing_slots: Number of slots currently executing
        - failed_slots: Number of slots that have failed
        - executions: List of in-progress executions
        - failures: List of failed executions with details
    """
    try:
        executor = get_autonomous_slot_executor()
        status = executor.get_execution_status()

        return {
            "success": True,
            "status": status
        }

    except Exception as e:
        logger.error(f"Error getting executor status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_executor() -> Dict[str, Any]:
    """
    Start the autonomous slot executor service.

    The executor will begin monitoring for scheduled slots and
    automatically trigger execution when slots are due.

    Returns:
        Success confirmation
    """
    try:
        executor = get_autonomous_slot_executor()

        if executor._is_running:
            return {
                "success": True,
                "message": "Autonomous executor is already running"
            }

        await executor.start()

        return {
            "success": True,
            "message": "Autonomous executor started successfully"
        }

    except Exception as e:
        logger.error(f"Error starting executor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_executor() -> Dict[str, Any]:
    """
    Stop the autonomous slot executor service.

    In-progress executions will continue, but no new slots
    will be triggered until the service is restarted.

    Returns:
        Success confirmation
    """
    try:
        executor = get_autonomous_slot_executor()

        if not executor._is_running:
            return {
                "success": True,
                "message": "Autonomous executor is not running"
            }

        await executor.stop()

        return {
            "success": True,
            "message": "Autonomous executor stopped successfully"
        }

    except Exception as e:
        logger.error(f"Error stopping executor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions")
async def get_active_executions() -> Dict[str, Any]:
    """
    Get list of active slot executions.

    Returns:
        List of currently executing slots with timing and status
    """
    try:
        executor = get_autonomous_slot_executor()
        status = executor.get_execution_status()

        return {
            "success": True,
            "executions": status["executions"],
            "count": len(status["executions"])
        }

    except Exception as e:
        logger.error(f"Error getting executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failures")
async def get_failures() -> Dict[str, Any]:
    """
    Get list of failed slot executions.

    Returns:
        Failed slots with error details and retry counts
    """
    try:
        executor = get_autonomous_slot_executor()
        status = executor.get_execution_status()

        return {
            "success": True,
            "failures": status["failures"],
            "failed_slot_count": len(status["failures"])
        }

    except Exception as e:
        logger.error(f"Error getting failures: {e}")
        raise HTTPException(status_code=500, detail=str(e))
