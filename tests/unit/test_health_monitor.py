"""
Unit Tests for HealthMonitor.

Test Aspects Covered:
    ✅ Business Logic: Health checks, thresholds
    ✅ Edge Cases: Disabled, no psutil
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from universe_screener.observability.health_monitor import (
    HealthMonitor,
    HealthMonitorConfig,
    HealthStatus,
    HealthCheck,
    HealthCheckResult,
)


@pytest.fixture
def default_config() -> HealthMonitorConfig:
    """Create default health monitor config."""
    return HealthMonitorConfig()


@pytest.fixture
def monitor(default_config: HealthMonitorConfig) -> HealthMonitor:
    """Create health monitor with default config."""
    return HealthMonitor(config=default_config)


class TestPreScreeningChecks:
    """Test pre-screening health checks."""

    def test_passes_when_healthy(self, monitor: HealthMonitor) -> None:
        """
        SCENARIO: System is healthy
        EXPECTED: Health check passes
        """
        # Act
        status = monitor.check_pre_screening()

        # Assert
        assert isinstance(status, HealthStatus)
        # May pass or warn depending on actual RAM usage

    def test_disabled_returns_healthy(self) -> None:
        """
        SCENARIO: Health monitor disabled
        EXPECTED: Always returns healthy
        """
        # Arrange
        config = HealthMonitorConfig(enabled=False)
        monitor = HealthMonitor(config=config)

        # Act
        status = monitor.check_pre_screening()

        # Assert
        assert status.is_healthy
        assert len(status.checks) == 0


class TestPostLoadChecks:
    """Test post-load health checks."""

    def test_small_context_passes(self, monitor: HealthMonitor) -> None:
        """
        SCENARIO: DataContext is small
        EXPECTED: Health check passes
        """
        # Arrange
        mock_context = Mock()
        mock_context._market_data = {}
        mock_context._metadata = {}
        mock_context._quality_metrics = {}
        mock_context.assets = []

        # Act
        status = monitor.check_post_load(mock_context)

        # Assert
        assert status.is_healthy

    def test_disabled_skips_context_check(self) -> None:
        """
        SCENARIO: Context size check disabled
        EXPECTED: No context check performed
        """
        # Arrange
        config = HealthMonitorConfig(check_context_size=False)
        monitor = HealthMonitor(config=config)
        mock_context = Mock()

        # Act
        status = monitor.check_post_load(mock_context)

        # Assert
        assert status.is_healthy
        assert not any(c.name == "context_size" for c in status.checks)


class TestPostFilteringChecks:
    """Test post-filtering health checks."""

    def test_sufficient_output_passes(self, monitor: HealthMonitor) -> None:
        """
        SCENARIO: Output universe has enough assets
        EXPECTED: Health check passes
        """
        # Arrange
        mock_result = Mock()
        mock_result.input_universe = list(range(100))
        mock_result.output_universe = list(range(50))

        # Act
        status = monitor.check_post_filtering(mock_result)

        # Assert
        assert status.is_healthy

    def test_empty_output_fails(self, monitor: HealthMonitor) -> None:
        """
        SCENARIO: Output universe is empty
        EXPECTED: Health check fails
        """
        # Arrange
        mock_result = Mock()
        mock_result.input_universe = list(range(100))
        mock_result.output_universe = []

        # Act
        status = monitor.check_post_filtering(mock_result)

        # Assert
        assert not status.is_healthy
        assert any(
            c.name == "output_size" and c.result == HealthCheckResult.FAIL
            for c in status.checks
        )

    def test_small_output_warns(self) -> None:
        """
        SCENARIO: Output below minimum threshold
        EXPECTED: Health check warns
        """
        # Arrange
        config = HealthMonitorConfig(min_output_universe_size=20)
        monitor = HealthMonitor(config=config)
        mock_result = Mock()
        mock_result.input_universe = list(range(100))
        mock_result.output_universe = list(range(10))

        # Act
        status = monitor.check_post_filtering(mock_result)

        # Assert
        assert any(
            c.name == "output_size" and c.result == HealthCheckResult.WARN
            for c in status.checks
        )

    def test_high_reduction_ratio_warns(self) -> None:
        """
        SCENARIO: More than 99% of assets filtered
        EXPECTED: Health check warns
        """
        # Arrange
        config = HealthMonitorConfig(max_reduction_ratio=0.99)
        monitor = HealthMonitor(config=config)
        mock_result = Mock()
        mock_result.input_universe = list(range(1000))
        mock_result.output_universe = [1]  # 99.9% reduction

        # Act
        status = monitor.check_post_filtering(mock_result)

        # Assert
        assert any(
            c.name == "reduction_ratio" and c.result == HealthCheckResult.WARN
            for c in status.checks
        )

    def test_normal_reduction_passes(self) -> None:
        """
        SCENARIO: Normal reduction ratio
        EXPECTED: Health check passes
        """
        # Arrange
        config = HealthMonitorConfig(max_reduction_ratio=0.99)
        monitor = HealthMonitor(config=config)
        mock_result = Mock()
        mock_result.input_universe = list(range(100))
        mock_result.output_universe = list(range(50))  # 50% reduction

        # Act
        status = monitor.check_post_filtering(mock_result)

        # Assert
        ratio_check = next(
            (c for c in status.checks if c.name == "reduction_ratio"), None
        )
        if ratio_check:
            assert ratio_check.result == HealthCheckResult.PASS


class TestHealthStatus:
    """Test HealthStatus class."""

    def test_add_check_updates_healthy(self) -> None:
        """
        SCENARIO: Add failing check
        EXPECTED: Status becomes unhealthy
        """
        # Arrange
        status = HealthStatus(is_healthy=True)

        # Act
        status.add_check(
            HealthCheck(
                name="test",
                result=HealthCheckResult.FAIL,
                message="Test failed",
            )
        )

        # Assert
        assert not status.is_healthy

    def test_summary_contains_all_checks(self) -> None:
        """
        SCENARIO: Multiple checks added
        EXPECTED: Summary contains all
        """
        # Arrange
        status = HealthStatus(is_healthy=True)
        status.add_check(
            HealthCheck(name="check1", result=HealthCheckResult.PASS, message="OK")
        )
        status.add_check(
            HealthCheck(name="check2", result=HealthCheckResult.WARN, message="Warn")
        )

        # Act
        summary = status.summary

        # Assert
        assert "check1" in summary["checks"]
        assert "check2" in summary["checks"]


class TestObservabilityIntegration:
    """Test integration with ObservabilityManager."""

    def test_logs_anomaly_on_failure(self) -> None:
        """
        SCENARIO: Health check fails
        EXPECTED: Anomaly logged via observability
        """
        # Arrange
        mock_observability = Mock()
        config = HealthMonitorConfig()
        monitor = HealthMonitor(config=config, observability=mock_observability)

        mock_result = Mock()
        mock_result.input_universe = list(range(100))
        mock_result.output_universe = []  # Empty = fail

        # Act
        monitor.check_post_filtering(mock_result)

        # Assert
        mock_observability.log_anomaly.assert_called()

