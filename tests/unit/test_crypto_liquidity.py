"""
Unit Tests for CryptoLiquidityStrategy.

Tests for:
    - Order book depth estimation
    - Slippage calculation
    - Threshold enforcement
"""

from __future__ import annotations

from datetime import datetime

import pytest

from universe_screener.config.models import CryptoLiquidityConfig
from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.domain.value_objects import MarketData
from universe_screener.filters.liquidity_strategies import CryptoLiquidityStrategy


@pytest.fixture
def default_config() -> CryptoLiquidityConfig:
    """Default crypto liquidity config."""
    return CryptoLiquidityConfig(
        max_slippage_pct=0.5,
        min_order_book_depth_usd=100_000,
    )


@pytest.fixture
def btc_asset() -> Asset:
    """Bitcoin asset for testing."""
    return Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_class=AssetClass.CRYPTO,
        asset_type=AssetType.CRYPTO,
        exchange="COINBASE",
        listing_date=datetime(2015, 1, 1).date(),
    )


def create_market_data(
    dollar_volume: float,
    num_days: int = 60,
) -> list[MarketData]:
    """Create market data with specified dollar volume."""
    from datetime import timedelta
    
    # Derive price and volume from dollar volume
    price = 50000.0  # $50k BTC price
    volume = int(dollar_volume / price)
    start_date = datetime(2024, 1, 1)
    
    return [
        MarketData(
            date=start_date + timedelta(days=i),
            open=price,
            high=price * 1.02,
            low=price * 0.98,
            close=price,
            volume=volume,
        )
        for i in range(num_days)
    ]


class TestCryptoLiquidityStrategyBasic:
    """Basic functionality tests."""

    def test_passes_with_sufficient_liquidity(
        self, default_config, btc_asset
    ) -> None:
        """Asset passes with sufficient liquidity."""
        strategy = CryptoLiquidityStrategy(default_config)
        
        # Very high volume = deep order book, low slippage
        # Daily volume of $100M → estimated depth = $5M (5%)
        # Slippage for $100k order = $100k / ($5M * 2) = 1%
        # But default max_slippage_pct = 0.5%, so need even higher volume
        # For slippage < 0.5%: depth > $100k / (0.005 * 2) = $10M
        # Volume needed = $10M / 0.05 = $200M
        market_data = create_market_data(200_000_000)
        
        is_liquid, reason = strategy.check_liquidity(btc_asset, market_data)
        
        assert is_liquid is True
        assert reason == ""

    def test_fails_with_insufficient_depth(
        self, default_config, btc_asset
    ) -> None:
        """Asset fails with insufficient order book depth."""
        strategy = CryptoLiquidityStrategy(default_config)
        
        # Low volume = shallow order book
        # Daily volume of $1M → estimated depth = $50k (5%)
        market_data = create_market_data(1_000_000)
        
        is_liquid, reason = strategy.check_liquidity(btc_asset, market_data)
        
        assert is_liquid is False
        assert "order_book_depth" in reason
        assert "$50,000" in reason

    def test_fails_with_excessive_slippage(
        self, btc_asset
    ) -> None:
        """Asset fails with excessive estimated slippage."""
        # Very tight slippage requirement
        config = CryptoLiquidityConfig(
            max_slippage_pct=0.1,  # Max 0.1% slippage
            min_order_book_depth_usd=10_000,  # Low depth requirement
        )
        strategy = CryptoLiquidityStrategy(config)
        
        # Volume gives $100k depth, but slippage for $100k order is too high
        # Depth = $100k, slippage = $100k / ($100k * 2) = 50%
        market_data = create_market_data(2_000_000)  # $100k depth
        
        is_liquid, reason = strategy.check_liquidity(btc_asset, market_data)
        
        assert is_liquid is False
        assert "slippage" in reason

    def test_fails_with_no_market_data(
        self, default_config, btc_asset
    ) -> None:
        """Asset fails with no market data."""
        strategy = CryptoLiquidityStrategy(default_config)
        
        is_liquid, reason = strategy.check_liquidity(btc_asset, [])
        
        assert is_liquid is False
        assert "no market data" in reason


class TestCryptoLiquidityStrategyThresholds:
    """Threshold configuration tests."""

    def test_respects_custom_depth_threshold(self, btc_asset) -> None:
        """Custom depth threshold is respected."""
        config = CryptoLiquidityConfig(
            max_slippage_pct=10.0,  # High slippage OK
            min_order_book_depth_usd=500_000,  # Require $500k depth
        )
        strategy = CryptoLiquidityStrategy(config)
        
        # $5M volume → $250k depth (below threshold)
        market_data = create_market_data(5_000_000)
        
        is_liquid, reason = strategy.check_liquidity(btc_asset, market_data)
        
        assert is_liquid is False
        assert "order_book_depth" in reason

    def test_respects_custom_slippage_threshold(self, btc_asset) -> None:
        """Custom slippage threshold is respected."""
        config = CryptoLiquidityConfig(
            max_slippage_pct=1.0,  # Allow 1% slippage
            min_order_book_depth_usd=10_000,  # Low depth OK
        )
        strategy = CryptoLiquidityStrategy(config)
        
        # $10M volume → $500k depth
        # Slippage for $100k order = $100k / ($500k * 2) = 10%
        market_data = create_market_data(10_000_000)
        
        is_liquid, reason = strategy.check_liquidity(btc_asset, market_data)
        
        # Slippage = 100k / (500k * 2) = 0.1 = 10% > 1%
        assert is_liquid is False
        assert "slippage" in reason


class TestCryptoLiquidityStrategyEdgeCases:
    """Edge case tests."""

    def test_handles_single_day_data(
        self, default_config, btc_asset
    ) -> None:
        """Works with single day of data."""
        strategy = CryptoLiquidityStrategy(default_config)
        
        # Very high volume single day - needs $200M for 0.5% slippage
        market_data = create_market_data(200_000_000, num_days=1)
        
        is_liquid, reason = strategy.check_liquidity(btc_asset, market_data)
        
        # Should pass (very high volume)
        assert is_liquid is True

    def test_handles_varying_volume(
        self, default_config, btc_asset
    ) -> None:
        """Works with varying daily volume."""
        from datetime import timedelta
        
        strategy = CryptoLiquidityStrategy(default_config)
        
        # High volume with some variation
        price = 50000.0
        start_date = datetime(2024, 1, 1)
        # Need avg volume of ~$200M for 0.5% slippage
        market_data = [
            MarketData(
                date=start_date + timedelta(days=i),
                open=price,
                high=price * 1.02,
                low=price * 0.98,
                close=price,
                volume=int((200_000_000 if i % 2 == 0 else 250_000_000) / price),
            )
            for i in range(60)
        ]
        
        is_liquid, reason = strategy.check_liquidity(btc_asset, market_data)
        
        # Average volume should be sufficient → passes
        assert is_liquid is True

