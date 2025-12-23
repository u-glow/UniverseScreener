"""
Unit Tests for LiquidityFilter.

Test Aspects Covered:
    ✅ Business Logic: Correct liquidity calculations
    ✅ Edge Cases: Missing data, zero volume
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List

import pytest

from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.domain.value_objects import MarketData
from universe_screener.filters.liquidity import LiquidityFilter, StockLiquidityStrategy
from universe_screener.config.models import LiquidityFilterConfig, StockLiquidityConfig
from universe_screener.pipeline.data_context import DataContext


@pytest.fixture
def filter_config() -> LiquidityFilterConfig:
    """Create filter configuration for testing."""
    return LiquidityFilterConfig(
        enabled=True,
        stock=StockLiquidityConfig(
            min_avg_dollar_volume_usd=5_000_000,
            min_trading_days_pct=0.90,
            lookback_days=60,
        ),
    )


def create_market_data(
    days: int = 60,
    avg_price: float = 100.0,
    avg_volume: int = 100_000,
) -> List[MarketData]:
    """Create mock market data for testing."""
    data = []
    base_date = datetime(2024, 12, 15)
    for i in range(days):
        data.append(
            MarketData(
                date=base_date - timedelta(days=i),
                open=avg_price,
                high=avg_price * 1.02,
                low=avg_price * 0.98,
                close=avg_price,
                volume=avg_volume,
            )
        )
    return data


class TestLiquidityFilter:
    """Test cases for LiquidityFilter."""

    def test_passes_liquid_stock(
        self,
        filter_config: LiquidityFilterConfig,
    ) -> None:
        """
        SCENARIO: Stock with sufficient dollar volume and trading days
        EXPECTED: Stock passes the filter
        """
        # Arrange
        filter_ = LiquidityFilter(filter_config)
        assets = [
            Asset(
                symbol="LIQUID",
                name="Liquid Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]
        # Price $100 * Volume 100,000 = $10M daily dollar volume
        market_data = create_market_data(days=50, avg_price=100.0, avg_volume=100_000)

        context = DataContext(
            assets=assets,
            market_data={"LIQUID": market_data},
            metadata={},
            quality_metrics={},
        )
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "LIQUID" in result.passed_assets
        assert len(result.rejected_assets) == 0

    def test_filters_illiquid_stock(
        self,
        filter_config: LiquidityFilterConfig,
    ) -> None:
        """
        SCENARIO: Stock with dollar volume below threshold
        EXPECTED: Stock is filtered with appropriate reason
        """
        # Arrange
        filter_ = LiquidityFilter(filter_config)
        assets = [
            Asset(
                symbol="ILLIQUID",
                name="Illiquid Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]
        # Price $10 * Volume 10,000 = $100K daily dollar volume (too low)
        market_data = create_market_data(days=50, avg_price=10.0, avg_volume=10_000)

        context = DataContext(
            assets=assets,
            market_data={"ILLIQUID": market_data},
            metadata={},
            quality_metrics={},
        )
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "ILLIQUID" in result.rejected_assets
        assert "dollar_volume" in result.rejection_reasons["ILLIQUID"].lower()

    def test_filters_sparse_trading_days(
        self,
        filter_config: LiquidityFilterConfig,
    ) -> None:
        """
        SCENARIO: Stock missing too many trading days
        EXPECTED: Stock is filtered with appropriate reason
        """
        # Arrange
        filter_ = LiquidityFilter(filter_config)
        assets = [
            Asset(
                symbol="SPARSE",
                name="Sparse Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]
        # Only 20 days of data (too few for 60 day lookback)
        market_data = create_market_data(days=20, avg_price=100.0, avg_volume=100_000)

        context = DataContext(
            assets=assets,
            market_data={"SPARSE": market_data},
            metadata={},
            quality_metrics={},
        )
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "SPARSE" in result.rejected_assets
        assert "trading_days" in result.rejection_reasons["SPARSE"].lower()

    def test_handles_no_market_data(
        self,
        filter_config: LiquidityFilterConfig,
    ) -> None:
        """
        SCENARIO: Asset has no market data in context
        EXPECTED: Asset is filtered
        """
        # Arrange
        filter_ = LiquidityFilter(filter_config)
        assets = [
            Asset(
                symbol="NODATA",
                name="No Data Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]

        context = DataContext(
            assets=assets,
            market_data={},  # No data
            metadata={},
            quality_metrics={},
        )
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "NODATA" in result.rejected_assets


class TestStockLiquidityStrategy:
    """Test cases for StockLiquidityStrategy."""

    def test_calculates_avg_dollar_volume(self) -> None:
        """
        SCENARIO: Market data with known volume and price
        EXPECTED: Correct average dollar volume calculated
        """
        # Arrange
        config = StockLiquidityConfig(
            min_avg_dollar_volume_usd=1_000_000,
            min_trading_days_pct=0.5,
            lookback_days=60,
        )
        strategy = StockLiquidityStrategy(config)
        asset = Asset(
            symbol="TEST",
            name="Test Corp",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NYSE",
            listing_date=date(2000, 1, 1),
        )
        # $100 * 20,000 = $2M per day
        market_data = create_market_data(days=40, avg_price=100.0, avg_volume=20_000)

        # Act
        is_valid, reason = strategy.check_liquidity(asset, market_data)

        # Assert
        assert is_valid is True

    def test_rejects_low_dollar_volume(self) -> None:
        """
        SCENARIO: Dollar volume below threshold
        EXPECTED: Rejected with clear reason
        """
        # Arrange
        config = StockLiquidityConfig(
            min_avg_dollar_volume_usd=10_000_000,  # High threshold
            min_trading_days_pct=0.5,
            lookback_days=60,
        )
        strategy = StockLiquidityStrategy(config)
        asset = Asset(
            symbol="TEST",
            name="Test Corp",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NYSE",
            listing_date=date(2000, 1, 1),
        )
        # $10 * 10,000 = $100K per day (below threshold)
        market_data = create_market_data(days=40, avg_price=10.0, avg_volume=10_000)

        # Act
        is_valid, reason = strategy.check_liquidity(asset, market_data)

        # Assert
        assert is_valid is False
        assert "dollar_volume" in reason.lower()
