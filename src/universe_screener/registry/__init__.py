"""
Registry Module - Dynamic Filter Management.

This module provides a registry for dynamically managing filter stages,
enabling config-driven filter activation and custom filter registration.

Components:
    - FilterRegistry: Central registry for filter management
    - FilterInfo: Metadata about registered filters
"""

from universe_screener.registry.filter_registry import (
    FilterRegistry,
    FilterInfo,
    FilterRegistryProtocol,
)

__all__ = [
    "FilterRegistry",
    "FilterInfo",
    "FilterRegistryProtocol",
]

