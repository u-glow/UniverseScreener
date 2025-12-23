"""
Pytest Configuration and Shared Fixtures.

This module contains fixtures available to all tests.
"""

from __future__ import annotations

import random
from datetime import date, datetime
from pathlib import Path
from typing import List

import pytest

from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.config.models import (
    ScreeningConfig,
    StructuralFilterConfig,
    LiquidityFilterConfig,
    DataQualityFilterConfig,
    StockLiquidityConfig,
)
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters.metrics_collector import InMemoryMetricsCollector


@pytest.fixture(autouse=True)
def set_random_seed():
    """Ensure all tests are deterministic."""
    random.seed(42)
    yield


@pytest.fixture
def sample_config_path() -> Path:
    """Path to sample configuration file."""
    return Path(__file__).parent / "fixtures" / "sample_config.yaml"


@pytest.fixture
def mock_provider() -> MockUniverseProvider:
    """Create mock provider for testing."""
    return MockUniverseProvider(seed=42)


@pytest.fixture
def console_logger() -> ConsoleAuditLogger:
    """Create console logger for testing."""
    return ConsoleAuditLogger(verbose=False)


@pytest.fixture
def metrics_collector() -> InMemoryMetricsCollector:
    """Create metrics collector for testing."""
    return InMemoryMetricsCollector()


@pytest.fixture
def default_config() -> ScreeningConfig:
    """Create default screening configuration."""
    return ScreeningConfig()


@pytest.fixture
def structural_config() -> StructuralFilterConfig:
    """Create structural filter configuration."""
    return StructuralFilterConfig(
        enabled=True,
        allowed_asset_types=["COMMON_STOCK"],
        allowed_exchanges=["NYSE", "NASDAQ", "XETRA"],
        min_listing_age_days=252,
    )


@pytest.fixture
def liquidity_config() -> LiquidityFilterConfig:
    """Create liquidity filter configuration."""
    return LiquidityFilterConfig(
        enabled=True,
        stock=StockLiquidityConfig(
            min_avg_dollar_volume_usd=5_000_000,
            min_trading_days_pct=0.95,
            lookback_days=60,
        ),
    )


@pytest.fixture
def data_quality_config() -> DataQualityFilterConfig:
    """Create data quality filter configuration."""
    return DataQualityFilterConfig(
        enabled=True,
        max_missing_days=3,
        min_news_articles=None,
        lookback_days=60,
    )


@pytest.fixture
def sample_stock() -> Asset:
    """Create a sample valid stock asset."""
    return Asset(
        symbol="AAPL",
        name="Apple Inc",
        asset_class=AssetClass.STOCK,
        asset_type=AssetType.COMMON_STOCK,
        exchange="NASDAQ",
        listing_date=date(2000, 1, 1),
        sector="Technology",
        country="US",
    )


@pytest.fixture
def sample_stocks() -> List[Asset]:
    """Create a list of sample stock assets."""
    return [
        Asset(
            symbol="AAPL",
            name="Apple Inc",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=date(2000, 1, 1),
            sector="Technology",
        ),
        Asset(
            symbol="MSFT",
            name="Microsoft Corporation",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            listing_date=date(1986, 3, 13),
            sector="Technology",
        ),
        Asset(
            symbol="JPM",
            name="JPMorgan Chase & Co",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NYSE",
            listing_date=date(1969, 3, 5),
            sector="Financials",
        ),
        # Wrong exchange
        Asset(
            symbol="WRONG_EXCHANGE",
            name="Wrong Exchange Corp",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="LSE",  # Not in allowed list
            listing_date=date(2000, 1, 1),
        ),
        # Young listing
        Asset(
            symbol="YOUNG",
            name="Young Corp",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NYSE",
            listing_date=date(2024, 6, 1),  # Very recent
        ),
        # Delisted
        Asset(
            symbol="DEAD",
            name="Delisted Corp",
            asset_class=AssetClass.STOCK,
            asset_type=AssetType.COMMON_STOCK,
            exchange="NYSE",
            listing_date=date(2010, 1, 1),
            delisting_date=date(2023, 12, 1),
        ),
    ]


@pytest.fixture
def reference_date() -> datetime:
    """Standard reference date for testing."""
    return datetime(2024, 12, 15)
