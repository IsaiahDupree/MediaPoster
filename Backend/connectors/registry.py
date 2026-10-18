from typing import Dict, List, Optional, Type
from loguru import logger
from .base import SourceAdapter

class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter):
        """Register a new adapter instance"""
        if adapter.id in self._adapters:
            logger.warning(f"Overwriting existing adapter with id: {adapter.id}")
        self._adapters[adapter.id] = adapter
        logger.info(f"Registered connector adapter: {adapter.id} ({adapter.display_name})")

    def get_enabled_adapters(self) -> List[SourceAdapter]:
        """Get all enabled adapters"""
        return [a for a in self._adapters.values() if a.is_enabled()]

    def get_adapter_by_id(self, adapter_id: str) -> Optional[SourceAdapter]:
        """Get adapter by ID"""
        return self._adapters.get(adapter_id)

    def get_adapters_for_platform(self, platform: str) -> List[SourceAdapter]:
        """Get all enabled adapters that support a specific platform"""
        return [
            a for a in self.get_enabled_adapters() 
            if platform in a.list_supported_platforms()
        ]

    def get_all_supported_platforms(self) -> List[str]:
        """Get list of all supported platforms across enabled adapters"""
        platforms = set()
        for adapter in self.get_enabled_adapters():
            platforms.update(adapter.list_supported_platforms())
        return list(platforms)

# Global registry instance
registry = AdapterRegistry()
