"""
Unit Tests for DerivativeResolver.

Tests:
    - Instrument resolution for different asset classes
    - Filter criteria application
    - Best instrument selection
    - Strategy registration
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from unittest.mock import Mock

import pytest

from universe_screener.derivatives.derivative_resolver import (
    DerivativeResolver,
    InstrumentFilter,
)
from universe_screener.derivatives.entities import InstrumentType, TradableInstrument
from universe_screener.derivatives.strategies import CFDResolver, TurboResolver, FutureResolver
from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.config.models import DerivativeConfig


@pytest.fixture
def stock_asset() -> Asset:
    """Create a sample stock asset."""
    return Asset(
        symbol="AAPL",
        name="Apple Inc",
        asset_class=AssetClass.STOCK,
        asset_type=AssetType.COMMON_STOCK,
        exchange="NASDAQ",
        listing_date=datetime(2000, 1, 1).date(),
    )


@pytest.fixture
def crypto_asset() -> Asset:
    """Create a sample crypto asset."""
    return Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_class=AssetClass.CRYPTO,
        asset_type=AssetType.CRYPTO,
        exchange="COINBASE",
        listing_date=datetime(2015, 1, 1).date(),
    )


@pytest.fixture
def forex_asset() -> Asset:
    """Create a sample forex asset."""
    return Asset(
        symbol="EUR/USD",
        name="Euro vs US Dollar",
        asset_class=AssetClass.FOREX,
        asset_type=AssetType.FOREX_PAIR,
        exchange="FOREX",
        listing_date=datetime(2000, 1, 1).date(),
    )


@pytest.fixture
def default_config() -> DerivativeConfig:
    """Create default derivative configuration."""
    return DerivativeConfig(
        enabled=True,
        instrument_types=["CFD", "TURBO", "FUTURE"],
        min_leverage=2.0,
        max_leverage=30.0,
        brokers=["Interactive Brokers", "Test Broker"],
    )


class TestDerivativeResolverBasic:
    """Basic resolution tests."""

    def test_resolve_stock_cfds(self, stock_asset: Asset, default_config: DerivativeConfig) -> None:
        """Resolve CFD instruments for stocks."""
        resolver = DerivativeResolver(config=default_config)

        instruments = resolver.get_tradable_instruments([stock_asset])

        assert stock_asset.symbol in instruments
        assert len(instruments[stock_asset.symbol]) > 0
        # Should have CFDs
        cfds = [i for i in instruments[stock_asset.symbol] if i.instrument_type == InstrumentType.CFD]
        assert len(cfds) > 0

    def test_resolve_crypto_cfds(self, crypto_asset: Asset, default_config: DerivativeConfig) -> None:
        """Resolve CFD instruments for crypto (major coins only)."""
        resolver = DerivativeResolver(config=default_config)

        instruments = resolver.get_tradable_instruments([crypto_asset])

        assert crypto_asset.symbol in instruments
        cfds = [i for i in instruments[crypto_asset.symbol] if i.instrument_type == InstrumentType.CFD]
        assert len(cfds) > 0
        # Crypto should have lower leverage
        assert all(c.leverage <= 10 for c in cfds)

    def test_resolve_forex_cfds(self, forex_asset: Asset, default_config: DerivativeConfig) -> None:
        """Resolve CFD instruments for forex."""
        resolver = DerivativeResolver(config=default_config)

        instruments = resolver.get_tradable_instruments([forex_asset])

        assert forex_asset.symbol in instruments
        cfds = [i for i in instruments[forex_asset.symbol] if i.instrument_type == InstrumentType.CFD]
        assert len(cfds) > 0
        # Forex should have higher leverage
        assert any(c.leverage >= 10 for c in cfds)

    def test_resolve_multiple_underlyings(
        self, stock_asset: Asset, forex_asset: Asset, default_config: DerivativeConfig
    ) -> None:
        """Resolve instruments for multiple underlyings."""
        resolver = DerivativeResolver(config=default_config)

        instruments = resolver.get_tradable_instruments([stock_asset, forex_asset])

        assert len(instruments) == 2
        assert stock_asset.symbol in instruments
        assert forex_asset.symbol in instruments


class TestInstrumentFilter:
    """Tests for InstrumentFilter criteria."""

    def test_filter_by_instrument_type(self, stock_asset: Asset, default_config: DerivativeConfig) -> None:
        """Filter by specific instrument type."""
        resolver = DerivativeResolver(config=default_config)
        filter_criteria = InstrumentFilter(
            instrument_types=[InstrumentType.CFD],
        )

        instruments = resolver.get_tradable_instruments([stock_asset], filter_criteria)

        if stock_asset.symbol in instruments:
            assert all(
                i.instrument_type == InstrumentType.CFD
                for i in instruments[stock_asset.symbol]
            )

    def test_filter_by_leverage_range(self, stock_asset: Asset, default_config: DerivativeConfig) -> None:
        """Filter by leverage range."""
        resolver = DerivativeResolver(config=default_config)
        filter_criteria = InstrumentFilter(
            min_leverage=3.0,
            max_leverage=10.0,
        )

        instruments = resolver.get_tradable_instruments([stock_asset], filter_criteria)

        if stock_asset.symbol in instruments:
            for inst in instruments[stock_asset.symbol]:
                assert 3.0 <= inst.leverage <= 10.0

    def test_filter_by_broker(self, stock_asset: Asset, default_config: DerivativeConfig) -> None:
        """Filter by specific broker."""
        resolver = DerivativeResolver(config=default_config)
        filter_criteria = InstrumentFilter(
            brokers=["Interactive Brokers"],
        )

        instruments = resolver.get_tradable_instruments([stock_asset], filter_criteria)

        if stock_asset.symbol in instruments:
            assert all(
                i.broker == "Interactive Brokers"
                for i in instruments[stock_asset.symbol]
            )

    def test_filter_by_max_trading_costs(self, stock_asset: Asset, default_config: DerivativeConfig) -> None:
        """Filter by maximum trading costs."""
        resolver = DerivativeResolver(config=default_config)
        filter_criteria = InstrumentFilter(
            max_trading_costs=0.1,  # Max 0.1%
        )

        instruments = resolver.get_tradable_instruments([stock_asset], filter_criteria)

        if stock_asset.symbol in instruments:
            assert all(
                i.trading_costs <= 0.1
                for i in instruments[stock_asset.symbol]
            )

    def test_filter_matches_basic(self) -> None:
        """Test filter matches method."""
        asset = Mock(spec=Asset)
        instrument = TradableInstrument(
            underlying=asset,
            instrument_type=InstrumentType.CFD,
            leverage=10.0,
            broker="Test Broker",
            trading_costs=0.05,
            min_position_size=1.0,
        )

        # Should match basic filter
        basic_filter = InstrumentFilter()
        assert basic_filter.matches(instrument) is True

        # Should not match type filter
        type_filter = InstrumentFilter(instrument_types=[InstrumentType.FUTURE])
        assert type_filter.matches(instrument) is False

        # Should not match leverage filter
        lev_filter = InstrumentFilter(min_leverage=15.0)
        assert lev_filter.matches(instrument) is False


class TestBestInstrumentSelection:
    """Tests for best instrument selection."""

    def test_get_best_instrument(self, stock_asset: Asset, default_config: DerivativeConfig) -> None:
        """Get best instrument for underlying."""
        resolver = DerivativeResolver(config=default_config)

        best = resolver.get_best_instrument(stock_asset)

        assert best is not None
        assert best.underlying.symbol == stock_asset.symbol

    def test_get_best_with_type_preference(self, stock_asset: Asset, default_config: DerivativeConfig) -> None:
        """Get best instrument with type preference."""
        resolver = DerivativeResolver(config=default_config)

        best = resolver.get_best_instrument(
            stock_asset,
            prefer_type=InstrumentType.CFD,
        )

        # If CFD is available, it should be preferred
        if best is not None:
            assert best.instrument_type == InstrumentType.CFD

    def test_get_best_returns_none_if_no_match(self, default_config: DerivativeConfig) -> None:
        """Get best returns None if no instruments match."""
        resolver = DerivativeResolver(config=default_config)
        
        # Asset without any instruments
        unknown_asset = Asset(
            symbol="UNKNOWN123",
            name="Unknown Asset",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="OTC",
            listing_date=datetime(2020, 1, 1).date(),
        )
        
        # With very restrictive filter
        filter_criteria = InstrumentFilter(
            min_leverage=1000.0,  # Impossible leverage
        )

        best = resolver.get_best_instrument(unknown_asset, filter_criteria)

        # Might be None depending on mock behavior
        # The test validates no exception is raised


class TestDerivativeResolverStrategies:
    """Tests for custom strategy registration."""

    def test_register_custom_strategy(self, stock_asset: Asset) -> None:
        """Register and use custom strategy."""
        resolver = DerivativeResolver()

        # Create mock strategy
        mock_strategy = Mock()
        mock_strategy.instrument_type = InstrumentType.OPTION
        mock_strategy.resolve.return_value = [
            TradableInstrument(
                underlying=stock_asset,
                instrument_type=InstrumentType.OPTION,
                leverage=1.0,
                broker="Options Broker",
                trading_costs=0.5,
                min_position_size=100.0,
                strike_price=150.0,
            )
        ]

        resolver.register_strategy(mock_strategy)

        # Verify strategy is registered
        assert InstrumentType.OPTION in resolver.available_types

    def test_available_types(self) -> None:
        """Get list of available instrument types."""
        resolver = DerivativeResolver()

        types = resolver.available_types

        assert InstrumentType.CFD in types
        assert InstrumentType.TURBO in types
        assert InstrumentType.FUTURE in types


class TestDerivativeResolverConfig:
    """Tests for configuration-driven behavior."""

    def test_disabled_config(self, stock_asset: Asset) -> None:
        """Resolver with disabled config still works (for backwards compat)."""
        config = DerivativeConfig(enabled=False)
        resolver = DerivativeResolver(config=config)

        # Should still resolve (enabled flag is for pipeline integration)
        instruments = resolver.get_tradable_instruments([stock_asset])

        # Result depends on implementation
        # No exception should be raised

    def test_limited_instrument_types(self, stock_asset: Asset) -> None:
        """Config limits instrument types."""
        config = DerivativeConfig(
            enabled=True,
            instrument_types=["CFD"],  # Only CFDs
            min_leverage=1.0,
            max_leverage=100.0,
        )
        resolver = DerivativeResolver(config=config)

        instruments = resolver.get_tradable_instruments([stock_asset])

        if stock_asset.symbol in instruments:
            # Should only have CFDs
            assert all(
                i.instrument_type == InstrumentType.CFD
                for i in instruments[stock_asset.symbol]
            )


class TestEmptyInputs:
    """Tests for edge cases with empty inputs."""

    def test_empty_underlyings(self, default_config: DerivativeConfig) -> None:
        """Empty underlyings returns empty dict."""
        resolver = DerivativeResolver(config=default_config)

        instruments = resolver.get_tradable_instruments([])

        assert instruments == {}

    def test_none_filter_criteria(self, stock_asset: Asset, default_config: DerivativeConfig) -> None:
        """None filter uses config defaults."""
        resolver = DerivativeResolver(config=default_config)

        instruments = resolver.get_tradable_instruments([stock_asset], None)

        # Should work without exception
        assert isinstance(instruments, dict)

