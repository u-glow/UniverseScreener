"""
Derivative Resolver - Main Entry Point.

This module provides the DerivativeResolver which coordinates
multiple instrument resolution strategies to find tradable
instruments for underlying assets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING

from universe_screener.derivatives.entities import InstrumentType, TradableInstrument
from universe_screener.derivatives.strategies import (
    CFDResolver,
    TurboResolver,
    FutureResolver,
    InstrumentResolverStrategy,
)
from universe_screener.domain.entities import Asset

if TYPE_CHECKING:
    from universe_screener.config.models import DerivativeConfig

logger = logging.getLogger(__name__)


@dataclass
class InstrumentFilter:
    """Criteria for filtering tradable instruments."""

    instrument_types: List[InstrumentType] = field(default_factory=list)
    min_leverage: float = 1.0
    max_leverage: float = 100.0
    brokers: List[str] = field(default_factory=list)
    max_trading_costs: float = 1.0  # Max 1% trading cost
    require_short_selling: bool = False
    exclude_expiring_within_days: int = 0

    def matches(self, instrument: TradableInstrument) -> bool:
        """Check if instrument matches filter criteria."""
        # Type filter
        if self.instrument_types and instrument.instrument_type not in self.instrument_types:
            return False

        # Leverage filter
        if instrument.leverage < self.min_leverage:
            return False
        if instrument.leverage > self.max_leverage:
            return False

        # Broker filter
        if self.brokers and instrument.broker not in self.brokers:
            return False

        # Cost filter
        if instrument.trading_costs > self.max_trading_costs:
            return False

        # Short selling filter
        if self.require_short_selling:
            short_allowed = instrument.metadata.get("short_selling", True)
            if not short_allowed:
                return False

        # Expiry filter
        if self.exclude_expiring_within_days > 0 and instrument.has_expiry:
            from datetime import datetime, timedelta
            cutoff = datetime.now() + timedelta(days=self.exclude_expiring_within_days)
            if instrument.expiry_date and instrument.expiry_date < cutoff:
                return False

        return True


class DerivativeResolverProtocol(Protocol):
    """Protocol for derivative resolution."""

    def get_tradable_instruments(
        self,
        underlyings: List[Asset],
        filter_criteria: Optional[InstrumentFilter] = None,
    ) -> Dict[str, List[TradableInstrument]]:
        """
        Get tradable instruments for underlying assets.

        Args:
            underlyings: List of underlying assets
            filter_criteria: Optional filter for instruments

        Returns:
            Dictionary mapping underlying symbol to list of instruments
        """
        ...


class DerivativeResolver:
    """
    Main resolver for finding tradable derivative instruments.
    
    Coordinates multiple instrument resolution strategies and
    applies filtering to find suitable trading instruments.
    
    Usage:
        resolver = DerivativeResolver(config)
        instruments = resolver.get_tradable_instruments(
            underlyings,
            filter_criteria=InstrumentFilter(
                instrument_types=[InstrumentType.CFD],
                min_leverage=5.0,
            )
        )
    """

    def __init__(
        self,
        config: Optional["DerivativeConfig"] = None,
        strategies: Optional[List[InstrumentResolverStrategy]] = None,
    ) -> None:
        """
        Initialize resolver with configuration.

        Args:
            config: Derivative configuration
            strategies: Custom strategies (default: CFD, Turbo, Future)
        """
        self.config = config
        self._strategies: Dict[InstrumentType, InstrumentResolverStrategy] = {}

        # Initialize default strategies
        if strategies:
            for strategy in strategies:
                self._strategies[strategy.instrument_type] = strategy
        else:
            self._strategies = {
                InstrumentType.CFD: CFDResolver(),
                InstrumentType.TURBO: TurboResolver(),
                InstrumentType.FUTURE: FutureResolver(),
            }

        # Get enabled types from config
        self._enabled_types: List[InstrumentType] = []
        if config:
            self._enabled_types = [
                InstrumentType(t) for t in config.instrument_types
            ]
        else:
            self._enabled_types = list(self._strategies.keys())

        logger.info(
            f"DerivativeResolver initialized with types: "
            f"{[t.value for t in self._enabled_types]}"
        )

    def get_tradable_instruments(
        self,
        underlyings: List[Asset],
        filter_criteria: Optional[InstrumentFilter] = None,
    ) -> Dict[str, List[TradableInstrument]]:
        """
        Get tradable instruments for underlying assets.

        Args:
            underlyings: List of underlying assets
            filter_criteria: Optional filter for instruments

        Returns:
            Dictionary mapping underlying symbol to list of instruments
        """
        if not underlyings:
            return {}

        # Build filter from config if not provided
        if filter_criteria is None:
            filter_criteria = self._build_filter_from_config()

        result: Dict[str, List[TradableInstrument]] = {}
        leverage_range = (filter_criteria.min_leverage, filter_criteria.max_leverage)

        # Get brokers
        brokers = filter_criteria.brokers or self._get_default_brokers()

        for underlying in underlyings:
            instruments: List[TradableInstrument] = []

            for inst_type in self._enabled_types:
                strategy = self._strategies.get(inst_type)
                if not strategy:
                    continue

                # Skip if type not in filter
                if filter_criteria.instrument_types:
                    if inst_type not in filter_criteria.instrument_types:
                        continue

                # Resolve for each broker
                for broker in brokers:
                    try:
                        resolved = strategy.resolve(
                            underlying, broker, leverage_range
                        )
                        instruments.extend(resolved)
                    except Exception as e:
                        logger.warning(
                            f"Failed to resolve {inst_type.value} for "
                            f"{underlying.symbol} at {broker}: {e}"
                        )

            # Apply filter
            filtered = [i for i in instruments if filter_criteria.matches(i)]
            
            if filtered:
                result[underlying.symbol] = filtered

        logger.info(
            f"Resolved instruments for {len(result)}/{len(underlyings)} underlyings"
        )
        return result

    def get_best_instrument(
        self,
        underlying: Asset,
        filter_criteria: Optional[InstrumentFilter] = None,
        prefer_type: Optional[InstrumentType] = None,
    ) -> Optional[TradableInstrument]:
        """
        Get the best tradable instrument for an underlying.

        Args:
            underlying: Underlying asset
            filter_criteria: Optional filter
            prefer_type: Preferred instrument type

        Returns:
            Best instrument or None if none available
        """
        instruments = self.get_tradable_instruments(
            [underlying], filter_criteria
        ).get(underlying.symbol, [])

        if not instruments:
            return None

        # Sort by preference
        def score(inst: TradableInstrument) -> float:
            score = 0.0
            
            # Prefer requested type
            if prefer_type and inst.instrument_type == prefer_type:
                score += 100.0
            
            # Lower costs are better
            score -= inst.trading_costs * 10
            
            # Higher leverage (within limits) is often preferred
            score += min(inst.leverage, 10.0)
            
            return score

        instruments.sort(key=score, reverse=True)
        return instruments[0]

    def _build_filter_from_config(self) -> InstrumentFilter:
        """Build filter from configuration."""
        if not self.config:
            return InstrumentFilter()

        return InstrumentFilter(
            instrument_types=[InstrumentType(t) for t in self.config.instrument_types],
            min_leverage=self.config.min_leverage,
            max_leverage=self.config.max_leverage,
            brokers=self.config.brokers,
        )

    def _get_default_brokers(self) -> List[str]:
        """Get default broker list."""
        if self.config and self.config.brokers:
            return self.config.brokers
        return ["Interactive Brokers"]

    def register_strategy(
        self,
        strategy: InstrumentResolverStrategy,
    ) -> None:
        """
        Register a custom resolution strategy.

        Args:
            strategy: Strategy instance
        """
        self._strategies[strategy.instrument_type] = strategy
        if strategy.instrument_type not in self._enabled_types:
            self._enabled_types.append(strategy.instrument_type)
        logger.info(f"Registered strategy for {strategy.instrument_type.value}")

    @property
    def available_types(self) -> List[InstrumentType]:
        """Get list of available instrument types."""
        return list(self._strategies.keys())

    @property
    def enabled_types(self) -> List[InstrumentType]:
        """Get list of enabled instrument types."""
        return self._enabled_types

