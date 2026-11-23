"""Single-process launch entry point for approved publication operations."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import sysconfig

if sys.flags.no_site:
    sys.path.append(sysconfig.get_paths()["purelib"])

import uvicorn
from dotenv import load_dotenv

load_dotenv(
    os.environ.get("MEDIAPOSTER_ENV_FILE", str(Path(__file__).with_name(".env"))),
    override=False,
)


def build_server() -> uvicorn.Server:
    return uvicorn.Server(
        uvicorn.Config(
            "control_plane_publication_app:app",
            host=os.environ.get("MEDIAPOSTER_HOST", "127.0.0.1"),
            port=int(os.environ.get("MEDIAPOSTER_PORT", "5555")),
            log_level=os.environ.get("MEDIAPOSTER_LOG_LEVEL", "info"),
            workers=1,
        )
    )


if __name__ == "__main__":
    build_server().run()
