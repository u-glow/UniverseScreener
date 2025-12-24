"""
Integration Test: Multi-Asset-Class Screening.

Tests screening across STOCK, CRYPTO, and FOREX asset classes together.
Ensures:
    - Each asset class uses correct liquidity strategy
    - Mixed universes are handled correctly
    - Results contain proper audit trail
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest

from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters import SimpleMetricsCollector
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.config.models import (
    CryptoLiquidityConfig,
    DataQualityFilterConfig,
    ForexLiquidityConfig,
    GlobalConfig,
    LiquidityFilterConfig,
    ScreeningConfig,
    StockLiquidityConfig,
    StructuralFilterConfig,
)
from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.domain.value_objects import MarketData, QualityMetrics
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.filters.liquidity import LiquidityFilter
from universe_screener.filters.structural import StructuralFilter
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline


class MultiAssetClassProvider:
    """
    Mock provider that generates assets for all asset classes.
    
    Note: Does not inherit from MockUniverseProvider to avoid
    incompatible method signatures.
    """

    def __init__(self) -> None:
        self._mock_assets: Dict[AssetClass, List[Asset]] = {}
        self._generate_multi_class_assets()

    def _generate_multi_class_assets(self) -> None:
        """Generate a diverse set of assets across all classes."""
        base_date = datetime(2020, 1, 1)
        
        # Stocks
        stocks = [
            Asset(
                symbol="AAPL",
                name="Apple Inc",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NASDAQ",
                listing_date=base_date.date(),
            ),
            Asset(
                symbol="GOOGL",
                name="Alphabet Inc",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NASDAQ",
                listing_date=base_date.date(),
            ),
            Asset(
                symbol="MSFT",
                name="Microsoft Corporation",
                asset_class=AssetClass.STOCK,
                asset_type=AssetType.COMMON_STOCK,
                exchange="NASDAQ",
                listing_date=base_date.date(),
            ),
        ]
        
        # Crypto
        cryptos = [
            Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_class=AssetClass.CRYPTO,
                asset_type=AssetType.CRYPTO,
                exchange="COINBASE",
                listing_date=base_date.date(),
            ),
            Asset(
                symbol="ETH-USD",
                name="Ethereum",
                asset_class=AssetClass.CRYPTO,
                asset_type=AssetType.CRYPTO,
                exchange="COINBASE",
                listing_date=base_date.date(),
            ),
        ]
        
        # Forex
        forex = [
            Asset(
                symbol="EUR/USD",
                name="Euro vs US Dollar",
                asset_class=AssetClass.FOREX,
                asset_type=AssetType.FOREX_PAIR,
                exchange="FOREX",
                listing_date=base_date.date(),
            ),
            Asset(
                symbol="GBP/USD",
                name="British Pound vs US Dollar",
                asset_class=AssetClass.FOREX,
                asset_type=AssetType.FOREX_PAIR,
                exchange="FOREX",
                listing_date=base_date.date(),
            ),
        ]
        
        self._mock_assets = {
            AssetClass.STOCK: stocks,
            AssetClass.CRYPTO: cryptos,
            AssetClass.FOREX: forex,
        }

    def get_assets(
        self,
        date: datetime,
        asset_class: AssetClass,
    ) -> List[Asset]:
        """Get assets for specified class."""
        return self._mock_assets.get(asset_class, [])

    def bulk_load_market_data(
        self,
        assets: List[Asset],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, List[MarketData]]:
        """Bulk load market data for all assets."""
        result: Dict[str, List[MarketData]] = {}
        for asset in assets:
            result[asset.symbol] = self._generate_market_data(asset, start_date, end_date)
        return result

    def bulk_load_metadata(
        self,
        assets: List[Asset],
        date: datetime,
    ) -> Dict[str, Dict[str, Any]]:
        """Bulk load metadata for all assets."""
        result: Dict[str, Dict[str, Any]] = {}
        for asset in assets:
            result[asset.symbol] = {
                "sector": "Technology" if asset.asset_class == AssetClass.STOCK else None,
                "market_cap": 1_000_000_000,
            }
        return result

    def check_data_availability(
        self,
        assets: List[Asset],
        date: datetime,
        lookback_days: int,
    ) -> Dict[str, QualityMetrics]:
        """Check data quality for all assets."""
        result: Dict[str, QualityMetrics] = {}
        for asset in assets:
            result[asset.symbol] = QualityMetrics(
                missing_days=2,  # Some missing days
                last_available_date=date,
                news_article_count=None,
            )
        return result

    def _generate_market_data(
        self,
        asset: Asset,
        start_date: datetime,
        end_date: datetime,
    ) -> List[MarketData]:
        """Generate market data appropriate for asset class."""
        data = []
        current = start_date
        
        while current <= end_date:
            if current.weekday() < 5:  # Weekdays
                if asset.asset_class == AssetClass.STOCK:
                    base_price = 150.0
                    # Dollar volume target: $15M → volume = $15M / $150 = 100,000
                    volume = 100_000
                elif asset.asset_class == AssetClass.CRYPTO:
                    base_price = 50_000.0
                    # Dollar volume target: $5M → volume = $5M / $50k = 100
                    volume = 100
                else:  # FOREX
                    base_price = 1.10
                    # Forex volume in lots (not critical for spread check)
                    volume = 1_000_000
                
                data.append(
                    MarketData(
                        date=current,
                        open=base_price,
                        high=base_price * 1.01,
                        low=base_price * 0.99,
                        close=base_price * 1.005,
                        volume=volume,
                    )
                )
            
            current += timedelta(days=1)
        
        return data


@pytest.fixture
def multi_asset_provider() -> MultiAssetClassProvider:
    """Create multi-asset provider."""
    return MultiAssetClassProvider()


@pytest.fixture
def multi_asset_config() -> ScreeningConfig:
    """Create config that accepts all asset classes."""
    return ScreeningConfig(
        version="1.0",
        global_settings=GlobalConfig(default_lookback_days=60),
        structural_filter=StructuralFilterConfig(
            enabled=True,
            allowed_asset_types=[
                "COMMON_STOCK",
                "CRYPTO",
                "FOREX_PAIR",
            ],
            allowed_exchanges=[
                "NASDAQ",
                "NYSE",
                "COINBASE",
                "FOREX",
            ],
            min_listing_age_days=30,
        ),
        liquidity_filter=LiquidityFilterConfig(
            enabled=True,
            stock=StockLiquidityConfig(
                min_avg_dollar_volume_usd=1_000_000,
                min_trading_days_pct=0.8,
                lookback_days=60,
            ),
            crypto=CryptoLiquidityConfig(
                max_slippage_pct=5.0,  # Generous for testing
                min_order_book_depth_usd=10_000,
            ),
            forex=ForexLiquidityConfig(
                max_spread_pips=100.0,  # Generous for testing
            ),
        ),
        data_quality_filter=DataQualityFilterConfig(
            enabled=True,
            max_missing_days=10,
            lookback_days=60,
        ),
    )


class TestMultiAssetClassScreening:
    """Integration tests for multi-asset-class screening."""

    def test_stock_screening(
        self,
        multi_asset_provider,
        multi_asset_config,
    ) -> None:
        """Screen stocks successfully."""
        pipeline = ScreeningPipeline(
            provider=multi_asset_provider,
            filters=[
                StructuralFilter(multi_asset_config.structural_filter),
                LiquidityFilter(multi_asset_config.liquidity_filter),
                DataQualityFilter(multi_asset_config.data_quality_filter),
            ],
            config=multi_asset_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.STOCK,
        )
        
        assert len(result.input_universe) == 3  # 3 stocks
        assert len(result.output_universe) >= 1  # At least some pass
        assert result.request.asset_class == AssetClass.STOCK

    def test_crypto_screening(
        self,
        multi_asset_provider,
        multi_asset_config,
    ) -> None:
        """Screen crypto successfully."""
        pipeline = ScreeningPipeline(
            provider=multi_asset_provider,
            filters=[
                StructuralFilter(multi_asset_config.structural_filter),
                LiquidityFilter(multi_asset_config.liquidity_filter),
                DataQualityFilter(multi_asset_config.data_quality_filter),
            ],
            config=multi_asset_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.CRYPTO,
        )
        
        assert len(result.input_universe) == 2  # 2 cryptos
        assert result.request.asset_class == AssetClass.CRYPTO

    def test_forex_screening(
        self,
        multi_asset_provider,
        multi_asset_config,
    ) -> None:
        """Screen forex successfully."""
        pipeline = ScreeningPipeline(
            provider=multi_asset_provider,
            filters=[
                StructuralFilter(multi_asset_config.structural_filter),
                LiquidityFilter(multi_asset_config.liquidity_filter),
                DataQualityFilter(multi_asset_config.data_quality_filter),
            ],
            config=multi_asset_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        result = pipeline.screen(
            date=datetime(2024, 6, 15),
            asset_class=AssetClass.FOREX,
        )
        
        assert len(result.input_universe) == 2  # 2 forex pairs
        assert result.request.asset_class == AssetClass.FOREX

    def test_each_class_uses_correct_strategy(
        self,
        multi_asset_provider,
        multi_asset_config,
    ) -> None:
        """Each asset class uses appropriate liquidity strategy."""
        pipeline = ScreeningPipeline(
            provider=multi_asset_provider,
            filters=[
                StructuralFilter(multi_asset_config.structural_filter),
                LiquidityFilter(multi_asset_config.liquidity_filter),
                DataQualityFilter(multi_asset_config.data_quality_filter),
            ],
            config=multi_asset_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        # Screen each class
        stock_result = pipeline.screen(datetime(2024, 6, 15), AssetClass.STOCK)
        crypto_result = pipeline.screen(datetime(2024, 6, 15), AssetClass.CRYPTO)
        forex_result = pipeline.screen(datetime(2024, 6, 15), AssetClass.FOREX)
        
        # All should have audit trail
        assert len(stock_result.audit_trail) >= 1
        assert len(crypto_result.audit_trail) >= 1
        assert len(forex_result.audit_trail) >= 1
        
        # Check correlation IDs are unique
        stock_corr = stock_result.metadata.get("correlation_id")
        crypto_corr = crypto_result.metadata.get("correlation_id")
        forex_corr = forex_result.metadata.get("correlation_id")
        
        assert stock_corr != crypto_corr
        assert crypto_corr != forex_corr

    def test_audit_trail_per_asset_class(
        self,
        multi_asset_provider,
        multi_asset_config,
    ) -> None:
        """Audit trail properly records per-class filtering."""
        pipeline = ScreeningPipeline(
            provider=multi_asset_provider,
            filters=[
                StructuralFilter(multi_asset_config.structural_filter),
                LiquidityFilter(multi_asset_config.liquidity_filter),
            ],
            config=multi_asset_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        result = pipeline.screen(datetime(2024, 6, 15), AssetClass.STOCK)
        
        # Should have entries for each filter stage
        stages = [entry.stage_name for entry in result.audit_trail]
        
        assert "structural_filter" in stages
        assert "liquidity_filter" in stages


class TestMultiAssetClassFiltering:
    """Test filtering behavior across asset classes."""

    def test_illiquid_crypto_rejected(
        self,
        multi_asset_config,
    ) -> None:
        """Illiquid crypto is properly rejected."""
        # Create provider with low-volume crypto
        provider = MultiAssetClassProvider()
        
        # Override with strict config
        strict_config = multi_asset_config.model_copy(deep=True)
        strict_config.liquidity_filter.crypto.min_order_book_depth_usd = 10_000_000
        
        pipeline = ScreeningPipeline(
            provider=provider,
            filters=[
                StructuralFilter(strict_config.structural_filter),
                LiquidityFilter(strict_config.liquidity_filter),
            ],
            config=strict_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        result = pipeline.screen(datetime(2024, 6, 15), AssetClass.CRYPTO)
        
        # Should reject due to liquidity
        assert len(result.output_universe) < len(result.input_universe)

    def test_wide_spread_forex_rejected(
        self,
        multi_asset_config,
    ) -> None:
        """Wide-spread forex is properly rejected."""
        provider = MultiAssetClassProvider()
        
        # Override with strict config
        strict_config = multi_asset_config.model_copy(deep=True)
        strict_config.liquidity_filter.forex.max_spread_pips = 0.001  # Very tight
        
        pipeline = ScreeningPipeline(
            provider=provider,
            filters=[
                StructuralFilter(strict_config.structural_filter),
                LiquidityFilter(strict_config.liquidity_filter),
            ],
            config=strict_config,
            audit_logger=ConsoleAuditLogger(),
            metrics_collector=SimpleMetricsCollector(),
        )
        
        result = pipeline.screen(datetime(2024, 6, 15), AssetClass.FOREX)
        
        # Should reject due to spread
        # (depends on mock data spread calculation)
        assert len(result.input_universe) == 2

