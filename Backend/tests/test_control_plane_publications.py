import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.control_plane_publications import (
    PublicationCoordinator,
    get_coordinator,
    router,
)
import api.control_plane_publications as publication_module


TOKEN = "test-mediaposter-control-token"


class FixtureDownloader:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.calls = 0

    async def fetch(self, request, destination):
        self.calls += 1
        assert hashlib.sha256(self.payload).hexdigest() == request.asset.sha256
        assert len(self.payload) == request.asset.bytes
        destination.write_bytes(self.payload)


class ReceiptProvider:
    def __init__(self, *, publish_result=None, status_result=None, raises=False):
        self.publish_result = publish_result or {
            "success": True,
            "post_submission_id": "provider-submission-1",
            "steps": {"publish": {"success": True}},
        }
        self.status_result = status_result or {
            "status": "published",
            "publicUrl": "https://social.example.test/post/123",
            "platformPostId": "123",
        }
        self.raises = raises
        self.publish_calls = 0
        self.status_calls = 0

    async def publish(self, file_path, request):
        self.publish_calls += 1
        assert file_path.read_bytes()
        if self.raises:
            raise RuntimeError("provider connection ended after submission began")
        return self.publish_result

    async def status(self, provider_submission_id):
        self.status_calls += 1
        assert provider_submission_id == "provider-submission-1"
        return self.status_result


@pytest.fixture()
def payload():
    return b"real deterministic contract fixture bytes"


@pytest.fixture()
def configured(tmp_path, monkeypatch, payload):
    monkeypatch.setenv("MEDIAPOSTER_CONTROL_TOKEN", TOKEN)
    monkeypatch.setenv("MEDIAPOSTER_CONTROL_PLANE_DB", str(tmp_path / "publications.sqlite3"))
    monkeypatch.setenv("MEDIA_VAULT_CONTROL_URL", "http://127.0.0.1:5563")
    monkeypatch.setenv("MEDIA_VAULT_CONTROL_TOKEN", "test-vault-token")
    monkeypatch.setenv("BLOTATO_API_KEY", "test-provider-key")
    monkeypatch.setenv("MEDIAPOSTER_CONTROL_PUBLISH_ENABLED", "true")
    provider = ReceiptProvider()
    downloader = FixtureDownloader(payload)
    coordinator = PublicationCoordinator(provider=provider, downloader=downloader)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_coordinator] = lambda: coordinator
    return TestClient(app), coordinator, provider, downloader


def attempt_request(payload, **overrides):
    now = datetime.now(timezone.utc)
    sha = hashlib.sha256(payload).hexdigest()
    document = {
        "schema_version": "1.0",
        "contract_type": "publication_attempt_request_v1",
        "content_work_item_id": "cwi_test_123",
        "production_plan_id": "plan_test_1",
        "production_plan_sha256": "a" * 64,
        "destination_id": "dst_test_tiktok",
        "attempt_number": 1,
        "platform": "tiktok",
        "airtime_account_id": "tiktok-isaiah",
        "provider_account_id": "710",
        "account_username": "@isaiah_dupree",
        "title": "A controlled publication test",
        "caption": "A complete caption for the controlled publication test.",
        "scheduled_at": (now - timedelta(minutes=1)).isoformat(),
        "freshness_deadline_at": (now + timedelta(days=1)).isoformat(),
        "asset": {
            "asset_id": "mv_asset_test",
            "sha256": sha,
            "bytes": len(payload),
            "download_path": "/v1/control-plane/assets/mv_asset_test/bytes",
        },
        "approval": {
            "generation_approval_id": "ga_test_1",
            "publication_policy": "auto_publish_after_qc",
            "approve_scheduled_publication": True,
            "approved_at": (now - timedelta(hours=1)).isoformat(),
        },
        "qc": {
            "decision": "passed",
            "receipt_sha256": "b" * 64,
            "asset_sha256": sha,
        },
        "held": False,
        "confirm_provider_write": True,
    }
    document.update(overrides)
    return document


def headers(key="publication-test-1"):
    return {"Authorization": f"Bearer {TOKEN}", "Idempotency-Key": key}


def test_control_routes_require_authentication(configured, payload):
    client, *_ = configured
    response = client.post(
        "/v1/control-plane/publication-preflights",
        json=attempt_request(payload),
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "MEDIAPOSTER_CONTROL_AUTH_REQUIRED"


def test_preflight_proves_approval_qc_and_readiness_without_a_write(configured, payload):
    client, _, provider, downloader = configured
    response = client.post(
        "/v1/control-plane/publication-preflights",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=attempt_request(payload),
    )
    assert response.status_code == 200, response.text
    assert response.json()["executable"] is True
    assert response.json()["approval_verified"] is True
    assert response.json()["qc_verified"] is True
    assert response.json()["provider_write_performed"] is False
    assert provider.publish_calls == 0
    assert downloader.calls == 0


def test_workspace_kill_switch_blocks_before_download(configured, payload, monkeypatch):
    client, _, provider, downloader = configured
    monkeypatch.setenv("MEDIAPOSTER_CONTROL_PUBLISH_ENABLED", "false")
    response = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("kill-switch"), json=attempt_request(payload),
    )
    assert response.status_code == 423
    assert response.json()["detail"]["code"] == "PUBLICATION_KILL_SWITCH_ACTIVE"
    assert provider.publish_calls == 0
    assert downloader.calls == 0


def test_attempt_is_journaled_and_double_submit_cannot_duplicate(configured, payload):
    client, _, provider, downloader = configured
    request = attempt_request(payload)
    first = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers(), json=request,
    )
    assert first.status_code == 200, first.text
    receipt = first.json()
    assert receipt["state"] == "submitted"
    assert receipt["provider_submission_id"] == "provider-submission-1"
    assert len(receipt["receipt_sha256"]) == 64

    second = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers(), json=request,
    )
    assert second.status_code == 200
    assert second.json()["attempt_id"] == receipt["attempt_id"]
    assert second.json()["idempotent_replay"] is True
    assert provider.publish_calls == 1
    assert downloader.calls == 1


def test_submitted_attempt_reconciles_to_public_url(configured, payload):
    client, _, provider, _ = configured
    created = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers(), json=attempt_request(payload),
    ).json()
    response = client.post(
        f"/v1/control-plane/publication-attempts/{created['attempt_id']}/reconcile",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    receipt = response.json()
    assert receipt["state"] == "published"
    assert receipt["public_url"] == "https://social.example.test/post/123"
    assert receipt["provider_post_id"] == "123"
    assert provider.status_calls == 1


def test_unknown_attempt_with_submission_id_reconciles_without_resubmit(configured, payload):
    client, _, provider, downloader = configured
    created = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("unknown-with-provider-id"), json=attempt_request(payload),
    ).json()
    db = sqlite3.connect(publication_module.os.environ["MEDIAPOSTER_CONTROL_PLANE_DB"])
    try:
        db.execute(
            "UPDATE control_plane_publication_attempts SET state='unknown' WHERE attempt_id=?",
            (created["attempt_id"],),
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/v1/control-plane/publication-attempts/{created['attempt_id']}/reconcile",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "published"
    assert provider.publish_calls == 1
    assert provider.status_calls == 1
    assert downloader.calls == 1


def test_ambiguous_provider_outcome_freezes_attempt(configured, payload):
    client, coordinator, _, downloader = configured
    provider = ReceiptProvider(raises=True)
    coordinator.provider = provider
    request = attempt_request(payload)
    response = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("ambiguous-attempt"), json=request,
    )
    assert response.status_code == 200
    assert response.json()["state"] == "unknown"
    assert response.json()["error"]["code"] == "PROVIDER_OUTCOME_UNKNOWN"

    replay = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("ambiguous-attempt"), json=request,
    )
    assert replay.json()["state"] == "unknown"
    assert provider.publish_calls == 1
    assert downloader.calls == 1


def test_failed_destination_can_use_next_attempt_without_touching_success(configured, payload):
    client, coordinator, provider, _ = configured
    first_request = attempt_request(payload)
    first = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("destination-one"), json=first_request,
    ).json()
    assert first["state"] == "submitted"

    coordinator.provider = ReceiptProvider(publish_result={
        "success": False, "error": "destination credential expired",
    })
    second_request = attempt_request(
        payload,
        destination_id="dst_test_instagram",
        platform="instagram_reels",
        airtime_account_id="instagram-test",
        provider_account_id="807",
    )
    second = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("destination-two"), json=second_request,
    ).json()
    assert second["state"] == "failed"
    assert second["error"]["message"] == "destination credential expired"

    unchanged = client.get(
        f"/v1/control-plane/publication-attempts/{first['attempt_id']}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ).json()
    assert unchanged["state"] == "submitted"
    assert unchanged["provider_submission_id"] == "provider-submission-1"
    assert provider.publish_calls == 1


def test_not_due_and_qc_asset_mismatch_fail_before_download(configured, payload):
    client, _, provider, downloader = configured
    future = attempt_request(
        payload,
        scheduled_at=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    )
    response = client.post(
        "/v1/control-plane/publication-preflights",
        headers={"Authorization": f"Bearer {TOKEN}"}, json=future,
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PUBLICATION_NOT_DUE"

    mismatch = attempt_request(payload)
    mismatch["qc"]["asset_sha256"] = "c" * 64
    response = client.post(
        "/v1/control-plane/publication-preflights",
        headers={"Authorization": f"Bearer {TOKEN}"}, json=mismatch,
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PUBLICATION_QC_ASSET_MISMATCH"
    assert provider.publish_calls == 0
    assert downloader.calls == 0


def test_completed_idempotent_receipt_replays_after_freshness_expires(
    configured, payload, monkeypatch
):
    client, _, provider, downloader = configured
    request = attempt_request(payload)
    first = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("freshness-replay"), json=request,
    )
    assert first.status_code == 200
    future = datetime.fromisoformat(request["freshness_deadline_at"]) + timedelta(days=1)
    monkeypatch.setattr(publication_module, "_now", lambda: future)

    replay = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("freshness-replay"), json=request,
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["attempt_id"] == first.json()["attempt_id"]
    assert provider.publish_calls == 1
    assert downloader.calls == 1


def test_preflight_requires_timezone_aware_timestamps(configured, payload):
    client, *_ = configured
    request = attempt_request(payload)
    request["scheduled_at"] = "2026-08-30T20:00:00"
    response = client.post(
        "/v1/control-plane/publication-preflights",
        headers={"Authorization": f"Bearer {TOKEN}"}, json=request,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PUBLICATION_TIMEZONE_REQUIRED"


def test_provider_receipts_strip_secrets_and_url_query_credentials(configured, payload):
    client, coordinator, _, _ = configured
    coordinator.provider = ReceiptProvider(publish_result={
        "success": True,
        "post_submission_id": "provider-submission-secret-test",
        "public_url": "https://social.example.test/post/456?access_token=do-not-store",
        "api_key": "do-not-store",
        "steps": {"publish": {"authorization": "Bearer do-not-store"}},
    })
    response = client.post(
        "/v1/control-plane/publication-attempts",
        headers=headers("sanitized-provider-receipt"), json=attempt_request(payload),
    )
    assert response.status_code == 200
    receipt = response.json()
    assert receipt["state"] == "published"
    assert receipt["public_url"] == "https://social.example.test/post/456"
    encoded = str(receipt)
    assert "do-not-store" not in encoded
    assert receipt["provider_result"]["api_key"] == "[REDACTED]"
