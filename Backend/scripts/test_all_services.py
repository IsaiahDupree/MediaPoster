"""
Test All Services
================
Comprehensive test suite for all backend services.
"""
import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Tuple


API_URL = "http://localhost:5555"
TIMEOUT = 30.0


class ServiceTester:
    """Test all backend services"""
    
    def __init__(self):
        self.results: Dict[str, Tuple[bool, str]] = {}
    
    async def test_service(self, name: str, test_func) -> Tuple[bool, str]:
        """Run a service test"""
        print(f"\n{'='*80}")
        print(f"🧪 Testing: {name}")
        print(f"{'='*80}")
        try:
            success, message = await test_func()
            self.results[name] = (success, message)
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {message}")
            return success, message
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            self.results[name] = (False, error_msg)
            print(f"❌ FAIL: {error_msg}")
            return False, error_msg
    
    async def test_health(self) -> Tuple[bool, str]:
        """Test health endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/health")
                if res.status_code == 200:
                    return True, "Health check passed"
                return False, f"Health check failed: {res.status_code}"
            except Exception as e:
                return False, f"Health check error: {str(e)}"
    
    async def test_media_list(self) -> Tuple[bool, str]:
        """Test media list endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/media-db/list?limit=10")
                if res.status_code == 200:
                    data = res.json()
                    # API returns list directly, or object with "media" key
                    if isinstance(data, list):
                        count = len(data)
                    else:
                        count = len(data.get("media", []))
                    return True, f"Media list returned {count} items"
                return False, f"Media list failed: {res.status_code}"
            except Exception as e:
                return False, f"Media list error: {str(e)}"
    
    async def test_media_stats(self) -> Tuple[bool, str]:
        """Test media stats endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/media-db/stats")
                if res.status_code == 200:
                    data = res.json()
                    total = data.get("total_count", 0)
                    analyzed = data.get("analyzed_count", 0)
                    return True, f"Stats: {total} total, {analyzed} analyzed"
                return False, f"Stats failed: {res.status_code}"
            except Exception as e:
                return False, f"Stats error: {str(e)}"
    
    async def test_social_accounts(self) -> Tuple[bool, str]:
        """Test social accounts endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/social/accounts")
                if res.status_code == 200:
                    data = res.json()
                    count = len(data) if isinstance(data, list) else 0
                    return True, f"Social accounts: {count} accounts"
                return False, f"Social accounts failed: {res.status_code}"
            except Exception as e:
                return False, f"Social accounts error: {str(e)}"
    
    async def test_scheduled_posts(self) -> Tuple[bool, str]:
        """Test scheduled posts endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/schedule/list?limit=10")
                if res.status_code == 200:
                    data = res.json()
                    count = len(data.get("posts", []))
                    return True, f"Scheduled posts: {count} posts"
                return False, f"Scheduled posts failed: {res.status_code}"
            except Exception as e:
                return False, f"Scheduled posts error: {str(e)}"
    
    async def test_narrative_goals(self) -> Tuple[bool, str]:
        """Test narrative goals endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/narrative/goals")
                if res.status_code == 200:
                    data = res.json()
                    count = len(data) if isinstance(data, list) else 0
                    return True, f"Narrative goals: {count} goals"
                return False, f"Narrative goals failed: {res.status_code}"
            except Exception as e:
                return False, f"Narrative goals error: {str(e)}"
    
    async def test_experiments(self) -> Tuple[bool, str]:
        """Test experiments endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/experiments/list")
                if res.status_code == 200:
                    data = res.json()
                    count = len(data.get("experiments", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
                    return True, f"Experiments: {count} experiments"
                return False, f"Experiments failed: {res.status_code}"
            except Exception as e:
                return False, f"Experiments error: {str(e)}"
    
    async def test_validation(self) -> Tuple[bool, str]:
        """Test app validation endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/app-validation/health-check")
                if res.status_code == 200:
                    data = res.json()
                    status = data.get("status", "unknown")
                    return True, f"App validation: {status}"
                return False, f"App validation failed: {res.status_code}"
            except Exception as e:
                return False, f"App validation error: {str(e)}"
    
    async def test_analysis_status(self) -> Tuple[bool, str]:
        """Test analysis status endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/media-db/analysis-status")
                if res.status_code == 200:
                    data = res.json()
                    jobs = len(data.get("jobs", []))
                    return True, f"Analysis status: {jobs} active jobs"
                return False, f"Analysis status failed: {res.status_code}"
            except Exception as e:
                return False, f"Analysis status error: {str(e)}"
    
    async def test_backup(self) -> Tuple[bool, str]:
        """Test backup endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/backup/stats")
                if res.status_code == 200:
                    data = res.json()
                    count = data.get("total_backups", 0)
                    return True, f"Backup: {count} backups available"
                return False, f"Backup failed: {res.status_code}"
            except Exception as e:
                return False, f"Backup error: {str(e)}"
    
    async def test_ingestion_status(self) -> Tuple[bool, str]:
        """Test ingestion status endpoint"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                res = await client.get(f"{API_URL}/api/ingestion/status")
                if res.status_code == 200:
                    data = res.json()
                    active = data.get("active", False)
                    return True, f"Ingestion: {'active' if active else 'inactive'}"
                return False, f"Ingestion status failed: {res.status_code}"
            except Exception as e:
                return False, f"Ingestion status error: {str(e)}"
    
    async def run_all_tests(self):
        """Run all service tests"""
        print("\n" + "="*80)
        print("🚀 COMPREHENSIVE SERVICE TEST SUITE")
        print("="*80)
        
        tests = [
            ("Health Check", self.test_health),
            ("Media List", self.test_media_list),
            ("Media Stats", self.test_media_stats),
            ("Social Accounts", self.test_social_accounts),
            ("Scheduled Posts", self.test_scheduled_posts),
            ("Narrative Goals", self.test_narrative_goals),
            ("Experiments", self.test_experiments),
            ("App Validation", self.test_validation),
            ("Analysis Status", self.test_analysis_status),
            ("Backup", self.test_backup),
            ("Ingestion Status", self.test_ingestion_status),
        ]
        
        for name, test_func in tests:
            await self.test_service(name, test_func)
        
        # Print summary
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for success, _ in self.results.values() if success)
        total = len(self.results)
        
        for name, (success, message) in self.results.items():
            status = "✅" if success else "❌"
            print(f"{status} {name}: {message}")
        
        print(f"\n{'='*80}")
        print(f"Results: {passed}/{total} tests passed")
        print(f"{'='*80}\n")
        
        return passed == total


async def main():
    """Main test runner"""
    tester = ServiceTester()
    success = await tester.run_all_tests()
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

