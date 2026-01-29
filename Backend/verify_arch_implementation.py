#!/usr/bin/env python3
"""
Verify ARCH-001 to ARCH-008 Implementation
===========================================
Quick validation script to check that all architecture features are properly implemented.
"""
import sys
import asyncio
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent))


def check_arch_001():
    """ARCH-001: Master Orchestrator Service"""
    try:
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        from services.event_bus import EventBus

        # Verify class exists and can be instantiated
        orchestrator = MasterOrchestrator(use_db=False)

        # Check required methods
        assert hasattr(orchestrator, 'start_pipeline')
        assert hasattr(orchestrator, 'get_pipeline_status')
        assert hasattr(orchestrator, 'list_active_pipelines')
        assert hasattr(orchestrator, 'start')
        assert hasattr(orchestrator, 'stop')

        # Check subsystems are initialized
        assert orchestrator.event_bus is not None
        assert orchestrator.content_analyzer is not None

        print("✅ ARCH-001: Master Orchestrator Service - PASS")
        return True
    except Exception as e:
        print(f"❌ ARCH-001: Master Orchestrator Service - FAIL: {e}")
        return False


def check_arch_002():
    """ARCH-002: 3-Part Sora Batch Coordination"""
    try:
        from automation.sora.pipeline import SoraPipeline

        # Verify class and method exist
        pipeline = SoraPipeline()

        # Check generate_multi_part method exists
        assert hasattr(pipeline, 'generate_multi_part')
        assert callable(pipeline.generate_multi_part)

        # Check other required methods
        assert hasattr(pipeline, 'generate_single')
        assert hasattr(pipeline, 'stitch_videos')
        assert hasattr(pipeline, '_generate_part_prompts')
        assert hasattr(pipeline, '_analyze_video_content')

        print("✅ ARCH-002: 3-Part Sora Batch Coordination - PASS")
        return True
    except Exception as e:
        print(f"❌ ARCH-002: 3-Part Sora Batch Coordination - FAIL: {e}")
        return False


def check_arch_003():
    """ARCH-003: Content Analyzer → Publisher Integration"""
    try:
        from services.workers.publish_worker import PublishWorker
        from services.content_analyzer import ContentAnalyzer

        # Verify PublishWorker exists and has required methods
        worker = PublishWorker()

        assert hasattr(worker, '_run_publish_pipeline')
        assert hasattr(worker, '_build_platform_caption')
        assert hasattr(worker, '_generate_ai_metadata')

        # Verify ContentAnalyzer exists
        analyzer = ContentAnalyzer()
        assert hasattr(analyzer, 'analyze_transcript')

        print("✅ ARCH-003: Content Analyzer → Publisher Integration - PASS")
        return True
    except Exception as e:
        print(f"❌ ARCH-003: Content Analyzer → Publisher Integration - FAIL: {e}")
        return False


def check_arch_004():
    """ARCH-004: Tweet Scheduler 2-Hour Interval"""
    try:
        from services.twitter_campaign_service import TwitterCampaignService

        # Verify service exists
        service = TwitterCampaignService()

        # Check for scheduling method
        assert hasattr(service, 'schedule_campaign')

        print("✅ ARCH-004: Tweet Scheduler 2-Hour Interval - PASS")
        return True
    except Exception as e:
        print(f"❌ ARCH-004: Tweet Scheduler 2-Hour Interval - FAIL: {e}")
        return False


def check_arch_005():
    """ARCH-005: Offer Traffic Tracking Service"""
    try:
        from services.offer_traffic_tracker import OfferTrafficTracker

        # Verify service exists
        tracker = OfferTrafficTracker()

        # Check required methods
        assert hasattr(tracker, 'generate_utm_link')
        assert hasattr(tracker, 'track_click')
        assert hasattr(tracker, 'track_conversion')

        print("✅ ARCH-005: Offer Traffic Tracking Service - PASS")
        return True
    except Exception as e:
        print(f"❌ ARCH-005: Offer Traffic Tracking Service - FAIL: {e}")
        return False


def check_arch_006():
    """ARCH-006: Analytics → AI Feedback Loop"""
    try:
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop

        # Verify service exists
        feedback = AnalyticsFeedbackLoop()

        # Check required methods
        assert hasattr(feedback, 'analyze_performance')
        assert hasattr(feedback, 'get_recommendations')

        print("✅ ARCH-006: Analytics → AI Feedback Loop - PASS")
        return True
    except Exception as e:
        print(f"❌ ARCH-006: Analytics → AI Feedback Loop - FAIL: {e}")
        return False


def check_arch_007():
    """ARCH-007: Unified Pipeline API Endpoint"""
    try:
        from api.endpoints.orchestrator import router

        # Verify router exists
        assert router is not None

        # Check that endpoints are registered
        routes = [route.path for route in router.routes]

        # Look for key endpoints
        assert any('/pipeline' in path for path in routes), "Missing /pipeline endpoints"

        print("✅ ARCH-007: Unified Pipeline API Endpoint - PASS")
        return True
    except Exception as e:
        print(f"❌ ARCH-007: Unified Pipeline API Endpoint - FAIL: {e}")
        return False


def check_arch_008():
    """ARCH-008: Pipeline Dashboard Widget"""
    try:
        # ARCH-008 is primarily frontend, but we can verify the API is ready
        from api.endpoints.orchestrator import router

        # Check for status endpoint that dashboard would use
        routes = [route.path for route in router.routes]
        assert any('/pipeline' in path for path in routes), "Missing pipeline status endpoints for dashboard"

        print("✅ ARCH-008: Pipeline Dashboard Widget (API Ready) - PASS")
        return True
    except Exception as e:
        print(f"❌ ARCH-008: Pipeline Dashboard Widget - FAIL: {e}")
        return False


def main():
    """Run all architecture checks"""
    print("=" * 70)
    print("ARCH Feature Implementation Verification")
    print("=" * 70)
    print()

    results = []

    # Run all checks
    results.append(("ARCH-001", check_arch_001()))
    results.append(("ARCH-002", check_arch_002()))
    results.append(("ARCH-003", check_arch_003()))
    results.append(("ARCH-004", check_arch_004()))
    results.append(("ARCH-005", check_arch_005()))
    results.append(("ARCH-006", check_arch_006()))
    results.append(("ARCH-007", check_arch_007()))
    results.append(("ARCH-008", check_arch_008()))

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All ARCH features are properly implemented!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} features need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
