# Bugfix Requirements Document

## Introduction

The async signal handler in `main_async.py` crashes with an `AttributeError` when attempting to call `.keys()` on a `TTLCache` object. The error occurs at line 112 during cache diagnostics when trying to list available cache keys for debugging purposes. This prevents the real-time signal processing from functioning correctly, blocking the WebSocket-driven signal analysis workflow.

The `TTLCache` class in `utils/cache.py` is a custom wrapper around a dictionary that provides time-to-live functionality, but it doesn't expose a `keys()` method directly. The underlying dictionary is stored in the `cache` attribute, which does support the `keys()` method.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the `SyncCandleManagerAdapter.get_candles()` method encounters a cache miss and attempts to log available cache keys THEN the system crashes with `AttributeError: 'TTLCache' object has no attribute 'keys'`

1.2 WHEN the code executes `list(self._async_manager._cache.keys())` at line 112 THEN the system raises an AttributeError because TTLCache doesn't implement a keys() method

1.3 WHEN the async signal handler calls `_handle_signal_async()` and triggers cache diagnostics THEN the entire signal processing fails and the error is logged as "Async signal handler error for OP-USDT: 'TTLCache' object has no attribute 'keys'"

### Expected Behavior (Correct)

2.1 WHEN the `SyncCandleManagerAdapter.get_candles()` method encounters a cache miss and attempts to log available cache keys THEN the system SHALL successfully retrieve and log the cache keys without crashing

2.2 WHEN the code needs to access cache keys for debugging THEN the system SHALL access the underlying dictionary's keys via `self._async_manager._cache.cache.keys()`

2.3 WHEN the async signal handler calls `_handle_signal_async()` and triggers cache diagnostics THEN the system SHALL complete the signal processing successfully and log cache information for debugging

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the cache has valid entries and `get_candles()` finds a cache hit THEN the system SHALL CONTINUE TO return cached candles without accessing the keys() method

3.2 WHEN the TTLCache is used for normal get/set operations throughout the codebase THEN the system SHALL CONTINUE TO function correctly with the existing API

3.3 WHEN other parts of the system use TTLCache for caching (orderbook, trade flow, etc.) THEN the system SHALL CONTINUE TO operate without any changes to their behavior

3.4 WHEN the cache cleanup and expiration logic runs THEN the system SHALL CONTINUE TO remove expired entries as designed
