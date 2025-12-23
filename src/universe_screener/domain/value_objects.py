"""
Value Objects for Domain Layer.

Value objects are immutable objects that describe characteristics of entities
but have no conceptual identity.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


# =============================================================================
# Type Aliases for improved readability
# =============================================================================

# Market data indexed by asset symbol
MarketDataDict = Dict[str, List["MarketData"]]

# Asset metadata indexed by symbol
MetadataDict = Dict[str, Dict[str, Any]]

# Quality metrics indexed by symbol
QualityMetricsDict = Dict[str, "QualityMetrics"]

# Rejection reasons: symbol -> reason string
RejectionReasonsDict = Dict[str, str]


class MarketData(BaseModel):
    """OHLCV market data point."""

    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    model_config = {"frozen": True}

    @computed_field
    @property
    def dollar_volume(self) -> float:
        """Calculate dollar volume (close * volume)."""
        return self.close * self.volume


class QualityMetrics(BaseModel):
    """Data quality indicators for an asset."""

    missing_days: int = Field(ge=0)
    last_available_date: datetime
    news_article_count: Optional[int] = Field(default=None, ge=0)

    model_config = {"frozen": True}


class FilterResult(BaseModel):
    """Result of applying a single filter stage."""

    passed_assets: List[str] = Field(
        default_factory=list, description="Symbols of passed assets"
    )
    rejected_assets: List[str] = Field(
        default_factory=list, description="Symbols of rejected assets"
    )
    rejection_reasons: Dict[str, str] = Field(
        default_factory=dict, description="Symbol -> rejection reason"
    )

    model_config = {"frozen": True}

    @property
    def passed_count(self) -> int:
        return len(self.passed_assets)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_assets)
