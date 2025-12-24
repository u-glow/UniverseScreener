# Deployment Guide

This guide covers deploying Universe Screener in development and production environments.

---

## Prerequisites

### System Requirements

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| Python | 3.10+ | 3.12+ |
| RAM | 2 GB | 8 GB+ |
| Disk | 500 MB | 2 GB+ |

### Required Software

- Python 3.10 or higher
- pip (Python package manager)
- Git (for version control)
- Virtual environment (venv recommended)

---

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/universe-screener.git
cd universe-screener
```

### Step 2: Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

# If you get an execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

**Development:**
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

**Production (minimal):**
```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
# Set PYTHONPATH
export PYTHONPATH=src  # Linux/Mac
$env:PYTHONPATH = "src"  # PowerShell

# Run tests
pytest tests/unit/ -v --tb=short

# Check version
python -c "import universe_screener; print(universe_screener.__version__)"
```

---

## Configuration Files

### Directory Structure

```
config/
├── default.yaml              # Base configuration
└── profiles/
    ├── conservative.yaml     # Strict filtering
    └── aggressive.yaml       # Loose filtering
```

### Configuration Hierarchy

1. **Default** (`config/default.yaml`) - Base settings
2. **Profile** (`config/profiles/*.yaml`) - Environment overrides
3. **Runtime** (`config_override` parameter) - Per-request overrides

### Loading Configuration

```python
from universe_screener.config.loader import ConfigLoader

# Load default
config = ConfigLoader.load("config/default.yaml")

# Load with profile override
config = ConfigLoader.load_with_profile(
    "config/default.yaml",
    "config/profiles/conservative.yaml"
)

# Load from dict (for testing)
config = ConfigLoader.from_dict({
    "version": "1.0",
    "structural_filter": {"min_listing_age_days": 30}
})
```

### Key Configuration Options

| Section | Option | Default | Description |
|---------|--------|---------|-------------|
| `global` | `default_lookback_days` | 60 | Days of history to load |
| `structural_filter` | `min_listing_age_days` | 252 | Minimum age (trading days) |
| `liquidity_filter.stock` | `min_avg_dollar_volume_usd` | 5M | Min daily volume |
| `data_quality_filter` | `max_missing_days` | 3 | Max missing data days |
| `cache` | `max_size_mb` | 1024 | Cache size limit (MB) |
| `cache` | `default_ttl_seconds` | 3600 | Cache entry lifetime |

---

## Environment Setup

### Development

```python
import logging
import universe_screener

# Enable verbose logging
universe_screener.configure_logging(logging.DEBUG)

# Use mock provider (no database needed)
from universe_screener.adapters.mock_provider import MockUniverseProvider
provider = MockUniverseProvider()
```

### Production

```python
import logging
import universe_screener

# Production logging (less verbose)
universe_screener.configure_logging(logging.INFO)

# Option 1: Use MockUniverseProvider with cache (for development/testing)
from universe_screener.adapters.cached_provider import CachedUniverseProvider
from universe_screener.adapters.mock_provider import MockUniverseProvider

provider = CachedUniverseProvider(MockUniverseProvider())

# Option 2: Use DatabaseUniverseProvider (when schema is available)
# NOTE: DatabaseUniverseProvider is currently a TEMPLATE only.
#       Implement the TODO methods when your database schema is finalized.
#
# from universe_screener.adapters.database_provider import DatabaseUniverseProvider
# 
# db_provider = DatabaseUniverseProvider(
#     connection_pool=your_connection_pool,
#     schema="screener",
# )
# provider = CachedUniverseProvider(db_provider)
```

### Environment Variables (Optional)

```bash
# Database connection (example)
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=screener
export DB_USER=screener_user
export DB_PASSWORD=your_password

# Logging
export LOG_LEVEL=INFO
export LOG_FORMAT=json
```

---

## Database Integration

> **Note:** Database schema is TBD. This section will be updated when the schema is finalized.

### Expected Schema

```sql
-- Assets table
CREATE TABLE assets (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    asset_class VARCHAR(20) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    listing_date DATE NOT NULL,
    delisting_date DATE,
    sector VARCHAR(100),
    country VARCHAR(50)
);

-- Market data table
CREATE TABLE market_data (
    symbol VARCHAR(20),
    date DATE,
    open DECIMAL(18,6),
    high DECIMAL(18,6),
    low DECIMAL(18,6),
    close DECIMAL(18,6),
    volume BIGINT,
    PRIMARY KEY (symbol, date)
);

-- Index for performance
CREATE INDEX idx_market_data_symbol_date 
ON market_data (symbol, date DESC);
```

### Connection Pool Setup

```python
# Example with psycopg2 (PostgreSQL)
from psycopg2.pool import ThreadedConnectionPool

pool = ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host="localhost",
    port=5432,
    dbname="screener",
    user="screener_user",
    password="your_password",
)

provider = DatabaseUniverseProvider(
    connection_pool=pool,
    schema="public",
    batch_size=500,
)
```

---

## Running the System

### Basic Usage

```python
from datetime import datetime
from universe_screener.domain.entities import AssetClass

# Create pipeline (see Quick Start in README)
result = pipeline.screen(
    date=datetime(2024, 6, 15),
    asset_class=AssetClass.STOCK,
)
```

### Scheduled Screening

```python
import schedule
import time

def daily_screening():
    from datetime import datetime
    result = pipeline.screen(datetime.now(), AssetClass.STOCK)
    print(f"Screened {len(result.output_universe)} assets")

# Run daily at 6:00 AM
schedule.every().day.at("06:00").do(daily_screening)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### CLI (Placeholder)

```bash
# Future: Command-line interface
universe-screener screen --date 2024-06-15 --asset-class STOCK
universe-screener config --show
universe-screener health --check
```

---

## Health Monitoring

### Using HealthMonitor

```python
from universe_screener.observability.health_monitor import (
    HealthMonitor,
    HealthMonitorConfig,
)

# Configure health monitoring
health_config = HealthMonitorConfig(
    max_ram_usage_pct=80.0,
    max_context_size_mb=2000,
    min_output_universe_size=10,
    max_reduction_ratio=0.99,
)
health_monitor = HealthMonitor(health_config)

# Check before screening
pre_status = health_monitor.check_pre_screening()
if not pre_status.is_healthy:
    print(f"Warning: {pre_status.summary}")

# Check after filtering
post_status = health_monitor.check_post_filtering(result)
if not post_status.is_healthy:
    print(f"Alert: {post_status.summary}")
```

### Health Check Endpoints

| Check | Trigger | Threshold |
|-------|---------|-----------|
| RAM Usage | Pre-screening | < 80% |
| Context Size | Post-load | < 2 GB |
| Output Size | Post-filter | > 10 assets |
| Reduction Ratio | Post-filter | < 99% filtered |

---

## Logging Configuration

### Standard Logging

```python
import logging

# Basic setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
```

### Structured Logging (JSON)

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
```

### Log Levels

| Level | Use Case |
|-------|----------|
| DEBUG | Development, detailed tracing |
| INFO | Production, normal operation |
| WARNING | Anomalies, non-critical issues |
| ERROR | Failures requiring attention |

---

## Troubleshooting

### Common Issues

#### ImportError: No module named 'universe_screener'

**Cause:** PYTHONPATH not set correctly.

**Solution:**
```bash
# Windows PowerShell
$env:PYTHONPATH = "src"

# Linux/Mac
export PYTHONPATH=src
```

#### pytest: No tests collected

**Cause:** Wrong directory or PYTHONPATH issue.

**Solution:**
```bash
cd /path/to/universe-screener
$env:PYTHONPATH = "src"
pytest tests/ -v
```

#### Memory Error with large universes

**Cause:** DataContext too large.

**Solution:**
1. Reduce `global.batch_size_mb` in config
2. Enable lazy loading in DataContext
3. Use CachedUniverseProvider to reduce redundant loads

#### Cache not working

**Cause:** Cache disabled or TTL expired.

**Solution:**
```python
# Check cache config
print(cache.config.enabled)
print(cache.config.default_ttl_seconds)

# Check cache stats
print(cached_provider.get_cache_stats())
```

#### Slow performance

**Cause:** No caching, batch loading not optimized.

**Solution:**
1. Enable CachedUniverseProvider
2. Increase `batch_size` in provider
3. Check provider query performance

---

## Upgrade Guide

### From 0.3.x to 0.4.x

1. **New dependencies:** None required
2. **New config options:** `cache` section in YAML
3. **Breaking changes:** None

```yaml
# Add to your config/default.yaml
cache:
  enabled: true
  max_size_mb: 1024
  default_ttl_seconds: 3600
```

### From 0.2.x to 0.3.x

1. **New dependencies:** `structlog`
2. **New config options:** `health_monitoring` section
3. **Breaking changes:** None

---

## Next Steps

- [Performance Tuning](PERFORMANCE.md)
- [API Reference](API_REFERENCE.md)
- [Architecture Overview](architecture/02_architecture_overview.md)

