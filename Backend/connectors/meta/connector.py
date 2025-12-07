import os
from typing import List, Dict, Any
from datetime import datetime
import httpx
from ..base import SourceAdapter, PlatformMetricSnapshot, ContentVariant

class MetaConnector(SourceAdapter):
    def __init__(self):
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN") # Long-lived token
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    @property
    def id(self) -> str:
        return "meta"

    def is_enabled(self) -> bool:
        return bool(self.app_id and self.app_secret and self.access_token)

    def list_supported_platforms(self) -> List[str]:
        return ["facebook", "instagram", "threads"]

    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        if not self.is_enabled():
            return []

        if variant.platform not in self.list_supported_platforms():
            return []

        # TODO: Implement actual Graph API calls here
        # For now, returning mock data structure to validate the pipeline
        
        # In a real implementation, we would:
        # 1. Determine if it's an IG Media or FB Post based on variant.platform
        # 2. Call /{object_id}/insights
        # 3. Map fields to PlatformMetricSnapshot

        # Mock response
        return [PlatformMetricSnapshot(
            platform=variant.platform,
            platform_post_id=variant.content_id, # Placeholder
            snapshot_at=datetime.now(),
            views=1000,
            likes=50,
            comments=10,
            shares=5,
            saves=2,
            impressions=1200,
            reach=900,
            raw_payload={"mock": True}
        )]
