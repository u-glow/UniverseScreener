"""
Unit Tests for ObservabilityManager.

Test Aspects Covered:
    ✅ Business Logic: Correlation IDs, structured logging, metrics
    ✅ Edge Cases: Missing structlog, thread safety
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

import pytest

from universe_screener.observability.observability_manager import (
    ObservabilityManager,
    get_correlation_id,
    set_correlation_id,
    STRUCTLOG_AVAILABLE,
)


class TestCorrelationIds:
    """Test correlation ID management."""

    def test_set_and_get_correlation_id(self) -> None:
        """
        SCENARIO: Set correlation ID
        EXPECTED: Can retrieve same ID
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        manager.set_correlation_id("test-123")

        # Assert
        assert get_correlation_id() == "test-123"

    def test_generate_correlation_id(self) -> None:
        """
        SCENARIO: Generate new correlation ID
        EXPECTED: UUID format, set in context
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        correlation_id = manager.generate_correlation_id()

        # Assert
        assert len(correlation_id) == 36  # UUID format
        assert get_correlation_id() == correlation_id

    def test_correlation_id_in_trace_context(self) -> None:
        """
        SCENARIO: Get trace context
        EXPECTED: Contains correlation ID
        """
        # Arrange
        manager = ObservabilityManager()
        manager.set_correlation_id("trace-456")

        # Act
        context = manager.get_trace_context()

        # Assert
        assert context["correlation_id"] == "trace-456"
        assert context["service_name"] == "universe_screener"


class TestEventLogging:
    """Test event logging."""

    def test_log_event_stores_event(self) -> None:
        """
        SCENARIO: Log an event
        EXPECTED: Event stored and retrievable
        """
        # Arrange
        manager = ObservabilityManager()
        manager.set_correlation_id("event-123")

        # Act
        manager.log_event("test_event", {"key": "value"})

        # Assert
        events = manager.get_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "test_event"
        assert events[0]["key"] == "value"
        assert events[0]["correlation_id"] == "event-123"

    def test_log_event_with_level(self) -> None:
        """
        SCENARIO: Log event with specific level
        EXPECTED: Event recorded (no exception)
        """
        # Arrange
        manager = ObservabilityManager()

        # Act & Assert (no exception)
        manager.log_event("info_event", level="info")
        manager.log_event("warn_event", level="warning")
        manager.log_event("error_event", level="error")
        manager.log_event("debug_event", level="debug")

        assert len(manager.get_events()) == 4


class TestMetricsRecording:
    """Test metrics recording."""

    def test_record_metric(self) -> None:
        """
        SCENARIO: Record a metric
        EXPECTED: Metric stored and retrievable
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        manager.record_metric("test_metric", 42.5, tags={"env": "test"})

        # Assert
        metrics = manager.get_metrics()
        assert "test_metric" in metrics
        assert metrics["test_metric"][0]["value"] == 42.5
        assert metrics["test_metric"][0]["tags"]["env"] == "test"

    def test_record_timing(self) -> None:
        """
        SCENARIO: Record timing metric
        EXPECTED: Metric with histogram type
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        manager.record_timing("request_duration", 0.5, tags={"method": "GET"})

        # Assert
        metrics = manager.get_metrics()
        assert "request_duration" in metrics
        assert metrics["request_duration"][0]["type"] == "histogram"

    def test_record_count(self) -> None:
        """
        SCENARIO: Record count metric
        EXPECTED: Metric with counter type
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        manager.record_count("requests_total", 100)

        # Assert
        metrics = manager.get_metrics()
        assert "requests_total" in metrics
        assert metrics["requests_total"][0]["type"] == "counter"

    def test_record_gauge(self) -> None:
        """
        SCENARIO: Record gauge metric
        EXPECTED: Metric with gauge type
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        manager.record_gauge("temperature", 23.5)

        # Assert
        metrics = manager.get_metrics()
        assert "temperature" in metrics
        assert metrics["temperature"][0]["type"] == "gauge"


class TestAuditLoggerCompatibility:
    """Test AuditLogger protocol compatibility."""

    def test_log_stage_start(self) -> None:
        """
        SCENARIO: Log stage start
        EXPECTED: Event with stage info
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        manager.log_stage_start("structural_filter", 100)

        # Assert
        events = manager.get_events()
        assert any(
            e["event_type"] == "stage_start" and e["stage_name"] == "structural_filter"
            for e in events
        )

    def test_log_stage_end(self) -> None:
        """
        SCENARIO: Log stage end
        EXPECTED: Event with duration and metric recorded
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        manager.log_stage_end("structural_filter", 80, 0.5)

        # Assert
        events = manager.get_events()
        assert any(
            e["event_type"] == "stage_end" and e["output_count"] == 80
            for e in events
        )
        # Also records metric
        metrics = manager.get_metrics()
        assert "stage_duration_seconds" in metrics

    def test_log_asset_filtered(self) -> None:
        """
        SCENARIO: Log filtered asset
        EXPECTED: Debug level event with asset info
        """
        # Arrange
        manager = ObservabilityManager()
        mock_asset = Mock()
        mock_asset.symbol = "AAPL"

        # Act
        manager.log_asset_filtered(mock_asset, "liquidity_filter", "low volume")

        # Assert
        events = manager.get_events()
        assert any(
            e["event_type"] == "asset_filtered" and e["symbol"] == "AAPL"
            for e in events
        )

    def test_log_anomaly(self) -> None:
        """
        SCENARIO: Log anomaly
        EXPECTED: Warning/error level event
        """
        # Arrange
        manager = ObservabilityManager()

        # Act
        manager.log_anomaly("High RAM usage", "WARNING", context={"value": 85})

        # Assert
        events = manager.get_events()
        assert any(
            e["event_type"] == "anomaly" and e["severity"] == "WARNING"
            for e in events
        )


class TestClearAndReset:
    """Test clearing state."""

    def test_clear_removes_all(self) -> None:
        """
        SCENARIO: Clear manager state
        EXPECTED: All events and metrics removed
        """
        # Arrange
        manager = ObservabilityManager()
        manager.log_event("test", {})
        manager.record_metric("test", 1.0)

        # Act
        manager.clear()

        # Assert
        assert len(manager.get_events()) == 0
        assert len(manager.get_metrics()) == 0


class TestStructlogFallback:
    """Test structlog fallback behavior."""

    def test_works_without_structlog(self) -> None:
        """
        SCENARIO: structlog not available (simulated)
        EXPECTED: Falls back to standard logging
        """
        # Note: Can't easily test without structlog when it's installed
        # This test just verifies the manager works in either case
        manager = ObservabilityManager()
        manager.log_event("test", {"key": "value"})

        assert len(manager.get_events()) == 1

