"""
Unit Tests for CachedUniverseProvider.

Tests for:
    - Cache hits and misses
    - Provider delegation
    - Statistics tracking
    - Cache invalidation
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import Mock, call

import pytest

from universe_screener.adapters.cached_provider import CachedUniverseProvider
from universe_screener.caching.cache_manager import CacheConfig, CacheManager
from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.domain.value_objects import MarketData, QualityMetrics


@pytest.fixture
def sample_assets() -> List[Asset]:
    """Create sample assets for testing."""
    return [
        Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        ),
        Asset(
            symbol="GOOGL",
            name="Alphabet Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2004, 8, 19).date(),
        ),
    ]


@pytest.fixture
def sample_market_data() -> Dict[str, List[MarketData]]:
    """Create sample market data."""
    return {
        "AAPL": [
            MarketData(
                date=datetime(2024, 1, 1),
                open=100.0,
                high=105.0,
                low=99.0,
                close=104.0,
                volume=1000000,
            ),
        ],
        "GOOGL": [
            MarketData(
                date=datetime(2024, 1, 1),
                open=150.0,
                high=155.0,
                low=149.0,
                close=154.0,
                volume=500000,
            ),
        ],
    }


@pytest.fixture
def mock_provider(sample_assets, sample_market_data) -> Mock:
    """Create a mock universe provider."""
    provider = Mock()
    provider.get_assets.return_value = sample_assets
    provider.bulk_load_market_data.return_value = sample_market_data
    provider.bulk_load_metadata.return_value = {
        "AAPL": {"sector": "Technology"},
        "GOOGL": {"sector": "Technology"},
    }
    provider.check_data_availability.return_value = {}
    return provider


class TestCachedProviderDelegation:
    """Test that provider delegates to underlying provider."""

    def test_get_assets_delegates_to_provider(
        self, mock_provider, sample_assets
    ) -> None:
        """get_assets always delegates (not cached)."""
        cached = CachedUniverseProvider(mock_provider)
        
        result = cached.get_assets(datetime(2024, 1, 1), AssetClass.STOCK)
        
        assert result == sample_assets
        mock_provider.get_assets.assert_called_once()

    def test_check_data_availability_delegates_to_provider(
        self, mock_provider, sample_assets
    ) -> None:
        """check_data_availability always delegates (not cached)."""
        cached = CachedUniverseProvider(mock_provider)
        
        cached.check_data_availability(sample_assets, datetime(2024, 1, 1), 60)
        
        mock_provider.check_data_availability.assert_called_once()


class TestCachedProviderMarketData:
    """Tests for bulk_load_market_data caching."""

    def test_first_call_misses_cache(
        self, mock_provider, sample_assets, sample_market_data
    ) -> None:
        """First call results in cache miss."""
        cached = CachedUniverseProvider(mock_provider)
        
        result = cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        assert result == sample_market_data
        mock_provider.bulk_load_market_data.assert_called_once()

    def test_second_call_hits_cache(
        self, mock_provider, sample_assets, sample_market_data
    ) -> None:
        """Second call with same params hits cache."""
        cached = CachedUniverseProvider(mock_provider)
        
        # First call
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        # Second call - should hit cache
        result = cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        assert result == sample_market_data
        # Provider should only be called once
        assert mock_provider.bulk_load_market_data.call_count == 1

    def test_different_params_miss_cache(
        self, mock_provider, sample_assets
    ) -> None:
        """Different parameters result in cache miss."""
        cached = CachedUniverseProvider(mock_provider)
        
        # First call
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        # Second call with different dates
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 2, 1),
            datetime(2024, 2, 28),
        )
        
        # Provider should be called twice
        assert mock_provider.bulk_load_market_data.call_count == 2


class TestCachedProviderMetadata:
    """Tests for bulk_load_metadata caching."""

    def test_metadata_cached(self, mock_provider, sample_assets) -> None:
        """Metadata is cached on second call."""
        cached = CachedUniverseProvider(mock_provider)
        
        # First call
        cached.bulk_load_metadata(sample_assets, datetime(2024, 1, 1))
        
        # Second call - should hit cache
        cached.bulk_load_metadata(sample_assets, datetime(2024, 1, 1))
        
        # Provider should only be called once
        assert mock_provider.bulk_load_metadata.call_count == 1


class TestCachedProviderStats:
    """Tests for cache statistics."""

    def test_stats_track_hits_and_misses(
        self, mock_provider, sample_assets
    ) -> None:
        """Statistics track cache hits and misses."""
        cached = CachedUniverseProvider(mock_provider)
        
        # First call - miss
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        # Second call - hit
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        stats = cached.get_cache_stats()
        
        assert stats["operations"]["bulk_load_market_data"]["misses"] == 1
        assert stats["operations"]["bulk_load_market_data"]["hits"] == 1

    def test_stats_include_cache_level_stats(
        self, mock_provider, sample_assets
    ) -> None:
        """Statistics include cache-level information."""
        cached = CachedUniverseProvider(mock_provider)
        
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        stats = cached.get_cache_stats()
        
        assert "cache" in stats
        assert "entries" in stats["cache"]
        assert stats["cache"]["entries"] == 1


class TestCachedProviderInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_market_data(
        self, mock_provider, sample_assets
    ) -> None:
        """Invalidating market data clears cache."""
        cached = CachedUniverseProvider(mock_provider)
        
        # Fill cache
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        # Invalidate
        count = cached.invalidate_market_data()
        
        assert count == 1
        
        # Next call should miss
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        assert mock_provider.bulk_load_market_data.call_count == 2

    def test_invalidate_metadata(
        self, mock_provider, sample_assets
    ) -> None:
        """Invalidating metadata clears cache."""
        cached = CachedUniverseProvider(mock_provider)
        
        # Fill cache
        cached.bulk_load_metadata(sample_assets, datetime(2024, 1, 1))
        
        # Invalidate
        count = cached.invalidate_metadata()
        
        assert count == 1


class TestCachedProviderWithMetrics:
    """Tests for metrics integration."""

    def test_records_cache_hit_metric(
        self, mock_provider, sample_assets
    ) -> None:
        """Records metric on cache hit."""
        metrics = Mock()
        cached = CachedUniverseProvider(
            mock_provider,
            metrics_collector=metrics,
        )
        
        # First call - miss
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        # Second call - hit
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        # Check metrics recorded
        calls = metrics.record_metric.call_args_list
        
        # Should have one miss and one hit
        miss_calls = [c for c in calls if c[0][0] == "cache_miss"]
        hit_calls = [c for c in calls if c[0][0] == "cache_hit"]
        
        assert len(miss_calls) == 1
        assert len(hit_calls) == 1


class TestCachedProviderCustomCache:
    """Tests with custom cache configuration."""

    def test_with_custom_cache_manager(
        self, mock_provider, sample_assets
    ) -> None:
        """Works with custom cache manager."""
        config = CacheConfig(default_ttl_seconds=1.0)
        cache = CacheManager(config)
        cached = CachedUniverseProvider(mock_provider, cache_manager=cache)
        
        # Cache should work
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        assert mock_provider.bulk_load_market_data.call_count == 1

    def test_with_disabled_cache(
        self, mock_provider, sample_assets
    ) -> None:
        """Disabled cache always calls provider."""
        config = CacheConfig(enabled=False)
        cache = CacheManager(config)
        cached = CachedUniverseProvider(mock_provider, cache_manager=cache)
        
        # Both calls should go to provider
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        cached.bulk_load_market_data(
            sample_assets,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        
        assert mock_provider.bulk_load_market_data.call_count == 2

