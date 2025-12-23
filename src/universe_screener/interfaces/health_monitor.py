"""
Health Monitor Protocol.

Defines the abstract interface for system health monitoring.
The health monitor performs pre-flight and post-processing checks
to detect anomalies and potential issues.

The health monitor is responsible for:
    - Pre-screening checks (RAM, provider availability)
    - Post-load checks (data context size)
    - Post-filtering checks (result sanity)
    - Raising alerts on anomalies

Design Notes:
    - Configurable thresholds
    - Non-blocking where possible
    - Clear severity levels
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing import List

    from universe_screener.domain.entities import Asset
    from universe_screener.pipeline.data_context import DataContext

# TODO: Implement
#
# @runtime_checkable
# class HealthMonitor(Protocol):
#     """Abstract interface for health monitoring."""
#
#     def check_pre_screening(self) -> HealthCheckResult:
#         """
#         Perform pre-screening health checks.
#
#         Checks:
#             - RAM available
#             - Provider reachable
#             - Config valid
#
#         Returns:
#             HealthCheckResult with status and details
#         """
#         ...
#
#     def check_post_load(
#         self,
#         context: DataContext,
#     ) -> HealthCheckResult:
#         """
#         Perform post-load health checks.
#
#         Checks:
#             - DataContext size within limits
#             - Memory usage acceptable
#
#         Args:
#             context: Loaded data context
#
#         Returns:
#             HealthCheckResult with status and details
#         """
#         ...
#
#     def check_post_filtering(
#         self,
#         input_assets: List[Asset],
#         output_assets: List[Asset],
#     ) -> HealthCheckResult:
#         """
#         Perform post-filtering health checks.
#
#         Checks:
#             - Output not empty
#             - Reduction ratio plausible
#
#         Args:
#             input_assets: Original asset list
#             output_assets: Filtered asset list
#
#         Returns:
#             HealthCheckResult with status and details
#         """
#         ...
#
#
# class HealthCheckResult(BaseModel):
#     """Result of a health check."""
#     status: str  # OK, WARNING, CRITICAL
#     checks: Dict[str, bool]
#     messages: List[str]

