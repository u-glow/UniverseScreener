"""
Universe Provider Protocol.

Defines the abstract interface for data access. All data sources
(mock, database, API) must implement this protocol to be used
with the screening pipeline.

The provider is responsible for:
    - Fetching available assets for a given date
    - Bulk loading market data (OHLCV)
    - Bulk loading asset metadata
    - Checking data availability/quality

Design Notes:
    - Uses typing.Protocol for structural subtyping
    - All methods support batch operations for performance
    - Point-in-time semantics (no look-ahead bias)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Dict, List

    from universe_screener.domain.entities import Asset, AssetClass
    from universe_screener.domain.value_objects import MarketData, QualityMetrics

# TODO: Implement
#
# @runtime_checkable
# class UniverseProvider(Protocol):
#     """Abstract interface for data access."""
#
#     def get_assets(
#         self,
#         date: datetime,
#         asset_class: AssetClass,
#     ) -> List[Asset]:
#         """
#         Get all available assets for a given date and asset class.
#
#         Args:
#             date: Point-in-time for data snapshot
#             asset_class: Filter by asset class
#
#         Returns:
#             List of assets available at the given date
#         """
#         ...
#
#     def bulk_load_market_data(
#         self,
#         assets: List[Asset],
#         start_date: datetime,
#         end_date: datetime,
#     ) -> Dict[str, List[MarketData]]:
#         """
#         Batch load OHLCV data for multiple assets.
#
#         Args:
#             assets: Assets to load data for
#             start_date: Start of lookback window
#             end_date: End of lookback window
#
#         Returns:
#             Dict mapping asset symbol to list of market data points
#         """
#         ...
#
#     def bulk_load_metadata(
#         self,
#         assets: List[Asset],
#         date: datetime,
#     ) -> Dict[str, Dict[str, Any]]:
#         """
#         Batch load metadata for multiple assets.
#
#         Args:
#             assets: Assets to load metadata for
#             date: Point-in-time for metadata snapshot
#
#         Returns:
#             Dict mapping asset symbol to metadata dict
#         """
#         ...
#
#     def check_data_availability(
#         self,
#         assets: List[Asset],
#         date: datetime,
#         lookback_days: int,
#     ) -> Dict[str, QualityMetrics]:
#         """
#         Check data quality for multiple assets.
#
#         Args:
#             assets: Assets to check
#             date: Reference date
#             lookback_days: Number of days to check
#
#         Returns:
#             Dict mapping asset symbol to quality metrics
#         """
#         ...

