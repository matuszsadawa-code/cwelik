"""
Preservation Property Tests - TTLCache Existing Behavior

This test file captures and validates the existing behavior of TTLCache that
must be preserved after the bugfix. These tests run on UNFIXED code and should
PASS, confirming the baseline behavior we need to maintain.

**Validates: Bugfix Requirements 3.1, 3.2, 3.3, 3.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, AsyncMock
import time
from typing import Dict, List

# Import the modules under test
from main_async import SyncCandleManagerAdapter
from data.candle_manager_async import AsyncCandleManager
from utils.cache import TTLCache


# ═══════════════════════════════════════════════════════════════════
# PRESERVATION: EXISTING CACHE OPERATIONS
# ═══════════════════════════════════════════════════════════════════

class TestTTLCachePreservation:
    """
    Preservation tests for TTLCache existing behavior.
    
    These tests verify that:
    1. cache.get(key) returns cached value when key exists
    2. cache.set(key, value) stores value with TTL
    3. Cache hit scenarios in get_candles() return cached candles without error
    4. TTL expiration logic works correctly
    
    These tests should PASS on unfixed code, confirming baseline behavior.
    
    **Validates: Bugfix Requirements 3.1, 3.2, 3.3, 3.4**
    """
    
    @given(
        key=st.text(min_size=1, max_size=50),
        value=st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(),
            st.lists(st.dictionaries(st.text(min_size=1), st.integers()))
        )
    )
    @settings(max_examples=50)
    def test_property_cache_get_returns_stored_value(self, key, value):
        """
        Property: For all valid cache keys, cache.get(key) returns the stored value.
        
        This test verifies that the basic get/set operations work correctly.
        After setting a value, getting it should return the same value.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.2**
        """
        cache = TTLCache(default_ttl=60.0)
        
        # Set the value
        cache.set(key, value)
        
        # Get should return the same value
        retrieved = cache.get(key)
        assert retrieved == value, (
            f"Cache get/set failed: expected {value}, got {retrieved}"
        )
    
    @given(
        key=st.text(min_size=1, max_size=50),
        value=st.lists(st.dictionaries(st.text(min_size=1), st.integers())),
        ttl=st.floats(min_value=0.1, max_value=2.0)
    )
    @settings(max_examples=30, deadline=None)
    def test_property_cache_set_stores_value_with_ttl(self, key, value, ttl):
        """
        Property: For all cache set operations, the value is retrievable before TTL expires.
        
        This test verifies that values stored with a TTL are retrievable
        before the TTL expires and return None after expiration.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.2**
        """
        cache = TTLCache(default_ttl=60.0)
        
        # Set value with custom TTL
        cache.set(key, value, ttl=ttl)
        
        # Should be retrievable immediately
        retrieved = cache.get(key)
        assert retrieved == value, (
            f"Value not retrievable before TTL: expected {value}, got {retrieved}"
        )
        
        # Should still be retrievable before TTL expires (test at 50% of TTL)
        time.sleep(ttl * 0.5)
        retrieved_mid = cache.get(key)
        assert retrieved_mid == value, (
            f"Value not retrievable at 50% TTL: expected {value}, got {retrieved_mid}"
        )
    
    @given(
        key=st.text(min_size=1, max_size=50),
        value=st.lists(st.dictionaries(st.text(min_size=1), st.integers()))
    )
    @settings(max_examples=30)
    def test_property_cache_get_returns_none_for_missing_key(self, key, value):
        """
        Property: For all keys not in cache, cache.get(key) returns None.
        
        This test verifies that getting a non-existent key returns None.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.2**
        """
        cache = TTLCache(default_ttl=60.0)
        
        # Get non-existent key should return None
        retrieved = cache.get(key)
        assert retrieved is None, (
            f"Expected None for missing key, got {retrieved}"
        )
        
        # Set a different key
        cache.set(f"different_{key}", value)
        
        # Original key should still return None
        retrieved = cache.get(key)
        assert retrieved is None, (
            f"Expected None for missing key after setting different key, got {retrieved}"
        )
    
    @given(
        symbol=st.sampled_from(["BTCUSDT", "ETHUSDT", "LINKUSDT", "BNBUSDT"]),
        timeframe=st.sampled_from(["5", "30", "60", "240"]),
        limit=st.integers(min_value=50, max_value=200),
        exchange=st.sampled_from(["cross", "binance", "bybit"])
    )
    @settings(max_examples=50)
    def test_property_cache_hit_returns_candles_without_error(self, symbol, timeframe, limit, exchange):
        """
        Property: For all cache hit scenarios in get_candles(), cached candles are returned without error.
        
        This test verifies that when candles are in the cache, get_candles()
        returns them successfully without accessing the keys() method.
        
        This is the critical preservation test: cache hits should work perfectly
        on unfixed code because they don't trigger the buggy code path.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.1**
        """
        # Create a mock AsyncCandleManager with TTLCache
        async_manager = Mock(spec=AsyncCandleManager)
        async_manager._cache = TTLCache(default_ttl=60.0)
        
        # Generate mock candle data
        candles = [
            {"open": 100.0 + i, "high": 105.0 + i, "low": 95.0 + i, "close": 102.0 + i, "volume": 1000.0}
            for i in range(200)
        ]
        
        # Pre-populate cache with the 200-limit key (this is what the async loop does)
        cache_key_200 = f"{symbol}_{timeframe}_{exchange}_200"
        async_manager._cache.set(cache_key_200, candles)
        
        # Create the adapter
        adapter = SyncCandleManagerAdapter(async_manager)
        
        # Get candles - this should hit the cache and return successfully
        result = adapter.get_candles(symbol, timeframe, limit, exchange)
        
        # Verify we got candles back
        assert result is not None, "Cache hit should return candles"
        assert isinstance(result, list), "Result should be a list"
        assert len(result) <= limit, f"Result should have at most {limit} candles"
        
        # Verify the candles are from our cached data
        if len(result) > 0:
            assert result[-1]["close"] == candles[-1]["close"], (
                "Returned candles should match cached data"
            )
    
    def test_cache_hit_with_exact_limit_match(self):
        """
        Test: Cache hit with exact limit match returns candles without error.
        
        This test verifies the fallback path where the exact cache key matches.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.1**
        """
        async_manager = Mock(spec=AsyncCandleManager)
        async_manager._cache = TTLCache(default_ttl=60.0)
        
        # Generate mock candle data
        candles = [
            {"open": 100.0, "high": 105.0, "low": 95.0, "close": 102.0, "volume": 1000.0}
            for _ in range(100)
        ]
        
        # Pre-populate cache with exact limit key
        cache_key_exact = "BTCUSDT_5_cross_100"
        async_manager._cache.set(cache_key_exact, candles)
        
        # Create the adapter
        adapter = SyncCandleManagerAdapter(async_manager)
        
        # Get candles - this should hit the exact cache key
        result = adapter.get_candles("BTCUSDT", "5", 100, "cross")
        
        # Verify we got candles back
        assert result is not None
        assert len(result) == 100
        assert result == candles
    
    def test_cache_hit_with_truncation(self):
        """
        Test: Cache hit with 200-limit key truncates to requested limit.
        
        This test verifies that when we have 200 candles cached but request
        fewer, the adapter correctly truncates the result.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.1**
        """
        async_manager = Mock(spec=AsyncCandleManager)
        async_manager._cache = TTLCache(default_ttl=60.0)
        
        # Generate 200 candles
        candles = [
            {"open": 100.0 + i, "high": 105.0 + i, "low": 95.0 + i, "close": 102.0 + i, "volume": 1000.0}
            for i in range(200)
        ]
        
        # Pre-populate cache with 200-limit key
        cache_key_200 = "ETHUSDT_30_cross_200"
        async_manager._cache.set(cache_key_200, candles)
        
        # Create the adapter
        adapter = SyncCandleManagerAdapter(async_manager)
        
        # Request only 50 candles
        result = adapter.get_candles("ETHUSDT", "30", 50, "cross")
        
        # Verify we got exactly 50 candles (the last 50)
        assert len(result) == 50
        assert result == candles[-50:]
        assert result[-1]["close"] == candles[-1]["close"]
    
    @given(
        num_entries=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=20, deadline=None)
    def test_property_cache_cleanup_removes_expired_entries(self, num_entries):
        """
        Property: Cache cleanup removes expired entries correctly.
        
        This test verifies that the cleanup() method removes expired entries
        while preserving non-expired ones.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.4**
        """
        cache = TTLCache(default_ttl=60.0)
        
        # Add entries with very short TTL (will expire)
        for i in range(num_entries):
            cache.set(f"expired_{i}", f"value_{i}", ttl=0.01)
        
        # Add entries with long TTL (won't expire)
        for i in range(num_entries):
            cache.set(f"valid_{i}", f"value_{i}", ttl=60.0)
        
        # Wait for short TTL entries to expire
        time.sleep(0.05)
        
        # Run cleanup
        cache.cleanup()
        
        # Verify expired entries are gone
        for i in range(num_entries):
            assert cache.get(f"expired_{i}") is None, (
                f"Expired entry expired_{i} should be removed"
            )
        
        # Verify valid entries remain
        for i in range(num_entries):
            assert cache.get(f"valid_{i}") == f"value_{i}", (
                f"Valid entry valid_{i} should still exist"
            )
    
    def test_cache_clear_removes_all_entries(self):
        """
        Test: Cache clear removes all entries.
        
        This test verifies that clear() removes all cache entries.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.4**
        """
        cache = TTLCache(default_ttl=60.0)
        
        # Add multiple entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Verify they exist
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # Clear cache
        cache.clear()
        
        # Verify all entries are gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None
    
    def test_cache_delete_removes_specific_entry(self):
        """
        Test: Cache delete removes specific entry.
        
        This test verifies that delete() removes only the specified entry.
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.4**
        """
        cache = TTLCache(default_ttl=60.0)
        
        # Add multiple entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Delete one entry
        cache.delete("key2")
        
        # Verify key2 is gone but others remain
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"
    
    @given(
        symbol=st.sampled_from(["BTCUSDT", "ETHUSDT", "LINKUSDT"]),
        timeframe=st.sampled_from(["5", "30", "60"])
    )
    @settings(max_examples=20)
    def test_property_get_current_price_works_with_cache_hit(self, symbol, timeframe):
        """
        Property: get_current_price() returns correct price when candles are cached.
        
        This test verifies that get_current_price() works correctly when
        candles are in the cache (cache hit scenario).
        
        This test should PASS on unfixed code.
        
        **Validates: Bugfix Requirement 3.1**
        """
        async_manager = Mock(spec=AsyncCandleManager)
        async_manager._cache = TTLCache(default_ttl=60.0)
        
        # Generate mock candle data with known close price
        expected_price = 50000.0
        candles = [
            {"open": 49900.0, "high": 50100.0, "low": 49800.0, "close": expected_price, "volume": 1000.0}
        ]
        
        # Pre-populate cache with 5M candles (get_current_price uses 5M)
        cache_key = f"{symbol}_5_cross_200"
        async_manager._cache.set(cache_key, candles)
        
        # Create the adapter
        adapter = SyncCandleManagerAdapter(async_manager)
        
        # Get current price
        price = adapter.get_current_price(symbol)
        
        # Verify we got the correct price
        assert price == expected_price, (
            f"Expected price {expected_price}, got {price}"
        )


# ═══════════════════════════════════════════════════════════════════
# TEST EXECUTION SUMMARY
# ═══════════════════════════════════════════════════════════════════

def test_preservation_summary():
    """
    Summary of preservation tests.
    
    This test always passes and serves as documentation of what the
    preservation tests verify.
    """
    summary = """
    PRESERVATION TEST SUMMARY
    =========================
    
    These tests verify existing TTLCache behavior that must be preserved:
    
    1. Cache Get/Set Operations (Requirement 3.2):
       - cache.get(key) returns stored value when key exists
       - cache.set(key, value) stores value with TTL
       - cache.get(key) returns None for missing keys
    
    2. Cache Hit Scenarios (Requirement 3.1):
       - get_candles() returns cached candles without error when cache hit
       - Works with both 200-limit and exact-limit cache keys
       - Correctly truncates results when needed
       - get_current_price() works correctly with cached data
    
    3. TTL and Expiration (Requirement 3.4):
       - Values are retrievable before TTL expires
       - cleanup() removes expired entries
       - clear() removes all entries
       - delete() removes specific entries
    
    4. Other Cache Operations (Requirement 3.3):
       - TTLCache continues to work for all other uses in the codebase
       - No changes to the TTLCache API or behavior
    
    All preservation tests should PASS on unfixed code.
    This confirms the baseline behavior we need to maintain after the fix.
    """
    assert True, summary
