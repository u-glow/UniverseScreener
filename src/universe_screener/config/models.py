"""
Configuration Models - Pydantic Models for Type-Safe Config.

All configuration is validated at load time using Pydantic.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class GlobalConfig(BaseModel):
    """Global configuration settings."""

    default_lookback_days: int = Field(default=60, ge=1, le=365)
    timezone: str = Field(default="UTC")
    batch_size_mb: int = Field(default=2000, ge=100)


class StructuralFilterConfig(BaseModel):
    """Configuration for structural filter."""

    enabled: bool = True
    allowed_asset_types: List[str] = Field(default_factory=lambda: ["COMMON_STOCK"])
    allowed_exchanges: List[str] = Field(
        default_factory=lambda: ["NYSE", "NASDAQ", "XETRA"]
    )
    min_listing_age_days: int = Field(default=252, ge=0)


class StockLiquidityConfig(BaseModel):
    """Stock-specific liquidity configuration."""

    min_avg_dollar_volume_usd: float = Field(default=5_000_000, ge=0)
    min_trading_days_pct: float = Field(default=0.95, ge=0, le=1)
    lookback_days: int = Field(default=60, ge=1)


class CryptoLiquidityConfig(BaseModel):
    """Crypto-specific liquidity configuration."""

    max_slippage_pct: float = Field(default=0.5, ge=0, le=100)
    min_order_book_depth_usd: float = Field(default=100_000, ge=0)


class ForexLiquidityConfig(BaseModel):
    """Forex-specific liquidity configuration."""

    max_spread_pips: float = Field(default=3.0, ge=0)


class LiquidityFilterConfig(BaseModel):
    """Configuration for liquidity filter."""

    enabled: bool = True
    stock: StockLiquidityConfig = Field(default_factory=StockLiquidityConfig)
    crypto: CryptoLiquidityConfig = Field(default_factory=CryptoLiquidityConfig)
    forex: ForexLiquidityConfig = Field(default_factory=ForexLiquidityConfig)


class DataQualityFilterConfig(BaseModel):
    """Configuration for data quality filter."""

    enabled: bool = True
    max_missing_days: int = Field(default=3, ge=0)
    min_news_articles: Optional[int] = Field(default=None, ge=0)
    lookback_days: int = Field(default=60, ge=1)


class HealthMonitorConfig(BaseModel):
    """Configuration for health monitoring."""

    enabled: bool = True
    max_ram_usage_pct: float = Field(default=80.0, ge=0, le=100)
    max_context_size_mb: int = Field(default=2000, ge=100)
    min_output_universe_size: int = Field(default=10, ge=0)
    max_reduction_ratio: float = Field(default=0.99, ge=0, le=1)


class ScreeningConfig(BaseModel):
    """Root configuration object."""

    version: str = "1.0"
    global_settings: GlobalConfig = Field(
        default_factory=GlobalConfig,
        alias="global",
    )
    structural_filter: StructuralFilterConfig = Field(
        default_factory=StructuralFilterConfig,
    )
    liquidity_filter: LiquidityFilterConfig = Field(
        default_factory=LiquidityFilterConfig,
    )
    data_quality_filter: DataQualityFilterConfig = Field(
        default_factory=DataQualityFilterConfig,
    )
    health_monitoring: HealthMonitorConfig = Field(
        default_factory=HealthMonitorConfig,
    )

    model_config = {"populate_by_name": True}
