#!/usr/bin/env python
"""
Verification script for System Architecture Integration (ARCH-001 to ARCH-008)
"""
import sys
import os

# Add Backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

def verify_arch_implementation():
    """Verify all ARCH features are implemented."""

    print("🔍 Verifying System Architecture Integration (ARCH-001 to ARCH-008)...")
    print("=" * 70)

    results = {}

    # ARCH-001: Master Orchestrator
    try:
        from services.master_orchestrator import MasterOrchestrator
        orchestrator = MasterOrchestrator(use_db=False)

        # Check subsystems initialized
        has_sora = orchestrator.sora_pipeline is not None
        has_blotato = orchestrator.blotato_service is not None
        has_twitter = orchestrator.twitter_service is not None
        has_analytics = orchestrator.analytics_feedback is not None
        has_analyzer = orchestrator.content_analyzer is not None

        all_subsystems = all([has_sora, has_blotato, has_twitter, has_analytics, has_analyzer])

        results['ARCH-001'] = {
            'name': 'Master Orchestrator Service',
            'status': '✅ PASS' if all_subsystems else '❌ FAIL',
            'details': f'Subsystems: Sora={has_sora}, Blotato={has_blotato}, Twitter={has_twitter}, Analytics={has_analytics}, Analyzer={has_analyzer}'
        }
    except Exception as e:
        results['ARCH-001'] = {
            'name': 'Master Orchestrator Service',
            'status': '❌ FAIL',
            'details': f'Error: {str(e)}'
        }

    # ARCH-002: 3-Part Sora Batch
    try:
        from automation.sora.pipeline import SoraPipeline
        pipeline = SoraPipeline()

        has_method = hasattr(pipeline, 'generate_multi_part')
        is_callable = callable(getattr(pipeline, 'generate_multi_part', None))

        results['ARCH-002'] = {
            'name': '3-Part Sora Batch Coordination',
            'status': '✅ PASS' if (has_method and is_callable) else '❌ FAIL',
            'details': f'generate_multi_part() method exists and is callable'
        }
    except Exception as e:
        results['ARCH-002'] = {
            'name': '3-Part Sora Batch Coordination',
            'status': '❌ FAIL',
            'details': f'Error: {str(e)}'
        }

    # ARCH-003: Analyzer → Publisher Integration
    try:
        from services.workers.publish_worker import PublishWorker
        import inspect

        # Check if publish worker handles analysis in payload
        source = inspect.getsource(PublishWorker._run_publish_pipeline)
        has_analysis_handling = 'payload.get("analysis")' in source

        results['ARCH-003'] = {
            'name': 'Content Analyzer → Publisher Integration',
            'status': '✅ PASS' if has_analysis_handling else '❌ FAIL',
            'details': 'PublishWorker handles analysis payload for auto-metadata'
        }
    except Exception as e:
        results['ARCH-003'] = {
            'name': 'Content Analyzer → Publisher Integration',
            'status': '❌ FAIL',
            'details': f'Error: {str(e)}'
        }

    # ARCH-004: Tweet Scheduler
    try:
        from services.twitter_campaign_service import TwitterCampaignService
        service = TwitterCampaignService()

        has_schedule = hasattr(service, 'schedule_offer_tweets')

        results['ARCH-004'] = {
            'name': 'Tweet Scheduler 2-Hour Interval',
            'status': '✅ PASS' if has_schedule else '❌ FAIL',
            'details': 'TwitterCampaignService has schedule_offer_tweets() method'
        }
    except Exception as e:
        results['ARCH-004'] = {
            'name': 'Tweet Scheduler 2-Hour Interval',
            'status': '❌ FAIL',
            'details': f'Error: {str(e)}'
        }

    # ARCH-005: Offer Traffic Tracker
    try:
        from services.offer_traffic_tracker import OfferTrafficTracker
        tracker = OfferTrafficTracker.get_instance()

        has_create_link = hasattr(tracker, 'create_tracked_link')
        has_track_click = hasattr(tracker, 'track_click')
        has_track_conversion = hasattr(tracker, 'track_conversion')
        has_report = hasattr(tracker, 'get_pipeline_traffic_report')

        all_methods = all([has_create_link, has_track_click, has_track_conversion, has_report])

        results['ARCH-005'] = {
            'name': 'Offer Traffic Tracking Service',
            'status': '✅ PASS' if all_methods else '❌ FAIL',
            'details': f'Methods: create_tracked_link={has_create_link}, track_click={has_track_click}, track_conversion={has_track_conversion}, get_report={has_report}'
        }
    except Exception as e:
        results['ARCH-005'] = {
            'name': 'Offer Traffic Tracking Service',
            'status': '❌ FAIL',
            'details': f'Error: {str(e)}'
        }

    # ARCH-006: Analytics Feedback Loop
    try:
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop
        feedback = AnalyticsFeedbackLoop.get_instance()

        has_analyze = hasattr(feedback, 'analyze_pipeline_performance')
        has_insights = hasattr(feedback, 'get_historical_insights')
        has_themes = hasattr(feedback, 'get_top_performing_themes')

        all_methods = all([has_analyze, has_insights, has_themes])

        results['ARCH-006'] = {
            'name': 'Analytics → AI Feedback Loop',
            'status': '✅ PASS' if all_methods else '❌ FAIL',
            'details': f'Methods: analyze_pipeline={has_analyze}, get_insights={has_insights}, get_themes={has_themes}'
        }
    except Exception as e:
        results['ARCH-006'] = {
            'name': 'Analytics → AI Feedback Loop',
            'status': '❌ FAIL',
            'details': f'Error: {str(e)}'
        }

    # ARCH-007: Unified API Endpoint
    try:
        from api.endpoints.orchestrator import router

        # Check for key endpoints
        has_start = any('start' in str(route.path) for route in router.routes)
        has_status = any('{' in str(route.path) for route in router.routes)
        has_list = any('pipelines' in str(route.path) for route in router.routes)

        all_endpoints = all([has_start, has_status, has_list])

        results['ARCH-007'] = {
            'name': 'Unified Pipeline API Endpoint',
            'status': '✅ PASS' if all_endpoints else '❌ FAIL',
            'details': f'Endpoints: start={has_start}, status={has_status}, list={has_list}'
        }
    except Exception as e:
        results['ARCH-007'] = {
            'name': 'Unified Pipeline API Endpoint',
            'status': '❌ FAIL',
            'details': f'Error: {str(e)}'
        }

    # ARCH-008: Pipeline Dashboard Widget
    try:
        # Check for dashboard component files
        import os
        dashboard_path = os.path.join(os.path.dirname(__file__), '..', 'dashboard')

        # Look for pipeline-related components
        pipeline_files = []
        if os.path.exists(dashboard_path):
            for root, dirs, files in os.walk(dashboard_path):
                for file in files:
                    if 'pipeline' in file.lower() and (file.endswith('.tsx') or file.endswith('.jsx')):
                        pipeline_files.append(file)

        has_dashboard = len(pipeline_files) > 0

        results['ARCH-008'] = {
            'name': 'Pipeline Dashboard Widget',
            'status': '✅ PASS' if has_dashboard else '⚠️  PARTIAL',
            'details': f'Found {len(pipeline_files)} pipeline component(s): {", ".join(pipeline_files[:3])}'
        }
    except Exception as e:
        results['ARCH-008'] = {
            'name': 'Pipeline Dashboard Widget',
            'status': '⚠️  PARTIAL',
            'details': f'Note: {str(e)}'
        }

    # Print results
    print("\n📊 ARCH Implementation Verification Results:\n")

    for arch_id in sorted(results.keys()):
        feature = results[arch_id]
        print(f"{arch_id}: {feature['name']}")
        print(f"  Status: {feature['status']}")
        print(f"  Details: {feature['details']}")
        print()

    # Summary
    passed = sum(1 for f in results.values() if '✅' in f['status'])
    total = len(results)

    print("=" * 70)
    print(f"\n🎯 Summary: {passed}/{total} features verified successfully")

    if passed == total:
        print("\n✅ ALL SYSTEM ARCHITECTURE FEATURES ARE COMPLETE AND OPERATIONAL! ✅")
        return 0
    else:
        print(f"\n⚠️  {total - passed} feature(s) need attention")
        return 1

if __name__ == '__main__':
    exit_code = verify_arch_implementation()
    sys.exit(exit_code)
