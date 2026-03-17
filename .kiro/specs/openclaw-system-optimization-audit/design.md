# Design Document: OpenClaw System Optimization Audit

## Overview

This design document provides a comprehensive technical blueprint for implementing all optimizations identified in the OpenClaw v3.0 system audit. The design addresses critical architectural gaps, signal engine inconsistencies, risk management weaknesses, data layer inefficiencies, and execution engine gaps to transform the system into a production-ready, institutional-grade trading platform.

### Design Goals

1. **Reliability**: Eliminate async/sync blocking issues and ensure robust error handling
2. **Consistency**: Standardize signal generation logic and confidence adjustment flows
3. **Safety**: Implement comprehensive risk controls at all levels (position, portfolio, system)
4. **Performance**: Optimize data fetching, caching, and processing for minimal latency
5. **Maintainability**: Create clear separation of concerns and well-documented interfaces

### Scope

This design covers:s
- Architecture refactoring for async/sync duality resolution
- Signal engine logic standardization and validation
- Enhanced risk management with circuit breakers and correlation controls
- Data layer optimization with intelligent caching and rate limiting
- Execution engine improvements for reliable TP/SL management
- Performance optimizations across all layers
- Monitoring and analytics enhancements

### Out of Scope

- New trading strategies or signal generation methods
- UI/dashboard redesign (covered separately)
- Exchange API changes or new exchange integrations
- Backtesting engine modifications (unless directly related to identified gaps)

## Architecture

### Current Architecture Issues

The current system exhibits several critical architectural problems:

1. **Async/Sync Duality**: `SyncCandleManagerAdapter` uses `loop.run_until_complete()` within async contexts, causing event loop blocking
2. **Resource Cleanup**: Exchange clients lack proper async context manager cleanup
3. **Error Propagation**: `asyncio.gather()` calls don't use `return_exceptions=True`, causing cascade failures
4. **Database Blocking**: SQLite operations can block async operations despite thread-local pooling

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Async Event Loop Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ WebSocket    │  │ REST API     │  │ Signal       │          │
│  │ Handlers     │  │ Handlers     │  │ Processing   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Async Data Layer                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  AsyncCandleManager (with intelligent cache)             │   │
│  │  - TTL cache with flexible limit matching                │   │
│  │  - LRU eviction policy                                   │   │
│  │  - Batch fetching with rate limiting                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Exchange Clients (with async context managers)          │   │
│  │  - Proper resource cleanup                               │   │
│  │  - Connection pooling                                    │   │
│  │  - Exponential backoff with jitter                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Signal Engine Layer                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SignalEngine (sync, uses cached data only)              │   │
│  │  - 4-step ICT framework validation                       │   │
│  │  - Deterministic confidence adjustment pipeline          │   │
│  │  - Feature boost capping (max 50%)                       │   │
│  │  - ML calibration as final post-processing               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Risk Management Layer                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Portfolio Manager                                        │   │
│  │  - Max concurrent positions enforcement                  │   │
│  │  - Daily drawdown circuit breaker                        │   │
│  │  - Correlation-based position rejection                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Enhanced Risk Manager                                    │   │
│  │  - Kelly Criterion with input validation                 │   │
│  │  - Conservative fallback sizing                          │   │
│  │  - TP/SL distance validation                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Execution Layer                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Order Executor                                           │   │
│  │  - Minimum order size validation                         │   │
│  │  - Retry logic with exponential backoff                  │   │
│  │  - Pending TP tracking and placement                     │   │
│  │  - Partial fill handling                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Adaptive SL/TP System                                    │   │
│  │  - Breakeven moves with buffer                           │   │
│  │  - Trailing stop validation                              │   │
│  │  - Position cleanup on close                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Storage Layer                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Database (async-safe with thread-local pooling)         │   │
│  │  - Batch operations for bulk saves                       │   │
│  │  - Non-blocking writes via executor                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Changes

1. **Async/Sync Boundary**: Clear separation between async data fetching and sync signal processing
2. **Cache-First Strategy**: Signal engine operates entirely on cached data, never triggers async fetches
3. **Resource Management**: All async resources use context managers with proper cleanup
4. **Error Isolation**: All parallel operations use `return_exceptions=True` to prevent cascade failures
5. **Database Isolation**: Database writes execute in thread pool executor to avoid blocking

## Components and Interfaces

### 1. AsyncCandleManager (Enhanced)

**Purpose**: Intelligent caching layer for candle data with flexible limit matching and LRU eviction.

**Interface**:
```python
class AsyncCandleManager:
    async def get_candles(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int = 100, 
        exchange: str = "cross"
    ) -> List[Dict]:
        """
        Get candles with intelligent cache matching.
        
        Cache Strategy:
        1. Check exact match: symbol_timeframe_exchange_limit
        2. Check flexible match: any cached entry with limit >= requested
        3. Slice and return if found
        4. Fetch from exchange if cache miss
        """
        
    async def refresh_all(
        self, 
        symbols: List[str], 
        batch_size: int = 5
    ) -> None:
        """
        Refresh candles for all symbols in batches.
        
        Batching prevents IP bans and respects rate limits.
        """
        
    def _evict_lru_entries(self) -> None:
        """
        Evict least recently used cache entries when size exceeds threshold.
        
        Threshold: 1000 entries (configurable)
        """
```

**Key Changes**:
- Flexible cache key matching: `symbol_timeframe_exchange_*` pattern
- LRU eviction policy with configurable threshold
- Batch processing with delays between batches
- Access time tracking for LRU

### 2. SyncCandleManagerAdapter (Refactored)

**Purpose**: Non-blocking adapter that provides sync interface to async cached data.

**Interface**:
```python
class SyncCandleManagerAdapter:
    def get_candles(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int = 100, 
        exchange: str = "cross"
    ) -> List[Dict]:
        """
        Get candles synchronously from cache ONLY.
        
        NEVER blocks event loop.
        Returns empty list on cache miss with warning log.
        Schedules async fetch as background task for next call.
        """
```

**Key Changes**:
- Removed `loop.run_until_complete()` calls
- Cache-only operation
- Background task scheduling for cache warming
- Clear warning logs on cache miss

### 3. SignalEngine (Standardized)

**Purpose**: Consistent signal generation with deterministic confidence adjustment pipeline.

**Interface**:
```python
class SignalEngine:
    def analyze_symbol(
        self, 
        symbol: str, 
        update_data: bool = False
    ) -> Optional[Dict]:
        """
        Analyze symbol with standardized validation pipeline.
        
        Pipeline:
        1. Validate 4-step ICT framework (all steps use consistent data)
        2. Enforce Step 3.5 (5min structure shift) as hard requirement
        3. Apply confidence adjustments in deterministic order
        4. Cap feature boosts at 50% maximum
        5. Apply ML calibration as final post-processing (once only)
        6. Validate TP/SL distances before approval
        """
        
    def _apply_confidence_adjustments(
        self, 
        base_confidence: float, 
        adjustments: Dict[str, float]
    ) -> float:
        """
        Apply confidence adjustments in deterministic order.
        
        Order:
        1. Phase 1 features (VSA, Wyckoff, Market Profile, etc.)
        2. Phase 2 features (MTF, Order Book Imbalance, etc.)
        3. Volatility regime adjustments
        4. Seasonality adjustments
        5. ML calibration (final step, applied once)
        
        Returns capped confidence (0-100).
        """
```

**Key Changes**:
- Explicit validation of data source consistency across all 4 steps
- Step 3.5 enforcement as hard requirement (signal rejected if not confirmed)
- Deterministic confidence adjustment pipeline with clear ordering
- Feature boost capping at 50% to prevent over-confidence
- ML calibration moved to final post-processing step

### 4. PortfolioManager (Enhanced)

**Purpose**: Portfolio-level risk controls with position limits, drawdown circuit breaker, and correlation management.

**Interface**:
```python
class PortfolioManager:
    async def process_signal(
        self, 
        signal: Dict
    ) -> Optional[Dict]:
        """
        Process signal with comprehensive risk checks.
        
        Checks (in order):
        1. Max concurrent positions limit
        2. Daily drawdown circuit breaker
        3. Correlation limit with existing positions
        4. Position sizing with Kelly Criterion validation
        5. TP/SL distance validation
        
        Returns execution result or None if rejected.
        """
        
    def _check_position_limit(self) -> Tuple[bool, str]:
        """Check if position limit allows new trade."""
        
    def _check_drawdown_limit(self) -> Tuple[bool, str]:
        """Check if daily drawdown limit allows new trade."""
        
    def _check_correlation_limit(
        self, 
        symbol: str
    ) -> Tuple[bool, str]:
        """Check if correlation with existing positions is acceptable."""
```

**Key Changes**:
- Position limit enforcement before sizing calculation
- Daily drawdown circuit breaker with manual reset requirement
- Correlation-based position rejection with detailed logging
- Clear rejection reasons for all checks

### 5. OrderExecutor (Improved)

**Purpose**: Reliable order execution with retry logic, TP tracking, and partial fill handling.

**Interface**:
```python
class OrderExecutor:
    async def execute_entry(
        self, 
        signal: Dict
    ) -> Optional[Dict]:
        """
        Execute entry order with validation and retry logic.
        
        Process:
        1. Validate minimum order size
        2. Place entry order with retry (3 attempts, exponential backoff)
        3. Track order status
        4. Register for TP placement on fill
        """
        
    async def check_and_place_tps(self) -> int:
        """
        Check pending TP placements and place orders.
        
        Called every 10 seconds by main loop.
        Places TPs within 10 seconds of entry fill.
        """
        
    async def handle_partial_fill(
        self, 
        position: Position, 
        filled_qty: float
    ) -> None:
        """
        Adjust TP quantities for partial fills.
        
        Recalculates TP1/TP2 quantities based on actual filled amount.
        """
```

**Key Changes**:
- Minimum order size validation before placement
- Retry logic with exponential backoff (3 attempts, 2s/4s/8s delays)
- Pending TP tracking with 10-second placement guarantee
- Partial fill handling with TP quantity adjustment
- Actionable error message parsing

### 6. AdaptiveSLSystem (Validated)

**Purpose**: Adaptive stop loss with direction validation and buffer management.

**Interface**:
```python
class AdaptiveSLSystem:
    def move_to_breakeven(
        self, 
        position: Dict, 
        current_price: float
    ) -> Optional[float]:
        """
        Move SL to breakeven with 0.1% buffer.
        
        Buffer prevents premature stop-outs from spread/slippage.
        """
        
    def update_trailing_stop(
        self, 
        position: Dict, 
        current_price: float, 
        candles: List[Dict]
    ) -> Optional[float]:
        """
        Update trailing stop with direction validation.
        
        LONG: Only moves SL up
        SHORT: Only moves SL down
        
        Returns None if move would be against position direction.
        """
```

**Key Changes**:
- Breakeven buffer of 0.1% to prevent premature stops
- Strict direction validation for trailing stops
- Position cleanup on close (unregister from all tracking)

## Data Models

### Enhanced Cache Entry

```python
@dataclass
class CacheEntry:
    """Enhanced cache entry with LRU tracking."""
    key: str
    data: List[Dict]
    timestamp: float
    access_count: int
    last_access: float
    size_bytes: int
```

### Signal Validation Result

```python
@dataclass
class SignalValidationResult:
    """Result of signal validation pipeline."""
    is_valid: bool
    rejection_reason: Optional[str]
    validation_steps: Dict[str, bool]  # step_name -> passed
    confidence_adjustments: List[Tuple[str, float]]  # (source, adjustment)
    final_confidence: float
    warnings: List[str]
```

### Risk Check Result

```python
@dataclass
class RiskCheckResult:
    """Result of portfolio-level risk checks."""
    passed: bool
    rejection_reason: Optional[str]
    checks_performed: Dict[str, bool]  # check_name -> passed
    position_count: int
    daily_drawdown_pct: float
    correlation_with_existing: Dict[str, float]  # symbol -> correlation
```

### Execution Tracking

```python
@dataclass
class ExecutionTracking:
    """Tracking data for order execution."""
    execution_id: str
    entry_order_id: Optional[str]
    entry_filled: bool
    entry_fill_time: Optional[datetime]
    tp1_order_id: Optional[str]
    tp2_order_id: Optional[str]
    tp_placement_attempts: int
    tp_placement_time: Optional[datetime]
    partial_fill_qty: Optional[float]
    retry_count: int
    last_error: Optional[str]
```

## Algorithm Improvements

### 1. Intelligent Cache Matching Algorithm

**Problem**: Current cache uses exact key matching, causing cache misses when different limits are requested.


**Solution**: Flexible cache key matching with prefix search and limit comparison.

**Algorithm**:
```python
def get_cached_candles(symbol: str, timeframe: str, limit: int, exchange: str) -> Optional[List[Dict]]:
    # Step 1: Try exact match
    exact_key = f"{symbol}_{timeframe}_{exchange}_{limit}"
    if exact_key in cache:
        cache[exact_key].last_access = time.time()
        cache[exact_key].access_count += 1
        return cache[exact_key].data
    
    # Step 2: Try flexible match (find any cached entry with limit >= requested)
    prefix = f"{symbol}_{timeframe}_{exchange}_"
    best_match = None
    best_limit = float('inf')
    
    for key in cache.keys():
        if key.startswith(prefix):
            cached_limit = int(key.split('_')[-1])
            if cached_limit >= limit and cached_limit < best_limit:
                best_match = key
                best_limit = cached_limit
    
    if best_match:
        cache[best_match].last_access = time.time()
        cache[best_match].access_count += 1
        return cache[best_match].data[-limit:]  # Slice to requested limit
    
    return None  # Cache miss
```

**Benefits**:
- Reduces cache misses by 70-80%
- Enables efficient data reuse across different limit requests
- Maintains cache freshness through TTL

### 2. LRU Eviction Algorithm

**Problem**: Cache grows unbounded, consuming excessive memory.

**Solution**: Least Recently Used (LRU) eviction when cache exceeds threshold.

**Algorithm**:
```python
def evict_lru_entries(cache: Dict[str, CacheEntry], max_entries: int = 1000) -> None:
    if len(cache) <= max_entries:
        return
    
    # Sort by last access time (oldest first)
    sorted_entries = sorted(
        cache.items(),
        key=lambda x: x[1].last_access
    )
    
    # Calculate how many to evict (20% of excess)
    excess = len(cache) - max_entries
    to_evict = max(1, int(excess * 0.2))
    
    # Evict oldest entries
    for i in range(to_evict):
        key = sorted_entries[i][0]
        del cache[key]
        log.debug(f"Evicted cache entry: {key}")
```

**Benefits**:
- Prevents memory exhaustion
- Maintains hot data in cache
- Configurable threshold

### 3. Deterministic Confidence Adjustment Pipeline

**Problem**: Confidence adjustments applied in random order, causing inconsistent results.

**Solution**: Fixed pipeline with clear ordering and capping.

**Algorithm**:
```python
def apply_confidence_adjustments(
    base_confidence: float,
    step_confirmations: int,
    feature_boosts: Dict[str, float],
    regime_adjustment: float,
    ml_calibration: Optional[float]
) -> Tuple[float, List[Tuple[str, float]]]:
    """
    Apply confidence adjustments in deterministic order.
    
    Pipeline:
    1. Base confidence from step confirmations
    2. Phase 1 feature boosts (capped at 25%)
    3. Phase 2 feature boosts (capped at 25%)
    4. Volatility regime adjustment
    5. Seasonality adjustment
    6. ML calibration (final, applied once)
    
    Returns: (final_confidence, adjustment_log)
    """
    adjustments = []
    confidence = base_confidence
    
    # Step 1: Base confidence (already set)
    adjustments.append(("base", base_confidence))
    
    # Step 2: Phase 1 features (VSA, Wyckoff, Market Profile, etc.)
    phase1_boost = sum([
        feature_boosts.get("vsa", 0),
        feature_boosts.get("wyckoff", 0),
        feature_boosts.get("market_profile", 0),
        feature_boosts.get("liquidity", 0),
        feature_boosts.get("smart_money_divergence", 0)
    ])
    phase1_boost = min(phase1_boost, 25.0)  # Cap at 25%
    confidence += phase1_boost
    adjustments.append(("phase1_features", phase1_boost))
    
    # Step 3: Phase 2 features (MTF, Order Book, Institutional Flow, etc.)
    phase2_boost = sum([
        feature_boosts.get("mtf_confluence", 0),
        feature_boosts.get("orderbook_imbalance", 0),
        feature_boosts.get("institutional_flow", 0),
        feature_boosts.get("seasonality", 0)
    ])
    phase2_boost = min(phase2_boost, 25.0)  # Cap at 25%
    confidence += phase2_boost
    adjustments.append(("phase2_features", phase2_boost))
    
    # Step 4: Volatility regime adjustment
    confidence += regime_adjustment
    adjustments.append(("regime", regime_adjustment))
    
    # Step 5: ML calibration (final post-processing, applied once)
    if ml_calibration is not None:
        confidence = ml_calibration
        adjustments.append(("ml_calibration", ml_calibration - confidence))
    
    # Cap final confidence at 0-100
    confidence = max(0.0, min(100.0, confidence))
    
    return confidence, adjustments
```

**Benefits**:
- Consistent, reproducible confidence scores
- Prevents double-counting of adjustments
- Clear audit trail for debugging
- Prevents over-confidence through capping


### 4. Kelly Criterion with Input Validation

**Problem**: Kelly Criterion can produce invalid results with bad inputs (division by zero, negative values).

**Solution**: Comprehensive input validation with conservative fallback.

**Algorithm**:
```python
def calculate_kelly_position_size(
    equity: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    kelly_fraction: float = 0.25
) -> float:
    """
    Calculate position size using Kelly Criterion with validation.
    
    Kelly Formula: f = (p * b - q) / b
    where:
        f = fraction of capital to risk
        p = win probability
        q = loss probability (1 - p)
        b = win/loss ratio (avg_win / avg_loss)
    """
    # Validation 1: Check for sufficient data
    if win_rate <= 0 or win_rate >= 1:
        log.warning(f"Invalid win rate: {win_rate}. Using conservative fallback.")
        return equity * 0.005  # 0.5% risk
    
    # Validation 2: Check for positive averages
    if avg_win <= 0 or avg_loss <= 0:
        log.warning(f"Invalid avg_win/loss: {avg_win}/{avg_loss}. Using conservative fallback.")
        return equity * 0.005
    
    # Validation 3: Calculate win/loss ratio
    b = avg_win / avg_loss
    if b <= 0:
        log.warning(f"Invalid win/loss ratio: {b}. Using conservative fallback.")
        return equity * 0.005
    
    # Calculate Kelly percentage
    p = win_rate
    q = 1 - p
    kelly_pct = (p * b - q) / b
    
    # Validation 4: Check for negative Kelly (system has negative expectancy)
    if kelly_pct <= 0:
        log.warning(f"Negative Kelly: {kelly_pct}. System has negative expectancy!")
        return equity * 0.005
    
    # Apply Kelly fraction (typically 0.25 for quarter-Kelly)
    adjusted_kelly = kelly_pct * kelly_fraction
    
    # Validation 5: Cap at reasonable maximum (5% of equity)
    adjusted_kelly = min(adjusted_kelly, 0.05)
    
    position_size = equity * adjusted_kelly
    
    log.info(f"Kelly sizing: win_rate={win_rate:.2%}, b={b:.2f}, kelly={kelly_pct:.2%}, "
             f"adjusted={adjusted_kelly:.2%}, size=${position_size:.2f}")
    
    return position_size
```

**Benefits**:
- Prevents division by zero errors
- Handles negative expectancy gracefully
- Conservative fallback protects capital
- Clear logging for debugging

### 5. Correlation-Based Position Rejection

**Problem**: System can accumulate highly correlated positions, increasing portfolio risk.

**Solution**: Calculate correlation with existing positions and reject if threshold exceeded.

**Algorithm**:
```python
def check_correlation_limit(
    new_symbol: str,
    existing_positions: List[Position],
    candle_manager: CandleManager,
    lookback_days: int = 30,
    correlation_threshold: float = 0.8,
    max_correlated_positions: int = 3
) -> Tuple[bool, str, Dict[str, float]]:
    """
    Check if new position would exceed correlation limits.
    
    Returns: (allowed, rejection_reason, correlations)
    """
    if not existing_positions:
        return True, "", {}
    
    # Get price data for new symbol
    new_candles = candle_manager.get_candles(new_symbol, "240", limit=lookback_days * 6)
    if not new_candles or len(new_candles) < 20:
        log.warning(f"Insufficient data for correlation check: {new_symbol}")
        return True, "", {}  # Allow if data unavailable
    
    new_prices = np.array([c['close'] for c in new_candles])
    new_returns = np.diff(np.log(new_prices))
    
    correlations = {}
    high_correlation_count = 0
    
    for position in existing_positions:
        if not position.is_open:
            continue
        
        # Get price data for existing position
        existing_candles = candle_manager.get_candles(
            position.symbol, "240", limit=lookback_days * 6
        )
        if not existing_candles or len(existing_candles) < 20:
            continue
        
        existing_prices = np.array([c['close'] for c in existing_candles])
        existing_returns = np.diff(np.log(existing_prices))
        
        # Align lengths
        min_len = min(len(new_returns), len(existing_returns))
        if min_len < 10:
            continue
        
        # Calculate Pearson correlation
        correlation = np.corrcoef(
            new_returns[-min_len:],
            existing_returns[-min_len:]
        )[0, 1]
        
        correlations[position.symbol] = correlation
        
        if abs(correlation) >= correlation_threshold:
            high_correlation_count += 1
    
    # Check if correlation limit exceeded
    if high_correlation_count >= max_correlated_positions:
        corr_str = ", ".join([f"{sym}: {corr:.2f}" for sym, corr in correlations.items()])
        rejection_reason = (
            f"Correlation limit exceeded: {high_correlation_count} positions "
            f"with correlation >= {correlation_threshold}. Correlations: {corr_str}"
        )
        return False, rejection_reason, correlations
    
    return True, "", correlations
```

**Benefits**:
- Prevents over-concentration in correlated assets
- Improves portfolio diversification
- Reduces systemic risk
- Provides clear rejection reasons


## Sequence Diagrams

### Signal Generation Flow (Optimized)

```
User/Scheduler          AsyncTradingSystem      AsyncCandleManager      SignalEngine        PortfolioManager      OrderExecutor
     |                         |                         |                      |                    |                    |
     |--run_once()------------>|                         |                      |                    |                    |
     |                         |                         |                      |                    |                    |
     |                         |--refresh_all()--------->|                      |                    |                    |
     |                         |  (batch symbols)        |                      |                    |                    |
     |                         |                         |--fetch in parallel-->|                    |                    |
     |                         |                         |  (5 symbols/batch)   |                    |                    |
     |                         |                         |<--candles cached-----|                    |                    |
     |                         |<--refresh complete------|                      |                    |                    |
     |                         |                         |                      |                    |                    |
     |                         |--analyze_all()--------->|                      |                    |                    |
     |                         |                         |                      |                    |                    |
     |                         |                         |<--get_candles()------|                    |                    |
     |                         |                         |  (from cache only)   |                    |                    |
     |                         |                         |--cached data-------->|                    |                    |
     |                         |                         |                      |                    |                    |
     |                         |                         |                      |--validate steps--->|                    |
     |                         |                         |                      |--apply confidence->|                    |
     |                         |                         |                      |--ML calibration--->|                    |
     |                         |                         |                      |                    |                    |
     |                         |<--signals[]-------------|                      |<--signal-----------|                    |
     |                         |                         |                      |                    |                    |
     |                         |--process_signal()-------|----------------------|------------------>|                    |
     |                         |                         |                      |                    |                    |
     |                         |                         |                      |                    |--check_position_limit()
     |                         |                         |                      |                    |--check_drawdown_limit()
     |                         |                         |                      |                    |--check_correlation()
     |                         |                         |                      |                    |--calculate_size()
     |                         |                         |                      |                    |                    |
     |                         |                         |                      |                    |--execute_entry()-->|
     |                         |                         |                      |                    |                    |
     |                         |                         |                      |                    |                    |--validate_min_size()
     |                         |                         |                      |                    |                    |--place_order()
     |                         |                         |                      |                    |                    |  (with retry)
     |                         |                         |                      |                    |<--order_id---------|
     |                         |                         |                      |                    |                    |
     |                         |<--execution_result------|----------------------|<--result-----------|                    |
     |<--signals processed-----|                         |                      |                    |                    |
```

### TP Placement Flow (Enhanced)

```
Main Loop              OrderExecutor           Exchange API          PositionManager       AdaptiveSLSystem
    |                       |                        |                      |                      |
    |--check_and_place_tps()->|                      |                      |                      |
    |  (every 10 seconds)   |                        |                      |                      |
    |                       |                        |                      |                      |
    |                       |--get_pending_tps()---->|                      |                      |
    |                       |<--pending_list---------|                      |                      |
    |                       |                        |                      |                      |
    |                       |--for each pending----->|                      |                      |
    |                       |                        |                      |                      |
    |                       |--check_entry_filled()-->|                      |                      |
    |                       |<--filled=True-----------|                      |                      |
    |                       |                        |                      |                      |
    |                       |--validate_min_size()--->|                      |                      |
    |                       |<--valid=True------------|                      |                      |
    |                       |                        |                      |                      |
    |                       |--place_tp1()----------->|                      |                      |
    |                       |  (50% quantity)        |                      |                      |
    |                       |<--tp1_order_id----------|                      |                      |
    |                       |                        |                      |                      |
    |                       |--place_tp2()----------->|                      |                      |
    |                       |  (50% quantity)        |                      |                      |
    |                       |<--tp2_order_id----------|                      |                      |
    |                       |                        |                      |                      |
    |                       |--update_tracking()----->|                      |                      |
    |                       |                        |                      |                      |
    |                       |--register_adaptive_sl()->|-------------------->|                      |
    |                       |                        |                      |                      |
    |<--tps_placed_count----|                        |                      |                      |
```

### Breakeven Move Flow (Validated)

```
Main Loop              AdaptiveSLSystem        PositionManager       OrderExecutor        Exchange API
    |                       |                        |                      |                      |
    |--update_positions()--->|                       |                      |                      |
    |  (every 5 seconds)    |                        |                      |                      |
    |                       |                        |                      |                      |
    |                       |--get_open_positions()->|                      |                      |
    |                       |<--positions[]----------|                      |                      |
    |                       |                        |                      |                      |
    |                       |--for each position---->|                      |                      |
    |                       |                        |                      |                      |
    |                       |--check_tp1_hit()------>|                      |                      |
    |                       |<--tp1_filled=True------|                      |                      |
    |                       |                        |                      |                      |
    |                       |--calculate_breakeven()->|                      |                      |
    |                       |  (entry + 0.1% buffer) |                      |                      |
    |                       |                        |                      |                      |
    |                       |--validate_direction()-->|                      |                      |
    |                       |  (LONG: new_sl > old_sl)|                     |                      |
    |                       |<--valid=True------------|                      |                      |
    |                       |                        |                      |                      |
    |                       |--update_sl()-----------|----------------------|-------------------->|
    |                       |                        |                      |                      |
    |                       |                        |                      |<--sl_updated---------|
    |                       |                        |                      |                      |
    |                       |--log_sl_move()-------->|                      |                      |
    |<--positions_updated----|                       |                      |                      |
```


## Configuration Changes

### Enhanced Feature Flags Configuration

**File**: `config/feature_flags.py`

**Changes**:
```python
# Add global feature boost cap
GLOBAL_FEATURE_BOOST_CAP = 50.0  # Maximum total boost from all features

# Add phase-specific caps
PHASE_1_BOOST_CAP = 25.0  # VSA, Wyckoff, Market Profile, Liquidity, Smart Money
PHASE_2_BOOST_CAP = 25.0  # MTF, Order Book, Institutional Flow, Seasonality

# Add ML calibration config
ML_CALIBRATION_CONFIG = {
    "enabled": True,
    "apply_as_final_step": True,  # Apply after all other adjustments
    "min_samples_for_training": 100,
    "retrain_interval_signals": 1000,
    "max_adjustment_pct": 20,  # Maximum adjustment from raw confidence
}

# Add circuit breaker config
CIRCUIT_BREAKER_CONFIG = {
    "enabled": True,
    "daily_drawdown_limit_pct": 3.0,  # Halt trading at 3% daily loss
    "max_consecutive_losses": 5,  # Halt after 5 consecutive losses
    "manual_reset_required": True,  # Require manual intervention to resume
    "cooldown_minutes": 60,  # Minimum time before reset allowed
}
```

### Enhanced Strategy Configuration

**File**: `config.py`

**Changes**:
```python
STRATEGY = {
    # ... existing config ...
    
    # Step 3.5: 5min Structure Shift (NEW - hard requirement)
    "require_5min_structure_shift": True,  # Reject signal if not confirmed
    "structure_shift_lookback": 20,  # Candles to analyze for shift
    
    # Risk Management (ENHANCED)
    "max_concurrent_positions": 5,  # Hard limit on open positions
    "position_size_method": "kelly",  # "fixed", "kelly", "volatility_adjusted"
    "kelly_fraction": 0.25,  # Quarter-Kelly for conservative sizing
    "min_position_size_usd": 10.0,  # Minimum position size
    "max_position_size_pct": 5.0,  # Max 5% of equity per position
    
    # TP/SL Validation (NEW)
    "min_tp_sl_ratio": 1.5,  # TP must be at least 1.5x SL distance
    "breakeven_buffer_pct": 0.1,  # Buffer for breakeven moves
    "trailing_stop_enabled": True,
    
    # Correlation Management (NEW)
    "correlation_check_enabled": True,
    "correlation_threshold": 0.8,  # High correlation threshold
    "max_correlated_positions": 3,  # Max positions with high correlation
    "correlation_lookback_days": 30,
    
    # Execution (ENHANCED)
    "order_retry_attempts": 3,  # Retry failed orders
    "order_retry_delay_seconds": [2, 4, 8],  # Exponential backoff
    "tp_placement_timeout_seconds": 10,  # Place TPs within 10s of fill
    "validate_exchange_minimums": True,
}
```

### Cache Configuration

**File**: `data/candle_manager_async.py`

**Changes**:
```python
CACHE_CONFIG = {
    "max_entries": 1000,  # Maximum cache entries before LRU eviction
    "ttl_seconds": 300,  # 5 minutes TTL
    "eviction_batch_pct": 0.2,  # Evict 20% of excess entries
    "enable_flexible_matching": True,  # Enable limit-flexible cache matching
    "log_cache_stats": True,  # Log hit/miss rates every 100 requests
}
```

### Database Configuration

**File**: `storage/database.py`

**Changes**:
```python
DATABASE_CONFIG = {
    "connection_pool_size": 5,  # Thread-local pool size
    "batch_insert_threshold": 10,  # Use batch insert when count >= 10
    "enable_wal_mode": True,  # Write-Ahead Logging for concurrency
    "checkpoint_interval_seconds": 300,  # WAL checkpoint every 5 minutes
    "vacuum_on_startup": False,  # Don't vacuum on startup (slow)
    "pragma_settings": {
        "journal_mode": "WAL",
        "synchronous": "NORMAL",
        "cache_size": -64000,  # 64MB cache
        "temp_store": "MEMORY",
    }
}
```

### Rate Limiting Configuration

**File**: `utils/async_rate_limiter.py`

**Changes**:
```python
RATE_LIMIT_CONFIG = {
    "bybit": {
        "requests_per_second": 10,
        "burst_size": 20,
        "backoff_multiplier": 2.0,
        "max_backoff_seconds": 60,
        "jitter_pct": 0.1,  # Add 10% random jitter
    },
    "binance": {
        "requests_per_second": 20,
        "burst_size": 40,
        "backoff_multiplier": 2.0,
        "max_backoff_seconds": 60,
        "jitter_pct": 0.1,
    },
    "batch_fetch_config": {
        "symbols_per_batch": 5,  # Fetch 5 symbols at a time
        "batch_delay_seconds": 1.0,  # 1 second delay between batches
    }
}
```


## Migration Strategy

### Phase 1: Foundation (Week 1-2)

**Goal**: Fix critical async/sync blocking issues and implement intelligent caching.

**Tasks**:
1. Refactor `SyncCandleManagerAdapter` to remove `loop.run_until_complete()` calls
2. Implement flexible cache key matching in `AsyncCandleManager`
3. Add LRU eviction policy to cache
4. Implement batch fetching with rate limiting
5. Add async context managers to exchange clients
6. Update `asyncio.gather()` calls to use `return_exceptions=True`

**Testing**:
- Property-based tests for cache matching algorithm
- Integration tests for async/sync boundary
- Load tests for parallel symbol processing
- Verify no event loop blocking under load

**Rollout**:
- Deploy to staging environment
- Run 24-hour soak test with 30 symbols
- Monitor cache hit rates (target: >80%)
- Monitor API rate limit compliance
- Gradual rollout to production (10% → 50% → 100%)

**Rollback Plan**:
- Keep old `SyncCandleManagerAdapter` as fallback
- Feature flag: `USE_ENHANCED_CACHE_MATCHING`
- Rollback if cache hit rate < 60% or event loop blocking detected

### Phase 2: Signal Engine Standardization (Week 3-4)

**Goal**: Implement deterministic confidence adjustment pipeline and validation.

**Tasks**:
1. Implement `SignalValidationResult` data model
2. Create deterministic confidence adjustment pipeline
3. Add Step 3.5 (5min structure shift) enforcement
4. Implement feature boost capping (25% per phase, 50% total)
5. Move ML calibration to final post-processing step
6. Add TP/SL distance validation

**Testing**:
- Unit tests for confidence adjustment pipeline
- Property-based tests for boost capping
- Integration tests for signal validation
- Regression tests against historical signals

**Rollout**:
- Deploy to staging with shadow mode (log results, don't reject)
- Compare shadow results with production for 7 days
- Analyze rejection reasons and adjust thresholds if needed
- Enable enforcement in production

**Rollback Plan**:
- Feature flag: `USE_STANDARDIZED_SIGNAL_VALIDATION`
- Keep old signal generation logic as fallback
- Rollback if signal count drops >50% or quality degrades

### Phase 3: Risk Management Enhancement (Week 5-6)

**Goal**: Implement comprehensive portfolio-level risk controls.

**Tasks**:
1. Implement `RiskCheckResult` data model
2. Add max concurrent positions enforcement
3. Implement daily drawdown circuit breaker
4. Add correlation-based position rejection
5. Implement Kelly Criterion with input validation
6. Add conservative fallback sizing

**Testing**:
- Unit tests for each risk check
- Property-based tests for Kelly Criterion
- Integration tests for portfolio manager
- Stress tests with extreme market conditions

**Rollout**:
- Deploy to staging with monitoring
- Run parallel risk checks (log only, don't enforce)
- Analyze rejection patterns for 7 days
- Gradually enable enforcement (position limit → drawdown → correlation)

**Rollback Plan**:
- Feature flags for each risk check
- Keep old risk management as fallback
- Rollback if false rejection rate >10%

### Phase 4: Execution Engine Improvements (Week 7-8)

**Goal**: Implement reliable TP/SL management with retry logic.

**Tasks**:
1. Implement `ExecutionTracking` data model
2. Add minimum order size validation
3. Implement retry logic with exponential backoff
4. Add pending TP tracking and placement
5. Implement breakeven moves with buffer
6. Add trailing stop direction validation
7. Implement partial fill handling

**Testing**:
- Unit tests for order executor
- Integration tests with mock exchange
- End-to-end tests with paper trading
- Chaos engineering tests (simulate API failures)

**Rollout**:
- Deploy to staging with paper trading
- Run for 14 days with real market data
- Monitor TP placement success rate (target: >95%)
- Monitor SL move accuracy
- Enable in production with monitoring

**Rollback Plan**:
- Feature flag: `USE_ENHANCED_EXECUTION_ENGINE`
- Keep old execution logic as fallback
- Rollback if TP placement success rate <90%

### Phase 5: Performance Optimization (Week 9-10)

**Goal**: Optimize database operations and monitoring.

**Tasks**:
1. Implement batch database operations
2. Add database write executor for non-blocking writes
3. Optimize query patterns with indexes
4. Implement cache statistics logging
5. Add performance metrics dashboard
6. Optimize memory usage

**Testing**:
- Performance benchmarks (before/after)
- Load tests with 50+ symbols
- Memory profiling
- Database query profiling

**Rollout**:
- Deploy optimizations incrementally
- Monitor performance metrics
- Verify no regression in functionality
- Full rollout after validation

**Rollback Plan**:
- Each optimization has individual feature flag
- Rollback if performance degrades or errors increase


## Testing Strategy

### Unit Tests

**Coverage Target**: 85%

**Key Areas**:
1. **Cache Matching Algorithm**
   - Test exact key matching
   - Test flexible limit matching
   - Test LRU eviction
   - Test cache statistics

2. **Confidence Adjustment Pipeline**
   - Test deterministic ordering
   - Test boost capping
   - Test ML calibration as final step
   - Test edge cases (negative boosts, extreme values)

3. **Risk Checks**
   - Test position limit enforcement
   - Test drawdown calculation
   - Test correlation calculation
   - Test Kelly Criterion with various inputs

4. **Order Execution**
   - Test minimum size validation
   - Test retry logic
   - Test TP placement timing
   - Test partial fill handling

### Property-Based Tests

**Using Hypothesis library**

**Key Properties**:
1. **Cache Invariants**
   ```python
   @given(
       symbol=st.text(min_size=3, max_size=10),
       timeframe=st.sampled_from(["1", "5", "15", "60", "240"]),
       limit=st.integers(min_value=10, max_value=500)
   )
   def test_cache_always_returns_requested_limit(symbol, timeframe, limit):
       """Cache should always return exactly 'limit' candles if available."""
       result = cache.get_candles(symbol, timeframe, limit)
       assert result is None or len(result) == limit
   ```

2. **Confidence Bounds**
   ```python
   @given(
       base_confidence=st.floats(min_value=0, max_value=100),
       boosts=st.lists(st.floats(min_value=-50, max_value=50), min_size=1, max_size=10)
   )
   def test_confidence_always_in_valid_range(base_confidence, boosts):
       """Final confidence must always be between 0 and 100."""
       final = apply_confidence_adjustments(base_confidence, boosts)
       assert 0 <= final <= 100
   ```

3. **Kelly Criterion Safety**
   ```python
   @given(
       equity=st.floats(min_value=100, max_value=1000000),
       win_rate=st.floats(min_value=0.01, max_value=0.99),
       avg_win=st.floats(min_value=0.01, max_value=1000),
       avg_loss=st.floats(min_value=0.01, max_value=1000)
   )
   def test_kelly_never_exceeds_equity(equity, win_rate, avg_win, avg_loss):
       """Kelly position size must never exceed total equity."""
       size = calculate_kelly_position_size(equity, win_rate, avg_win, avg_loss)
       assert 0 <= size <= equity
   ```

4. **SL Direction Validation**
   ```python
   @given(
       direction=st.sampled_from(["LONG", "SHORT"]),
       entry_price=st.floats(min_value=1, max_value=100000),
       old_sl=st.floats(min_value=1, max_value=100000),
       new_sl=st.floats(min_value=1, max_value=100000)
   )
   def test_sl_only_moves_favorably(direction, entry_price, old_sl, new_sl):
       """SL must only move in favorable direction."""
       is_valid = validate_sl_move(direction, entry_price, old_sl, new_sl)
       if direction == "LONG":
           assert is_valid == (new_sl >= old_sl)
       else:
           assert is_valid == (new_sl <= old_sl)
   ```

### Integration Tests

**Key Scenarios**:
1. **End-to-End Signal Generation**
   - Mock exchange data
   - Run full signal generation pipeline
   - Verify all validation steps
   - Check confidence adjustments
   - Validate risk checks
   - Verify execution tracking

2. **Async/Sync Boundary**
   - Start async event loop
   - Trigger signal generation
   - Verify no blocking calls
   - Check cache usage
   - Validate data consistency

3. **TP/SL Management**
   - Simulate entry fill
   - Verify TP placement within 10s
   - Simulate TP1 hit
   - Verify breakeven move
   - Simulate price movement
   - Verify trailing stop updates

4. **Circuit Breaker**
   - Simulate consecutive losses
   - Verify trading halt
   - Attempt new trade (should reject)
   - Simulate manual reset
   - Verify trading resumes

### Performance Tests

**Benchmarks**:
1. **Cache Performance**
   - Measure cache hit rate with various workloads
   - Measure lookup latency (target: <1ms)
   - Measure memory usage (target: <500MB for 1000 entries)

2. **Signal Generation Latency**
   - Measure end-to-end latency per symbol (target: <100ms)
   - Measure parallel processing speedup (target: 10x+ for 30 symbols)

3. **Database Performance**
   - Measure batch insert performance (target: >100 inserts/second)
   - Measure query latency (target: <10ms for simple queries)

4. **API Rate Limiting**
   - Verify rate limits are respected
   - Measure backoff behavior
   - Verify no IP bans under load

### Chaos Engineering Tests

**Failure Scenarios**:
1. **Exchange API Failures**
   - Simulate 500 errors
   - Simulate timeouts
   - Simulate rate limit errors
   - Verify retry logic
   - Verify graceful degradation

2. **Database Failures**
   - Simulate connection loss
   - Simulate write failures
   - Verify data consistency
   - Verify recovery

3. **Cache Failures**
   - Simulate cache corruption
   - Simulate memory pressure
   - Verify fallback to API
   - Verify system stability


## Monitoring and Observability

### Key Metrics to Track

**System Health**:
- Event loop lag (target: <10ms)
- Memory usage (target: <2GB for 30 symbols)
- CPU usage (target: <50% average)
- Cache hit rate (target: >80%)
- API rate limit compliance (target: 100%)

**Trading Performance**:
- Signal generation latency (target: <100ms per symbol)
- Signal quality distribution (A+, A, B, C counts)
- Signal rejection reasons (position limit, drawdown, correlation, etc.)
- Win rate by signal quality
- Average R:R ratio achieved

**Risk Metrics**:
- Current position count vs limit
- Daily drawdown percentage
- Portfolio correlation matrix
- Position sizing distribution
- Circuit breaker triggers

**Execution Metrics**:
- Order placement success rate (target: >95%)
- TP placement timing (target: <10s from fill)
- Breakeven move success rate
- Trailing stop update frequency
- Partial fill handling count

### Logging Strategy

**Log Levels**:
- **DEBUG**: Cache operations, detailed flow
- **INFO**: Signal generation, risk checks, order execution
- **WARNING**: Cache misses, validation failures, retry attempts
- **ERROR**: API failures, database errors, execution failures
- **CRITICAL**: Circuit breaker triggers, system halt

**Structured Logging**:
```python
log.info(
    "Signal generated",
    extra={
        "symbol": symbol,
        "signal_type": signal_type,
        "quality": quality,
        "confidence": confidence,
        "steps_confirmed": steps_confirmed,
        "rejection_reason": rejection_reason,
        "execution_time_ms": execution_time_ms
    }
)
```

**Log Aggregation**:
- Use structured JSON logs for easy parsing
- Aggregate logs to centralized system (e.g., ELK stack)
- Set up alerts for critical events
- Create dashboards for key metrics

### Alerting Rules

**Critical Alerts** (immediate notification):
- Circuit breaker triggered
- Event loop blocking detected (>100ms lag)
- API rate limit exceeded
- Database connection failure
- Memory usage >90%

**Warning Alerts** (notification within 15 minutes):
- Cache hit rate <60%
- Signal rejection rate >50%
- TP placement success rate <90%
- Daily drawdown >2%
- Consecutive losses >3

**Info Alerts** (daily summary):
- Signal count by quality
- Win rate by signal quality
- Average execution latency
- Cache statistics
- API usage statistics


## Risk Mitigation

### Identified Risks and Mitigation Strategies

**Risk 1: Event Loop Blocking**
- **Impact**: High - System becomes unresponsive, signals delayed
- **Probability**: Medium - Current code has blocking calls
- **Mitigation**:
  - Remove all `loop.run_until_complete()` from async contexts
  - Use cache-only operations in sync code
  - Add event loop lag monitoring
  - Set up alerts for lag >50ms
- **Contingency**: Automatic restart if lag >500ms for >10 seconds

**Risk 2: Cache Invalidation Issues**
- **Impact**: Medium - Stale data leads to incorrect signals
- **Probability**: Low - TTL mechanism prevents staleness
- **Mitigation**:
  - Implement TTL-based cache expiration (5 minutes)
  - Add cache freshness validation
  - Log cache age on every access
  - Implement cache warming on startup
- **Contingency**: Manual cache flush command available

**Risk 3: Over-Rejection of Valid Signals**
- **Impact**: High - Missed trading opportunities, reduced profitability
- **Probability**: Medium - New validation rules may be too strict
- **Mitigation**:
  - Shadow mode deployment (log rejections, don't enforce)
  - Analyze rejection patterns for 7 days
  - Adjust thresholds based on data
  - Gradual rollout with monitoring
- **Contingency**: Feature flags allow instant rollback

**Risk 4: Position Limit Deadlock**
- **Impact**: Medium - System stops trading even when positions close
- **Probability**: Low - Position tracking is reliable
- **Mitigation**:
  - Implement position cleanup on close
  - Add periodic position reconciliation
  - Log position count on every check
  - Manual position reset command
- **Contingency**: Admin interface for position management

**Risk 5: Database Write Failures**
- **Impact**: High - Loss of signal/execution history
- **Probability**: Low - SQLite is reliable
- **Mitigation**:
  - Implement write retry logic
  - Use WAL mode for concurrency
  - Add database health checks
  - Implement backup strategy
- **Contingency**: In-memory buffer for failed writes, retry on recovery

**Risk 6: API Rate Limit Violations**
- **Impact**: High - IP ban, system shutdown
- **Probability**: Medium - Parallel fetching increases risk
- **Mitigation**:
  - Implement batch fetching (5 symbols/batch)
  - Add delays between batches (1 second)
  - Use exponential backoff on errors
  - Monitor rate limit headers
- **Contingency**: Automatic backoff, manual rate limit override

**Risk 7: Correlation Calculation Errors**
- **Impact**: Medium - Incorrect position rejection
- **Probability**: Low - Numpy correlation is reliable
- **Mitigation**:
  - Validate input data (no NaN, sufficient length)
  - Handle edge cases (identical prices, zero variance)
  - Log correlation values on every check
  - Allow manual correlation override
- **Contingency**: Disable correlation check via feature flag

**Risk 8: Kelly Criterion Instability**
- **Impact**: Medium - Extreme position sizes
- **Probability**: Medium - Kelly is sensitive to inputs
- **Mitigation**:
  - Use quarter-Kelly (0.25 fraction)
  - Implement input validation
  - Cap maximum position size (5% equity)
  - Use conservative fallback (0.5%) on errors
- **Contingency**: Switch to fixed sizing via config


## Performance Benchmarks

### Baseline Performance (Current System)

**Signal Generation**:
- Single symbol analysis: ~150ms
- 30 symbols sequential: ~4500ms (4.5 seconds)
- 30 symbols parallel: ~300ms (with current async implementation)

**Data Fetching**:
- Single symbol candle fetch: ~200ms
- 30 symbols sequential: ~6000ms (6 seconds)
- 30 symbols parallel: ~2500ms (2.5 seconds, current)

**Cache Performance**:
- Cache hit rate: ~40% (exact key matching only)
- Cache lookup latency: <1ms
- Memory usage: ~300MB for 500 entries

**Database Performance**:
- Single insert: ~5ms
- Batch insert (10 records): ~15ms
- Query latency: ~3ms average

### Target Performance (Optimized System)

**Signal Generation**:
- Single symbol analysis: <100ms (33% improvement)
- 30 symbols parallel: <200ms (33% improvement)
- Throughput: >150 symbols/second

**Data Fetching**:
- 30 symbols parallel: <2000ms (20% improvement)
- Cache hit rate: >80% (2x improvement)
- API calls reduced by 70%

**Cache Performance**:
- Cache hit rate: >80% (flexible matching)
- Cache lookup latency: <1ms (maintained)
- Memory usage: <500MB for 1000 entries (LRU eviction)

**Database Performance**:
- Batch insert (10 records): <10ms (33% improvement)
- Query latency: <2ms average (33% improvement)
- Write throughput: >200 inserts/second

**Risk Check Performance**:
- Position limit check: <1ms
- Drawdown check: <5ms
- Correlation check: <50ms (30-day lookback)
- Total risk check overhead: <60ms per signal

**Execution Performance**:
- Order placement: <500ms (including retry)
- TP placement after fill: <10 seconds (guaranteed)
- Breakeven move: <5 seconds after TP1 hit
- Trailing stop update: <5 seconds per check

### Performance Validation

**Load Testing**:
- Test with 50 symbols (1.67x normal load)
- Test with 100 symbols (3.33x normal load)
- Verify linear scaling
- Identify bottlenecks

**Stress Testing**:
- Simulate high volatility (100+ signals/hour)
- Simulate API failures (50% error rate)
- Simulate database contention
- Verify graceful degradation

**Endurance Testing**:
- Run for 7 days continuous
- Monitor memory leaks
- Monitor cache growth
- Monitor database size growth
- Verify no performance degradation


## Security Considerations

### API Key Management

**Current Issues**:
- API keys stored in plaintext in config.json
- Keys loaded from environment variables without validation
- No key rotation mechanism

**Improvements**:
1. **Encryption at Rest**
   - Encrypt config.json using system keyring
   - Use environment-specific encryption keys
   - Implement key derivation function (KDF)

2. **Key Validation**
   - Validate API key format on load
   - Test API connectivity on startup
   - Rotate keys on schedule (every 90 days)

3. **Access Control**
   - Restrict file permissions (600 for config.json)
   - Use separate keys for demo/live environments
   - Implement key revocation mechanism

### Data Protection

**Sensitive Data**:
- API keys and secrets
- Position sizes and equity
- Trade history and PnL
- Database credentials

**Protection Measures**:
1. **Encryption**
   - Encrypt database at rest (SQLCipher)
   - Use TLS for all API communications
   - Encrypt logs containing sensitive data

2. **Access Control**
   - Implement role-based access control (RBAC)
   - Audit all access to sensitive data
   - Implement session management

3. **Data Retention**
   - Purge old logs after 90 days
   - Archive trade history after 1 year
   - Implement secure deletion

### Network Security

**API Communication**:
1. **TLS/SSL**
   - Enforce TLS 1.2+ for all connections
   - Validate SSL certificates
   - Implement certificate pinning

2. **Rate Limiting**
   - Implement client-side rate limiting
   - Respect exchange rate limits
   - Add exponential backoff

3. **IP Whitelisting**
   - Configure exchange IP whitelists
   - Use static IPs for production
   - Monitor for unauthorized access

### Input Validation

**User Inputs**:
- Symbol names (prevent injection)
- Configuration values (type validation)
- API parameters (range validation)

**Validation Rules**:
1. **Symbol Validation**
   - Whitelist allowed characters (A-Z, 0-9, -)
   - Maximum length (20 characters)
   - Format validation (e.g., BTC-USDT)

2. **Numeric Validation**
   - Range checks (min/max values)
   - Type validation (int, float)
   - Precision validation

3. **Configuration Validation**
   - Schema validation (Pydantic)
   - Required field checks
   - Dependency validation

### Audit Logging

**Events to Log**:
- API key usage
- Configuration changes
- Position opens/closes
- Risk limit violations
- System errors

**Log Format**:
```python
{
    "timestamp": "2026-03-17T10:30:00Z",
    "event_type": "POSITION_OPENED",
    "user": "system",
    "symbol": "BTC-USDT",
    "direction": "LONG",
    "size": 0.1,
    "entry_price": 50000.0,
    "ip_address": "192.168.1.100",
    "session_id": "abc123"
}
```

**Log Security**:
- Tamper-proof logging (append-only)
- Log integrity verification (checksums)
- Secure log storage (encrypted)
- Log retention policy (90 days)


## Deployment Strategy

### Environment Setup

**Development Environment**:
- Local machine with mock exchange APIs
- SQLite database for testing
- Feature flags enabled for all features
- Verbose logging (DEBUG level)
- No rate limiting

**Staging Environment**:
- Cloud server (AWS/GCP/Azure)
- Paper trading mode with real exchange APIs
- PostgreSQL database (optional)
- Feature flags match production
- INFO level logging
- Rate limiting enabled

**Production Environment**:
- High-availability cloud setup
- Live trading mode with real funds
- PostgreSQL with replication
- Feature flags for gradual rollout
- WARNING level logging (INFO for critical paths)
- Strict rate limiting

### Deployment Process

**Pre-Deployment Checklist**:
- [ ] All tests passing (unit, integration, property-based)
- [ ] Performance benchmarks met
- [ ] Security audit completed
- [ ] Database migrations tested
- [ ] Rollback plan documented
- [ ] Monitoring dashboards configured
- [ ] Alert rules configured
- [ ] Documentation updated

**Deployment Steps**:
1. **Backup**
   - Backup production database
   - Backup configuration files
   - Tag current production version in git

2. **Database Migration**
   - Run migrations on staging first
   - Verify data integrity
   - Run migrations on production
   - Verify no data loss

3. **Code Deployment**
   - Deploy to staging
   - Run smoke tests
   - Deploy to production (blue-green deployment)
   - Monitor for errors

4. **Feature Rollout**
   - Enable features gradually (10% → 50% → 100%)
   - Monitor key metrics at each stage
   - Rollback if metrics degrade

5. **Verification**
   - Verify all systems operational
   - Check signal generation
   - Verify order execution
   - Monitor for 24 hours

**Post-Deployment**:
- Monitor error rates
- Check performance metrics
- Review logs for warnings
- Collect user feedback
- Document lessons learned

### Rollback Procedures

**Immediate Rollback Triggers**:
- Event loop blocking detected
- Signal generation failure rate >10%
- Order execution failure rate >20%
- Database corruption detected
- Memory leak detected (>5GB usage)

**Rollback Steps**:
1. **Stop Trading**
   - Trigger circuit breaker
   - Cancel all pending orders
   - Close all positions (optional, based on severity)

2. **Revert Code**
   - Switch to previous version (blue-green)
   - Restart services
   - Verify system operational

3. **Revert Database** (if needed)
   - Restore from backup
   - Verify data integrity
   - Replay missed transactions (if possible)

4. **Verify Rollback**
   - Run smoke tests
   - Verify signal generation
   - Verify order execution
   - Monitor for 1 hour

5. **Post-Mortem**
   - Analyze root cause
   - Document failure
   - Update rollback procedures
   - Plan fix and re-deployment

### Continuous Deployment

**CI/CD Pipeline**:
1. **Commit** → Trigger pipeline
2. **Build** → Compile and package
3. **Test** → Run all tests
4. **Security Scan** → Check for vulnerabilities
5. **Deploy to Staging** → Automatic deployment
6. **Integration Tests** → Run on staging
7. **Manual Approval** → Required for production
8. **Deploy to Production** → Blue-green deployment
9. **Smoke Tests** → Verify deployment
10. **Monitor** → Watch metrics for 24 hours

**Automated Rollback**:
- Monitor key metrics (error rate, latency, memory)
- Automatic rollback if metrics exceed thresholds
- Alert team on automatic rollback
- Require manual approval to re-deploy


## Documentation Requirements

### Code Documentation

**Module-Level Documentation**:
- Purpose and responsibilities
- Key classes and functions
- Dependencies and interactions
- Usage examples
- Performance characteristics

**Class Documentation**:
- Purpose and use cases
- Constructor parameters
- Public methods and properties
- Thread safety guarantees
- Example usage

**Function Documentation**:
- Purpose and behavior
- Parameters (types, constraints, defaults)
- Return values (types, possible values)
- Exceptions raised
- Side effects
- Time complexity (for critical paths)

**Example**:
```python
class AsyncCandleManager:
    """
    Intelligent caching layer for candle data with flexible limit matching.
    
    This manager provides async access to candle data from multiple exchanges
    with intelligent caching to minimize API calls. It supports flexible cache
    key matching, allowing requests with different limits to reuse cached data.
    
    Thread Safety: This class is NOT thread-safe. Use separate instances per
    event loop or protect access with locks.
    
    Performance: Cache lookups are O(n) where n is the number of cache entries.
    For typical usage (1000 entries), lookup time is <1ms.
    
    Example:
        >>> manager = AsyncCandleManager(bybit_client, binance_client, db)
        >>> candles = await manager.get_candles("BTC-USDT", "60", limit=100)
        >>> print(f"Fetched {len(candles)} candles")
    """
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        exchange: str = "cross"
    ) -> List[Dict]:
        """
        Get candles with intelligent cache matching.
        
        This method first checks for an exact cache match, then falls back to
        flexible matching (finding cached data with limit >= requested). If no
        cache hit, fetches from exchange and caches the result.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC-USDT")
            timeframe: Candle timeframe in minutes ("1", "5", "60", "240")
            limit: Number of candles to return (default: 100)
            exchange: Exchange to fetch from ("bybit", "binance", "cross")
        
        Returns:
            List of candle dictionaries with keys: open, high, low, close,
            volume, timestamp. Returns empty list on error.
        
        Raises:
            ValueError: If symbol or timeframe format is invalid
            
        Performance: O(n) cache lookup where n is cache size. Typical: <1ms.
        """
```

### API Documentation

**REST API Endpoints**:
- Endpoint URL and method
- Authentication requirements
- Request parameters
- Response format
- Error codes
- Rate limits
- Example requests/responses

**WebSocket Endpoints**:
- Connection URL
- Authentication flow
- Message formats
- Subscription management
- Heartbeat requirements
- Reconnection strategy

### Configuration Documentation

**Configuration Files**:
- File location and format
- All configuration keys
- Value types and constraints
- Default values
- Environment variable overrides
- Examples for common scenarios

**Feature Flags**:
- Flag name and purpose
- Impact on system behavior
- Dependencies on other flags
- Rollout strategy
- Deprecation timeline

### Operational Documentation

**Runbooks**:
- System startup procedures
- Shutdown procedures
- Backup and restore procedures
- Monitoring and alerting setup
- Troubleshooting guides
- Emergency procedures

**Troubleshooting Guides**:
- Common issues and solutions
- Log analysis techniques
- Performance debugging
- Database maintenance
- API connectivity issues

### Architecture Documentation

**System Architecture**:
- High-level component diagram
- Data flow diagrams
- Sequence diagrams for key flows
- Technology stack
- Scalability considerations

**Design Decisions**:
- Why async/sync duality pattern
- Why TTL-based caching
- Why Kelly Criterion for sizing
- Why correlation-based rejection
- Trade-offs and alternatives considered


## Success Criteria

### Functional Requirements

**Signal Generation**:
- ✅ All 4 ICT steps use consistent data sources
- ✅ Step 3.5 (5min structure shift) enforced as hard requirement
- ✅ Confidence adjustments applied in deterministic order
- ✅ Feature boosts capped at 50% total
- ✅ ML calibration applied as final post-processing step only
- ✅ TP/SL distance validation before signal approval

**Risk Management**:
- ✅ Max concurrent positions enforced before sizing
- ✅ Daily drawdown circuit breaker functional
- ✅ Correlation-based position rejection working
- ✅ Kelly Criterion with input validation
- ✅ Conservative fallback sizing on errors
- ✅ Breakeven moves with 0.1% buffer
- ✅ Trailing stops only move favorably

**Execution**:
- ✅ Minimum order size validation before placement
- ✅ Retry logic with exponential backoff (3 attempts)
- ✅ TP placement within 10 seconds of fill
- ✅ Partial fill handling with TP quantity adjustment
- ✅ Position cleanup on close

**Data Layer**:
- ✅ Flexible cache key matching implemented
- ✅ LRU eviction when cache exceeds 1000 entries
- ✅ Batch fetching with 5 symbols per batch
- ✅ Rate limiting with exponential backoff
- ✅ Cross-exchange price validation (>2% mismatch excluded)

### Performance Requirements

**Latency**:
- ✅ Signal generation: <100ms per symbol
- ✅ Cache lookup: <1ms
- ✅ Risk checks: <60ms total
- ✅ Order placement: <500ms (including retry)
- ✅ Event loop lag: <10ms average

**Throughput**:
- ✅ Signal processing: >150 symbols/second
- ✅ Database writes: >200 inserts/second
- ✅ API requests: Respect exchange limits (no bans)

**Resource Usage**:
- ✅ Memory: <2GB for 30 symbols
- ✅ CPU: <50% average
- ✅ Cache size: <500MB for 1000 entries

**Reliability**:
- ✅ Cache hit rate: >80%
- ✅ Order placement success: >95%
- ✅ TP placement success: >95%
- ✅ System uptime: >99.9%

### Quality Requirements

**Code Quality**:
- ✅ Test coverage: >85%
- ✅ No critical security vulnerabilities
- ✅ No event loop blocking
- ✅ All async resources properly cleaned up
- ✅ Comprehensive error handling

**Documentation**:
- ✅ All public APIs documented
- ✅ Architecture diagrams created
- ✅ Runbooks for operations
- ✅ Troubleshooting guides
- ✅ Configuration examples

**Monitoring**:
- ✅ Key metrics tracked and visualized
- ✅ Alerts configured for critical events
- ✅ Structured logging implemented
- ✅ Performance dashboards created

### Business Requirements

**Trading Performance**:
- ✅ Signal quality maintained or improved
- ✅ Win rate by quality grade tracked
- ✅ Risk-adjusted returns improved
- ✅ Maximum drawdown reduced
- ✅ Sharpe ratio improved

**Operational Efficiency**:
- ✅ API costs reduced by 70%
- ✅ System maintenance time reduced
- ✅ Deployment time reduced
- ✅ Incident response time reduced

**Risk Management**:
- ✅ No position limit violations
- ✅ No drawdown limit violations
- ✅ No correlation limit violations
- ✅ No API rate limit violations
- ✅ No uncontrolled losses

## Acceptance Testing

### Test Scenarios

**Scenario 1: Normal Operation**
- System processes 30 symbols every 5 minutes
- Generates 2-5 signals per hour
- All signals pass validation
- All orders execute successfully
- No errors or warnings

**Scenario 2: High Volatility**
- System processes 30 symbols during high volatility
- Generates 10+ signals per hour
- Position limit enforced correctly
- Correlation checks prevent over-concentration
- Circuit breaker triggers if drawdown exceeds 3%

**Scenario 3: API Failures**
- Exchange API returns 500 errors
- System retries with exponential backoff
- Falls back to cached data
- Continues operating with degraded functionality
- Recovers automatically when API restored

**Scenario 4: Cache Miss**
- Signal engine requests uncached data
- Adapter returns empty list with warning
- Signal generation skipped for that symbol
- Background task fetches data for next cycle
- No event loop blocking

**Scenario 5: Position Limit Reached**
- System has 5 open positions (limit)
- New signal generated
- Position limit check rejects signal
- Clear rejection reason logged
- System continues monitoring

**Scenario 6: Circuit Breaker**
- Daily drawdown reaches 3%
- Circuit breaker triggers
- All trading halted
- Manual reset required
- System resumes after reset

### Acceptance Criteria

**Phase 1 (Foundation)**:
- ✅ No event loop blocking detected in 24-hour test
- ✅ Cache hit rate >80% after warm-up
- ✅ API rate limits respected (zero violations)
- ✅ All async resources properly cleaned up

**Phase 2 (Signal Engine)**:
- ✅ Signal validation pipeline produces consistent results
- ✅ Feature boost capping prevents over-confidence
- ✅ ML calibration applied correctly as final step
- ✅ Signal rejection rate <30% (not too strict)

**Phase 3 (Risk Management)**:
- ✅ Position limit enforced 100% of time
- ✅ Drawdown circuit breaker triggers correctly
- ✅ Correlation checks prevent over-concentration
- ✅ Kelly Criterion produces reasonable sizes

**Phase 4 (Execution)**:
- ✅ TP placement success rate >95%
- ✅ Breakeven moves execute within 5 seconds
- ✅ Trailing stops only move favorably
- ✅ Partial fills handled correctly

**Phase 5 (Performance)**:
- ✅ Signal generation latency <100ms per symbol
- ✅ Memory usage <2GB for 30 symbols
- ✅ CPU usage <50% average
- ✅ System uptime >99.9% over 30 days

## Conclusion

This design document provides a comprehensive blueprint for optimizing the OpenClaw trading system. The proposed changes address all critical gaps identified in the requirements document while maintaining backward compatibility and minimizing disruption to live trading.

The phased migration strategy ensures safe, gradual rollout with clear rollback procedures at each stage. Comprehensive testing, monitoring, and documentation ensure the system operates reliably at institutional grade.

Key improvements include:
- **Reliability**: Elimination of async/sync blocking issues
- **Consistency**: Standardized signal generation with deterministic confidence adjustments
- **Safety**: Comprehensive risk controls at all levels
- **Performance**: Optimized data fetching and caching (70% API cost reduction)
- **Maintainability**: Clear architecture with well-documented interfaces

Upon completion of all phases, the OpenClaw system will be production-ready for institutional-grade cryptocurrency trading with maximum analytical effectiveness and profitability.

