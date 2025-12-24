"""
Core Domain Entities.

This module defines the fundamental entities of the Universe Screener domain.
These entities represent the core concepts that the business logic operates on.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssetClass(str, Enum):
    """Classification of financial assets."""

    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"


class AssetType(str, Enum):
    """Type of financial asset."""

    # Stock types
    COMMON_STOCK = "COMMON_STOCK"
    ETF = "ETF"
    ADR = "ADR"
    PREFERRED = "PREFERRED"
    
    # Crypto types
    CRYPTO = "CRYPTO"
    STABLECOIN = "STABLECOIN"
    
    # Forex types
    FOREX_PAIR = "FOREX_PAIR"
    FOREX_CROSS = "FOREX_CROSS"


class Asset(BaseModel):
    """Represents a tradable financial instrument."""

    symbol: str = Field(..., description="Ticker symbol")
    name: str = Field(..., description="Full company/asset name")
    asset_class: AssetClass = Field(..., description="Asset classification")
    asset_type: AssetType = Field(
        default=AssetType.COMMON_STOCK, description="Specific asset type"
    )
    exchange: str = Field(..., description="Trading exchange")
    listing_date: date = Field(..., description="Date when asset was listed")
    delisting_date: Optional[date] = Field(
        default=None, description="Date when asset was delisted"
    )
    isin: Optional[str] = Field(default=None, description="ISIN identifier")
    sector: Optional[str] = Field(default=None, description="Industry sector")
    country: Optional[str] = Field(default=None, description="Country of domicile")

    model_config = {"frozen": True}

    def __hash__(self) -> int:
        return hash(self.symbol)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Asset):
            return NotImplemented
        return self.symbol == other.symbol


class ScreeningRequest(BaseModel):
    """Input for a screening operation."""

    date: datetime = Field(..., description="Point-in-time for screening")
    asset_class: AssetClass = Field(..., description="Asset class to screen")
    config_override: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional config overrides"
    )
    correlation_id: str = Field(..., description="Unique request identifier")

    model_config = {"frozen": True}


class StageResult(BaseModel):
    """Result of a single filter stage for audit trail."""

    stage_name: str
    input_count: int
    output_count: int
    duration_seconds: float
    filtered_assets: List[str] = Field(
        default_factory=list, description="Symbols of filtered assets"
    )
    filter_reasons: Dict[str, str] = Field(
        default_factory=dict, description="Symbol -> rejection reason"
    )

    @property
    def reduction_ratio(self) -> float:
        """Calculate reduction ratio (0.0 = no reduction, 1.0 = all filtered)."""
        if self.input_count == 0:
            return 0.0
        return 1.0 - (self.output_count / self.input_count)


class ScreeningResult(BaseModel):
    """Complete result of a screening run."""

    request: ScreeningRequest
    input_universe: List[Asset]
    output_universe: List[Asset]
    audit_trail: List[StageResult] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def total_reduction_ratio(self) -> float:
        """Calculate total reduction ratio."""
        if len(self.input_universe) == 0:
            return 0.0
        return 1.0 - (len(self.output_universe) / len(self.input_universe))
