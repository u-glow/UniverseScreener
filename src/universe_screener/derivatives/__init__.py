"""
Derivatives Module - Tradable Instrument Resolution.

This module provides functionality to map underlying assets to tradable
derivative instruments (CFDs, Turbos, Futures, Options).

Components:
    - TradableInstrument: Entity representing a tradable derivative
    - InstrumentType: Enum for derivative types
    - DerivativeResolver: Resolves underlyings to tradable instruments
    - CFDResolver: Strategy for CFD resolution
    - TurboResolver: Strategy for Turbo certificate resolution
    - FutureResolver: Strategy for futures resolution
"""

from universe_screener.derivatives.entities import (
    TradableInstrument,
    InstrumentType,
)
from universe_screener.derivatives.derivative_resolver import (
    DerivativeResolver,
    DerivativeResolverProtocol,
    InstrumentFilter,
)
from universe_screener.derivatives.strategies import (
    CFDResolver,
    TurboResolver,
    FutureResolver,
    InstrumentResolverStrategy,
)

__all__ = [
    "TradableInstrument",
    "InstrumentType",
    "DerivativeResolver",
    "DerivativeResolverProtocol",
    "InstrumentFilter",
    "CFDResolver",
    "TurboResolver",
    "FutureResolver",
    "InstrumentResolverStrategy",
]

