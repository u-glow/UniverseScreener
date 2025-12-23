# Universe Screener

A high-performance, multi-stage asset filtering pipeline for trading systems.

## Overview

The Universe Screener reduces large asset universes (stocks, crypto, forex) to tradable subsets based on:

- **Structural criteria**: Asset type, exchange, listing age
- **Liquidity criteria**: Dollar volume, trading frequency, slippage
- **Data quality**: Missing data, news coverage

Designed for integration with sentiment analysis, backtesting, and live trading systems.

## Features

- 🚀 **High Performance**: Batch loading, in-memory filtering
- 🧪 **Testable**: Full dependency injection, mock providers
- 📊 **Observable**: Structured logging, metrics, audit trail
- ⚙️ **Configurable**: YAML configs with profile support
- 🔌 **Extensible**: Plugin-ready architecture (Strategy Pattern)

## Quick Start

```python
from universe_screener.pipeline.screening_pipeline import ScreeningPipeline
from universe_screener.adapters.mock_provider import MockUniverseProvider
from universe_screener.config.loader import load_config

# Load configuration
config = load_config("config/default.yaml")

# Create pipeline (see docs for full setup)
pipeline = create_pipeline(config)

# Screen stocks
result = pipeline.screen(
    date=datetime(2024, 1, 15),
    asset_class=AssetClass.STOCK,
)

print(f"Input: {len(result.input_universe)} assets")
print(f"Output: {len(result.output_universe)} assets")
```

## Installation

```bash
# Clone repository
git clone <repo-url>
cd universe-screener

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/ --cov=src/universe_screener
```

## Project Structure

```
universe-screener/
├── src/universe_screener/     # Main package
│   ├── domain/                # Core entities (Asset, ScreeningResult)
│   ├── interfaces/            # Abstract protocols (UniverseProvider, etc.)
│   ├── filters/               # Filter implementations
│   ├── pipeline/              # Orchestration (ScreeningPipeline)
│   ├── adapters/              # Infrastructure (MockProvider, loggers)
│   └── config/                # Configuration models and loaders
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # End-to-end tests
│   └── fixtures/              # Test data
├── config/                    # Configuration files
│   ├── default.yaml           # Default configuration
│   └── profiles/              # Configuration profiles
└── docs/architecture/         # Architecture documentation
```

## Configuration

### Default Configuration

```yaml
# config/default.yaml
structural_filter:
  allowed_exchanges: [NYSE, NASDAQ, XETRA]
  min_listing_age_days: 252

liquidity_filter:
  stock:
    min_avg_dollar_volume_usd: 5000000
    min_trading_days_pct: 0.95
```

### Profiles

- **conservative.yaml**: Strict filtering for production trading
- **aggressive.yaml**: Relaxed filtering for broader coverage
- **research.yaml**: Minimal filtering for data exploration

```python
config = load_config("config/default.yaml", profile="conservative")
```

## Architecture

The system follows **Hexagonal Architecture** (Ports & Adapters):

- **Domain Layer**: Pure business logic (entities, value objects)
- **Interface Layer**: Abstract protocols (no implementations)
- **Adapter Layer**: Concrete implementations (database, mock, etc.)
- **Application Layer**: Orchestration (ScreeningPipeline)

Key design patterns:
- Dependency Injection
- Strategy Pattern (asset-class specific logic)
- Protocol-based interfaces (not ABC)

See `docs/architecture/` for detailed documentation.

## Filter Stages

### 1. Structural Filter
Filters by asset properties:
- Asset type (COMMON_STOCK only by default)
- Exchange (NYSE, NASDAQ, XETRA)
- Listing age (≥252 days)
- Delisting status

### 2. Liquidity Filter
Filters by tradability (asset-class specific):
- **Stocks**: Average dollar volume, trading days %
- **Crypto**: Order book depth, slippage (future)
- **Forex**: Spread in pips (future)

### 3. Data Quality Filter
Filters by data availability:
- Missing days in lookback window
- News article coverage (optional)

## Development

### Running Tests

```bash
# All tests with coverage
pytest tests/ --cov=src/universe_screener --cov-report=html

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

## Project Maturity

Current maturity level: **EXPLORATION**

See `pyproject.toml` for maturity configuration and `.cursorrules` for development guidelines.

## Roadmap

- [ ] **Phase 0**: Foundation (MVP) - Core filters, mock provider
- [ ] **Phase 1**: Resilience - Error handling, validation
- [ ] **Phase 2**: Observability - Structured logging, metrics
- [ ] **Phase 3**: Scalability - Caching, database integration

See `docs/architecture/04_implementation_roadmap.md` for details.

## License

MIT License - See LICENSE file for details.

## Contributing

1. Read the architecture docs (`docs/architecture/`)
2. Follow `.cursorrules` guidelines
3. Write tests for new features
4. Submit PR with clear description

