"""
Cached Universe Provider - Caching Wrapper for Universe Providers.

Wraps any UniverseProvider implementation to add caching for bulk operations.

Design Notes:
    - Decorator/Wrapper pattern
    - Caches bulk_load_market_data() and bulk_load_metadata()
    - Tracks cache hits via MetricsCollector
    - Thread-safe (uses CacheManager's lock)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from universe_screener.caching.cache_manager import CacheManager, CacheConfig
from universe_screener.domain.entities import Asset, AssetClass
from universe_screener.domain.value_objects import (
    MarketData,
    MarketDataDict,
    MetadataDict,
    QualityMetrics,
    QualityMetricsDict,
)

logger = logging.getLogger(__name__)


class UniverseProviderProtocol(Protocol):
    """Protocol for universe data providers."""

    def get_assets(self, date: datetime, asset_class: AssetClass) -> List[Asset]:
        """Get all assets for screening."""
        ...

    def bulk_load_market_data(
        self,
        assets: List[Asset],
        start_date: datetime,
        end_date: datetime,
    ) -> MarketDataDict:
        """Bulk load market data for all assets."""
        ...

    def bulk_load_metadata(
        self,
        assets: List[Asset],
        date: datetime,
    ) -> MetadataDict:
        """Bulk load metadata for all assets."""
        ...

    def check_data_availability(
        self,
        assets: List[Asset],
        date: datetime,
        lookback_days: int,
    ) -> QualityMetricsDict:
        """Check data quality for all assets."""
        ...


class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collection."""

    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric."""
        ...


class CachedUniverseProvider:
    """
    Caching wrapper for UniverseProvider implementations.
    
    Caches results from bulk operations to avoid redundant database/API calls.
    Tracks cache hits/misses via MetricsCollector.
    
    Usage:
        provider = DatabaseUniverseProvider(connection)
        cached_provider = CachedUniverseProvider(provider, cache_manager)
        
        # First call: cache miss, fetches from provider
        data = cached_provider.bulk_load_market_data(assets, start, end)
        
        # Second call with same params: cache hit
        data = cached_provider.bulk_load_market_data(assets, start, end)
    """

    def __init__(
        self,
        provider: UniverseProviderProtocol,
        cache_manager: Optional[CacheManager] = None,
        cache_config: Optional[CacheConfig] = None,
        metrics_collector: Optional[MetricsCollectorProtocol] = None,
    ) -> None:
        """
        Initialize cached provider.
        
        Args:
            provider: Underlying universe provider to wrap
            cache_manager: Cache manager instance (creates one if None)
            cache_config: Cache configuration (used if cache_manager is None)
            metrics_collector: Optional metrics collector for tracking
        """
        self.provider = provider
        self.cache = cache_manager or CacheManager(cache_config)
        self.metrics = metrics_collector
        
        # Track cache statistics per operation
        self._cache_hits: Dict[str, int] = {}
        self._cache_misses: Dict[str, int] = {}

    def get_assets(self, date: datetime, asset_class: AssetClass) -> List[Asset]:
        """
        Get all assets for screening.
        
        Note: Assets are NOT cached as they change frequently and
        should always reflect the latest state.
        
        Args:
            date: Reference date
            asset_class: Asset class to filter
            
        Returns:
            List of assets
        """
        return self.provider.get_assets(date, asset_class)

    def bulk_load_market_data(
        self,
        assets: List[Asset],
        start_date: datetime,
        end_date: datetime,
    ) -> MarketDataDict:
        """
        Bulk load market data with caching.
        
        Args:
            assets: Assets to load data for
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Market data by symbol
        """
        operation = "bulk_load_market_data"
        
        # Create cache key from parameters
        asset_symbols = sorted([a.symbol for a in assets])
        cache_key = CacheManager.make_key(
            operation,
            symbols=tuple(asset_symbols),
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            self._record_hit(operation)
            logger.debug(f"Cache HIT for {operation}: {len(assets)} assets")
            return cached
        
        # Cache miss: fetch from provider
        self._record_miss(operation)
        logger.debug(f"Cache MISS for {operation}: {len(assets)} assets")
        
        result = self.provider.bulk_load_market_data(assets, start_date, end_date)
        
        # Store in cache
        self.cache.set(cache_key, result)
        
        return result

    def bulk_load_metadata(
        self,
        assets: List[Asset],
        date: datetime,
    ) -> MetadataDict:
        """
        Bulk load metadata with caching.
        
        Args:
            assets: Assets to load metadata for
            date: Reference date
            
        Returns:
            Metadata by symbol
        """
        operation = "bulk_load_metadata"
        
        # Create cache key
        asset_symbols = sorted([a.symbol for a in assets])
        cache_key = CacheManager.make_key(
            operation,
            symbols=tuple(asset_symbols),
            date=date.isoformat(),
        )
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            self._record_hit(operation)
            logger.debug(f"Cache HIT for {operation}: {len(assets)} assets")
            return cached
        
        # Cache miss: fetch from provider
        self._record_miss(operation)
        logger.debug(f"Cache MISS for {operation}: {len(assets)} assets")
        
        result = self.provider.bulk_load_metadata(assets, date)
        
        # Store in cache
        self.cache.set(cache_key, result)
        
        return result

    def check_data_availability(
        self,
        assets: List[Asset],
        date: datetime,
        lookback_days: int,
    ) -> QualityMetricsDict:
        """
        Check data availability.
        
        Note: Not cached as quality checks should reflect current state.
        
        Args:
            assets: Assets to check
            date: Reference date
            lookback_days: Lookback period
            
        Returns:
            Quality metrics by symbol
        """
        return self.provider.check_data_availability(assets, date, lookback_days)

    def invalidate_market_data(self, symbols: Optional[List[str]] = None) -> int:
        """
        Invalidate cached market data.
        
        Args:
            symbols: Specific symbols to invalidate (all if None)
            
        Returns:
            Number of entries invalidated
        """
        if symbols:
            # Invalidate entries containing these symbols
            # Note: This is a simple approach; more efficient would be
            # to maintain a reverse index
            pattern = "bulk_load_market_data:"
            return self.cache.invalidate_pattern(pattern)
        else:
            return self.cache.invalidate_pattern("bulk_load_market_data:")

    def invalidate_metadata(self, symbols: Optional[List[str]] = None) -> int:
        """
        Invalidate cached metadata.
        
        Args:
            symbols: Specific symbols to invalidate (all if None)
            
        Returns:
            Number of entries invalidated
        """
        return self.cache.invalidate_pattern("bulk_load_metadata:")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats and operation-specific hit/miss counts
        """
        cache_stats = self.cache.get_stats()
        
        return {
            "cache": {
                "hits": cache_stats.hits,
                "misses": cache_stats.misses,
                "hit_rate": cache_stats.hit_rate,
                "evictions": cache_stats.evictions,
                "expirations": cache_stats.expirations,
                "size_bytes": cache_stats.current_size_bytes,
                "entries": cache_stats.current_entries,
            },
            "operations": {
                op: {
                    "hits": self._cache_hits.get(op, 0),
                    "misses": self._cache_misses.get(op, 0),
                }
                for op in ["bulk_load_market_data", "bulk_load_metadata"]
            },
        }

    def _record_hit(self, operation: str) -> None:
        """Record a cache hit."""
        self._cache_hits[operation] = self._cache_hits.get(operation, 0) + 1
        
        if self.metrics:
            self.metrics.record_metric(
                "cache_hit",
                1.0,
                tags={"operation": operation},
            )

    def _record_miss(self, operation: str) -> None:
        """Record a cache miss."""
        self._cache_misses[operation] = self._cache_misses.get(operation, 0) + 1
        
        if self.metrics:
            self.metrics.record_metric(
                "cache_miss",
                1.0,
                tags={"operation": operation},
            )

