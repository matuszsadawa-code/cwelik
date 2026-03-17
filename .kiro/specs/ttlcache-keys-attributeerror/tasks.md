# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - TTLCache Keys Method AttributeError
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For this deterministic bug, scope the property to the concrete failing case: cache miss scenario with debug logging enabled
  - Test that `SyncCandleManagerAdapter.get_candles()` crashes with AttributeError when attempting to access cache keys during a cache miss
  - The test should verify that calling `list(self._async_manager._cache.keys())` raises `AttributeError: 'TTLCache' object has no attribute 'keys'`
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause (e.g., "get_candles('BTCUSDT', '5', 100) with cache miss crashes with AttributeError instead of logging cache keys")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Cache Operations
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (cache hit scenarios, normal get/set operations)
  - Observe: `cache.get(key)` returns cached value when key exists
  - Observe: `cache.set(key, value)` stores value with TTL
  - Observe: Cache hit scenarios in `get_candles()` return cached candles without accessing keys()
  - Write property-based tests capturing observed behavior patterns:
    - For all valid cache keys, `cache.get(key)` returns the stored value or None if expired
    - For all cache set operations, the value is retrievable before TTL expires
    - For all cache hit scenarios in `get_candles()`, cached candles are returned without error
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for TTLCache keys() AttributeError

  - [x] 3.1 Implement the fix
    - Change line 112 in `main_async.py` from `list(self._async_manager._cache.keys())` to `list(self._async_manager._cache.cache.keys())`
    - Access the underlying dictionary's keys via the `cache` attribute
    - Ensure the fix only affects the cache diagnostics logging code path
    - _Bug_Condition: isBugCondition(input) where input.operation == "get_candles" AND input.cache_hit == False AND input.debug_logging_enabled == True AND input.attempts_to_call_keys_method == True_
    - _Expected_Behavior: Cache diagnostics successfully retrieve and log cache keys without crashing (from requirements 2.1, 2.2, 2.3)_
    - _Preservation: Existing cache get/set operations and TTL functionality remain unchanged (from requirements 3.1, 3.2, 3.3, 3.4)_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - TTLCache Keys Method Access
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Cache Operations
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
