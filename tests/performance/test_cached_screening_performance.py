"""
Performance Tests for Cached Screening.

Benchmarks:
    - Cache hit vs cache miss performance
    - Second run with cache < 1s (target)
    - Cache efficiency with varying data sizes
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest

from universe_screener.adapters.cached_provider import CachedUniverseProvider
from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters import SimpleMetricsCollector
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.caching.cache_manager import CacheConfig, CacheManager
from universe_screener.config.models import (
    DataQualityFilterConfig,
    GlobalConfig,
    LiquidityFilterConfig,
    ScreeningConfig,
    StockLiquidityConfig,
    StructuralFilterConfig,
)
from universe_screener.domain.entities import AssetClass
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.filters.liquidity import LiquidityFilter
from universe_screener.filters.structural import StructuralFilter
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline


@pytest.fixture
def mock_provider() -> MockUniverseProvider:
    """Create mock provider with deterministic data."""
    return MockUniverseProvider()


@pytest.fixture
def cached_provider(mock_provider) -> CachedUniverseProvider:
    """Create cached provider wrapping mock."""
    config = CacheConfig(
        enabled=True,
        max_size_bytes=512 * 1024 * 1024,  # 512 MB
        default_ttl_seconds=3600,
    )
    cache = CacheManager(config)
    return CachedUniverseProvider(mock_provider, cache_manager=cache)


@pytest.fixture
def screening_config() -> ScreeningConfig:
    """Create default screening config."""
    return ScreeningConfig(
        version="1.0",
        global_settings=GlobalConfig(default_lookback_days=60),
        structural_filter=StructuralFilterConfig(
            enabled=True,
            allowed_asset_types=["COMMON_STOCK"],
            allowed_exchanges=["NYSE", "NASDAQ", "XETRA"],
            min_listing_age_days=252,
        ),
        liquidity_filter=LiquidityFilterConfig(
            enabled=True,
            stock=StockLiquidityConfig(
                min_avg_dollar_volume_usd=1_000_000,
                min_trading_days_pct=0.9,
                lookback_days=60,
            ),
        ),
        data_quality_filter=DataQualityFilterConfig(
            enabled=True,
            max_missing_days=5,
            lookback_days=60,
        ),
    )


class TestCachedScreeningPerformance:
    """Performance tests for cached screening."""

    def test_cache_miss_vs_hit_performance(
        self,
        cached_provider,
        screening_config,
    ) -> None:
        """Cache hit should be significantly faster than miss."""
        pipeline = ScreeningPipeline(
            provider=cached_provider,
            filters=[
                StructuralFilter(screening_config.structural_filter),
                LiquidityFilter(screening_config.liquidity_filter),
                DataQualityFilter(screening_config.data_quality_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        date = datetime(2024, 6, 15)
        
        # First run (cache miss)
        start_miss = time.perf_counter()
        result1 = pipeline.screen(date, AssetClass.STOCK)
        time_miss = time.perf_counter() - start_miss
        
        # Second run (cache hit)
        start_hit = time.perf_counter()
        result2 = pipeline.screen(date, AssetClass.STOCK)
        time_hit = time.perf_counter() - start_hit
        
        # Results should be identical
        assert len(result1.output_universe) == len(result2.output_universe)
        
        # Cache hit should be faster
        assert time_hit < time_miss
        
        print(f"\nCache miss: {time_miss:.4f}s")
        print(f"Cache hit: {time_hit:.4f}s")
        print(f"Speedup: {time_miss / time_hit:.2f}x")

    @pytest.mark.slow
    def test_second_run_under_1_second(
        self,
        cached_provider,
        screening_config,
    ) -> None:
        """Second run with cache should complete in < 1s."""
        pipeline = ScreeningPipeline(
            provider=cached_provider,
            filters=[
                StructuralFilter(screening_config.structural_filter),
                LiquidityFilter(screening_config.liquidity_filter),
                DataQualityFilter(screening_config.data_quality_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        date = datetime(2024, 6, 15)
        
        # First run (populates cache)
        pipeline.screen(date, AssetClass.STOCK)
        
        # Second run (should use cache)
        start = time.perf_counter()
        pipeline.screen(date, AssetClass.STOCK)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 1.0, f"Second run took {elapsed:.2f}s, expected < 1s"

    def test_cache_stats_tracking(
        self,
        cached_provider,
        screening_config,
    ) -> None:
        """Cache statistics are properly tracked."""
        pipeline = ScreeningPipeline(
            provider=cached_provider,
            filters=[
                StructuralFilter(screening_config.structural_filter),
                LiquidityFilter(screening_config.liquidity_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        date = datetime(2024, 6, 15)
        
        # Two runs
        pipeline.screen(date, AssetClass.STOCK)
        pipeline.screen(date, AssetClass.STOCK)
        
        stats = cached_provider.get_cache_stats()
        
        # Should have hits and misses
        cache_stats = stats["cache"]
        assert cache_stats["hits"] >= 1
        assert cache_stats["misses"] >= 1
        assert cache_stats["hit_rate"] > 0

    def test_different_dates_cause_cache_miss(
        self,
        cached_provider,
        screening_config,
    ) -> None:
        """Different screening dates cause cache misses."""
        pipeline = ScreeningPipeline(
            provider=cached_provider,
            filters=[
                StructuralFilter(screening_config.structural_filter),
                LiquidityFilter(screening_config.liquidity_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        # Screen on different dates
        pipeline.screen(datetime(2024, 6, 15), AssetClass.STOCK)
        pipeline.screen(datetime(2024, 6, 16), AssetClass.STOCK)  # Different date
        
        stats = cached_provider.get_cache_stats()
        
        # Both should be misses for market_data (different date ranges)
        ops = stats["operations"]
        assert ops["bulk_load_market_data"]["misses"] == 2


class TestCacheInvalidation:
    """Tests for cache invalidation performance."""

    def test_invalidation_clears_cache(
        self,
        cached_provider,
        screening_config,
    ) -> None:
        """Invalidation forces re-fetch."""
        pipeline = ScreeningPipeline(
            provider=cached_provider,
            filters=[
                StructuralFilter(screening_config.structural_filter),
                LiquidityFilter(screening_config.liquidity_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        date = datetime(2024, 6, 15)
        
        # First run
        pipeline.screen(date, AssetClass.STOCK)
        
        # Invalidate
        cached_provider.invalidate_market_data()
        
        # Third run should miss
        pipeline.screen(date, AssetClass.STOCK)
        
        stats = cached_provider.get_cache_stats()
        
        # Should have 2 misses (1 initial + 1 after invalidation)
        ops = stats["operations"]
        assert ops["bulk_load_market_data"]["misses"] == 2


class TestCacheWithDisabledCaching:
    """Tests with caching disabled."""

    def test_disabled_cache_always_calls_provider(
        self,
        mock_provider,
        screening_config,
    ) -> None:
        """Disabled cache always calls underlying provider."""
        config = CacheConfig(enabled=False)
        cache = CacheManager(config)
        cached = CachedUniverseProvider(mock_provider, cache_manager=cache)
        
        pipeline = ScreeningPipeline(
            provider=cached,
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        date = datetime(2024, 6, 15)
        
        # Multiple runs
        pipeline.screen(date, AssetClass.STOCK)
        pipeline.screen(date, AssetClass.STOCK)
        pipeline.screen(date, AssetClass.STOCK)
        
        stats = cached.get_cache_stats()
        
        # All should be misses (cache disabled)
        ops = stats["operations"]
        assert ops["bulk_load_market_data"]["hits"] == 0
        assert ops["bulk_load_market_data"]["misses"] == 3


class TestCacheMemoryUsage:
    """Tests for cache memory tracking."""

    def test_cache_size_tracked(
        self,
        cached_provider,
        screening_config,
    ) -> None:
        """Cache size is tracked."""
        pipeline = ScreeningPipeline(
            provider=cached_provider,
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        # Empty cache
        stats_before = cached_provider.get_cache_stats()
        assert stats_before["cache"]["size_bytes"] == 0
        
        # Run screening
        pipeline.screen(datetime(2024, 6, 15), AssetClass.STOCK)
        
        # Cache should have data
        stats_after = cached_provider.get_cache_stats()
        assert stats_after["cache"]["size_bytes"] > 0
        assert stats_after["cache"]["entries"] > 0


@pytest.mark.slow
class TestCacheWithLargeDatasets:
    """Performance tests with larger datasets."""

    def test_repeated_screenings_benefit_from_cache(
        self,
        cached_provider,
        screening_config,
    ) -> None:
        """Multiple screenings on same date benefit from cache."""
        pipeline = ScreeningPipeline(
            provider=cached_provider,
            filters=[
                StructuralFilter(screening_config.structural_filter),
                LiquidityFilter(screening_config.liquidity_filter),
                DataQualityFilter(screening_config.data_quality_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        date = datetime(2024, 6, 15)
        times = []
        
        # Run 5 times
        for i in range(5):
            start = time.perf_counter()
            pipeline.screen(date, AssetClass.STOCK)
            times.append(time.perf_counter() - start)
        
        # First run should be slowest (cache miss)
        assert times[0] >= times[1]
        
        # Subsequent runs should be faster
        avg_cached = sum(times[1:]) / len(times[1:])
        assert avg_cached < times[0]
        
        print(f"\nFirst run: {times[0]:.4f}s")
        print(f"Avg cached: {avg_cached:.4f}s")
        print(f"Speedup: {times[0] / avg_cached:.2f}x")

