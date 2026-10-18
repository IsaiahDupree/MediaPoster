from typing import List
from uuid import UUID
from datetime import datetime
from connectors import registry
from connectors.base import ContentVariant, PlatformMetricSnapshot

# Mock DB interface for now
class MockDB:
    async def get_active_variants(self) -> List[ContentVariant]:
        # TODO: Replace with actual DB call
        # Return some mock variants
        return [
            ContentVariant(
                id="mock-var-1",
                content_id="mock-content-1",
                platform="instagram",
                platform_post_id="ig_123",
                is_paid=False
            )
        ]

    async def save_metrics_snapshots(self, snapshots: List[PlatformMetricSnapshot]):
        # TODO: Replace with actual DB insert
        print(f"Saving {len(snapshots)} metrics snapshots to DB")
        for s in snapshots:
            print(f"  - {s.platform}: {s.views} views")

db = MockDB()

async def poll_metrics_for_active_variants():
    """
    Main job function:
    1. Fetch all active content variants (published, recent)
    2. Group by platform
    3. Call appropriate adapters to fetch metrics
    4. Save snapshots to DB
    """
    variants = await db.get_active_variants()
    
    snapshots: List[PlatformMetricSnapshot] = []
    
    for variant in variants:
        # Find adapter
        adapters = registry.get_adapters_for_platform(variant.platform)
        if not adapters:
            continue
            
        adapter = adapters[0]
        
        try:
            # Fetch metrics
            variant_snapshots = await adapter.fetch_metrics_for_variant(variant)
            snapshots.extend(variant_snapshots)
        except Exception as e:
            print(f"Error fetching metrics for variant {variant.id} on {variant.platform}: {e}")
            
    # Save all snapshots
    if snapshots:
        await db.save_metrics_snapshots(snapshots)
        
    return len(snapshots)
