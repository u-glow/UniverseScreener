"""
Data Context - In-Memory Data Container.

The DataContext holds all loaded data for a screening run.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

from universe_screener.domain.entities import Asset
from universe_screener.domain.value_objects import MarketData, QualityMetrics


class DataContext:
    """In-memory container for screening data."""

    def __init__(
        self,
        assets: List[Asset],
        market_data: Dict[str, List[MarketData]],
        metadata: Dict[str, Dict[str, Any]],
        quality_metrics: Dict[str, QualityMetrics],
    ) -> None:
        """
        Initialize data context.

        Args:
            assets: All assets to be filtered
            market_data: OHLCV data by asset symbol
            metadata: Metadata by asset symbol
            quality_metrics: Quality metrics by asset symbol
        """
        self._assets = assets
        self._assets_by_symbol = {a.symbol: a for a in assets}
        self._market_data = market_data
        self._metadata = metadata
        self._quality_metrics = quality_metrics

    @property
    def assets(self) -> List[Asset]:
        """Get all assets in the context."""
        return self._assets

    def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get asset by symbol."""
        return self._assets_by_symbol.get(symbol)

    def get_assets_by_symbols(self, symbols: List[str]) -> List[Asset]:
        """Get multiple assets by their symbols."""
        return [
            self._assets_by_symbol[s]
            for s in symbols
            if s in self._assets_by_symbol
        ]

    def get_market_data(self, symbol: str) -> List[MarketData]:
        """
        Get market data for an asset.

        Args:
            symbol: Asset symbol

        Returns:
            List of MarketData points, empty if not found
        """
        return self._market_data.get(symbol, [])

    def get_metadata(self, symbol: str) -> Dict[str, Any]:
        """
        Get metadata for an asset.

        Args:
            symbol: Asset symbol

        Returns:
            Metadata dict, empty if not found
        """
        return self._metadata.get(symbol, {})

    def get_quality_metrics(self, symbol: str) -> Optional[QualityMetrics]:
        """
        Get quality metrics for an asset.

        Args:
            symbol: Asset symbol

        Returns:
            QualityMetrics or None if not found
        """
        return self._quality_metrics.get(symbol)

    @property
    def size_bytes(self) -> int:
        """Estimate memory size of the context in bytes."""
        # Rough estimation for health monitoring
        size = sys.getsizeof(self._assets)
        size += sys.getsizeof(self._market_data)
        for data_list in self._market_data.values():
            size += len(data_list) * 100  # ~100 bytes per MarketData
        size += sys.getsizeof(self._metadata)
        size += sys.getsizeof(self._quality_metrics)
        return size

    def __len__(self) -> int:
        """Number of assets in the context."""
        return len(self._assets)
