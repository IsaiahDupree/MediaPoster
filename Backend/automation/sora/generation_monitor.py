"""
Generation Monitor - Monitors Sora video generation progress

Polls Safari for generation status and provides callbacks/events.
"""
import asyncio
from typing import Callable, Dict, Optional
from datetime import datetime
from loguru import logger

from .sora_controller import SoraController


class GenerationMonitor:
    """Monitors Sora video generation and provides status updates."""
    
    def __init__(self, controller: Optional[SoraController] = None):
        self.controller = controller or SoraController()
        self.is_monitoring = False
        self.current_job_id: Optional[str] = None
        self.callbacks: Dict[str, Callable] = {}
    
    def on_progress(self, callback: Callable[[int], None]):
        """Register callback for progress updates."""
        self.callbacks["progress"] = callback
    
    def on_complete(self, callback: Callable[[Dict], None]):
        """Register callback for completion."""
        self.callbacks["complete"] = callback
    
    def on_error(self, callback: Callable[[str], None]):
        """Register callback for errors."""
        self.callbacks["error"] = callback
    
    async def start_monitoring(
        self,
        job_id: str,
        timeout_minutes: int = 10,
        poll_interval: int = 10
    ) -> Dict:
        """
        Start monitoring a generation job.
        
        Args:
            job_id: Unique identifier for this generation job
            timeout_minutes: Maximum time to wait
            poll_interval: Seconds between status checks
            
        Returns:
            Final status dict
        """
        self.is_monitoring = True
        self.current_job_id = job_id
        
        logger.info(f"📊 Starting generation monitor for job {job_id}")
        
        start_time = datetime.now()
        max_seconds = timeout_minutes * 60
        last_progress = 0
        
        try:
            while self.is_monitoring:
                elapsed = (datetime.now() - start_time).total_seconds()
                
                if elapsed > max_seconds:
                    error_msg = f"Generation timeout after {timeout_minutes} minutes"
                    logger.error(f"❌ {error_msg}")
                    if "error" in self.callbacks:
                        self.callbacks["error"](error_msg)
                    return {"status": "timeout", "job_id": job_id, "elapsed_seconds": elapsed}
                
                status = await self.controller.get_generation_status()
                
                # Handle progress updates
                progress = status.get("progress_percent")
                if progress and progress != last_progress:
                    last_progress = progress
                    logger.info(f"📈 Progress: {progress}%")
                    if "progress" in self.callbacks:
                        self.callbacks["progress"](progress)
                
                # Handle completion
                if status.get("status") == "completed":
                    logger.success(f"✅ Generation completed for job {job_id}")
                    result = {
                        "status": "completed",
                        "job_id": job_id,
                        "elapsed_seconds": elapsed,
                        "video_src": status.get("video_src")
                    }
                    if "complete" in self.callbacks:
                        self.callbacks["complete"](result)
                    return result
                
                # Handle failure
                if status.get("status") == "failed":
                    error_msg = status.get("error_text", "Unknown error")
                    logger.error(f"❌ Generation failed: {error_msg}")
                    if "error" in self.callbacks:
                        self.callbacks["error"](error_msg)
                    return {
                        "status": "failed",
                        "job_id": job_id,
                        "error": error_msg,
                        "elapsed_seconds": elapsed
                    }
                
                await asyncio.sleep(poll_interval)
        
        finally:
            self.is_monitoring = False
            self.current_job_id = None
        
        return {"status": "stopped", "job_id": job_id}
    
    def stop_monitoring(self):
        """Stop the current monitoring session."""
        self.is_monitoring = False
        logger.info("⏹️ Monitoring stopped")
    
    async def get_current_status(self) -> Dict:
        """Get current generation status without blocking."""
        status = await self.controller.get_generation_status()
        return {
            "job_id": self.current_job_id,
            "is_monitoring": self.is_monitoring,
            **status
        }


class GenerationQueue:
    """Queue for managing multiple generation jobs."""
    
    def __init__(self, controller: Optional[SoraController] = None):
        self.controller = controller or SoraController()
        self.monitor = GenerationMonitor(self.controller)
        self.queue: list = []
        self.completed: list = []
        self.failed: list = []
        self.is_processing = False
    
    def add_job(self, prompt: str, character: Optional[str] = None, job_id: Optional[str] = None):
        """Add a generation job to the queue."""
        import uuid
        job = {
            "id": job_id or str(uuid.uuid4()),
            "prompt": prompt,
            "character": character,
            "status": "queued",
            "created_at": datetime.now().isoformat()
        }
        self.queue.append(job)
        logger.info(f"📝 Added job to queue: {job['id']}")
        return job
    
    async def process_queue(
        self,
        timeout_per_job: int = 10,
        delay_between_jobs: int = 5
    ) -> Dict:
        """Process all jobs in the queue."""
        if self.is_processing:
            return {"error": "Queue already processing"}
        
        self.is_processing = True
        results = []
        
        try:
            # Launch Sora if needed
            await self.controller.launch_sora()
            await asyncio.sleep(2)
            
            while self.queue:
                job = self.queue.pop(0)
                job["status"] = "processing"
                logger.info(f"🎬 Processing job {job['id']}: {job['prompt'][:50]}...")
                
                # Submit the prompt
                success = await self.controller.submit_prompt(
                    job["prompt"],
                    job.get("character")
                )
                
                if not success:
                    job["status"] = "failed"
                    job["error"] = "Failed to submit prompt"
                    self.failed.append(job)
                    results.append(job)
                    continue
                
                # Monitor generation
                result = await self.monitor.start_monitoring(
                    job["id"],
                    timeout_minutes=timeout_per_job
                )
                
                job["status"] = result.get("status")
                job["result"] = result
                
                if result.get("status") == "completed":
                    job["video_src"] = result.get("video_src")
                    self.completed.append(job)
                else:
                    job["error"] = result.get("error")
                    self.failed.append(job)
                
                results.append(job)
                
                # Delay between jobs
                if self.queue:
                    logger.info(f"⏳ Waiting {delay_between_jobs}s before next job...")
                    await asyncio.sleep(delay_between_jobs)
        
        finally:
            self.is_processing = False
        
        return {
            "total": len(results),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "results": results
        }
    
    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        return {
            "is_processing": self.is_processing,
            "queued": len(self.queue),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "queue": self.queue,
            "completed_jobs": self.completed,
            "failed_jobs": self.failed
        }
