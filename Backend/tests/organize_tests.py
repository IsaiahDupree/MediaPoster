#!/usr/bin/env python3
"""
Test Directory Organization Script
Moves test files into organized subdirectories for better maintainability.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, List

# Test file mappings: source -> destination
TEST_ORGANIZATION = {
    # API Tests
    "api/accounts/": [
        "test_accounts_api.py",
        "test_social_accounts.py",
        "test_blotato_accounts.py",
    ],
    "api/media/": [
        "test_media_api.py",
        "test_media_processing_api.py",
        "test_media_processing_db.py",
        "test_video_api_endpoints.py",
        "test_video_streaming.py",
        "test_thumbnail_service.py",
        "test_thumbnail_generator.py",
        "test_image_analysis.py",
    ],
    "api/schedule/": [
        "test_schedule_api.py",
        "test_calendar_api.py",
        "test_scheduler_api.py",
        "test_automation_api.py",
    ],
    "api/content/": [
        "test_content_api.py",
        "test_posted_content_api.py",
        "test_posted_media.py",
        "test_content_services.py",
        "test_content_pipeline.py",
        "test_content_pipeline_part2.py",
        "test_content_pipeline_part3.py",
        "test_content_pipeline_part4.py",
        "test_content_pipeline_part5.py",
        "test_content_pipeline_part6.py",
    ],
    "api/posting/": [
        "test_posting_api.py",
        "test_publishing_flow.py",
        "test_publishing_system.py",
        "test_publishing_queue.py",
        "test_publishing_queue_api.py",
    ],
    "api/narrative/": [
        "test_narrative_builder.py",
        "test_narrative_scheduler.py",
    ],
    "api/experiments/": [
        "test_experiments.py",
        "test_experiments_scheduler.py",
    ],
    "api/analytics/": [
        "test_analytics_service.py",
        "test_analytics_system.py",
        "test_rapidapi_metrics.py",
        "test_rapidapi_integration.py",
    ],
    "api/": [
        "test_api_edge_cases.py",
        "test_api_integration.py",
        "test_api_endpoints_comprehensive.py",
        "test_health_api.py",
        "test_all_backend_endpoints.py",
    ],
    
    # Unit Tests
    "unit/services/": [
        "test_agent_services.py",
        "test_goals_service.py",
        "test_ingestion_service.py",
        "test_publisher_service.py",
        "test_calendar_service.py",
        "test_metrics_scheduler.py",
    ],
    "unit/utils/": [
        "test_assessor.py",
        "test_video_providers.py",
        "test_music_selector.py",
        "test_clip_extraction.py",
        "test_clip_editor.py",
        "test_clip_selector.py",
        "test_video_validator.py",
        "test_file_watcher.py",
        "test_platform_limits.py",
    ],
    "unit/": [
        "test_scheduler_unit_logic.py",
        "test_caption_generation.py",
        "test_analyze_endpoint.py",
        "test_enhanced_analysis_api.py",
    ],
    
    # Integration Tests
    "integration/workflows/": [
        "test_schedule_integration.py",
        "test_integration_scheduling.py",
        "test_posting_workflow_e2e.py",
        "test_full_pipeline_e2e.py",
    ],
    "integration/services/": [
        "test_google_drive_integration.py",
        "test_orchestration_worker.py",
        "test_background_analysis.py",
    ],
    
    # E2E Tests
    "e2e/workflows/": [
        "test_e2e_all_pages.py",
        "test_e2e_real_media.py",
        "test_frontend_pages_e2e.py",
        "test_frontend_integration.py",
        "test_all_pages_functionality.py",
        "test_all_pages_accessibility.py",
        "test_sidebar_pages.py",
        "test_frontend_button_functionality.py",
    ],
    
    # Comprehensive Tests
    "comprehensive/workflows/": [
        "test_content_growth.py",
        "test_approval_queue.py",
        "test_comment_automation.py",
        "test_analysis_triggering.py",
        "test_recent_features.py",
    ],
    "comprehensive/": [
        "test_orchestrator_comprehensive.py",
        "test_calendar_comprehensive.py",
        "test_hydration_comprehensive.py",
        "test_api_endpoints_comprehensive.py",
        "test_schedule_complete.py",
        "test_full_system_audit.py",
    ],
}

# Files to keep in root (runners, configs, docs)
KEEP_IN_ROOT = [
    "__init__.py",
    "conftest.py",
    "conftest_async.py",
    "conftest_real_db.py",
    "run_all_test_types.py",
    "README.md",
    "TEST_MATRIX.md",
    "FULL_PIPELINE_TEST_README.md",
    "PRD_TEST_COVERAGE.md",
    "ORGANIZATION_PLAN.md",
    "organize_tests.py",
]

def organize_tests(dry_run: bool = True):
    """Organize test files into subdirectories."""
    tests_dir = Path(__file__).parent
    moved = []
    not_found = []
    
    print("=" * 80)
    print("TEST DIRECTORY ORGANIZATION")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()
    
    for dest_dir, files in TEST_ORGANIZATION.items():
        dest_path = tests_dir / dest_dir
        if not dest_path.exists():
            if not dry_run:
                dest_path.mkdir(parents=True, exist_ok=True)
                # Create __init__.py
                (dest_path / "__init__.py").touch()
            print(f"📁 Creating: {dest_dir}")
        
        for filename in files:
            source = tests_dir / filename
            dest = dest_path / filename
            
            if not source.exists():
                not_found.append(filename)
                continue
            
            if source == dest:
                continue  # Already in right place
            
            if dest.exists():
                print(f"⚠️  Skipping {filename} - destination exists")
                continue
            
            print(f"   {filename} -> {dest_dir}")
            moved.append((source, dest))
            
            if not dry_run:
                shutil.move(str(source), str(dest))
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files to move: {len(moved)}")
    print(f"Files not found: {len(not_found)}")
    
    if not_found:
        print("\n⚠️  Files not found:")
        for f in not_found:
            print(f"   - {f}")
    
    if dry_run:
        print("\n💡 This was a dry run. Run with --execute to actually move files.")
    else:
        print("\n✅ Files moved successfully!")
    
    return moved, not_found

if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    organize_tests(dry_run=dry_run)

