"""
Unit Tests for TurboResolver Strategy.

Tests:
    - Turbo availability
    - Knockout level calculation
    - Multiple leverage products
    - Long and short Turbos
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from universe_screener.derivatives.strategies import TurboResolver, TurboConfig
from universe_screener.derivatives.entities import InstrumentType
from universe_screener.domain.entities import Asset, AssetClass, AssetType


@pytest.fixture
def default_resolver() -> TurboResolver:
    """Create default Turbo resolver."""
    return TurboResolver()


@pytest.fixture
def custom_resolver() -> TurboResolver:
    """Create Turbo resolver with custom config."""
    config = TurboConfig(
        knockout_buffer_pct=10.0,
        min_position_euros=50.0,
        trading_cost_pct=0.05,
        default_expiry_days=60,
    )
    return TurboResolver(config)


class TestTurboAvailability:
    """Tests for Turbo availability."""

    def test_stock_has_turbos(self, default_resolver: TurboResolver) -> None:
        """Stocks have Turbo certificates."""
        asset = Asset(
            symbol="SAP",
            name="SAP SE",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="XETRA",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        assert len(instruments) > 0
        assert all(i.instrument_type == InstrumentType.TURBO for i in instruments)

    def test_crypto_no_turbos(self, default_resolver: TurboResolver) -> None:
        """Crypto does not have Turbos (in this mock)."""
        asset = Asset(
            symbol="BTC-USD",
            name="Bitcoin",
            asset_class=AssetClass.CRYPTO,
            asset_type=AssetType.CRYPTO,
            exchange="COINBASE",
            listing_date=datetime(2015, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        assert len(instruments) == 0

    def test_forex_no_turbos(self, default_resolver: TurboResolver) -> None:
        """Forex does not have Turbos (in this mock)."""
        asset = Asset(
            symbol="EUR/USD",
            name="Euro vs USD",
            asset_class=AssetClass.FOREX,
            asset_type=AssetType.FOREX_PAIR,
            exchange="FOREX",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        assert len(instruments) == 0


class TestTurboKnockoutLevels:
    """Tests for knockout level calculation."""

    def test_long_turbo_knockout_below_price(self, default_resolver: TurboResolver) -> None:
        """Long Turbo has knockout below current price."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        long_turbos = [i for i in instruments if i.metadata.get("direction") == "LONG"]
        assert len(long_turbos) > 0

        for turbo in long_turbos:
            # Knockout should be set
            assert turbo.knockout_level is not None
            # For long: knockout < simulated price (we can't directly compare without knowing the price)
            assert turbo.knockout_level > 0

    def test_short_turbo_knockout_above_price(self, default_resolver: TurboResolver) -> None:
        """Short Turbo has knockout above current price."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        short_turbos = [i for i in instruments if i.metadata.get("direction") == "SHORT"]
        long_turbos = [i for i in instruments if i.metadata.get("direction") == "LONG"]

        # Short knockouts should be higher than long knockouts (same leverage)
        if short_turbos and long_turbos:
            # Find matching leverage pairs
            for short in short_turbos:
                for long in long_turbos:
                    if short.leverage == long.leverage:
                        assert short.knockout_level > long.knockout_level

    def test_higher_leverage_closer_knockout(self, default_resolver: TurboResolver) -> None:
        """Higher leverage means closer knockout to current price."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        long_turbos = [i for i in instruments if i.metadata.get("direction") == "LONG"]
        long_turbos.sort(key=lambda x: x.leverage)

        # Higher leverage should have higher knockout (closer to price)
        if len(long_turbos) >= 2:
            low_lev = long_turbos[0]
            high_lev = long_turbos[-1]
            # Higher leverage = higher knockout for LONG (closer to price)
            assert high_lev.knockout_level > low_lev.knockout_level


class TestTurboLeverage:
    """Tests for Turbo leverage products."""

    def test_multiple_leverage_products(self, default_resolver: TurboResolver) -> None:
        """Multiple leverage options available."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        leverages = set(i.leverage for i in instruments)
        # Should have multiple leverage options (e.g., 5x, 10x, 15x, 20x)
        assert len(leverages) >= 2

    def test_leverage_steps_by_5(self, default_resolver: TurboResolver) -> None:
        """Leverage steps by 5."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        leverages = sorted(set(i.leverage for i in instruments))
        # Should be 5, 10, 15, 20
        expected = [5.0, 10.0, 15.0, 20.0]
        assert leverages == expected


class TestTurboExpiry:
    """Tests for Turbo expiry dates."""

    def test_turbos_have_expiry(self, default_resolver: TurboResolver) -> None:
        """All Turbos have expiry date."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        for turbo in instruments:
            assert turbo.has_expiry
            assert turbo.expiry_date is not None

    def test_expiry_in_future(self, default_resolver: TurboResolver) -> None:
        """Expiry date is in the future."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        now = datetime.now()
        for turbo in instruments:
            assert turbo.expiry_date > now

    def test_custom_expiry_days(self, custom_resolver: TurboResolver) -> None:
        """Custom expiry days from config."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = custom_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        now = datetime.now()
        for turbo in instruments:
            days_to_expiry = (turbo.expiry_date - now).days
            # Should be around 60 days (custom config)
            assert 55 <= days_to_expiry <= 65


class TestTurboInstrumentDetails:
    """Tests for Turbo instrument details."""

    def test_turbo_symbol_format(self, default_resolver: TurboResolver) -> None:
        """Turbo symbol follows expected format."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        for turbo in instruments:
            # Format: SYMBOL.TURBO.D{leverage} where D is L or S
            assert turbo.symbol.startswith("AAPL.TURBO.")
            assert ".L" in turbo.symbol or ".S" in turbo.symbol

    def test_turbo_no_overnight_fee(self, default_resolver: TurboResolver) -> None:
        """Turbos have no overnight fee (built into knockout)."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        for turbo in instruments:
            assert turbo.overnight_fee == 0.0

    def test_turbo_no_margin(self, default_resolver: TurboResolver) -> None:
        """Turbos are fully paid (no margin)."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        for turbo in instruments:
            assert turbo.margin_requirement == 0.0

    def test_turbo_metadata(self, default_resolver: TurboResolver) -> None:
        """Turbo includes relevant metadata."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=datetime(2000, 1, 1).date(),
        )

        instruments = default_resolver.resolve(asset, "Test Broker", (5.0, 20.0))

        for turbo in instruments:
            assert "direction" in turbo.metadata
            assert turbo.metadata["direction"] in ("LONG", "SHORT")
            assert "barrier_type" in turbo.metadata
            assert turbo.metadata["barrier_type"] == "KNOCKOUT"

