import os
from typing import List, Dict, Any
from datetime import datetime
import httpx
from ..base import SourceAdapter, PlatformMetricSnapshot, ContentVariant

class BlotatoConnector(SourceAdapter):
    def __init__(self):
        self.api_key = os.getenv("BLOTATO_API_KEY")
        self.base_url = "https://api.blotato.com/v2"

    @property
    def id(self) -> str:
        return "blotato"

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def list_supported_platforms(self) -> List[str]:
        return [
            "instagram", "tiktok", "youtube", "facebook", 
            "threads", "twitter", "linkedin", "pinterest", "bluesky"
        ]

    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        if not self.is_enabled():
            return []

        return [PlatformMetricSnapshot(
            platform=variant.platform,
            platform_post_id=variant.content_id,
            snapshot_at=datetime.now(),
            views=500,
            likes=25,
            comments=5,
            shares=2,
            saves=1,
            raw_payload={"source": "blotato_mock"}
        )]

    async def publish_variant(self, variant: ContentVariant, file_url: str = None, caption: str = None) -> Dict[str, str]:
        if not self.is_enabled():
            raise RuntimeError("Blotato connector is not enabled.")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/posts",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "platform": variant.platform,
                    "file_url": file_url,
                    "caption": caption,
                }
            )
            response.raise_for_status()
            data = response.json()
            return {
                "platform_post_id": data.get("post_id"),
                "public_url": data.get("public_url"),
            }
