# Requirements: Universe Screening System

## Business Context

### Purpose
Pre-filter large asset universes (stocks, crypto, forex) before applying sentiment analysis, trading logic, and risk management. The goal is to reduce computational overhead and focus resources on tradable, liquid assets with sufficient data availability.

### Target Use Cases
- **Trading Strategy**: Daytrading and swing trading (max 5 days holding period)
- **Asset Classes**: 
  - Initial: S&P 500, XETRA (German stocks)
  - Future: APAC equities, Bitcoin, Forex
- **Instruments**: Primarily leveraged derivatives (CFDs, futures, turbos) rather than underlying assets
- **Scale**: 500-5000 assets per screening run

---

## Functional Requirements

### FR1: Multi-Stage Filtering Pipeline
- **Description**: Sequential filtering of assets through multiple independent stages
- **Stages**:
  1. **Structural Filter**: Asset type, exchange, listing age
  2. **Liquidity Filter**: Tradability based on volume/spread (asset-class specific)
  3. **Data Availability Filter**: Sufficient price data and news coverage
- **Output**: Reduced universe of eligible assets (typically 15-30% of input)

### FR2: Asset Class Polymorphism
- **Description**: Support heterogeneous asset classes with class-specific logic
- **Asset Classes**:
  - **Stocks**: Filter by dollar volume, market cap
  - **Crypto**: Filter by order book depth, slippage
  - **Forex**: Filter by spread
- **Requirement**: Same interface, different implementations (Strategy Pattern)

### FR3: Point-in-Time Data Access
- **Description**: All data must reflect state at specific datetime (no look-ahead bias)
- **Timeframes**: Support both end-of-day (EOD) and intraday (datetime-aware)
- **Consistency**: Single snapshot per screening run (transactional)

### FR4: Configuration-Driven Behavior
- **Description**: All filter parameters configurable via YAML/JSON
- **A/B Testing**: Support multiple configuration profiles
- **Parameters**: Thresholds, lookback periods, enabled stages, asset-class specific rules

### FR5: Comprehensive Audit Trail
- **Description**: Track what was filtered and why
- **Per Stage**: Input count, output count, filtered assets with reasons
- **Use Cases**: Debugging, backtesting validation, regulatory compliance

---

## Non-Functional Requirements

### NFR1: Performance
- **Target**: Screen 5000 assets in < 10 seconds (with database)
- **Strategy**: Batch-loading (prefetch all data once)
- **Scalability**: Linear time complexity O(n) in number of assets

### NFR2: Testability
- **Dependency Injection**: All external dependencies injectable
- **Mock Support**: Abstract interfaces for all data sources
- **Test Coverage**: Minimum 40% for DEVELOPMENT maturity level

### NFR3: Extensibility
- **New Filters**: Add filter stages without modifying pipeline
- **New Asset Classes**: Add asset classes without breaking existing code
- **Plugin Architecture**: (Future) Third-party filter extensions

### NFR4: Observability
- **Structured Logging**: JSON logs with correlation IDs
- **Metrics**: Execution time, reduction ratios, data quality scores
- **Health Monitoring**: RAM usage, data availability, anomaly detection

### NFR5: Reproducibility
- **Versioning**: Track code version, config hash, filter versions
- **Determinism**: Same inputs → same outputs
- **Audit**: Every screening result traceable

---

## Data Requirements

### Input Data (from Universe Provider)

#### Asset Metadata
```
Required Fields:
- symbol: str (ticker)
- name: str
- asset_class: Enum (STOCK, CRYPTO, FOREX)
- exchange: str (NYSE, NASDAQ, BINANCE, etc.)
- listing_date: date
- delisting_date: Optional[date]

Optional Fields:
- isin: str
- sector: str
- country: str
```

#### Market Data (Time Series)
```
Required Fields:
- date: datetime
- open: float
- high: float
- low: float
- close: float
- volume: int (shares)

Derived Fields:
- dollar_volume: float (close * volume)
- market_cap: float (optional, for stocks)
- bid_ask_spread: float (optional, if available)
```

#### Data Quality Metrics
```
- last_available_date: date
- missing_days_pct: float (in lookback window)
- news_article_count: int (optional, for sentiment feasibility)
```

### Output Data (Screening Result)

```
ScreeningResult:
- request:
  - date: datetime
  - asset_class: AssetClass
  - config_hash: str
- input_universe: List[Asset]
- output_universe: List[Asset]
- audit_trail: List[StageResult]
  - stage_name: str
  - input_count: int
  - output_count: int
  - filtered_assets: List[Asset]
  - filter_reasons: Dict[Asset, str]
- metrics:
  - total_time: float (seconds)
  - stage_times: Dict[str, float]
  - peak_memory: int (bytes)
- metadata:
  - timestamp: datetime
  - code_version: str
  - config_version: str
```

---

## Integration Requirements

### INT1: Universe Provider Interface
- **Type**: Abstract interface (adapter pattern)
- **Implementations**: 
  - MockProvider (fake data for development)
  - DatabaseProvider (real data, TBD schema)
- **Methods**:
  - `get_assets(date, asset_class)` → List[Asset]
  - `bulk_load_market_data(assets, start_date, end_date)` → DataFrame
  - `bulk_load_metadata(assets, date)` → Dict[Asset, Metadata]
  - `check_data_availability(assets, date, lookback_days)` → Dict[Asset, QualityMetrics]

### INT2: Configuration System
- **Format**: YAML (human-readable) with Pydantic validation
- **Location**: `config/screening_profiles/`
- **Profiles**: `conservative.yaml`, `aggressive.yaml`, `research.yaml`
- **Hot-Reload**: Support config changes without restart (future)

### INT3: Logging & Metrics
- **Logging**: Structured JSON logs (use `structlog`)
- **Metrics**: OpenMetrics compatible (future Prometheus integration)
- **Destinations**: Console (dev), file (production), remote (optional)

---

## Constraints & Assumptions

### Constraints
1. **No Real-Time**: System works with snapshots, not streaming data
2. **Read-Only**: No write operations to data source (query-only)
3. **Python 3.10+**: Type hints, dataclasses, match statements
4. **Single-Threaded MVP**: Parallelization later if needed

### Assumptions
1. **Data Availability**: UniverseProvider always returns data (or explicit None)
2. **Data Quality**: Provider returns clean data (NaNs handled upstream)
3. **Static Universe**: Asset list doesn't change during screening run
4. **Memory Budget**: Can load 5000 assets × 60 days data in RAM (~200MB)

---

## Success Criteria

### MVP Success (Phase 1)
- [ ] Filter 500 S&P 500 stocks in < 5 seconds
- [ ] Audit trail shows reason for each filtered asset
- [ ] A/B test two configurations (conservative vs aggressive)
- [ ] All interfaces defined and documented
- [ ] MockProvider with 20 fake assets working
- [ ] One integration test: end-to-end pipeline

### Production Ready (Phase 2)
- [ ] DatabaseProvider integrated (real data)
- [ ] Support 3 asset classes (Stock, Crypto, Forex)
- [ ] Health monitoring detects anomalies
- [ ] Error handling with retry logic
- [ ] Test coverage ≥ 40%
- [ ] Documentation complete

### Future Enhancements (Phase 3)
- [ ] Plugin architecture for custom filters
- [ ] Async/await for parallel processing
- [ ] Cache layer for repeated queries
- [ ] Derivative mapping (underlying → tradable instruments)
- [ ] Real-time screening (streaming mode)

---

## Out of Scope (Explicitly NOT included)

- **Sentiment Analysis**: Separate system
- **Trading Logic**: Separate system
- **Order Execution**: Not part of screening
- **Portfolio Management**: Not part of screening
- **Backtesting Framework**: Screening is ONE component of backtesting
- **UI/Dashboard**: CLI/API only for MVP

---

## Glossary

- **Universe**: Set of all potentially tradable assets
- **Screening**: Process of filtering universe to eligible subset
- **Eligible**: Asset passes all filter stages
- **Point-in-Time**: Data state at specific datetime (no future information)
- **Lookback Period**: Historical window for calculations (e.g., 60 days)
- **Batch Loading**: Loading all data upfront (vs. lazy loading)
- **Asset Class**: Category of financial instrument (Stock, Crypto, Forex)
- **Derivative**: Financial instrument derived from underlying (CFD, Future)
- **Liquidity**: Measure of tradability (volume, spread, slippage)
