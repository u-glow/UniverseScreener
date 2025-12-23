"""
Console Audit Logger.

A simple audit logger that outputs to the console.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from universe_screener.domain.entities import Asset


class ConsoleAuditLogger:
    """Simple console-based audit logger."""

    def __init__(self, verbose: bool = True) -> None:
        """
        Initialize console logger.

        Args:
            verbose: If True, log all events. If False, only summaries.
        """
        self._verbose = verbose
        self._correlation_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for subsequent log entries."""
        self._correlation_id = correlation_id

    def log_stage_start(
        self,
        stage_name: str,
        input_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log the start of a filter stage."""
        if self._verbose:
            self._log("INFO", f"Starting {stage_name} with {input_count} assets")

    def log_stage_end(
        self,
        stage_name: str,
        output_count: int,
        duration_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log the end of a filter stage."""
        self._log(
            "INFO",
            f"Completed {stage_name}: {output_count} assets passed "
            f"({duration_seconds:.3f}s)",
        )

    def log_asset_filtered(
        self,
        asset: Asset,
        stage_name: str,
        reason: str,
    ) -> None:
        """Log that an asset was filtered out."""
        if self._verbose:
            self._log("DEBUG", f"{asset.symbol} filtered by {stage_name}: {reason}")

    def log_anomaly(
        self,
        message: str,
        severity: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an anomaly or warning."""
        self._log(severity, f"ANOMALY: {message}")

    def _log(self, level: str, message: str) -> None:
        """Internal logging method."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        corr_id = self._correlation_id[:8] if self._correlation_id else "--------"
        print(f"[{timestamp}] [{corr_id}] [{level:5}] {message}")
