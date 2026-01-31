"""
Commands Router

Handles command submission to MediaPoster.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from loguru import logger

from ..schemas import (
    CommandEnvelope,
    CommandAck,
    ErrorResponse,
    generate_id
)
from ..storage import job_store, event_store

router = APIRouter()


SUPPORTED_COMMANDS = {
    "ingest.sync",
    "ingest.scan", 
    "ingest.register",
    "analyze.transcribe",
    "analyze.vision",
    "analyze.summarize",
    "highlights.detect",
    "highlights.approve",
    "highlights.reject",
    "clip.generate",
    "clip.render_variations",
    "stage.upload",
    "publish.blotato",
    "monitor.check",
    "monitor.schedule",
    "monitor.autodelete",
    "watermark.remove",
    "config.get",
    "config.set",
    "system.snapshot",
    "safari.sora.generate",
    "safari.sora.generate.clean",
    "safari.sora.clean",
}


@router.post("/commands", response_model=CommandAck)
async def submit_command(envelope: CommandEnvelope):
    """
    Submit a command for execution.
    
    The command is validated, a job is created, and the job ID is returned.
    The actual execution happens asynchronously.
    
    Returns:
        CommandAck with job_id for tracking
    """
    if envelope.command not in SUPPORTED_COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown command: {envelope.command}. Supported: {sorted(SUPPORTED_COMMANDS)}"
        )
    
    if envelope.idempotency_key:
        existing_job = job_store.get_by_idempotency_key(envelope.idempotency_key)
        if existing_job:
            logger.info(f"Duplicate command with idempotency_key={envelope.idempotency_key}, returning existing job")
            return CommandAck(
                accepted=True,
                job_id=existing_job["job_id"],
                command_id=envelope.command_id,
                queued_at=existing_job["created_at"]
            )
    
    job_id = generate_id("job_")
    
    job = {
        "job_id": job_id,
        "command_id": envelope.command_id,
        "correlation_id": envelope.correlation_id,
        "command": envelope.command,
        "args": envelope.args,
        "state": "QUEUED",
        "stage": None,
        "percent": 0,
        "result": None,
        "error_code": None,
        "error_message": None,
        "idempotency_key": envelope.idempotency_key,
        "priority": envelope.priority,
        "timeout_s": envelope.timeout_s,
        "created_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None,
        "updated_at": datetime.utcnow()
    }
    
    job_store.create(job)
    
    event_store.emit({
        "event_id": generate_id("evt_"),
        "job_id": job_id,
        "correlation_id": envelope.correlation_id,
        "type": "job.queued",
        "message": f"Job queued: {envelope.command}",
        "timestamp": datetime.utcnow()
    })
    
    _dispatch_command(job_id, envelope)
    
    logger.info(f"Command accepted: {envelope.command} -> job_id={job_id}")
    
    return CommandAck(
        accepted=True,
        job_id=job_id,
        command_id=envelope.command_id,
        queued_at=datetime.utcnow()
    )


def _dispatch_command(job_id: str, envelope: CommandEnvelope):
    """
    Dispatch command to appropriate handler.
    
    This would typically enqueue a Celery task or call internal APIs.
    For now, we handle Safari commands directly.
    """
    if envelope.command.startswith("safari."):
        _handle_safari_command(job_id, envelope)
    else:
        pass


def _handle_safari_command(job_id: str, envelope: CommandEnvelope):
    """Handle Safari Automation commands."""
    import threading
    
    def run_safari_command():
        try:
            from services.safari_automation_client import SafariAutomationClient
            
            client = SafariAutomationClient()
            
            job_store.update(job_id, {
                "state": "RUNNING",
                "started_at": datetime.utcnow()
            })
            
            event_store.emit({
                "event_id": generate_id("evt_"),
                "job_id": job_id,
                "type": "job.started",
                "message": f"Executing: {envelope.command}",
                "timestamp": datetime.utcnow()
            })
            
            result = None
            
            if envelope.command == "safari.sora.generate":
                result = client.generate_video(
                    prompt=envelope.args.get("prompt", ""),
                    character=envelope.args.get("character"),
                    wait=True
                )
            elif envelope.command == "safari.sora.generate.clean":
                result = client.generate_clean_video(
                    prompt=envelope.args.get("prompt", ""),
                    character=envelope.args.get("character"),
                    wait=True
                )
            elif envelope.command == "safari.sora.clean":
                result = client.clean_video(
                    input_path=envelope.args.get("input_path", ""),
                    wait=True
                )
            
            if result and result.get("status") == "SUCCEEDED":
                job_store.update(job_id, {
                    "state": "SUCCEEDED",
                    "result": result.get("result"),
                    "percent": 100,
                    "completed_at": datetime.utcnow()
                })
                event_store.emit({
                    "event_id": generate_id("evt_"),
                    "job_id": job_id,
                    "type": "job.completed",
                    "message": "Command completed successfully",
                    "data": result.get("result", {}),
                    "timestamp": datetime.utcnow()
                })
            else:
                error = result.get("error", "Unknown error") if result else "No result"
                job_store.update(job_id, {
                    "state": "FAILED",
                    "error_code": "PROCESSING_FAILED",
                    "error_message": error,
                    "completed_at": datetime.utcnow()
                })
                event_store.emit({
                    "event_id": generate_id("evt_"),
                    "job_id": job_id,
                    "type": "job.failed",
                    "message": error,
                    "timestamp": datetime.utcnow()
                })
                
        except Exception as e:
            logger.error(f"Safari command failed: {e}")
            job_store.update(job_id, {
                "state": "FAILED",
                "error_code": "PROCESSING_FAILED",
                "error_message": str(e),
                "completed_at": datetime.utcnow()
            })
            event_store.emit({
                "event_id": generate_id("evt_"),
                "job_id": job_id,
                "type": "job.failed",
                "message": str(e),
                "timestamp": datetime.utcnow()
            })
    
    thread = threading.Thread(target=run_safari_command, daemon=True)
    thread.start()
