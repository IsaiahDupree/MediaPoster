#!/usr/bin/env python3
"""
Backend Performance Test Suite
Tests API response times, throughput, and identifies bottlenecks.

Usage:
    python tests/performance_test.py [--url URL] [--iterations N] [--concurrent N]
"""

import asyncio
import aiohttp
import time
import statistics
import argparse
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import requests

# Default configuration
DEFAULT_BASE_URL = "http://localhost:5555"
DEFAULT_ITERATIONS = 10
DEFAULT_CONCURRENT = 5


@dataclass
class EndpointResult:
    """Result of testing a single endpoint"""
    endpoint: str
    method: str
    times: List[float]
    errors: int
    status_codes: Dict[int, int]
    
    @property
    def avg_time(self) -> float:
        return statistics.mean(self.times) if self.times else 0
    
    @property
    def min_time(self) -> float:
        return min(self.times) if self.times else 0
    
    @property
    def max_time(self) -> float:
        return max(self.times) if self.times else 0
    
    @property
    def p95_time(self) -> float:
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    @property
    def success_rate(self) -> float:
        total = sum(self.status_codes.values())
        if total == 0:
            return 0
        success = sum(count for code, count in self.status_codes.items() if 200 <= code < 400)
        return (success / total) * 100


# Endpoints to test
ENDPOINTS = [
    # Health & Basic
    {"method": "GET", "path": "/", "name": "Root"},
    {"method": "GET", "path": "/health", "name": "Health Check"},
    
    # Media DB
    {"method": "GET", "path": "/api/media-db/list?limit=20", "name": "Media List (20)"},
    {"method": "GET", "path": "/api/media-db/list?limit=100", "name": "Media List (100)"},
    {"method": "GET", "path": "/api/media-db/stats", "name": "Media Stats"},
    
    # Content Growth
    {"method": "GET", "path": "/api/content-growth/summary", "name": "Growth Summary"},
    {"method": "GET", "path": "/api/content-growth/summary?days=7", "name": "Growth Summary (7d)"},
    
    # Metrics Scheduler
    {"method": "GET", "path": "/api/metrics-scheduler/status", "name": "Scheduler Status"},
    {"method": "GET", "path": "/api/metrics-scheduler/configs", "name": "Scheduler Configs"},
    {"method": "GET", "path": "/api/metrics-scheduler/line-graph-aggregate?metric=views&days=30", "name": "Line Graph Data"},
    
    # Approval Queue
    {"method": "GET", "path": "/api/approval-queue/list", "name": "Approval Queue"},
    {"method": "GET", "path": "/api/approval-queue/stats", "name": "Queue Stats"},
    
    # Image Analysis
    {"method": "GET", "path": "/api/image-analysis/fields", "name": "Analysis Fields"},
    
    # Posted Media
    {"method": "GET", "path": "/api/posted-media/list", "name": "Posted Media"},
    {"method": "GET", "path": "/api/posted-media/platforms", "name": "Platform Breakdown"},
    
    # Social Accounts
    {"method": "GET", "path": "/api/social-accounts/accounts", "name": "Social Accounts"},
]


def test_endpoint_sync(base_url: str, endpoint: dict) -> tuple:
    """Test a single endpoint synchronously"""
    url = f"{base_url}{endpoint['path']}"
    method = endpoint['method']
    
    start = time.perf_counter()
    try:
        if method == 'GET':
            response = requests.get(url, timeout=30)
        elif method == 'POST':
            response = requests.post(url, json=endpoint.get('body', {}), timeout=30)
        else:
            response = requests.request(method, url, timeout=30)
        
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        return elapsed, response.status_code, None
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, 0, str(e)


async def test_endpoint_async(session: aiohttp.ClientSession, base_url: str, endpoint: dict) -> tuple:
    """Test a single endpoint asynchronously"""
    url = f"{base_url}{endpoint['path']}"
    method = endpoint['method']
    
    start = time.perf_counter()
    try:
        async with session.request(method, url, json=endpoint.get('body')) as response:
            await response.read()
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed, response.status, None
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, 0, str(e)


def run_sequential_tests(base_url: str, iterations: int) -> Dict[str, EndpointResult]:
    """Run tests sequentially"""
    results = {}
    
    print(f"\n🔄 Running sequential tests ({iterations} iterations per endpoint)...")
    print("-" * 60)
    
    for endpoint in ENDPOINTS:
        name = endpoint['name']
        times = []
        status_codes = {}
        errors = 0
        
        for i in range(iterations):
            elapsed, status, error = test_endpoint_sync(base_url, endpoint)
            
            if error:
                errors += 1
            else:
                times.append(elapsed)
                status_codes[status] = status_codes.get(status, 0) + 1
        
        result = EndpointResult(
            endpoint=endpoint['path'],
            method=endpoint['method'],
            times=times,
            errors=errors,
            status_codes=status_codes
        )
        results[name] = result
        
        # Print progress
        status = "✅" if result.success_rate == 100 else "⚠️" if result.success_rate > 0 else "❌"
        print(f"  {status} {name}: {result.avg_time:.1f}ms avg ({result.min_time:.1f}-{result.max_time:.1f}ms)")
    
    return results


async def run_concurrent_tests(base_url: str, iterations: int, concurrent: int) -> Dict[str, EndpointResult]:
    """Run tests concurrently"""
    results = {}
    
    print(f"\n⚡ Running concurrent tests ({iterations} iterations, {concurrent} concurrent)...")
    print("-" * 60)
    
    connector = aiohttp.TCPConnector(limit=concurrent)
    async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30)) as session:
        for endpoint in ENDPOINTS:
            name = endpoint['name']
            times = []
            status_codes = {}
            errors = 0
            
            # Create tasks for concurrent execution
            tasks = [test_endpoint_async(session, base_url, endpoint) for _ in range(iterations)]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in task_results:
                if isinstance(result, Exception):
                    errors += 1
                else:
                    elapsed, status, error = result
                    if error:
                        errors += 1
                    else:
                        times.append(elapsed)
                        status_codes[status] = status_codes.get(status, 0) + 1
            
            result = EndpointResult(
                endpoint=endpoint['path'],
                method=endpoint['method'],
                times=times,
                errors=errors,
                status_codes=status_codes
            )
            results[name] = result
            
            status = "✅" if result.success_rate == 100 else "⚠️" if result.success_rate > 0 else "❌"
            print(f"  {status} {name}: {result.avg_time:.1f}ms avg, p95={result.p95_time:.1f}ms")
    
    return results


def run_load_test(base_url: str, duration_seconds: int = 10) -> Dict:
    """Run a load test for specified duration"""
    print(f"\n🔥 Running load test ({duration_seconds}s)...")
    print("-" * 60)
    
    # Pick a few key endpoints
    test_endpoints = [e for e in ENDPOINTS if e['name'] in ['Health Check', 'Media Stats', 'Queue Stats']]
    
    results = {
        'requests': 0,
        'errors': 0,
        'times': [],
    }
    
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    while time.time() < end_time:
        for endpoint in test_endpoints:
            elapsed, status, error = test_endpoint_sync(base_url, endpoint)
            results['requests'] += 1
            results['times'].append(elapsed)
            if error or status >= 500:
                results['errors'] += 1
    
    actual_duration = time.time() - start_time
    results['duration'] = actual_duration
    results['rps'] = results['requests'] / actual_duration
    results['avg_time'] = statistics.mean(results['times']) if results['times'] else 0
    results['error_rate'] = (results['errors'] / results['requests'] * 100) if results['requests'] > 0 else 0
    
    print(f"  Total Requests: {results['requests']}")
    print(f"  Requests/Second: {results['rps']:.1f}")
    print(f"  Avg Response Time: {results['avg_time']:.1f}ms")
    print(f"  Error Rate: {results['error_rate']:.1f}%")
    
    return results


def print_summary(sequential_results: Dict, concurrent_results: Dict):
    """Print a summary of all test results"""
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    # Find slow endpoints
    slow_endpoints = []
    for name, result in sequential_results.items():
        if result.avg_time > 500:  # > 500ms is slow
            slow_endpoints.append((name, result.avg_time))
    
    if slow_endpoints:
        print("\n⚠️ Slow Endpoints (>500ms):")
        for name, time in sorted(slow_endpoints, key=lambda x: -x[1]):
            print(f"   - {name}: {time:.0f}ms")
    
    # Find unreliable endpoints
    unreliable = []
    for name, result in sequential_results.items():
        if result.success_rate < 100:
            unreliable.append((name, result.success_rate))
    
    if unreliable:
        print("\n❌ Unreliable Endpoints (<100% success):")
        for name, rate in sorted(unreliable, key=lambda x: x[1]):
            print(f"   - {name}: {rate:.0f}% success")
    
    # Overall stats
    all_times = []
    for result in sequential_results.values():
        all_times.extend(result.times)
    
    if all_times:
        print(f"\n📈 Overall Statistics:")
        print(f"   Average: {statistics.mean(all_times):.1f}ms")
        print(f"   Median: {statistics.median(all_times):.1f}ms")
        print(f"   Min: {min(all_times):.1f}ms")
        print(f"   Max: {max(all_times):.1f}ms")
        
        # Calculate p95
        sorted_times = sorted(all_times)
        p95_idx = int(len(sorted_times) * 0.95)
        print(f"   P95: {sorted_times[p95_idx]:.1f}ms")


def check_server_available(base_url: str) -> bool:
    """Check if server is running"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code < 500
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description='Backend Performance Tests')
    parser.add_argument('--url', default=DEFAULT_BASE_URL, help='Base URL of the backend')
    parser.add_argument('--iterations', '-n', type=int, default=DEFAULT_ITERATIONS, help='Iterations per test')
    parser.add_argument('--concurrent', '-c', type=int, default=DEFAULT_CONCURRENT, help='Concurrent requests')
    parser.add_argument('--load-test', '-l', type=int, default=0, help='Load test duration in seconds')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick test (3 iterations)')
    args = parser.parse_args()
    
    base_url = args.url
    iterations = 3 if args.quick else args.iterations
    concurrent = args.concurrent
    
    print("=" * 60)
    print("🚀 MediaPoster Backend Performance Tests")
    print("=" * 60)
    print(f"Target: {base_url}")
    print(f"Iterations: {iterations}")
    print(f"Concurrency: {concurrent}")
    
    # Check if server is running
    if not check_server_available(base_url):
        print(f"\n❌ Server not available at {base_url}")
        print("   Start the backend with: uvicorn main:app --port 5555")
        return 1
    
    print("\n✅ Server is available")
    
    # Run sequential tests
    sequential_results = run_sequential_tests(base_url, iterations)
    
    # Run concurrent tests
    concurrent_results = asyncio.run(run_concurrent_tests(base_url, iterations, concurrent))
    
    # Run load test if requested
    if args.load_test > 0:
        run_load_test(base_url, args.load_test)
    
    # Print summary
    print_summary(sequential_results, concurrent_results)
    
    print("\n✅ Performance tests completed!")
    return 0


if __name__ == "__main__":
    exit(main())
