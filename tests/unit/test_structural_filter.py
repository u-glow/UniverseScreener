"""
Unit Tests for StructuralFilter.

Test Aspects Covered:
    ✅ Business Logic: Correct filtering based on criteria
    ✅ Edge Cases: Empty input, boundary conditions
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List

import pytest

from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.filters.structural import StructuralFilter
from universe_screener.config.models import StructuralFilterConfig
from universe_screener.pipeline.data_context import DataContext


@pytest.fixture
def filter_config() -> StructuralFilterConfig:
    """Create filter configuration for testing."""
    return StructuralFilterConfig(
        enabled=True,
        allowed_asset_types=["COMMON_STOCK"],
        allowed_exchanges=["NYSE", "NASDAQ"],
        min_listing_age_days=252,
    )


@pytest.fixture
def empty_context() -> DataContext:
    """Create empty data context for structural filter (not needed)."""
    return DataContext(
        assets=[],
        market_data={},
        metadata={},
        quality_metrics={},
    )


class TestStructuralFilter:
    """Test cases for StructuralFilter."""

    def test_passes_valid_stock(
        self,
        filter_config: StructuralFilterConfig,
        empty_context: DataContext,
    ) -> None:
        """
        SCENARIO: Stock meets all structural requirements
        EXPECTED: Stock passes the filter
        """
        # Arrange
        filter_ = StructuralFilter(filter_config)
        assets = [
            Asset(
                symbol="AAPL",
                name="Apple Inc",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NASDAQ",
                listing_date=date(2000, 1, 1),
            )
        ]
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, empty_context)

        # Assert
        assert "AAPL" in result.passed_assets
        assert len(result.rejected_assets) == 0

    def test_filters_wrong_exchange(
        self,
        filter_config: StructuralFilterConfig,
        empty_context: DataContext,
    ) -> None:
        """
        SCENARIO: Exchange not in allowed list
        EXPECTED: Asset is filtered with appropriate reason
        """
        # Arrange
        filter_ = StructuralFilter(filter_config)
        assets = [
            Asset(
                symbol="TEST",
                name="Test Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="LSE",  # Not allowed
                listing_date=date(2000, 1, 1),
            )
        ]
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, empty_context)

        # Assert
        assert "TEST" in result.rejected_assets
        assert "exchange" in result.rejection_reasons["TEST"].lower()

    def test_filters_young_listing(
        self,
        filter_config: StructuralFilterConfig,
        empty_context: DataContext,
    ) -> None:
        """
        SCENARIO: Asset listed less than min_listing_age_days ago
        EXPECTED: Asset is filtered with appropriate reason
        """
        # Arrange
        filter_ = StructuralFilter(filter_config)
        assets = [
            Asset(
                symbol="NEW",
                name="New Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2024, 10, 1),  # Only 2 months old
            )
        ]
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, empty_context)

        # Assert
        assert "NEW" in result.rejected_assets
        assert "listing_age" in result.rejection_reasons["NEW"].lower()

    def test_filters_delisted_asset(
        self,
        filter_config: StructuralFilterConfig,
        empty_context: DataContext,
    ) -> None:
        """
        SCENARIO: Asset was delisted before reference date
        EXPECTED: Asset is filtered
        """
        # Arrange
        filter_ = StructuralFilter(filter_config)
        assets = [
            Asset(
                symbol="DEAD",
                name="Dead Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
                delisting_date=date(2023, 6, 1),
            )
        ]
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, empty_context)

        # Assert
        assert "DEAD" in result.rejected_assets
        assert "delisted" in result.rejection_reasons["DEAD"].lower()

    def test_empty_input_returns_empty(
        self,
        filter_config: StructuralFilterConfig,
        empty_context: DataContext,
    ) -> None:
        """
        SCENARIO: Empty asset list provided
        EXPECTED: Empty result, no errors
        """
        # Arrange
        filter_ = StructuralFilter(filter_config)
        assets: List[Asset] = []
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, empty_context)

        # Assert
        assert len(result.passed_assets) == 0
        assert len(result.rejected_assets) == 0

    def test_disabled_filter_passes_all(
        self,
        empty_context: DataContext,
    ) -> None:
        """
        SCENARIO: Filter is disabled in config
        EXPECTED: All assets pass through
        """
        # Arrange
        config = StructuralFilterConfig(enabled=False)
        filter_ = StructuralFilter(config)
        assets = [
            Asset(
                symbol="ANY",
                name="Any Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="UNKNOWN",  # Would normally be filtered
                listing_date=date(2024, 12, 1),  # Would normally be filtered
            )
        ]
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, empty_context)

        # Assert
        assert "ANY" in result.passed_assets
        assert len(result.rejected_assets) == 0

    def test_multiple_assets_mixed_results(
        self,
        filter_config: StructuralFilterConfig,
        empty_context: DataContext,
    ) -> None:
        """
        SCENARIO: Mix of valid and invalid assets
        EXPECTED: Correct categorization for each
        """
        # Arrange
        filter_ = StructuralFilter(filter_config)
        assets = [
            Asset(
                symbol="GOOD1",
                name="Good Corp 1",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            ),
            Asset(
                symbol="BAD1",
                name="Bad Corp 1",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="LSE",  # Wrong exchange
                listing_date=date(2000, 1, 1),
            ),
            Asset(
                symbol="GOOD2",
                name="Good Corp 2",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NASDAQ",
                listing_date=date(2010, 1, 1),
            ),
        ]
        ref_date = datetime(2024, 12, 15)

        # Act
        result = filter_.apply(assets, ref_date, empty_context)

        # Assert
        assert len(result.passed_assets) == 2
        assert len(result.rejected_assets) == 1
        assert "GOOD1" in result.passed_assets
        assert "GOOD2" in result.passed_assets
        assert "BAD1" in result.rejected_assets
