from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class PlatformMetricSnapshot(BaseModel):
    platform: str
    platform_post_id: str
    url: Optional[str] = None
    snapshot_at: datetime
    views: Optional[int] = None
    impressions: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    clicks: Optional[int] = None
    watch_time_seconds: Optional[int] = None
    raw_payload: Optional[Dict[str, Any]] = None

class ContentVariant(BaseModel):
    content_id: str
    platform: str
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    media_url: Optional[str] = None

class SourceAdapter(ABC):
    """
    Abstract base class for all social platform connectors.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the connector (e.g., 'meta', 'youtube')."""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if the connector is enabled based on env vars and config."""
        pass

    @abstractmethod
    def list_supported_platforms(self) -> List[str]:
        """List platforms supported by this connector (e.g., ['instagram', 'facebook'])."""
        pass

    @abstractmethod
    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """Fetch latest metrics for a specific content variant."""
        pass

    async def publish_variant(self, variant: ContentVariant) -> Dict[str, str]:
        """
        Publish content to the platform.
        Returns a dict with 'platform_post_id' and 'url'.
        Optional: Raise NotImplementedError if not supported.
        """
        raise NotImplementedError(f"Publishing not supported by {self.id} connector.")
