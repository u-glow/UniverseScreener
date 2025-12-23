# Implementation Roadmap

## Overview

This document provides a detailed, phase-by-phase plan for implementing the Universe Screening System. Each phase has clear deliverables, success criteria, and estimated timelines.

---

## Development Philosophy

### Iterative Development Principles

1. **Walking Skeleton First**: End-to-end pipeline with minimal functionality
2. **Interface Before Implementation**: Define contracts before coding
3. **Test Alongside Code**: Not after, not before – together
4. **Document Decisions**: ADRs for architectural choices
5. **Incremental Complexity**: Add features only when needed

### Quality Over Speed

- Working software > Perfect architecture
- Testable code > Clever code
- Simple solutions > Complex solutions
- Documented decisions > Undocumented assumptions

---

## Phase 0: Foundation (MVP)

### Timeline: 1-2 Weeks

### Goals
- Prove architecture viability
- Establish development workflow
- Create foundation for iteration

### Deliverables

#### 1. Project Structure
```
universe-screener/
├── src/
│   └── universe_screener/
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── entities.py          # Asset, AssetClass, ScreeningResult
│       │   └── value_objects.py     # FilterResult, StageMetrics
│       ├── interfaces/
│       │   ├── __init__.py
│       │   ├── universe_provider.py  # Abstract interface
│       │   ├── filter_stage.py       # Abstract filter base
│       │   ├── audit_logger.py       # Abstract logger
│       │   └── metrics_collector.py  # Abstract metrics
│       ├── filters/
│       │   ├── __init__.py
│       │   ├── structural.py         # StructuralFilter
│       │   ├── liquidity.py          # LiquidityFilter + StockStrategy
│       │   └── data_quality.py       # DataQualityFilter
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── screening_pipeline.py # Main orchestrator
│       │   └── data_context.py       # In-memory data container
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── mock_provider.py      # MockUniverseProvider
│       │   └── console_logger.py     # Console logging
│       └── config/
│           ├── __init__.py
│           ├── models.py              # Pydantic config models
│           └── loader.py              # YAML config loader
├── tests/
│   ├── unit/
│   │   ├── test_structural_filter.py
│   │   ├── test_liquidity_filter.py
│   │   └── test_data_quality_filter.py
│   ├── integration/
│   │   └── test_screening_pipeline.py
│   └── fixtures/
│       └── sample_config.yaml
├── config/
│   ├── default.yaml                   # Default configuration
│   └── profiles/
│       ├── conservative.yaml
│       └── aggressive.yaml
├── docs/
│   ├── architecture/
│   │   ├── 01_requirements.md
│   │   ├── 02_architecture_overview.md
│   │   ├── 03_critical_improvements.md
│   │   └── 04_implementation_roadmap.md  # This file
│   └── decisions/
│       └── README.md
├── .cursorrules                       # Cursor AI rules
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

#### 2. Core Interfaces (All Abstract)

**Priority Order**:
1. Asset, AssetClass (domain entities)
2. UniverseProvider (data access)
3. FilterStage (filter base)
4. AuditLogger, MetricsCollector (observability)
5. ScreeningConfig (configuration)

**Acceptance Criteria**:
- All interfaces have docstrings
- All methods have type hints
- Contract documented (what each method must do)
- No implementations yet (just interfaces)

#### 3. MockUniverseProvider

**Mock Data**:
- 20 fake assets (10 stocks, 5 crypto, 5 forex)
- 2 years of daily OHLCV data
- Complete metadata (exchange, sector, listing_date)
- Realistic volumes and prices

**Purpose**:
- Enable development without database
- Provide consistent test data
- Fast iteration (no I/O overhead)

**Acceptance Criteria**:
- Returns data in same format as real provider would
- Deterministic (same data every time)
- Covers edge cases (missing data, delisted assets)

#### 4. Filter Implementations (Minimal)

**StructuralFilter**:
- Check asset_type in allowed list
- Check exchange in allowed list
- Check listing age > threshold
- Check not delisted

**LiquidityFilter**:
- StockLiquidityStrategy only (defer Crypto/Forex)
- Calculate avg_dollar_volume (60d)
- Calculate trading_days_percentage
- Apply thresholds from config

**DataQualityFilter**:
- Count missing days in lookback
- Check against threshold
- (Skip news coverage for MVP)

**Acceptance Criteria**:
- Each filter unit tested in isolation
- Clear rejection reasons logged
- Config-driven thresholds

#### 5. ScreeningPipeline (Orchestrator)

**Minimal Implementation**:
- Accept injected dependencies (provider, config, logger, metrics)
- Validate request (basic checks)
- Batch load data → DataContext
- Run filters sequentially
- Create ScreeningResult
- Return to caller

**What to Skip for MVP**:
- Advanced error handling (just fail fast)
- Health monitoring
- Performance optimization
- Async support

**Acceptance Criteria**:
- One successful end-to-end run
- Audit trail shows all stages
- Result contains input/output counts

#### 6. Configuration System

**Minimal YAML**:
```yaml
version: "1.0"

global:
  default_lookback_days: 60

structural_filter:
  enabled: true
  allowed_asset_types:
    - COMMON_STOCK
  allowed_exchanges:
    - NYSE
    - NASDAQ
  min_listing_age_days: 252

liquidity_filter:
  enabled: true
  stock:
    min_avg_dollar_volume: 5000000
    min_trading_days_pct: 0.95

data_quality_filter:
  enabled: true
  max_missing_days: 3
```

**Acceptance Criteria**:
- Pydantic validates config on load
- Invalid config → clear error message
- Support config profiles (conservative/aggressive)

#### 7. Testing

**Unit Tests**:
- `test_structural_filter.py`: 5+ test cases
- `test_liquidity_filter.py`: 5+ test cases
- `test_data_quality_filter.py`: 3+ test cases
- `test_config_loader.py`: Config validation

**Integration Test**:
- `test_screening_pipeline.py`: One happy-path test
  - Load 20 mock assets
  - Run through all filters
  - Assert expected output count
  - Verify audit trail

**Coverage Target**: 40% (critical paths)

### Success Criteria (Phase 0)

- [ ] All interfaces defined and documented
- [ ] MockUniverseProvider works with 20 assets
- [ ] Three filters implemented (Structural, Liquidity, DataQuality)
- [ ] Pipeline orchestrates filters successfully
- [ ] Config loaded from YAML
- [ ] Console logger shows filtering decisions
- [ ] One integration test passes
- [ ] `mypy` passes (no type errors)
- [ ] Documentation updated

### Estimated Effort

- Day 1: Project structure + interfaces
- Day 2-3: MockUniverseProvider + domain entities
- Day 4-5: Filter implementations
- Day 6-7: Pipeline + config system
- Day 8-9: Testing + documentation
- Day 10: Buffer for issues

**Total**: 10 days (2 weeks with interruptions)

---

## Phase 1: Resilience (Pre-Production)

### Timeline: 1 Week

### Goals
- Make system robust to failures
- Implement error handling
- Add input validation

### Deliverables

#### 1. ErrorHandler Component

**Responsibilities**:
- Retry with exponential backoff
- Circuit breaker pattern
- Partial success handling
- Graceful degradation

**Implementation**:
```
ErrorHandler:
  - retry(func, max_attempts=3, backoff_base=2)
  - circuit_breaker(failure_threshold=5, timeout=60)
  - handle_partial_failure(results, min_success_rate=0.5)
```

**Test Scenarios**:
- UniverseProvider timeout → retry 3x
- Persistent failure → circuit opens
- 50% assets fail → continue with 50%
- All assets fail → graceful error

#### 2. RequestValidator Component

**Validations**:
- Date not in future
- Date > 1970-01-01
- AssetClass supported by system
- AssetClass supported by provider
- Config complete for AssetClass

**Acceptance Criteria**:
- Invalid requests rejected before data loading
- Clear, actionable error messages
- No exceptions leak (all caught and handled)

#### 3. DataValidator Component

**Validations**:
- Market data: No negative prices/volumes
- Market data: No extreme outliers (>10 sigma)
- Metadata: Required fields present
- Metadata: Dates in valid ranges

**Behavior**:
- Warn on suspicious data (don't fail)
- Log anomalies for investigation
- Allow override in config (skip_validation=true for testing)

#### 4. Enhanced Pipeline Integration

**Changes**:
- Inject ErrorHandler, RequestValidator, DataValidator
- Wrap bulk_load in retry logic
- Validate request before processing
- Validate data after loading

**Acceptance Criteria**:
- Pipeline doesn't crash on errors
- Logs explain what went wrong
- Partial failures handled gracefully

#### 5. Error Scenario Testing

**Test Cases**:
- Provider timeout (mock delay)
- Provider returns partial data
- Provider returns corrupted data
- Invalid date in request
- Unsupported asset class
- Config missing required fields

**Coverage Target**: 60%

### Success Criteria (Phase 1)

- [ ] ErrorHandler with retry + circuit breaker working
- [ ] RequestValidator rejects invalid requests
- [ ] DataValidator warns on suspicious data
- [ ] Pipeline handles errors gracefully
- [ ] 10+ error scenario tests passing
- [ ] No uncaught exceptions in tests
- [ ] Logs structured (JSON format)

### Estimated Effort

- Day 1: ErrorHandler implementation
- Day 2: RequestValidator + DataValidator
- Day 3: Pipeline integration
- Day 4-5: Error scenario testing

**Total**: 5 days

---

## Phase 2: Observability (Production)

### Timeline: 1 Week

### Goals
- Full operational visibility
- Reproducible results
- Performance monitoring

### Deliverables

#### 1. ObservabilityManager Component

**Unifies**:
- Structured logging (JSON with `structlog`)
- Metrics collection (OpenMetrics format)
- Correlation ID propagation
- Audit trail storage

**Features**:
- Every request gets UUID correlation_id
- All logs tagged with correlation_id
- All metrics tagged with correlation_id
- End-to-end request tracing

**Example Log**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "correlation_id": "abc-123-def",
  "level": "INFO",
  "component": "liquidity_filter",
  "event": "asset_filtered",
  "asset": "AAPL",
  "reason": "avg_dollar_volume=2.1M < threshold=5M",
  "stage_duration_ms": 45
}
```

#### 2. HealthMonitor Component

**Health Checks**:
- `pre_screening()`: RAM available? Provider responsive?
- `post_load()`: DataContext size < threshold?
- `post_filtering()`: Output not empty? Reduction plausible?

**Thresholds (Configurable)**:
```yaml
health_monitoring:
  max_ram_usage_pct: 80
  max_context_size_mb: 2000
  min_output_universe_size: 10
  max_reduction_ratio: 0.99
  alert_on_anomaly: true
```

**Acceptance Criteria**:
- Health checks run automatically
- Anomalies logged with severity (INFO/WARNING/CRITICAL)
- Optional: Raise exception on CRITICAL

#### 3. SnapshotManager Component

**Purpose**: Guarantee point-in-time consistency

**Implementation**:
- UniverseProvider methods accept `snapshot_id`
- SnapshotManager creates immutable snapshot at T0
- All filter stages use same snapshot
- Prevents mid-screening data changes

**Acceptance Criteria**:
- Test: Modify data mid-screening → no effect
- Test: Snapshot reproducible (same ID → same data)

#### 4. VersionManager Component

**Tracks**:
- Config version (SHA256 hash of YAML)
- Code version (Git commit SHA or package version)
- Filter versions (manually versioned, e.g., "1.0.0")

**ScreeningResult Metadata**:
```yaml
metadata:
  timestamp: "2024-01-15T10:30:00Z"
  correlation_id: "abc-123"
  versions:
    config_hash: "a3f5c2..."
    code_version: "v0.2.1-abc123"
    filters:
      structural: "1.0.0"
      liquidity: "2.1.3"
      data_quality: "1.2.0"
```

**Acceptance Criteria**:
- Same config → same hash
- Different config → different hash
- Code version extracted from Git or package

#### 5. Performance Benchmarking

**Benchmarks**:
- Screen 500 assets: < 5 seconds
- Screen 5000 assets: < 10 seconds
- Memory usage < 200 MB for 5000 assets
- Prefetch time < 50% of total time

**Test Setup**:
- Use `pytest-benchmark` for reproducible tests
- Mock provider with controlled data sizes
- Measure: total time, stage times, peak RAM

**Acceptance Criteria**:
- All benchmarks pass
- Performance regression test in CI

#### 6. Monitoring Dashboards (Optional)

**If time allows**:
- Grafana dashboard with:
  - Screening requests/sec
  - Average duration
  - Filter reduction ratios
  - Error rate
  - RAM/CPU usage

**Metrics Export**:
- Prometheus endpoint: `/metrics`
- OpenMetrics format

### Success Criteria (Phase 2)

- [ ] ObservabilityManager with correlation IDs working
- [ ] HealthMonitor detects anomalies
- [ ] SnapshotManager ensures consistency
- [ ] VersionManager tracks versions
- [ ] Logs are structured JSON
- [ ] Performance benchmarks pass
- [ ] Test coverage ≥ 70%
- [ ] Documentation updated (how to read logs)

### Estimated Effort

- Day 1-2: ObservabilityManager + structured logging
- Day 3: HealthMonitor + SnapshotManager
- Day 4: VersionManager
- Day 5: Performance benchmarking
- Day 6-7: Testing + documentation

**Total**: 7 days

---

## Phase 3: Scalability (Optimization)

### Timeline: 2-3 Weeks

### Goals
- Handle large universes (>5k assets)
- Integrate real database
- Support multiple asset classes

### Deliverables

#### 1. CacheManager Component

**Strategy**: Time-based (TTL) initially

**Features**:
- Cache bulk_load results for 1 hour
- Cache key: (asset_list, date, lookback)
- Max cache size: 1 GB
- LRU eviction policy

**Acceptance Criteria**:
- Second screening with same params → cache hit
- Cache miss → fetch from provider
- Cache invalidates after TTL

#### 2. DatabaseUniverseProvider

**Implementation**:
- Adapter for real database (schema from colleague)
- Batch queries optimized (single query per stage)
- Connection pooling
- Query timeout handling

**Acceptance Criteria**:
- Passes same contract tests as MockProvider
- Performance meets benchmarks
- Error handling for DB outages

#### 3. Crypto & Forex Liquidity Strategies

**CryptoLiquidityStrategy**:
- Check order book depth
- Estimate slippage for 100k order
- Threshold: slippage < 0.5%

**ForexLiquidityStrategy**:
- Check avg spread (in pips)
- Threshold: spread < 3 pips
- Check 24/5 trading availability

**Acceptance Criteria**:
- Each strategy unit tested
- Integration test with mixed asset classes

#### 4. Memory Optimization

**Profiling**:
- Use `memory_profiler` to identify hotspots
- Optimize DataContext structure
- Consider lazy-loading for very large universes

**Batch Size Tuning**:
- Configurable batch size limit
- Automatic switching: batch < 2GB → batch_load, else lazy_load

**Acceptance Criteria**:
- Screen 10k assets without OOM
- Memory usage linear with asset count

#### 5. Parallel Asset Processing (Optional)

**If needed**:
- Process assets in parallel within filter stage
- Use `concurrent.futures` (ThreadPoolExecutor)
- Benchmark: Does parallelism help?

**Acceptance Criteria**:
- Speedup > 1.5x on multi-core machine
- No race conditions
- Deterministic results (order-independent)

### Success Criteria (Phase 3)

- [ ] CacheManager reduces redundant queries
- [ ] DatabaseProvider integrated
- [ ] Support Stock + Crypto + Forex
- [ ] Screen 10k assets in < 20 seconds
- [ ] Memory usage < 500 MB for 10k assets
- [ ] Test coverage ≥ 75%
- [ ] Performance regression tests

### Estimated Effort

- Week 1: CacheManager + memory optimization
- Week 2: DatabaseProvider integration
- Week 3: Crypto/Forex strategies + testing

**Total**: 15-20 days

---

## Phase 4: Extensibility (Future)

### Timeline: TBD (Not MVP)

### Goals
- Community-friendly architecture
- Plugin system for custom filters
- Async support for high throughput

### Deliverables (Optional)

#### 1. FilterRegistry (Plugin Architecture)

**Features**:
- Dynamic filter registration
- Config-driven filter loading
- Validation of custom filters

#### 2. Async/Await Migration

**Changes**:
- UniverseProvider methods become `async def`
- Pipeline becomes async
- Filters can run in parallel

#### 3. Event Bus Architecture

**Components**:
- EventBus for loose coupling
- Subscribers for observability
- Async event processing

#### 4. Derivative Resolver

**Features**:
- Map underlying → tradable instruments
- Filter by leverage, broker, costs

### Not Planned for MVP

- Real-time streaming mode
- GraphQL API
- Web UI/dashboard
- Multi-tenancy
- Distributed screening (multiple workers)

---

## Testing Strategy Summary

### Unit Tests (Per Component)
- Filters: 5+ test cases each
- Config: Validation tests
- Validators: Edge case coverage
- Utilities: Pure function tests

### Integration Tests
- End-to-end pipeline (happy path)
- Error scenarios (retries, partial failures)
- Multi-asset-class scenarios

### Performance Tests
- Benchmarks with `pytest-benchmark`
- Load tests (100, 1k, 10k assets)
- Memory profiling

### Contract Tests
- All UniverseProvider implementations
- All FilterStage implementations
- Ensures interface compliance

### Property-Based Tests (Phase 3+)
- Use Hypothesis
- Generate random but valid inputs
- Find edge cases automatically

---

## Continuous Integration (CI/CD)

### Phase 1: Basic CI
- Run tests on every commit
- Check code formatting (black, ruff)
- Type checking (mypy)
- Coverage report

### Phase 2: Enhanced CI
- Performance regression tests
- Contract tests
- Security scanning (Bandit)

### Phase 3: CD Pipeline
- Automatic versioning (semantic-release)
- PyPI publishing
- Docker image build
- Documentation deployment

---

## Documentation Plan

### Developer Documentation
- Architecture overview (this repo)
- API reference (auto-generated from docstrings)
- Contribution guide
- Development setup guide

### User Documentation
- Quick start guide
- Configuration reference
- Troubleshooting guide
- Examples and tutorials

### Operational Documentation
- Deployment guide
- Monitoring and alerting
- Performance tuning
- Disaster recovery

---

## Risk Management

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Database schema incompatible | High | Medium | MockProvider + adapter pattern |
| Performance bottleneck | Medium | Medium | Profiling + benchmarks early |
| Memory constraints | High | Low | Configurable batch size + monitoring |
| Over-engineering | Low | High | Strict phase boundaries |

### Schedule Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope creep | High | Medium | "Can defer" lists per phase |
| Underestimated complexity | Medium | High | Buffer time in estimates |
| Dependency on external data | High | Medium | MockProvider for development |

---

## Success Metrics

### Phase 0 (MVP)
- ✅ Working prototype in 2 weeks
- ✅ One end-to-end test passes
- ✅ Code coverage ≥ 40%

### Phase 1 (Resilience)
- ✅ Zero uncaught exceptions in tests
- ✅ Error scenarios handled gracefully
- ✅ Code coverage ≥ 60%

### Phase 2 (Production)
- ✅ Full observability (logs + metrics + traces)
- ✅ Performance benchmarks met
- ✅ Code coverage ≥ 70%

### Phase 3 (Scalability)
- ✅ Support 10k assets
- ✅ Multiple asset classes working
- ✅ Real database integrated
- ✅ Code coverage ≥ 75%

---

## Conclusion

This roadmap provides a clear path from concept to production-ready system. The phased approach allows for:
- Early validation of architecture
- Incremental complexity
- Continuous delivery of value
- Risk mitigation through iteration

**Next Steps**: Begin Phase 0 with project structure setup and interface definitions.
