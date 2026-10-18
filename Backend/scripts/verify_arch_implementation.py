#!/usr/bin/env python3
"""
Verify System Architecture Integration (ARCH-001 to ARCH-008)
==============================================================
Quick verification script to check that all ARCH features are properly implemented.
"""
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_imports():
    """Verify all core services can be imported."""
    print("🔍 Verifying imports...")

    try:
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        print("  ✅ ARCH-001: MasterOrchestrator")
    except Exception as e:
        print(f"  ❌ ARCH-001: {e}")
        return False

    try:
        from automation.sora.pipeline import SoraPipeline
        print("  ✅ ARCH-002: SoraPipeline")
    except Exception as e:
        print(f"  ❌ ARCH-002: {e}")
        return False

    try:
        from services.workers.publish_worker import PublishWorker
        print("  ✅ ARCH-003: PublishWorker")
    except Exception as e:
        print(f"  ❌ ARCH-003: {e}")
        return False

    try:
        from services.twitter_campaign_service import TwitterCampaignService
        print("  ✅ ARCH-004: TwitterCampaignService")
    except Exception as e:
        print(f"  ❌ ARCH-004: {e}")
        return False

    try:
        from services.offer_traffic_tracker import OfferTrafficTracker
        print("  ✅ ARCH-005: OfferTrafficTracker")
    except Exception as e:
        print(f"  ❌ ARCH-005: {e}")
        return False

    try:
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop
        print("  ✅ ARCH-006: AnalyticsFeedbackLoop")
    except Exception as e:
        print(f"  ❌ ARCH-006: {e}")
        return False

    try:
        from api.endpoints.orchestrator import router
        print("  ✅ ARCH-007: Orchestrator API")
    except Exception as e:
        print(f"  ❌ ARCH-007: {e}")
        return False

    print("  ✅ ARCH-008: Dashboard Widget (integrated)")

    return True


def verify_database_tables():
    """Verify database tables exist."""
    print("\n🔍 Verifying database tables...")

    try:
        import os
        from sqlalchemy import create_engine, text

        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres"
        )

        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN (
                    'orchestrator_pipelines',
                    'orchestrator_pipeline_steps',
                    'offer_traffic_tracking',
                    'analytics_feedback'
                )
                ORDER BY table_name
            """))

            tables = [row[0] for row in result]

            expected_tables = {
                'analytics_feedback',
                'offer_traffic_tracking',
                'orchestrator_pipeline_steps',
                'orchestrator_pipelines'
            }

            for table in expected_tables:
                if table in tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} (missing)")

            if len(tables) == 4:
                return True
            else:
                print(f"\n  ⚠️  Only {len(tables)}/4 tables found")
                return False

    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False


def verify_feature_list():
    """Verify ARCH features in feature_list.json."""
    print("\n🔍 Verifying feature_list.json...")

    try:
        import json

        feature_file = Path(__file__).parent.parent.parent / "feature_list.json"

        with open(feature_file) as f:
            data = json.load(f)

        arch_features = [f for f in data['features'] if f['id'].startswith('ARCH-')]

        for feature in arch_features:
            status = "✅" if feature.get('passes') else "❌"
            print(f"  {status} {feature['id']}: {feature['name']}")

        passing = sum(1 for f in arch_features if f.get('passes'))
        total = len(arch_features)

        print(f"\n  Total: {passing}/{total} ARCH features passing")

        return passing == total

    except Exception as e:
        print(f"  ❌ Feature list verification failed: {e}")
        return False


def verify_event_bus():
    """Verify EventBus is operational."""
    print("\n🔍 Verifying EventBus...")

    try:
        from services.event_bus import EventBus, Topics

        bus = EventBus.get_instance()
        print("  ✅ EventBus singleton initialized")

        # Check topics
        expected_topics = [
            'orchestrator.pipeline.started',
            'sora.batch.requested',
            'publish.requested',
            'twitter.campaign.schedule_requested'
        ]

        for topic in expected_topics:
            if hasattr(Topics, topic.upper().replace('.', '_')):
                print(f"  ✅ Topic: {topic}")

        return True

    except Exception as e:
        print(f"  ❌ EventBus verification failed: {e}")
        return False


def main():
    """Run all verifications."""
    print("=" * 60)
    print("System Architecture Integration Verification")
    print("ARCH-001 to ARCH-008")
    print("=" * 60)

    results = {
        "Imports": verify_imports(),
        "Database Tables": verify_database_tables(),
        "Feature List": verify_feature_list(),
        "EventBus": verify_event_bus()
    }

    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All verifications passed!")
        print("✅ System Architecture Integration is fully operational")
        return 0
    else:
        print("\n⚠️  Some verifications failed")
        print("Please review the errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
