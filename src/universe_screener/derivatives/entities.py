"""
Derivative Entities - Core Domain Objects.

This module defines the core entities for derivative instruments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from universe_screener.domain.entities import Asset


class InstrumentType(str, Enum):
    """Type of derivative instrument."""

    CFD = "CFD"  # Contract for Difference
    TURBO = "TURBO"  # Turbo/Knockout Certificate
    FUTURE = "FUTURE"  # Exchange-traded Future
    OPTION = "OPTION"  # Exchange-traded Option
    WARRANT = "WARRANT"  # Covered Warrant
    MINI_FUTURE = "MINI_FUTURE"  # Mini Future
    ETF = "ETF"  # Leveraged ETF (not strictly derivative)


@dataclass(frozen=True)
class TradableInstrument:
    """
    Represents a tradable derivative instrument.

    This entity maps an underlying asset to a specific tradable product
    offered by a broker, including all relevant trading parameters.

    Attributes:
        underlying: The underlying asset
        instrument_type: Type of derivative (CFD, TURBO, etc.)
        leverage: Leverage factor (e.g., 10.0 for 10x leverage)
        broker: Broker offering this instrument
        trading_costs: Total trading cost as percentage (spread + commission)
        min_position_size: Minimum position size in underlying units
        symbol: Broker-specific symbol for the instrument
        currency: Trading currency
        margin_requirement: Required margin as percentage
        overnight_fee: Daily financing cost as percentage
        expiry_date: Expiration date (for time-limited instruments)
        knockout_level: Knockout/barrier level (for Turbos)
        strike_price: Strike price (for options/warrants)
        metadata: Additional broker-specific metadata
    """

    underlying: Asset
    instrument_type: InstrumentType
    leverage: float
    broker: str
    trading_costs: float  # As percentage (e.g., 0.1 for 0.1%)
    min_position_size: float
    symbol: str = ""
    currency: str = "USD"
    margin_requirement: float = 0.0  # As percentage
    overnight_fee: float = 0.0  # Daily fee as percentage
    expiry_date: Optional[datetime] = None
    knockout_level: Optional[float] = None
    strike_price: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate instrument parameters."""
        if self.leverage < 1.0:
            raise ValueError(f"Leverage must be >= 1.0, got {self.leverage}")
        if self.trading_costs < 0:
            raise ValueError(f"Trading costs must be >= 0, got {self.trading_costs}")
        if self.min_position_size <= 0:
            raise ValueError(
                f"Min position size must be > 0, got {self.min_position_size}"
            )

    @property
    def is_leveraged(self) -> bool:
        """Check if instrument is leveraged."""
        return self.leverage > 1.0

    @property
    def has_expiry(self) -> bool:
        """Check if instrument has expiry date."""
        return self.expiry_date is not None

    @property
    def has_knockout(self) -> bool:
        """Check if instrument has knockout level."""
        return self.knockout_level is not None

    @property
    def effective_leverage(self) -> float:
        """Calculate effective leverage considering margin."""
        if self.margin_requirement > 0:
            return 100.0 / self.margin_requirement
        return self.leverage

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "underlying_symbol": self.underlying.symbol,
            "underlying_name": self.underlying.name,
            "instrument_type": self.instrument_type.value,
            "leverage": self.leverage,
            "broker": self.broker,
            "trading_costs": self.trading_costs,
            "min_position_size": self.min_position_size,
            "symbol": self.symbol,
            "currency": self.currency,
            "margin_requirement": self.margin_requirement,
            "overnight_fee": self.overnight_fee,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "knockout_level": self.knockout_level,
            "strike_price": self.strike_price,
            "metadata": self.metadata,
        }

