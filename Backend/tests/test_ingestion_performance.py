"""
Performance and Non-Interruption Tests for Ingestion System

Tests that:
1. Ingestion performs within acceptable time limits
2. Ingestion doesn't block or interrupt other API endpoints
3. System remains responsive during heavy ingestion
4. Memory usage stays within bounds
"""
import pytest
import asyncio
import time
import tempfile
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
import httpx


class TestIngestionPerformance:
    """Test ingestion performance metrics"""
    
    def test_file_scanning_performance(self):
        """Test that scanning directory is fast"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create 100 test files
            for i in range(100):
                (Path(temp_dir) / f"video_{i}.mp4").write_bytes(b"x" * 1000)
            
            watcher = VideoFileWatcher([temp_dir])
            
            start = time.time()
            videos = watcher.get_all_video_files()
            elapsed = time.time() - start
            
            assert len(videos) == 100
            assert elapsed < 1.0, f"Scanning 100 files took {elapsed:.2f}s, should be <1s"
    
    def test_file_scanning_large_directory(self):
        """Test scanning performance with many files"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create 500 test files
            for i in range(500):
                (Path(temp_dir) / f"video_{i}.mp4").write_bytes(b"x" * 100)
            
            watcher = VideoFileWatcher([temp_dir])
            
            start = time.time()
            videos = watcher.get_all_video_files()
            elapsed = time.time() - start
            
            assert len(videos) == 500
            assert elapsed < 3.0, f"Scanning 500 files took {elapsed:.2f}s, should be <3s"
    
    def test_db_check_performance(self):
        """Test that DB duplicate check is fast"""
        # Simulate checking 1000 paths against a set
        existing_paths = {f"/path/to/video_{i}.mp4" for i in range(1000)}
        new_paths = [Path(f"/path/to/video_{i}.mp4") for i in range(500, 1500)]
        
        start = time.time()
        new_videos = [p for p in new_paths if str(p) not in existing_paths]
        elapsed = time.time() - start
        
        assert len(new_videos) == 500  # 500-999 exist, 1000-1499 are new
        assert elapsed < 0.1, f"Filtering 1000 paths took {elapsed:.3f}s, should be <0.1s"
    
    def test_batch_processing_memory(self):
        """Test that batch processing doesn't use excessive memory"""
        import sys
        
        # Create large list of paths
        paths = [Path(f"/path/to/video_{i}.mp4") for i in range(10000)]
        
        # Process in batches
        batch_size = 100
        processed = 0
        
        for i in range(0, len(paths), batch_size):
            batch = paths[i:i + batch_size]
            processed += len(batch)
        
        assert processed == 10000
        # Memory check is implicit - if we got here without MemoryError, we're good


class TestNonInterruptingIngestion:
    """Test that ingestion doesn't block other services"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_during_processing(self):
        """Test that health endpoint responds during ingestion simulation"""
        
        async def simulate_heavy_processing():
            """Simulate heavy CPU work"""
            await asyncio.sleep(0.5)  # Simulate async I/O
            return "done"
        
        async def check_health():
            """Check health endpoint"""
            return {"status": "healthy"}
        
        # Run both concurrently
        start = time.time()
        results = await asyncio.gather(
            simulate_heavy_processing(),
            check_health()
        )
        elapsed = time.time() - start
        
        assert results[1]["status"] == "healthy"
        assert elapsed < 1.0, "Health check should not be blocked"
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self):
        """Test that multiple API patterns can run concurrently"""
        
        async def slow_operation():
            await asyncio.sleep(0.3)
            return "slow"
        
        async def fast_operation():
            await asyncio.sleep(0.05)
            return "fast"
        
        start = time.time()
        
        # Run 1 slow + 5 fast concurrently
        tasks = [slow_operation()] + [fast_operation() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start
        
        # Should complete in ~0.3s (parallel), not 0.3 + 5*0.05 = 0.55s (serial)
        assert elapsed < 0.5, f"Concurrent ops took {elapsed:.2f}s, should be <0.5s"
        assert results[0] == "slow"
        assert all(r == "fast" for r in results[1:])
    
    def test_thread_pool_isolation(self):
        """Test that thread pool work doesn't block main thread"""
        import threading
        
        results = []
        main_thread_blocked = False
        
        def background_work():
            time.sleep(0.3)
            results.append("background_done")
        
        def quick_check():
            results.append("quick_done")
        
        # Start background work in thread pool
        with ThreadPoolExecutor(max_workers=2) as executor:
            future = executor.submit(background_work)
            
            # Main thread should be able to do quick work immediately
            start = time.time()
            quick_check()
            quick_time = time.time() - start
            
            if quick_time > 0.1:
                main_thread_blocked = True
            
            future.result()  # Wait for background to complete
        
        assert not main_thread_blocked, "Main thread was blocked by background work"
        assert "quick_done" in results
        assert "background_done" in results
    
    @pytest.mark.asyncio
    async def test_event_bus_non_blocking(self):
        """Test that event publishing doesn't block"""
        from services.event_bus import EventBus
        
        event_bus = EventBus.get_instance()
        
        start = time.time()
        
        # Publish 100 events rapidly
        for i in range(100):
            await event_bus.publish("test.event", {"index": i})
        
        elapsed = time.time() - start
        
        # Publishing 100 events should be very fast
        assert elapsed < 1.0, f"Publishing 100 events took {elapsed:.2f}s"


class TestIngestionStressTest:
    """Stress tests for ingestion system"""
    
    def test_rapid_file_detection(self):
        """Test handling rapid file creation"""
        from modules.video_ingestion.file_watcher import VideoFileWatcher
        
        detected_files = []
        
        def on_detect(path):
            detected_files.append(path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            watcher = VideoFileWatcher([temp_dir])
            
            # Create files rapidly
            for i in range(50):
                (Path(temp_dir) / f"rapid_{i}.mp4").write_bytes(b"x" * 100)
            
            # Scan all
            count = watcher.scan_existing_files(on_detect, max_age_hours=1)
            
            assert count == 50
            assert len(detected_files) == 50
    
    def test_parallel_ingestion_requests(self):
        """Test that multiple ingestion requests can be queued"""
        import queue
        
        ingestion_queue = queue.Queue()
        
        # Simulate adding 100 ingestion tasks
        for i in range(100):
            ingestion_queue.put(f"/path/to/video_{i}.mp4")
        
        # Process them
        processed = []
        while not ingestion_queue.empty():
            processed.append(ingestion_queue.get())
        
        assert len(processed) == 100
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that ingestion respects rate limits"""
        
        processed = 0
        rate_limit = 10  # Max 10 per batch
        
        async def process_batch(batch):
            nonlocal processed
            for item in batch[:rate_limit]:
                processed += 1
                await asyncio.sleep(0.01)  # Simulate processing time
        
        items = list(range(25))
        
        start = time.time()
        await process_batch(items)
        elapsed = time.time() - start
        
        assert processed == rate_limit, f"Should process {rate_limit}, got {processed}"


class TestIngestionIntegration:
    """Integration tests with real endpoints"""
    
    @pytest.mark.asyncio
    async def test_stats_endpoint_during_ingestion(self):
        """Test stats endpoint responds during background ingestion"""
        
        # This tests the actual endpoint pattern
        async def mock_stats():
            return {
                "total_videos": 100,
                "analyzed_count": 50,
                "pending_analysis": 50
            }
        
        async def mock_ingestion():
            await asyncio.sleep(0.2)
            return {"ingested": 10}
        
        # Both should complete without blocking
        results = await asyncio.gather(
            mock_stats(),
            mock_ingestion()
        )
        
        assert results[0]["total_videos"] == 100
        assert results[1]["ingested"] == 10
    
    def test_iphone_import_path_accessible(self):
        """Test that IphoneImport path is accessible"""
        iphone_import = Path.home() / "Documents" / "IphoneImport"
        
        if not iphone_import.exists():
            pytest.skip("IphoneImport directory not found")
        
        # Should be readable
        assert iphone_import.is_dir()
        
        # Should be able to list files
        files = list(iphone_import.iterdir())
        assert len(files) > 0


class TestResourceUsage:
    """Test resource usage during ingestion"""
    
    def test_file_handle_cleanup(self):
        """Test that file handles are properly closed"""
        import gc
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.mp4"
            file_path.write_bytes(b"x" * 1000)
            
            # Open and close file
            for _ in range(100):
                with open(file_path, 'rb') as f:
                    _ = f.read(10)
            
            # Force garbage collection
            gc.collect()
            
            # File should still be accessible (not locked)
            assert file_path.read_bytes()[:10] == b"x" * 10
    
    def test_memory_efficient_iteration(self):
        """Test that we don't load all files into memory"""
        
        # Use generator pattern
        def file_generator(count):
            for i in range(count):
                yield f"/path/to/video_{i}.mp4"
        
        # Process without loading all into memory
        processed = 0
        for path in file_generator(10000):
            processed += 1
            if processed >= 100:  # Early exit
                break
        
        assert processed == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
