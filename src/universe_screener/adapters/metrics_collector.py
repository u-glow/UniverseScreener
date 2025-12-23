"""
In-Memory Metrics Collector.

A simple metrics collector that stores metrics in memory.
"""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional


class InMemoryMetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = Lock()

    def record_timing(
        self,
        name: str,
        duration_seconds: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a timing metric."""
        with self._lock:
            self._record(name, "timing", duration_seconds, tags)

    def record_count(
        self,
        name: str,
        value: int,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a count metric."""
        with self._lock:
            self._record(name, "count", value, tags)

    def record_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a gauge metric."""
        with self._lock:
            self._record(name, "gauge", value, tags)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self._lock:
            # Return a summary instead of raw data
            summary = {}
            for name, entries in self._metrics.items():
                if entries:
                    values = [e["value"] for e in entries]
                    summary[name] = {
                        "count": len(values),
                        "total": sum(values) if isinstance(values[0], (int, float)) else None,
                        "last": values[-1],
                    }
            return summary

    def clear(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()

    def _record(
        self,
        name: str,
        metric_type: str,
        value: Any,
        tags: Optional[Dict[str, str]],
    ) -> None:
        """Internal recording method."""
        if name not in self._metrics:
            self._metrics[name] = []

        self._metrics[name].append(
            {
                "type": metric_type,
                "value": value,
                "tags": tags or {},
                "timestamp": datetime.now().isoformat(),
            }
        )
