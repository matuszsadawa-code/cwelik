# Technology Stack

## Language & Runtime

- **Python 3.10+**: Primary language for all components
- **asyncio**: Async/await for parallel processing and WebSocket handling

## Core Dependencies

- **requests** (>=2.28.0): HTTP client for REST APIs
- **websocket-client** (>=1.4.0): WebSocket connections for real-time data
- **numpy** (>=1.24.0): Numerical computations
- **pandas** (>=2.0.0): Data manipulation and analysis
- **scikit-learn** (>=1.3.0): ML confidence calibration (Isotonic Regression)
- **tabulate** (>=0.9.0): Table formatting for reports
- **pytz** (>=2023.3): Timezone handling for ICT Killzones

## Dashboard Backend Dependencies

- **fastapi** (>=0.104.0): Modern async web framework for REST API server
- **uvicorn[standard]** (>=0.24.0): ASGI server with WebSocket support
- **websockets** (>=12.0): WebSocket server for real-time dashboard updates
- **pydantic** (>=2.5.0): Data validation and serialization for API models
- **sqlalchemy** (>=2.0.0): Database ORM and connection pooling
- **python-multipart** (>=0.0.6): Form data parsing for file uploads

## Database

- **SQLite3**: Persistent storage with WAL mode
- Thread-local connection pooling for performance
- Tables: signals, signal_outcomes, candle_cache, orderbook_snapshots, trade_clusters, analytics_daily, executions, equity_snapshots

## Testing Framework

- **pytest**: Test runner
- **hypothesis**: Property-based testing
- **pytest-mock**: Mocking utilities

## Project Structure

```
trading_system/
├── analytics/          # Analysis modules (VSA, Wyckoff, Market Profile, etc.)
├── api/               # REST API server for dashboard
├── backtesting/       # Backtesting engine
├── config/            # Configuration files and feature flags
├── dashboard/         # Performance dashboard
├── data/              # Data layer (exchange clients, candle manager, orderbook)
├── db/                # Database files and migrations
├── docs/              # Feature documentation
├── execution/         # Order execution and position management
├── ml/                # Machine learning modules
├── storage/           # Database abstraction layer
├── strategy/          # Signal engine and market analysis
├── testing/           # A/B testing framework
├── tests/             # Test suite
└── utils/             # Utilities (logging, rate limiting, error handling)
```

## Common Commands

### Running the System

```bash
# Standard synchronous mode
python main.py

# Async mode with parallel processing (16x faster, recommended)
python main_async.py

# Single scan mode
python main_async.py --once

# Real-time only mode (WebSocket-driven)
python main_async.py --realtime

# Custom scan interval
python main_async.py --interval 300

# Performance report
python main_async.py --report --days 7c

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_vsa_analyzer.py

# Run with verbose output
pytest tests/ -v

# Run property-based tests only
pytest tests/ -m property

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run integration tests
pytest tests/test_infrastructure.py
```

### Backtesting

```bash
# Run backtest with default config
python -m backtesting

# Run with custom config and date range
python -m backtesting --config my_config.json --start 2023-01-01 --end 2024-01-01
```

### A/B Testing

```bash
# Run A/B test experiment
python -m testing --experiment experiment_name
```

### Dashboard

```bash
# Start legacy performance dashboard
python dashboard/performance_dashboard.py
# Access at http://localhost:8000/dashboard

# Start FastAPI dashboard backend (new)
cd api
uvicorn server:app --reload --host 0.0.0.0 --port 8000
# Access API documentation at http://localhost:8000/docs
# WebSocket endpoint: ws://localhost:8000/ws
```

### Database

```bash
# Run database migrations
python db/migrate.py
```

## Configuration

- **config.json**: API keys for Binance and Bybit
- **config.py**: Strategy parameters, symbols, timeframes
- **config/feature_flags.py**: Enable/disable 20 advanced features across 4 phases
- **config/advanced_features_*.py**: Configuration profiles (default, conservative, aggressive)

## Performance Optimizations

- **Async parallel processing**: 16x faster candle fetching (2-3s vs 40-50s)
- **Connection pooling**: Thread-local SQLite connections
- **WAL mode**: Write-Ahead Logging for better concurrency
- **Caching**: TTL cache for candle data, rate limiting for API calls
- **Batch operations**: Bulk inserts for database writes
