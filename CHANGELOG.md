# Changelog

All notable changes to Universe Screener are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.5.0] - 2024-12-24

### Phase 4: Extensibility Layer

Major release focused on dynamic filter management and derivative instrument resolution.

### Added

- **FilterRegistry** (`src/universe_screener/registry/filter_registry.py`)
  - Dynamic filter registration with `register()`, `unregister()`
  - Enable/disable filters at runtime with `enable_filters()`, `disable_filter()`
  - Version tracking per filter with `get_version()`, `get_versions()`
  - Custom factory support with `register_with_factory()`
  - Thread-safe with RLock
  - Config update support with `update_config()`

- **DerivativeResolver** (`src/universe_screener/derivatives/`)
  - Maps underlyings to tradable instruments (CFD, Turbo, Future)
  - `InstrumentFilter` for filtering by type, leverage, broker, costs
  - `get_tradable_instruments()` and `get_best_instrument()`
  - Strategy Pattern for extensibility

- **CFDResolver** (`src/universe_screener/derivatives/strategies.py`)
  - Mock CFD resolution for stocks, crypto, forex
  - Leverage calculation by asset class
  - Spread calculation

- **TurboResolver** (`src/universe_screener/derivatives/strategies.py`)
  - Knockout certificate resolution
  - Long/Short with multiple leverage levels
  - Expiry date calculation

- **FutureResolver** (`src/universe_screener/derivatives/strategies.py`)
  - Exchange-traded futures resolution
  - Multiple expiry months
  - Contract code generation

- **TradableInstrument Entity** (`src/universe_screener/derivatives/entities.py`)
  - Complete instrument representation
  - Leverage, margin, knockout, expiry support
  - Metadata for broker-specific info

- **InstrumentType Enum**
  - CFD, TURBO, FUTURE, OPTION, WARRANT, MINI_FUTURE, ETF

- **Configuration Extensions**
  - `FilterRegistryConfig` with `enabled_filters` list
  - `DerivativeConfig` with instrument types, leverage range, brokers

- **Pipeline Extensions**
  - `ScreeningPipeline` accepts `Union[List[FilterStage], FilterRegistry]`
  - Optional `derivative_resolver` parameter
  - `ScreeningResult.tradable_instruments` field

- **New Test Suites**
  - `tests/unit/test_filter_registry.py` (23 tests)
  - `tests/unit/test_derivative_resolver.py` (18 tests)
  - `tests/unit/test_cfd_resolver.py` (17 tests)
  - `tests/unit/test_turbo_resolver.py` (14 tests)
  - `tests/integration/test_pipeline_with_registry.py` (8 tests)
  - `tests/integration/test_end_to_end_with_derivatives.py` (8 tests)

### Changed

- ScreeningPipeline now supports FilterRegistry (backwards compatible with list)
- ScreeningResult includes optional `tradable_instruments`
- Version bumped to 0.5.0

### Performance

- 291 tests passing
- 89.07% code coverage

---

## [0.4.0] - 2024-12-24

### Phase 3: Scalability Layer

Major release focused on performance optimization and multi-asset-class support.

### Added

- **CacheManager** (`src/universe_screener/caching/cache_manager.py`)
  - TTL-based caching with configurable expiration
  - LRU eviction policy when max size exceeded
  - Thread-safe with reentrant lock (RLock)
  - Statistics tracking (hits, misses, evictions, expirations)
  - `get_or_compute()` convenience method
  - Pattern-based cache invalidation

- **CachedUniverseProvider** (`src/universe_screener/adapters/cached_provider.py`)
  - Wrapper pattern for any UniverseProvider
  - Caches `bulk_load_market_data()` and `bulk_load_metadata()`
  - Per-operation hit/miss tracking
  - Metrics integration for monitoring

- **CryptoLiquidityStrategy** (`src/universe_screener/filters/liquidity_strategies.py`)
  - Order book depth estimation from volume
  - Slippage calculation for $100k order
  - Configurable thresholds (max_slippage_pct, min_order_book_depth_usd)

- **ForexLiquidityStrategy** (`src/universe_screener/filters/liquidity_strategies.py`)
  - Spread calculation in pips (simulated from high-low)
  - Minimum trading days requirement (30 days)
  - Configurable max_spread_pips threshold

- **DatabaseUniverseProvider Template** (`src/universe_screener/adapters/database_provider.py`)
  - Skeleton implementation with TODOs
  - SQL query templates documented
  - Connection pooling placeholders
  - Batch query optimization outlined

- **DataContext Lazy Loading** (`src/universe_screener/pipeline/data_context.py`)
  - Optional lazy loading with callbacks
  - Memory size warning when threshold exceeded
  - `preload_all()` method for batch loading

- **CacheConfig** in configuration models
  - `enabled`, `max_size_mb`, `default_ttl_seconds`, `log_access`
  - Added to `config/default.yaml`

- **AssetType Extensions**
  - Added `CRYPTO`, `STABLECOIN`, `FOREX_PAIR`, `FOREX_CROSS`

- **New Test Suites**
  - `tests/unit/test_cache_manager.py` (26 tests)
  - `tests/unit/test_cached_provider.py` (14 tests)
  - `tests/unit/test_crypto_liquidity.py` (8 tests)
  - `tests/unit/test_forex_liquidity.py` (10 tests)
  - `tests/integration/test_multi_asset_class_screening.py` (7 tests)
  - `tests/performance/test_cached_screening_performance.py` (8 tests)

### Changed

- **LiquidityFilter** now supports STOCK, CRYPTO, and FOREX strategies
- Version bumped to 0.4.0

### Performance

- Cache hit: Second screening run < 1 second
- 203 tests passing
- 87.98% code coverage

---

## [0.3.0] - 2024-12-23

### Phase 2: Observability Layer

Release focused on operational visibility and reproducibility.

### Added

- **ObservabilityManager** (`src/universe_screener/observability/observability_manager.py`)
  - Unified logging + metrics + tracing
  - Correlation ID propagation
  - Structured JSON logging with structlog
  - Compatible with AuditLogger and MetricsCollector protocols

- **HealthMonitor** (`src/universe_screener/observability/health_monitor.py`)
  - Pre-screening health checks (RAM usage)
  - Post-load health checks (DataContext size)
  - Post-filtering health checks (output size, reduction ratio)
  - Configurable thresholds

- **SnapshotManager** (`src/universe_screener/observability/snapshot_manager.py`)
  - Point-in-time consistency guarantees
  - Snapshot creation and retrieval
  - Invalidation support

- **VersionManager** (`src/universe_screener/observability/version_manager.py`)
  - Config version tracking (SHA256 hash)
  - Code version (Git SHA or package version)
  - Filter version registration

- **structlog dependency** added to requirements.txt

### Changed

- ScreeningPipeline now accepts optional observability components
- Result metadata includes version information

### Performance

- 131 tests passing
- 89.34% code coverage
- 5,000 assets screened in 0.09s

---

## [0.2.0] - 2024-12-23

### Phase 1: Resilience Layer

Release focused on production-ready error handling.

### Added

- **ErrorHandler** (`src/universe_screener/resilience/error_handler.py`)
  - Retry with exponential backoff (configurable attempts)
  - Circuit breaker pattern (opens after consecutive failures)
  - Partial failure handling (continue with available data)
  - Configurable delays and thresholds

- **RequestValidator** (`src/universe_screener/validation/request_validator.py`)
  - Date validation (not future, not pre-1970)
  - Asset class validation
  - Config completeness checks

- **DataValidator** (`src/universe_screener/validation/data_validator.py`)
  - Market data validation (no negative prices/volumes)
  - Metadata validation (required fields)
  - Outlier detection (> 10 sigma warning)

### Changed

- ScreeningPipeline integrates optional validators and error handler
- Provider calls wrapped with retry logic when ErrorHandler injected

---

## [0.1.0] - 2024-12-23

### Phase 0: Foundation (MVP)

Initial release with core filtering functionality.

### Added

- **Domain Entities**
  - `Asset` - Financial instrument representation
  - `AssetClass` - STOCK, CRYPTO, FOREX
  - `AssetType` - COMMON_STOCK, ETF, ADR, PREFERRED
  - `ScreeningRequest` - Screening input parameters
  - `ScreeningResult` - Complete screening output
  - `StageResult` - Per-filter audit information

- **Value Objects**
  - `MarketData` - OHLCV data point with computed dollar_volume
  - `QualityMetrics` - Data quality indicators
  - `FilterResult` - Filter stage output

- **Filters**
  - `StructuralFilter` - Asset type, exchange, listing age checks
  - `LiquidityFilter` - Stock liquidity (dollar volume, trading days)
  - `DataQualityFilter` - Data completeness checks

- **Pipeline**
  - `ScreeningPipeline` - Main orchestrator
  - `DataContext` - In-memory data container

- **Adapters**
  - `MockUniverseProvider` - Fake data for development
  - `ConsoleAuditLogger` - Console-based audit logging
  - `InMemoryMetricsCollector` - Simple metrics collection

- **Configuration**
  - Pydantic models for type-safe configuration
  - YAML configuration loader
  - Default configuration file

- **Testing**
  - Unit tests for all filters
  - Integration test for full pipeline
  - pytest configuration with markers

### Technical

- Python 3.10+ required
- Pydantic for configuration validation
- Type hints throughout
- Dependency injection pattern

---

## [Unreleased]

### Planned for Phase 4: Extensibility

- FilterRegistry for dynamic filter registration
- Plugin architecture for custom filters
- Async/await migration
- Event bus architecture
- Builder pattern for pipeline construction

---

## Migration Guide

### Upgrading to 0.4.0

No breaking changes. Add cache configuration to your YAML:

```yaml
cache:
  enabled: true
  max_size_mb: 1024
  default_ttl_seconds: 3600
```

### Upgrading to 0.3.0

No breaking changes. Install structlog if using JSON logging:

```bash
pip install structlog
```

### Upgrading to 0.2.0

No breaking changes. Optional components added.

---

## Links

- [README](README.md)
- [API Reference](docs/API_REFERENCE.md)
- [Architecture](docs/architecture/02_architecture_overview.md)

