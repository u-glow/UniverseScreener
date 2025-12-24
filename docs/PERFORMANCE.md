# Performance Guide

This guide covers performance optimization, benchmarking, and monitoring for Universe Screener.

---

## Benchmark Results

### Screening Performance

| Assets | Time | Memory | Throughput |
|--------|------|--------|------------|
| 500 | 0.5s | ~50 MB | 1,000 assets/sec |
| 1,000 | 0.9s | ~100 MB | 1,100 assets/sec |
| 5,000 | 4.5s | ~200 MB | 1,100 assets/sec |
| 10,000 | 9.0s | ~400 MB | 1,100 assets/sec |

*Measured with MockUniverseProvider, 60-day lookback, all filters enabled.*

### Stage Timing Breakdown

| Stage | % of Total | Optimization |
|-------|-----------|--------------|
| Data Loading | 60-70% | Caching, batch queries |
| Structural Filter | 5-10% | Already O(n) |
| Liquidity Filter | 10-15% | Pre-computed metrics |
| Data Quality Filter | 5-10% | Already O(n) |
| Result Building | 5-10% | Minimal overhead |

---

## Cache Configuration

### CacheManager Settings

```python
from universe_screener.caching.cache_manager import CacheManager, CacheConfig

config = CacheConfig(
    max_size_bytes=1 * 1024 * 1024 * 1024,  # 1 GB
    default_ttl_seconds=3600.0,  # 1 hour
    enabled=True,
    log_access=False,  # Set True for debugging
)

cache = CacheManager(config)
```

### YAML Configuration

```yaml
cache:
  enabled: true
  max_size_mb: 1024        # 1 GB max cache size
  default_ttl_seconds: 3600  # 1 hour TTL
  log_access: false        # Disable for production
```

### Cache Sizing Guidelines

| Universe Size | Lookback | Recommended Cache Size |
|---------------|----------|------------------------|
| < 1,000 | 60 days | 256 MB |
| 1,000 - 5,000 | 60 days | 512 MB |
| 5,000 - 10,000 | 60 days | 1 GB |
| > 10,000 | 60 days | 2 GB |

### TTL Strategy

| Use Case | Recommended TTL |
|----------|-----------------|
| Intraday screening | 15 minutes |
| Daily screening | 1 hour |
| Weekly analysis | 24 hours |
| Backtesting | Infinite (disable TTL) |

```python
# For backtesting: disable TTL
cache.set(key, value, ttl_seconds=float('inf'))
```

---

## Cache Performance

### First Run vs Cached Run

```python
import time

# First run: cache miss
start = time.perf_counter()
result1 = pipeline.screen(date, AssetClass.STOCK)
first_run = time.perf_counter() - start

# Second run: cache hit
start = time.perf_counter()
result2 = pipeline.screen(date, AssetClass.STOCK)
cached_run = time.perf_counter() - start

print(f"First run: {first_run:.3f}s")
print(f"Cached run: {cached_run:.3f}s")
print(f"Speedup: {first_run / cached_run:.1f}x")
```

**Expected Results:**
- First run: 2-5 seconds (depending on provider)
- Cached run: < 0.5 seconds
- Speedup: 5-10x

### Cache Hit Rate

```python
stats = cached_provider.get_cache_stats()

print(f"Hits: {stats['cache']['hits']}")
print(f"Misses: {stats['cache']['misses']}")
print(f"Hit Rate: {stats['cache']['hit_rate']:.1%}")
print(f"Size: {stats['cache']['size_bytes'] / 1024 / 1024:.1f} MB")
```

### Cache Invalidation

```python
# Invalidate specific data
cached_provider.invalidate_market_data()
cached_provider.invalidate_metadata()

# Clear entire cache
cache.clear()

# Invalidate by pattern
cache.invalidate_pattern("bulk_load_market_data:")
```

---

## Memory Optimization

### DataContext Sizing

```python
# Check context size
context = pipeline._load_data(request)
print(f"Context size: {context.size_mb:.1f} MB")
print(f"Assets: {len(context)}")
print(f"Per asset: {context.size_bytes / len(context) / 1024:.1f} KB")
```

### Lazy Loading

For very large universes, enable lazy loading:

```python
from universe_screener.pipeline.data_context import DataContext

# Lazy loading: data loaded on first access
context = DataContext(
    assets=assets,
    lazy_loading=True,
    market_data_loader=lambda symbol: provider.get_market_data(symbol),
    metadata_loader=lambda symbol: provider.get_metadata(symbol),
    size_warning_bytes=2 * 1024 * 1024 * 1024,  # 2 GB warning
)
```

### Memory Profiling

```python
import tracemalloc

tracemalloc.start()

# Run screening
result = pipeline.screen(date, AssetClass.STOCK)

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

tracemalloc.stop()
```

### Memory Reduction Tips

1. **Reduce lookback period**
   ```yaml
   global:
     default_lookback_days: 30  # Instead of 60
   ```

2. **Filter early**
   - Put strict filters first to reduce universe early

3. **Use lazy loading**
   - For universes > 5,000 assets

4. **Limit market data**
   - Only load OHLCV, skip additional fields

5. **Clear cache periodically**
   ```python
   cache.clear()  # After batch processing
   ```

---

## Batch Size Tuning

### Provider Batch Size

```python
from universe_screener.adapters.database_provider import DatabaseUniverseProvider

provider = DatabaseUniverseProvider(
    connection_pool=pool,
    batch_size=500,  # Tune based on DB performance
)
```

### Batch Size Guidelines

| Database | Network | Recommended Batch Size |
|----------|---------|------------------------|
| Local | Fast | 1,000 - 2,000 |
| LAN | Medium | 500 - 1,000 |
| WAN | Slow | 100 - 500 |

### Measuring Optimal Batch Size

```python
import time

for batch_size in [100, 250, 500, 1000, 2000]:
    provider = DatabaseUniverseProvider(batch_size=batch_size)
    
    start = time.perf_counter()
    data = provider.bulk_load_market_data(assets, start_date, end_date)
    elapsed = time.perf_counter() - start
    
    print(f"Batch size {batch_size}: {elapsed:.2f}s")
```

---

## Provider Performance

### Mock Provider (Development)

```python
# Very fast - generates data in memory
from universe_screener.adapters.mock_provider import MockUniverseProvider
provider = MockUniverseProvider()

# Performance: ~10,000 assets/second
```

### Database Provider (Production)

```python
# Performance depends on:
# - Query optimization
# - Index usage
# - Network latency
# - Connection pooling

# Typical: 1,000 - 5,000 assets/second
```

### Cached Provider (Recommended)

```python
# Best of both worlds:
# - First call: database speed
# - Subsequent calls: cache speed (~10,000 assets/second)

from universe_screener.adapters.cached_provider import CachedUniverseProvider
cached = CachedUniverseProvider(db_provider, cache_manager=cache)
```

### Provider Comparison

| Provider | First Call | Cached Call | Memory |
|----------|------------|-------------|--------|
| MockUniverseProvider | Fast | N/A | Low |
| DatabaseUniverseProvider | Medium | N/A | Low |
| CachedUniverseProvider | Medium | Very Fast | Higher |

---

## Monitoring Performance

### Metrics Collection

```python
from universe_screener.adapters.metrics_collector import InMemoryMetricsCollector

collector = InMemoryMetricsCollector()

# After screening
metrics = collector.get_metrics()

print(f"Data load time: {metrics.get('data_load_seconds', {}).get('last')}s")
print(f"Filter time: {metrics.get('filter_duration_seconds', {}).get('last')}s")
print(f"Total time: {metrics.get('screening_duration_seconds', {}).get('last')}s")
```

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| `screening_duration_seconds` | Total screening time | < 10s |
| `data_load_seconds` | Data loading time | < 5s |
| `filter_duration_seconds` | Per-filter execution | < 1s |
| `context_size_bytes` | DataContext memory | < 2 GB |
| `cache_hit_rate` | Cache efficiency | > 80% |

### Performance Alerts

```python
# Check performance after screening
if result.metadata.get("duration_seconds", 0) > 10:
    logging.warning(f"Slow screening: {result.metadata['duration_seconds']:.1f}s")

if context.size_mb > 1500:
    logging.warning(f"Large context: {context.size_mb:.0f} MB")
```

---

## Performance Checklist

### Before Production

- [ ] Enable caching (`cache.enabled: true`)
- [ ] Set appropriate TTL for use case
- [ ] Configure cache size based on universe
- [ ] Test with production-size data
- [ ] Verify memory usage is acceptable
- [ ] Check cache hit rate > 80%

### Optimization Priority

1. **Enable caching** - Biggest impact
2. **Tune batch size** - Reduces I/O
3. **Reduce lookback** - Less data to process
4. **Filter ordering** - Strict filters first
5. **Lazy loading** - For very large universes

### Monitoring

- Track `screening_duration_seconds` over time
- Alert on anomalies (> 2x baseline)
- Monitor cache hit rate
- Watch memory usage trends

---

## Troubleshooting Performance

### Symptom: Slow first run

**Cause:** Data loading from source is slow.

**Solutions:**
1. Check database query performance
2. Add database indexes
3. Increase provider batch size
4. Use connection pooling

### Symptom: Cache not helping

**Cause:** TTL too short, different parameters each call.

**Solutions:**
1. Increase TTL
2. Standardize screening parameters
3. Check cache key generation
4. Verify cache is enabled

### Symptom: High memory usage

**Cause:** Large universe or long lookback period.

**Solutions:**
1. Enable lazy loading
2. Reduce lookback days
3. Filter more aggressively
4. Clear cache between batches

### Symptom: Slow filters

**Cause:** Inefficient strategy implementation.

**Solutions:**
1. Profile filter execution
2. Check for O(n²) algorithms
3. Pre-compute expensive metrics
4. Consider parallel processing

---

## Next Steps

- [API Reference](API_REFERENCE.md) - Component documentation
- [Deployment Guide](DEPLOYMENT.md) - Production setup
- [Architecture](architecture/02_architecture_overview.md) - System design

