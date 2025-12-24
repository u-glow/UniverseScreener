"""
Data Context - In-Memory Data Container.

The DataContext holds all loaded data for a screening run.

Design Notes:
    - Supports eager (batch) and lazy loading modes
    - Tracks memory usage for health monitoring
    - Provides warning when data size exceeds threshold
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, Dict, List, Optional

from universe_screener.domain.entities import Asset
from universe_screener.domain.value_objects import MarketData, QualityMetrics

logger = logging.getLogger(__name__)

# Memory threshold for warning (2 GB default)
DEFAULT_SIZE_WARNING_BYTES = 2 * 1024 * 1024 * 1024


class DataContext:
    """
    In-memory container for screening data.
    
    Supports two modes:
        - Eager (default): All data loaded upfront
        - Lazy: Data loaded on first access via loader callbacks
    
    Memory Monitoring:
        - Tracks estimated size in bytes
        - Logs warning when threshold exceeded
    """

    def __init__(
        self,
        assets: List[Asset],
        market_data: Optional[Dict[str, List[MarketData]]] = None,
        metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        quality_metrics: Optional[Dict[str, QualityMetrics]] = None,
        *,
        lazy_loading: bool = False,
        market_data_loader: Optional[Callable[[str], List[MarketData]]] = None,
        metadata_loader: Optional[Callable[[str], Dict[str, Any]]] = None,
        size_warning_bytes: int = DEFAULT_SIZE_WARNING_BYTES,
    ) -> None:
        """
        Initialize data context.

        Args:
            assets: All assets to be filtered
            market_data: OHLCV data by asset symbol (optional in lazy mode)
            metadata: Metadata by asset symbol (optional in lazy mode)
            quality_metrics: Quality metrics by asset symbol
            lazy_loading: If True, use loaders instead of preloaded data
            market_data_loader: Callback to load market data by symbol
            metadata_loader: Callback to load metadata by symbol
            size_warning_bytes: Threshold for memory warning
        """
        self._assets = assets
        self._assets_by_symbol = {a.symbol: a for a in assets}
        self._market_data = market_data or {}
        self._metadata = metadata or {}
        self._quality_metrics = quality_metrics or {}
        
        # Lazy loading support
        self._lazy_loading = lazy_loading
        self._market_data_loader = market_data_loader
        self._metadata_loader = metadata_loader
        self._size_warning_bytes = size_warning_bytes
        
        # Track which symbols have been lazily loaded
        self._loaded_market_data: set = set()
        self._loaded_metadata: set = set()
        
        # Check size and warn if needed (only for eager loading)
        if not lazy_loading:
            self._check_size_warning()

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
        
        In lazy mode, loads data on first access.

        Args:
            symbol: Asset symbol

        Returns:
            List of MarketData points, empty if not found
        """
        # Lazy loading
        if (
            self._lazy_loading
            and symbol not in self._loaded_market_data
            and self._market_data_loader is not None
        ):
            try:
                data = self._market_data_loader(symbol)
                self._market_data[symbol] = data
                self._loaded_market_data.add(symbol)
                logger.debug(f"Lazy loaded market data for {symbol}: {len(data)} records")
            except Exception as e:
                logger.warning(f"Failed to lazy load market data for {symbol}: {e}")
                return []
        
        return self._market_data.get(symbol, [])

    def get_metadata(self, symbol: str) -> Dict[str, Any]:
        """
        Get metadata for an asset.
        
        In lazy mode, loads data on first access.

        Args:
            symbol: Asset symbol

        Returns:
            Metadata dict, empty if not found
        """
        # Lazy loading
        if (
            self._lazy_loading
            and symbol not in self._loaded_metadata
            and self._metadata_loader is not None
        ):
            try:
                data = self._metadata_loader(symbol)
                self._metadata[symbol] = data
                self._loaded_metadata.add(symbol)
                logger.debug(f"Lazy loaded metadata for {symbol}")
            except Exception as e:
                logger.warning(f"Failed to lazy load metadata for {symbol}: {e}")
                return {}
        
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

    @property
    def size_mb(self) -> float:
        """Estimated size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    @property
    def is_lazy(self) -> bool:
        """Check if lazy loading is enabled."""
        return self._lazy_loading

    def _check_size_warning(self) -> None:
        """Log warning if data size exceeds threshold."""
        size = self.size_bytes
        if size > self._size_warning_bytes:
            size_gb = size / (1024 * 1024 * 1024)
            threshold_gb = self._size_warning_bytes / (1024 * 1024 * 1024)
            logger.warning(
                f"DataContext size ({size_gb:.2f} GB) exceeds threshold "
                f"({threshold_gb:.2f} GB). Consider using lazy_loading=True."
            )

    def preload_all(self) -> None:
        """
        Preload all data in lazy mode.
        
        Useful when you want to load everything upfront after
        switching to lazy mode.
        """
        if not self._lazy_loading:
            return
            
        for asset in self._assets:
            self.get_market_data(asset.symbol)
            self.get_metadata(asset.symbol)
        
        # Check size after full load
        self._check_size_warning()

    def __len__(self) -> int:
        """Number of assets in the context."""
        return len(self._assets)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"DataContext(assets={len(self._assets)}, "
            f"market_data_symbols={len(self._market_data)}, "
            f"lazy={self._lazy_loading}, "
            f"size_mb={self.size_mb:.2f})"
        )
