# Architecture Overview: Universe Screening System

## Executive Summary

The Universe Screening System is a **multi-stage filtering pipeline** that reduces large asset universes to tradable subsets based on liquidity, data quality, and structural criteria. The architecture follows **Hexagonal Architecture** principles with strict separation between domain logic and infrastructure.

**Key Design Principles:**
- **Dependency Injection**: All external dependencies injectable for testability
- **Interface Segregation**: Abstract interfaces for all infrastructure components
- **Strategy Pattern**: Asset-class-specific behavior via polymorphic strategies
- **Batch Loading**: Prefetch data once, filter in-memory for performance
- **Configuration-Driven**: All parameters externalized to YAML configs

---

## System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SYSTEMS                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Database   │  │  GDELT API   │  │ Alpha Vantage│     │
│  │  (Colleague) │  │  (News)      │  │  (Prices)    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                    ┌────────▼────────┐
                    │  UNIVERSE       │
                    │  PROVIDER       │
                    │  (Adapter)      │
                    └────────┬────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
    ┌─────▼─────────────────────────────────────▼─────┐
    │       UNIVERSE SCREENING SYSTEM (Core)          │
    │                                                  │
    │  ┌──────────────────────────────────────┐      │
    │  │      SCREENING PIPELINE              │      │
    │  │  (Orchestration + Business Logic)    │      │
    │  └──────────────────────────────────────┘      │
    │                                                  │
    └──────────────────┬───────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
    ┌─────▼──────┐          ┌──────▼──────┐
    │  Sentiment │          │  Backtesting│
    │  System    │          │  Framework  │
    └────────────┘          └─────────────┘
```

---

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: PRESENTATION (External Interface)                  │
│  • CLI (MVP)                                                 │
│  • API Endpoints (future)                                    │
│  • Backtesting Integration                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  LAYER 2: APPLICATION (Orchestration)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         SCREENING PIPELINE                            │   │
│  │  • Manages workflow                                   │   │
│  │  • Coordinates dependencies                           │   │
│  │  • Enforces business rules                            │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  LAYER 3: DOMAIN (Business Logic)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Structural  │  │  Liquidity   │  │ Data Quality │      │
│  │  Filter      │  │  Filter      │  │  Filter      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Domain Entities: Asset, ScreeningResult, Config    │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  LAYER 4: INFRASTRUCTURE (Technical Services)                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Universe  │  │   Audit    │  │  Metrics   │            │
│  │  Provider  │  │   Logger   │  │ Collector  │            │
│  │ (Abstract) │  └────────────┘  └────────────┘            │
│  └─────┬──────┘                                             │
│        │                                                     │
│  ┌─────▼──────┐  ┌──────────────┐                          │
│  │    Mock    │  │   Database   │                          │
│  │  Provider  │  │   Provider   │                          │
│  └────────────┘  └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Screening Pipeline (Orchestrator)

**Responsibility**: Coordinates entire screening workflow

```
Dependencies (Injected):
- UniverseProvider: Data access
- ScreeningConfig: Filter parameters
- AuditLogger: Audit trail
- MetricsCollector: Performance tracking
- HealthMonitor: System health
- ErrorHandler: Resilience

Workflow:
1. Validate request (date, asset_class)
2. Health check (pre-flight)
3. Bulk load data (via UniverseProvider)
4. Create DataContext (in-memory container)
5. Execute filter stages sequentially
6. Health check (post-processing)
7. Generate ScreeningResult
8. Return to caller
```

**Interface**:
```
Method: screen(request: ScreeningRequest) → ScreeningResult
  - request.date: datetime
  - request.asset_class: AssetClass
  - request.config_override: Optional[Dict]
  - request.correlation_id: str (for tracing)
```

---

### 2. Universe Provider (Adapter Interface)

**Responsibility**: Abstract all data access

```
Abstract Methods:
- get_assets(date, asset_class) → List[Asset]
  Returns all available assets at given date
  
- bulk_load_market_data(assets, start_date, end_date) → MarketDataSet
  Returns OHLCV data for multiple assets (batch query)
  
- bulk_load_metadata(assets, date) → Dict[Asset, Metadata]
  Returns structural data (exchange, sector, listing_date)
  
- check_data_availability(assets, date, lookback_days) → Dict[Asset, QualityMetrics]
  Returns missing_days count, news coverage, etc.
```

**Implementations**:
- **MockUniverseProvider**: Fake data (20 assets, 2 years history)
- **DatabaseUniverseProvider**: Real data (TBD schema, from colleague)
- **CachedUniverseProvider**: Wrapper with caching layer

---

### 3. Filter Stages (Domain Logic)

**Base Interface**:
```
Abstract Class: FilterStage
  
Methods:
- apply(assets: List[Asset], date: datetime, context: DataContext) → FilterResult
  
  Returns:
    - filtered_assets: List[Asset] (passing assets)
    - rejected_assets: List[Asset] (failing assets)
    - reasons: Dict[Asset, str] (why rejected)
    - metrics: Dict[str, Any] (stage performance)
```

**Concrete Implementations**:

#### a) StructuralFilter
```
Purpose: Filter by asset properties (type, exchange, age)

Configuration:
- allowed_asset_types: [COMMON_STOCK]
- allowed_exchanges: [NYSE, NASDAQ, XETRA]
- min_listing_age_days: 252 (1 year)

Logic:
- Check asset.asset_type in allowed_asset_types
- Check asset.exchange in allowed_exchanges
- Check (date - asset.listing_date).days >= min_listing_age_days
- Check asset not delisted at date
```

#### b) LiquidityFilter (Strategy Pattern)
```
Purpose: Filter by tradability (asset-class specific)

Strategy Selection:
- If asset.asset_class == STOCK → StockLiquidityStrategy
- If asset.asset_class == CRYPTO → CryptoLiquidityStrategy
- If asset.asset_class == FOREX → ForexLiquidityStrategy

StockLiquidityStrategy:
  - Calculate avg_dollar_volume (last 60 days)
  - Calculate trading_days_percentage
  - Check avg_dollar_volume > threshold (e.g., 5M USD)
  - Check trading_days_pct > 0.95

CryptoLiquidityStrategy:
  - Calculate order_book_depth (from market data)
  - Estimate slippage for 100k order
  - Check slippage < threshold (e.g., 0.5%)

ForexLiquidityStrategy:
  - Check avg_spread_pips < threshold (e.g., 3 pips)
  - Check 24/5 availability
```

#### c) DataAvailabilityFilter
```
Purpose: Ensure sufficient data for analysis

Configuration:
- max_missing_days: 3 (in lookback window)
- min_news_articles: 10 (optional, for GDELT)

Logic:
- Count missing days in [date-60d, date]
- Check missing_days <= max_missing_days
- Optionally: Check news_article_count >= min_news_articles
```

---

### 4. Data Context (In-Memory Container)

**Responsibility**: Hold all loaded data for filtering

```
Structure:
{
  "assets": List[Asset],  # All assets to filter
  
  "market_data": {
    Asset: DataFrame[date, open, high, low, close, volume]
  },
  
  "metadata": {
    Asset: {
      "asset_type": str,
      "exchange": str,
      "listing_date": date,
      "delisting_date": Optional[date],
      "sector": str,
      ...
    }
  },
  
  "quality_metrics": {
    Asset: {
      "missing_days": int,
      "news_count": int,
      "last_update": date
    }
  }
}

Methods:
- get_market_data(asset) → DataFrame
- get_metadata(asset) → Dict
- get_quality_metrics(asset) → Dict
```

---

### 5. Configuration System

**Structure**:
```
ScreeningConfig:
  
  global:
    default_lookback_days: 60
    timezone: "UTC"
    batch_size_mb: 2000
  
  structural_filter:
    enabled: true
    asset_types: [COMMON_STOCK]
    exchanges: [NYSE, NASDAQ, XETRA]
    min_listing_age_days: 252
  
  liquidity_filter:
    enabled: true
    
    stock:
      min_avg_dollar_volume: 5_000_000
      min_trading_days_pct: 0.95
      lookback_days: 60
    
    crypto:
      max_slippage_pct: 0.5
      min_order_book_depth: 100_000
    
    forex:
      max_spread_pips: 3
  
  data_quality_filter:
    enabled: true
    max_missing_days: 3
    min_news_articles: 10  # optional
```

**Loading**:
- YAML file → Pydantic model → Type-safe config
- Validation on load (detect typos, invalid values)
- Support config profiles (aggressive.yaml, conservative.yaml)

---

### 6. Audit & Observability

#### AuditLogger
```
Purpose: Track filtering decisions for compliance/debugging

Methods:
- log_stage_start(stage_name, input_count)
- log_stage_end(stage_name, output_count, duration)
- log_asset_filtered(asset, stage, reason)
- log_anomaly(message, severity)

Output Format: Structured JSON
{
  "timestamp": "2024-01-15T10:30:00Z",
  "correlation_id": "abc-123",
  "stage": "liquidity_filter",
  "event": "asset_filtered",
  "asset": "AAPL",
  "reason": "avg_dollar_volume=2.1M < threshold=5M"
}
```

#### MetricsCollector
```
Purpose: Track performance and system health

Metrics:
- screening_duration_seconds (histogram)
- stage_duration_seconds (histogram, by stage)
- assets_filtered_total (counter, by stage)
- data_context_size_bytes (gauge)
- peak_memory_bytes (gauge)

Export: OpenMetrics format (future Prometheus integration)
```

#### HealthMonitor
```
Purpose: Detect system anomalies

Checks:
- pre_screening(): RAM available? Provider reachable?
- post_load(): DataContext size < threshold?
- post_filtering(): Result not empty? Reduction ratio plausible?

Thresholds (from config):
- max_ram_usage_pct: 80
- max_context_size_mb: 2000
- min_output_universe_size: 10
- max_reduction_ratio: 0.99 (warn if >99% filtered)
```

---

### 7. Error Handling & Resilience

#### ErrorHandler
```
Purpose: Handle failures gracefully

Strategies:
- Retry with exponential backoff (for transient errors)
- Circuit breaker (for persistent failures)
- Partial success handling (continue with available data)
- Graceful degradation (use cached data if available)

Examples:
- UniverseProvider timeout → Retry 3x with backoff
- 50% of assets fail to load → Continue with remaining 50%, log warning
- Circuit open → Use cached data or fail fast
```

#### RequestValidator
```
Purpose: Fail fast on invalid input

Validations:
- Date not in future
- Date > 1970-01-01
- AssetClass supported
- Config complete for AssetClass
- UniverseProvider supports AssetClass
```

---

## Data Flow (End-to-End)

```
1. USER REQUEST
   ↓
   request = ScreeningRequest(
     date="2024-01-15",
     asset_class=AssetClass.STOCK
   )

2. VALIDATION
   ↓
   RequestValidator.validate(request)
   → Checks date, asset_class, config

3. HEALTH CHECK (PRE)
   ↓
   HealthMonitor.check_pre_screening()
   → RAM available? Provider responsive?

4. BULK DATA LOAD
   ↓
   assets = provider.get_assets(date, asset_class)
   → Returns 3000 stocks
   
   market_data = provider.bulk_load_market_data(assets, date-60d, date)
   → Single query for all assets
   
   metadata = provider.bulk_load_metadata(assets, date)
   → Single query for all assets
   
   quality = provider.check_data_availability(assets, date, 60)
   
   context = DataContext(assets, market_data, metadata, quality)

5. HEALTH CHECK (POST-LOAD)
   ↓
   HealthMonitor.check_post_load(context)
   → Context size < 2GB?

6. FILTER STAGE 1: STRUCTURAL
   ↓
   result1 = StructuralFilter.apply(assets, date, context)
   → 3000 → 2500 assets
   AuditLogger.log_stage_result(result1)

7. FILTER STAGE 2: LIQUIDITY
   ↓
   strategy = select_strategy(asset_class)  # StockLiquidityStrategy
   result2 = LiquidityFilter.apply(result1.assets, date, context)
   → 2500 → 800 assets
   AuditLogger.log_stage_result(result2)

8. FILTER STAGE 3: DATA QUALITY
   ↓
   result3 = DataQualityFilter.apply(result2.assets, date, context)
   → 800 → 750 assets
   AuditLogger.log_stage_result(result3)

9. HEALTH CHECK (POST-FILTER)
   ↓
   HealthMonitor.check_post_filtering(result3)
   → Output not empty? Reduction plausible?

10. CREATE RESULT
    ↓
    screening_result = ScreeningResult(
      input_universe=assets,  # 3000
      output_universe=result3.assets,  # 750
      audit_trail=[result1, result2, result3],
      metrics={...},
      metadata={...}
    )

11. RETURN TO USER
    ↓
    return screening_result
```

---

## Dependency Injection Map

```
FACTORY / MAIN
  ↓ creates
  
ConfigLoader
  ↓ loads
  
ScreeningConfig ──────────┐
                          │
UniverseProvider ─────────┤
(Mock or Database)        │
                          │
AuditLogger ──────────────┤
                          │
MetricsCollector ─────────┤
                          │
HealthMonitor ────────────┤
                          │
ErrorHandler ─────────────┤
                          │
RequestValidator ─────────┤
                          │
                          ↓
                  ScreeningPipeline
                  (all injected)
                          │
                          ↓
        ┌─────────────────┴─────────────────┐
        │                                   │
  FilterStage1              FilterStage2   FilterStage3
  (injected with          (injected with (injected with
   config params)          config params)  config params)
```

---

## Extension Points (Future)

### 1. Plugin Architecture (Filter Registry)
```
Future Enhancement:
- FilterRegistry manages all filter stages
- Stages register themselves
- Config controls which stages are active
- Users can add custom filters without modifying core

Example:
registry = FilterRegistry()
registry.register("structural", StructuralFilter)
registry.register("liquidity", LiquidityFilter)
registry.register("esg", CustomESGFilter)  # User-defined!

pipeline = ScreeningPipeline(filter_registry=registry)
```

### 2. Async/Await Support
```
Future Enhancement:
- UniverseProvider methods become async
- Pipeline runs filters in parallel where possible
- Better scalability for I/O-heavy operations

Example:
async def screen(request):
    assets = await provider.get_assets(...)
    data = await provider.bulk_load_market_data(...)
    results = await asyncio.gather(
        filter1.apply(...),
        filter2.apply(...),
        filter3.apply(...)
    )
```

### 3. Event-Driven Architecture
```
Future Enhancement:
- Pipeline emits events (ScreeningStarted, StageCompleted, etc.)
- Components subscribe to events
- Loose coupling, easy to extend

Example:
event_bus.subscribe(ScreeningCompleted, my_custom_analyzer)
```

### 4. Derivative Resolver
```
Future Enhancement:
- Map underlying assets to tradable derivatives
- Filter by leverage, broker, costs

Example:
instruments = derivative_resolver.get_tradable_instruments(
    underlying=filtered_assets,
    min_leverage=5,
    max_leverage=20,
    broker="Interactive Brokers"
)
```

---

## Technology Stack

### Core
- **Python**: 3.10+ (type hints, dataclasses, match statements)
- **Pydantic**: Type-safe configs and data models
- **PyYAML**: Configuration files
- **python-dateutil**: Datetime handling

### Testing
- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **hypothesis**: Property-based testing (future)

### Code Quality
- **black**: Code formatter
- **ruff**: Fast linter (replaces flake8, isort, etc.)
- **mypy**: Static type checker

### Observability (Future)
- **structlog**: Structured logging
- **prometheus_client**: Metrics export
- **OpenTelemetry**: Distributed tracing

---

## Design Patterns Used

1. **Hexagonal Architecture (Ports & Adapters)**
   - Core domain isolated from infrastructure
   - Abstract interfaces for all external dependencies

2. **Strategy Pattern**
   - LiquidityFilter uses different strategies per asset class
   - Easily extensible to new asset classes

3. **Dependency Injection**
   - All dependencies injected via constructor
   - Enables testing with mocks

4. **Builder Pattern** (Future)
   - ScreeningPipelineBuilder for fluent API
   - Makes optional dependencies clear

5. **Command Pattern** (Future)
   - ScreeningRequest as command object
   - Serializable, queueable, versioned

6. **Template Method** (FilterStage)
   - Base class defines workflow
   - Subclasses implement specific logic

7. **Adapter Pattern** (UniverseProvider)
   - Abstract data access
   - Mock/Database/API adapters interchangeable

---

## Deployment Considerations (Future)

### Packaging
- Installable via pip: `pip install universe-screener`
- Separate package from main trading system
- Semantic versioning

### Configuration Management
- Environment-specific configs (dev, staging, prod)
- Config validation on startup
- Hot-reload support (no restart needed)

### Monitoring
- Prometheus metrics endpoint
- Grafana dashboards for visualization
- AlertManager for anomaly alerts

### Scalability
- Horizontal: Run multiple instances (stateless)
- Vertical: Async for I/O, multiprocessing for CPU
- Caching: Redis for shared cache across instances
