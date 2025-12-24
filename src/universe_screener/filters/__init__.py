"""
Filters Package - Concrete Filter Implementations.

This package contains the concrete implementations of filter stages.
Each filter implements the FilterStage protocol and provides specific
filtering logic for the screening pipeline.

Filters:
    - StructuralFilter: Filters by asset properties (type, exchange, age)
    - LiquidityFilter: Filters by tradability (volume, spread)
    - DataQualityFilter: Filters by data availability

Liquidity Strategies:
    - StockLiquidityStrategy: Dollar volume, trading days
    - CryptoLiquidityStrategy: Order book depth, slippage
    - ForexLiquidityStrategy: Spread in pips

Design Principles:
    - Each filter is independently testable
    - Configuration injected via constructor
    - Stateless filtering (all state via DataContext)
    - Clear rejection reasons for audit trail
"""

from universe_screener.filters.structural import StructuralFilter
from universe_screener.filters.liquidity import LiquidityFilter
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.filters.liquidity_strategies import (
    CryptoLiquidityStrategy,
    ForexLiquidityStrategy,
    LiquidityStrategy,
    StockLiquidityStrategy,
    create_liquidity_strategies,
)

__all__ = [
    "StructuralFilter",
    "LiquidityFilter",
    "DataQualityFilter",
    "StockLiquidityStrategy",
    "CryptoLiquidityStrategy",
    "ForexLiquidityStrategy",
    "LiquidityStrategy",
    "create_liquidity_strategies",
]

