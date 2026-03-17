"""
Performance Cache for Advanced Trading Optimization
Implements caching for expensive computations like correlation matrix and market profiles.
"""

from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import threading
import hashlib
import json


@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""
    value: Any
    timestamp: datetime
    ttl_seconds: int
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl_seconds
    
    def record_hit(self):
        """Record cache hit."""
        self.hit_count += 1


class PerformanceCache:
    """
    Thread-safe cache for expensive computations.
    
    Features:
    - TTL-based expiration
    - Thread-safe operations
    - Cache statistics
    - Automatic cleanup
    """
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
    
    def _make_key(self, namespace: str, *args, **kwargs) -> str:
        """
        Generate cache key from namespace and arguments.
        
        Args:
            namespace: Cache namespace (e.g., "correlation_matrix")
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        # Create deterministic key from arguments
        key_data = {
            "namespace": namespace,
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{namespace}:{key_hash}"
    
    def get(self, namespace: str, *args, **kwargs) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            namespace: Cache namespace
            *args: Positional arguments for key
            **kwargs: Keyword arguments for key
            
        Returns:
            Cached value or None if not found/expired
        """
        key = self._make_key(namespace, *args, **kwargs)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats["misses"] += 1
                self._stats["evictions"] += 1
                return None
            
            entry.record_hit()
            self._stats["hits"] += 1
            return entry.value
    
    def set(self, namespace: str, value: Any, ttl_seconds: int, *args, **kwargs):
        """
        Set value in cache.
        
        Args:
            namespace: Cache namespace
            value: Value to cache
            ttl_seconds: Time-to-live in seconds
            *args: Positional arguments for key
            **kwargs: Keyword arguments for key
        """
        key = self._make_key(namespace, *args, **kwargs)
        
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                timestamp=datetime.now(),
                ttl_seconds=ttl_seconds
            )
    
    def invalidate(self, namespace: str, *args, **kwargs):
        """
        Invalidate specific cache entry.
        
        Args:
            namespace: Cache namespace
            *args: Positional arguments for key
            **kwargs: Keyword arguments for key
        """
        key = self._make_key(namespace, *args, **kwargs)
        
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["evictions"] += 1
    
    def invalidate_namespace(self, namespace: str):
        """
        Invalidate all entries in a namespace.
        
        Args:
            namespace: Cache namespace to clear
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{namespace}:")]
            for key in keys_to_delete:
                del self._cache[key]
                self._stats["evictions"] += 1
    
    def cleanup_expired(self):
        """Remove all expired entries."""
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache[key]
                self._stats["evictions"] += 1
    
    def clear(self):
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            self._stats["evictions"] += len(self._cache)
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
            
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate": hit_rate,
                "size": len(self._cache),
                "total_requests": total_requests,
            }
    
    def get_entry_info(self, namespace: str, *args, **kwargs) -> Optional[Dict]:
        """
        Get information about a cache entry.
        
        Args:
            namespace: Cache namespace
            *args: Positional arguments for key
            **kwargs: Keyword arguments for key
            
        Returns:
            Entry information or None if not found
        """
        key = self._make_key(namespace, *args, **kwargs)
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            age_seconds = (datetime.now() - entry.timestamp).total_seconds()
            
            return {
                "timestamp": entry.timestamp.isoformat(),
                "age_seconds": age_seconds,
                "ttl_seconds": entry.ttl_seconds,
                "remaining_seconds": max(0, entry.ttl_seconds - age_seconds),
                "hit_count": entry.hit_count,
                "is_expired": entry.is_expired(),
            }


# Global cache instance
_global_cache = PerformanceCache()


def get_cache() -> PerformanceCache:
    """Get global cache instance."""
    return _global_cache


# Cache TTL configurations (in seconds)
CACHE_TTL = {
    "correlation_matrix": 3600,  # 1 hour
    "market_profile": 1800,      # 30 minutes
    "seasonality": 86400,        # 24 hours
    "volatility_metrics": 300,   # 5 minutes
    "wyckoff_phase": 600,        # 10 minutes
    "sentiment_score": 900,      # 15 minutes
}


def cached(namespace: str, ttl_seconds: Optional[int] = None):
    """
    Decorator for caching function results.
    
    Args:
        namespace: Cache namespace
        ttl_seconds: Time-to-live (uses CACHE_TTL if not specified)
        
    Example:
        @cached("correlation_matrix")
        def calculate_correlation(symbols, lookback_days):
            # expensive computation
            return result
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache()
            ttl = ttl_seconds or CACHE_TTL.get(namespace, 300)
            
            # Try to get from cache
            cached_value = cache.get(namespace, *args, **kwargs)
            if cached_value is not None:
                return cached_value
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(namespace, result, ttl, *args, **kwargs)
            
            return result
        
        return wrapper
    return decorator
