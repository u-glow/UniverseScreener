"""
Audit Logger Protocol.

Defines the abstract interface for audit logging. The audit logger
tracks all filtering decisions for compliance, debugging, and
backtesting validation.

The audit logger is responsible for:
    - Logging stage start/end events
    - Logging individual asset filter decisions
    - Logging anomalies and warnings
    - Maintaining correlation across a screening run

Design Notes:
    - Structured logging (JSON format recommended)
    - Correlation ID propagation for tracing
    - No side effects on filtering logic
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing import Any, Dict, Optional

    from universe_screener.domain.entities import Asset

# TODO: Implement
#
# @runtime_checkable
# class AuditLogger(Protocol):
#     """Abstract interface for audit logging."""
#
#     def set_correlation_id(self, correlation_id: str) -> None:
#         """Set correlation ID for subsequent log entries."""
#         ...
#
#     def log_stage_start(
#         self,
#         stage_name: str,
#         input_count: int,
#         metadata: Optional[Dict[str, Any]] = None,
#     ) -> None:
#         """
#         Log the start of a filter stage.
#
#         Args:
#             stage_name: Name of the filter stage
#             input_count: Number of assets entering the stage
#             metadata: Optional additional context
#         """
#         ...
#
#     def log_stage_end(
#         self,
#         stage_name: str,
#         output_count: int,
#         duration_seconds: float,
#         metadata: Optional[Dict[str, Any]] = None,
#     ) -> None:
#         """
#         Log the end of a filter stage.
#
#         Args:
#             stage_name: Name of the filter stage
#             output_count: Number of assets passing the stage
#             duration_seconds: Time taken for the stage
#             metadata: Optional additional context
#         """
#         ...
#
#     def log_asset_filtered(
#         self,
#         asset: Asset,
#         stage_name: str,
#         reason: str,
#     ) -> None:
#         """
#         Log that an asset was filtered out.
#
#         Args:
#             asset: The filtered asset
#             stage_name: Which stage filtered it
#             reason: Human-readable rejection reason
#         """
#         ...
#
#     def log_anomaly(
#         self,
#         message: str,
#         severity: str,
#         context: Optional[Dict[str, Any]] = None,
#     ) -> None:
#         """
#         Log an anomaly or warning.
#
#         Args:
#             message: Description of the anomaly
#             severity: INFO, WARNING, or CRITICAL
#             context: Optional additional context
#         """
#         ...

