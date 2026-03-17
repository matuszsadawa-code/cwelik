"""
Query Result Caching Layer for OpenClaw Trading Dashboard

Implements TTL-based caching for database query results to reduce database load
and improve response times. Supports configurable TTL per cache key.

Features:
- TTL-based cache expiration (30-60 seconds default)
- Thread-safe cache operations
- Automatic cache invalidation
- Cache statistics tracking
- Memory-efficient storage
"""

import logging
import threading
import time
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)


class QueryCache:
    """
    Thread-safe TTL-based cache for database query results.
    
    Responsibilities:
    - Store query results with TTL
    - Automatic expiration of stale data
    - Thread-safe operations
    - Cache statistics tracking
    """
    
    def __init__(self, default_ttl: int = 30):
        """
        Initialize query cache.
        
        Args:
            default_ttl: Default TTL in seconds (default: 30)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.info(f"QueryCache initialized with default TTL: {default_ttl}s")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if time.time() > entry['expires_at']:
                del self._cache[key]
                self._evictions += 1
                self._misses += 1
                return None
            
            self._hits += 1
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set cached value with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
        """
        with self._lock:
            ttl = ttl if ttl is not None else self.default_ttl
            
            self._cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
    
    def delete(self, key: str):
        """
        Delete cached value.
        
        Args:
            key: Cache key
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._evictions += 1
    
    def clear(self):
        """Clear all cached values."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._evictions += count
            logger.info(f"Cache cleared: {count} entries removed")
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all cache keys matching pattern.
        
        Args:
            pattern: Pattern to match (simple substring match)
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
                self._evictions += 1
            
            if keys_to_delete:
                logger.info(f"Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'")
    
    def cleanup_expired(self):
        """Remove all expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                k for k, v in self._cache.items()
                if current_time > v['expires_at']
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._evictions += 1
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            dict: Cache statistics including hits, misses, hit rate, size
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': round(hit_rate, 2),
                'size': len(self._cache),
                'total_requests': total_requests
            }
    
    def reset_stats(self):
        """Reset cache statistics."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0


# Global cache instance
_global_cache = QueryCache(default_ttl=30)


def get_cache() -> QueryCache:
    """Get global cache instance."""
    return _global_cache


def cached_query(ttl: int = 30, key_prefix: str = ""):
    """
    Decorator for caching query results.
    
    Args:
        ttl: TTL in seconds
        key_prefix: Prefix for cache key
        
    Usage:
        @cached_query(ttl=60, key_prefix="performance")
        def get_performance_metrics(self):
            # Query database
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}"
            
            # Add args to key (skip self/cls if present)
            # Check if first arg is self/cls by checking if it has __dict__ or __class__
            start_idx = 0
            if args and len(args) > 0:
                first_arg = args[0]
                # Skip self/cls if it's an instance or class
                if hasattr(first_arg, '__dict__') or (isinstance(first_arg, type)):
                    start_idx = 1
            
            if len(args) > start_idx:
                cache_key += f":{':'.join(str(arg) for arg in args[start_idx:])}"
            
            # Add kwargs to key
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # Try to get from cache
            cache = get_cache()
            cached_value = cache.get(cache_key)
            
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Cache miss - execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str = ""):
    """
    Invalidate cache entries matching pattern.
    
    Args:
        pattern: Pattern to match (empty string clears all)
    """
    cache = get_cache()
    if pattern:
        cache.invalidate_pattern(pattern)
    else:
        cache.clear()
