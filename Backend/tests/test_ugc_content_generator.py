"""
Live integration tests for UGC Content Generation API and Publishing Controls API.
No mocks — hits the running server on localhost:5555.
Requires: server running, PostgreSQL available.
"""
import os
import uuid
import pytest
import requests

BASE = os.getenv("TEST_BASE_URL", "http://localhost:5555")
UGC = f"{BASE}/api/ugc-content"
PUB = f"{BASE}/api/publish-controls"
OFFERS = f"{BASE}/api/offers"
BRANDS = f"{BASE}/api/brands"


def _server_up():
    try:
        r = requests.get(f"{UGC}/stats", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _server_up(), reason="Server not running on localhost:5555")


# ══════════════════════════════════════════════════════════════════════════════
# UGC Content Generation API
# ══════════════════════════════════════════════════════════════════════════════

class TestUGCStats:
    def test_stats_returns_valid_structure(self):
        r = requests.get(f"{UGC}/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "by_status" in data
        assert "offers_covered" in data
        assert "format_types" in data


class TestUGCOffers:
    def test_list_offers_for_ugc(self):
        r = requests.get(f"{UGC}/offers")
        assert r.status_code == 200
        data = r.json()
        assert "offers" in data
        assert "count" in data
        assert isinstance(data["offers"], list)


class TestUGCScriptsCRUD:
    def test_list_scripts(self):
        r = requests.get(f"{UGC}/scripts")
        assert r.status_code == 200
        data = r.json()
        assert "scripts" in data
        assert "count" in data
        assert data["count"] == len(data["scripts"])

    def test_list_scripts_with_filters(self):
        r = requests.get(f"{UGC}/scripts", params={
            "status": "generated", "format_type": "talking_head", "limit": 5
        })
        assert r.status_code == 200
        for s in r.json()["scripts"]:
            assert s["status"] == "generated"
            assert s["format_type"] == "talking_head"

    def test_get_script_not_found(self):
        fake_id = str(uuid.uuid4())
        r = requests.get(f"{UGC}/scripts/{fake_id}")
        assert r.status_code == 404

    def test_update_status_invalid(self):
        r = requests.patch(f"{UGC}/scripts/any-id/status", params={"status": "bad_status"})
        assert r.status_code == 400

    def test_update_status_not_found(self):
        fake_id = str(uuid.uuid4())
        r = requests.patch(f"{UGC}/scripts/{fake_id}/status", params={"status": "approved"})
        assert r.status_code == 404

    def test_delete_not_found(self):
        fake_id = str(uuid.uuid4())
        r = requests.delete(f"{UGC}/scripts/{fake_id}")
        assert r.status_code == 404

    def test_update_script_no_fields(self):
        r = requests.patch(f"{UGC}/scripts/any-id", json={})
        assert r.status_code == 400

    def test_update_script_not_found(self):
        fake_id = str(uuid.uuid4())
        r = requests.patch(f"{UGC}/scripts/{fake_id}", json={"title": "New Title"})
        assert r.status_code == 404


class TestUGCGenerate:
    def test_generate_missing_offer_returns_404(self):
        fake_id = str(uuid.uuid4())
        r = requests.post(f"{UGC}/generate", json={
            "offer_id": fake_id,
            "count": 1,
        })
        assert r.status_code == 404


class TestUGCQueueIntegration:
    def test_queue_script_not_found(self):
        fake_id = str(uuid.uuid4())
        r = requests.post(f"{UGC}/scripts/{fake_id}/queue", json={
            "platform": "tiktok",
            "account_id": "710",
            "video_url": "/tmp/test.mp4",
        })
        assert r.status_code == 404

    def test_bulk_queue_empty(self):
        r = requests.post(f"{UGC}/scripts/bulk-queue", json={"items": []})
        assert r.status_code == 200
        data = r.json()
        assert data["queued"] == 0
        assert data["failed"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# Publishing Controls API
# ══════════════════════════════════════════════════════════════════════════════

class TestPublishControlsConfig:
    def test_get_config(self):
        r = requests.get(f"{PUB}/config")
        assert r.status_code == 200
        data = r.json()
        assert "global_enabled" in data
        assert "global_videos_per_day" in data
        assert "platform_limits" in data
        assert "posting_windows" in data
        assert "min_interval_minutes" in data

    def test_update_config(self):
        orig = requests.get(f"{PUB}/config").json()
        orig_limit = orig["global_videos_per_day"]

        # Update — response is {"updated": true, "config": {...}}
        r = requests.patch(f"{PUB}/config", json={"global_videos_per_day": 99})
        assert r.status_code == 200
        body = r.json()
        assert body["updated"] is True
        assert body["config"]["global_videos_per_day"] == 99

        # Restore
        requests.patch(f"{PUB}/config", json={"global_videos_per_day": orig_limit})


class TestPublishControlsPauseResume:
    def test_pause_and_resume(self):
        r = requests.post(f"{PUB}/config/pause")
        assert r.status_code == 200
        assert r.json()["global_enabled"] is False

        r = requests.post(f"{PUB}/config/resume")
        assert r.status_code == 200
        assert r.json()["global_enabled"] is True


class TestPublishControlsCanPublish:
    def test_can_publish_returns_structure(self):
        # Ensure publishing is on
        requests.post(f"{PUB}/config/resume")
        r = requests.get(f"{PUB}/can-publish/tiktok")
        assert r.status_code == 200
        data = r.json()
        assert "can_publish" in data
        assert "platform" in data
        assert data["platform"] == "tiktok"
        assert "global_enabled" in data
        assert "global_remaining" in data


class TestPublishControlsQueue:
    def test_list_queue(self):
        r = requests.get(f"{PUB}/queue")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "count" in data

    def test_queue_stats(self):
        r = requests.get(f"{PUB}/queue/stats")
        assert r.status_code == 200

    def test_cancel_not_found(self):
        fake_id = str(uuid.uuid4())
        r = requests.post(f"{PUB}/queue/{fake_id}/cancel")
        assert r.status_code == 404


class TestPublishControlsStatus:
    def test_full_status_dashboard(self):
        r = requests.get(f"{PUB}/status")
        assert r.status_code == 200
        data = r.json()
        assert "config" in data
        assert "daily_summary" in data
        assert "queue_stats" in data

    def test_daily_summary(self):
        r = requests.get(f"{PUB}/daily-summary")
        assert r.status_code == 200
        data = r.json()
        assert "global_enabled" in data
        assert "global_published" in data
        assert "global_remaining" in data


class TestPublishControlsQueueLifecycle:
    """Enqueue a video, then walk it through pause/resume/cancel/delete."""

    def test_enqueue_and_lifecycle(self):
        # Enqueue — response is {"queued": true, "item": {...}}
        r = requests.post(f"{PUB}/queue", json={
            "video_url": "https://example.com/test_video.mp4",
            "caption": "Integration test caption",
            "platform": "tiktok",
            "account_id": "test-710",
            "title": "Integration Test Video",
            "hashtags": ["#test", "#integration"],
            "priority": 8,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["queued"] is True
        item_id = body["item"]["id"]
        assert body["item"]["platform"] == "tiktok"
        assert body["item"]["status"] == "queued"

        # Get the item back
        r = requests.get(f"{PUB}/queue/{item_id}")
        assert r.status_code == 200
        assert r.json()["id"] == item_id

        # Update caption
        r = requests.patch(f"{PUB}/queue/{item_id}", json={"caption": "Updated caption"})
        assert r.status_code == 200

        # Change priority
        r = requests.patch(f"{PUB}/queue/{item_id}/priority", json={"priority": 2})
        assert r.status_code == 200

        # Pause the item
        r = requests.post(f"{PUB}/queue/{item_id}/pause")
        assert r.status_code == 200

        # Resume
        r = requests.post(f"{PUB}/queue/{item_id}/resume")
        assert r.status_code == 200

        # Cancel
        r = requests.post(f"{PUB}/queue/{item_id}/cancel")
        assert r.status_code == 200

        # Delete
        r = requests.delete(f"{PUB}/queue/{item_id}")
        assert r.status_code == 200

        # Confirm gone
        r = requests.get(f"{PUB}/queue/{item_id}")
        assert r.status_code == 404


class TestPublishControlsHistory:
    def test_history_endpoint(self):
        r = requests.get(f"{PUB}/history", params={"days": 7, "limit": 10})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "count" in data


# ══════════════════════════════════════════════════════════════════════════════
# Offers API (dependency for UGC generation)
# ══════════════════════════════════════════════════════════════════════════════

class TestOffersAPI:
    def test_list_offers(self):
        r = requests.get(f"{OFFERS}/", allow_redirects=True)
        assert r.status_code == 200

    def test_create_and_delete_offer(self):
        # Create a brand first (required FK)
        brand_r = requests.post(f"{BRANDS}/", json={
            "name": "Test Brand Live",
            "description": "Created by integration test",
        }, allow_redirects=True)
        if brand_r.status_code not in (200, 201):
            pytest.skip(f"Could not create brand: {brand_r.status_code} {brand_r.text[:200]}")
        brand_id = brand_r.json().get("id")
        if not brand_id:
            pytest.skip("Brand creation returned no id")

        try:
            # Create offer (brand_id required)
            r = requests.post(f"{OFFERS}/", json={
                "brand_id": brand_id,
                "title": "Integration Test Offer",
                "description": "Created by live integration test",
                "offer_type": "product",
                "landing_page_url": "https://example.com/test-offer",
                "cta_text": "Try it free",
                "price": 9.99,
                "currency": "USD",
                "priority": 1,
            }, allow_redirects=True)
            assert r.status_code in (200, 201), f"Offer create failed: {r.text[:300]}"
            offer = r.json()
            offer_id = offer.get("id")
            assert offer_id is not None
            assert offer["title"] == "Integration Test Offer"

            # Verify via GET
            r = requests.get(f"{OFFERS}/{offer_id}")
            assert r.status_code == 200

            # Verify it shows up in UGC offers list
            r = requests.get(f"{UGC}/offers")
            assert r.status_code == 200
            ids = [o["id"] for o in r.json()["offers"]]
            assert offer_id in ids

            # Clean up offer
            requests.delete(f"{OFFERS}/{offer_id}")

        finally:
            # Clean up brand
            requests.delete(f"{BRANDS}/{brand_id}")


# ══════════════════════════════════════════════════════════════════════════════
# End-to-End: Create Offer -> Generate UGC -> Review -> Queue -> Cleanup
# ══════════════════════════════════════════════════════════════════════════════

class TestE2EOfferToUGC:
    """Full pipeline test: offer -> UGC generation -> script lifecycle -> queue."""

    def test_full_pipeline(self):
        # 1. Create brand
        brand_r = requests.post(f"{BRANDS}/", json={
            "name": "E2E Test Brand",
            "description": "E2E integration test brand",
        }, allow_redirects=True)
        if brand_r.status_code not in (200, 201):
            pytest.skip(f"Brand creation failed: {brand_r.text[:200]}")
        brand_id = brand_r.json().get("id")
        if not brand_id:
            pytest.skip("No brand_id returned")

        # 2. Create offer
        r = requests.post(f"{OFFERS}/", json={
            "brand_id": brand_id,
            "title": "E2E Test Product",
            "description": "Amazing product for integration testing",
            "offer_type": "product",
            "landing_page_url": "https://example.com/e2e",
            "cta_text": "Get it now",
            "price": 19.99,
            "priority": 1,
        }, allow_redirects=True)
        if r.status_code not in (200, 201):
            requests.delete(f"{BRANDS}/{brand_id}")
            pytest.skip(f"Offer creation failed: {r.text[:200]}")
        offer_id = r.json()["id"]

        try:
            # 3. Generate UGC scripts (requires OPENAI_API_KEY)
            r = requests.post(f"{UGC}/generate", json={
                "offer_id": offer_id,
                "count": 2,
                "formats": ["talking_head"],
                "duration": 30,
            })
            if r.status_code == 404:
                pytest.skip("Generation returned no scripts (OpenAI key may be missing)")
            assert r.status_code == 200
            data = r.json()
            assert data["generated"] >= 1
            scripts = data["scripts"]
            script_id = scripts[0]["id"]

            # 4. Verify script retrieval
            r = requests.get(f"{UGC}/scripts/{script_id}")
            assert r.status_code == 200
            assert r.json()["offer_id"] == offer_id

            # 5. List scripts filtered by offer
            r = requests.get(f"{UGC}/scripts", params={"offer_id": offer_id})
            assert r.status_code == 200
            assert r.json()["count"] >= 1

            # 6. Edit the script
            r = requests.patch(f"{UGC}/scripts/{script_id}", json={
                "caption": "Updated by E2E test",
                "status": "approved",
            })
            assert r.status_code == 200

            # 7. Queue for publishing
            r = requests.post(f"{UGC}/scripts/{script_id}/queue", json={
                "platform": "tiktok",
                "account_id": "test-710",
                "video_url": "/tmp/e2e_test_video.mp4",
            })
            assert r.status_code == 200
            assert r.json()["queued"] is True

            # 8. Verify script status updated
            r = requests.get(f"{UGC}/scripts/{script_id}")
            assert r.status_code == 200
            assert r.json()["status"] == "queued"

            # 9. Stats should reflect new scripts
            r = requests.get(f"{UGC}/stats")
            assert r.status_code == 200
            assert r.json()["total"] >= 1

            # 10. Clean up scripts
            for s in scripts:
                requests.delete(f"{UGC}/scripts/{s['id']}")

        finally:
            requests.delete(f"{OFFERS}/{offer_id}")
            requests.delete(f"{BRANDS}/{brand_id}")
