"""
Tests for AI-Assisted Curation System
Tests coverage stats, sentiment analysis, duplicate detection, auto-curation, and bulk operations.
"""
import pytest
import httpx
import asyncio

API_URL = "http://localhost:5555"
TIMEOUT = 30.0


class TestAICuration:
    """Test suite for AI curation endpoints."""

    @pytest.mark.asyncio
    async def test_coverage_stats(self):
        """Test coverage stats endpoint returns expected fields."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.get(f"{API_URL}/api/curation/coverage-stats")
            assert res.status_code == 200
            data = res.json()
            
            # Verify all required fields exist
            assert "total_media" in data
            assert "analyzed" in data
            assert "unanalyzed" in data
            assert "with_transcript" in data
            assert "with_sentiment" in data
            assert "approved" in data
            assert "rejected" in data
            assert "pending" in data
            
            # Verify counts are non-negative
            assert data["total_media"] >= 0
            assert data["analyzed"] >= 0
            assert data["with_sentiment"] >= 0
            
            print(f"✅ Coverage stats: {data['analyzed']}/{data['total_media']} analyzed, {data['with_sentiment']} with sentiment")

    @pytest.mark.asyncio
    async def test_duplicate_detection_excludes_caption_variants(self):
        """Test that duplicate detection excludes caption variants by default."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.get(f"{API_URL}/api/curation/duplicates?threshold=0.9")
            assert res.status_code == 200
            data = res.json()
            
            # Verify response structure
            assert "groups" in data
            assert "total_duplicates" in data
            assert "caption_variants_excluded" in data
            assert "caption_variant_groups" in data
            assert "message" in data
            
            # Caption variants should be tracked
            assert isinstance(data["caption_variants_excluded"], int)
            assert isinstance(data["caption_variant_groups"], int)
            
            print(f"✅ Duplicates: {data['total_duplicates']} deletable, {data['caption_variants_excluded']} caption variants excluded")

    @pytest.mark.asyncio
    async def test_duplicate_detection_include_caption_variants(self):
        """Test that caption variants can be included when requested."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.get(f"{API_URL}/api/curation/duplicates?threshold=0.9&include_caption_variants=true")
            assert res.status_code == 200
            data = res.json()
            
            # When include_caption_variants=true, groups should include them
            for group in data.get("groups", []):
                assert "is_caption_variant" in group
                assert "videos" in group
                assert "similarity_score" in group
                
                # Caption variants should have a reason
                if group["is_caption_variant"]:
                    assert group.get("caption_variant_reason") is not None
            
            print(f"✅ With caption variants: {len(data['groups'])} total groups")

    @pytest.mark.asyncio
    async def test_auto_curation_settings(self):
        """Test auto-curation settings endpoint."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Get current settings
            res = await client.get(f"{API_URL}/api/curation/auto-curate/settings")
            assert res.status_code == 200
            data = res.json()
            
            # Verify settings fields
            assert "auto_deny_threshold" in data
            assert "auto_approve_threshold" in data
            assert "min_score_for_approval" in data
            assert "enabled" in data
            
            # Thresholds should be in valid range
            assert -1.0 <= data["auto_deny_threshold"] <= 1.0
            assert -1.0 <= data["auto_approve_threshold"] <= 1.0
            
            print(f"✅ Auto-curation settings: deny<{data['auto_deny_threshold']}, approve>{data['auto_approve_threshold']}")

    @pytest.mark.asyncio
    async def test_auto_curation_preview(self):
        """Test auto-curation preview shows what would be curated."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.get(f"{API_URL}/api/curation/auto-curate/preview")
            assert res.status_code == 200
            data = res.json()
            
            # Verify preview fields
            assert "would_deny" in data
            assert "would_approve" in data
            assert "need_review" in data
            assert "settings" in data
            
            # Counts should be non-negative
            assert data["would_deny"] >= 0
            assert data["would_approve"] >= 0
            assert data["need_review"] >= 0
            
            print(f"✅ Auto-curation preview: {data['would_approve']} approve, {data['would_deny']} deny, {data['need_review']} review")

    @pytest.mark.asyncio
    async def test_filter_preview(self):
        """Test filter preview endpoint."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Test with sentiment filter
            res = await client.get(f"{API_URL}/api/curation/filter-preview?sentiment_min=0.5")
            assert res.status_code == 200
            data = res.json()
            
            assert "count" in data
            assert data["count"] >= 0
            
            print(f"✅ Filter preview (sentiment>0.5): {data['count']} videos")

    @pytest.mark.asyncio
    async def test_bulk_approve_requires_input(self):
        """Test bulk approve requires media_ids or filter."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.post(f"{API_URL}/api/curation/bulk-approve", json={})
            # Should return 400 error
            assert res.status_code == 400
            
            print("✅ Bulk approve correctly requires media_ids or filter")

    @pytest.mark.asyncio
    async def test_bulk_deny_requires_input(self):
        """Test bulk deny requires media_ids or filter."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.post(f"{API_URL}/api/curation/bulk-deny", json={})
            # Should return 400 error
            assert res.status_code == 400
            
            print("✅ Bulk deny correctly requires media_ids or filter")


# Run tests directly
if __name__ == "__main__":
    async def run_all_tests():
        test = TestAICuration()
        print("\n" + "="*60)
        print("🧪 Running AI Curation Tests")
        print("="*60 + "\n")
        
        tests = [
            ("Coverage Stats", test.test_coverage_stats),
            ("Duplicate Detection (excludes caption variants)", test.test_duplicate_detection_excludes_caption_variants),
            ("Duplicate Detection (include caption variants)", test.test_duplicate_detection_include_caption_variants),
            ("Auto-Curation Settings", test.test_auto_curation_settings),
            ("Auto-Curation Preview", test.test_auto_curation_preview),
            ("Filter Preview", test.test_filter_preview),
            ("Bulk Approve Validation", test.test_bulk_approve_requires_input),
            ("Bulk Deny Validation", test.test_bulk_deny_requires_input),
        ]
        
        passed = 0
        failed = 0
        
        for name, test_fn in tests:
            try:
                await test_fn()
                passed += 1
            except Exception as e:
                print(f"❌ {name}: {e}")
                failed += 1
        
        print("\n" + "="*60)
        print(f"📊 Results: {passed} passed, {failed} failed")
        print("="*60)
        
        return failed == 0
    
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
