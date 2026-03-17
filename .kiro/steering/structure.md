# Project Structure

## Directory Organization

### Core Modules

- **main.py**: Synchronous entry point with real-time WebSocket monitoring
- **main_async.py**: Async entry point with parallel processing (recommended, 16x faster)
- **config.py**: Global configuration (symbols, timeframes, strategy parameters)
- **config.json**: API credentials for exchanges

### /analytics

Market analysis modules implementing 20 advanced trading features:

- **vsa_analyzer.py**: Volume Spread Analysis (market maker manipulation)
- **wyckoff_analyzer.py**: Wyckoff Method (accumulation/distribution phases)
- **market_profile.py**: Market Profile TPO (Value Area, POC)
- **liquidity_engineer.py**: Liquidity sweeps and stop hunts
- **smart_money_divergence.py**: CVD, OI, funding rate divergences
- **mtf_confluence.py**: Multi-timeframe signal validation
- **orderbook_imbalance.py**: Iceberg, spoofing, absorption detection
- **institutional_flow.py**: TWAP/VWAP execution patterns
- **volatility_regime.py**: Dynamic parameter adjustment by regime
- **seasonality.py**: Cyclical pattern detection
- **momentum_indicators.py**: RSI, MACD, momentum analysis
- **reversal_patterns.py**: Pattern recognition
- **news_sentiment.py**: Real-time sentiment analysis
- **microstructure.py**: Spread dynamics and toxic flow
- **performance.py**: Performance metrics and reporting
- **signal_tracker.py**: Signal lifecycle tracking (MFE/MAE)

### /data

Data layer for exchange connectivity and market data:

- **bybit_client.py**: Synchronous Bybit REST API client
- **bybit_client_async.py**: Async Bybit client with parallel processing
- **binance_client.py**: Synchronous Binance REST API client
- **binance_client_async.py**: Async Binance client with parallel processing
- **candle_manager.py**: Synchronous candle data management
- **candle_manager_async.py**: Async candle manager with TTL cache (16x faster)
- **orderbook.py**: Order book snapshot management
- **trade_flow.py**: Trade flow analysis (CVD, delta)
- **footprint.py**: Footprint chart analysis
- **advanced_orderflow.py**: Advanced order flow metrics
- **crypto_analytics.py**: Crypto-specific analytics (funding, OI)
- **symbol_manager.py**: Dynamic symbol list management
- **realtime_monitor.py**: WebSocket real-time monitoring

### /strategy

Signal generation and market analysis:

- **signal_engine.py**: Main signal generation engine (4-step ICT framework)
- **market_structure.py**: Market structure analysis (CHoCH, BOS)
- **market_regime.py**: Market regime detection (TRENDING/RANGING/VOLATILE/QUIET)
- **step1_trend.py**: Step 1 - Trend analysis
- **step2_zones.py**: Step 2 - Zone identification (OB, FVG)
- **step3_volume.py**: Step 3 - Volume confirmation
- **step4_orderflow.py**: Step 4 - Order flow validation
- **risk_manager.py**: Risk management rules
- **dynamic_weights.py**: Dynamic feature weighting

### /execution

Order execution and position management:

- **order_executor.py**: Order execution engine (paper/live modes)
- **position_manager.py**: Position tracking and management
- **portfolio.py**: Portfolio-level management
- **adaptive_sl.py**: Adaptive stop loss system
- **dynamic_tp_optimizer.py**: Dynamic take profit optimization
- **correlation_optimizer.py**: Correlation-based portfolio optimization
- **enhanced_risk_manager.py**: Enhanced risk management (Kelly Criterion)
- **tp_calculator.py**: Take profit calculation utilities
- **exchange_minimums.py**: Exchange minimum order sizes

### /storage

Database abstraction layer:

- **database.py**: SQLite database manager with connection pooling
- **query_optimizer.py**: Query optimization utilities

### /ml

Machine learning modules:

- **confidence_calibrator.py**: ML-based confidence calibration (Isotonic Regression)

### /backtesting

Backtesting engine:

- **backtest_engine.py**: Walk-forward analysis with overfitting detection
- **example_usage.py**: Backtesting examples

### /testing

A/B testing framework:

- **ab_framework.py**: Statistical A/B testing for features
- **integration_example.py**: Integration examples

### /dashboard

Performance analytics:

- **performance_dashboard.py**: Real-time performance dashboard (web UI)

### /api

REST API server:

- **server.py**: FastAPI/Flask server for dashboard backend

### /config

Configuration management:

- **feature_flags.py**: Feature flags for 20 advanced features (4 phases)
- **advanced_features_default.py**: Default configuration profile
- **advanced_features_conservative.py**: Conservative profile (lower risk)
- **advanced_features_aggressive.py**: Aggressive profile (higher risk)
- **ict_config.py**: ICT-specific configuration
- **config_validator.py**: Configuration validation

### /utils

Utility modules:

- **logger.py**: Centralized logging
- **rate_limiter.py**: API rate limiting (sync)
- **async_rate_limiter.py**: API rate limiting (async)
- **error_handler.py**: Error handling utilities
- **async_error_handler.py**: Async error handling
- **cache.py**: Caching utilities
- **circuit_breaker.py**: Circuit breaker pattern

### /tests

Comprehensive test suite:

- **conftest.py**: Pytest configuration and shared fixtures
- **test_*.py**: Unit tests for each module
- Property-based tests using Hypothesis for correctness validation
- Integration tests for end-to-end workflows

### /db

Database files:

- **trading_system.db**: Main SQLite database
- **migrate.py**: Database migration script

### /docs

Feature documentation (20+ markdown files):

- Implementation guides for each advanced feature
- Configuration guides
- Deployment checklists
- Integration verification reports

### /logs

Log files:

- **trading_system.log**: Application logs

### /reports

Performance reports:

- JSON and text format performance reports

## Key Architectural Patterns

### Async/Sync Duality

- Most modules have both sync and async versions
- Async versions use `asyncio` for parallel processing
- Sync versions for backward compatibility and simpler use cases

### Adapter Pattern

- `SyncCandleManagerAdapter`: Wraps async candle manager for sync signal engine
- Allows sync code to use async cached data

### Repository Pattern

- `Database` class abstracts all database operations
- Thread-local connection pooling for performance

### Strategy Pattern

- Feature flags enable/disable features dynamically
- Configuration profiles (default/conservative/aggressive)

### Observer Pattern

- `RealtimeMonitor` triggers callbacks on market events
- `SignalTracker` tracks signal lifecycle events

## Data Flow

1. **Data Ingestion**: Exchange clients fetch candles, orderbook, trades via REST/WebSocket
2. **Caching**: `AsyncCandleManager` caches data with TTL for performance
3. **Analysis**: Analytics modules process data (VSA, Wyckoff, Market Profile, etc.)
4. **Signal Generation**: `SignalEngine` runs 4-step ICT framework
5. **Risk Management**: Regime detection, volatility adjustment, correlation checks
6. **Execution**: `OrderExecutor` places orders (paper/live)
7. **Tracking**: `SignalTracker` monitors signal outcomes (MFE/MAE, TP/SL)
8. **Storage**: `Database` persists signals, executions, analytics
9. **Reporting**: `PerformanceReporter` generates metrics and reports

## Module Dependencies

### Core Dependencies

- `config.py` → Used by all modules for global configuration
- `utils/logger.py` → Used by all modules for logging
- `storage/database.py` → Used by modules that persist data

### Data Layer Dependencies

- Exchange clients → Used by candle managers, orderbook, trade flow
- Candle managers → Used by signal engine, analytics modules
- Orderbook/Trade flow → Used by advanced order flow analysis

### Strategy Layer Dependencies

- Signal engine → Depends on candle manager, orderbook, trade flow, analytics
- Market regime → Depends on candle manager
- Risk manager → Depends on signal engine, market regime

### Execution Layer Dependencies

- Order executor → Depends on exchange clients
- Position manager → Depends on order executor
- Portfolio → Depends on position manager, correlation optimizer

## Testing Strategy

- **Unit tests**: Test individual functions and classes in isolation
- **Property-based tests**: Use Hypothesis to validate invariants and correctness properties
- **Integration tests**: Test end-to-end workflows
- **Fixtures**: Shared test data in `conftest.py`
- **Mocking**: Mock external dependencies (exchange APIs, database)
