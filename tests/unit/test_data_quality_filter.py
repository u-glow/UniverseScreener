"""
Unit Tests for DataQualityFilter.

Test Aspects Covered:
    ✅ Business Logic: Correct quality assessment
    ✅ Edge Cases: Missing metrics, boundary values
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.domain.value_objects import QualityMetrics
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.config.models import DataQualityFilterConfig
from universe_screener.pipeline.data_context import DataContext


@pytest.fixture
def filter_config() -> DataQualityFilterConfig:
    """Create filter configuration for testing."""
    return DataQualityFilterConfig(
        enabled=True,
        max_missing_days=3,
        min_news_articles=None,
        lookback_days=60,
    )


class TestDataQualityFilter:
    """Test cases for DataQualityFilter."""

    def test_passes_high_quality_data(
        self,
        filter_config: DataQualityFilterConfig,
    ) -> None:
        """
        SCENARIO: Asset with few missing days
        EXPECTED: Asset passes the filter
        """
        # Arrange
        filter_ = DataQualityFilter(filter_config)
        assets = [
            Asset(
                symbol="GOOD",
                name="Good Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]
        ref_date = datetime(2024, 12, 15)

        context = DataContext(
            assets=assets,
            market_data={},
            metadata={},
            quality_metrics={
                "GOOD": QualityMetrics(
                    missing_days=1,  # Below threshold
                    last_available_date=ref_date,
                    news_article_count=20,
                )
            },
        )

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "GOOD" in result.passed_assets
        assert len(result.rejected_assets) == 0

    def test_filters_too_many_missing_days(
        self,
        filter_config: DataQualityFilterConfig,
    ) -> None:
        """
        SCENARIO: Asset with missing days > threshold
        EXPECTED: Asset is filtered with appropriate reason
        """
        # Arrange
        filter_ = DataQualityFilter(filter_config)
        assets = [
            Asset(
                symbol="BAD",
                name="Bad Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]
        ref_date = datetime(2024, 12, 15)

        context = DataContext(
            assets=assets,
            market_data={},
            metadata={},
            quality_metrics={
                "BAD": QualityMetrics(
                    missing_days=10,  # Above threshold of 3
                    last_available_date=ref_date,
                    news_article_count=20,
                )
            },
        )

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "BAD" in result.rejected_assets
        assert "missing_days" in result.rejection_reasons["BAD"].lower()

    def test_boundary_missing_days(
        self,
        filter_config: DataQualityFilterConfig,
    ) -> None:
        """
        SCENARIO: Asset with exactly max_missing_days
        EXPECTED: Asset passes (<=, not <)
        """
        # Arrange
        filter_ = DataQualityFilter(filter_config)
        assets = [
            Asset(
                symbol="BOUNDARY",
                name="Boundary Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]
        ref_date = datetime(2024, 12, 15)

        context = DataContext(
            assets=assets,
            market_data={},
            metadata={},
            quality_metrics={
                "BOUNDARY": QualityMetrics(
                    missing_days=3,  # Exactly at threshold
                    last_available_date=ref_date,
                )
            },
        )

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "BOUNDARY" in result.passed_assets

    def test_news_coverage_when_enabled(self) -> None:
        """
        SCENARIO: min_news_articles configured
        EXPECTED: Assets with insufficient news filtered
        """
        # Arrange
        config = DataQualityFilterConfig(
            enabled=True,
            max_missing_days=5,
            min_news_articles=10,  # Require 10 articles
            lookback_days=60,
        )
        filter_ = DataQualityFilter(config)
        assets = [
            Asset(
                symbol="LOWCOVERAGE",
                name="Low Coverage Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]
        ref_date = datetime(2024, 12, 15)

        context = DataContext(
            assets=assets,
            market_data={},
            metadata={},
            quality_metrics={
                "LOWCOVERAGE": QualityMetrics(
                    missing_days=0,
                    last_available_date=ref_date,
                    news_article_count=5,  # Below threshold of 10
                )
            },
        )

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "LOWCOVERAGE" in result.rejected_assets
        assert "news_count" in result.rejection_reasons["LOWCOVERAGE"].lower()

    def test_handles_missing_quality_metrics(
        self,
        filter_config: DataQualityFilterConfig,
    ) -> None:
        """
        SCENARIO: Asset has no quality metrics in context
        EXPECTED: Asset is filtered
        """
        # Arrange
        filter_ = DataQualityFilter(filter_config)
        assets = [
            Asset(
                symbol="NOMETRICS",
                name="No Metrics Corp",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NYSE",
                listing_date=date(2000, 1, 1),
            )
        ]
        ref_date = datetime(2024, 12, 15)

        context = DataContext(
            assets=assets,
            market_data={},
            metadata={},
            quality_metrics={},  # No metrics for asset
        )

        # Act
        result = filter_.apply(assets, ref_date, context)

        # Assert
        assert "NOMETRICS" in result.rejected_assets
