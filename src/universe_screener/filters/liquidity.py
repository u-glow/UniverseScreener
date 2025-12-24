"""
Liquidity Filter Implementation.

Filters assets based on tradability metrics. Uses the Strategy Pattern
to support different liquidity checks per asset class.

Supported Asset Classes:
    - STOCK: Dollar volume, trading days
    - CRYPTO: Order book depth, slippage
    - FOREX: Spread in pips, 24/5 availability
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Protocol, Tuple

from universe_screener.domain.entities import Asset, AssetClass
from universe_screener.domain.value_objects import FilterResult, MarketData
from universe_screener.config.models import LiquidityFilterConfig
from universe_screener.filters.liquidity_strategies import (
    StockLiquidityStrategy,
    CryptoLiquidityStrategy,
    ForexLiquidityStrategy,
    LiquidityStrategy,
)

if TYPE_CHECKING:
    from universe_screener.pipeline.data_context import DataContext

logger = logging.getLogger(__name__)


class LiquidityFilter:
    """
    Filter assets by liquidity metrics.
    
    Uses Strategy Pattern to apply asset-class specific liquidity checks.
    Strategies are injected via config and can be extended for new asset classes.
    """

    def __init__(self, config: LiquidityFilterConfig) -> None:
        """
        Initialize with configuration.

        Args:
            config: Liquidity filter configuration
        """
        self.config = config
        self._strategies: Dict[AssetClass, LiquidityStrategy] = {
            AssetClass.STOCK: StockLiquidityStrategy(config.stock),
            AssetClass.CRYPTO: CryptoLiquidityStrategy(config.crypto),
            AssetClass.FOREX: ForexLiquidityStrategy(config.forex),
        }

    @property
    def name(self) -> str:
        """Unique name of this filter stage."""
        return "liquidity_filter"

    def apply(
        self,
        assets: List[Asset],
        date: datetime,
        context: "DataContext",
    ) -> FilterResult:
        """
        Apply liquidity filtering using asset-class specific strategies.

        Args:
            assets: Assets to filter
            date: Reference date
            context: Data context with market data

        Returns:
            FilterResult with passed/rejected assets
        """
        if not self.config.enabled:
            return FilterResult(
                passed_assets=[a.symbol for a in assets],
                rejected_assets=[],
                rejection_reasons={},
            )

        passed: List[str] = []
        rejected: List[str] = []
        reasons: Dict[str, str] = {}

        for asset in assets:
            strategy = self._strategies.get(asset.asset_class)
            if strategy is None:
                # No strategy for this asset class, skip filtering
                passed.append(asset.symbol)
                continue

            market_data = context.get_market_data(asset.symbol)
            is_valid, reason = strategy.check_liquidity(asset, market_data)

            if is_valid:
                passed.append(asset.symbol)
            else:
                rejected.append(asset.symbol)
                reasons[asset.symbol] = reason

        return FilterResult(
            passed_assets=passed,
            rejected_assets=rejected,
            rejection_reasons=reasons,
        )
