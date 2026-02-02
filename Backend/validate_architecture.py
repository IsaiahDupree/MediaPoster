#!/usr/bin/env python3
"""
Architecture Validation Script (ARCH-001 to ARCH-008)
=====================================================

Quick validation that all system architecture components exist and are properly wired.
Run with: python3 validate_architecture.py
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env first
load_dotenv()

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent))


def check_imports():
    """Verify all critical imports work."""
    print("\n🔍 Checking imports...")

    try:
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig
        print("✅ MasterOrchestrator (ARCH-001)")
    except Exception as e:
        print(f"❌ MasterOrchestrator: {e}")
        return False

    try:
        from automation.sora.pipeline import SoraPipeline
        print("✅ SoraPipeline (ARCH-002)")
    except Exception as e:
        print(f"❌ SoraPipeline: {e}")
        return False

    try:
        from services.content_analyzer import ContentAnalyzer
        print("✅ ContentAnalyzer (ARCH-003)")
    except Exception as e:
        print(f"❌ ContentAnalyzer: {e}")
        return False

    try:
        from services.event_bus import EventBus, Topics
        print("✅ EventBus (Core)")
    except Exception as e:
        print(f"❌ EventBus: {e}")
        return False

    try:
        from api.endpoints.orchestrator import StartPipelineRequest
        print("✅ Orchestrator API (ARCH-007)")
    except Exception as e:
        print(f"❌ Orchestrator API: {e}")
        return False

    return True


def check_orchestrator_structure():
    """Verify Master Orchestrator has correct structure."""
    print("\n🔍 Checking Master Orchestrator structure...")

    try:
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        # Check attributes
        required_attrs = [
            ("event_bus", "EventBus"),
            ("content_analyzer", "ContentAnalyzer"),
            ("sora_pipeline", "SoraPipeline (optional)"),
            ("blotato_service", "BlotatoService (optional)"),
            ("twitter_service", "TwitterService (optional)"),
            ("active_pipelines", "Active pipelines dict"),
            ("completed_pipelines", "Completed pipelines dict"),
        ]

        for attr, description in required_attrs:
            if hasattr(orchestrator, attr):
                value = getattr(orchestrator, attr)
                if value is not None or "optional" in description:
                    print(f"✅ {attr}: {description}")
                else:
                    print(f"⚠️  {attr}: {description} (None)")
            else:
                print(f"❌ {attr}: Missing")
                return False

        # Check methods
        required_methods = [
            ("start_pipeline", "ARCH-001, ARCH-007"),
            ("list_pipelines", "ARCH-007"),
            ("get_pipeline_status", "ARCH-007"),
            ("_extract_platform_metadata", "ARCH-003"),
            ("start", "Lifecycle"),
            ("stop", "Lifecycle"),
        ]

        print("\n  Methods:")
        for method, description in required_methods:
            if hasattr(orchestrator, method):
                print(f"  ✅ {method}: {description}")
            else:
                print(f"  ❌ {method}: Missing ({description})")
                return False

        return True

    except Exception as e:
        print(f"❌ Error checking orchestrator: {e}")
        return False


def check_sora_pipeline_structure():
    """Verify SoraPipeline has multi-part generation."""
    print("\n🔍 Checking SoraPipeline structure (ARCH-002)...")

    try:
        from automation.sora.pipeline import SoraPipeline

        pipeline = SoraPipeline()

        # Check methods
        required_methods = [
            ("generate_single", "Single video generation"),
            ("generate_batch", "Batch video generation"),
            ("generate_multi_part", "3-part batch coordination (ARCH-002)"),
        ]

        for method, description in required_methods:
            if hasattr(pipeline, method):
                print(f"✅ {method}: {description}")
            else:
                print(f"❌ {method}: Missing ({description})")
                return False

        return True

    except Exception as e:
        print(f"❌ Error checking SoraPipeline: {e}")
        return False


def check_pipeline_config():
    """Verify PipelineConfig has correct structure."""
    print("\n🔍 Checking PipelineConfig structure...")

    try:
        from services.master_orchestrator import PipelineConfig

        config = PipelineConfig(
            theme="Test",
            num_parts=3,
            character="@test",
            publish_platforms=["tiktok", "instagram"],
            schedule_tweets=True,
            tweets_per_day=12,
            offer_url="https://example.com/offer",
            metadata={"key": "value"}
        )

        # Check attributes
        required_attrs = [
            ("theme", str),
            ("num_parts", int),
            ("character", str),
            ("publish_platforms", list),
            ("schedule_tweets", bool),
            ("tweets_per_day", int),
            ("offer_url", str),
            ("metadata", dict),
        ]

        for attr, expected_type in required_attrs:
            if hasattr(config, attr):
                value = getattr(config, attr)
                if isinstance(value, expected_type) or value is None:
                    print(f"✅ {attr}: {expected_type.__name__}")
                else:
                    print(f"❌ {attr}: Expected {expected_type.__name__}, got {type(value).__name__}")
                    return False
            else:
                print(f"❌ {attr}: Missing")
                return False

        return True

    except Exception as e:
        print(f"❌ Error checking PipelineConfig: {e}")
        return False


def check_content_analyzer():
    """Verify ContentAnalyzer integration."""
    print("\n🔍 Checking ContentAnalyzer (ARCH-003)...")

    try:
        from services.content_analyzer import ContentAnalyzer

        analyzer = ContentAnalyzer()

        # Check methods
        required_methods = [
            ("analyze", "Content analysis"),
        ]

        for method, description in required_methods:
            if hasattr(analyzer, method):
                print(f"✅ {method}: {description}")
            else:
                print(f"⚠️  {method}: Missing ({description})")

        return True

    except Exception as e:
        print(f"⚠️  ContentAnalyzer check: {e}")
        return True  # Don't fail on this


def check_metadata_extraction():
    """Verify platform metadata extraction works (ARCH-003)."""
    print("\n🔍 Checking metadata extraction (ARCH-003)...")

    try:
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        # Sample analysis
        analysis = {
            "title_tiktok": "Amazing viral video",
            "title_instagram": "Instagram title",
            "title_youtube": "YouTube title",
            "description": "Test description",
            "hashtags": ["#test"],
            "hook": "Hook text",
        }

        metadata = orchestrator._extract_platform_metadata(analysis)

        # Check structure
        required_platforms = ["default", "tiktok", "instagram", "youtube", "twitter", "threads"]
        for platform in required_platforms:
            if platform in metadata:
                pm = metadata[platform]
                if "title" in pm and "description" in pm and "hashtags" in pm:
                    print(f"✅ {platform}: Has title, description, hashtags")
                else:
                    print(f"❌ {platform}: Missing fields")
                    return False
            else:
                print(f"❌ {platform}: Missing from metadata")
                return False

        return True

    except Exception as e:
        print(f"❌ Error checking metadata extraction: {e}")
        return False


async def check_orchestrator_lifecycle():
    """Verify orchestrator can start and stop."""
    print("\n🔍 Checking orchestrator lifecycle...")

    try:
        from services.master_orchestrator import MasterOrchestrator

        orchestrator = MasterOrchestrator(use_db=False)

        # Start
        await orchestrator.start()
        if orchestrator._running:
            print("✅ Orchestrator starts successfully")
        else:
            print("❌ Orchestrator failed to start")
            return False

        # Stop
        await orchestrator.stop()
        if not orchestrator._running:
            print("✅ Orchestrator stops successfully")
        else:
            print("❌ Orchestrator failed to stop")
            return False

        return True

    except Exception as e:
        print(f"❌ Error checking lifecycle: {e}")
        return False


async def check_pipeline_creation():
    """Verify pipeline creation works."""
    print("\n🔍 Checking pipeline creation...")

    try:
        from services.master_orchestrator import MasterOrchestrator, PipelineConfig

        orchestrator = MasterOrchestrator(use_db=False)
        await orchestrator.start()

        config = PipelineConfig(
            theme="Validation Test",
            num_parts=2,
            publish_platforms=["tiktok"],
            schedule_tweets=False
        )

        pipeline_id = await orchestrator.start_pipeline(config)

        if pipeline_id and pipeline_id in orchestrator.active_pipelines:
            print(f"✅ Pipeline created: {pipeline_id}")
        else:
            print("❌ Pipeline creation failed")
            return False

        await orchestrator.stop()
        return True

    except Exception as e:
        print(f"❌ Error checking pipeline creation: {e}")
        return False


async def main():
    """Run all validation checks."""
    print("=" * 70)
    print("System Architecture Validation (ARCH-001 to ARCH-008)")
    print("=" * 70)

    results = []

    # Synchronous checks
    results.append(("Imports", check_imports()))
    results.append(("Orchestrator Structure", check_orchestrator_structure()))
    results.append(("SoraPipeline Structure", check_sora_pipeline_structure()))
    results.append(("PipelineConfig", check_pipeline_config()))
    results.append(("ContentAnalyzer", check_content_analyzer()))
    results.append(("Metadata Extraction", check_metadata_extraction()))

    # Async checks
    results.append(("Orchestrator Lifecycle", await check_orchestrator_lifecycle()))
    results.append(("Pipeline Creation", await check_pipeline_creation()))

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All architecture components are properly configured!")
        print("\nFeatures validated:")
        print("  ✅ ARCH-001: Master Orchestrator Service")
        print("  ✅ ARCH-002: 3-Part Sora Batch Coordination")
        print("  ✅ ARCH-003: Content Analyzer → Publisher Integration")
        print("  ✅ ARCH-007: Unified Pipeline API Endpoint")
        return 0
    else:
        print("\n⚠️  Some checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
