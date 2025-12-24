"""
Unit Tests for FilterRegistry.

Tests:
    - Filter registration and unregistration
    - Enable/disable functionality
    - Version tracking
    - Thread-safety
    - Factory pattern support
"""

from __future__ import annotations

import threading
import time
from typing import Any, List
from unittest.mock import Mock

import pytest

from universe_screener.registry.filter_registry import FilterRegistry, FilterInfo


class MockFilterConfig:
    """Mock filter configuration."""

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold


class MockFilter:
    """Mock filter for testing."""

    def __init__(self, config: MockFilterConfig) -> None:
        self.config = config

    @property
    def name(self) -> str:
        return "mock_filter"

    def apply(self, assets: List[Any], date: Any, context: Any) -> Any:
        return Mock(passed_assets=assets, rejected_assets=[], rejection_reasons={})


class TestFilterRegistryRegistration:
    """Tests for filter registration."""

    def test_register_new_filter(self) -> None:
        """Successfully register a new filter."""
        registry = FilterRegistry()

        registry.register(
            name="structural",
            filter_class=MockFilter,
            version="1.0.0",
            config=MockFilterConfig(),
        )

        assert registry.registered_count == 1
        assert "structural" in registry.list_all()

    def test_register_with_description_and_tags(self) -> None:
        """Register filter with metadata."""
        registry = FilterRegistry()

        registry.register(
            name="liquidity",
            filter_class=MockFilter,
            version="2.1.0",
            config=MockFilterConfig(),
            description="Filters by trading volume",
            tags=["liquidity", "volume"],
        )

        info = registry.list_all()["liquidity"]
        assert info.description == "Filters by trading volume"
        assert "liquidity" in info.tags
        assert info.version == "2.1.0"

    def test_register_duplicate_raises(self) -> None:
        """Registering duplicate filter name raises error."""
        registry = FilterRegistry()
        registry.register("filter1", MockFilter, "1.0", MockFilterConfig())

        with pytest.raises(ValueError, match="already registered"):
            registry.register("filter1", MockFilter, "2.0", MockFilterConfig())

    def test_unregister_existing_filter(self) -> None:
        """Successfully unregister a filter."""
        registry = FilterRegistry()
        registry.register("filter1", MockFilter, "1.0", MockFilterConfig())

        result = registry.unregister("filter1")

        assert result is True
        assert registry.registered_count == 0

    def test_unregister_nonexistent_returns_false(self) -> None:
        """Unregistering non-existent filter returns False."""
        registry = FilterRegistry()

        result = registry.unregister("nonexistent")

        assert result is False

    def test_register_with_factory(self) -> None:
        """Register filter using custom factory."""
        registry = FilterRegistry()

        def custom_factory(config: MockFilterConfig) -> MockFilter:
            return MockFilter(config)

        registry.register_with_factory(
            name="custom",
            factory=custom_factory,
            version="1.0.0",
            config=MockFilterConfig(threshold=0.8),
        )

        filter_instance = registry.get_filter("custom")
        assert filter_instance is not None
        assert filter_instance.config.threshold == 0.8


class TestFilterRegistryEnableDisable:
    """Tests for enable/disable functionality."""

    @pytest.fixture
    def registry_with_filters(self) -> FilterRegistry:
        """Create registry with multiple filters."""
        registry = FilterRegistry()
        registry.register("structural", MockFilter, "1.0", MockFilterConfig())
        registry.register("liquidity", MockFilter, "1.0", MockFilterConfig())
        registry.register("data_quality", MockFilter, "1.0", MockFilterConfig())
        return registry

    def test_enable_filters_in_order(self, registry_with_filters: FilterRegistry) -> None:
        """Enable filters in specific order."""
        registry_with_filters.enable_filters(["liquidity", "structural"])

        enabled = registry_with_filters.get_enabled_filters()
        assert len(enabled) == 2
        # Order should match enable order
        assert enabled[0].name == "mock_filter"  # liquidity (MockFilter)
        assert enabled[1].name == "mock_filter"  # structural (MockFilter)

    def test_enable_unknown_filter_raises(self, registry_with_filters: FilterRegistry) -> None:
        """Enabling unknown filter raises error."""
        with pytest.raises(ValueError, match="Unknown filters"):
            registry_with_filters.enable_filters(["structural", "unknown"])

    def test_disable_filter(self, registry_with_filters: FilterRegistry) -> None:
        """Disable a specific filter."""
        registry_with_filters.enable_filters(["structural", "liquidity"])

        result = registry_with_filters.disable_filter("structural")

        assert result is True
        assert registry_with_filters.enabled_count == 1

    def test_enable_single_filter(self, registry_with_filters: FilterRegistry) -> None:
        """Enable single filter after initial setup."""
        registry_with_filters.enable_filters(["structural"])

        registry_with_filters.enable_filter("liquidity")

        assert registry_with_filters.enabled_count == 2

    def test_enable_replaces_previous(self, registry_with_filters: FilterRegistry) -> None:
        """Calling enable_filters replaces previous enabled set."""
        registry_with_filters.enable_filters(["structural", "liquidity"])
        registry_with_filters.enable_filters(["data_quality"])

        assert registry_with_filters.enabled_count == 1
        enabled = registry_with_filters.get_enabled_filters()
        # Only data_quality should be enabled
        assert len(enabled) == 1


class TestFilterRegistryGetFilter:
    """Tests for getting filter instances."""

    def test_get_filter_returns_instance(self) -> None:
        """Get filter returns instantiated filter."""
        registry = FilterRegistry()
        config = MockFilterConfig(threshold=0.7)
        registry.register("test", MockFilter, "1.0", config)

        filter_instance = registry.get_filter("test")

        assert filter_instance is not None
        assert isinstance(filter_instance, MockFilter)
        assert filter_instance.config.threshold == 0.7

    def test_get_nonexistent_returns_none(self) -> None:
        """Getting non-existent filter returns None."""
        registry = FilterRegistry()

        result = registry.get_filter("nonexistent")

        assert result is None

    def test_get_enabled_filters_returns_instances(self) -> None:
        """Get enabled filters returns list of instances."""
        registry = FilterRegistry()
        registry.register("filter1", MockFilter, "1.0", MockFilterConfig())
        registry.register("filter2", MockFilter, "1.0", MockFilterConfig())
        registry.enable_filters(["filter1", "filter2"])

        filters = registry.get_enabled_filters()

        assert len(filters) == 2
        assert all(isinstance(f, MockFilter) for f in filters)


class TestFilterRegistryVersioning:
    """Tests for version tracking."""

    def test_get_version(self) -> None:
        """Get version of specific filter."""
        registry = FilterRegistry()
        registry.register("test", MockFilter, "2.3.1", MockFilterConfig())

        version = registry.get_version("test")

        assert version == "2.3.1"

    def test_get_version_nonexistent(self) -> None:
        """Get version of non-existent filter returns None."""
        registry = FilterRegistry()

        version = registry.get_version("nonexistent")

        assert version is None

    def test_get_all_versions(self) -> None:
        """Get versions of all registered filters."""
        registry = FilterRegistry()
        registry.register("filter1", MockFilter, "1.0.0", MockFilterConfig())
        registry.register("filter2", MockFilter, "2.1.0", MockFilterConfig())

        versions = registry.get_versions()

        assert versions == {"filter1": "1.0.0", "filter2": "2.1.0"}


class TestFilterRegistryConfig:
    """Tests for config management."""

    def test_update_config(self) -> None:
        """Update filter configuration."""
        registry = FilterRegistry()
        registry.register("test", MockFilter, "1.0", MockFilterConfig(threshold=0.5))

        new_config = MockFilterConfig(threshold=0.9)
        result = registry.update_config("test", new_config)

        assert result is True
        filter_instance = registry.get_filter("test")
        assert filter_instance.config.threshold == 0.9

    def test_update_config_nonexistent(self) -> None:
        """Update config of non-existent filter returns False."""
        registry = FilterRegistry()

        result = registry.update_config("nonexistent", MockFilterConfig())

        assert result is False


class TestFilterRegistryThreadSafety:
    """Tests for thread-safety."""

    def test_concurrent_registration(self) -> None:
        """Concurrent registration is thread-safe."""
        registry = FilterRegistry()
        num_threads = 10
        filters_per_thread = 100
        errors: List[Exception] = []

        def register_filters(thread_id: int) -> None:
            try:
                for i in range(filters_per_thread):
                    name = f"filter_{thread_id}_{i}"
                    registry.register(name, MockFilter, "1.0", MockFilterConfig())
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_filters, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert registry.registered_count == num_threads * filters_per_thread

    def test_concurrent_enable_disable(self) -> None:
        """Concurrent enable/disable is thread-safe."""
        registry = FilterRegistry()
        for i in range(100):
            registry.register(f"filter_{i}", MockFilter, "1.0", MockFilterConfig())

        errors: List[Exception] = []

        def toggle_filters(iterations: int) -> None:
            try:
                for i in range(iterations):
                    # Enable some filters
                    registry.enable_filters([f"filter_{i % 100}"])
                    time.sleep(0.001)  # Tiny delay
                    registry.disable_filter(f"filter_{i % 100}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=toggle_filters, args=(50,))
            for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash, no assertion on count as it's non-deterministic
        assert len(errors) == 0


class TestFilterRegistryClear:
    """Tests for clearing registry."""

    def test_clear_removes_all(self) -> None:
        """Clear removes all filters."""
        registry = FilterRegistry()
        registry.register("filter1", MockFilter, "1.0", MockFilterConfig())
        registry.register("filter2", MockFilter, "1.0", MockFilterConfig())
        registry.enable_filters(["filter1"])

        registry.clear()

        assert registry.registered_count == 0
        assert registry.enabled_count == 0


class TestFilterInfo:
    """Tests for FilterInfo dataclass."""

    def test_to_dict(self) -> None:
        """FilterInfo.to_dict() creates serializable dict."""
        info = FilterInfo(
            name="test",
            version="1.0.0",
            enabled=True,
            filter_class=MockFilter,
            config=MockFilterConfig(),
            description="Test filter",
            tags=["test", "mock"],
        )

        result = info.to_dict()

        assert result["name"] == "test"
        assert result["version"] == "1.0.0"
        assert result["enabled"] is True
        assert result["description"] == "Test filter"
        assert "test" in result["tags"]
        assert result["config_type"] == "MockFilterConfig"

