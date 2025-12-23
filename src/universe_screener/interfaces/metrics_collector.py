"""
Metrics Collector Protocol.

Defines the abstract interface for performance metrics collection.
The metrics collector tracks execution times, reduction ratios,
memory usage, and other operational metrics.

The metrics collector is responsible for:
    - Recording timing metrics (histograms)
    - Recording count metrics (counters)
    - Recording gauge metrics (current values)
    - Exporting in OpenMetrics format (future)

Design Notes:
    - Non-blocking metric recording
    - Tag/label support for dimensionality
    - Compatible with Prometheus/OpenMetrics
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing import Dict, Optional

# TODO: Implement
#
# @runtime_checkable
# class MetricsCollector(Protocol):
#     """Abstract interface for metrics collection."""
#
#     def record_timing(
#         self,
#         name: str,
#         duration_seconds: float,
#         tags: Optional[Dict[str, str]] = None,
#     ) -> None:
#         """
#         Record a timing metric (histogram).
#
#         Args:
#             name: Metric name (e.g., "screening_duration_seconds")
#             duration_seconds: Duration value
#             tags: Optional dimension tags
#         """
#         ...
#
#     def record_count(
#         self,
#         name: str,
#         value: int,
#         tags: Optional[Dict[str, str]] = None,
#     ) -> None:
#         """
#         Record a count metric (counter).
#
#         Args:
#             name: Metric name (e.g., "assets_filtered_total")
#             value: Count value
#             tags: Optional dimension tags
#         """
#         ...
#
#     def record_gauge(
#         self,
#         name: str,
#         value: float,
#         tags: Optional[Dict[str, str]] = None,
#     ) -> None:
#         """
#         Record a gauge metric (current value).
#
#         Args:
#             name: Metric name (e.g., "data_context_size_bytes")
#             value: Current value
#             tags: Optional dimension tags
#         """
#         ...
#
#     def get_metrics(self) -> Dict[str, Any]:
#         """
#         Get all collected metrics.
#
#         Returns:
#             Dict of metric name to values
#         """
#         ...

