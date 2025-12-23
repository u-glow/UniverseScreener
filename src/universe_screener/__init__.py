"""
Universe Screener - Multi-Stage Asset Filtering Pipeline.

A high-performance system for filtering large asset universes based on
liquidity, data quality, and structural criteria. Designed for trading
systems that need to reduce computational overhead by focusing on
tradable, liquid assets.

Architecture:
    - Hexagonal Architecture (Ports & Adapters)
    - Dependency Injection for testability
    - Strategy Pattern for asset-class specific logic
    - Configuration-driven behavior via YAML

Main Components:
    - domain: Core entities (Asset, ScreeningResult, etc.)
    - interfaces: Abstract protocols for all dependencies
    - filters: Concrete filter implementations
    - pipeline: Orchestration and data context
    - adapters: Infrastructure implementations (providers, loggers)
    - config: Configuration models and loaders

Example:
    >>> from universe_screener import ScreeningPipeline
    >>> pipeline = create_pipeline(config_path="config/default.yaml")
    >>> result = pipeline.screen(date=date(2024, 1, 15), asset_class=AssetClass.STOCK)
    >>> print(f"Filtered {len(result.output_universe)} assets")

"""

__version__ = "0.1.0"

# TODO: Implement - Export main components after implementation

