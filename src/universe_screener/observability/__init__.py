"""
Observability Package - Unified Logging, Metrics, Tracing.

This package provides comprehensive observability:
    - ObservabilityManager: Unified logging with correlation IDs
    - HealthMonitor: System health checks
    - SnapshotManager: Point-in-time data consistency
    - VersionManager: Code and config versioning

Design Principles:
    - All dependencies optional (backwards compatible)
    - Structured JSON logging via structlog (fallback to stdlib)
    - Correlation ID propagation for end-to-end tracing
"""

from universe_screener.observability.observability_manager import (
    ObservabilityManager,
)
from universe_screener.observability.health_monitor import (
    HealthMonitor,
    HealthStatus,
)
from universe_screener.observability.snapshot_manager import (
    SnapshotManager,
)
from universe_screener.observability.version_manager import (
    VersionManager,
)

__all__ = [
    "ObservabilityManager",
    "HealthMonitor",
    "HealthStatus",
    "SnapshotManager",
    "VersionManager",
]

