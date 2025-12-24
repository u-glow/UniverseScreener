"""
Derivative Resolution Strategies.

This module implements the Strategy Pattern for resolving different
types of derivative instruments from underlying assets.

Each strategy handles the specifics of a particular instrument type
(CFD, Turbo, Future, etc.) and generates mock data for development.
Real implementations would connect to broker APIs.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Protocol

from universe_screener.derivatives.entities import InstrumentType, TradableInstrument
from universe_screener.domain.entities import Asset

logger = logging.getLogger(__name__)


class InstrumentResolverStrategy(Protocol):
    """Protocol for instrument resolution strategies."""

    @property
    def instrument_type(self) -> InstrumentType:
        """The instrument type this strategy handles."""
        ...

    def resolve(
        self,
        underlying: Asset,
        broker: str,
        leverage_range: tuple[float, float],
    ) -> List[TradableInstrument]:
        """
        Resolve tradable instruments for an underlying asset.

        Args:
            underlying: The underlying asset
            broker: Broker name
            leverage_range: (min_leverage, max_leverage) tuple

        Returns:
            List of available tradable instruments
        """
        ...


@dataclass
class CFDConfig:
    """Configuration for CFD resolution."""

    default_spread_pct: float = 0.05  # 0.05% spread
    min_position_units: float = 1.0
    overnight_fee_pct: float = 0.01  # 0.01% daily
    margin_pct: float = 10.0  # 10% margin = 10x leverage


class CFDResolver:
    """
    Strategy for resolving CFD (Contract for Difference) instruments.
    
    CFDs are synthetic instruments that mirror the underlying price
    without owning the actual asset. They offer leverage and can be
    used for both long and short positions.
    
    Note: This is a mock implementation. Real implementation would
    connect to broker APIs (e.g., Interactive Brokers, IG, CMC Markets).
    """

    def __init__(self, config: Optional[CFDConfig] = None) -> None:
        self.config = config or CFDConfig()

    @property
    def instrument_type(self) -> InstrumentType:
        return InstrumentType.CFD

    def resolve(
        self,
        underlying: Asset,
        broker: str,
        leverage_range: tuple[float, float],
    ) -> List[TradableInstrument]:
        """
        Resolve CFD instruments for an underlying.
        
        Generates mock CFD data based on the underlying asset.
        Real implementation would query broker API.
        """
        min_leverage, max_leverage = leverage_range

        # Simulate CFD availability based on asset characteristics
        if not self._is_cfd_available(underlying):
            return []

        # Calculate leverage based on asset type and broker
        leverage = self._calculate_leverage(underlying, min_leverage, max_leverage)
        if leverage < min_leverage or leverage > max_leverage:
            return []

        # Generate CFD instrument
        cfd = TradableInstrument(
            underlying=underlying,
            instrument_type=InstrumentType.CFD,
            leverage=leverage,
            broker=broker,
            trading_costs=self._calculate_spread(underlying),
            min_position_size=self.config.min_position_units,
            symbol=f"{underlying.symbol}.CFD",
            currency="USD",
            margin_requirement=100.0 / leverage,
            overnight_fee=self.config.overnight_fee_pct,
            metadata={
                "product_type": "CFD",
                "tradable_hours": "24/5",
                "short_selling": True,
            },
        )

        logger.debug(f"Resolved CFD for {underlying.symbol}: {leverage}x leverage")
        return [cfd]

    def _is_cfd_available(self, asset: Asset) -> bool:
        """Check if CFD is available for this asset (mock)."""
        # Simulate: CFDs available for stocks and major crypto
        from universe_screener.domain.entities import AssetClass

        if asset.asset_class == AssetClass.STOCK:
            # Most stocks have CFDs
            return True
        if asset.asset_class == AssetClass.CRYPTO:
            # Only major crypto has CFDs
            major_crypto = ["BTC", "ETH", "SOL", "XRP", "ADA"]
            return any(c in asset.symbol for c in major_crypto)
        if asset.asset_class == AssetClass.FOREX:
            # All forex pairs have CFDs
            return True
        return False

    def _calculate_leverage(
        self,
        asset: Asset,
        min_lev: float,
        max_lev: float,
    ) -> float:
        """Calculate available leverage for asset (mock)."""
        from universe_screener.domain.entities import AssetClass

        # Simulate: Different leverage by asset class
        if asset.asset_class == AssetClass.STOCK:
            base_leverage = 5.0
        elif asset.asset_class == AssetClass.CRYPTO:
            base_leverage = 2.0  # Lower leverage for volatile crypto
        elif asset.asset_class == AssetClass.FOREX:
            base_leverage = 30.0  # High leverage for forex
        else:
            base_leverage = 5.0

        # Clamp to range
        return max(min_lev, min(max_lev, base_leverage))

    def _calculate_spread(self, asset: Asset) -> float:
        """Calculate spread/trading cost (mock)."""
        from universe_screener.domain.entities import AssetClass

        if asset.asset_class == AssetClass.FOREX:
            return 0.01  # Tight spreads for forex
        if asset.asset_class == AssetClass.CRYPTO:
            return 0.15  # Wider spreads for crypto
        return self.config.default_spread_pct


@dataclass
class TurboConfig:
    """Configuration for Turbo certificate resolution."""

    knockout_buffer_pct: float = 5.0  # 5% buffer from current price
    min_position_euros: float = 100.0
    trading_cost_pct: float = 0.10  # 0.1% spread
    default_expiry_days: int = 30


class TurboResolver:
    """
    Strategy for resolving Turbo/Knockout certificates.
    
    Turbos are leveraged products with a knockout barrier.
    If the underlying touches the barrier, the product expires worthless.
    Popular in European markets (Germany, Netherlands).
    
    Note: Mock implementation. Real would connect to issuers
    (e.g., Société Générale, BNP Paribas, Vontobel).
    """

    def __init__(self, config: Optional[TurboConfig] = None) -> None:
        self.config = config or TurboConfig()

    @property
    def instrument_type(self) -> InstrumentType:
        return InstrumentType.TURBO

    def resolve(
        self,
        underlying: Asset,
        broker: str,
        leverage_range: tuple[float, float],
    ) -> List[TradableInstrument]:
        """
        Resolve Turbo instruments for an underlying.
        
        Generates multiple Turbo products with different knockout levels.
        """
        min_leverage, max_leverage = leverage_range

        # Turbos mainly for stocks and indices
        if not self._is_turbo_available(underlying):
            return []

        # Generate multiple Turbo products
        instruments = []

        # Simulate current price (in real implementation, fetch from market data)
        current_price = self._get_simulated_price(underlying)

        # Generate Turbo Long and Turbo Short
        for direction in ["LONG", "SHORT"]:
            for leverage in self._get_leverage_steps(min_leverage, max_leverage):
                knockout = self._calculate_knockout(
                    current_price, leverage, direction
                )
                expiry = datetime.now() + timedelta(days=self.config.default_expiry_days)

                turbo = TradableInstrument(
                    underlying=underlying,
                    instrument_type=InstrumentType.TURBO,
                    leverage=leverage,
                    broker=broker,
                    trading_costs=self.config.trading_cost_pct,
                    min_position_size=self.config.min_position_euros,
                    symbol=f"{underlying.symbol}.TURBO.{direction[0]}{int(leverage)}",
                    currency="EUR",
                    margin_requirement=0.0,  # Turbos are fully paid
                    overnight_fee=0.0,  # No overnight (built into knockout)
                    expiry_date=expiry,
                    knockout_level=knockout,
                    metadata={
                        "direction": direction,
                        "issuer": "Mock Issuer",
                        "barrier_type": "KNOCKOUT",
                    },
                )
                instruments.append(turbo)

        logger.debug(
            f"Resolved {len(instruments)} Turbos for {underlying.symbol}"
        )
        return instruments

    def _is_turbo_available(self, asset: Asset) -> bool:
        """Check if Turbos are available (mock)."""
        from universe_screener.domain.entities import AssetClass

        # Turbos mainly for stocks on European exchanges
        return asset.asset_class == AssetClass.STOCK

    def _get_simulated_price(self, asset: Asset) -> float:
        """Get simulated current price (mock)."""
        # Generate deterministic price from symbol hash
        hash_val = int(hashlib.md5(asset.symbol.encode()).hexdigest()[:8], 16)
        return 50.0 + (hash_val % 200)  # Price between 50 and 250

    def _get_leverage_steps(
        self,
        min_lev: float,
        max_lev: float,
    ) -> List[float]:
        """Generate leverage steps within range."""
        steps = []
        current = max(min_lev, 5.0)
        while current <= max_lev:
            steps.append(current)
            current += 5.0  # Step by 5
        return steps or [min_lev]

    def _calculate_knockout(
        self,
        price: float,
        leverage: float,
        direction: str,
    ) -> float:
        """Calculate knockout level based on leverage."""
        # Higher leverage = closer knockout
        distance_pct = 100.0 / leverage
        
        if direction == "LONG":
            return price * (1 - distance_pct / 100)
        else:  # SHORT
            return price * (1 + distance_pct / 100)


@dataclass
class FutureConfig:
    """Configuration for futures resolution."""

    min_contract_value: float = 1000.0
    trading_cost_pct: float = 0.02  # 0.02% commission
    margin_pct: float = 5.0  # 5% initial margin


class FutureResolver:
    """
    Strategy for resolving exchange-traded futures.
    
    Futures are standardized contracts traded on exchanges
    (e.g., CME, EUREX). They offer leverage through margin.
    
    Note: Mock implementation. Real would connect to exchange APIs
    or data providers (e.g., CME, Interactive Brokers).
    """

    def __init__(self, config: Optional[FutureConfig] = None) -> None:
        self.config = config or FutureConfig()

    @property
    def instrument_type(self) -> InstrumentType:
        return InstrumentType.FUTURE

    def resolve(
        self,
        underlying: Asset,
        broker: str,
        leverage_range: tuple[float, float],
    ) -> List[TradableInstrument]:
        """
        Resolve futures contracts for an underlying.
        
        Generates futures with different expiry months.
        """
        min_leverage, max_leverage = leverage_range

        # Futures mainly for indices, commodities, major stocks
        if not self._is_future_available(underlying):
            return []

        instruments = []

        # Calculate leverage from margin
        leverage = 100.0 / self.config.margin_pct
        if leverage < min_leverage or leverage > max_leverage:
            return []

        # Generate front-month and next-month contracts
        for months_ahead in [1, 2, 3]:
            expiry = self._get_expiry_date(months_ahead)
            contract_code = self._get_contract_code(underlying, expiry)

            future = TradableInstrument(
                underlying=underlying,
                instrument_type=InstrumentType.FUTURE,
                leverage=leverage,
                broker=broker,
                trading_costs=self.config.trading_cost_pct,
                min_position_size=1.0,  # 1 contract
                symbol=contract_code,
                currency="USD",
                margin_requirement=self.config.margin_pct,
                overnight_fee=0.0,  # No overnight for futures
                expiry_date=expiry,
                metadata={
                    "contract_size": self._get_contract_size(underlying),
                    "tick_size": 0.01,
                    "exchange": self._get_exchange(underlying),
                },
            )
            instruments.append(future)

        logger.debug(
            f"Resolved {len(instruments)} futures for {underlying.symbol}"
        )
        return instruments

    def _is_future_available(self, asset: Asset) -> bool:
        """Check if futures are available (mock)."""
        from universe_screener.domain.entities import AssetClass

        # Futures for stocks (single stock futures) and forex
        return asset.asset_class in (AssetClass.STOCK, AssetClass.FOREX)

    def _get_expiry_date(self, months_ahead: int) -> datetime:
        """Get expiry date for contract (third Friday of month)."""
        now = datetime.now()
        target_month = now.month + months_ahead
        target_year = now.year

        while target_month > 12:
            target_month -= 12
            target_year += 1

        # Third Friday of the month
        first_day = datetime(target_year, target_month, 1)
        # Find first Friday
        days_to_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_to_friday)
        # Third Friday
        third_friday = first_friday + timedelta(weeks=2)
        
        return third_friday

    def _get_contract_code(self, asset: Asset, expiry: datetime) -> str:
        """Generate contract code."""
        month_codes = "FGHJKMNQUVXZ"
        month_code = month_codes[expiry.month - 1]
        year_code = str(expiry.year)[-1]
        return f"{asset.symbol}{month_code}{year_code}"

    def _get_contract_size(self, asset: Asset) -> int:
        """Get contract size (mock)."""
        return 100  # Standard 100 shares

    def _get_exchange(self, asset: Asset) -> str:
        """Get exchange for futures (mock)."""
        return "CME"  # Simplified

