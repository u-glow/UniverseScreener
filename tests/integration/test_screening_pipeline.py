"""
Integration Tests for ScreeningPipeline.

Tests cover:
    - Full end-to-end screening workflow
    - Multiple filter stages in sequence
    - Audit trail generation
"""

from __future__ import annotations

from datetime import datetime

import pytest

from universe_screener.domain.entities import AssetClass
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters.metrics_collector import InMemoryMetricsCollector
from universe_screener.filters.structural import StructuralFilter
from universe_screener.filters.liquidity import LiquidityFilter
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.config.models import ScreeningConfig


@pytest.fixture
def pipeline() -> ScreeningPipeline:
    """Create a fully configured pipeline for testing."""
    config = ScreeningConfig()
    provider = MockUniverseProvider(seed=42)
    logger = ConsoleAuditLogger(verbose=False)
    metrics = InMemoryMetricsCollector()

    filters = [
        StructuralFilter(config.structural_filter),
        LiquidityFilter(config.liquidity_filter),
        DataQualityFilter(config.data_quality_filter),
    ]

    return ScreeningPipeline(
        provider=provider,
        filters=filters,
        config=config,
        audit_logger=logger,
        metrics_collector=metrics,
    )


class TestScreeningPipeline:
    """Integration tests for ScreeningPipeline."""

    def test_happy_path_screening(self, pipeline: ScreeningPipeline) -> None:
        """
        SCENARIO: Screen stocks with valid configuration
        EXPECTED: Returns ScreeningResult with filtered universe
        """
        # Arrange
        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Assert
        assert result is not None
        assert len(result.input_universe) > 0
        assert len(result.output_universe) <= len(result.input_universe)
        assert len(result.audit_trail) == 3  # 3 filter stages

    def test_generates_audit_trail(self, pipeline: ScreeningPipeline) -> None:
        """
        SCENARIO: Complete screening run
        EXPECTED: Audit trail contains entries for each stage
        """
        # Arrange
        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Assert
        assert len(result.audit_trail) == 3

        stage_names = [s.stage_name for s in result.audit_trail]
        assert "structural_filter" in stage_names
        assert "liquidity_filter" in stage_names
        assert "data_quality_filter" in stage_names

        # Each stage should have valid metrics
        for stage in result.audit_trail:
            assert stage.input_count >= 0
            assert stage.output_count >= 0
            assert stage.output_count <= stage.input_count
            assert stage.duration_seconds >= 0

    def test_collects_metrics(self, pipeline: ScreeningPipeline) -> None:
        """
        SCENARIO: Complete screening run
        EXPECTED: Metrics collected for timing and counts
        """
        # Arrange
        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Assert
        assert result.metrics is not None
        assert len(result.metrics) > 0

    def test_correlation_id_in_metadata(self, pipeline: ScreeningPipeline) -> None:
        """
        SCENARIO: Screening run
        EXPECTED: Correlation ID present in metadata
        """
        # Arrange
        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Assert
        assert "correlation_id" in result.metadata
        assert result.metadata["correlation_id"] == result.request.correlation_id

    def test_filters_reduce_universe(self, pipeline: ScreeningPipeline) -> None:
        """
        SCENARIO: Screening run with filters
        EXPECTED: Output universe smaller than input
        """
        # Arrange
        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Assert
        # Some assets should be filtered out
        assert result.total_reduction_ratio > 0

    def test_request_contains_parameters(self, pipeline: ScreeningPipeline) -> None:
        """
        SCENARIO: Screening with specific parameters
        EXPECTED: Request object contains those parameters
        """
        # Arrange
        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Assert
        assert result.request.date == screening_date
        assert result.request.asset_class == AssetClass.STOCK
        assert result.request.correlation_id is not None

    def test_filtered_assets_have_reasons(self, pipeline: ScreeningPipeline) -> None:
        """
        SCENARIO: Assets are filtered out
        EXPECTED: Each filtered asset has a reason
        """
        # Arrange
        screening_date = datetime(2024, 12, 15)

        # Act
        result = pipeline.screen(
            date=screening_date,
            asset_class=AssetClass.STOCK,
        )

        # Assert
        for stage in result.audit_trail:
            # Each filtered asset should have a reason
            for symbol in stage.filtered_assets:
                assert symbol in stage.filter_reasons
                assert len(stage.filter_reasons[symbol]) > 0
