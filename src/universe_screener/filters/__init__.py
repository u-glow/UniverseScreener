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
    - CryptoLiquidityStrategy: Order book depth, slippage (future)
    - ForexLiquidityStrategy: Spread in pips (future)

Design Principles:
    - Each filter is independently testable
    - Configuration injected via constructor
    - Stateless filtering (all state via DataContext)
    - Clear rejection reasons for audit trail
"""

# TODO: Implement - Export filter classes after implementation

