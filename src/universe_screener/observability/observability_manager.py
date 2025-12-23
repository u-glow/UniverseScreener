"""
Observability Manager - Unified Logging, Metrics, and Tracing.

Provides:
    - Structured JSON logging via structlog
    - Correlation ID propagation
    - Metrics recording
    - Trace context management

Design Notes:
    - Falls back to standard logging if structlog not available
    - Thread-safe correlation ID storage
    - Compatible with existing AuditLogger protocol
"""

from __future__ import annotations

import logging
import threading
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, List, Optional

# Try to import structlog, fallback to standard logging
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

# Context variable for correlation ID (thread-safe)
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    _correlation_id.set(correlation_id)


class ObservabilityManager:
    """
    Unified observability: logging, metrics, and tracing.

    Provides structured logging with correlation IDs and metrics recording.
    Falls back to standard logging if structlog is not installed.
    """

    def __init__(
        self,
        service_name: str = "universe_screener",
        use_json: bool = True,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Initialize observability manager.

        Args:
            service_name: Service name for log entries
            use_json: Use JSON output (only with structlog)
            log_level: Logging level
        """
        self.service_name = service_name
        self.use_json = use_json
        self.log_level = log_level
        self._metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

        # Configure logger
        if STRUCTLOG_AVAILABLE:
            self._configure_structlog()
            self._logger = structlog.get_logger(service_name)
        else:
            self._configure_stdlib_logging()
            self._logger = logging.getLogger(service_name)

    def _configure_structlog(self) -> None:
        """Configure structlog for structured logging."""
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
        ]

        if self.use_json:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(self.log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def _configure_stdlib_logging(self) -> None:
        """Configure standard library logging as fallback."""
        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def set_correlation_id(self, correlation_id: str) -> None:
        """
        Set correlation ID for current context.

        Args:
            correlation_id: Unique ID for request tracing
        """
        set_correlation_id(correlation_id)
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    def generate_correlation_id(self) -> str:
        """Generate and set a new correlation ID."""
        correlation_id = str(uuid.uuid4())
        self.set_correlation_id(correlation_id)
        return correlation_id

    def log_event(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        level: str = "info",
    ) -> None:
        """
        Log a structured event.

        Args:
            event_type: Type of event (e.g., "stage_start", "asset_filtered")
            data: Additional event data
            level: Log level (debug, info, warning, error)
        """
        event_data = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "correlation_id": get_correlation_id(),
            **(data or {}),
        }

        # Store event
        with self._lock:
            self._events.append(event_data)

        # Log via logger
        log_method = getattr(self._logger, level.lower(), self._logger.info)
        if STRUCTLOG_AVAILABLE:
            log_method(event_type, **event_data)
        else:
            log_method(f"{event_type}: {event_data}")

    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        metric_type: str = "gauge",
    ) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            tags: Additional tags/labels
            metric_type: Type (gauge, counter, histogram)
        """
        metric_entry = {
            "timestamp": datetime.now().isoformat(),
            "value": value,
            "tags": tags or {},
            "type": metric_type,
            "correlation_id": get_correlation_id(),
        }

        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(metric_entry)

    def get_trace_context(self) -> Dict[str, Any]:
        """
        Get current trace context.

        Returns:
            Dict with correlation_id and service info
        """
        return {
            "correlation_id": get_correlation_id(),
            "service_name": self.service_name,
            "timestamp": datetime.now().isoformat(),
        }

    def get_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all recorded metrics."""
        with self._lock:
            return dict(self._metrics)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all recorded events."""
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        """Clear all recorded metrics and events."""
        with self._lock:
            self._metrics.clear()
            self._events.clear()

    # =========================================================================
    # AuditLogger Protocol Compatibility
    # =========================================================================

    def log_stage_start(
        self,
        stage_name: str,
        input_count: int,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Log start of a pipeline stage (AuditLogger compatible)."""
        self.log_event(
            "stage_start",
            {
                "stage_name": stage_name,
                "input_count": input_count,
                **(metadata or {}),
            },
        )

    def log_stage_end(
        self,
        stage_name: str,
        output_count: int,
        duration_seconds: float,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Log end of a pipeline stage (AuditLogger compatible)."""
        self.log_event(
            "stage_end",
            {
                "stage_name": stage_name,
                "output_count": output_count,
                "duration_seconds": duration_seconds,
                **(metadata or {}),
            },
        )
        self.record_metric(
            f"stage_duration_seconds",
            duration_seconds,
            tags={"stage": stage_name},
        )

    def log_asset_filtered(
        self,
        asset: Any,
        stage_name: str,
        reason: str,
    ) -> None:
        """Log filtered asset (AuditLogger compatible)."""
        self.log_event(
            "asset_filtered",
            {
                "symbol": getattr(asset, "symbol", str(asset)),
                "stage_name": stage_name,
                "reason": reason,
            },
            level="debug",
        )

    def log_anomaly(
        self,
        message: str,
        severity: str,
        context: Optional[Dict] = None,
    ) -> None:
        """Log an anomaly (AuditLogger compatible)."""
        level = "warning" if severity.upper() == "WARNING" else "error"
        self.log_event(
            "anomaly",
            {
                "message": message,
                "severity": severity,
                **(context or {}),
            },
            level=level,
        )

    # =========================================================================
    # MetricsCollector Protocol Compatibility
    # =========================================================================

    def record_timing(
        self,
        name: str,
        duration_seconds: float,
        tags: Optional[Dict] = None,
    ) -> None:
        """Record timing metric (MetricsCollector compatible)."""
        self.record_metric(name, duration_seconds, tags, metric_type="histogram")

    def record_count(
        self,
        name: str,
        value: int,
        tags: Optional[Dict] = None,
    ) -> None:
        """Record count metric (MetricsCollector compatible)."""
        self.record_metric(name, float(value), tags, metric_type="counter")

    def record_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict] = None,
    ) -> None:
        """Record gauge metric (MetricsCollector compatible)."""
        self.record_metric(name, value, tags, metric_type="gauge")

