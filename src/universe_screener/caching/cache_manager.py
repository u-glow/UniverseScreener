"""
Cache Manager - TTL-based Caching with LRU Eviction.

Provides thread-safe caching for expensive data operations.

Design Notes:
    - TTL-based expiration for freshness
    - LRU eviction when max size exceeded
    - Thread-safe with Lock
    - Memory size tracking
"""

from __future__ import annotations

import hashlib
import logging
import sys
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Protocol, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheManagerProtocol(Protocol):
    """Protocol for cache manager implementations."""

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Set value in cache with optional TTL."""
        ...

    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        ...

    def clear(self) -> None:
        """Clear all cache entries."""
        ...


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""
    
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class CacheConfig:
    """Configuration for cache manager."""
    
    # Maximum cache size in bytes (default 1 GB)
    max_size_bytes: int = 1 * 1024 * 1024 * 1024
    
    # Default TTL in seconds (default 1 hour)
    default_ttl_seconds: float = 3600.0
    
    # Whether to enable caching
    enabled: bool = True
    
    # Log cache hits/misses
    log_access: bool = False


@dataclass
class CacheStats:
    """Cache statistics."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    current_size_bytes: int = 0
    current_entries: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheManager:
    """
    TTL-based cache with LRU eviction policy.
    
    Features:
        - Thread-safe with reentrant lock
        - Configurable max size (in bytes)
        - TTL-based expiration
        - LRU eviction when size exceeded
        - Statistics tracking
    
    Cache Key Format:
        f"{operation}:{params_hash}"
        
        Example: "bulk_load_market_data:a3f5c2b1..."
    """

    def __init__(self, config: Optional[CacheConfig] = None) -> None:
        """
        Initialize cache manager.
        
        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()
        self._current_size_bytes = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.config.enabled:
            return None
            
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                if self.config.log_access:
                    logger.debug(f"Cache MISS: {key}")
                return None
            
            # Check expiration
            if entry.is_expired:
                self._remove_entry(key)
                self._stats.expirations += 1
                self._stats.misses += 1
                if self.config.log_access:
                    logger.debug(f"Cache EXPIRED: {key}")
                return None
            
            # Move to end for LRU
            self._cache.move_to_end(key)
            
            self._stats.hits += 1
            if self.config.log_access:
                logger.debug(f"Cache HIT: {key}")
            
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds (uses default if None)
        """
        if not self.config.enabled:
            return
            
        ttl = ttl_seconds if ttl_seconds is not None else self.config.default_ttl_seconds
        expires_at = time.time() + ttl if ttl > 0 else None
        
        # Estimate size
        size_bytes = self._estimate_size(value)
        
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)
            
            # Evict entries if needed
            self._evict_if_needed(size_bytes)
            
            # Create and store entry
            entry = CacheEntry(
                value=value,
                expires_at=expires_at,
                size_bytes=size_bytes,
            )
            
            self._cache[key] = entry
            self._current_size_bytes += size_bytes
            
            if self.config.log_access:
                logger.debug(f"Cache SET: {key} ({size_bytes} bytes, TTL={ttl}s)")

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if entry was removed, False if not found
        """
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                logger.debug(f"Cache INVALIDATED: {key}")
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all entries matching pattern.
        
        Args:
            pattern: Pattern to match (startswith check)
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(pattern)]
            for key in keys_to_remove:
                self._remove_entry(key)
            
            if keys_to_remove:
                logger.debug(f"Cache INVALIDATED {len(keys_to_remove)} entries matching '{pattern}'")
            
            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._current_size_bytes = 0
            logger.info("Cache CLEARED")

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            stats = CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                expirations=self._stats.expirations,
                current_size_bytes=self._current_size_bytes,
                current_entries=len(self._cache),
            )
            return stats

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], T],
        ttl_seconds: Optional[float] = None,
    ) -> T:
        """
        Get from cache or compute and store.
        
        This is a convenience method that combines get and set.
        
        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl_seconds: TTL in seconds
            
        Returns:
            Cached or computed value
        """
        cached = self.get(key)
        if cached is not None:
            return cached
        
        value = compute_fn()
        self.set(key, value, ttl_seconds)
        return value

    def _remove_entry(self, key: str) -> None:
        """Remove entry from cache (internal, must hold lock)."""
        entry = self._cache.pop(key, None)
        if entry:
            self._current_size_bytes -= entry.size_bytes

    def _evict_if_needed(self, new_entry_size: int) -> None:
        """Evict entries if adding new entry would exceed max size."""
        target_size = self.config.max_size_bytes - new_entry_size
        
        while self._current_size_bytes > target_size and self._cache:
            # Remove oldest (first) entry (LRU)
            key, entry = self._cache.popitem(last=False)
            self._current_size_bytes -= entry.size_bytes
            self._stats.evictions += 1
            logger.debug(f"Cache EVICTED (LRU): {key}")

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of a value in bytes."""
        try:
            # Basic size estimate
            size = sys.getsizeof(value)
            
            # For dicts and lists, recursively estimate
            if isinstance(value, dict):
                for k, v in value.items():
                    size += sys.getsizeof(k)
                    if isinstance(v, (list, dict)):
                        size += self._estimate_size(v)
                    else:
                        size += sys.getsizeof(v)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, (list, dict)):
                        size += self._estimate_size(item)
                    else:
                        size += sys.getsizeof(item)
            
            return size
        except Exception:
            # Fallback: assume 1KB per entry
            return 1024

    @staticmethod
    def make_key(operation: str, **params: Any) -> str:
        """
        Create a cache key from operation and parameters.
        
        Args:
            operation: Operation name (e.g., "bulk_load_market_data")
            **params: Parameters to hash
            
        Returns:
            Cache key in format "operation:params_hash"
        """
        # Sort params for consistent ordering
        sorted_params = sorted(params.items())
        param_str = str(sorted_params)
        
        # Hash the parameters
        param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        
        return f"{operation}:{param_hash}"

