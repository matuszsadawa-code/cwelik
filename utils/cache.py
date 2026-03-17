"""
Simple TTL Cache - Reduces API calls by caching responses.
"""

import time
import threading
from typing import Any, Optional, Dict, Callable
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with value and expiration."""
    value: Any
    expires_at: float


class TTLCache:
    """Thread-safe cache with time-to-live."""
    
    def __init__(self, default_ttl: float = 60.0):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self.lock:
            entry = self.cache.get(key)
            
            if entry is None:
                return None
            
            # Check if expired
            if time.time() > entry.expires_at:
                del self.cache[key]
                return None
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set value in cache with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        
        with self.lock:
            self.cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl
            )
    
    def delete(self, key: str):
        """Delete key from cache."""
        with self.lock:
            self.cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
    
    def cleanup(self):
        """Remove expired entries."""
        now = time.time()
        with self.lock:
            expired = [k for k, v in self.cache.items() if now > v.expires_at]
            for key in expired:
                del self.cache[key]
    
    def get_or_fetch(self, key: str, fetch_func: Callable, ttl: Optional[float] = None) -> Any:
        """Get from cache or fetch and cache."""
        # Try cache first
        value = self.get(key)
        if value is not None:
            return value
        
        # Fetch and cache
        value = fetch_func()
        if value is not None:
            self.set(key, value, ttl)
        
        return value
    
    def keys(self):
        """Return cache keys (for compatibility and debugging)."""
        with self.lock:
            return self.cache.keys()
    
    def values(self):
        """Return cache values (for compatibility and debugging)."""
        with self.lock:
            return [entry.value for entry in self.cache.values()]
    
    def items(self):
        """Return cache items as (key, value) pairs (for compatibility and debugging)."""
        with self.lock:
            return [(k, entry.value) for k, entry in self.cache.items()]
    
    def __len__(self):
        """Return number of cached items."""
        with self.lock:
            return len(self.cache)
    
    def __contains__(self, key: str):
        """Check if key exists in cache (doesn't check expiration)."""
        with self.lock:
            return key in self.cache
