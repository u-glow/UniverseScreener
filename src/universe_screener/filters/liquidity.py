"""
Liquidity Filter Implementation.

Filters assets based on tradability metrics. Uses the Strategy Pattern
to support different liquidity checks per asset class.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Protocol, Tuple

from universe_screener.domain.entities import Asset, AssetClass
from universe_screener.domain.value_objects import FilterResult, MarketData
from universe_screener.config.models import LiquidityFilterConfig, StockLiquidityConfig

if TYPE_CHECKING:
    from universe_screener.pipeline.data_context import DataContext


class LiquidityStrategy(Protocol):
    """Strategy protocol for asset-class specific liquidity checks."""

    def check_liquidity(
        self,
        asset: Asset,
        market_data: List[MarketData],
    ) -> Tuple[bool, str]:
        """Check if asset meets liquidity requirements."""
        ...


class StockLiquidityStrategy:
    """Liquidity strategy for stocks."""

    def __init__(self, config: StockLiquidityConfig) -> None:
        self.config = config

    def check_liquidity(
        self,
        asset: Asset,
        market_data: List[MarketData],
    ) -> Tuple[bool, str]:
        """
        Check stock liquidity.

        Metrics:
            - Average dollar volume over lookback period
            - Percentage of trading days with data
        """
        if not market_data:
            return False, "no market data available"

        # Calculate average dollar volume
        dollar_volumes = [d.dollar_volume for d in market_data]
        avg_dollar_volume = sum(dollar_volumes) / len(dollar_volumes)

        # Calculate trading days percentage
        # Assume 252 trading days per year, proportional for lookback
        expected_days = int(self.config.lookback_days * (252 / 365))
        actual_days = len(market_data)
        trading_days_pct = actual_days / expected_days if expected_days > 0 else 0

        # Check thresholds
        if avg_dollar_volume < self.config.min_avg_dollar_volume_usd:
            return (
                False,
                f"avg_dollar_volume=${avg_dollar_volume:,.0f} < min=${self.config.min_avg_dollar_volume_usd:,.0f}",
            )

        if trading_days_pct < self.config.min_trading_days_pct:
            return (
                False,
                f"trading_days_pct={trading_days_pct:.2%} < min={self.config.min_trading_days_pct:.2%}",
            )

        return True, ""


class LiquidityFilter:
    """Filter assets by liquidity metrics."""

    def __init__(self, config: LiquidityFilterConfig) -> None:
        """
        Initialize with configuration.

        Args:
            config: Liquidity filter configuration
        """
        self.config = config
        self._strategies: Dict[AssetClass, LiquidityStrategy] = {
            AssetClass.STOCK: StockLiquidityStrategy(config.stock),
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
