"""
App Mode Configuration
Manages feature flags and adapter enablement based on APP_MODE
Defaults to full_stack (everything enabled)
"""
import os
from typing import List, Dict, Any
from enum import Enum


class AppMode(str, Enum):
    """Available application modes"""
    FULL_STACK = "full_stack"  # All features enabled (default)
    META_ONLY = "meta_only"  # Only Meta platforms
    BLOTATO_ONLY = "blotato_only"  # Only Blotato multi-platform
    LOCAL_LITE = "local_lite"  # Offline/local development


class FeatureFlags:
    """Feature flag configuration"""
    
    def __init__(self):
        self.app_mode = AppMode(os.getenv("APP_MODE", "full_stack"))
    
    # Core Features (always enabled)
    @property
    def people_graph_enabled(self) -> bool:
        """People Graph ingestion and analytics"""
        return True
    
    @property
    def content_metrics_enabled(self) -> bool:
        """Content cross-platform metrics"""
        return True
    
    @property
    def segments_enabled(self) -> bool:
        """Segment management"""
        return True
    
    @property
    def briefs_enabled(self) -> bool:
        """Content brief generation"""
        return True
    
    # Platform Adapters
    @property
    def meta_adapter_enabled(self) -> bool:
        """Meta (FB/IG/Threads) connector"""
        if self.app_mode == AppMode.BLOTATO_ONLY:
            return False
        if self.app_mode == AppMode.LOCAL_LITE:
            return False
        # Enabled in meta_only and full_stack
        return bool(os.getenv("META_PAGE_ACCESS_TOKEN"))
    
    @property
    def blotato_adapter_enabled(self) -> bool:
        """Blotato multi-platform connector"""
        if self.app_mode == AppMode.META_ONLY:
            return False
        if self.app_mode == AppMode.LOCAL_LITE:
            return False
        # Enabled in blotato_only and full_stack
        return bool(os.getenv("BLOTATO_API_KEY"))
    
    @property
    def youtube_adapter_enabled(self) -> bool:
        """YouTube native connector"""
        if self.app_mode != AppMode.FULL_STACK:
            return False
        return bool(os.getenv("YOUTUBE_API_KEY"))
    
    @property
    def tiktok_adapter_enabled(self) -> bool:
        """TikTok native connector"""
        if self.app_mode != AppMode.FULL_STACK:
            return False
        return bool(os.getenv("TIKTOK_API_KEY"))
    
    @property
    def linkedin_adapter_enabled(self) -> bool:
        """LinkedIn native connector"""
        if self.app_mode != AppMode.FULL_STACK:
            return False
        return bool(os.getenv("LINKEDIN_API_KEY"))
    
    # Optional Features
    @property
    def email_service_enabled(self) -> bool:
        """Email Service Provider"""
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        return bool(smtp_user and smtp_password)
    
    @property
    def rapidapi_enrichment_enabled(self) -> bool:
        """RapidAPI social handle enrichment"""
        # Disabled by default (privacy concerns)
        if os.getenv("ENABLE_RAPIDAPI_ENRICHMENT", "false").lower() != "true":
            return False
        return bool(os.getenv("RAPIDAPI_KEY"))
    
    @property
    def local_scrapers_enabled(self) -> bool:
        """Local scrapers for platforms"""
        # Only in full_stack or local_lite
        if self.app_mode not in [AppMode.FULL_STACK, AppMode.LOCAL_LITE]:
            return False
        return os.getenv("ENABLE_LOCAL_SCRAPERS", "false").lower() == "true"
    
    @property
    def ai_sentiment_enabled(self) -> bool:
        """OpenAI sentiment analysis"""
        return bool(os.getenv("OPENAI_API_KEY"))
    
    # Helper methods
    def get_enabled_adapters(self) -> List[str]:
        """Get list of enabled adapter IDs"""
        adapters = []
        if self.meta_adapter_enabled:
            adapters.append("meta")
        if self.blotato_adapter_enabled:
            adapters.append("blotato")
        if self.youtube_adapter_enabled:
            adapters.append("youtube")
        if self.tiktok_adapter_enabled:
            adapters.append("tiktok")
        if self.linkedin_adapter_enabled:
            adapters.append("linkedin")
        return adapters
    
    def get_enabled_features(self) -> List[str]:
        """Get list of enabled feature names"""
        features = []
        
        # Core (always enabled)
        features.extend([
            "people_graph",
            "content_metrics",
            "segments",
            "briefs"
        ])
        
        # Optional
        if self.email_service_enabled:
            features.append("email_service")
        if self.rapidapi_enrichment_enabled:
            features.append("rapidapi_enrichment")
        if self.local_scrapers_enabled:
            features.append("local_scrapers")
        if self.ai_sentiment_enabled:
            features.append("ai_sentiment")
        
        return features
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dict"""
        return {
            "app_mode": self.app_mode.value,
            "features": {
                "core": {
                    "people_graph": self.people_graph_enabled,
                    "content_metrics": self.content_metrics_enabled,
                    "segments": self.segments_enabled,
                    "briefs": self.briefs_enabled
                },
                "adapters": {
                    "meta": self.meta_adapter_enabled,
                    "blotato": self.blotato_adapter_enabled,
                    "youtube": self.youtube_adapter_enabled,
                    "tiktok": self.tiktok_adapter_enabled,
                    "linkedin": self.linkedin_adapter_enabled
                },
                "optional": {
                    "email_service": self.email_service_enabled,
                    "rapidapi_enrichment": self.rapidapi_enrichment_enabled,
                    "local_scrapers": self.local_scrapers_enabled,
                    "ai_sentiment": self.ai_sentiment_enabled
                }
            },
            "enabled_adapters": self.get_enabled_adapters(),
            "enabled_features": self.get_enabled_features()
        }


# Global feature flags instance
feature_flags = FeatureFlags()
