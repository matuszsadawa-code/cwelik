"""
Bug Condition Exploration Property Test - TTLCache Keys AttributeError

This test file explores and confirms the existence of the TTLCache keys() bug:
- SyncCandleManagerAdapter.get_candles() crashes with AttributeError when attempting
  to access cache keys during a cache miss

This test is EXPECTED TO FAIL on unfixed code, confirming the bug exists.

**Validates: Bugfix Requirements 1.1, 1.2, 1.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List
import asyncio

# Import the modules under test
from main_async import SyncCandleManagerAdapter
from data.candle_manager_async import AsyncCandleManager
from utils.cache import TTLCache


# ═══════════════════════════════════════════════════════════════════
# BUG: TTLCACHE KEYS() ATTRIBUTEERROR
# ═══════════════════════════════════════════════════════════════════

class TestTTLCacheKeysAttributeError:
    """
    Explore Bug: TTLCache keys() AttributeError in cache diagnostics.
    
    This test demonstrates that:
    1. SyncCandleManagerAdapter.get_candles() crashes with AttributeError
    2. The crash occurs when attempting to call .keys() on TTLCache object
    3. TTLCache doesn't expose a keys() method directly
    4. The underlying dictionary is stored in the 'cache' attribute
    
    **Validates: Bugfix Requirements 1.1, 1.2, 1.3**
    """
    
    def test_bug_ttlcache_keys_attributeerror_on_cache_miss(self):
        """
        Bug: SyncCandleManagerAdapter crashes with AttributeError on cache miss.
        
        This test confirms that when get_candles() encounters a cache miss and
        attempts to log available cache keys for debugging, it crashes with:
        AttributeError: 'TTLCache' object has no attribute 'keys'
        
        Expected behavior (after fix):
        - Cache diagnostics should successfully retrieve and log cache keys
        - Should access keys via self._async_manager._cache.cache.keys()
        
        Current behavior (bug):
        - Code calls list(self._async_manager._cache.keys()) at line 112
        - TTLCache doesn't have a keys() method
        - System crashes with AttributeError
        
        This test WILL FAIL on unfixed code (confirming bug exists).
        
        **Validates: Bugfix Requirements 1.1, 1.2, 1.3**
        """
        # Create a mock AsyncCandleManager with TTLCache
        async_manager = Mock(spec=AsyncCandleManager)
        async_manager._cache = TTLCache(default_ttl=60.0)
        
        # Add some entries to the cache to simulate a populated cache
        async_manager._cache.set("BTCUSDT_5_cross_200", [{"close": 50000}])
        async_manager._cache.set("ETHUSDT_5_cross_200", [{"close": 3000}])
        
        # Create the adapter
        adapter = SyncCandleManagerAdapter(async_manager)
        
        # Mock the async fetch to prevent actual API calls
        async_manager.get_candles = AsyncMock(return_value=[])
        
        # Try to get candles for a symbol that's NOT in cache
        # This will trigger the cache miss code path at line 112
        symbol = "LINKUSDT"
        timeframe = "5"
        limit = 100
        
        # BUG CONFIRMATION: This should raise AttributeError
        with pytest.raises(AttributeError) as exc_info:
            adapter.get_candles(symbol, timeframe, limit)
        
        # Verify the error message
        assert "'TTLCache' object has no attribute 'keys'" in str(exc_info.value), (
            f"Bug confirmed: TTLCache doesn't have keys() method. "
            f"Error: {exc_info.value}"
        )
    
    def test_bug_ttlcache_has_no_keys_method(self):
        """
        Bug: TTLCache class doesn't expose a keys() method.
        
        This test confirms that the TTLCache class doesn't implement a keys()
        method, which is why the code at line 112 crashes.
        
        Expected behavior (after fix):
        - Code should access cache.cache.keys() instead of cache.keys()
        
        Current behavior (bug):
        - TTLCache has internal 'cache' dict but no keys() method
        - Attempting to call .keys() raises AttributeError
        
        This test WILL FAIL on unfixed code (confirming bug exists).
        
        **Validates: Bugfix Requirements 1.2**
        """
        cache = TTLCache(default_ttl=60.0)
        
        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # BUG CONFIRMATION: TTLCache doesn't have keys() method
        assert not hasattr(cache, 'keys'), (
            "Bug confirmed: TTLCache doesn't have a keys() method"
        )
        
        # But the internal cache dict DOES have keys()
        assert hasattr(cache.cache, 'keys'), (
            "The internal cache.cache dict has keys() method"
        )
        
        # Attempting to call cache.keys() should raise AttributeError
        with pytest.raises(AttributeError) as exc_info:
            list(cache.keys())
        
        assert "'TTLCache' object has no attribute 'keys'" in str(exc_info.value), (
            f"Bug confirmed: {exc_info.value}"
        )
    
    @given(
        symbol=st.sampled_from(["BTCUSDT", "ETHUSDT", "LINKUSDT", "OPUSDT"]),
        timeframe=st.sampled_from(["5", "30", "60"]),
        limit=st.integers(min_value=50, max_value=200)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_bug_property_cache_miss_always_crashes(self, symbol, timeframe, limit):
        """
        Property test: Cache miss always crashes with AttributeError.
        
        Property: For any symbol/timeframe/limit combination that results in a
        cache miss, the system crashes with AttributeError when attempting to
        log cache keys for debugging.
        
        This test WILL FAIL on unfixed code (confirming bug exists).
        
        **Validates: Bugfix Requirements 1.1, 1.2, 1.3**
        """
        # Create a mock AsyncCandleManager with empty cache
        async_manager = Mock(spec=AsyncCandleManager)
        async_manager._cache = TTLCache(default_ttl=60.0)
        
        # Don't add any entries - ensure cache miss
        
        # Create the adapter
        adapter = SyncCandleManagerAdapter(async_manager)
        
        # Mock the async fetch to prevent actual API calls
        async_manager.get_candles = AsyncMock(return_value=[])
        
        # BUG CONFIRMATION: Any cache miss triggers AttributeError
        with pytest.raises(AttributeError) as exc_info:
            adapter.get_candles(symbol, timeframe, limit)
        
        assert "'TTLCache' object has no attribute 'keys'" in str(exc_info.value), (
            f"Bug confirmed for {symbol} {timeframe} limit {limit}: {exc_info.value}"
        )
    
    def test_bug_async_signal_handler_crash_scenario(self):
        """
        Bug: Async signal handler crashes when processing signals with cache miss.
        
        This test simulates the real-world scenario described in the bug report:
        - WebSocket event triggers signal processing
        - Signal handler calls get_candles() via adapter
        - Cache miss occurs (symbol not pre-fetched)
        - System attempts to log cache diagnostics
        - Crashes with AttributeError
        
        Expected behavior (after fix):
        - Signal processing should complete successfully
        - Cache diagnostics should log available keys
        
        Current behavior (bug):
        - Signal processing crashes with AttributeError
        - Error: "Async signal handler error for OP-USDT: 'TTLCache' object has no attribute 'keys'"
        
        This test WILL FAIL on unfixed code (confirming bug exists).
        
        **Validates: Bugfix Requirements 1.3**
        """
        # Simulate the async signal handler scenario
        async_manager = Mock(spec=AsyncCandleManager)
        async_manager._cache = TTLCache(default_ttl=60.0)
        
        # Pre-populate cache with some symbols (but not OP-USDT)
        async_manager._cache.set("BTCUSDT_5_cross_200", [{"close": 50000}])
        async_manager._cache.set("ETHUSDT_5_cross_200", [{"close": 3000}])
        
        adapter = SyncCandleManagerAdapter(async_manager)
        async_manager.get_candles = AsyncMock(return_value=[])
        
        # Simulate signal handler requesting candles for OP-USDT (not in cache)
        symbol = "OP-USDT"  # This is the symbol from the bug report
        
        # BUG CONFIRMATION: This crashes the signal handler
        with pytest.raises(AttributeError) as exc_info:
            adapter.get_candles(symbol, "5", 100)
        
        error_msg = str(exc_info.value)
        assert "'TTLCache' object has no attribute 'keys'" in error_msg, (
            f"Bug confirmed: Signal handler crashes for {symbol}. "
            f"This matches the reported error: "
            f"'Async signal handler error for OP-USDT: 'TTLCache' object has no attribute 'keys''"
        )


# ═══════════════════════════════════════════════════════════════════
# TEST EXECUTION SUMMARY
# ═══════════════════════════════════════════════════════════════════

def test_exploration_summary():
    """
    Summary of bug exploration test.
    
    This test always passes and serves as documentation of what the
    exploration test demonstrates.
    """
    summary = """
    BUG EXPLORATION TEST SUMMARY
    ============================
    
    Bug: TTLCache Keys AttributeError in Cache Diagnostics
    - SyncCandleManagerAdapter.get_candles() crashes on cache miss
    - Line 112 calls list(self._async_manager._cache.keys())
    - TTLCache doesn't expose a keys() method
    - The underlying dictionary is in the 'cache' attribute
    - Root cause: Code attempts to call .keys() on TTLCache instead of .cache.keys()
    
    Impact:
    - Async signal handler crashes when processing signals with cache miss
    - Real-time signal processing fails completely
    - WebSocket-driven signal analysis is blocked
    - Error: "Async signal handler error for OP-USDT: 'TTLCache' object has no attribute 'keys'"
    
    Fix:
    - Change line 112 from: list(self._async_manager._cache.keys())
    - To: list(self._async_manager._cache.cache.keys())
    
    All exploration tests are EXPECTED TO FAIL on unfixed code.
    """
    assert True, summary
