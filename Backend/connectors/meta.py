import os
from typing import List, Dict, Any
from datetime import datetime
from .base import SourceAdapter, ContentVariant, PlatformMetricSnapshot

class MetaAdapter(SourceAdapter):
    def __init__(self):
        self._app_id = os.getenv("META_APP_ID")
        self._app_secret = os.getenv("META_APP_SECRET")
        self._page_access_token = os.getenv("META_PAGE_ACCESS_TOKEN")
        self._app_mode = os.getenv("APP_MODE", "full_stack")

    @property
    def id(self) -> str:
        return "meta"

    @property
    def display_name(self) -> str:
        return "Meta (FB/IG/Threads)"

    def is_enabled(self) -> bool:
        # Enabled if mode allows AND credentials exist
        mode_allows = self._app_mode in ["meta_only", "full_stack"]
        has_creds = bool(self._app_id and self._page_access_token)
        return mode_allows and has_creds

    def list_supported_platforms(self) -> List[str]:
        return ["facebook", "instagram", "threads"]

    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        if not self.is_enabled():
            return []
        
        # TODO: Implement actual Graph API calls
        # For now, return empty list or mock if in debug mode
        return []

    async def publish_variant(self, variant: ContentVariant) -> Dict[str, str]:
        if not self.is_enabled():
            raise RuntimeError("Meta adapter is not enabled")
            
        # TODO: Implement publishing logic
        return {"url": "", "platform_post_id": ""}
