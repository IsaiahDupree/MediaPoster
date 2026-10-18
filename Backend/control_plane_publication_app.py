"""Minimal supervised runtime for Airtime-bound publication attempts."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI

from api.control_plane_publications import router


app = FastAPI(
    title="MediaPoster Publication Control Plane",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)
app.include_router(router)


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "mediaposter-publication-control-plane",
        "version": 1,
        "configured": {
            "control_token": bool(os.environ.get("MEDIAPOSTER_CONTROL_TOKEN")),
            "media_vault": bool(
                os.environ.get("MEDIA_VAULT_CONTROL_URL")
                and os.environ.get("MEDIA_VAULT_CONTROL_TOKEN")
            ),
            "provider": bool(os.environ.get("BLOTATO_API_KEY")),
            "provider_writes": (
                os.environ.get("MEDIAPOSTER_CONTROL_PUBLISH_ENABLED", "").lower()
                == "true"
            ),
        },
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
