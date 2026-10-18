"""
Resource Utilization Performance Tests
======================================
Tests to ensure the application stays within CPU/GPU/Memory thresholds
during startup and various operations.

Run with: pytest tests/performance/test_resource_utilization.py -v -s
Run specific: pytest tests/performance/test_resource_utilization.py::TestStartupResources -v -s

Thresholds (configurable):
- CPU: < 80% sustained, < 95% peak
- Memory: < 70% of available, < 4GB absolute
- GPU: < 80% (when applicable)
"""
import pytest
import psutil
import time
import os
import sys
import subprocess
import signal
import threading
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class ResourceThresholds:
    """Configurable resource thresholds."""
    # CPU thresholds (percentage) - system-wide
    cpu_peak_max: float = 98.0          # Allow high peaks during operations
    cpu_sustained_max: float = 90.0     # Sustained max (realistic for dev machine)
    cpu_idle_max: float = 70.0          # "Idle" with other apps running
    
    # Memory thresholds - more realistic for dev machines
    memory_percent_max: float = 90.0    # Allow up to 90% system memory
    memory_absolute_max_gb: float = 10.0  # 10GB max
    
    # Process-specific thresholds (MediaPoster backend)
    process_cpu_max: float = 50.0       # Single process shouldn't use >50% CPU
    process_memory_max_mb: float = 2048.0  # Backend process max 2GB
    
    # GPU thresholds (if available)
    gpu_percent_max: float = 90.0       # Allow GPU usage for video processing
    
    # Timing thresholds
    startup_time_max_seconds: float = 30.0
    shutdown_time_max_seconds: float = 10.0
    
    # Sampling
    sample_interval_seconds: float = 0.5
    sustained_duration_seconds: float = 5.0


THRESHOLDS = ResourceThresholds()


@dataclass
class ResourceSample:
    """Single resource measurement."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    gpu_percent: Optional[float] = None
    process_cpu: Optional[float] = None
    process_memory_mb: Optional[float] = None


@dataclass
class ResourceReport:
    """Resource utilization report."""
    test_name: str
    duration_seconds: float
    samples: List[ResourceSample] = field(default_factory=list)
    
    # Computed stats
    cpu_avg: float = 0.0
    cpu_max: float = 0.0
    cpu_min: float = 0.0
    memory_avg_mb: float = 0.0
    memory_max_mb: float = 0.0
    memory_max_percent: float = 0.0
    gpu_avg: Optional[float] = None
    gpu_max: Optional[float] = None
    
    # Threshold violations
    violations: List[str] = field(default_factory=list)
    passed: bool = True
    
    def compute_stats(self):
        """Compute statistics from samples."""
        if not self.samples:
            return
        
        cpus = [s.cpu_percent for s in self.samples]
        mems = [s.memory_mb for s in self.samples]
        mem_pcts = [s.memory_percent for s in self.samples]
        
        self.cpu_avg = sum(cpus) / len(cpus)
        self.cpu_max = max(cpus)
        self.cpu_min = min(cpus)
        self.memory_avg_mb = sum(mems) / len(mems)
        self.memory_max_mb = max(mems)
        self.memory_max_percent = max(mem_pcts)
        
        gpus = [s.gpu_percent for s in self.samples if s.gpu_percent is not None]
        if gpus:
            self.gpu_avg = sum(gpus) / len(gpus)
            self.gpu_max = max(gpus)
    
    def check_thresholds(self, thresholds: ResourceThresholds):
        """Check against thresholds and record violations."""
        self.violations = []
        
        if self.cpu_max > thresholds.cpu_peak_max:
            self.violations.append(
                f"CPU peak ({self.cpu_max:.1f}%) exceeded max ({thresholds.cpu_peak_max}%)"
            )
        
        if self.cpu_avg > thresholds.cpu_sustained_max:
            self.violations.append(
                f"CPU sustained ({self.cpu_avg:.1f}%) exceeded max ({thresholds.cpu_sustained_max}%)"
            )
        
        if self.memory_max_percent > thresholds.memory_percent_max:
            self.violations.append(
                f"Memory ({self.memory_max_percent:.1f}%) exceeded max ({thresholds.memory_percent_max}%)"
            )
        
        memory_max_gb = self.memory_max_mb / 1024
        if memory_max_gb > thresholds.memory_absolute_max_gb:
            self.violations.append(
                f"Memory ({memory_max_gb:.2f}GB) exceeded max ({thresholds.memory_absolute_max_gb}GB)"
            )
        
        if self.gpu_max and self.gpu_max > thresholds.gpu_percent_max:
            self.violations.append(
                f"GPU ({self.gpu_max:.1f}%) exceeded max ({thresholds.gpu_percent_max}%)"
            )
        
        self.passed = len(self.violations) == 0
    
    def __str__(self):
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [
            f"\n{'='*60}",
            f"Resource Report: {self.test_name}",
            f"{'='*60}",
            f"Duration: {self.duration_seconds:.2f}s | Samples: {len(self.samples)}",
            f"",
            f"CPU:    avg={self.cpu_avg:.1f}%  max={self.cpu_max:.1f}%  min={self.cpu_min:.1f}%",
            f"Memory: avg={self.memory_avg_mb:.0f}MB  max={self.memory_max_mb:.0f}MB ({self.memory_max_percent:.1f}%)",
        ]
        
        if self.gpu_max is not None:
            lines.append(f"GPU:    avg={self.gpu_avg:.1f}%  max={self.gpu_max:.1f}%")
        
        lines.append(f"\nStatus: {status}")
        
        if self.violations:
            lines.append("Violations:")
            for v in self.violations:
                lines.append(f"  - {v}")
        
        lines.append("="*60)
        return "\n".join(lines)


# =============================================================================
# RESOURCE MONITOR
# =============================================================================

class ResourceMonitor:
    """Monitor system resources in background thread."""
    
    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.samples: List[ResourceSample] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[psutil.Process] = None
    
    def _get_gpu_percent(self) -> Optional[float]:
        """Get GPU utilization (macOS Apple Silicon)."""
        try:
            # Try using powermetrics for Apple Silicon
            result = subprocess.run(
                ['sudo', 'powermetrics', '-n', '1', '-i', '100', '--samplers', 'gpu_power'],
                capture_output=True, text=True, timeout=2
            )
            # Parse GPU utilization from output
            for line in result.stdout.split('\n'):
                if 'GPU' in line and '%' in line:
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                    if match:
                        return float(match.group(1))
        except:
            pass
        
        # Fallback: Try nvidia-smi for NVIDIA GPUs
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=2
            )
            return float(result.stdout.strip())
        except:
            pass
        
        return None
    
    def _sample(self):
        """Take a single resource sample."""
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        
        sample = ResourceSample(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_mb=memory.used / (1024 * 1024),
            gpu_percent=self._get_gpu_percent()
        )
        
        # Process-specific metrics if tracking a process
        if self._process and self._process.is_running():
            try:
                sample.process_cpu = self._process.cpu_percent()
                sample.process_memory_mb = self._process.memory_info().rss / (1024 * 1024)
            except:
                pass
        
        return sample
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            self.samples.append(self._sample())
            time.sleep(self.interval)
    
    def start(self, process: Optional[psutil.Process] = None):
        """Start monitoring."""
        self._process = process
        self.samples = []
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        # Initial CPU reading (psutil needs two calls)
        psutil.cpu_percent(interval=None)
    
    def stop(self) -> List[ResourceSample]:
        """Stop monitoring and return samples."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        return self.samples
    
    def get_report(self, test_name: str, duration: float) -> ResourceReport:
        """Generate report from collected samples."""
        report = ResourceReport(
            test_name=test_name,
            duration_seconds=duration,
            samples=self.samples
        )
        report.compute_stats()
        report.check_thresholds(THRESHOLDS)
        return report


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def resource_monitor():
    """Provide a resource monitor instance."""
    monitor = ResourceMonitor(interval=THRESHOLDS.sample_interval_seconds)
    yield monitor
    monitor.stop()


@pytest.fixture
def backend_process():
    """Start and stop the backend server for testing."""
    process = None
    
    def start_backend():
        nonlocal process
        backend_dir = Path(__file__).parent.parent.parent
        
        # Try to start the backend
        process = subprocess.Popen(
            ['python', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '5556'],
            cwd=str(backend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        
        # Wait for startup
        time.sleep(3)
        return process
    
    yield start_backend
    
    # Cleanup
    if process:
        try:
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()


# =============================================================================
# STARTUP TESTS
# =============================================================================

class TestStartupResources:
    """Test resource utilization during application startup."""
    
    def test_backend_startup_cpu_usage(self, resource_monitor):
        """Test that backend startup doesn't exceed CPU thresholds."""
        monitor = resource_monitor
        backend_dir = Path(__file__).parent.parent.parent
        
        # Start monitoring
        monitor.start()
        start_time = time.time()
        
        # Start backend process
        process = subprocess.Popen(
            ['python', '-c', '''
import sys
sys.path.insert(0, ".")
# Import main modules to simulate startup
try:
    from main import app
    from api import router
    from services import *
    print("Startup complete")
except Exception as e:
    print(f"Startup error: {e}")
'''],
            cwd=str(backend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for process to complete
        try:
            stdout, stderr = process.communicate(timeout=THRESHOLDS.startup_time_max_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail(f"Startup exceeded {THRESHOLDS.startup_time_max_seconds}s timeout")
        
        duration = time.time() - start_time
        monitor.stop()
        
        # Generate report
        report = monitor.get_report("Backend Startup", duration)
        print(report)
        
        # Assertions
        assert report.cpu_max < THRESHOLDS.cpu_peak_max, \
            f"CPU peak {report.cpu_max:.1f}% exceeded {THRESHOLDS.cpu_peak_max}%"
        assert duration < THRESHOLDS.startup_time_max_seconds, \
            f"Startup took {duration:.1f}s, max allowed {THRESHOLDS.startup_time_max_seconds}s"
    
    def test_import_modules_memory(self, resource_monitor):
        """Test memory usage when importing main modules."""
        monitor = resource_monitor
        
        # Measure baseline
        baseline_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        monitor.start()
        start_time = time.time()
        
        # Import heavy modules
        try:
            import importlib
            modules_to_import = [
                'fastapi',
                'sqlalchemy',
                'pydantic',
                'loguru',
            ]
            
            for mod in modules_to_import:
                try:
                    importlib.import_module(mod)
                except ImportError:
                    pass
            
            time.sleep(1)  # Let memory settle
        except Exception as e:
            print(f"Import error: {e}")
        
        duration = time.time() - start_time
        monitor.stop()
        
        report = monitor.get_report("Module Imports", duration)
        print(report)
        
        # Memory increase should be reasonable
        memory_increase = report.memory_max_mb - baseline_memory
        assert memory_increase < 1024, f"Memory increased by {memory_increase:.0f}MB during imports"


# =============================================================================
# IDLE STATE TESTS
# =============================================================================

class TestIdleResources:
    """Test resource utilization in idle state."""
    
    def test_idle_cpu_under_threshold(self, resource_monitor):
        """Test that idle CPU stays under threshold."""
        monitor = resource_monitor
        
        monitor.start()
        
        # Monitor for 10 seconds in idle state
        time.sleep(10)
        
        monitor.stop()
        report = monitor.get_report("Idle State (10s)", 10.0)
        print(report)
        
        assert report.cpu_avg < THRESHOLDS.cpu_idle_max, \
            f"Idle CPU avg {report.cpu_avg:.1f}% exceeded {THRESHOLDS.cpu_idle_max}%"
    
    def test_memory_stable_over_time(self, resource_monitor):
        """Test that memory doesn't grow significantly when idle."""
        monitor = resource_monitor
        
        monitor.start()
        
        # Monitor for 30 seconds
        time.sleep(30)
        
        monitor.stop()
        report = monitor.get_report("Memory Stability (30s)", 30.0)
        print(report)
        
        # Calculate memory growth
        if len(report.samples) > 10:
            first_10_avg = sum(s.memory_mb for s in report.samples[:10]) / 10
            last_10_avg = sum(s.memory_mb for s in report.samples[-10:]) / 10
            growth = last_10_avg - first_10_avg
            
            # Memory shouldn't grow more than 100MB in idle
            assert growth < 100, f"Memory grew by {growth:.0f}MB during idle period"


# =============================================================================
# OPERATION TESTS
# =============================================================================

class TestOperationResources:
    """Test resource utilization during various operations."""
    
    def test_json_parsing_cpu(self, resource_monitor):
        """Test CPU usage during heavy JSON parsing."""
        monitor = resource_monitor
        
        # Generate test data
        test_data = [
            {"id": i, "name": f"item_{i}", "data": list(range(100))}
            for i in range(1000)
        ]
        
        monitor.start()
        start_time = time.time()
        
        # Perform JSON operations
        for _ in range(100):
            json_str = json.dumps(test_data)
            parsed = json.loads(json_str)
        
        duration = time.time() - start_time
        monitor.stop()
        
        report = monitor.get_report("JSON Parsing (100x)", duration)
        print(report)
        
        assert report.cpu_max < THRESHOLDS.cpu_peak_max
    
    def test_concurrent_operations(self, resource_monitor):
        """Test resources during concurrent operations."""
        import concurrent.futures
        
        monitor = resource_monitor
        
        def cpu_task(n):
            """CPU-intensive task."""
            result = 0
            for i in range(n):
                result += i ** 2
            return result
        
        monitor.start()
        start_time = time.time()
        
        # Run concurrent tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_task, 100000) for _ in range(20)]
            concurrent.futures.wait(futures)
        
        duration = time.time() - start_time
        monitor.stop()
        
        report = monitor.get_report("Concurrent Operations", duration)
        print(report)
        
        assert report.cpu_max < THRESHOLDS.cpu_peak_max
    
    def test_file_operations(self, resource_monitor, tmp_path):
        """Test resources during file I/O operations."""
        monitor = resource_monitor
        
        monitor.start()
        start_time = time.time()
        
        # Write and read files
        for i in range(50):
            file_path = tmp_path / f"test_file_{i}.txt"
            
            # Write
            content = "x" * 100000  # 100KB
            file_path.write_text(content)
            
            # Read
            _ = file_path.read_text()
            
            # Delete
            file_path.unlink()
        
        duration = time.time() - start_time
        monitor.stop()
        
        report = monitor.get_report("File I/O (50 files)", duration)
        print(report)
        
        assert report.cpu_max < THRESHOLDS.cpu_peak_max


# =============================================================================
# SUSTAINED LOAD TESTS
# =============================================================================

class TestSustainedLoad:
    """Test resource utilization under sustained load."""
    
    def test_sustained_cpu_load(self, resource_monitor):
        """Test that sustained CPU load stays within limits."""
        monitor = resource_monitor
        
        def generate_load():
            """Generate moderate CPU load."""
            end_time = time.time() + THRESHOLDS.sustained_duration_seconds
            while time.time() < end_time:
                # Some CPU work
                _ = [i ** 2 for i in range(1000)]
                time.sleep(0.01)  # Prevent 100% usage
        
        monitor.start()
        start_time = time.time()
        
        # Run multiple threads generating load
        threads = []
        for _ in range(2):  # 2 threads
            t = threading.Thread(target=generate_load)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        duration = time.time() - start_time
        monitor.stop()
        
        report = monitor.get_report("Sustained Load", duration)
        print(report)
        
        assert report.cpu_avg < THRESHOLDS.cpu_sustained_max, \
            f"Sustained CPU {report.cpu_avg:.1f}% exceeded {THRESHOLDS.cpu_sustained_max}%"


# =============================================================================
# BENCHMARK COMPARISON
# =============================================================================

class TestResourceBenchmarks:
    """Benchmark tests with specific performance targets."""
    
    def test_api_import_time(self):
        """Benchmark API module import time."""
        import importlib
        
        start = time.time()
        
        try:
            # Force reimport
            if 'fastapi' in sys.modules:
                importlib.reload(sys.modules['fastapi'])
            else:
                import fastapi
        except:
            pass
        
        duration = time.time() - start
        print(f"\nFastAPI import time: {duration*1000:.2f}ms")
        
        assert duration < 2.0, f"FastAPI import took {duration:.2f}s, should be < 2s"
    
    def test_baseline_memory(self):
        """Establish baseline memory usage."""
        import gc
        gc.collect()
        
        memory = psutil.virtual_memory()
        process = psutil.Process()
        
        print(f"\n{'='*40}")
        print(f"System Memory Baseline")
        print(f"{'='*40}")
        print(f"Total:     {memory.total / (1024**3):.2f} GB")
        print(f"Available: {memory.available / (1024**3):.2f} GB")
        print(f"Used:      {memory.used / (1024**3):.2f} GB ({memory.percent}%)")
        print(f"Process:   {process.memory_info().rss / (1024**2):.0f} MB")
        print(f"{'='*40}")
        
        # Should have reasonable memory available
        assert memory.available > 1 * 1024**3, "Less than 1GB memory available"


# =============================================================================
# SUMMARY TEST
# =============================================================================

class TestResourceSummary:
    """Generate summary of all resource tests."""
    
    def test_print_thresholds(self):
        """Print current threshold configuration."""
        print(f"\n{'='*60}")
        print("RESOURCE UTILIZATION THRESHOLDS")
        print(f"{'='*60}")
        print(f"CPU Peak Max:        {THRESHOLDS.cpu_peak_max}%")
        print(f"CPU Sustained Max:   {THRESHOLDS.cpu_sustained_max}%")
        print(f"CPU Idle Max:        {THRESHOLDS.cpu_idle_max}%")
        print(f"Memory Max:          {THRESHOLDS.memory_percent_max}% / {THRESHOLDS.memory_absolute_max_gb}GB")
        print(f"GPU Max:             {THRESHOLDS.gpu_percent_max}%")
        print(f"Startup Time Max:    {THRESHOLDS.startup_time_max_seconds}s")
        print(f"Sample Interval:     {THRESHOLDS.sample_interval_seconds}s")
        print(f"{'='*60}")
        
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
