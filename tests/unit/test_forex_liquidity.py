"""
Unit Tests for ForexLiquidityStrategy.

Tests for:
    - Spread calculation in pips
    - 24/5 trading availability
    - Threshold enforcement
"""

from __future__ import annotations

from datetime import datetime

import pytest

from universe_screener.config.models import ForexLiquidityConfig
from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.domain.value_objects import MarketData
from universe_screener.filters.liquidity_strategies import ForexLiquidityStrategy


@pytest.fixture
def default_config() -> ForexLiquidityConfig:
    """Default forex liquidity config."""
    return ForexLiquidityConfig(max_spread_pips=3.0)


@pytest.fixture
def eurusd_asset() -> Asset:
    """EUR/USD pair for testing."""
    return Asset(
        symbol="EUR/USD",
        name="Euro vs US Dollar",
        asset_class=AssetClass.FOREX,
        asset_type=AssetType.FOREX_PAIR,
        exchange="FOREX",
        listing_date=datetime(1999, 1, 1).date(),
    )


def create_market_data(
    base_price: float = 1.1000,
    spread_pct: float = 0.0001,  # 0.01% = ~1 pip
    num_days: int = 60,
) -> list[MarketData]:
    """Create market data with specified spread."""
    from datetime import timedelta
    
    # High-Low range determines spread
    range_pct = spread_pct * 100  # Convert to percentage range
    start_date = datetime(2024, 1, 1)
    
    return [
        MarketData(
            date=start_date + timedelta(days=i),
            open=base_price,
            high=base_price * (1 + range_pct / 2),
            low=base_price * (1 - range_pct / 2),
            close=base_price,
            volume=1_000_000,
        )
        for i in range(num_days)
    ]


class TestForexLiquidityStrategyBasic:
    """Basic functionality tests."""

    def test_passes_with_tight_spread(
        self, default_config, eurusd_asset
    ) -> None:
        """Asset passes with tight spread."""
        strategy = ForexLiquidityStrategy(default_config)
        
        # Very tight spread
        market_data = create_market_data(spread_pct=0.00001)
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        assert is_liquid is True
        assert reason == ""

    def test_fails_with_wide_spread(
        self, default_config, eurusd_asset
    ) -> None:
        """Asset fails with wide spread."""
        strategy = ForexLiquidityStrategy(default_config)
        
        # Wide spread (5% range → large pips)
        market_data = create_market_data(spread_pct=0.05)
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        assert is_liquid is False
        assert "spread" in reason

    def test_fails_with_no_market_data(
        self, default_config, eurusd_asset
    ) -> None:
        """Asset fails with no market data."""
        strategy = ForexLiquidityStrategy(default_config)
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, [])
        
        assert is_liquid is False
        assert "no market data" in reason


class TestForexLiquidityStrategyThresholds:
    """Threshold configuration tests."""

    def test_respects_custom_spread_threshold(self, eurusd_asset) -> None:
        """Custom spread threshold is respected."""
        config = ForexLiquidityConfig(max_spread_pips=1.0)  # Very tight
        strategy = ForexLiquidityStrategy(config)
        
        # Moderate spread
        market_data = create_market_data(spread_pct=0.001)
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        # Should fail with tight requirement
        assert is_liquid is False
        assert "spread" in reason

    def test_generous_threshold_passes(self, eurusd_asset) -> None:
        """Generous threshold allows wider spreads."""
        config = ForexLiquidityConfig(max_spread_pips=100.0)  # Very generous
        strategy = ForexLiquidityStrategy(config)
        
        # Wide spread
        market_data = create_market_data(spread_pct=0.01)
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        # Should pass with generous threshold
        assert is_liquid is True


class TestForexLiquidityStrategyTradingAvailability:
    """Trading availability tests."""

    def test_fails_with_insufficient_trading_days(
        self, default_config, eurusd_asset
    ) -> None:
        """Asset fails with insufficient trading days."""
        strategy = ForexLiquidityStrategy(default_config)
        
        # Only 10 trading days (need minimum 30)
        market_data = create_market_data(num_days=10)
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        # With less than 30 days, should fail trading_days check
        assert is_liquid is False
        assert "trading_days" in reason

    def test_passes_with_sufficient_trading_days(
        self, default_config, eurusd_asset
    ) -> None:
        """Asset passes with sufficient trading days."""
        strategy = ForexLiquidityStrategy(default_config)
        
        # 60 trading days (more than sufficient)
        market_data = create_market_data(num_days=60)
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        assert is_liquid is True


class TestForexLiquidityStrategyEdgeCases:
    """Edge case tests."""

    def test_handles_zero_high_low(
        self, default_config, eurusd_asset
    ) -> None:
        """Handles data with zero high/low."""
        from datetime import timedelta
        
        strategy = ForexLiquidityStrategy(default_config)
        start_date = datetime(2024, 1, 1)
        
        market_data = [
            MarketData(
                date=start_date + timedelta(days=i),
                open=1.1,
                high=0.0,  # Invalid
                low=0.0,   # Invalid
                close=1.1,
                volume=1000,
            )
            for i in range(60)
        ]
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        # Should fail gracefully
        assert is_liquid is False
        assert "spread" in reason.lower() or "calculate" in reason.lower()

    def test_handles_single_day_data(
        self, default_config, eurusd_asset
    ) -> None:
        """Works with single day of data."""
        strategy = ForexLiquidityStrategy(default_config)
        
        market_data = create_market_data(num_days=1)
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        # Should fail due to insufficient trading days
        assert is_liquid is False
        assert "trading_days" in reason

    def test_handles_varying_spreads(
        self, default_config, eurusd_asset
    ) -> None:
        """Works with varying daily spreads."""
        from datetime import timedelta
        
        strategy = ForexLiquidityStrategy(default_config)
        
        base_price = 1.1000
        start_date = datetime(2024, 1, 1)
        market_data = []
        
        for i in range(60):
            # Alternate tight and wide spreads
            if i % 2 == 0:
                spread = 0.00001  # Tight
            else:
                spread = 0.0001   # Normal
            
            market_data.append(
                MarketData(
                    date=start_date + timedelta(days=i),
                    open=base_price,
                    high=base_price * (1 + spread),
                    low=base_price * (1 - spread),
                    close=base_price,
                    volume=1_000_000,
                )
            )
        
        is_liquid, reason = strategy.check_liquidity(eurusd_asset, market_data)
        
        # Average spread should be acceptable
        assert is_liquid is True

