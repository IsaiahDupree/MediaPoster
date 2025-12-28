"""
Background Jobs Service
Unified job tracking for import, extraction, render, and scrape operations.
Replaces in-memory tracking with database persistence.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger


class BackgroundJobsService:
    """Service for managing background jobs in the database."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_job(
        self,
        job_type: str,
        input_data: Optional[Dict[str, Any]] = None,
        related_id: Optional[str] = None,
        related_type: Optional[str] = None,
    ) -> str:
        """
        Create a new background job.
        
        Args:
            job_type: Type of job ('import', 'extraction', 'render', 'scrape', 'analysis')
            input_data: Input parameters for the job
            related_id: Optional ID of related entity (e.g., video_id)
            related_type: Optional type of related entity (e.g., 'video')
            
        Returns:
            Job ID as string
        """
        import json
        job_id = str(uuid.uuid4())
        
        await self.db.execute(text("""
            INSERT INTO background_jobs (id, job_type, status, input_json, related_id, related_type)
            VALUES (:id, :job_type, 'pending', :input_json, :related_id, :related_type)
        """), {
            "id": job_id,
            "job_type": job_type,
            "input_json": json.dumps(input_data) if input_data else None,
            "related_id": related_id,
            "related_type": related_type,
        })
        await self.db.commit()
        
        logger.info(f"📋 [Jobs] Created {job_type} job: {job_id[:8]}...")
        return job_id
    
    async def start_job(self, job_id: str) -> bool:
        """Mark a job as started/running."""
        result = await self.db.execute(text("""
            UPDATE background_jobs 
            SET status = 'running', started_at = NOW(), updated_at = NOW()
            WHERE id = :id
        """), {"id": job_id})
        await self.db.commit()
        
        logger.info(f"▶️ [Jobs] Started job: {job_id[:8]}...")
        return result.rowcount > 0
    
    async def update_progress(
        self,
        job_id: str,
        progress: float,
        status: Optional[str] = None,
        output_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update job progress.
        
        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            status: Optional new status
            output_data: Optional partial output data
        """
        import json
        
        updates = ["progress = :progress", "updated_at = NOW()"]
        params: Dict[str, Any] = {"id": job_id, "progress": progress}
        
        if status:
            updates.append("status = :status")
            params["status"] = status
        
        if output_data:
            updates.append("output_json = :output_json")
            params["output_json"] = json.dumps(output_data)
        
        query = f"UPDATE background_jobs SET {', '.join(updates)} WHERE id = :id"
        result = await self.db.execute(text(query), params)
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def complete_job(
        self,
        job_id: str,
        output_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark a job as completed with optional output data."""
        import json
        
        result = await self.db.execute(text("""
            UPDATE background_jobs 
            SET status = 'completed', progress = 100, completed_at = NOW(), 
                updated_at = NOW(), output_json = :output_json
            WHERE id = :id
        """), {
            "id": job_id,
            "output_json": json.dumps(output_data) if output_data else None,
        })
        await self.db.commit()
        
        logger.info(f"✅ [Jobs] Completed job: {job_id[:8]}...")
        return result.rowcount > 0
    
    async def fail_job(self, job_id: str, error_message: str) -> bool:
        """Mark a job as failed with error message."""
        result = await self.db.execute(text("""
            UPDATE background_jobs 
            SET status = 'failed', completed_at = NOW(), updated_at = NOW(),
                error_message = :error_message
            WHERE id = :id
        """), {"id": job_id, "error_message": error_message})
        await self.db.commit()
        
        logger.error(f"❌ [Jobs] Failed job: {job_id[:8]}... - {error_message}")
        return result.rowcount > 0
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job."""
        result = await self.db.execute(text("""
            UPDATE background_jobs 
            SET status = 'cancelled', completed_at = NOW(), updated_at = NOW()
            WHERE id = :id AND status IN ('pending', 'running')
        """), {"id": job_id})
        await self.db.commit()
        
        logger.info(f"🚫 [Jobs] Cancelled job: {job_id[:8]}...")
        return result.rowcount > 0
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a single job by ID."""
        import json
        
        result = await self.db.execute(text("""
            SELECT id, job_type, status, progress, input_json, output_json,
                   error_message, started_at, completed_at, created_at, updated_at,
                   related_id, related_type
            FROM background_jobs WHERE id = :id
        """), {"id": job_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        return {
            "id": str(row[0]),
            "job_type": row[1],
            "status": row[2],
            "progress": float(row[3]) if row[3] else 0,
            "input_json": row[4] if isinstance(row[4], dict) else json.loads(row[4]) if row[4] else None,
            "output_json": row[5] if isinstance(row[5], dict) else json.loads(row[5]) if row[5] else None,
            "error_message": row[6],
            "started_at": row[7].isoformat() if row[7] else None,
            "completed_at": row[8].isoformat() if row[8] else None,
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
            "related_id": str(row[11]) if row[11] else None,
            "related_type": row[12],
        }
    
    async def list_jobs(
        self,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List jobs with optional filtering.
        
        Args:
            job_type: Filter by job type
            status: Filter by status
            limit: Max results
            offset: Pagination offset
            
        Returns:
            Dict with jobs list and total count
        """
        import json
        
        where_clauses = []
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        
        if job_type:
            where_clauses.append("job_type = :job_type")
            params["job_type"] = job_type
        
        if status:
            where_clauses.append("status = :status")
            params["status"] = status
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Get total count
        count_result = await self.db.execute(
            text(f"SELECT COUNT(*) FROM background_jobs {where_sql}"),
            params
        )
        total = count_result.scalar() or 0
        
        # Get jobs
        result = await self.db.execute(text(f"""
            SELECT id, job_type, status, progress, input_json, output_json,
                   error_message, started_at, completed_at, created_at, updated_at,
                   related_id, related_type
            FROM background_jobs 
            {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """), params)
        rows = result.fetchall()
        
        jobs = []
        for row in rows:
            jobs.append({
                "id": str(row[0]),
                "job_type": row[1],
                "status": row[2],
                "progress": float(row[3]) if row[3] else 0,
                "input_json": row[4] if isinstance(row[4], dict) else json.loads(row[4]) if row[4] else None,
                "output_json": row[5] if isinstance(row[5], dict) else json.loads(row[5]) if row[5] else None,
                "error_message": row[6],
                "started_at": row[7].isoformat() if row[7] else None,
                "completed_at": row[8].isoformat() if row[8] else None,
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None,
                "related_id": str(row[11]) if row[11] else None,
                "related_type": row[12],
            })
        
        return {
            "jobs": jobs,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    async def get_active_jobs(self, job_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all running jobs, optionally filtered by type."""
        result = await self.list_jobs(job_type=job_type, status="running", limit=100)
        return result["jobs"]
    
    async def cleanup_old_jobs(self, days: int = 30) -> int:
        """Delete completed/failed jobs older than specified days."""
        result = await self.db.execute(text("""
            DELETE FROM background_jobs 
            WHERE status IN ('completed', 'failed', 'cancelled')
            AND created_at < NOW() - INTERVAL ':days days'
        """), {"days": days})
        await self.db.commit()
        
        deleted = result.rowcount
        logger.info(f"🗑️ [Jobs] Cleaned up {deleted} old jobs")
        return deleted


# Convenience function for getting service instance
async def get_jobs_service(db: AsyncSession) -> BackgroundJobsService:
    """Get a BackgroundJobsService instance."""
    return BackgroundJobsService(db)
