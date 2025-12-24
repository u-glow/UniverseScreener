"""
Filter Registry - Dynamic Filter Stage Management.

This module provides a thread-safe registry for managing filter stages
dynamically. Filters can be registered, enabled/disabled, and retrieved
based on configuration.

Usage:
    registry = FilterRegistry()
    registry.register("structural", StructuralFilter, "1.0.0", config)
    registry.register("liquidity", LiquidityFilter, "1.0.0", config)
    
    # Enable specific filters
    registry.enable_filters(["structural", "liquidity"])
    
    # Get enabled filters for pipeline
    filters = registry.get_enabled_filters()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Protocol, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from universe_screener.interfaces.filter_stage import FilterStageProtocol

logger = logging.getLogger(__name__)


@dataclass
class FilterInfo:
    """Metadata about a registered filter."""

    name: str
    version: str
    enabled: bool
    filter_class: Type[Any]
    config: Any
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "description": self.description,
            "tags": self.tags,
            "config_type": type(self.config).__name__ if self.config else None,
        }


class FilterRegistryProtocol(Protocol):
    """Protocol for filter registry implementations."""

    def register(
        self,
        name: str,
        filter_class: Type[Any],
        version: str,
        config: Any,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> None:
        """Register a filter with the registry."""
        ...

    def unregister(self, name: str) -> bool:
        """Unregister a filter by name."""
        ...

    def get_filter(self, name: str) -> Optional[Any]:
        """Get an instantiated filter by name."""
        ...

    def get_enabled_filters(self) -> List[Any]:
        """Get all enabled filters as instances."""
        ...

    def list_all(self) -> Dict[str, FilterInfo]:
        """List all registered filters."""
        ...

    def enable_filters(self, names: List[str]) -> None:
        """Enable specific filters by name."""
        ...

    def disable_filter(self, name: str) -> bool:
        """Disable a specific filter."""
        ...


class FilterRegistry:
    """
    Thread-safe registry for managing filter stages.
    
    Supports:
        - Dynamic registration of custom filters
        - Config-driven enable/disable
        - Version tracking per filter
        - Factory pattern for filter instantiation
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._filters: Dict[str, FilterInfo] = {}
        self._enabled_order: List[str] = []
        self._lock = RLock()
        self._factory_overrides: Dict[str, Callable[[Any], Any]] = {}
        logger.debug("FilterRegistry initialized")

    def register(
        self,
        name: str,
        filter_class: Type[Any],
        version: str,
        config: Any,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Register a filter with the registry.

        Args:
            name: Unique name for the filter
            filter_class: Filter class (must accept config in __init__)
            version: Version string for the filter
            config: Configuration object for the filter
            description: Optional description
            tags: Optional tags for categorization

        Raises:
            ValueError: If a filter with this name is already registered
        """
        with self._lock:
            if name in self._filters:
                raise ValueError(
                    f"Filter '{name}' is already registered. "
                    f"Use unregister() first or update_config()."
                )

            info = FilterInfo(
                name=name,
                version=version,
                enabled=False,
                filter_class=filter_class,
                config=config,
                description=description,
                tags=tags or [],
            )
            self._filters[name] = info
            logger.info(f"Registered filter: {name} v{version}")

    def register_with_factory(
        self,
        name: str,
        factory: Callable[[Any], Any],
        version: str,
        config: Any,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Register a filter with a custom factory function.

        Args:
            name: Unique name for the filter
            factory: Factory function that creates the filter instance
            version: Version string
            config: Configuration passed to factory
            description: Optional description
            tags: Optional tags
        """
        with self._lock:
            if name in self._filters:
                raise ValueError(f"Filter '{name}' is already registered.")

            # Use a placeholder class for info storage
            info = FilterInfo(
                name=name,
                version=version,
                enabled=False,
                filter_class=type(None),  # Placeholder
                config=config,
                description=description,
                tags=tags or [],
            )
            self._filters[name] = info
            self._factory_overrides[name] = factory
            logger.info(f"Registered filter with factory: {name} v{version}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a filter by name.

        Args:
            name: Name of the filter to remove

        Returns:
            True if filter was removed, False if not found
        """
        with self._lock:
            if name not in self._filters:
                logger.warning(f"Cannot unregister: filter '{name}' not found")
                return False

            del self._filters[name]
            if name in self._factory_overrides:
                del self._factory_overrides[name]
            if name in self._enabled_order:
                self._enabled_order.remove(name)

            logger.info(f"Unregistered filter: {name}")
            return True

    def get_filter(self, name: str) -> Optional[Any]:
        """
        Get an instantiated filter by name.

        Args:
            name: Name of the filter

        Returns:
            Filter instance or None if not found
        """
        with self._lock:
            info = self._filters.get(name)
            if info is None:
                return None

            return self._instantiate_filter(info)

    def get_enabled_filters(self) -> List[Any]:
        """
        Get all enabled filters as instances, in registration order.

        Returns:
            List of filter instances
        """
        with self._lock:
            filters = []
            for name in self._enabled_order:
                info = self._filters.get(name)
                if info and info.enabled:
                    try:
                        instance = self._instantiate_filter(info)
                        filters.append(instance)
                    except Exception as e:
                        logger.error(f"Failed to instantiate filter '{name}': {e}")
            return filters

    def _instantiate_filter(self, info: FilterInfo) -> Any:
        """Create filter instance from FilterInfo."""
        if info.name in self._factory_overrides:
            factory = self._factory_overrides[info.name]
            return factory(info.config)
        return info.filter_class(info.config)

    def list_all(self) -> Dict[str, FilterInfo]:
        """
        List all registered filters.

        Returns:
            Dictionary of filter name to FilterInfo
        """
        with self._lock:
            return dict(self._filters)

    def enable_filters(self, names: List[str]) -> None:
        """
        Enable specific filters by name and set execution order.

        Args:
            names: List of filter names to enable (in order)

        Raises:
            ValueError: If any filter name is not registered
        """
        with self._lock:
            # Validate all names exist
            unknown = [n for n in names if n not in self._filters]
            if unknown:
                raise ValueError(f"Unknown filters: {unknown}")

            # Disable all first
            for info in self._filters.values():
                info.enabled = False

            # Enable specified filters in order
            self._enabled_order = []
            for name in names:
                self._filters[name].enabled = True
                self._enabled_order.append(name)

            logger.info(f"Enabled filters: {names}")

    def disable_filter(self, name: str) -> bool:
        """
        Disable a specific filter.

        Args:
            name: Name of filter to disable

        Returns:
            True if disabled, False if not found
        """
        with self._lock:
            if name not in self._filters:
                return False

            self._filters[name].enabled = False
            if name in self._enabled_order:
                self._enabled_order.remove(name)

            logger.info(f"Disabled filter: {name}")
            return True

    def enable_filter(self, name: str) -> bool:
        """
        Enable a specific filter (appends to order if not already enabled).

        Args:
            name: Name of filter to enable

        Returns:
            True if enabled, False if not found
        """
        with self._lock:
            if name not in self._filters:
                return False

            self._filters[name].enabled = True
            if name not in self._enabled_order:
                self._enabled_order.append(name)

            logger.info(f"Enabled filter: {name}")
            return True

    def update_config(self, name: str, config: Any) -> bool:
        """
        Update configuration for a registered filter.

        Args:
            name: Filter name
            config: New configuration

        Returns:
            True if updated, False if not found
        """
        with self._lock:
            if name not in self._filters:
                return False

            self._filters[name].config = config
            logger.info(f"Updated config for filter: {name}")
            return True

    def get_version(self, name: str) -> Optional[str]:
        """Get version string for a filter."""
        with self._lock:
            info = self._filters.get(name)
            return info.version if info else None

    def get_versions(self) -> Dict[str, str]:
        """Get all filter versions."""
        with self._lock:
            return {name: info.version for name, info in self._filters.items()}

    @property
    def enabled_count(self) -> int:
        """Number of currently enabled filters."""
        with self._lock:
            return len(self._enabled_order)

    @property
    def registered_count(self) -> int:
        """Total number of registered filters."""
        with self._lock:
            return len(self._filters)

    def clear(self) -> None:
        """Remove all registered filters."""
        with self._lock:
            self._filters.clear()
            self._enabled_order.clear()
            self._factory_overrides.clear()
            logger.info("Cleared all filters from registry")

