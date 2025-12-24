# Universe Screener

<!-- TODO: Replace with CI badges when GitHub Actions configured:
[![Tests](https://github.com/your-org/universe-screener/actions/workflows/tests.yml/badge.svg)](https://github.com/your-org/universe-screener/actions)
[![Coverage](https://codecov.io/gh/your-org/universe-screener/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/universe-screener)
-->
[![Tests](https://img.shields.io/badge/tests-203%20passed-brightgreen)](#-testing)
[![Coverage](https://img.shields.io/badge/coverage-88%25-green)](#-testing)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**High-performance multi-stage asset filtering pipeline for trading systems.**

Universe Screener reduces large asset universes to tradable, liquid subsets by applying configurable filters based on liquidity, data quality, and structural criteria. Designed for quantitative trading systems that need to focus computational resources on assets that can actually be traded.

---

## 🎯 Key Features

### Multi-Asset-Class Support
- **Stocks**: Dollar volume, trading days, exchange filters
- **Crypto**: Order book depth, slippage estimation
- **Forex**: Spread analysis, trading availability

### Performance Optimized
- **5,000 assets** screened in **< 10 seconds**
- **TTL-based caching** reduces redundant data fetches
- **Batch loading** minimizes I/O overhead
- **LRU eviction** keeps memory usage bounded

### Production Ready
- **Resilience**: Retry logic, circuit breakers, partial failure handling
- **Observability**: Structured logging, correlation IDs, health monitoring
- **Reproducibility**: Version tracking, config hashing, point-in-time snapshots

### Extensible Architecture
- **Strategy Pattern**: Easy to add new asset-class specific logic
- **Dependency Injection**: All components are testable and swappable
- **Configuration-Driven**: Behavior controlled via YAML, not code

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/universe-screener.git
cd universe-screener

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### First Screening

```python
from datetime import datetime
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.adapters.console_logger import ConsoleAuditLogger
from universe_screener.adapters.metrics_collector import InMemoryMetricsCollector
from universe_screener.config.loader import ConfigLoader
from universe_screener.filters.structural import StructuralFilter
from universe_screener.filters.liquidity import LiquidityFilter
from universe_screener.filters.data_quality import DataQualityFilter
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline
from universe_screener.domain.entities import AssetClass

# Load configuration
config = ConfigLoader.load("config/default.yaml")

# Create pipeline with mock data
pipeline = ScreeningPipeline(
    provider=MockUniverseProvider(),
    filters=[
        StructuralFilter(config.structural_filter),
        LiquidityFilter(config.liquidity_filter),
        DataQualityFilter(config.data_quality_filter),
    ],
    config=config,
    audit_logger=ConsoleAuditLogger(),
    metrics_collector=InMemoryMetricsCollector(),
)

# Run screening
result = pipeline.screen(
    date=datetime(2024, 6, 15),
    asset_class=AssetClass.STOCK,
)

# Results
print(f"Input: {len(result.input_universe)} assets")
print(f"Output: {len(result.output_universe)} assets")
print(f"Filtered: {result.total_reduction_ratio:.1%}")

# View audit trail
for stage in result.audit_trail:
    print(f"  {stage.stage_name}: {stage.input_count} → {stage.output_count}")
```

### With Caching (Production)

```python
from universe_screener.adapters.cached_provider import CachedUniverseProvider
from universe_screener.caching.cache_manager import CacheManager, CacheConfig

# Create cached provider for repeated screenings
cache_config = CacheConfig(
    max_size_bytes=1024 * 1024 * 1024,  # 1 GB
    default_ttl_seconds=3600,  # 1 hour
)
cache = CacheManager(cache_config)
cached_provider = CachedUniverseProvider(
    provider=MockUniverseProvider(),
    cache_manager=cache,
)

# First run: cache miss (fetches data)
result1 = pipeline.screen(datetime(2024, 6, 15), AssetClass.STOCK)

# Second run: cache hit (instant)
result2 = pipeline.screen(datetime(2024, 6, 15), AssetClass.STOCK)

# View cache stats
print(cached_provider.get_cache_stats())
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      ScreeningPipeline                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Provider   │──│  DataContext │──│      Filters         │   │
│  │  (Cached)    │  │  (In-Memory) │  │ Structural→Liquidity │   │
│  └──────────────┘  └──────────────┘  │ →DataQuality         │   │
│                                      └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ AuditLogger  │  │   Metrics    │  │   HealthMonitor      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Filter Pipeline

1. **StructuralFilter**: Asset type, exchange, listing age
2. **LiquidityFilter**: Volume, trading activity (strategy per asset class)
3. **DataQualityFilter**: Data completeness, missing days

### Key Components

| Component | Purpose |
|-----------|---------|
| `ScreeningPipeline` | Orchestrates the filtering process |
| `UniverseProvider` | Supplies asset and market data |
| `CacheManager` | TTL-based caching with LRU eviction |
| `ErrorHandler` | Retry logic and circuit breakers |
| `ObservabilityManager` | Structured logging and metrics |
| `HealthMonitor` | Pre/post screening health checks |

---

## ⚙️ Configuration

### Default Configuration (`config/default.yaml`)

```yaml
version: "1.0"

global:
  default_lookback_days: 60
  timezone: "UTC"

structural_filter:
  enabled: true
  allowed_asset_types:
    - COMMON_STOCK
  allowed_exchanges:
    - NYSE
    - NASDAQ
    - XETRA
  min_listing_age_days: 252

liquidity_filter:
  enabled: true
  stock:
    min_avg_dollar_volume_usd: 5000000
    min_trading_days_pct: 0.95
  crypto:
    max_slippage_pct: 0.5
    min_order_book_depth_usd: 100000
  forex:
    max_spread_pips: 3.0

data_quality_filter:
  enabled: true
  max_missing_days: 3

cache:
  enabled: true
  max_size_mb: 1024
  default_ttl_seconds: 3600
```

### Configuration Profiles

- `config/profiles/conservative.yaml` - Stricter thresholds
- `config/profiles/aggressive.yaml` - Looser thresholds

---

## 🧪 Testing

### Run All Tests

```bash
# Set PYTHONPATH
$env:PYTHONPATH = "src"  # PowerShell
export PYTHONPATH=src    # Bash

# Run tests with coverage
pytest tests/ --cov=src/universe_screener --cov-report=term-missing -v
```

### Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Performance benchmarks
pytest tests/performance/ -v

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Test Statistics

| Category | Tests | Status |
|----------|-------|--------|
| Unit | 172 | ✅ Passing |
| Integration | 14 | ✅ Passing |
| Performance | 17 | ✅ Passing |
| **Total** | **203** | **✅ All Passing** |

---

## 📊 Performance Benchmarks

| Assets | Time | Memory |
|--------|------|--------|
| 500 | < 1s | ~50 MB |
| 1,000 | < 2s | ~100 MB |
| 5,000 | < 10s | ~200 MB |

### Cache Performance

- **First run (cold)**: Fetches from provider
- **Second run (warm)**: < 1 second (cache hit)
- **Cache hit rate**: > 95% for repeated screenings

---

## 📁 Project Structure

```
universe-screener/
├── src/universe_screener/
│   ├── domain/          # Core entities (Asset, ScreeningResult)
│   ├── interfaces/      # Abstract protocols
│   ├── filters/         # Filter implementations
│   ├── pipeline/        # Orchestration
│   ├── adapters/        # Concrete implementations
│   ├── caching/         # Cache layer
│   ├── observability/   # Logging, metrics, health
│   ├── resilience/      # Error handling, retry
│   ├── validation/      # Input/data validation
│   └── config/          # Configuration models
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   ├── performance/     # Benchmarks
│   └── fixtures/        # Test data
├── config/
│   ├── default.yaml     # Default configuration
│   └── profiles/        # Environment profiles
├── docs/
│   ├── architecture/    # Design documents
│   ├── DEPLOYMENT.md    # Deployment guide
│   ├── PERFORMANCE.md   # Performance tuning
│   └── API_REFERENCE.md # API documentation
└── requirements.txt     # Dependencies
```

---

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Follow** the coding standards (see `.cursorrules`)
4. **Write tests** for new functionality
5. **Run** the full test suite (`pytest tests/ -v`)
6. **Submit** a Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run type checking
mypy src/

# Run linting
ruff check src/

# Format code
black src/ tests/
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📚 Documentation

- [Deployment Guide](docs/DEPLOYMENT.md)
- [Performance Tuning](docs/PERFORMANCE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Architecture Overview](docs/architecture/02_architecture_overview.md)
- [Changelog](CHANGELOG.md)

---

## 🙏 Acknowledgments

- Built with [Pydantic](https://pydantic.dev/) for configuration validation
- Logging powered by [structlog](https://www.structlog.org/)
- Tested with [pytest](https://pytest.org/)
