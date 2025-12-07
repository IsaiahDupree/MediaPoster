import asyncio
import httpx
from uuid import uuid4
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5555/api"

async def test_content_workflow():
    print("\n--- Testing Content Workflow ---")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Create Content Item
        print("1. Creating Content Item...")
        item_payload = {
            "title": "E2E Test Video",
            "description": "A video created during E2E testing",
            "type": "video",
            "source_url": "http://example.com/video.mp4"
        }
        response = await client.post("/content/items", json=item_payload)
        if response.status_code != 201:
            print(f"❌ Failed to create item: {response.text}")
            return
        item = response.json()
        item_id = item["id"]
        print(f"✅ Created Item: {item_id}")

        # 2. Generate Variants
        print("2. Generating Variants...")
        platforms = ["instagram", "linkedin"]
        response = await client.post(f"/content/items/{item_id}/generate-variants", json=platforms)
        if response.status_code != 200:
            print(f"❌ Failed to generate variants: {response.text}")
            return
        variants = response.json()
        print(f"✅ Generated {len(variants)} variants")
        
        # 3. Publish Variant (Mock)
        print("3. Publishing Variant...")
        variant_id = variants[0]["id"]
        response = await client.post(f"/content/variants/{variant_id}/publish")
        if response.status_code != 200:
            print(f"❌ Failed to publish variant: {response.text}")
            return
        result = response.json()
        print(f"✅ Published: {result}")

async def test_metrics_workflow():
    print("\n--- Testing Metrics Workflow ---")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Poll Metrics
        print("1. Polling Metrics...")
        response = await client.post("/content/jobs/poll-metrics")
        if response.status_code != 200:
            print(f"❌ Failed to poll metrics: {response.text}")
            return
        print(f"✅ Polling Result: {response.json()}")

        # 2. Aggregate Rollups
        print("2. Aggregating Rollups...")
        response = await client.post("/content/jobs/aggregate-rollups")
        if response.status_code != 200:
            print(f"❌ Failed to aggregate rollups: {response.text}")
            return
        print(f"✅ Aggregation Result: {response.json()}")

async def test_segments_workflow():
    print("\n--- Testing Segments Workflow ---")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Create Segment
        print("1. Creating Segment...")
        segment_payload = {
            "name": "E2E Test Segment",
            "description": "Created by E2E test",
            "definition": {
                "operator": "AND",
                "conditions": [{"field": "interests", "operator": "contains", "value": "Testing"}]
            }
        }
        response = await client.post("/segments/", json=segment_payload)
        if response.status_code != 201:
            print(f"❌ Failed to create segment: {response.text}")
            return
        segment = response.json()
        segment_id = segment["id"]
        print(f"✅ Created Segment: {segment_id}")

        # 2. Get Insights
        print("2. Fetching Insights...")
        response = await client.get(f"/segments/{segment_id}/insights")
        if response.status_code != 200:
            print(f"❌ Failed to get insights: {response.text}")
            return
        insights = response.json()
        print(f"✅ Insights received: {len(insights)} types (organic/paid)")

        # 3. Generate Briefs
        print("3. Generating Briefs...")
        response = await client.post(f"/briefs/generate/{segment_id}")
        if response.status_code != 200:
            print(f"❌ Failed to generate briefs: {response.text}")
            return
        briefs = response.json()
        print(f"✅ Generated {len(briefs)} briefs")
        if briefs:
            print(f"   - Sample Topic: {briefs[0]['topic']}")

async def main():
    print("🚀 Starting EverReach/Blend E2E Test")
    
    # Ensure server is running (check health or root)
    async with httpx.AsyncClient(base_url="http://localhost:5555", timeout=5.0) as client:
        try:
            await client.get("/health")
            print("✅ Backend is reachable")
        except Exception:
            print("❌ Backend is NOT reachable. Make sure it's running on localhost:5555")
            return

    await test_content_workflow()
    await test_metrics_workflow()
    await test_segments_workflow()
    
    print("\n✨ E2E Test Complete")

if __name__ == "__main__":
    asyncio.run(main())
