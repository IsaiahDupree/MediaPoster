import os
from typing import List, Dict, Any
from datetime import datetime
from ..base import SourceAdapter, PlatformMetricSnapshot, ContentVariant

class TikTokConnector(SourceAdapter):
    def __init__(self):
        self.app_key = os.getenv("TIKTOK_APP_KEY")
        self.app_secret = os.getenv("TIKTOK_APP_SECRET")

    @property
    def id(self) -> str:
        return "tiktok"

    def is_enabled(self) -> bool:
        return bool(self.app_key and self.app_secret)

    def list_supported_platforms(self) -> List[str]:
        return ["tiktok"]

    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        if not self.is_enabled():
            return []

        if variant.platform != "tiktok":
            return []

        # In a real implementation:
        # Call TikTok API /video/query/
        
        # Mock response
        return [PlatformMetricSnapshot(
            platform="tiktok",
            platform_post_id=variant.content_id, # Placeholder
            snapshot_at=datetime.now(),
            views=5000,
            likes=300,
            comments=80,
            shares=150,
            saves=200,
            raw_payload={"source": "tiktok_mock"}
        )]

    async def publish_variant(self, variant: ContentVariant) -> Dict[str, str]:
        if not self.is_enabled():
            raise RuntimeError("TikTok connector is not enabled.")

        # In a real implementation:
        # Upload video via TikTok API
        
        # Mock response
        return {
            "platform_post_id": f"tt_{datetime.now().timestamp()}",
            "url": f"https://tiktok.com/@user/video/mock_id"
        }
