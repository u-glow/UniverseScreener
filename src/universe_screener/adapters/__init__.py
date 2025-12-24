"""
Adapters Package - Infrastructure Implementations.

This package contains concrete implementations of the abstract
interfaces defined in the interfaces package. Following the
Hexagonal Architecture (Ports & Adapters) pattern.

Providers:
    - MockUniverseProvider: Fake data for development/testing
    - DatabaseUniverseProvider: Real database connection (future)
    - CachedUniverseProvider: Caching wrapper (future)

Loggers:
    - ConsoleAuditLogger: Simple console output
    - JsonAuditLogger: Structured JSON logging (future)

Metrics:
    - InMemoryMetricsCollector: Simple in-memory collection
    - PrometheusMetricsCollector: OpenMetrics export (future)

Design Principles:
    - All adapters implement their respective protocols
    - Easily swappable via Dependency Injection
    - No business logic in adapters
"""

from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.adapters.cached_provider import CachedUniverseProvider
from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters.metrics_collector import InMemoryMetricsCollector

# Alias for backward compatibility
SimpleMetricsCollector = InMemoryMetricsCollector

__all__ = [
    "MockUniverseProvider",
    "CachedUniverseProvider",
    "ConsoleAuditLogger",
    "InMemoryMetricsCollector",
    "SimpleMetricsCollector",
]

