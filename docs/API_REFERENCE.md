# API Reference

Complete reference for Universe Screener components, configuration, and extension points.

---

## Core Components

### ScreeningPipeline

The main orchestrator that coordinates data loading, filtering, and result generation.

```python
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline

pipeline = ScreeningPipeline(
    provider: UniverseProviderProtocol,        # Required: data source
    filters: List[FilterStageProtocol],        # Required: filter stages
    config: ScreeningConfig,                   # Required: configuration
    audit_logger: AuditLoggerProtocol,         # Required: audit logging
    metrics_collector: MetricsCollectorProtocol,  # Required: metrics
    
    # Optional components (Phase 1+)
    error_handler: Optional[ErrorHandlerProtocol] = None,
    request_validator: Optional[RequestValidatorProtocol] = None,
    data_validator: Optional[DataValidatorProtocol] = None,
    
    # Optional components (Phase 2+)
    observability_manager: Optional[ObservabilityManagerProtocol] = None,
    health_monitor: Optional[HealthMonitorProtocol] = None,
    snapshot_manager: Optional[SnapshotManagerProtocol] = None,
    version_manager: Optional[VersionManagerProtocol] = None,
)
```

#### Methods

**`screen(date, asset_class, config_override=None) -> ScreeningResult`**

Execute a screening operation.

| Parameter | Type | Description |
|-----------|------|-------------|
| `date` | `datetime` | Point-in-time for screening |
| `asset_class` | `AssetClass` | Asset class to screen |
| `config_override` | `Optional[dict]` | Runtime config overrides |

Returns: `ScreeningResult` with filtered universe and audit trail.

---

### Filters

#### StructuralFilter

Filters assets by static properties.

```python
from universe_screener.filters.structural import StructuralFilter

filter = StructuralFilter(config: StructuralFilterConfig)
result = filter.apply(assets, date, context)
```

**Configuration Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable/disable filter |
| `allowed_asset_types` | `List[str]` | `["COMMON_STOCK"]` | Allowed asset types |
| `allowed_exchanges` | `List[str]` | `["NYSE", "NASDAQ", "XETRA"]` | Allowed exchanges |
| `min_listing_age_days` | `int` | `252` | Minimum trading days since listing |

#### LiquidityFilter

Filters assets by tradability using asset-class specific strategies.

```python
from universe_screener.filters.liquidity import LiquidityFilter

filter = LiquidityFilter(config: LiquidityFilterConfig)
result = filter.apply(assets, date, context)
```

**Stock Configuration:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `min_avg_dollar_volume_usd` | `float` | `5,000,000` | Minimum average daily dollar volume |
| `min_trading_days_pct` | `float` | `0.95` | Minimum percentage of trading days |
| `lookback_days` | `int` | `60` | Days for average calculation |

**Crypto Configuration:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_slippage_pct` | `float` | `0.5` | Maximum estimated slippage for $100k order |
| `min_order_book_depth_usd` | `float` | `100,000` | Minimum estimated order book depth |

**Forex Configuration:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_spread_pips` | `float` | `3.0` | Maximum average spread in pips |

#### DataQualityFilter

Filters assets by data availability.

```python
from universe_screener.filters.data_quality import DataQualityFilter

filter = DataQualityFilter(config: DataQualityFilterConfig)
result = filter.apply(assets, date, context)
```

**Configuration Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable/disable filter |
| `max_missing_days` | `int` | `3` | Maximum missing data days |
| `min_news_articles` | `Optional[int]` | `None` | Minimum news articles (optional) |
| `lookback_days` | `int` | `60` | Lookback period for checks |

---

### Providers

#### UniverseProviderProtocol

Interface for data providers.

```python
from typing import Protocol

class UniverseProviderProtocol(Protocol):
    def get_assets(
        self,
        date: datetime,
        asset_class: AssetClass,
    ) -> List[Asset]:
        """Get all assets for screening."""
        ...
    
    def bulk_load_market_data(
        self,
        assets: List[Asset],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, List[MarketData]]:
        """Bulk load OHLCV data."""
        ...
    
    def bulk_load_metadata(
        self,
        assets: List[Asset],
        date: datetime,
    ) -> Dict[str, Dict[str, Any]]:
        """Bulk load asset metadata."""
        ...
    
    def check_data_availability(
        self,
        assets: List[Asset],
        date: datetime,
        lookback_days: int,
    ) -> Dict[str, QualityMetrics]:
        """Check data quality for assets."""
        ...
```

#### MockUniverseProvider

Mock provider for testing and development.

```python
from universe_screener.adapters.mock_provider import MockUniverseProvider

provider = MockUniverseProvider()
assets = provider.get_assets(date, AssetClass.STOCK)
```

#### CachedUniverseProvider

Caching wrapper for any provider.

```python
from universe_screener.adapters.cached_provider import CachedUniverseProvider
from universe_screener.caching.cache_manager import CacheManager

cache = CacheManager()
cached = CachedUniverseProvider(
    provider=underlying_provider,
    cache_manager=cache,
    metrics_collector=metrics,  # Optional
)

# Check cache stats
stats = cached.get_cache_stats()
```

---

### Caching

#### CacheManager

TTL-based cache with LRU eviction.

```python
from universe_screener.caching.cache_manager import CacheManager, CacheConfig

config = CacheConfig(
    max_size_bytes=1024 * 1024 * 1024,  # 1 GB
    default_ttl_seconds=3600.0,
    enabled=True,
    log_access=False,
)

cache = CacheManager(config)
```

**Methods:**

| Method | Description |
|--------|-------------|
| `get(key)` | Get cached value or None |
| `set(key, value, ttl_seconds=None)` | Store value with optional TTL |
| `invalidate(key)` | Remove specific entry |
| `invalidate_pattern(pattern)` | Remove entries matching pattern |
| `clear()` | Remove all entries |
| `get_stats()` | Get cache statistics |
| `get_or_compute(key, fn, ttl)` | Get cached or compute and store |

**Static Methods:**

| Method | Description |
|--------|-------------|
| `make_key(operation, **params)` | Create consistent cache key |

---

## Configuration Reference

### ScreeningConfig

Root configuration model.

```python
from universe_screener.config.models import ScreeningConfig

config = ScreeningConfig(
    version="1.0",
    global_settings=GlobalConfig(...),
    structural_filter=StructuralFilterConfig(...),
    liquidity_filter=LiquidityFilterConfig(...),
    data_quality_filter=DataQualityFilterConfig(...),
    health_monitoring=HealthMonitorConfig(...),
    cache=CacheConfig(...),
)
```

### GlobalConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `default_lookback_days` | `int` | `60` | Default lookback period |
| `timezone` | `str` | `"UTC"` | Timezone for operations |
| `batch_size_mb` | `int` | `2000` | Max batch size in MB |

### HealthMonitorConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable health checks |
| `max_ram_usage_pct` | `float` | `80.0` | Max RAM usage before warning |
| `max_context_size_mb` | `int` | `2000` | Max DataContext size |
| `min_output_universe_size` | `int` | `10` | Min assets in output |
| `max_reduction_ratio` | `float` | `0.99` | Max acceptable reduction |

### CacheConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable caching |
| `max_size_mb` | `int` | `1024` | Max cache size (MB) |
| `default_ttl_seconds` | `float` | `3600` | Default TTL |
| `log_access` | `bool` | `False` | Log cache hits/misses |

---

## Domain Entities

### Asset

```python
from universe_screener.domain.entities import Asset, AssetClass, AssetType

asset = Asset(
    symbol="AAPL",
    name="Apple Inc",
    asset_class=AssetClass.STOCK,
    asset_type=AssetType.COMMON_STOCK,
    exchange="NASDAQ",
    listing_date=date(2000, 1, 1),
    delisting_date=None,  # Optional
    isin="US0378331005",  # Optional
    sector="Technology",  # Optional
    country="US",  # Optional
)
```

### AssetClass

| Value | Description |
|-------|-------------|
| `STOCK` | Equities |
| `CRYPTO` | Cryptocurrencies |
| `FOREX` | Foreign exchange pairs |

### AssetType

| Value | Description |
|-------|-------------|
| `COMMON_STOCK` | Common shares |
| `ETF` | Exchange-traded funds |
| `ADR` | American depositary receipts |
| `PREFERRED` | Preferred shares |
| `CRYPTO` | Cryptocurrency |
| `STABLECOIN` | Stablecoins |
| `FOREX_PAIR` | Major forex pairs |
| `FOREX_CROSS` | Cross currency pairs |

### MarketData

```python
from universe_screener.domain.value_objects import MarketData

data = MarketData(
    date=datetime(2024, 1, 15),
    open=150.0,
    high=152.0,
    low=149.0,
    close=151.0,
    volume=1_000_000,
)

# Computed property
print(data.dollar_volume)  # close * volume
```

### ScreeningResult

```python
result = pipeline.screen(date, asset_class)

# Access results
result.request              # ScreeningRequest
result.input_universe       # List[Asset] - all input assets
result.output_universe      # List[Asset] - filtered assets
result.audit_trail          # List[StageResult]
result.metrics              # Dict[str, Any]
result.metadata             # Dict[str, Any]

# Computed properties
result.total_reduction_ratio  # float (0.0 to 1.0)
```

---

## Extension Points

### Custom Filters

Implement the `FilterStageProtocol`:

```python
from typing import List, TYPE_CHECKING
from universe_screener.domain.entities import Asset
from universe_screener.domain.value_objects import FilterResult

if TYPE_CHECKING:
    from universe_screener.pipeline.data_context import DataContext

class MyCustomFilter:
    """Custom filter implementation."""
    
    def __init__(self, config: MyFilterConfig) -> None:
        self.config = config
    
    @property
    def name(self) -> str:
        return "my_custom_filter"
    
    def apply(
        self,
        assets: List[Asset],
        date: datetime,
        context: "DataContext",
    ) -> FilterResult:
        passed = []
        rejected = []
        reasons = {}
        
        for asset in assets:
            if self._check(asset, context):
                passed.append(asset.symbol)
            else:
                rejected.append(asset.symbol)
                reasons[asset.symbol] = "Failed custom check"
        
        return FilterResult(
            passed_assets=passed,
            rejected_assets=rejected,
            rejection_reasons=reasons,
        )
    
    def _check(self, asset: Asset, context: "DataContext") -> bool:
        # Your logic here
        return True
```

### Custom Liquidity Strategies

Implement the `LiquidityStrategy` protocol:

```python
from universe_screener.filters.liquidity_strategies import LiquidityStrategy
from universe_screener.domain.entities import Asset, AssetClass
from universe_screener.domain.value_objects import MarketData
from typing import List, Tuple

class MyLiquidityStrategy:
    """Custom liquidity strategy."""
    
    def __init__(self, config: MyLiquidityConfig) -> None:
        self.config = config
    
    def check_liquidity(
        self,
        asset: Asset,
        market_data: List[MarketData],
    ) -> Tuple[bool, str]:
        if not market_data:
            return False, "no market data"
        
        # Your liquidity check
        avg_volume = sum(d.volume for d in market_data) / len(market_data)
        
        if avg_volume < self.config.min_volume:
            return False, f"volume={avg_volume} < min={self.config.min_volume}"
        
        return True, ""
```

Register in LiquidityFilter:

```python
filter = LiquidityFilter(config)
filter._strategies[AssetClass.MY_CLASS] = MyLiquidityStrategy(my_config)
```

### Custom Providers

Implement the `UniverseProviderProtocol`:

```python
class MyDatabaseProvider:
    """Custom database provider."""
    
    def __init__(self, connection_string: str) -> None:
        self.conn = create_connection(connection_string)
    
    def get_assets(
        self,
        date: datetime,
        asset_class: AssetClass,
    ) -> List[Asset]:
        query = """
            SELECT * FROM assets 
            WHERE asset_class = %s 
            AND listing_date <= %s
        """
        rows = self.conn.execute(query, (asset_class.value, date))
        return [self._row_to_asset(row) for row in rows]
    
    def bulk_load_market_data(
        self,
        assets: List[Asset],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, List[MarketData]]:
        # Implement batch loading
        ...
```

---

## Observability

### ObservabilityManager

Unified logging and metrics.

```python
from universe_screener.observability.observability_manager import ObservabilityManager

obs = ObservabilityManager(use_json=True)

# Set correlation ID
obs.set_correlation_id("request-123")

# Log events
obs.log_event("screening_started", {"asset_class": "STOCK"})

# Record metrics
obs.record_metric("duration_seconds", 1.5, tags={"stage": "load"})
obs.record_timing("filter_time", 0.5)
obs.record_count("filtered_assets", 50)
```

### HealthMonitor

System health checks.

```python
from universe_screener.observability.health_monitor import HealthMonitor

monitor = HealthMonitor(config)

# Pre-screening check
status = monitor.check_pre_screening()
if not status.is_healthy:
    print(status.summary)

# Post-load check
status = monitor.check_post_load(context)

# Post-filter check
status = monitor.check_post_filtering(result)
```

---

## Error Handling

### ErrorHandler

Retry logic and circuit breakers.

```python
from universe_screener.resilience.error_handler import ErrorHandler

handler = ErrorHandler(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    failure_threshold=5,
)

# Retry with backoff
result = handler.retry(
    lambda: provider.get_assets(date, asset_class),
    operation_name="get_assets",
)

# Circuit breaker
result = handler.with_circuit_breaker(
    lambda: provider.bulk_load_market_data(assets, start, end),
    circuit_name="market_data",
)
```

---

## Validation

### RequestValidator

Validates screening requests.

```python
from universe_screener.validation.request_validator import RequestValidator

validator = RequestValidator()

# Validate request
validator.validate(request, config)  # Raises on invalid

# Validate date only
validator.validate_date(date)  # Raises on invalid
```

### DataValidator

Validates loaded data.

```python
from universe_screener.validation.data_validator import DataValidator

validator = DataValidator(
    sigma_threshold=10.0,  # Outlier detection
    required_metadata_fields=["sector"],
)

# Validate all data
result = validator.validate_all(market_data, metadata)

if result.has_issues:
    print(f"Warnings: {result.warnings}")
    print(f"Errors: {result.errors}")
    print(f"Outliers: {result.outliers}")
```

---

## See Also

- [Deployment Guide](DEPLOYMENT.md)
- [Performance Guide](PERFORMANCE.md)
- [Architecture Overview](architecture/02_architecture_overview.md)
- [Implementation Roadmap](architecture/04_implementation_roadmap.md)

