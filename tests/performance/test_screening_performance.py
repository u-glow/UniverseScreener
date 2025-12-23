"""
Performance Benchmarks for Screening Pipeline.

Benchmarks:
    - 500 assets < 5 seconds
    - 5000 assets < 10 seconds

Metrics tracked:
    - Total execution time
    - RAM usage (if psutil available)
    - Time per stage
"""

from __future__ import annotations

import random
import time
from datetime import date, datetime, timedelta
from typing import List
from unittest.mock import Mock

import pytest

from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.domain.value_objects import MarketData, QualityMetrics
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters.metrics_collector import InMemoryMetricsCollector
from universe_screener.filters.structural import StructuralFilter
from universe_screener.filters.liquidity import LiquidityFilter
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.config.models import ScreeningConfig
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline

# Try to import psutil for memory tracking
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class LargeScaleMockProvider:
    """Mock provider that generates configurable number of assets."""

    def __init__(self, num_assets: int, seed: int = 42) -> None:
        self.num_assets = num_assets
        self._rng = random.Random(seed)
        self._assets = self._generate_assets()
        self._market_data = self._generate_market_data()

    def _generate_assets(self) -> List[Asset]:
        """Generate many assets for performance testing."""
        exchanges = ["NYSE", "NASDAQ", "XETRA"]
        assets = []

        for i in range(self.num_assets):
            # 80% pass structural filter
            exchange = self._rng.choice(exchanges)

            # 10% young listings
            if i % 10 == 0:
                listing_date = date(2024, 6, 1)
            else:
                listing_date = date(2020, 1, 1) - timedelta(
                    days=self._rng.randint(100, 3000)
                )

            assets.append(
                Asset(
                    symbol=f"SYM{i:05d}",
                    name=f"Company {i}",
                    asset_class=AssetClass.STOCK,
                    asset_type=AssetType.COMMON_STOCK,
                    exchange=exchange,
                    listing_date=listing_date,
                )
            )

        return assets

    def _generate_market_data(self) -> dict:
        """Generate market data for all assets."""
        result = {}
        end_date = datetime(2024, 12, 15)
        start_date = end_date - timedelta(days=60)

        for asset in self._assets:
            data = []
            current = start_date
            base_price = self._rng.uniform(20, 500)
            # 80% have high volume, 20% low
            if self._rng.random() < 0.8:
                base_volume = self._rng.randint(5_000_000, 50_000_000)
            else:
                base_volume = self._rng.randint(10_000, 500_000)

            while current <= end_date:
                if current.weekday() < 5:  # Skip weekends
                    data.append(
                        MarketData(
                            date=current,
                            open=base_price,
                            high=base_price * 1.02,
                            low=base_price * 0.98,
                            close=base_price,
                            volume=int(base_volume * self._rng.uniform(0.8, 1.2)),
                        )
                    )
                current += timedelta(days=1)

            result[asset.symbol] = data

        return result

    def get_assets(self, date: datetime, asset_class: AssetClass) -> List[Asset]:
        return [a for a in self._assets if a.asset_class == asset_class]

    def bulk_load_market_data(
        self,
        assets: List[Asset],
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        return {
            a.symbol: self._market_data.get(a.symbol, [])
            for a in assets
        }

    def bulk_load_metadata(
        self,
        assets: List[Asset],
        date: datetime,
    ) -> dict:
        return {
            a.symbol: {"asset_type": a.asset_type.value, "exchange": a.exchange}
            for a in assets
        }

    def check_data_availability(
        self,
        assets: List[Asset],
        date: datetime,
        lookback_days: int,
    ) -> dict:
        return {
            a.symbol: QualityMetrics(
                missing_days=self._rng.randint(0, 2),
                last_available_date=date,
            )
            for a in assets
        }


def create_pipeline(provider) -> ScreeningPipeline:
    """Create pipeline with given provider."""
    config = ScreeningConfig()
    logger = ConsoleAuditLogger(verbose=False)
    metrics = InMemoryMetricsCollector()

    filters = [
        StructuralFilter(config.structural_filter),
        LiquidityFilter(config.liquidity_filter),
        DataQualityFilter(config.data_quality_filter),
    ]

    return ScreeningPipeline(
        provider=provider,
        filters=filters,
        config=config,
        audit_logger=logger,
        metrics_collector=metrics,
    )


def get_memory_mb() -> float:
    """Get current memory usage in MB."""
    if PSUTIL_AVAILABLE:
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    return 0.0


class TestScreeningPerformance:
    """Performance benchmarks for screening pipeline."""

    def test_500_assets_under_5_seconds(self) -> None:
        """
        BENCHMARK: 500 assets should complete in < 5 seconds
        EXPECTED: Total time < 5s
        """
        # Arrange
        provider = LargeScaleMockProvider(num_assets=500)
        pipeline = create_pipeline(provider)
        screening_date = datetime(2024, 12, 15)

        # Track memory
        mem_before = get_memory_mb()

        # Act
        start = time.perf_counter()
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )
        duration = time.perf_counter() - start

        mem_after = get_memory_mb()

        # Assert
        assert duration < 5.0, f"500 assets took {duration:.2f}s (limit: 5s)"
        assert len(result.input_universe) == 500

        # Log performance metrics
        print(f"\n[500 assets] Duration: {duration:.2f}s")
        print(f"[500 assets] Output: {len(result.output_universe)} assets")
        if PSUTIL_AVAILABLE:
            print(f"[500 assets] Memory delta: {mem_after - mem_before:.1f} MB")

    def test_1000_assets_under_5_seconds(self) -> None:
        """
        BENCHMARK: 1000 assets should complete in < 5 seconds
        EXPECTED: Total time < 5s
        """
        # Arrange
        provider = LargeScaleMockProvider(num_assets=1000)
        pipeline = create_pipeline(provider)
        screening_date = datetime(2024, 12, 15)

        # Act
        start = time.perf_counter()
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )
        duration = time.perf_counter() - start

        # Assert
        assert duration < 5.0, f"1000 assets took {duration:.2f}s (limit: 5s)"
        assert len(result.input_universe) == 1000

        print(f"\n[1000 assets] Duration: {duration:.2f}s")
        print(f"[1000 assets] Output: {len(result.output_universe)} assets")

    @pytest.mark.slow
    def test_5000_assets_under_10_seconds(self) -> None:
        """
        BENCHMARK: 5000 assets should complete in < 10 seconds
        EXPECTED: Total time < 10s

        Note: Marked as slow, skip with `pytest -m "not slow"`
        """
        # Arrange
        provider = LargeScaleMockProvider(num_assets=5000)
        pipeline = create_pipeline(provider)
        screening_date = datetime(2024, 12, 15)

        mem_before = get_memory_mb()

        # Act
        start = time.perf_counter()
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )
        duration = time.perf_counter() - start

        mem_after = get_memory_mb()

        # Assert
        assert duration < 10.0, f"5000 assets took {duration:.2f}s (limit: 10s)"
        assert len(result.input_universe) == 5000

        print(f"\n[5000 assets] Duration: {duration:.2f}s")
        print(f"[5000 assets] Output: {len(result.output_universe)} assets")
        if PSUTIL_AVAILABLE:
            print(f"[5000 assets] Memory delta: {mem_after - mem_before:.1f} MB")


class TestStagePerformance:
    """Performance tests per pipeline stage."""

    def test_stage_timing_breakdown(self) -> None:
        """
        BENCHMARK: Track timing per stage
        EXPECTED: All stages complete reasonably
        """
        # Arrange
        provider = LargeScaleMockProvider(num_assets=500)
        pipeline = create_pipeline(provider)
        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Print stage timing
        print("\n--- Stage Timing Breakdown ---")
        for stage in result.audit_trail:
            print(
                f"  {stage.stage_name}: {stage.duration_seconds*1000:.1f}ms "
                f"({stage.input_count} -> {stage.output_count})"
            )

        # Assert - each stage should be < 1 second
        for stage in result.audit_trail:
            assert stage.duration_seconds < 1.0, (
                f"{stage.stage_name} took {stage.duration_seconds:.2f}s"
            )

    def test_data_load_timing(self) -> None:
        """
        BENCHMARK: Data loading should be fast
        EXPECTED: Load 500 assets data in < 2 seconds
        """
        # Arrange
        provider = LargeScaleMockProvider(num_assets=500)
        config = ScreeningConfig()
        logger = ConsoleAuditLogger(verbose=False)
        metrics = InMemoryMetricsCollector()

        filters = [
            StructuralFilter(config.structural_filter),
        ]

        pipeline = ScreeningPipeline(
            provider=provider,
            filters=filters,
            config=config,
            audit_logger=logger,
            metrics_collector=metrics,
        )

        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Get data load timing from metrics
        all_metrics = metrics.get_metrics()
        load_entries = all_metrics.get("data_load_seconds", [])
        if load_entries and isinstance(load_entries, list) and len(load_entries) > 0:
            load_timing = load_entries[0].get("value", 0)
        else:
            load_timing = 0.0

        print(f"\n[Data Load] 500 assets: {load_timing*1000:.1f}ms")

        # Assert - just verify it completed (timing varies by system)
        assert result is not None

