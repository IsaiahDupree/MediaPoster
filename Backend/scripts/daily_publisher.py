#!/usr/bin/env python3
"""
Daily Publisher - Automated startup, health check, publish, and shutdown script.

Usage:
    python scripts/daily_publisher.py              # Run full cycle
    python scripts/daily_publisher.py --check-only # Just check what's scheduled
    python scripts/daily_publisher.py --keep-alive # Don't shutdown after publishing

This script:
1. Starts Supabase (if not running)
2. Starts Backend API
3. Runs health checks
4. Publishes all due scheduled posts
5. Shuts down to minimal state (optional)
"""

import subprocess
import time
import sys
import os
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "Backend"
BACKEND_PORT = 5555
SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
HEALTH_CHECK_TIMEOUT = 30
PUBLISH_WAIT_TIME = 120  # Wait for scheduler to process posts

class DailyPublisher:
    def __init__(self, check_only=False, keep_alive=False, verbose=True):
        self.check_only = check_only
        self.keep_alive = keep_alive
        self.verbose = verbose
        self.backend_started = False
        self.supabase_started = False
        
    def log(self, msg, level="INFO"):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "")
            print(f"[{timestamp}] {emoji} {msg}")
    
    def run_cmd(self, cmd, cwd=None, timeout=60):
        """Run a shell command and return output."""
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd or BACKEND_DIR,
                capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def check_supabase(self):
        """Check if Supabase is running."""
        success, output = self.run_cmd("supabase status 2>/dev/null | grep -q 'API URL'", cwd=PROJECT_ROOT)
        return success
    
    def start_supabase(self):
        """Start Supabase if not running."""
        if self.check_supabase():
            self.log("Supabase already running", "SUCCESS")
            return True
        
        self.log("Starting Supabase...")
        success, output = self.run_cmd("supabase start", cwd=PROJECT_ROOT, timeout=120)
        if success:
            self.log("Supabase started", "SUCCESS")
            self.supabase_started = True
            return True
        else:
            self.log(f"Failed to start Supabase: {output}", "ERROR")
            return False
    
    def check_backend(self):
        """Check if backend is healthy."""
        try:
            resp = requests.get(f"http://localhost:{BACKEND_PORT}/health", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def start_backend(self):
        """Start backend API."""
        if self.check_backend():
            self.log("Backend already running", "SUCCESS")
            return True
        
        self.log("Starting Backend API...")
        cmd = f"cd {BACKEND_DIR} && source venv/bin/activate && nohup uvicorn main:app --host 0.0.0.0 --port {BACKEND_PORT} > /tmp/daily_publisher_backend.log 2>&1 &"
        subprocess.Popen(cmd, shell=True, executable='/bin/zsh')
        
        # Wait for backend to be ready
        for i in range(HEALTH_CHECK_TIMEOUT):
            time.sleep(1)
            if self.check_backend():
                self.log(f"Backend started in {i+1}s", "SUCCESS")
                self.backend_started = True
                return True
        
        self.log("Backend failed to start within timeout", "ERROR")
        return False
    
    def get_scheduled_posts(self):
        """Get posts that are scheduled and due."""
        import psycopg2
        try:
            conn = psycopg2.connect(SUPABASE_DB_URL)
            cur = conn.cursor()
            
            # Get posts due now or in the past
            cur.execute("""
                SELECT id, title, platform, status, scheduled_at, account_id
                FROM scheduled_posts 
                WHERE status = 'scheduled' AND scheduled_at <= NOW()
                ORDER BY scheduled_at
            """)
            due_posts = cur.fetchall()
            
            # Get upcoming posts for today
            cur.execute("""
                SELECT id, title, platform, status, scheduled_at, account_id
                FROM scheduled_posts 
                WHERE status = 'scheduled' 
                  AND scheduled_at > NOW() 
                  AND scheduled_at < NOW() + INTERVAL '24 hours'
                ORDER BY scheduled_at
            """)
            upcoming_posts = cur.fetchall()
            
            conn.close()
            return due_posts, upcoming_posts
        except Exception as e:
            self.log(f"Database error: {e}", "ERROR")
            return [], []
    
    def trigger_publish(self):
        self.log("airtime_required: legacy due-post publisher is disabled; use Airtime", "ERROR")
        return False
    
    def wait_for_publishing(self, due_count):
        """Wait for posts to be published."""
        if due_count == 0:
            return
        
        self.log(f"Waiting for {due_count} posts to be published...")
        # Wait up to 2 minutes per post, max 10 minutes
        max_wait = min(due_count * 120, 600)
        
        import psycopg2
        start = time.time()
        while time.time() - start < max_wait:
            try:
                conn = psycopg2.connect(SUPABASE_DB_URL)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM scheduled_posts WHERE status = 'scheduled' AND scheduled_at <= NOW()")
                remaining = cur.fetchone()[0]
                conn.close()
                
                if remaining == 0:
                    self.log(f"All posts processed!", "SUCCESS")
                    return
                
                self.log(f"  {remaining} posts remaining...")
                time.sleep(15)
            except:
                time.sleep(15)
        
        self.log("Timeout waiting for posts to publish", "WARNING")
    
    def shutdown(self):
        """Shutdown services."""
        if self.keep_alive:
            self.log("Keeping services alive as requested")
            return
        
        self.log("Shutting down services...")
        
        # Kill backend
        self.run_cmd("pkill -f 'uvicorn main:app'")
        self.log("Backend stopped", "SUCCESS")
        
        # Stop supabase only if we started it
        if self.supabase_started:
            self.run_cmd("supabase stop", cwd=PROJECT_ROOT, timeout=60)
            self.log("Supabase stopped", "SUCCESS")
        else:
            self.log("Leaving Supabase running (was already running)")
    
    def run(self):
        """Main execution flow."""
        self.log("=" * 50)
        self.log(f"Daily Publisher - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.log("=" * 50)
        
        # Step 1: Start services
        if not self.start_supabase():
            return False
        
        if not self.start_backend():
            return False
        
        # Step 2: Health checks
        self.log("Running health checks...")
        if not self.check_backend():
            self.log("Backend health check failed", "ERROR")
            return False
        self.log("All health checks passed", "SUCCESS")
        
        # Step 3: Check scheduled posts
        due_posts, upcoming_posts = self.get_scheduled_posts()
        
        self.log(f"\n📅 Scheduled Posts Summary:")
        self.log(f"  Due now: {len(due_posts)}")
        self.log(f"  Upcoming (24h): {len(upcoming_posts)}")
        
        if due_posts:
            self.log("\n🚀 Posts due NOW:")
            for post in due_posts:
                self.log(f"  - [{post[2]}] {post[1][:40]}...")
        
        if upcoming_posts:
            self.log("\n⏰ Upcoming posts:")
            for post in upcoming_posts[:5]:
                self.log(f"  - [{post[2]}] {post[4]} - {post[1][:30]}...")
        
        if self.check_only:
            self.log("\n--check-only mode, skipping publish")
            return True
        
        # Step 4: Publish due posts
        if due_posts:
            self.log(f"\n📤 Publishing {len(due_posts)} due posts...")
            self.trigger_publish()
            self.wait_for_publishing(len(due_posts))
        else:
            self.log("\nNo posts due right now")
        
        # Step 5: Shutdown (unless keep-alive)
        self.shutdown()
        
        self.log("\n" + "=" * 50)
        self.log("Daily Publisher complete!", "SUCCESS")
        return True


def main():
    print("airtime_required: legacy publisher startup and delivery are disabled; use Airtime")
    return 2


if __name__ == "__main__":
    raise SystemExit(main() or 0)
