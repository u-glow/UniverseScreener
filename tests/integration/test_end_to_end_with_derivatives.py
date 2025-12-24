"""
Integration Test: End-to-End Screening with Derivatives.

Tests:
    - Full screening workflow with derivative resolution
    - Underlyings mapped to tradable instruments
    - Result contains derivative information
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any

import pytest

from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters.metrics_collector import InMemoryMetricsCollector
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.config.models import (
    DataQualityFilterConfig,
    DerivativeConfig,
    LiquidityFilterConfig,
    ScreeningConfig,
    StructuralFilterConfig,
)
from universe_screener.derivatives.derivative_resolver import DerivativeResolver
from universe_screener.derivatives.entities import InstrumentType
from universe_screener.domain.entities import AssetClass
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.filters.liquidity import LiquidityFilter
from universe_screener.filters.structural import StructuralFilter
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline


@pytest.fixture
def screening_config() -> ScreeningConfig:
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
        derivatives=DerivativeConfig(
            enabled=True,
            instrument_types=["CFD", "TURBO"],
            min_leverage=2.0,
            max_leverage=20.0,
            brokers=["Interactive Brokers"],
        ),
    )


@pytest.fixture
def derivative_resolver(screening_config: ScreeningConfig) -> DerivativeResolver:
    """Create derivative resolver."""
    return DerivativeResolver(config=screening_config.derivatives)


class TestEndToEndWithDerivatives:
    """End-to-end tests with derivative resolution."""

    def test_screening_with_derivatives(
        self, screening_config: ScreeningConfig, derivative_resolver: DerivativeResolver
    ) -> None:
        """Full screening with derivative resolution."""
        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=[
                StructuralFilter(screening_config.structural_filter),
                LiquidityFilter(screening_config.liquidity_filter),
                DataQualityFilter(screening_config.data_quality_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
            derivative_resolver=derivative_resolver,
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Should have output universe
        assert len(result.output_universe) > 0

        # Should have tradable instruments
        assert result.has_tradable_instruments
        assert result.tradable_instruments is not None

        # At least some underlyings should have instruments
        assert len(result.tradable_instruments) > 0

    def test_tradable_instruments_count(
        self, screening_config: ScreeningConfig, derivative_resolver: DerivativeResolver
    ) -> None:
        """Tradable instruments count is correct."""
        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
            derivative_resolver=derivative_resolver,
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Count should match actual instruments
        if result.tradable_instruments:
            expected_count = sum(
                len(instruments)
                for instruments in result.tradable_instruments.values()
            )
            assert result.tradable_instruments_count == expected_count

    def test_instruments_have_correct_underlying(
        self, screening_config: ScreeningConfig, derivative_resolver: DerivativeResolver
    ) -> None:
        """Instruments reference correct underlying."""
        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
            derivative_resolver=derivative_resolver,
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        if result.tradable_instruments:
            for symbol, instruments in result.tradable_instruments.items():
                for inst in instruments:
                    assert inst.underlying.symbol == symbol

    def test_instruments_match_config(
        self, screening_config: ScreeningConfig, derivative_resolver: DerivativeResolver
    ) -> None:
        """Instruments match derivative config."""
        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
            derivative_resolver=derivative_resolver,
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        if result.tradable_instruments:
            for instruments in result.tradable_instruments.values():
                for inst in instruments:
                    # Should match configured types
                    assert inst.instrument_type.value in screening_config.derivatives.instrument_types
                    # Should be within leverage range
                    assert inst.leverage >= screening_config.derivatives.min_leverage
                    assert inst.leverage <= screening_config.derivatives.max_leverage
                    # Should be from configured broker
                    assert inst.broker in screening_config.derivatives.brokers

    def test_screening_without_derivatives(
        self, screening_config: ScreeningConfig
    ) -> None:
        """Screening works without derivative resolver."""
        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
            # No derivative_resolver
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Should still work
        assert len(result.output_universe) > 0
        # But no instruments
        assert not result.has_tradable_instruments
        assert result.tradable_instruments is None


class TestDerivativeMetrics:
    """Tests for derivative-related metrics."""

    def test_instruments_count_in_metrics(
        self, screening_config: ScreeningConfig, derivative_resolver: DerivativeResolver
    ) -> None:
        """Tradable instruments count recorded in metrics."""
        metrics_collector = InMemoryMetricsCollector()

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=metrics_collector,
            derivative_resolver=derivative_resolver,
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        # Should have metric for instruments count
        metrics = result.metrics
        if result.has_tradable_instruments:
            assert "tradable_instruments_total" in metrics


class TestDerivativeTypes:
    """Tests for different derivative types."""

    def test_cfd_instruments(
        self, screening_config: ScreeningConfig
    ) -> None:
        """CFD instruments resolved correctly."""
        config = DerivativeConfig(
            enabled=True,
            instrument_types=["CFD"],
            min_leverage=1.0,
            max_leverage=10.0,
            brokers=["Test Broker"],
        )
        resolver = DerivativeResolver(config=config)

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
            derivative_resolver=resolver,
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        if result.tradable_instruments:
            for instruments in result.tradable_instruments.values():
                for inst in instruments:
                    assert inst.instrument_type == InstrumentType.CFD

    def test_turbo_instruments(
        self, screening_config: ScreeningConfig
    ) -> None:
        """Turbo instruments resolved correctly."""
        config = DerivativeConfig(
            enabled=True,
            instrument_types=["TURBO"],
            min_leverage=5.0,
            max_leverage=20.0,
            brokers=["Test Broker"],
        )
        resolver = DerivativeResolver(config=config)

        pipeline = ScreeningPipeline(
            provider=MockUniverseProvider(),
            filters=[
                StructuralFilter(screening_config.structural_filter),
            ],
            config=screening_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=InMemoryMetricsCollector(),
            derivative_resolver=resolver,
        )

        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )

        if result.tradable_instruments:
            for instruments in result.tradable_instruments.values():
                for inst in instruments:
                    assert inst.instrument_type == InstrumentType.TURBO
                    # Turbos should have knockout level
                    assert inst.has_knockout

