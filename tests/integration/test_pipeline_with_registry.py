"""
Integration Test: Pipeline with FilterRegistry.

Tests:
    - Dynamic filter loading from registry
    - Backwards compatibility with list
    - Filter ordering
    - Version tracking
"""

from __future__ import annotations

from datetime import datetime
from typing import List

import pytest

from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters.metrics_collector import InMemoryMetricsCollector
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.config.models import (
    DataQualityFilterConfig,
    LiquidityFilterConfig,
    ScreeningConfig,
    StructuralFilterConfig,
)
from universe_screener.domain.entities import AssetClass
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.filters.liquidity import LiquidityFilter
from universe_screener.filters.structural import StructuralFilter
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline
from universe_screener.registry.filter_registry import FilterRegistry


@pytest.fixture
def config() -> ScreeningConfig:
    """Create screening configuration."""
    return ScreeningConfig(
        structural_filter=StructuralFilterConfig(
            min_listing_age_days=30,
            allowed_asset_types=["COMMON_STOCK"],
            allowed_exchanges=["NYSE", "NASDAQ"],
        ),
        liquidity_filter=LiquidityFilterConfig(enabled=True),
        data_quality_filter=DataQualityFilterConfig(
            max_missing_days=10,
        ),
    )


@pytest.fixture
def filter_registry(config: ScreeningConfig) -> FilterRegistry:
    """Create and populate filter registry."""
    registry = FilterRegistry()

    registry.register(
        name="structural",
        filter_class=StructuralFilter,
        version="1.0.0",
        config=config.structural_filter,
        description="Filters by asset type, exchange, listing age",
    )

    registry.register(
        name="liquidity",
        filter_class=LiquidityFilter,
        version="1.0.0",
        config=config.liquidity_filter,
        description="Filters by trading volume and activity",
    )

    registry.register(
        name="data_quality",
        filter_class=DataQualityFilter,
        version="1.0.0",
        config=config.data_quality_filter,
        description="Filters by data completeness",
    )

    return registry


class TestPipelineWithRegistry:
    """Integration tests for pipeline with registry."""

    def test_pipeline_with_registry(
        self, filter_registry: FilterRegistry, config: ScreeningConfig
    ) -> None:
        """Pipeline works with FilterRegistry."""
        # Enable filters in registry
        filter_registry.enable_filters(["structural", "liquidity", "data_quality"])

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=filter_registry,  # Pass registry instead of list
            config=config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Should complete successfully
        assert len(result.audit_trail) == 3
        assert result.audit_trail[0].stage_name == "structural_filter"
        assert result.audit_trail[1].stage_name == "liquidity_filter"
        assert result.audit_trail[2].stage_name == "data_quality_filter"

    def test_pipeline_with_list_backwards_compatible(
        self, config: ScreeningConfig
    ) -> None:
        """Pipeline still works with list of filters (backwards compatible)."""
        filters = [
            StructuralFilter(config.structural_filter),
            LiquidityFilter(config.liquidity_filter),
            DataQualityFilter(config.data_quality_filter),
        ]

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=filters,  # Pass list as before
            config=config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Should complete successfully
        assert len(result.audit_trail) == 3

    def test_registry_filter_ordering(
        self, filter_registry: FilterRegistry, config: ScreeningConfig
    ) -> None:
        """Filter ordering matches enable order."""
        # Enable in different order
        filter_registry.enable_filters(["data_quality", "structural", "liquidity"])

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=filter_registry,
            config=config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Order should match enable order
        assert result.audit_trail[0].stage_name == "data_quality_filter"
        assert result.audit_trail[1].stage_name == "structural_filter"
        assert result.audit_trail[2].stage_name == "liquidity_filter"

    def test_registry_subset_of_filters(
        self, filter_registry: FilterRegistry, config: ScreeningConfig
    ) -> None:
        """Can run with subset of registered filters."""
        # Only enable structural and liquidity
        filter_registry.enable_filters(["structural", "liquidity"])

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=filter_registry,
            config=config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Should only have 2 stages
        assert len(result.audit_trail) == 2

    def test_registry_dynamic_enable_disable(
        self, filter_registry: FilterRegistry, config: ScreeningConfig
    ) -> None:
        """Filters can be dynamically enabled/disabled."""
        filter_registry.enable_filters(["structural", "liquidity", "data_quality"])

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=filter_registry,
            config=config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
        )

        # First run with all filters
        result1 = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )
        assert len(result1.audit_trail) == 3

        # Disable liquidity
        filter_registry.disable_filter("liquidity")

        # Second run without liquidity
        result2 = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )
        assert len(result2.audit_trail) == 2
        assert all(
            s.stage_name != "liquidity_filter" for s in result2.audit_trail
        )

    def test_registry_config_update(
        self, filter_registry: FilterRegistry, config: ScreeningConfig
    ) -> None:
        """Filter config can be updated dynamically."""
        filter_registry.enable_filters(["structural"])

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=filter_registry,
            config=config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
        )

        # First run with original config
        result1 = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Update config to be more restrictive
        new_config = StructuralFilterConfig(
            min_listing_age_days=365,  # Much stricter
            allowed_asset_types=["COMMON_STOCK"],
            allowed_exchanges=["NYSE"],  # Only NYSE
        )
        filter_registry.update_config("structural", new_config)

        # Second run with updated config
        result2 = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Second run should have more filtering
        assert result2.audit_trail[0].output_count <= result1.audit_trail[0].output_count


class TestRegistryVersionTracking:
    """Tests for version tracking with registry."""

    def test_registry_versions_available(
        self, filter_registry: FilterRegistry, config: ScreeningConfig
    ) -> None:
        """Filter versions are tracked."""
        filter_registry.enable_filters(["structural", "liquidity"])

        versions = filter_registry.get_versions()

        assert versions["structural"] == "1.0.0"
        assert versions["liquidity"] == "1.0.0"

    def test_version_in_filter_info(
        self, filter_registry: FilterRegistry
    ) -> None:
        """Version included in filter info."""
        all_filters = filter_registry.list_all()

        for name, info in all_filters.items():
            assert info.version == "1.0.0"

