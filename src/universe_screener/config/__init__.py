"""
Configuration Package - Models and Loaders.

This package handles all configuration aspects of the Universe Screener:
    - Pydantic models for type-safe configuration
    - YAML loader with validation
    - Support for configuration profiles

Configuration Structure:
    - ScreeningConfig: Root configuration object
    - GlobalConfig: Global settings (lookback, timezone)
    - StructuralFilterConfig: Structural filter settings
    - LiquidityFilterConfig: Liquidity filter settings
    - DataQualityFilterConfig: Data quality filter settings

Design Principles:
    - Type-safe via Pydantic
    - Validation on load (fail fast)
    - Support for profiles (conservative, aggressive)
    - Environment variable overrides (future)
"""

# TODO: Implement - Export config classes after implementation

