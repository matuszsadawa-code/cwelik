# TTLCache AttributeError Bugfix Design

## Overview

The async signal handler crashes with an `AttributeError` when attempting to call `.keys()` on a `TTLCache` object at line 112 in `main_async.py`. The `TTLCache` class is a custom wrapper around a dictionary that provides time-to-live functionality but doesn't expose a `keys()` method directly. The underlying dictionary is stored in the `cache` attribute, which does support the `keys()` method.

This bug prevents real-time signal processing from functioning correctly, blocking the WebSocket-driven signal analysis workflow. The fix requires accessing the underlying dictionary's keys via `self._async_manager._cache.cache.keys()` instead of `self._async_manager._cache.keys()`.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when cache diagnostics attempt to list cache keys during a cache miss
- **Property (P)**: The desired behavior - cache diagnostics should successfully retrieve and log cache keys without crashing
- **Preservation**: Existing cache get/set operations and TTL functionality that must remain unchanged by the fix
- **TTLCache**: The custom cache class in `utils/cache.py` that wraps a dictionary with time-to-live functionality
- **SyncCandleManagerAdapter**: The adapter class in `main_async.py` that provides synchronous access to the async candle manager's cache
- **AsyncCandleManager**: The async candle manager in `data/candle_manager_async.py` that uses TTLCache for caching candle data

## Bug Details

### Bug Condition

The bug manifests when the `SyncCandleManagerAdapter.get_candles()` method encounters a cache miss and attempts to log available cache keys for debugging purposes. The code at line 112 calls `list(self._async_manager._cache.keys())`, but the `TTLCache` class doesn't implement a `keys()` method, causing an `AttributeError`.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type CacheAccessContext
  OUTPUT: boolean
  
  RETURN input.operation == "get_candles"
         AND input.cache_hit == False
         AND input.debug_logging_enabled == True
         AND input.attempts_to_call_keys_method == True
END FUNCTION
```

### Examples

- **Cache Miss Scenario**: When `get_candles("BTCUSDT", "5", 100)` is called and neither `BTCUSDT_5_cross_200` nor `BTCUSDT_5_cross_100` exist in cache, the code attempts to log available keys and crashes
- **Real-time Signal Processing**: When `_handle_signal_async()` triggers signal analysis for "OP-USDT" and encounters a cache miss, the entire signal processing fails with error: "Async signal handler error for OP-USDT: 'TTLCache' object has no attribute 'keys'"
- **WebSocket Trigger**: When a WebSocket event triggers `_on_realtime_trigger()` which calls `get_candles()`, any cache miss causes the system to crash instead of gracefully logging diagnostics
- **Edge Case - Empty Cache**: When the cache is completely empty and the code tries to log "Cache is EMPTY!", it still crashes before reaching that log statement

