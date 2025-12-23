"""
Mock Universe Provider.

A fake data provider for development and testing. Generates
deterministic mock data for assets, market data, and quality metrics.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from universe_screener.domain.entities import Asset, AssetClass, AssetType
from universe_screener.domain.value_objects import MarketData, QualityMetrics


class MockUniverseProvider:
    """Fake data provider for development and testing."""

    # Sample stock data
    MOCK_STOCKS = [
        ("AAPL", "Apple Inc", "NASDAQ", "Technology"),
        ("MSFT", "Microsoft Corporation", "NASDAQ", "Technology"),
        ("GOOGL", "Alphabet Inc", "NASDAQ", "Technology"),
        ("AMZN", "Amazon.com Inc", "NASDAQ", "Consumer Discretionary"),
        ("META", "Meta Platforms Inc", "NASDAQ", "Technology"),
        ("JPM", "JPMorgan Chase & Co", "NYSE", "Financials"),
        ("BAC", "Bank of America Corp", "NYSE", "Financials"),
        ("WMT", "Walmart Inc", "NYSE", "Consumer Staples"),
        ("JNJ", "Johnson & Johnson", "NYSE", "Healthcare"),
        ("PG", "Procter & Gamble Co", "NYSE", "Consumer Staples"),
        ("SAP", "SAP SE", "XETRA", "Technology"),
        ("SIE", "Siemens AG", "XETRA", "Industrials"),
        ("ALV", "Allianz SE", "XETRA", "Financials"),
        ("BAS", "BASF SE", "XETRA", "Materials"),
        ("BMW", "Bayerische Motoren Werke AG", "XETRA", "Consumer Discretionary"),
        # Low liquidity stocks (for testing filtering)
        ("TINY", "Tiny Corp", "NYSE", "Technology"),
        ("SMALL", "Small Company Inc", "NASDAQ", "Industrials"),
        # Young listing (for testing age filter)
        ("NEW1", "New Listing Corp", "NYSE", "Technology"),
        # Delisted stock
        ("DEAD", "Delisted Corp", "NYSE", "Financials"),
        # Missing data stock
        ("SPARSE", "Sparse Data Inc", "NASDAQ", "Healthcare"),
    ]

    MOCK_CRYPTO = [
        ("BTC", "Bitcoin", "BINANCE", None),
        ("ETH", "Ethereum", "BINANCE", None),
        ("SOL", "Solana", "BINANCE", None),
        ("ADA", "Cardano", "BINANCE", None),
        ("DOT", "Polkadot", "BINANCE", None),
    ]

    MOCK_FOREX = [
        ("EURUSD", "Euro/US Dollar", "FOREX", None),
        ("GBPUSD", "British Pound/US Dollar", "FOREX", None),
        ("USDJPY", "US Dollar/Japanese Yen", "FOREX", None),
        ("AUDUSD", "Australian Dollar/US Dollar", "FOREX", None),
        ("USDCHF", "US Dollar/Swiss Franc", "FOREX", None),
    ]

    def __init__(self, seed: int = 42) -> None:
        """
        Initialize mock provider with random seed.

        Args:
            seed: Random seed for reproducibility
        """
        self._seed = seed
        self._rng = random.Random(seed)
        self._assets = self._generate_assets()
        self._market_data = self._generate_market_data()

    def get_assets(
        self,
        date: datetime,
        asset_class: AssetClass,
    ) -> List[Asset]:
        """Get mock assets for a date and asset class."""
        # Convert datetime to date for comparison with Asset.listing_date
        ref_date = date.date()
        return [
            a
            for a in self._assets
            if a.asset_class == asset_class
            and a.listing_date <= ref_date
            and (a.delisting_date is None or a.delisting_date > ref_date)
        ]

    def bulk_load_market_data(
        self,
        assets: List[Asset],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, List[MarketData]]:
        """Get mock market data for assets."""
        result = {}
        for asset in assets:
            if asset.symbol in self._market_data:
                data = [
                    d
                    for d in self._market_data[asset.symbol]
                    if start_date <= d.date <= end_date
                ]
                result[asset.symbol] = data
            else:
                result[asset.symbol] = []
        return result

    def bulk_load_metadata(
        self,
        assets: List[Asset],
        date: datetime,
    ) -> Dict[str, Dict[str, Any]]:
        """Get mock metadata for assets."""
        return {
            a.symbol: {
                "asset_type": a.asset_type.value,
                "exchange": a.exchange,
                "sector": a.sector,
                "listing_date": a.listing_date,
                "delisting_date": a.delisting_date,
            }
            for a in assets
        }

    def check_data_availability(
        self,
        assets: List[Asset],
        date: datetime,
        lookback_days: int,
    ) -> Dict[str, QualityMetrics]:
        """Get mock quality metrics."""
        result = {}
        for asset in assets:
            # SPARSE stock has many missing days
            if asset.symbol == "SPARSE":
                missing = 20
            # Most stocks have 0-2 missing days
            else:
                missing = self._rng.randint(0, 2)

            result[asset.symbol] = QualityMetrics(
                missing_days=missing,
                last_available_date=date,
                news_article_count=self._rng.randint(5, 50),
            )
        return result

    def _generate_assets(self) -> List[Asset]:
        """Generate mock assets."""
        assets = []
        base_date = date(2020, 1, 1)

        # Generate stocks
        for i, (symbol, name, exchange, sector) in enumerate(self.MOCK_STOCKS):
            # Most stocks have old listing dates
            if symbol == "NEW1":
                listing_date = date(2024, 6, 1)  # Recent listing
            elif symbol == "DEAD":
                listing_date = date(2010, 1, 1)
            else:
                listing_date = base_date - timedelta(days=self._rng.randint(500, 5000))

            delisting_date = None
            if symbol == "DEAD":
                delisting_date = date(2023, 12, 1)

            assets.append(
                Asset(
                    symbol=symbol,
                    name=name,
                    asset_class=AssetClass.STOCK,
                    asset_type=AssetType.COMMON_STOCK,
                    exchange=exchange,
                    listing_date=listing_date,
                    delisting_date=delisting_date,
                    sector=sector,
                    country="US" if exchange in ["NYSE", "NASDAQ"] else "DE",
                )
            )

        # Generate crypto
        for symbol, name, exchange, _ in self.MOCK_CRYPTO:
            assets.append(
                Asset(
                    symbol=symbol,
                    name=name,
                    asset_class=AssetClass.CRYPTO,
                    asset_type=AssetType.COMMON_STOCK,  # Placeholder
                    exchange=exchange,
                    listing_date=base_date - timedelta(days=self._rng.randint(365, 2000)),
                )
            )

        # Generate forex
        for symbol, name, exchange, _ in self.MOCK_FOREX:
            assets.append(
                Asset(
                    symbol=symbol,
                    name=name,
                    asset_class=AssetClass.FOREX,
                    asset_type=AssetType.COMMON_STOCK,  # Placeholder
                    exchange=exchange,
                    listing_date=date(2000, 1, 1),  # Forex always available
                )
            )

        return assets

    def _generate_market_data(self) -> Dict[str, List[MarketData]]:
        """Generate mock market data for 2 years."""
        result = {}
        end_date = datetime(2024, 12, 31)
        start_date = end_date - timedelta(days=730)  # 2 years

        for asset in self._assets:
            data = []
            current_date = start_date

            # Set base price and volume based on asset
            if asset.symbol in ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]:
                base_price = self._rng.uniform(100, 500)
                base_volume = self._rng.randint(10_000_000, 50_000_000)
            elif asset.symbol in ["TINY", "SMALL"]:
                base_price = self._rng.uniform(5, 20)
                base_volume = self._rng.randint(10_000, 100_000)  # Low volume
            elif asset.symbol == "SPARSE":
                base_price = self._rng.uniform(30, 60)
                base_volume = self._rng.randint(500_000, 2_000_000)
            else:
                base_price = self._rng.uniform(50, 300)
                base_volume = self._rng.randint(1_000_000, 20_000_000)

            price = base_price

            while current_date <= end_date:
                # Skip weekends for stocks
                if asset.asset_class == AssetClass.STOCK and current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue

                # Skip some days for SPARSE stock
                if asset.symbol == "SPARSE" and self._rng.random() < 0.3:
                    current_date += timedelta(days=1)
                    continue

                # Random walk for price
                change = self._rng.gauss(0, 0.02)
                price = price * (1 + change)
                price = max(price, 1.0)  # No negative prices

                # OHLCV generation
                open_price = price * (1 + self._rng.gauss(0, 0.005))
                high_price = max(open_price, price) * (1 + abs(self._rng.gauss(0, 0.01)))
                low_price = min(open_price, price) * (1 - abs(self._rng.gauss(0, 0.01)))
                close_price = price
                volume = int(base_volume * (1 + self._rng.gauss(0, 0.3)))
                volume = max(volume, 1000)

                data.append(
                    MarketData(
                        date=current_date,
                        open=round(open_price, 2),
                        high=round(high_price, 2),
                        low=round(low_price, 2),
                        close=round(close_price, 2),
                        volume=volume,
                    )
                )

                current_date += timedelta(days=1)

            result[asset.symbol] = data

        return result
