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

import logging

__version__ = "0.3.0"  # Phase 2 with observability


def configure_logging(
    level: int = logging.INFO,
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
) -> None:
    """
    Configure logging for Universe Screener.

    Call this at application startup to see log messages.
    By default, only WARNING and above are visible.

    Args:
        level: Logging level (default: INFO)
        format: Log message format

    Example:
        >>> import universe_screener
        >>> universe_screener.configure_logging(logging.DEBUG)
    """
    logging.basicConfig(
        level=level,
        format=format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Set our package's logger
    logging.getLogger("universe_screener").setLevel(level)


# TODO: Export main components after implementation
