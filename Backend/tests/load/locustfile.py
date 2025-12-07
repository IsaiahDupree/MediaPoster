"""
Load Testing with Locust
Run with: locust -f tests/load/locustfile.py --host=http://localhost:5555
"""
from locust import HttpUser, task, between


class MediaPosterUser(HttpUser):
    """Simulates a typical user browsing MediaPoster"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    @task(10)
    def view_dashboard(self):
        """Most common action - view dashboard/overview"""
        self.client.get("/api/social-analytics/overview")
    
    @task(8)
    def view_analytics(self):
        """View analytics data"""
        self.client.get("/api/social-analytics/accounts")
        self.client.get("/api/social-analytics/trends?days=7")
    
    @task(6)
    def browse_content(self):
        """Browse content library"""
        self.client.get("/api/social-analytics/content?limit=20")
    
    @task(5)
    def browse_videos(self):
        """Browse video library"""
        self.client.get("/api/videos?limit=20")
    
    @task(4)
    def view_scheduled(self):
        """View scheduled posts"""
        self.client.get("/api/publishing/scheduled")
    
    @task(3)
    def view_goals(self):
        """Check goals"""
        self.client.get("/api/goals")
    
    @task(2)
    def get_recommendations(self):
        """Get recommendations"""
        self.client.get("/api/recommendations")
    
    @task(1)
    def view_api_docs(self):
        """View API documentation"""
        self.client.get("/docs")


class PowerUser(HttpUser):
    """Simulates a power user making more API calls"""
    
    wait_time = between(0.5, 1.5)
    
    @task(5)
    def rapid_analytics_check(self):
        """Frequently check analytics"""
        self.client.get("/api/social-analytics/overview")
        self.client.get("/api/social-analytics/content?limit=50")
    
    @task(3)
    def search_content(self):
        """Search for content"""
        self.client.get("/api/videos?search=test")
    
    @task(2)
    def pagination_test(self):
        """Test pagination"""
        for offset in [0, 20, 40]:
            self.client.get(f"/api/videos?limit=20&offset={offset}")


class APIStressUser(HttpUser):
    """Simulates API stress testing"""
    
    wait_time = between(0.1, 0.5)
    
    @task
    def stress_overview(self):
        """Stress test main endpoint"""
        self.client.get("/api/social-analytics/overview")


# Quick test script (run without Locust)
if __name__ == "__main__":
    import requests
    import time
    import statistics
    
    BASE_URL = "http://localhost:5555"
    
    endpoints = [
        "/api/social-analytics/overview",
        "/api/social-analytics/accounts",
        "/api/videos",
        "/api/publishing/scheduled",
        "/api/goals",
    ]
    
    print("Quick Load Test")
    print("=" * 50)
    
    for endpoint in endpoints:
        times = []
        errors = 0
        
        for _ in range(10):
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}{endpoint}")
                elapsed = time.time() - start
                times.append(elapsed)
                
                if response.status_code >= 500:
                    errors += 1
            except Exception as e:
                errors += 1
        
        if times:
            avg = statistics.mean(times) * 1000
            p95 = statistics.quantiles(times, n=20)[18] * 1000 if len(times) >= 2 else avg
            print(f"{endpoint}")
            print(f"  Avg: {avg:.1f}ms | P95: {p95:.1f}ms | Errors: {errors}")
        else:
            print(f"{endpoint} - All requests failed")
    
    print("\nDone!")
