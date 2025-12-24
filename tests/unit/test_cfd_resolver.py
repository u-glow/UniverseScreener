"""
Unit Tests for CFDResolver Strategy.

Tests:
    - CFD availability for different asset classes
    - Leverage calculation
    - Spread calculation
    - Edge cases
"""

from __future__ import annotations

from datetime import datetime
from typing import List

import pytest

from universe_screener.derivatives.strategies import CFDResolver, CFDConfig
from universe_screener.derivatives.entities import InstrumentType
from universe_screener.domain.entities import Asset, AssetClass, AssetType


@pytest.fixture
def default_resolver() -> CFDResolver:
    """Create default CFD resolver."""
    return CFDResolver()


@pytest.fixture
def custom_resolver() -> CFDResolver:
    """Create CFD resolver with custom config."""
    config = CFDConfig(
        default_spread_pct=0.1,
        min_position_units=0.5,
        overnight_fee_pct=0.02,
        margin_pct=5.0,  # 20x leverage
    )
    return CFDResolver(config)


class TestCFDAvailability:
    """Tests for CFD availability checks."""

    def test_stock_has_cfd(self, default_resolver: CFDResolver) -> None:
        """Stocks have CFDs available."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        assert len(instruments) == 1
        assert instruments[0].instrument_type == InstrumentType.CFD

    def test_major_crypto_has_cfd(self, default_resolver: CFDResolver) -> None:
        """Major cryptocurrencies have CFDs."""
        btc = Asset(
            symbol="BTC-USD",
            name="Bitcoin",
            asset_class=AssetClass.CRYPTO,
            asset_type=AssetType.CRYPTO,
            exchange="COINBASE",
            listing_date=datetime(2015, 1, 1).date(),
        )

        instruments = default_resolver.resolve(btc, "Test Broker", (1.0, 100.0))

        assert len(instruments) == 1

    def test_minor_crypto_no_cfd(self, default_resolver: CFDResolver) -> None:
        """Minor cryptocurrencies may not have CFDs."""
        minor = Asset(
            symbol="SHIB-USD",
            name="Shiba Inu",
            asset_class=AssetClass.CRYPTO,
            asset_type=AssetType.CRYPTO,
            exchange="COINBASE",
            listing_date=datetime(2020, 1, 1).date(),
        )

        instruments = default_resolver.resolve(minor, "Test Broker", (1.0, 100.0))

        # Minor crypto should not have CFD (based on mock logic)
        assert len(instruments) == 0

    def test_forex_has_cfd(self, default_resolver: CFDResolver) -> None:
        """Forex pairs have CFDs."""
        eurusd = Asset(
            symbol="EUR/USD",
            name="Euro vs USD",
            asset_class=AssetClass.FOREX,
            asset_type=AssetType.FOREX_PAIR,
            exchange="FOREX",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(eurusd, "Test Broker", (1.0, 100.0))

        assert len(instruments) == 1


class TestCFDLeverage:
    """Tests for leverage calculation."""

    def test_stock_leverage(self, default_resolver: CFDResolver) -> None:
        """Stocks get moderate leverage."""
        asset = Asset(
            symbol="MSFT",
            name="Microsoft",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        assert len(instruments) == 1
        assert instruments[0].leverage == 5.0  # Default stock leverage

    def test_crypto_lower_leverage(self, default_resolver: CFDResolver) -> None:
        """Crypto gets lower leverage due to volatility."""
        asset = Asset(
            symbol="ETH-USD",
            name="Ethereum",
            asset_class=AssetClass.CRYPTO,
            asset_type=AssetType.CRYPTO,
            exchange="COINBASE",
            listing_date=datetime(2015, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        assert len(instruments) == 1
        assert instruments[0].leverage == 2.0  # Lower for crypto

    def test_forex_higher_leverage(self, default_resolver: CFDResolver) -> None:
        """Forex gets higher leverage."""
        asset = Asset(
            symbol="GBP/USD",
            name="British Pound vs USD",
            asset_class=AssetClass.FOREX,
            asset_type=AssetType.FOREX_PAIR,
            exchange="FOREX",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        assert len(instruments) == 1
        assert instruments[0].leverage == 30.0  # Higher for forex

    def test_leverage_clamped_to_range(self, default_resolver: CFDResolver) -> None:
        """Leverage is clamped to specified range."""
        asset = Asset(
            symbol="EUR/USD",
            name="Euro vs USD",
            asset_class=AssetClass.FOREX,
            asset_type=AssetType.FOREX_PAIR,
            exchange="FOREX",
            listing_date=datetime(2000, 1, 1).date(),
        )

        # Clamp to max 10x
        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 10.0))

        if instruments:
            assert instruments[0].leverage <= 10.0

    def test_leverage_clamped_to_min(self, default_resolver: CFDResolver) -> None:
        """Leverage is clamped UP to minimum when base is lower."""
        asset = Asset(
            symbol="ETH-USD",
            name="Ethereum",
            asset_class=AssetClass.CRYPTO,
            asset_type=AssetType.CRYPTO,
            exchange="COINBASE",
            listing_date=datetime(2015, 1, 1).date(),
        )

        # Crypto base leverage = 2x, but min is 5x
        # Clamping brings it up to 5x
        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 100.0))

        assert len(instruments) == 1
        assert instruments[0].leverage == 5.0  # Clamped up to min


class TestCFDSpread:
    """Tests for spread/trading cost calculation."""

    def test_forex_tight_spread(self, default_resolver: CFDResolver) -> None:
        """Forex has tight spreads."""
        asset = Asset(
            symbol="EUR/USD",
            name="Euro vs USD",
            asset_class=AssetClass.FOREX,
            asset_type=AssetType.FOREX_PAIR,
            exchange="FOREX",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        assert instruments[0].trading_costs == 0.01  # Tight forex spread

    def test_crypto_wider_spread(self, default_resolver: CFDResolver) -> None:
        """Crypto has wider spreads."""
        asset = Asset(
            symbol="BTC-USD",
            name="Bitcoin",
            asset_class=AssetClass.CRYPTO,
            asset_type=AssetType.CRYPTO,
            exchange="COINBASE",
            listing_date=datetime(2015, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        assert instruments[0].trading_costs == 0.15  # Wider crypto spread

    def test_stock_default_spread(self, default_resolver: CFDResolver) -> None:
        """Stocks use default spread."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        assert instruments[0].trading_costs == 0.05  # Default spread


class TestCFDInstrumentDetails:
    """Tests for CFD instrument details."""

    def test_cfd_symbol_format(self, default_resolver: CFDResolver) -> None:
        """CFD symbol follows expected format."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        assert instruments[0].symbol == "AAPL.CFD"

    def test_cfd_has_metadata(self, default_resolver: CFDResolver) -> None:
        """CFD includes relevant metadata."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        metadata = instruments[0].metadata
        assert metadata["product_type"] == "CFD"
        assert metadata["short_selling"] is True

    def test_cfd_margin_calculation(self, default_resolver: CFDResolver) -> None:
        """CFD margin is calculated from leverage."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        # 5x leverage = 20% margin
        assert instruments[0].margin_requirement == 20.0

    def test_custom_config_applied(self, custom_resolver: CFDResolver) -> None:
        """Custom config is applied to CFDs."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = custom_resolver.resolve(asset, "Test Broker", (1.0, 100.0))

        # Custom overnight fee
        assert instruments[0].overnight_fee == 0.02
        # Custom min position
        assert instruments[0].min_position_size == 0.5

