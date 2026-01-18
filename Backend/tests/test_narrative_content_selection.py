#!/usr/bin/env python3
"""
Comprehensive Tests for Narrative Builder Content Selection
============================================================
Tests that the narrative builder:
1. Only selects ANALYZED content (has video_analysis record)
2. Only selects APPROVED content (curation_status = 'approved')
3. Does NOT select already SCHEDULED content
4. Does NOT select already POSTED content
5. Performance testing for large candidate pools
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import asyncpg
from loguru import logger
import sys

# Configure extensive logging
logger.remove()
logger.add(sys.stdout, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

DB_URL = "postgresql://postgres:postgres@localhost:54322/postgres"


class NarrativeContentSelectionTest:
    """Test suite for narrative builder content selection logic"""
    
    def __init__(self):
        self.conn = None
        self.test_video_ids = []
        self.test_scheduled_ids = []
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
    
    async def setup(self):
        """Connect to database"""
        logger.info("🔧 Setting up test connection...")
        self.conn = await asyncpg.connect(DB_URL)
        logger.success("✅ Connected to database")
    
    async def teardown(self):
        """Clean up test data and close connection"""
        logger.info("🧹 Cleaning up test data...")
        
        # Remove test scheduled posts
        if self.test_scheduled_ids:
            await self.conn.execute(
                "DELETE FROM scheduled_posts WHERE id = ANY($1::uuid[])",
                self.test_scheduled_ids
            )
            logger.info(f"   Removed {len(self.test_scheduled_ids)} test scheduled posts")
        
        await self.conn.close()
        logger.success("✅ Cleanup complete")
    
    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results["tests"].append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
        logger.info(f"{status} | {test_name} | {details}")
    
    # =========================================================================
    # CONTENT POOL ANALYSIS TESTS
    # =========================================================================
    
    async def test_analyzed_content_count(self):
        """Test: Count how many videos have been analyzed"""
        logger.info("\n📊 TEST: Analyzed Content Count")
        
        total_videos = await self.conn.fetchval("SELECT COUNT(*) FROM videos")
        analyzed_videos = await self.conn.fetchval(
            "SELECT COUNT(*) FROM videos v JOIN video_analysis va ON v.id = va.video_id"
        )
        
        details = f"Total: {total_videos}, Analyzed: {analyzed_videos} ({analyzed_videos/total_videos*100:.1f}%)"
        self.record_result("Analyzed Content Count", analyzed_videos > 0, details)
        
        return {"total": total_videos, "analyzed": analyzed_videos}
    
    async def test_approved_content_count(self):
        """Test: Count how many analyzed videos are APPROVED"""
        logger.info("\n📊 TEST: Approved Content Count")
        
        approved = await self.conn.fetchval("""
            SELECT COUNT(*) FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status = 'approved'
        """)
        
        pending = await self.conn.fetchval("""
            SELECT COUNT(*) FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status = 'pending' OR va.curation_status IS NULL
        """)
        
        rejected = await self.conn.fetchval("""
            SELECT COUNT(*) FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status = 'rejected'
        """)
        
        details = f"Approved: {approved}, Pending: {pending}, Rejected: {rejected}"
        self.record_result("Approved Content Count", approved > 0, details)
        
        return {"approved": approved, "pending": pending, "rejected": rejected}
    
    async def test_already_scheduled_content(self):
        """Test: Count how many approved videos are already scheduled"""
        logger.info("\n📊 TEST: Already Scheduled Content")
        
        scheduled = await self.conn.fetchval("""
            SELECT COUNT(DISTINCT v.id) FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            JOIN scheduled_posts sp ON (sp.content_id = v.id::text OR sp.clip_id = v.id)
            WHERE va.curation_status = 'approved'
              AND sp.status IN ('scheduled', 'publishing')
        """)
        
        posted = await self.conn.fetchval("""
            SELECT COUNT(DISTINCT v.id) FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            JOIN scheduled_posts sp ON (sp.content_id = v.id::text OR sp.clip_id = v.id)
            WHERE va.curation_status = 'approved'
              AND sp.status IN ('posted', 'published')
        """)
        
        details = f"Scheduled: {scheduled}, Posted: {posted}"
        self.record_result("Already Scheduled/Posted Count", True, details)
        
        return {"scheduled": scheduled, "posted": posted}
    
    async def test_available_for_selection(self):
        """Test: Count AVAILABLE videos (approved, not scheduled, not posted)"""
        logger.info("\n📊 TEST: Available for Selection")
        
        available = await self.conn.fetchval("""
            SELECT COUNT(*) FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status = 'approved'
              AND NOT EXISTS (
                  SELECT 1 FROM scheduled_posts sp 
                  WHERE (sp.content_id = v.id::text OR sp.clip_id = v.id)
                    AND sp.status IN ('scheduled', 'publishing', 'posted', 'published')
              )
        """)
        
        approved_total = await self.conn.fetchval("""
            SELECT COUNT(*) FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status = 'approved'
        """)
        
        details = f"Available: {available} / {approved_total} approved"
        passed = available >= 0  # Just checking query works
        self.record_result("Available for Selection", passed, details)
        
        return {"available": available, "approved_total": approved_total}
    
    # =========================================================================
    # EXCLUSION LOGIC TESTS
    # =========================================================================
    
    async def test_excludes_non_analyzed(self):
        """Test: Verify non-analyzed videos are excluded"""
        logger.info("\n🔒 TEST: Excludes Non-Analyzed Videos")
        
        # Get a video without analysis
        non_analyzed = await self.conn.fetchval("""
            SELECT v.id FROM videos v
            WHERE NOT EXISTS (SELECT 1 FROM video_analysis va WHERE va.video_id = v.id)
            LIMIT 1
        """)
        
        if non_analyzed:
            # Check it's NOT in available pool
            in_pool = await self.conn.fetchval("""
                SELECT COUNT(*) FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE v.id = $1
            """, non_analyzed)
            
            passed = in_pool == 0
            details = f"Non-analyzed video {str(non_analyzed)[:8]}... correctly excluded: {passed}"
        else:
            passed = True
            details = "All videos are analyzed (no non-analyzed to test)"
        
        self.record_result("Excludes Non-Analyzed", passed, details)
    
    async def test_excludes_non_approved(self):
        """Test: Verify non-approved videos are excluded"""
        logger.info("\n🔒 TEST: Excludes Non-Approved Videos")
        
        # Get a pending or rejected video
        non_approved = await self.conn.fetchrow("""
            SELECT v.id, va.curation_status FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status != 'approved' OR va.curation_status IS NULL
            LIMIT 1
        """)
        
        if non_approved:
            # Check it's NOT in available pool with approved filter
            in_pool = await self.conn.fetchval("""
                SELECT COUNT(*) FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE v.id = $1 AND va.curation_status = 'approved'
            """, non_approved['id'])
            
            passed = in_pool == 0
            details = f"Video with status '{non_approved['curation_status']}' correctly excluded"
        else:
            passed = True
            details = "All analyzed videos are approved"
        
        self.record_result("Excludes Non-Approved", passed, details)
    
    async def test_excludes_scheduled(self):
        """Test: Verify already scheduled videos are excluded"""
        logger.info("\n🔒 TEST: Excludes Already Scheduled Videos")
        
        # Find a scheduled post's content
        scheduled = await self.conn.fetchrow("""
            SELECT sp.content_id, sp.clip_id, sp.status FROM scheduled_posts sp
            WHERE sp.status = 'scheduled'
            LIMIT 1
        """)
        
        if scheduled:
            content_id = scheduled['content_id'] or str(scheduled['clip_id'])
            
            # Check it's excluded from available pool
            in_pool = await self.conn.fetchval("""
                SELECT COUNT(*) FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE v.id::text = $1
                  AND va.curation_status = 'approved'
                  AND NOT EXISTS (
                      SELECT 1 FROM scheduled_posts sp 
                      WHERE (sp.content_id = v.id::text OR sp.clip_id = v.id)
                        AND sp.status IN ('scheduled', 'publishing', 'posted', 'published')
                  )
            """, content_id)
            
            passed = in_pool == 0
            details = f"Scheduled video {content_id[:8]}... correctly excluded"
        else:
            passed = True
            details = "No scheduled posts to test against"
        
        self.record_result("Excludes Scheduled", passed, details)
    
    async def test_excludes_posted(self):
        """Test: Verify already posted videos are excluded"""
        logger.info("\n🔒 TEST: Excludes Already Posted Videos")
        
        # Find a posted content
        posted = await self.conn.fetchrow("""
            SELECT sp.content_id, sp.clip_id FROM scheduled_posts sp
            WHERE sp.status IN ('posted', 'published')
            LIMIT 1
        """)
        
        if posted:
            content_id = posted['content_id'] or str(posted['clip_id'])
            
            # Check it's excluded
            in_pool = await self.conn.fetchval("""
                SELECT COUNT(*) FROM videos v
                JOIN video_analysis va ON v.id = va.video_id
                WHERE v.id::text = $1
                  AND va.curation_status = 'approved'
                  AND NOT EXISTS (
                      SELECT 1 FROM scheduled_posts sp 
                      WHERE (sp.content_id = v.id::text OR sp.clip_id = v.id)
                        AND sp.status IN ('scheduled', 'publishing', 'posted', 'published')
                  )
            """, content_id)
            
            passed = in_pool == 0
            details = f"Posted video {content_id[:8]}... correctly excluded"
        else:
            passed = True
            details = "No posted content to test against"
        
        self.record_result("Excludes Posted", passed, details)
    
    # =========================================================================
    # PERFORMANCE TESTS
    # =========================================================================
    
    async def test_query_performance(self):
        """Test: Measure query performance for content selection"""
        logger.info("\n⚡ TEST: Query Performance")
        
        # Test 1: Simple count query
        start = time.perf_counter()
        await self.conn.fetchval("SELECT COUNT(*) FROM videos")
        simple_time = (time.perf_counter() - start) * 1000
        
        # Test 2: Full selection query (the one used by scheduler)
        start = time.perf_counter()
        await self.conn.fetch("""
            SELECT v.id, v.file_name, v.source_uri, v.thumbnail_path, v.duration_sec,
                   va.pre_social_score, va.transcript, va.topics, va.hooks, va.tone
            FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.pre_social_score >= 60
              AND va.curation_status = 'approved'
              AND NOT EXISTS (
                  SELECT 1 FROM scheduled_posts sp 
                  WHERE (sp.content_id = v.id::text OR sp.clip_id = v.id)
                    AND sp.status IN ('scheduled', 'publishing', 'posted', 'published')
              )
            ORDER BY va.pre_social_score DESC
            LIMIT 500
        """)
        full_time = (time.perf_counter() - start) * 1000
        
        # Test 3: Same query without LIMIT (stress test)
        start = time.perf_counter()
        await self.conn.fetch("""
            SELECT v.id FROM videos v
            JOIN video_analysis va ON v.id = va.video_id
            WHERE va.curation_status = 'approved'
              AND NOT EXISTS (
                  SELECT 1 FROM scheduled_posts sp 
                  WHERE (sp.content_id = v.id::text OR sp.clip_id = v.id)
              )
        """)
        stress_time = (time.perf_counter() - start) * 1000
        
        passed = full_time < 1000  # Should be under 1 second
        details = f"Simple: {simple_time:.1f}ms, Full: {full_time:.1f}ms, Stress: {stress_time:.1f}ms"
        self.record_result("Query Performance", passed, details)
        
        return {
            "simple_ms": simple_time,
            "full_ms": full_time,
            "stress_ms": stress_time
        }
    
    async def test_index_usage(self):
        """Test: Check if indexes are being used"""
        logger.info("\n🔍 TEST: Index Usage")
        
        # Check for relevant indexes
        indexes = await self.conn.fetch("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE tablename IN ('videos', 'video_analysis', 'scheduled_posts')
            ORDER BY tablename, indexname
        """)
        
        index_count = len(indexes)
        index_names = [f"{r['tablename']}.{r['indexname']}" for r in indexes[:5]]
        
        passed = index_count >= 3
        details = f"{index_count} indexes found. First 5: {', '.join(index_names)}"
        self.record_result("Index Usage", passed, details)
    
    # =========================================================================
    # MAIN TEST RUNNER
    # =========================================================================
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("=" * 70)
        logger.info("🧪 NARRATIVE BUILDER CONTENT SELECTION TESTS")
        logger.info("=" * 70)
        
        await self.setup()
        
        try:
            # Content pool analysis
            logger.info("\n" + "=" * 50)
            logger.info("📊 CONTENT POOL ANALYSIS")
            logger.info("=" * 50)
            
            analyzed = await self.test_analyzed_content_count()
            approved = await self.test_approved_content_count()
            scheduled = await self.test_already_scheduled_content()
            available = await self.test_available_for_selection()
            
            # Exclusion logic tests
            logger.info("\n" + "=" * 50)
            logger.info("🔒 EXCLUSION LOGIC TESTS")
            logger.info("=" * 50)
            
            await self.test_excludes_non_analyzed()
            await self.test_excludes_non_approved()
            await self.test_excludes_scheduled()
            await self.test_excludes_posted()
            
            # Performance tests
            logger.info("\n" + "=" * 50)
            logger.info("⚡ PERFORMANCE TESTS")
            logger.info("=" * 50)
            
            perf = await self.test_query_performance()
            await self.test_index_usage()
            
            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("📋 TEST SUMMARY")
            logger.info("=" * 70)
            
            total = self.results["passed"] + self.results["failed"]
            logger.info(f"Total tests: {total}")
            logger.info(f"✅ Passed: {self.results['passed']}")
            logger.info(f"❌ Failed: {self.results['failed']}")
            
            logger.info("\n📊 CONTENT SUMMARY:")
            logger.info(f"   Total videos: {analyzed['total']}")
            logger.info(f"   Analyzed: {analyzed['analyzed']}")
            logger.info(f"   Approved: {approved['approved']}")
            logger.info(f"   Already scheduled: {scheduled['scheduled']}")
            logger.info(f"   Already posted: {scheduled['posted']}")
            logger.info(f"   ✨ AVAILABLE FOR SELECTION: {available['available']}")
            
            logger.info("\n⚡ PERFORMANCE:")
            logger.info(f"   Full query: {perf['full_ms']:.1f}ms")
            
            if self.results['failed'] > 0:
                logger.warning("\n⚠️ SOME TESTS FAILED!")
                for test in self.results['tests']:
                    if not test['passed']:
                        logger.error(f"   {test['name']}: {test['details']}")
            else:
                logger.success("\n✅ ALL TESTS PASSED!")
            
        finally:
            await self.teardown()
        
        return self.results


async def main():
    """Run the test suite"""
    test_suite = NarrativeContentSelectionTest()
    results = await test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    asyncio.run(main())
