"""
Structural Filter Implementation.

Filters assets based on structural properties:
    - Asset type (e.g., only COMMON_STOCK)
    - Exchange (e.g., NYSE, NASDAQ, XETRA)
    - Listing age (e.g., min 252 trading days)
    - Delisting status (exclude delisted assets)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Tuple

from universe_screener.domain.entities import Asset
from universe_screener.domain.value_objects import FilterResult
from universe_screener.config.models import StructuralFilterConfig

if TYPE_CHECKING:
    from universe_screener.pipeline.data_context import DataContext


class StructuralFilter:
    """Filter assets by structural properties."""

    def __init__(self, config: StructuralFilterConfig) -> None:
        """
        Initialize with configuration.

        Args:
            config: Structural filter configuration
        """
        self.config = config

    @property
    def name(self) -> str:
        """Unique name of this filter stage."""
        return "structural_filter"

    def apply(
        self,
        assets: List[Asset],
        date: datetime,
        context: "DataContext",
    ) -> FilterResult:
        """
        Apply structural filtering.

        Checks:
            1. Asset type in allowed list
            2. Exchange in allowed list
            3. Listing age >= threshold
            4. Not delisted at date

        Args:
            assets: Assets to filter
            date: Reference date
            context: Data context (unused for structural filter)

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

        # Convert datetime to date for comparison with Asset.listing_date
        ref_date = date.date()

        for asset in assets:
            is_valid, reason = self._check_asset(asset, ref_date)
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

    def _check_asset(self, asset: Asset, ref_date) -> Tuple[bool, str]:
        """Check if a single asset passes structural requirements."""
        # Check asset type
        if asset.asset_type.value not in self.config.allowed_asset_types:
            return False, f"asset_type={asset.asset_type.value} not in allowed list"

        # Check exchange
        if asset.exchange not in self.config.allowed_exchanges:
            return False, f"exchange={asset.exchange} not in allowed list"

        # Check listing age
        listing_age_days = (ref_date - asset.listing_date).days
        if listing_age_days < self.config.min_listing_age_days:
            return (
                False,
                f"listing_age={listing_age_days}d < min={self.config.min_listing_age_days}d",
            )

        # Check delisting status
        if asset.delisting_date is not None and asset.delisting_date <= ref_date:
            return False, f"delisted on {asset.delisting_date}"

        return True, ""
