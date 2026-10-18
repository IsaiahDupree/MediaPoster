"""
Batch Video Analysis Processor

Analyzes multiple videos in parallel with progress tracking, error handling,
and performance optimization.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

from services.video_pipeline import VideoAnalysisPipeline
from database.connection import get_db
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BatchAnalyzer:
    """Batch video analysis with parallel processing"""
    
    def __init__(self, max_workers: int = 10):
        """
        Initialize batch analyzer
        
        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers
        self.pipeline = VideoAnalysisPipeline()
        
        # Statistics
        self.total_videos = 0
        self.processed = 0
        self.succeeded = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = None
        self.errors = []
    
    async def analyze_all_videos(
        self,
        workspace_id: Optional[str] = None,
        limit: Optional[int] = None,
        skip_existing: bool = True,
        video_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze all videos (or filtered subset)
        
        Args:
            workspace_id: Only analyze videos in this workspace
            limit: Maximum videos to process
            skip_existing: Skip already analyzed videos
            video_ids: Specific video IDs to analyze
            
        Returns:
            Summary dict with statistics
        """
        self.start_time = datetime.now()
        logger.info("="* 60)
        logger.info("BATCH VIDEO ANALYSIS STARTED")
        logger.info(f"Max workers: {self.max_workers}")
        logger.info(f"Skip existing: {skip_existing}")
        logger.info("="* 60)
        
        # Get videos to analyze
        async for session in get_db():
            videos = await self._get_videos_to_analyze(
                session,
                workspace_id=workspace_id,
                limit=limit,
                skip_existing=skip_existing,
                video_ids=video_ids
            )
            
            self.total_videos = len(videos)
            logger.info(f"\n📊 Found {self.total_videos} videos to analyze\n")
            
            if self.total_videos == 0:
                return self._get_summary()
            
            # Create semaphore for worker limit
            semaphore = asyncio.Semaphore(self.max_workers)
            
            # Create tasks for all videos
            tasks = [
                self._analyze_with_semaphore(
                    video_id=video['id'],
                    video_path=video['source_uri'],
                    video_name=video['file_name'],
                    semaphore=semaphore,
                    skip_existing=skip_existing
                )
                for video in videos
            ]
            
            # Run all tasks with progress reporting
            results = await self._run_with_progress(tasks)
            
            # Process results
            for result in results:
                if result['status'] == 'success':
                    self.succeeded += 1
                elif result['status'] == 'skipped':
                    self.skipped += 1
                elif result['status'] == 'error':
                    self.failed += 1
                    self.errors.append({
                        'video_id': result.get('video_id'),
                        'error': result.get('error')
                    })
        
        return self._get_summary()
    
    async def _get_videos_to_analyze(
        self,
        session,
        workspace_id: Optional[str],
        limit: Optional[int],
        skip_existing: bool,
        video_ids: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Get list of videos to analyze"""
        
        where_clauses = []
        params = {}
        
        # Filter by workspace
        if workspace_id:
            where_clauses.append("workspace_id = :workspace_id")
            params['workspace_id'] = workspace_id
        
        # Filter by specific IDs
        if video_ids:
            placeholders = ','.join([f':vid{i}' for i in range(len(video_ids))])
            where_clauses.append(f"id IN ({placeholders})")
            for i, vid in enumerate(video_ids):
                params[f'vid{i}'] = vid
        
        # Skip already analyzed
        if skip_existing:
            where_clauses.append("""
                id NOT IN (
                    SELECT DISTINCT video_id 
                    FROM video_words
                )
            """)
        
        # Build query
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT 
                id,
                file_name,
                source_uri,
                duration_sec
            FROM videos
            WHERE {where_sql}
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        result = await session.execute(text(query), params)
        videos = result.fetchall()
        
        return [
            {
                'id': str(v.id),
                'file_name': v.file_name,
                'source_uri': v.source_uri,
                'duration_sec': v.duration_sec
            }
            for v in videos
        ]
    
    async def _analyze_with_semaphore(
        self,
        video_id: str,
        video_path: str,
        video_name: str,
        semaphore: asyncio.Semaphore,
        skip_existing: bool
    ) -> Dict[str, Any]:
        """Analyze single video with semaphore control"""
        
        async with semaphore:
            logger.info(f"🎬 Starting: {video_name[:50]}")
            
            async for session in get_db():
                try:
                    # Check if file exists
                    if not Path(video_path).exists():
                        logger.warning(f"  ⚠️  File not found: {video_path}")
                        return {
                            'status': 'error',
                            'video_id': video_id,
                            'error': 'File not found'
                        }
                    
                    # Run analysis
                    result = await self.pipeline.analyze_video_complete(
                        video_id=video_id,
                        video_path=video_path,
                        db_session=session,
                        skip_existing=skip_existing
                    )
                    
                    self.processed += 1
                    
                    if result['status'] == 'success':
                        logger.info(f"  ✅ Complete: {result['word_count']} words, {result['frame_count']} frames ({result['duration_seconds']:.1f}s)")
                    elif result['status'] == 'skipped':
                        logger.info(f"  ⏭️  Skipped: Already analyzed")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"  ❌ Error: {e}")
                    self.processed += 1
                    return {
                        'status': 'error',
                        'video_id': video_id,
                        'error': str(e)
                    }
    
    async def _run_with_progress(self, tasks: List) -> List[Dict[str, Any]]:
        """Run tasks with progress reporting"""
        
        results = []
        
        # Run all tasks and collect results
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            
            # Log progress every 10 videos
            if self.processed % 10 == 0:
                self._log_progress()
        
        return results
    
    def _log_progress(self):
        """Log current progress"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.processed / elapsed if elapsed > 0 else 0
        remaining = self.total_videos - self.processed
        eta_seconds = remaining / rate if rate > 0 else 0
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"📊 Progress: {self.processed}/{self.total_videos} ({self.processed/self.total_videos*100:.1f}%)")
        logger.info(f"   ✅ Succeeded: {self.succeeded}")
        logger.info(f"   ⏭️  Skipped: {self.skipped}")
        logger.info(f"   ❌ Failed: {self.failed}")
        logger.info(f"   ⚡ Rate: {rate:.1f} videos/sec")
        logger.info(f"   ⏱️  ETA: {timedelta(seconds=int(eta_seconds))}")
        logger.info("=" * 60)
        logger.info("")
    
    def _get_summary(self) -> Dict[str, Any]:
        """Get final summary"""
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        summary = {
            'status': 'completed',
            'total_videos': self.total_videos,
            'processed': self.processed,
            'succeeded': self.succeeded,
            'skipped': self.skipped,
            'failed': self.failed,
            'duration_seconds': round(elapsed, 2),
            'avg_seconds_per_video': round(elapsed / self.processed, 2) if self.processed > 0 else 0,
            'videos_per_second': round(self.processed / elapsed, 2) if elapsed > 0 else 0
        }
        
        if self.errors:
            summary['errors'] = self.errors[:10]  # First 10 errors
            summary['error_count'] = len(self.errors)
        
        return summary
    
    def save_summary(self, output_file: str = "batch_analysis_summary.json"):
        """Save summary to file"""
        summary = self._get_summary()
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"\n📝 Summary saved to {output_file}")


async def analyze_batch_cli(
    limit: int = None,
    workers: int = 10,
    workspace_id: str = None,
    skip_existing: bool = True
):
    """
    CLI interface for batch analysis
    
    Usage:
        python -m services.batch_analyzer --limit 100 --workers 20
    """
    
    # Initialize database connection
    from database.connection import init_db
    await init_db()
    logger.info("Database initialized")
    
    analyzer = BatchAnalyzer(max_workers=workers)
    
    summary = await analyzer.analyze_all_videos(
        workspace_id=workspace_id,
        limit=limit,
        skip_existing=skip_existing
    )
    
    # Print final summary
    logger.info("\n")
    logger.info("=" * 60)
    logger.info("BATCH ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total videos: {summary['total_videos']}")
    logger.info(f"Processed: {summary['processed']}")
    logger.info(f"Succeeded: {summary['succeeded']}")
    logger.info(f"Skipped: {summary['skipped']}")
    logger.info(f"Failed: {summary['failed']}")
    logger.info(f"Duration: {timedelta(seconds=int(summary['duration_seconds']))}")
    logger.info(f"Rate: {summary['videos_per_second']:.2f} videos/sec")
    logger.info(f"Avg time per video: {summary['avg_seconds_per_video']:.1f}s")
    
    if summary.get('errors'):
        logger.info(f"\n❌ Errors ({summary['error_count']}):")
        for error in summary['errors']:
            logger.info(f"  - {error['video_id']}: {error['error']}")
    
    logger.info("=" * 60)
    
    # Save summary
    analyzer.save_summary()
    
    return summary


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch analyze videos")
    parser.add_argument('--limit', type=int, help='Max videos to process')
    parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers')
    parser.add_argument('--workspace-id', type=str, help='Workspace ID to filter')
    parser.add_argument('--no-skip', action='store_true', help='Reanalyze already processed videos')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Run batch analysis
    asyncio.run(analyze_batch_cli(
        limit=args.limit,
        workers=args.workers,
        workspace_id=args.workspace_id,
        skip_existing=not args.no_skip
    ))
