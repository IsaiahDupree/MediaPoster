from fastapi.testclient import TestClient

from control_plane_publication_app import app


def test_minimal_control_plane_health_reports_readiness_without_secrets(monkeypatch):
    monkeypatch.setenv("MEDIAPOSTER_CONTROL_TOKEN", "private-control-token")
    monkeypatch.setenv("MEDIA_VAULT_CONTROL_URL", "http://127.0.0.1:5563")
    monkeypatch.setenv("MEDIA_VAULT_CONTROL_TOKEN", "private-vault-token")
    monkeypatch.setenv("BLOTATO_API_KEY", "private-provider-token")
    monkeypatch.setenv("MEDIAPOSTER_CONTROL_PUBLISH_ENABLED", "true")

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["configured"] == {
        "control_token": True,
        "media_vault": True,
        "provider": True,
        "provider_writes": True,
    }
    serialized = response.text
    assert "private-control-token" not in serialized
    assert "private-vault-token" not in serialized
    assert "private-provider-token" not in serialized


def test_minimal_control_plane_keeps_publication_routes_authenticated(monkeypatch):
    monkeypatch.setenv("MEDIAPOSTER_CONTROL_TOKEN", "expected-token")
    response = TestClient(app).get(
        "/v1/control-plane/publication-attempts/missing-attempt",
    )
    assert response.status_code == 401
