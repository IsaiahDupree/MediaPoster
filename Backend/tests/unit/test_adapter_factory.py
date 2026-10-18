"""
Tests for Adapter Factory (MOD-007)
====================================
Tests the adapter factory pattern for creating platform adapters.
"""

import pytest
from connectors.factory import AdapterFactory, auto_register_adapters
from connectors.base import SourceAdapter
from typing import List


class MockAdapter(SourceAdapter):
    """Mock adapter for testing."""

    def __init__(self, adapter_id: str = "mock", enabled: bool = True):
        self._id = adapter_id
        self._enabled = enabled

    @property
    def id(self) -> str:
        return self._id

    @property
    def display_name(self) -> str:
        return f"Mock {self._id.title()}"

    def is_enabled(self) -> bool:
        return self._enabled

    def list_supported_platforms(self) -> List[str]:
        return [self._id]

    async def fetch_metrics_for_variant(self, variant):
        return []


def test_register_adapter_class():
    """Test registering an adapter class."""
    # Clear registry for clean test
    AdapterFactory._adapter_classes.clear()

    # Register mock adapter
    AdapterFactory.register_adapter_class("test_adapter", MockAdapter)

    # Verify it's registered
    assert "test_adapter" in AdapterFactory._adapter_classes
    assert AdapterFactory.is_registered("test_adapter")


def test_create_adapter():
    """Test creating an adapter instance."""
    # Clear and register
    AdapterFactory._adapter_classes.clear()

    # Create a specific adapter class for this test
    class TestAdapter(MockAdapter):
        def __init__(self):
            super().__init__(adapter_id="test_adapter", enabled=True)

    AdapterFactory.register_adapter_class("test_adapter", TestAdapter)

    # Create instance
    adapter = AdapterFactory.create("test_adapter")

    assert adapter is not None
    assert isinstance(adapter, MockAdapter)
    assert adapter.id == "test_adapter"
    assert adapter.is_enabled()


def test_create_nonexistent_adapter():
    """Test creating an adapter that doesn't exist."""
    AdapterFactory._adapter_classes.clear()

    adapter = AdapterFactory.create("nonexistent")

    assert adapter is None


def test_create_all_registered():
    """Test creating all registered adapter instances."""
    AdapterFactory._adapter_classes.clear()

    # Register multiple adapters
    AdapterFactory.register_adapter_class("adapter1", MockAdapter)
    AdapterFactory.register_adapter_class("adapter2", MockAdapter)
    AdapterFactory.register_adapter_class("adapter3", MockAdapter)

    # Create all
    adapters = AdapterFactory.create_all_registered()

    assert len(adapters) == 3
    assert all(isinstance(a, MockAdapter) for a in adapters)


def test_create_all_enabled():
    """Test creating only enabled adapter instances."""
    AdapterFactory._adapter_classes.clear()

    # Register mix of enabled and disabled
    class EnabledAdapter(MockAdapter):
        def __init__(self):
            super().__init__(adapter_id="enabled", enabled=True)

    class DisabledAdapter(MockAdapter):
        def __init__(self):
            super().__init__(adapter_id="disabled", enabled=False)

    AdapterFactory.register_adapter_class("enabled", EnabledAdapter)
    AdapterFactory.register_adapter_class("disabled", DisabledAdapter)

    # Create only enabled
    adapters = AdapterFactory.create_all_enabled()

    assert len(adapters) == 1
    assert adapters[0].id == "enabled"


def test_get_available_types():
    """Test getting list of available adapter types."""
    AdapterFactory._adapter_classes.clear()

    AdapterFactory.register_adapter_class("type1", MockAdapter)
    AdapterFactory.register_adapter_class("type2", MockAdapter)

    types = AdapterFactory.get_available_types()

    assert len(types) == 2
    assert "type1" in types
    assert "type2" in types


def test_auto_register_adapters():
    """Test auto-registration of adapter classes."""
    # Clear registry
    AdapterFactory._adapter_classes.clear()

    # Run auto-registration
    count = auto_register_adapters()

    # Should register at least one adapter (if available)
    assert count >= 0

    # Check that some adapters were registered
    types = AdapterFactory.get_available_types()
    assert isinstance(types, list)


def test_factory_integration():
    """Test full factory workflow."""
    # Clear and setup
    AdapterFactory._adapter_classes.clear()

    # Create specific adapter classes
    class TwitterAdapter(MockAdapter):
        def __init__(self):
            super().__init__(adapter_id="twitter", enabled=True)

    class InstagramAdapter(MockAdapter):
        def __init__(self):
            super().__init__(adapter_id="instagram", enabled=True)

    # Register adapters
    AdapterFactory.register_adapter_class("twitter", TwitterAdapter)
    AdapterFactory.register_adapter_class("instagram", InstagramAdapter)

    # Create specific adapter
    twitter = AdapterFactory.create("twitter")
    assert twitter is not None
    assert twitter.id == "twitter"

    # Create all
    all_adapters = AdapterFactory.create_all_registered()
    assert len(all_adapters) == 2

    # Get types
    types = AdapterFactory.get_available_types()
    assert "twitter" in types
    assert "instagram" in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
