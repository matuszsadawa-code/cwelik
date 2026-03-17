# API Services

Business logic services for the OpenClaw Trading Dashboard API.

## Overview

Services encapsulate business logic and handle data fetching, processing, and broadcasting. They run as background tasks and communicate with WebSocket clients for real-time updates.

## Available Services

### 1. WebSocket Manager (`websocket_manager.py`)

Manages WebSocket connections and message broadcasting.

**Features:**
- Connection lifecycle management (accept, track, disconnect)
- Channel-based subscriptions (market_data, signals, positions, performance)
- Heartbeat mechanism (ping every 30s, timeout after 60s)
- Broadcast to all clients or specific channels
- Connection status tracking

**Usage:**
```python
from api.services.websocket_manager import ConnectionManager

manager = ConnectionManager()

# Accept new connection
await manager.connect(websocket)

# Subscribe to channels
await manager.subscribe(websocket, ["market_data", "signals"])

# Broadcast to all clients
await manager.broadcast({"type": "update", "data": {...}})

# Broadcast to specific channel
await manager.broadcast({"type": "market_data_update", "data": {...}}, channel="market_data")

# Disconnect client
manager.disconnect(websocket)
```

---

### 2. Market Data Service (`market_data_service.py`)

Fetches real-time market data from exchanges and broadcasts updates via WebSocket.

**Features:**
- **Ticker Updates**: Fetches price, volume, 24h change every 1 second
- **Trade Flow Updates**: Fetches recent trades every 2 seconds for CVD calculation
- **CVD Calculation**: Cumulative Volume Delta (buy volume - sell volume)
- **Multi-Exchange Support**: Binance and Bybit with automatic fallback
- **Circuit Breaker**: Skips symbols after 5 consecutive errors
- **Error Recovery**: Resets error counts every 5 minutes
- **Parallel Fetching**: Async parallel requests for all symbols

**Architecture:**
```
MarketDataService
├── _ticker_update_loop (1s interval)
│   ├── _fetch_bybit_ticker (parallel)
│   └── _fetch_binance_ticker (parallel)
├── _trade_flow_update_loop (2s interval)
│   ├── _fetch_bybit_trades (parallel)
│   ├── _fetch_binance_trades (parallel)
│   └── _calculate_cvd_delta
└── _error_reset_loop (5min interval)
```

**Usage:**
```python
from api.services.market_data_service import MarketDataService
from api.services.websocket_manager import ConnectionManager

# Initialize
connection_manager = ConnectionManager()
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
service = MarketDataService(connection_manager, symbols=symbols)

# Start background tasks
await service.start()

# Get cached market data
data = service.get_market_data("BTCUSDT")
# Returns: {
#   "symbol": "BTCUSDT",
#   "price": 45000.0,
#   "volume24h": 1000000.0,
#   "change24h": 2.5,
#   "bid": 44999.5,
#   "ask": 45000.5,
#   "bidAskSpread": 1.0,
#   "cvd": 1234.5678,
#   "exchange": "bybit",
#   "timestamp": 1704110400000
# }

# Get all market data
all_data = service.get_all_market_data()

# Get CVD for a symbol
cvd = service.get_cvd("BTCUSDT")

# Reset CVD for a symbol
service.reset_cvd("BTCUSDT")

# Get service status
status = service.get_service_status()
# Returns: {
#   "running": True,
#   "symbols_monitored": 3,
#   "symbols_with_data": 3,
#   "symbols_with_errors": 0,
#   "total_errors": 0,
#   "cvd_tracked_symbols": 3
# }

# Stop service
await service.stop()
```

**WebSocket Broadcast:**
Broadcasts `market_data_update` messages to clients subscribed to the `market_data` channel:

```json
{
  "type": "market_data_update",
  "data": {
    "symbol": "BTCUSDT",
    "price": 45000.0,
    "volume24h": 1000000.0,
    "change24h": 2.5,
    "bidAskSpread": 1.0,
    "cvd": 1234.5678,
    "timestamp": 1704110400000
  }
}
```

**Error Handling:**
- **Circuit Breaker**: After 5 consecutive errors for a symbol, it's temporarily skipped
- **Automatic Recovery**: Error counts reset every 5 minutes to allow retry
- **Graceful Degradation**: If one exchange fails, falls back to the other
- **Logging**: Debug-level logs for individual fetch failures, warning for circuit breaker activation

**Performance:**
- Fetches data for 30 symbols in ~2-3 seconds (parallel async)
- Sub-100ms latency from exchange data to WebSocket broadcast
- Minimal memory footprint with efficient caching

---

### 3. Market Regime Service (`market_regime_service.py`)

Calculates market regime and broadcasts updates via WebSocket.

**Features:**
- **Regime Detection**: TRENDING, RANGING, VOLATILE, QUIET
- **Confidence Scoring**: 0-100% confidence in regime classification
- **Volatility Percentile**: Current volatility vs 30-day historical
- **Trend Strength**: ADX-based trend strength indicator
- **Periodic Updates**: Calculates regime every 60 seconds
- **Multi-Symbol Support**: Tracks regime for all monitored symbols

**Usage:**
```python
from api.services.market_regime_service import MarketRegimeService
from api.services.websocket_manager import ConnectionManager

# Initialize
connection_manager = ConnectionManager()
symbols = ["BTCUSDT", "ETHUSDT"]
service = MarketRegimeService(connection_manager, symbols=symbols)

# Start background task
await service.start()

# Get cached regime data
regime = service.get_regime("BTCUSDT")
# Returns: {
#   "symbol": "BTCUSDT",
#   "regime": "TRENDING",
#   "confidence": 85.5,
#   "volatility_percentile": 65.0,
#   "trend_strength": 45.2,
#   "timestamp": 1704110400000
# }

# Get all regime data
all_regimes = service.get_all_regimes()

# Get service status
status = service.get_service_status()

# Stop service
await service.stop()
```

**WebSocket Broadcast:**
Broadcasts `regime_update` messages to clients subscribed to the `market_data` channel:

```json
{
  "type": "regime_update",
  "data": {
    "symbol": "BTCUSDT",
    "regime": "TRENDING",
    "confidence": 85.5,
    "volatility_percentile": 65.0,
    "trend_strength": 45.2,
    "timestamp": 1704110400000
  }
}
```

---

### 4. Liquidity Zones Service (`liquidity_zones_service.py`)

Identifies and analyzes liquidity zones from order book imbalances and historical volume profile.

**Features:**
- **Order Book Analysis**: Identifies liquidity concentration from order book walls and large resting orders
- **Volume Profile Analysis**: Identifies high-volume price levels (POC, VAH, VAL)
- **Support/Resistance Classification**: Classifies zones based on price position
- **Strength Rating**: Assigns high/medium/low strength based on liquidity amount
- **Multi-Exchange Support**: Merges order book data from Binance and Bybit
- **Zone Deduplication**: Merges zones within 0.5% of each other
- **Periodic Updates**: Updates zones every 5 minutes
- **On-Demand Calculation**: Calculates zones on-demand if not cached

**Architecture:**
```
LiquidityZonesService
├── _zones_update_loop (5min interval)
│   └── _update_all_zones (parallel for all symbols)
│       ├── _fetch_orderbook (Bybit + Binance)
│       ├── _identify_orderbook_zones
│       ├── _identify_volume_profile_zones
│       └── _merge_zones
└── get_liquidity_zones (on-demand)
```

**Usage:**
```python
from api.services.liquidity_zones_service import LiquidityZonesService
from data.candle_manager_async import AsyncCandleManager

# Initialize
candle_manager = AsyncCandleManager()
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
service = LiquidityZonesService(candle_manager, symbols=symbols)

# Start background task
await service.start()

# Get liquidity zones for a symbol
zones = await service.get_liquidity_zones("BTCUSDT")
# Returns: [
#   {
#     "symbol": "BTCUSDT",
#     "priceLevel": 45000.0,
#     "priceRangeLow": 44910.0,
#     "priceRangeHigh": 45090.0,
#     "type": "support",
#     "strength": "high",
#     "liquidityAmount": 1234.5678,
#     "source": "combined",
#     "isNearPrice": True,
#     "label": "POC",
#     "timestamp": 1704110400000
#   },
#   ...
# ]

# Get service status
status = service.get_service_status()
# Returns: {
#   "running": True,
#   "symbols_monitored": 3,
#   "symbols_with_zones": 3,
#   "total_zones": 45
# }

# Stop service
await service.stop()
```

**Zone Structure:**

Each zone contains:
- `symbol`: Trading pair symbol
- `priceLevel`: Central price level of the zone
- `priceRangeLow`: Lower bound of zone (±0.2% from price level)
- `priceRangeHigh`: Upper bound of zone (±0.2% from price level)
- `type`: "support" (below price) or "resistance" (above price)
- `strength`: "high", "medium", or "low" based on liquidity amount
- `liquidityAmount`: Estimated liquidity at this level
- `source`: "orderbook", "volume_profile", or "combined"
- `isNearPrice`: True if zone is within 0.5% of current price
- `label`: Optional label (e.g., "POC", "VAH", "VAL")
- `timestamp`: Unix timestamp in milliseconds

**Zone Identification Logic:**

**Order Book Zones:**
- Identifies price levels with order size ≥ 3x average
- Creates zones with ±0.2% range around price level
- Strength based on size relative to average (5x = high, 3x = medium, <3x = low)

**Volume Profile Zones:**
- POC (Point of Control): Highest volume price level (high strength)
- VAH (Value Area High): Upper bound of 70% volume area (medium strength)
- VAL (Value Area Low): Lower bound of 70% volume area (medium strength)
- Other significant levels: Volume ≥ 2x average (strength based on volume percentile)

**Zone Merging:**
- Zones within 0.5% of each other are merged
- Keeps zone with highest liquidity amount
- Upgrades strength if confirmed by multiple sources (orderbook + volume profile)
- Limits output to top 20 zones by liquidity amount

**REST API Endpoint:**
```
GET /api/market/{symbol}/liquidity-zones
```

Returns liquidity zones for the specified symbol.

**Performance:**
- Updates all symbols in parallel every 5 minutes
- Fetches order book from both exchanges simultaneously
- Caches zones for fast retrieval
- On-demand calculation if zones not cached

**Error Handling:**
- Graceful degradation if one exchange fails
- Continues processing other symbols on error
- Debug-level logging for individual fetch failures

---

### 5. Performance Metrics Service (`performance_metrics_service.py`)

Calculates comprehensive performance metrics and broadcasts updates via WebSocket.

**Features:**
- **Win Rate**: Percentage of winning trades
- **Profit Factor**: Ratio of gross profit to gross loss
- **Sharpe Ratio**: Risk-adjusted return metric (annualized)
- **Drawdown Tracking**: Current and maximum drawdown
- **P&L Aggregation**: Daily, weekly, monthly P&L
- **Position Tracking**: Total trades and active positions count
- **Periodic Updates**: Calculates metrics every 30 seconds
- **In-Memory Caching**: Fast retrieval of cached metrics

**Usage:**
```python
from api.services.performance_metrics_service import PerformanceMetricsService
from api.services.websocket_manager import ConnectionManager

# Initialize
connection_manager = ConnectionManager()
service = PerformanceMetricsService(connection_manager)

# Start background task
await service.start()

# Get cached metrics
metrics = service.get_cached_metrics()
# Returns: {
#   "winRate": 58.5,
#   "profitFactor": 1.85,
#   "sharpeRatio": 1.42,
#   "maxDrawdown": -12.5,
#   "currentDrawdown": -3.2,
#   "dailyPnL": 2.5,
#   "weeklyPnL": 8.3,
#   "monthlyPnL": 15.7,
#   "totalTrades": 127,
#   "activePositions": 3,
#   "timestamp": 1704067200000
# }

# Get service status
status = service.get_service_status()

# Stop service
await service.stop()
```

**WebSocket Broadcast:**
Broadcasts `performance_update` messages to clients subscribed to the `performance` channel every 30 seconds.

---

### 6. Equity Curve Service (`equity_curve_service.py`)

Generates equity curves from historical snapshots and identifies significant drawdown periods.

**Features:**
- **Equity Curve Generation**: Query and format equity snapshots
- **Drawdown Detection**: Identify periods exceeding 5% threshold
- **Peak Tracking**: Calculate all-time and current equity peaks
- **Time Range Filtering**: Support 1d, 7d, 30d, 90d, 1y, all
- **TradingView Format**: Output formatted for Lightweight Charts
- **Drawdown Analysis**: Calculate depth, duration, peak, and trough

**Usage:**
```python
from api.services.equity_curve_service import EquityCurveService

# Initialize
service = EquityCurveService()

# Get equity curve with drawdown analysis
data = service.get_equity_curve(time_range="30d")
# Returns: {
#   "timestamps": [1704067200000, ...],
#   "equityValues": [10000.0, 10250.5, ...],
#   "drawdownPeriods": [
#     {
#       "startDate": 1704067200000,
#       "endDate": 1704153600000,
#       "depth": -8.5,
#       "duration": 1440,
#       "peakEquity": 10500.0,
#       "troughEquity": 9607.5
#     }
#   ],
#   "peakEquity": 10500.0,
#   "currentEquity": 10250.5,
#   "maxDrawdown": -8.5,
#   "maxDrawdownDuration": 1440
# }

# Get service status
status = service.get_service_status()
```

**REST API Endpoint:**
```
GET /api/analytics/equity-curve?time_range=30d
```

**Drawdown Detection Algorithm:**
- Tracks running peak equity
- Identifies drops >5% from peak
- Records start, end, depth, duration
- Handles ongoing drawdowns at data end

See [README_EQUITY_CURVE.md](./README_EQUITY_CURVE.md) for detailed documentation.

---

## Service Lifecycle

All services follow a consistent lifecycle pattern:

1. **Initialization**: Create service instance with dependencies
2. **Start**: Call `await service.start()` to begin background tasks
3. **Running**: Service runs background loops and broadcasts updates
4. **Stop**: Call `await service.stop()` to gracefully shutdown

**Example:**
```python
# Initialize services
market_data_service = MarketDataService(connection_manager, symbols)
market_regime_service = MarketRegimeService(connection_manager, symbols)
liquidity_zones_service = LiquidityZonesService(candle_manager, symbols)

# Start all services
await market_data_service.start()
await market_regime_service.start()
await liquidity_zones_service.start()

# Services run in background...

# Graceful shutdown
await market_data_service.stop()
await market_regime_service.stop()
await liquidity_zones_service.stop()
```

---

## Integration with Main Application

Services are initialized and started in `api/main.py`:

```python
from api.services.websocket_manager import ConnectionManager
from api.services.market_data_service import MarketDataService
from api.services.market_regime_service import MarketRegimeService
from api.services.liquidity_zones_service import LiquidityZonesService
from data.candle_manager_async import AsyncCandleManager

# Initialize connection manager and candle manager
connection_manager = ConnectionManager()
candle_manager = AsyncCandleManager()

# Initialize services
market_data_service = MarketDataService(connection_manager)
market_regime_service = MarketRegimeService(connection_manager)
liquidity_zones_service = LiquidityZonesService(candle_manager)

# Startup event
@app.on_event("startup")
async def startup_event():
    await market_data_service.start()
    await market_regime_service.start()
    await liquidity_zones_service.start()

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    await market_data_service.stop()
    await market_regime_service.stop()
    await liquidity_zones_service.stop()
```

---

## Testing

Each service has a corresponding test file:

- `test_market_data_service.py` - Unit tests for MarketDataService
- `test_market_regime_service.py` - Unit tests for MarketRegimeService
- `test_liquidity_zones_service.py` - Unit tests for LiquidityZonesService

Run tests:
```bash
# Run all service tests
pytest api/services/test_*.py -v

# Run specific service test
pytest api/services/test_liquidity_zones_service.py -v
```

---

## Adding New Services

To add a new service:

1. **Create service file** in `api/services/`:
   ```python
   # api/services/my_service.py
   import asyncio
   import logging
   from typing import Dict
   
   from api.services.websocket_manager import ConnectionManager
   
   logger = logging.getLogger(__name__)
   
   class MyService:
       def __init__(self, connection_manager: ConnectionManager):
           self.connection_manager = connection_manager
           self.running = False
           self.tasks = []
       
       async def start(self):
           if self.running:
               return
           self.running = True
           self.tasks = [
               asyncio.create_task(self._update_loop())
           ]
           logger.info("MyService started")
       
       async def stop(self):
           if not self.running:
               return
           self.running = False
           for task in self.tasks:
               task.cancel()
           await asyncio.gather(*self.tasks, return_exceptions=True)
           logger.info("MyService stopped")
       
       async def _update_loop(self):
           while self.running:
               try:
                   # Your logic here
                   await asyncio.sleep(10.0)
               except asyncio.CancelledError:
                   break
               except Exception as e:
                   logger.error(f"Error in update loop: {e}")
   ```

2. **Register in main.py**:
   ```python
   from api.services.my_service import MyService
   
   my_service = MyService(connection_manager)
   
   @app.on_event("startup")
   async def startup_event():
       await my_service.start()
   
   @app.on_event("shutdown")
   async def shutdown_event():
       await my_service.stop()
   ```

3. **Create tests**:
   ```python
   # api/services/test_my_service.py
   import pytest
   from api.services.my_service import MyService
   from api.services.websocket_manager import ConnectionManager
   
   @pytest.mark.asyncio
   async def test_my_service_lifecycle():
       manager = ConnectionManager()
       service = MyService(manager)
       
       await service.start()
       assert service.running is True
       
       await service.stop()
       assert service.running is False
   ```

---

## Best Practices

1. **Async/Await**: All services use async/await for non-blocking I/O
2. **Error Handling**: Catch exceptions in loops to prevent service crashes
3. **Graceful Shutdown**: Cancel tasks and cleanup resources in `stop()`
4. **Logging**: Use appropriate log levels (debug, info, warning, error)
5. **Circuit Breaker**: Implement error tracking to avoid hammering failing APIs
6. **Status Methods**: Provide `get_service_status()` for health monitoring
7. **Caching**: Cache frequently accessed data to reduce API calls
8. **Testing**: Write comprehensive unit tests for all services

---

## Performance Considerations

- **Parallel Fetching**: Use `asyncio.gather()` for parallel API calls
- **Rate Limiting**: Respect exchange rate limits (handled by exchange clients)
- **Connection Pooling**: Reuse HTTP connections (handled by exchange clients)
- **Memory Management**: Clear old data periodically to prevent memory leaks
- **CPU Usage**: Avoid CPU-intensive operations in async loops
- **WebSocket Efficiency**: Batch updates when possible to reduce message overhead
