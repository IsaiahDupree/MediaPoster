#!/usr/bin/env python3
"""
MediaPoster Health Check Script
================================
Comprehensive health check for:
1. Database tables existence
2. Service connectivity
3. Safari automation status
4. Feature health checks

Run: python scripts/health_check.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Configure minimal logging for health check
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")


class HealthCheck:
    """MediaPoster Health Check"""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        print("\n" + "="*60)
        print("🏥 MEDIAPOSTER HEALTH CHECK")
        print("="*60 + "\n")
        
        # 1. Database checks
        await self.check_database_tables()
        
        # 2. Service imports
        await self.check_service_imports()
        
        # 3. Safari automation files
        await self.check_safari_automations()
        
        # 4. Sora automation status
        await self.check_sora_status()
        
        # 5. Event bus
        await self.check_event_bus()
        
        # Summary
        self.print_summary()
        
        return self.results
    
    async def check_database_tables(self):
        """Check if required database tables exist"""
        print("📊 CHECKING DATABASE TABLES...")
        
        # Tables that services are trying to query (from error logs)
        service_expected_tables = {
            "scheduled_posts": "post_scheduler.py expects this",
            "weekly_plan_slots": "slot_executor.py expects this", 
            "original_videos": "video_ready_pipeline.py expects this",
            "analyzed_videos": "video_ready_pipeline.py expects this",
        }
        
        # Tables that actually exist and are similar
        actual_tables = [
            "safari_videos",
            "sora_video_pipeline",
            "posted_tweets",
            "posted_visual_content",
            "scheduled_tweets",
            "scheduled_visual_content",
            "sora_daily_plans",
            "platform_accounts",
        ]
        
        try:
            import psycopg2
            from config import settings
            
            # Parse database URL for psycopg2
            db_url = settings.database_url
            # Connect directly with psycopg2
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Get existing tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            print(f"   📋 Total tables in DB: {len(existing_tables)}")
            
            # Check service-expected tables
            print("\n   🔍 SERVICE-EXPECTED TABLES:")
            missing_critical = []
            for table, service in service_expected_tables.items():
                exists = table in existing_tables
                print(f"      {'✅' if exists else '❌'} {table} ({service})")
                if not exists:
                    missing_critical.append(table)
                    self.errors.append(f"Missing table: {table} - {service}")
            
            # Check actual related tables
            print("\n   📋 EXISTING RELATED TABLES:")
            for table in actual_tables:
                exists = table in existing_tables
                print(f"      {'✅' if exists else '❌'} {table}")
            
            self.results["database"] = {
                "status": "ok" if not missing_critical else "error",
                "total_tables": len(existing_tables),
                "missing_critical": missing_critical,
                "service_expected": list(service_expected_tables.keys()),
                "actual_related": [t for t in actual_tables if t in existing_tables]
            }
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Database error: {e}")
            self.errors.append(f"Database connection failed: {e}")
            self.results["database"] = {"status": "error", "error": str(e)}
    
    async def check_service_imports(self):
        """Check if core services can be imported"""
        print("\n📦 CHECKING SERVICE IMPORTS...")
        
        services = [
            ("services.video_ready_pipeline", "VideoReadyPipeline"),
            ("services.blotato_service", "BlotatoService"),
            ("services.event_bus", "EventBus"),
            ("services.post_scheduler", "PostScheduler"),
            ("services.master_orchestrator", "MasterOrchestrator"),
            ("services.content_analyzer", "ContentAnalyzer"),
            ("services.safari_event_listener", "SafariEventListener"),
            ("workers.slot_executor", "SlotExecutor"),
            ("services.bandit_allocator", "BanditAllocator"),
        ]
        
        import_results = {}
        for module_path, class_name in services:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name, None)
                if cls:
                    import_results[class_name] = "✅"
                else:
                    import_results[class_name] = "⚠️ class not found"
                    self.warnings.append(f"{class_name} not found in {module_path}")
            except Exception as e:
                import_results[class_name] = f"❌ {str(e)[:50]}"
                self.errors.append(f"Import failed: {module_path}.{class_name}: {e}")
        
        for name, status in import_results.items():
            print(f"   {status} {name}")
        
        self.results["services"] = import_results
    
    async def check_safari_automations(self):
        """List all Safari automation files"""
        print("\n🦁 SAFARI AUTOMATION FILES...")
        
        automation_dir = Path(__file__).parent.parent / "automation"
        safari_files = list(automation_dir.glob("safari*.py"))
        safari_files += list(automation_dir.glob("**/safari*.py"))
        
        # Also check services
        services_dir = Path(__file__).parent.parent / "services"
        safari_files += list(services_dir.glob("safari*.py"))
        
        safari_automations = []
        for f in sorted(set(safari_files)):
            rel_path = f.relative_to(Path(__file__).parent.parent)
            safari_automations.append(str(rel_path))
            print(f"   📄 {rel_path}")
        
        print(f"\n   Total: {len(safari_automations)} Safari automation files")
        
        self.results["safari_automations"] = safari_automations
    
    async def check_sora_status(self):
        """Check Sora automation status"""
        print("\n🎬 SORA AUTOMATION STATUS...")
        
        sora_files = [
            "automation/sora_full_automation.py",
            "automation/sora/sora_controller.py",
            "automation/safari_sora_scraper.py",
            "services/workers/sora_worker.py",
            "api/endpoints/sora_automation.py",
        ]
        
        backend_dir = Path(__file__).parent.parent
        sora_status = {}
        
        for rel_path in sora_files:
            full_path = backend_dir / rel_path
            exists = full_path.exists()
            sora_status[rel_path] = "✅" if exists else "❌"
            print(f"   {'✅' if exists else '❌'} {rel_path}")
        
        # Check for generated videos
        sora_videos_dir = backend_dir / "data" / "sora_videos"
        if sora_videos_dir.exists():
            videos = list(sora_videos_dir.glob("*.mp4"))
            print(f"\n   📹 {len(videos)} Sora videos in data/sora_videos/")
        
        self.results["sora"] = sora_status
    
    async def check_event_bus(self):
        """Check EventBus health"""
        print("\n📡 EVENT BUS STATUS...")
        
        try:
            from services.event_bus import EventBus, Topics
            bus = EventBus.get_instance()
            
            # List available topics
            topics = [t for t in dir(Topics) if not t.startswith("_")]
            print(f"   ✅ EventBus initialized")
            print(f"   📋 {len(topics)} topics available")
            
            # Check key topics
            key_topics = ["CONTENT_INGESTED", "CONTENT_ANALYSIS_COMPLETED", 
                         "PUBLISH_REQUESTED", "VIDEO_READY"]
            for topic in key_topics:
                has_topic = hasattr(Topics, topic)
                print(f"      {'✅' if has_topic else '❌'} {topic}")
            
            self.results["event_bus"] = {"status": "ok", "topic_count": len(topics)}
            
        except Exception as e:
            print(f"   ❌ EventBus error: {e}")
            self.errors.append(f"EventBus failed: {e}")
            self.results["event_bus"] = {"status": "error", "error": str(e)}
    
    def print_summary(self):
        """Print health check summary"""
        print("\n" + "="*60)
        print("📋 HEALTH CHECK SUMMARY")
        print("="*60)
        
        if not self.errors and not self.warnings:
            print("\n✅ ALL CHECKS PASSED!")
        else:
            if self.errors:
                print(f"\n❌ ERRORS ({len(self.errors)}):")
                for err in self.errors:
                    print(f"   - {err}")
            
            if self.warnings:
                print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
                for warn in self.warnings:
                    print(f"   - {warn}")
        
        print("\n" + "="*60)
        print(f"Completed at: {datetime.now(timezone.utc).isoformat()}")
        print("="*60 + "\n")


async def main():
    """Run health check"""
    checker = HealthCheck()
    results = await checker.run_all_checks()
    
    # Return exit code based on errors
    return 1 if checker.errors else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
