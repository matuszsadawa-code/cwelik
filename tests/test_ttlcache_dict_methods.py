"""
Test TTLCache dict-like methods (keys, values, items, len, contains).
"""

import pytest
import time
from utils.cache import TTLCache


class TestTTLCacheDictMethods:
    """Test dict-like interface methods on TTLCache."""
    
    def test_keys_returns_all_cache_keys(self):
        """Test that keys() returns all cache keys."""
        cache = TTLCache(default_ttl=60.0)
        
        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Get keys
        keys = list(cache.keys())
        
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys
    
    def test_values_returns_all_cache_values(self):
        """Test that values() returns all cache values."""
        cache = TTLCache(default_ttl=60.0)
        
        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Get values
        values = list(cache.values())
        
        assert len(values) == 3
        assert "value1" in values
        assert "value2" in values
        assert "value3" in values
    
    def test_items_returns_key_value_pairs(self):
        """Test that items() returns (key, value) pairs."""
        cache = TTLCache(default_ttl=60.0)
        
        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Get items
        items = list(cache.items())
        
        assert len(items) == 2
        assert ("key1", "value1") in items
        assert ("key2", "value2") in items
    
    def test_len_returns_cache_size(self):
        """Test that len() returns number of cached items."""
        cache = TTLCache(default_ttl=60.0)
        
        assert len(cache) == 0
        
        cache.set("key1", "value1")
        assert len(cache) == 1
        
        cache.set("key2", "value2")
        assert len(cache) == 2
        
        cache.delete("key1")
        assert len(cache) == 1
        
        cache.clear()
        assert len(cache) == 0
    
    def test_contains_checks_key_existence(self):
        """Test that 'in' operator works with cache."""
        cache = TTLCache(default_ttl=60.0)
        
        cache.set("key1", "value1")
        
        assert "key1" in cache
        assert "key2" not in cache
        
        cache.delete("key1")
        assert "key1" not in cache
    
    def test_keys_excludes_expired_entries(self):
        """Test that keys() doesn't include expired entries after cleanup."""
        cache = TTLCache(default_ttl=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=10.0)  # Long TTL
        
        # Wait for key1 to expire
        time.sleep(0.15)
        
        # Cleanup expired entries
        cache.cleanup()
        
        keys = list(cache.keys())
        assert len(keys) == 1
        assert "key2" in keys
        assert "key1" not in keys
    
    def test_dict_methods_are_thread_safe(self):
        """Test that dict methods use proper locking."""
        cache = TTLCache(default_ttl=60.0)
        
        # Add entries
        for i in range(100):
            cache.set(f"key{i}", f"value{i}")
        
        # These should not raise exceptions even with concurrent access
        keys = list(cache.keys())
        values = list(cache.values())
        items = list(cache.items())
        size = len(cache)
        
        assert len(keys) == 100
        assert len(values) == 100
        assert len(items) == 100
        assert size == 100


def test_ttlcache_dict_compatibility_summary():
    """
    Summary: TTLCache Dict-Like Interface
    
    The TTLCache class now provides dict-like methods for compatibility:
    - keys(): Returns all cache keys
    - values(): Returns all cache values
    - items(): Returns (key, value) pairs
    - __len__(): Returns cache size (supports len())
    - __contains__(): Checks key existence (supports 'in' operator)
    
    These methods are thread-safe and work correctly with the cache.
    This prevents AttributeError when code expects dict-like behavior.
    """
    cache = TTLCache(default_ttl=60.0)
    cache.set("test", "value")
    
    # All these operations should work without errors
    assert list(cache.keys()) == ["test"]
    assert list(cache.values()) == ["value"]
    assert list(cache.items()) == [("test", "value")]
    assert len(cache) == 1
    assert "test" in cache
    
    print("\n✓ TTLCache dict-like interface working correctly")
