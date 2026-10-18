"""
Storage Module

In-memory storage for jobs and events.
In production, this would be backed by PostgreSQL/Supabase.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from threading import Lock
import uuid


class JobStore:
    """In-memory job storage with thread safety."""
    
    def __init__(self):
        self._jobs: Dict[str, Dict] = {}
        self._idempotency_index: Dict[str, str] = {}
        self._lock = Lock()
    
    def create(self, job: Dict) -> None:
        """Create a new job."""
        with self._lock:
            job_id = job["job_id"]
            self._jobs[job_id] = job.copy()
            
            if job.get("idempotency_key"):
                self._idempotency_index[job["idempotency_key"]] = job_id
    
    def get(self, job_id: str) -> Optional[Dict]:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(job_id, {}).copy() if job_id in self._jobs else None
    
    def get_by_idempotency_key(self, key: str) -> Optional[Dict]:
        """Get a job by idempotency key."""
        with self._lock:
            job_id = self._idempotency_index.get(key)
            if job_id:
                return self._jobs.get(job_id, {}).copy()
            return None
    
    def update(self, job_id: str, updates: Dict) -> bool:
        """Update a job."""
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            self._jobs[job_id].update(updates)
            self._jobs[job_id]["updated_at"] = datetime.utcnow()
            return True
    
    def list(
        self,
        filters: Optional[Dict] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict], int]:
        """List jobs with optional filters."""
        with self._lock:
            jobs = list(self._jobs.values())
            
            if filters:
                for key, value in filters.items():
                    jobs = [j for j in jobs if j.get(key) == value]
            
            jobs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
            
            total = len(jobs)
            jobs = jobs[offset:offset + limit]
            
            return [j.copy() for j in jobs], total
    
    def delete(self, job_id: str) -> bool:
        """Delete a job."""
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs.pop(job_id)
            if job.get("idempotency_key"):
                self._idempotency_index.pop(job["idempotency_key"], None)
            return True


class EventStore:
    """In-memory event storage with cursor support."""
    
    def __init__(self):
        self._events: List[Dict] = []
        self._cursor_counter = 0
        self._lock = Lock()
    
    def emit(self, event: Dict) -> str:
        """Emit a new event and return its cursor."""
        with self._lock:
            self._cursor_counter += 1
            cursor = f"cursor_{self._cursor_counter}"
            
            event_copy = event.copy()
            event_copy["cursor"] = cursor
            event_copy["stored_at"] = datetime.utcnow()
            
            if "timestamp" not in event_copy:
                event_copy["timestamp"] = datetime.utcnow()
            
            self._events.append(event_copy)
            
            return cursor
    
    def list_for_job(
        self,
        job_id: str,
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Tuple[List[Dict], int, Optional[str]]:
        """List events for a specific job."""
        with self._lock:
            events = [e for e in self._events if e.get("job_id") == job_id]
            
            if cursor:
                start_idx = 0
                for i, e in enumerate(events):
                    if e.get("cursor") == cursor:
                        start_idx = i + 1
                        break
                events = events[start_idx:]
            
            total = len(events)
            events = events[:limit]
            
            next_cursor = events[-1]["cursor"] if events else None
            
            return [e.copy() for e in events], total, next_cursor
    
    def get_since_cursor(
        self,
        cursor: Optional[str] = None,
        job_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get events since a cursor, with optional filters."""
        with self._lock:
            start_idx = 0
            
            if cursor:
                for i, e in enumerate(self._events):
                    if e.get("cursor") == cursor:
                        start_idx = i + 1
                        break
            
            events = self._events[start_idx:]
            
            if job_id:
                events = [e for e in events if e.get("job_id") == job_id]
            
            if correlation_id:
                events = [e for e in events if e.get("correlation_id") == correlation_id]
            
            return [e.copy() for e in events[:limit]]
    
    def get_all(self) -> List[Dict]:
        """Get all events."""
        with self._lock:
            return [e.copy() for e in self._events]


job_store = JobStore()
event_store = EventStore()
