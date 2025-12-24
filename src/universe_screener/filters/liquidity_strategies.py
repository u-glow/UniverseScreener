"""
Liquidity Strategies - Asset-Class Specific Liquidity Checks.

Provides Strategy Pattern implementations for different asset classes:
    - StockLiquidityStrategy: Dollar volume, trading days
    - CryptoLiquidityStrategy: Order book depth, slippage estimation
    - ForexLiquidityStrategy: Spread in pips, 24/5 availability

Design Notes:
    - Each strategy checks liquidity using asset-class specific metrics
    - Strategies are mock-based for now (real data integration later)
    - Thresholds come from config (DI via constructor)
"""

from __future__ import annotations

import logging
from typing import List, Protocol, Tuple

from universe_screener.domain.entities import Asset
from universe_screener.domain.value_objects import MarketData
from universe_screener.config.models import (
    CryptoLiquidityConfig,
    ForexLiquidityConfig,
    StockLiquidityConfig,
)

logger = logging.getLogger(__name__)


class LiquidityStrategy(Protocol):
    """Strategy protocol for asset-class specific liquidity checks."""

    def check_liquidity(
        self,
        asset: Asset,
        market_data: List[MarketData],
    ) -> Tuple[bool, str]:
        """
        Check if asset meets liquidity requirements.
        
        Args:
            asset: Asset to check
            market_data: Market data for the asset
            
        Returns:
            Tuple of (is_liquid, rejection_reason)
        """
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


class CryptoLiquidityStrategy:
    """
    Liquidity strategy for cryptocurrencies.
    
    Metrics (simulated from market data):
        - Order book depth (estimated from volume)
        - Slippage estimate for standard order size
    
    Note: Real implementation would use actual order book data.
    For now, we simulate metrics based on volume.
    """

    def __init__(self, config: CryptoLiquidityConfig) -> None:
        self.config = config

    def check_liquidity(
        self,
        asset: Asset,
        market_data: List[MarketData],
    ) -> Tuple[bool, str]:
        """
        Check crypto liquidity.
        
        Simulates order book depth and slippage from volume data.
        """
        if not market_data:
            return False, "no market data available"

        # Calculate average daily volume
        dollar_volumes = [d.dollar_volume for d in market_data]
        avg_dollar_volume = sum(dollar_volumes) / len(dollar_volumes)

        # Simulate order book depth from volume
        # Assumption: order book depth ≈ 5% of daily volume
        estimated_depth_usd = avg_dollar_volume * 0.05

        if estimated_depth_usd < self.config.min_order_book_depth_usd:
            return (
                False,
                f"estimated_order_book_depth=${estimated_depth_usd:,.0f} < min=${self.config.min_order_book_depth_usd:,.0f}",
            )

        # Estimate slippage for $100k order
        # Simple model: slippage = order_size / (depth * 2)
        order_size_usd = 100_000
        estimated_slippage_pct = (order_size_usd / (estimated_depth_usd * 2)) * 100

        if estimated_slippage_pct > self.config.max_slippage_pct:
            return (
                False,
                f"estimated_slippage={estimated_slippage_pct:.2f}% > max={self.config.max_slippage_pct:.2f}%",
            )

        logger.debug(
            f"Crypto {asset.symbol}: depth=${estimated_depth_usd:,.0f}, "
            f"slippage={estimated_slippage_pct:.2f}%"
        )

        return True, ""


class ForexLiquidityStrategy:
    """
    Liquidity strategy for forex pairs.
    
    Metrics (simulated from market data):
        - Average spread in pips (estimated from high-low)
        - 24/5 trading availability (simulated)
    
    Note: Real implementation would use actual bid/ask spreads.
    For now, we simulate spread from price volatility.
    """

    def __init__(self, config: ForexLiquidityConfig) -> None:
        self.config = config

    def check_liquidity(
        self,
        asset: Asset,
        market_data: List[MarketData],
    ) -> Tuple[bool, str]:
        """
        Check forex liquidity.
        
        Simulates spread from high-low range.
        """
        if not market_data:
            return False, "no market data available"

        # Calculate average spread from high-low (simulated)
        # Assumption: spread ≈ 1% of average (high - low)
        spreads_pct = []
        for d in market_data:
            if d.high > 0 and d.low > 0:
                spread_pct = ((d.high - d.low) / d.close) * 0.01  # 1% of range
                spreads_pct.append(spread_pct)

        if not spreads_pct:
            return False, "cannot calculate spread from market data"

        avg_spread_pct = sum(spreads_pct) / len(spreads_pct)

        # Convert to pips (1 pip = 0.0001 for most pairs, 0.01 for JPY pairs)
        # For simplicity, assume 1 pip = 0.0001
        pip_value = 0.0001
        avg_spread_pips = avg_spread_pct / pip_value

        if avg_spread_pips > self.config.max_spread_pips:
            return (
                False,
                f"avg_spread={avg_spread_pips:.2f}pips > max={self.config.max_spread_pips:.2f}pips",
            )

        # Check 24/5 availability (simulated)
        # Requirement: Forex should have data for most trading days
        # Minimum: 30 trading days (roughly 6 weeks of 5-day weeks)
        min_trading_days = 30
        
        if len(market_data) < min_trading_days:
            return (
                False,
                f"insufficient_trading_days={len(market_data)} < min={min_trading_days}",
            )

        logger.debug(
            f"Forex {asset.symbol}: avg_spread={avg_spread_pips:.2f}pips, "
            f"trading_days={len(market_data)}"
        )

        return True, ""


# =============================================================================
# Strategy Factory
# =============================================================================

def create_liquidity_strategies(
    stock_config: StockLiquidityConfig,
    crypto_config: CryptoLiquidityConfig,
    forex_config: ForexLiquidityConfig,
) -> dict:
    """
    Factory function to create all liquidity strategies.
    
    Args:
        stock_config: Stock liquidity config
        crypto_config: Crypto liquidity config
        forex_config: Forex liquidity config
        
    Returns:
        Dict mapping AssetClass to LiquidityStrategy
    """
    from universe_screener.domain.entities import AssetClass
    
    return {
        AssetClass.STOCK: StockLiquidityStrategy(stock_config),
        AssetClass.CRYPTO: CryptoLiquidityStrategy(crypto_config),
        AssetClass.FOREX: ForexLiquidityStrategy(forex_config),
    }

