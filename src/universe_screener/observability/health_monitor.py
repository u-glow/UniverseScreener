"""
Health Monitor - System Health Checks.

Provides health checks at key pipeline stages:
    - Pre-screening: System resources available
    - Post-load: DataContext size within limits
    - Post-filtering: Results plausible

Design Notes:
    - Configurable thresholds from ScreeningConfig
    - Returns HealthStatus with pass/fail and details
    - Logs anomalies via ObservabilityManager if provided
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from universe_screener.pipeline.data_context import DataContext
    from universe_screener.domain.entities import ScreeningResult

logger = logging.getLogger(__name__)

# Try to import psutil for RAM monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class HealthCheckResult(Enum):
    """Result of a health check."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    result: HealthCheckResult
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class HealthStatus:
    """Overall health status."""
    is_healthy: bool
    checks: List[HealthCheck] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        from datetime import datetime
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def add_check(self, check: HealthCheck) -> None:
        """Add a health check result."""
        self.checks.append(check)
        if check.result == HealthCheckResult.FAIL:
            self.is_healthy = False

    @property
    def summary(self) -> Dict[str, Any]:
        """Get summary of health status."""
        return {
            "is_healthy": self.is_healthy,
            "timestamp": self.timestamp,
            "checks": {
                c.name: {
                    "result": c.result.value,
                    "message": c.message,
                    "value": c.value,
                    "threshold": c.threshold,
                }
                for c in self.checks
            },
        }


@dataclass
class HealthMonitorConfig:
    """Configuration for health monitoring."""
    # RAM thresholds
    max_ram_usage_pct: float = 80.0
    warn_ram_usage_pct: float = 70.0

    # DataContext thresholds
    max_context_size_mb: float = 2000.0
    warn_context_size_mb: float = 1500.0

    # Output thresholds
    min_output_universe_size: int = 10
    max_reduction_ratio: float = 0.99  # Max 99% filtered out

    # Enable/disable checks
    enabled: bool = True
    check_ram: bool = True
    check_context_size: bool = True
    check_output_size: bool = True
    check_reduction_ratio: bool = True


class HealthMonitor:
    """
    Monitor system health at key pipeline stages.

    Performs checks:
        - Pre-screening: RAM usage
        - Post-load: DataContext size
        - Post-filtering: Output size, reduction ratio
    """

    def __init__(
        self,
        config: Optional[HealthMonitorConfig] = None,
        observability: Optional[Any] = None,
    ) -> None:
        """
        Initialize health monitor.

        Args:
            config: Health monitoring configuration
            observability: ObservabilityManager for logging (optional)
        """
        self.config = config or HealthMonitorConfig()
        self.observability = observability

    def check_pre_screening(self) -> HealthStatus:
        """
        Check system health before screening.

        Checks:
            - RAM usage below threshold

        Returns:
            HealthStatus with check results
        """
        status = HealthStatus(is_healthy=True)

        if not self.config.enabled:
            return status

        # Check RAM usage
        if self.config.check_ram:
            ram_check = self._check_ram_usage()
            status.add_check(ram_check)
            if ram_check.result != HealthCheckResult.PASS:
                self._log_anomaly(ram_check)

        return status

    def check_post_load(self, context: "DataContext") -> HealthStatus:
        """
        Check health after data loading.

        Args:
            context: Loaded DataContext

        Checks:
            - DataContext size within limits

        Returns:
            HealthStatus with check results
        """
        status = HealthStatus(is_healthy=True)

        if not self.config.enabled:
            return status

        # Check context size
        if self.config.check_context_size:
            size_check = self._check_context_size(context)
            status.add_check(size_check)
            if size_check.result != HealthCheckResult.PASS:
                self._log_anomaly(size_check)

        return status

    def check_post_filtering(self, result: "ScreeningResult") -> HealthStatus:
        """
        Check health after filtering.

        Args:
            result: Screening result

        Checks:
            - Output universe not empty
            - Reduction ratio plausible

        Returns:
            HealthStatus with check results
        """
        status = HealthStatus(is_healthy=True)

        if not self.config.enabled:
            return status

        # Check output size
        if self.config.check_output_size:
            output_check = self._check_output_size(result)
            status.add_check(output_check)
            if output_check.result != HealthCheckResult.PASS:
                self._log_anomaly(output_check)

        # Check reduction ratio
        if self.config.check_reduction_ratio:
            ratio_check = self._check_reduction_ratio(result)
            status.add_check(ratio_check)
            if ratio_check.result != HealthCheckResult.PASS:
                self._log_anomaly(ratio_check)

        return status

    def _check_ram_usage(self) -> HealthCheck:
        """Check current RAM usage."""
        if not PSUTIL_AVAILABLE:
            return HealthCheck(
                name="ram_usage",
                result=HealthCheckResult.PASS,
                message="psutil not available, skipping RAM check",
            )

        ram_pct = psutil.virtual_memory().percent

        if ram_pct >= self.config.max_ram_usage_pct:
            return HealthCheck(
                name="ram_usage",
                result=HealthCheckResult.FAIL,
                message=f"RAM usage {ram_pct:.1f}% exceeds max {self.config.max_ram_usage_pct}%",
                value=ram_pct,
                threshold=self.config.max_ram_usage_pct,
            )
        elif ram_pct >= self.config.warn_ram_usage_pct:
            return HealthCheck(
                name="ram_usage",
                result=HealthCheckResult.WARN,
                message=f"RAM usage {ram_pct:.1f}% approaching limit",
                value=ram_pct,
                threshold=self.config.warn_ram_usage_pct,
            )
        else:
            return HealthCheck(
                name="ram_usage",
                result=HealthCheckResult.PASS,
                message=f"RAM usage {ram_pct:.1f}% OK",
                value=ram_pct,
                threshold=self.config.max_ram_usage_pct,
            )

    def _check_context_size(self, context: "DataContext") -> HealthCheck:
        """Check DataContext memory size."""
        # Estimate size in MB
        size_mb = self._estimate_context_size_mb(context)

        if size_mb >= self.config.max_context_size_mb:
            return HealthCheck(
                name="context_size",
                result=HealthCheckResult.FAIL,
                message=f"DataContext {size_mb:.1f}MB exceeds max {self.config.max_context_size_mb}MB",
                value=size_mb,
                threshold=self.config.max_context_size_mb,
            )
        elif size_mb >= self.config.warn_context_size_mb:
            return HealthCheck(
                name="context_size",
                result=HealthCheckResult.WARN,
                message=f"DataContext {size_mb:.1f}MB approaching limit",
                value=size_mb,
                threshold=self.config.warn_context_size_mb,
            )
        else:
            return HealthCheck(
                name="context_size",
                result=HealthCheckResult.PASS,
                message=f"DataContext {size_mb:.1f}MB OK",
                value=size_mb,
                threshold=self.config.max_context_size_mb,
            )

    def _estimate_context_size_mb(self, context: "DataContext") -> float:
        """Estimate DataContext size in MB."""
        try:
            # Use sys.getsizeof for rough estimate
            total_bytes = sys.getsizeof(context)

            # Add estimates for contained data
            if hasattr(context, "_market_data"):
                total_bytes += sys.getsizeof(context._market_data)
            if hasattr(context, "_metadata"):
                total_bytes += sys.getsizeof(context._metadata)
            if hasattr(context, "_quality_metrics"):
                total_bytes += sys.getsizeof(context._quality_metrics)
            if hasattr(context, "assets"):
                total_bytes += sys.getsizeof(context.assets)

            return total_bytes / (1024 * 1024)
        except Exception:
            return 0.0

    def _check_output_size(self, result: "ScreeningResult") -> HealthCheck:
        """Check output universe size."""
        output_size = len(result.output_universe)

        if output_size == 0:
            return HealthCheck(
                name="output_size",
                result=HealthCheckResult.FAIL,
                message="Output universe is empty!",
                value=float(output_size),
                threshold=float(self.config.min_output_universe_size),
            )
        elif output_size < self.config.min_output_universe_size:
            return HealthCheck(
                name="output_size",
                result=HealthCheckResult.WARN,
                message=f"Output universe ({output_size}) below minimum ({self.config.min_output_universe_size})",
                value=float(output_size),
                threshold=float(self.config.min_output_universe_size),
            )
        else:
            return HealthCheck(
                name="output_size",
                result=HealthCheckResult.PASS,
                message=f"Output universe size {output_size} OK",
                value=float(output_size),
                threshold=float(self.config.min_output_universe_size),
            )

    def _check_reduction_ratio(self, result: "ScreeningResult") -> HealthCheck:
        """Check if reduction ratio is plausible."""
        input_size = len(result.input_universe)
        output_size = len(result.output_universe)

        if input_size == 0:
            return HealthCheck(
                name="reduction_ratio",
                result=HealthCheckResult.WARN,
                message="Input universe is empty, cannot calculate ratio",
                value=0.0,
                threshold=self.config.max_reduction_ratio,
            )

        reduction_ratio = 1.0 - (output_size / input_size)

        if reduction_ratio > self.config.max_reduction_ratio:
            return HealthCheck(
                name="reduction_ratio",
                result=HealthCheckResult.WARN,
                message=f"Reduction ratio {reduction_ratio:.1%} exceeds max {self.config.max_reduction_ratio:.1%}",
                value=reduction_ratio,
                threshold=self.config.max_reduction_ratio,
            )
        else:
            return HealthCheck(
                name="reduction_ratio",
                result=HealthCheckResult.PASS,
                message=f"Reduction ratio {reduction_ratio:.1%} OK",
                value=reduction_ratio,
                threshold=self.config.max_reduction_ratio,
            )

    def _log_anomaly(self, check: HealthCheck) -> None:
        """Log health check anomaly."""
        severity = "ERROR" if check.result == HealthCheckResult.FAIL else "WARNING"

        if self.observability:
            self.observability.log_anomaly(
                check.message,
                severity,
                context={
                    "check_name": check.name,
                    "value": check.value,
                    "threshold": check.threshold,
                },
            )
        else:
            log_fn = logger.error if severity == "ERROR" else logger.warning
            log_fn(f"Health check {check.name}: {check.message}")

