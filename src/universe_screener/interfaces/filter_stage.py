"""
Filter Stage Protocol.

Defines the abstract interface for filter stages. Each filter stage
implements specific filtering logic (structural, liquidity, data quality)
while conforming to a common interface.

The filter stage is responsible for:
    - Applying filter logic to a list of assets
    - Returning filtered assets with rejection reasons
    - Providing stage metrics for observability

Design Notes:
    - Uses typing.Protocol for structural subtyping
    - Filters are stateless (all state via DataContext)
    - Configuration injected via constructor
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime
    from typing import List

    from universe_screener.domain.entities import Asset
    from universe_screener.domain.value_objects import FilterResult
    from universe_screener.pipeline.data_context import DataContext

# TODO: Implement
#
# @runtime_checkable
# class FilterStage(Protocol):
#     """Abstract interface for filter stages."""
#
#     @property
#     def name(self) -> str:
#         """Unique name of this filter stage."""
#         ...
#
#     def apply(
#         self,
#         assets: List[Asset],
#         date: datetime,
#         context: DataContext,
#     ) -> FilterResult:
#         """
#         Apply filter logic to assets.
#
#         Args:
#             assets: Assets to filter
#             date: Reference date for filtering
#             context: Data context with loaded market data
#
#         Returns:
#             FilterResult with passed/rejected assets and reasons
#         """
#         ...
#
#
# class LiquidityStrategy(Protocol):
#     """Strategy protocol for asset-class specific liquidity checks."""
#
#     def check_liquidity(
#         self,
#         asset: Asset,
#         market_data: List[MarketData],
#         config: LiquidityConfig,
#     ) -> tuple[bool, str]:
#         """
#         Check if asset meets liquidity requirements.
#
#         Args:
#             asset: Asset to check
#             market_data: Historical market data
#             config: Liquidity thresholds
#
#         Returns:
#             Tuple of (passes: bool, reason: str)
#         """
#         ...

