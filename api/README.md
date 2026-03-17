# OpenClaw Trading Dashboard API

FastAPI backend providing REST endpoints and WebSocket connections for real-time market monitoring, performance analytics, and configuration management.

## Project Structure

```
api/
├── __init__.py           # Package initialization
├── main.py               # Main FastAPI application
├── run.py                # Entry point for running the server
├── server.py             # Legacy server (backward compatibility)
├── auth.py               # JWT authentication and authorization
├── database.py           # Database connection pooling
├── models/               # Pydantic models for request/response validation
│   ├── __init__.py
│   ├── market.py         # Market data models
│   ├── trading.py        # Signal and position models
│   ├── performance.py    # Performance metrics models
│   ├── config.py         # Configuration models
│   └── system.py         # System health models
├── routes/               # API route handlers
│   ├── __init__.py       # Route exports
│   ├── market.py         # Market data endpoints
│   ├── signals.py        # Trading signals endpoints
│   └── positions.py      # Position management endpoints
├── services/             # Business logic services
│   ├── __init__.py
│   ├── websocket_manager.py  # WebSocket connection management
│   └── market_data_service.py  # Real-time market data fetching and broadcasting
└── utils/                # Utility functions
    ├── __init__.py
    ├── database.py       # Database connection utilities
    └── config.py         # Configuration utilities
```

## Running the Server

### Method 1: Using the run script
```bash
python -m api.run
```

### Method 2: Using uvicorn directly
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: For production
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check
- `GET /` - Root health check
- `GET /api/health` - Detailed system health

### Authentication
All endpoints (except health checks) require JWT authentication via Bearer token:
```
Authorization: Bearer <jwt_token>
```

User roles:
- **viewer**: Read-only access to market data, signals, and positions
- **trader**: Can close positions manually
- **admin**: Full access to all endpoints and configuration

### Market Data
- `GET /api/market/symbols` - Get list of monitored trading symbols
  - **Auth**: Requires viewer role or higher
  - **Returns**: `List[str]` - Array of symbol names (e.g., ["BTCUSDT", "ETHUSDT"])

### Trading Signals
- `GET /api/signals/active` - Get all active trading signals
  - **Auth**: Requires viewer role or higher
  - **Returns**: `List[SignalResponse]` - Active signals with MFE/MAE, quality, confidence
  - **Limit**: Returns up to 100 most recent signals

### Trade Journal
- `GET /api/trades/history` - Get paginated trade history with filtering and sorting
  - **Auth**: Requires viewer role or higher
  - **Query Params**:
    - `page` (int, default=1): Page number (1-indexed)
    - `page_size` (int, default=50, max=100): Trades per page
    - `symbol` (string, optional): Filter by symbol (e.g., "BTCUSDT")
    - `start_date` (string, optional): Filter trades after date (ISO format)
    - `end_date` (string, optional): Filter trades before date (ISO format)
    - `outcome` (string, optional): Filter by outcome ("WIN" or "LOSS")
    - `quality` (string, optional): Filter by quality grade ("A+", "A", "B", "C")
    - `sort_by` (string, default="closed_at"): Sort column (entry_time, exit_time, pnl, duration, symbol, quality, closed_at)
    - `sort_order` (string, default="desc"): Sort order ("asc" or "desc")
  - **Returns**: Trade history with pagination metadata and applied filters
  - **Example**: `/api/trades/history?page=1&page_size=50&symbol=BTCUSDT&outcome=WIN&sort_by=pnl&sort_order=desc`

- `GET /api/trades/{trade_id}` - Get detailed information for a single trade
  - **Auth**: Requires viewer role or higher
  - **Path Params**: `trade_id` (string) - Trade ID to retrieve
  - **Returns**: Comprehensive trade data including feature contributions, step data, and advanced analytics
  - **Errors**: 404 if trade not found

### Position Management
- `GET /api/positions/open` - Get all open trading positions
  - **Auth**: Requires viewer role or higher
  - **Returns**: `List[PositionResponse]` - Open positions with current P&L
  - **Limit**: Returns up to 100 most recent positions

- `POST /api/positions/{position_id}/close` - Close an open position manually
  - **Auth**: Requires trader role or higher
  - **Path Params**: `position_id` (string) - Position ID to close
  - **Returns**: Success message with closed position details
  - **Errors**: 
    - 404 if position not found or already closed
    - 403 if user lacks trader role

### WebSocket
- `WS /ws` - WebSocket endpoint for real-time updates
  - **Auth**: Token-based authentication via query parameter or initial message

## Middleware

### Performance Monitoring Middleware

The `PerformanceMonitorMiddleware` automatically tracks request timing, database query performance, and WebSocket message latency:

**Features:**
- Automatic request timing with slow request detection (>200ms)
- Database query performance tracking (>50ms threshold)
- WebSocket message latency monitoring (<100ms target)
- Per-endpoint performance statistics
- Query pattern analysis (SELECT, INSERT, UPDATE, DELETE)
- Recent slow operation tracking (last 100 of each type)
- Automatic logging of slow operations
- X-Response-Time header on all responses

**Usage:**
The middleware is automatically applied to all API requests in `api/main.py`:

```python
from api.middleware.performance_monitor import PerformanceMonitorMiddleware

app.add_middleware(PerformanceMonitorMiddleware)
```

**Accessing Performance Data:**
```python
from api.middleware.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()

# Get overall statistics
stats = monitor.get_stats()

# Get per-endpoint statistics
endpoint_stats = monitor.get_endpoint_stats()

# Get query pattern statistics
query_stats = monitor.get_query_pattern_stats()

# Get recent slow requests
slow_requests = monitor.get_recent_slow_requests(limit=10)

# Get recent slow queries
slow_queries = monitor.get_recent_slow_queries(limit=10)

# Reset statistics
monitor.reset_stats()
```

**Performance Thresholds:**
- Slow API request: >200ms
- Slow database query: >50ms
- Slow WebSocket message: >100ms

**API Endpoints:**
- `GET /api/performance/stats` - Overall performance statistics
- `GET /api/performance/endpoints` - Per-endpoint statistics
- `GET /api/performance/queries` - Query pattern statistics
- `GET /api/performance/slow-requests?limit=10` - Recent slow requests
- `GET /api/performance/slow-queries?limit=10` - Recent slow queries
- `POST /api/performance/reset` - Reset statistics (admin only)

See [Performance Monitoring Documentation](../docs/PERFORMANCE_MONITORING.md) for detailed usage and best practices.

## Services

### Market Data Service

The `MarketDataService` provides real-time market data fetching and broadcasting:

**Features:**
- Periodic ticker updates every 1 second (price, volume, 24h change)
- Trade flow updates every 2 seconds for CVD calculation
- Multi-exchange support (Binance and Bybit with automatic fallback)
- CVD (Cumulative Volume Delta) calculation from trade flow
- Circuit breaker pattern for error handling (skips symbols after 5 consecutive errors)
- Efficient async parallel fetching for multiple symbols
- Automatic error recovery (resets error counts every 5 minutes)

**Usage:**
```python
from api.services.market_data_service import MarketDataService
from api.services.websocket_manager import ConnectionManager

# Initialize
connection_manager = ConnectionManager()
market_data_service = MarketDataService(connection_manager, symbols=["BTCUSDT", "ETHUSDT"])

# Start background tasks
await market_data_service.start()

# Get cached data
data = market_data_service.get_market_data("BTCUSDT")
cvd = market_data_service.get_cvd("BTCUSDT")

# Get service status
status = market_data_service.get_service_status()

# Stop service
await market_data_service.stop()
```

**Broadcast Messages:**
The service broadcasts `market_data_update` messages to all WebSocket clients subscribed to the `market_data` channel.

### Performance Metrics Service

The `PerformanceMetricsService` calculates and broadcasts comprehensive trading performance metrics:

**Features:**
- Periodic metrics calculation every 30 seconds
- Win rate calculation from completed trades
- Profit factor (sum of wins / abs(sum of losses))
- Sharpe ratio with annualization (√252 trading days)
- Maximum drawdown (peak-to-trough decline)
- Current drawdown from peak equity
- Daily, weekly, and monthly P&L aggregations
- Total trades and active positions count
- Real-time WebSocket broadcasting to subscribed clients

**Metrics Calculated:**
- **Win Rate**: (winning trades / total trades) × 100
- **Profit Factor**: sum(winning P&L) / abs(sum(losing P&L))
- **Sharpe Ratio**: (mean return - risk-free rate) / std(returns) × √252
- **Max Drawdown**: Maximum peak-to-trough decline in equity curve
- **Current Drawdown**: Current decline from peak equity
- **Daily P&L**: P&L for current day (percentage)
- **Weekly P&L**: P&L for last 7 days (percentage)
- **Monthly P&L**: P&L for last 30 days (percentage)

**Usage:**
```python
from api.services.performance_metrics_service import PerformanceMetricsService
from api.services.websocket_manager import ConnectionManager
from storage.database import Database

# Initialize
connection_manager = ConnectionManager()
database = Database()
metrics_service = PerformanceMetricsService(connection_manager, database)

# Start background calculation loop (30s interval)
await metrics_service.start()

# Get cached metrics
metrics = metrics_service.get_cached_metrics()

# Get service status
status = metrics_service.get_service_status()

# Stop service
await metrics_service.stop()
```

**Data Sources:**
- `signal_outcomes` table: Completed trades with P&L data
- `equity_snapshots` table: Historical equity curve data
- `executions` table: Active positions count

**Broadcast Messages:**
The service broadcasts `performance_update` messages to all WebSocket clients subscribed to the `performance` channel every 30 seconds.

### Trade Journal Service

The `TradeJournalService` provides comprehensive trade history retrieval and management for the trade journal interface:

**Features:**
- Retrieve completed trades from `signal_outcomes` table with associated signal details
- Pagination support for large trade histories (configurable page size)
- Multi-criteria filtering (symbol, date range, outcome, quality grade)
- Flexible sorting by any column (entry time, exit time, P&L, duration)
- Complete trade data including entry/exit prices, P&L, MFE/MAE, reasons
- Detailed single trade retrieval with feature contributions and step data
- Service health monitoring with trade count and date range

**API Methods:**

**`get_trade_history()`** - Retrieve paginated trade history with filtering and sorting
```python
from api.services.trade_journal_service import TradeJournalService

service = TradeJournalService()

# Get trades with filters
result = service.get_trade_history(
    page=1,
    page_size=50,
    symbol="BTCUSDT",           # Optional: Filter by symbol
    start_date="2024-01-01",    # Optional: ISO format date
    end_date="2024-12-31",      # Optional: ISO format date
    outcome="WIN",              # Optional: "WIN" or "LOSS"
    quality="A+",               # Optional: "A+", "A", "B", "C"
    sort_by="closed_at",        # entry_time, exit_time, pnl, duration, symbol, quality
    sort_order="desc"           # "asc" or "desc"
)

# Returns:
# {
#   "trades": [...],           # List of trade dictionaries
#   "pagination": {
#     "page": 1,
#     "pageSize": 50,
#     "totalTrades": 150,
#     "totalPages": 3
#   },
#   "filters": {...}           # Applied filters
# }
```

**`get_trade_detail(trade_id)`** - Get detailed information for a single trade
```python
# Get detailed trade information
trade = service.get_trade_detail("123")

# Returns comprehensive trade data including:
# - Basic trade info (symbol, direction, prices, P&L)
# - Quality metrics (quality grade, confidence, MFE/MAE)
# - Timing data (entry time, exit time, duration)
# - Exit details (TP/SL hit, exit reason)
# - Feature contributions from advanced analytics
# - Step-by-step ICT framework data (step1_data, step2_data, etc.)
# - Advanced analytics (market regime, feature contributions)
```

**`get_service_status()`** - Get service health status
```python
# Check service status
status = service.get_service_status()

# Returns:
# {
#   "initialized": True,
#   "total_trades": 150,
#   "earliest_trade": "2024-01-01T00:00:00Z",
#   "latest_trade": "2024-12-31T23:59:59Z",
#   "has_data": True
# }
```

**Trade Data Structure:**

Each trade in the history includes:
- **tradeId**: Unique trade identifier
- **signalId**: Associated signal ID
- **symbol**: Trading pair (e.g., "BTCUSDT")
- **direction**: Trade direction ("LONG" or "SHORT")
- **quality**: Signal quality grade ("A+", "A", "B", "C")
- **confidence**: Signal confidence score (0-100)
- **entryPrice**: Entry price (8 decimal precision)
- **exitPrice**: Exit price (8 decimal precision)
- **stopLoss**: Stop loss price
- **takeProfit**: Take profit price
- **pnl**: Realized P&L percentage (2 decimal precision)
- **outcome**: Trade outcome ("WIN" or "LOSS")
- **rrAchieved**: Achieved risk-reward ratio
- **mfe**: Maximum Favorable Excursion (%)
- **mae**: Maximum Adverse Excursion (%)
- **duration**: Trade duration in minutes
- **entryTime**: Entry timestamp (ISO format)
- **exitTime**: Exit timestamp (ISO format)
- **entryReason**: Signal entry reasoning
- **exitReason**: Trade exit reason
- **tpHit**: Whether take profit was hit (boolean)
- **slHit**: Whether stop loss was hit (boolean)
- **marketRegime**: Market regime at entry ("TRENDING", "RANGING", "VOLATILE", "QUIET")

**Data Sources:**
- `signal_outcomes` table: Completed trades with P&L and exit data
- `signals` table: Signal details, entry prices, quality metrics

**Usage in API Routes:**
```python
from fastapi import APIRouter, Query
from api.services.trade_journal_service import TradeJournalService

router = APIRouter(prefix="/api/trades", tags=["trades"])
service = TradeJournalService()

@router.get("/history")
async def get_trade_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    symbol: str = None,
    start_date: str = None,
    end_date: str = None,
    outcome: str = None,
    quality: str = None,
    sort_by: str = "closed_at",
    sort_order: str = "desc"
):
    return service.get_trade_history(
        page=page,
        page_size=page_size,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        outcome=outcome,
        quality=quality,
        sort_by=sort_by,
        sort_order=sort_order
    )

@router.get("/{trade_id}")
async def get_trade_detail(trade_id: str):
    trade = service.get_trade_detail(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade
```

## WebSocket Message Types

### Client → Server

**Subscribe to channels:**
```json
{
  "type": "subscribe",
  "channels": ["market_data", "signals", "positions", "performance"]
}
```

**Unsubscribe from channels:**
```json
{
  "type": "unsubscribe",
  "channels": ["market_data"]
}
```

**Heartbeat ping:**
```json
{
  "type": "ping"
}
```

### Server → Client

**Market data update:**
```json
{
  "type": "market_data_update",
  "data": {
    "symbol": "BTCUSDT",
    "price": 45000.0,
    "volume24h": 1000000.0,
    "change24h": 2.5,
    "bidAskSpread": 0.5,
    "cvd": 1234.5678,
    "timestamp": 1704110400000
  }
}
```

**Signal update:**
```json
{
  "type": "signal_update",
  "data": {
    "signal_id": "sig_123",
    "symbol": "ETHUSDT",
    "direction": "LONG",
    "current_price": 2550.0,
    "unrealized_pnl": 2.0,
    "mfe": 3.0,
    "mae": -1.0,
    "status": "ACTIVE"
  }
}
```

**Position update:**
```json
{
  "type": "position_update",
  "data": {
    "position_id": "pos_456",
    "symbol": "BTCUSDT",
    "side": "LONG",
    "current_price": 45500.0,
    "unrealized_pnl": 500.0,
    "unrealized_pnl_percent": 1.11
  }
}
```

**Performance metrics update:**
```json
{
  "type": "performance_update",
  "data": {
    "winRate": 58.5,
    "profitFactor": 1.85,
    "sharpeRatio": 1.42,
    "maxDrawdown": -12.5,
    "currentDrawdown": -3.2,
    "dailyPnL": 2.5,
    "weeklyPnL": 8.3,
    "monthlyPnL": 15.7,
    "totalTrades": 150,
    "activePositions": 3,
    "timestamp": 1704110400000
  }
}
```

**Heartbeat pong:**
```json
{
  "type": "pong"
}
```

## Security

### Security Logger

The API includes comprehensive security event logging with anomaly detection via `api/utils/security_logger.py`.

**Features:**
- Authentication and authorization event logging
- Automatic anomaly detection (excessive auth failures, suspicious IPs)
- Configuration change tracking
- Severity-based logging (INFO, WARNING, ERROR, CRITICAL)
- User context tracking (user ID, username, IP address, user agent)

**Quick Usage:**
```python
from api.utils.security_logger import get_security_logger

security_logger = get_security_logger()

# Log authentication failure
security_logger.log_auth_failure(
    username="trader1",
    ip_address="192.168.1.100",
    reason="Invalid password"
)

# Log configuration change
security_logger.log_config_change(
    user_id="user_123",
    username="admin1",
    ip_address="192.168.1.100",
    config_type="risk_settings",
    changes={"max_position_size": 10000}
)
```

**Anomaly Detection:**
- Automatically detects excessive authentication failures (threshold: 5 attempts)
- Flags suspicious IPs after repeated violations
- Logs CRITICAL alerts for detected anomalies

See [Security Documentation](../docs/SECURITY.md) for comprehensive usage guide, best practices, and integration examples.

## Dependencies

- fastapi>=0.104.0 - Modern async web framework
- uvicorn[standard]>=0.24.0 - ASGI server with WebSocket support
- websockets>=12.0 - WebSocket protocol implementation
- pydantic>=2.5.0 - Data validation and serialization
- sqlalchemy>=2.0.0 - Database ORM and connection pooling
- python-jose[cryptography]>=3.3.0 - JWT token handling
- passlib[bcrypt]>=1.7.4 - Password hashing
- python-multipart>=0.0.6 - Form data parsing
- sentry-sdk[fastapi]>=1.40.0 - Error tracking and performance monitoring (optional)

## Authentication

The API uses JWT (JSON Web Tokens) for authentication with role-based access control.

### User Roles

- **viewer**: Read-only access to market data, signals, and positions
- **trader**: Can close positions manually + viewer permissions
- **admin**: Full access to all endpoints and configuration

### Getting a Token

Authentication endpoints will be implemented in Phase 1.5. For now, tokens can be generated using the `api.auth` module:

```python
from api.auth import create_access_token

token = create_access_token(
    data={"sub": "username", "role": "trader"}
)
```

### Using the Token

Include the token in the Authorization header:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/signals/active
```

## Development

### Project Integration

The API is designed to work seamlessly with the existing OpenClaw trading system:
- Uses the existing `storage.database.Database` for data access
- Integrates with the existing `config` module for configuration
- Maintains backward compatibility with legacy `server.py`
- Implements connection pooling via `api.database.DatabaseConnectionPool`

### Route Organization

Routes are organized by domain in the `api/routes/` directory:
- **market.py**: Market data endpoints (symbols, orderbook, liquidity zones)
- **signals.py**: Trading signal endpoints (active signals, signal details)
- **positions.py**: Position management endpoints (open positions, close position)

All routes are registered in `api/main.py` via the router imports from `api/routes/__init__.py`.

### Adding New Routes

1. Create a new route file in `api/routes/` (e.g., `analytics.py`)
2. Define your router with appropriate prefix and tags:
   ```python
   from fastapi import APIRouter
   
   router = APIRouter(prefix="/api/analytics", tags=["analytics"])
   
   @router.get("/performance")
   async def get_performance():
       # Implementation
       pass
   ```
3. Export the router in `api/routes/__init__.py`:
   ```python
   from .analytics import router as analytics_router
   
   __all__ = [..., "analytics_router"]
   ```
4. Register the router in `api/main.py`:
   ```python
   from api.routes import analytics_router
   
   app.include_router(analytics_router)
   ```

### Testing

Run the test suite:
```bash
pytest tests/test_api_setup.py -v
```

Test specific endpoints:
```bash
pytest tests/test_api_setup.py::TestAPISetup::test_root_endpoint -v
```
