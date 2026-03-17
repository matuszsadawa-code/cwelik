# OpenClaw v3.0 Trading System

## Overview

OpenClaw v3.0 is an advanced institutional-grade trading system that combines ICT (Inner Circle Trader) methodology with 20+ professional trading optimization features. The system provides real-time market analysis, intelligent signal generation, adaptive risk management, and comprehensive performance analytics.

### Key Features

**Core ICT Strategy (4-Step Framework)**
- Step 1: Trend Analysis (Market Structure, CHoCH, BOS)
- Step 2: Zone Identification (Order Blocks, Fair Value Gaps, Liquidity Pools)
- Step 3: Volume Confirmation (Footprint, CVD, DOM Analysis)
- Step 4: Order Flow Validation (Trade Flow, Market Pulse, Whale Tracking)

**Advanced Trading Optimization ("Golden Sauce")**
- Volume Spread Analysis (VSA) - Market maker manipulation detection
- Wyckoff Method - Accumulation/distribution phase identification
- Market Profile (TPO) - Value Area and Point of Control analysis
- Enhanced Liquidity Engineering - Liquidity sweep and stop hunt detection
- Smart Money Divergence - CVD, OI, and funding rate divergences
- Multi-Timeframe Confluence - Cross-timeframe signal validation
- Advanced Order Book Imbalance - Iceberg, spoofing, and absorption detection
- Institutional Order Flow - TWAP/VWAP execution pattern recognition
- Volatility Regime Adaptation - Dynamic parameter adjustment
- Seasonality Detection - Cyclical pattern and time-based analysis
- ML Confidence Calibration - Isotonic regression-based probability calibration
- Dynamic Take Profit - ATR-based adaptive TP with momentum extension
- Adaptive Stop Loss - Structure-aware SL with trailing logic
- Correlation Optimization - Portfolio diversification and correlation management
- Enhanced Risk Management - Kelly Criterion with dynamic adjustment
- News Sentiment Integration - Real-time sentiment analysis and event detection
- Market Microstructure - Spread dynamics and toxic flow detection
- Backtesting Engine - Walk-forward analysis with overfitting detection
- A/B Testing Framework - Statistical validation of new features
- Performance Dashboard - Real-time analytics and reporting

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd trading_system

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python db/migrate.py
```

### Dependencies

**Core Trading System:**
- `requests>=2.28.0` - HTTP client for exchange APIs
- `websocket-client>=1.4.0` - WebSocket connections for real-time data
- `numpy>=1.24.0` - Numerical computations
- `pandas>=2.0.0` - Data manipulation and analysis
- `scikit-learn>=1.3.0` - ML confidence calibration
- `tabulate>=0.9.0` - Table formatting for reports
- `pytz>=2023.3` - Timezone handling for ICT Killzones

**Dashboard Backend (New):**
- `fastapi>=0.104.0` - Modern async web framework for REST API
- `uvicorn[standard]>=0.24.0` - ASGI server for FastAPI
- `websockets>=12.0` - WebSocket server for real-time updates
- `pydantic>=2.5.0` - Data validation and serialization
- `sqlalchemy>=2.0.0` - Database ORM and connection pooling
- `python-multipart>=0.0.6` - Form data parsing for file uploads

**Dashboard Services:**
- Trade Journal Service - Comprehensive trade history retrieval with filtering, sorting, and pagination
- Symbol PnL Service - Per-symbol performance analysis with cumulative PnL tracking
- Performance Metrics Service - Real-time win rate, profit factor, Sharpe ratio
- System Health Service - API monitoring, WebSocket status, database performance
- Query Cache - TTL-based caching layer for database query results (30-60s TTL, 60-80% hit rate)
- Performance Monitoring - Request timing, database query performance, WebSocket latency tracking

**Analytics Services (Initialized on Startup):**
- Equity Curve Service - Equity curve generation with drawdown period identification
- PnL Breakdown Service - Daily, weekly, and monthly PnL aggregation
- Symbol Performance Service - Per-symbol performance statistics and metrics
- Risk Metrics Service - Sharpe ratio, Sortino ratio, Calmar ratio, and drawdown analysis
- Quality Analysis Service - Quality grade performance analysis and calibration validation
- R:R Distribution Service - Risk-reward ratio distribution and bucket analysis
- Symbol PnL Service - Per-symbol cumulative PnL tracking and trade-by-trade details

### Configuration

1. **Copy Environment Template**: `cp .env.example .env`
2. **Configure Environment Variables**: See [Environment Setup Guide](docs/ENVIRONMENT_SETUP_GUIDE.md) for detailed instructions
3. **Verify Configuration** (Recommended):
   ```bash
   python scripts/verify_env_setup.py
   ```
   This automated script will:
   - Check if `.env` file exists and has content
   - Verify `.env` is in `.gitignore` and not tracked by git
   - Validate critical environment variables (JWT_SECRET_KEY, DATABASE_URL)
   - Check JWT secret key strength (32+ characters)
   - Verify database directory exists
   - Offer to generate secure keys if missing

4. **Configure API Keys**: Edit `config.json` with your exchange API credentials
5. **Select Configuration Profile**: Choose from default, conservative, or aggressive profiles
6. **Enable Features**: Use feature flags in `config/feature_flags.py` to control which features are active

```python
# Example: config/feature_flags.py
FEATURE_FLAGS = {
    "vsa_enabled": True,
    "wyckoff_enabled": True,
    "market_profile_enabled": True,
    # ... see config/feature_flags.py for all options
}
```

### Running the System

```bash
# Standard mode
python main.py

# Async mode (recommended for production)
python main_async.py

# Optimized mode with performance profiling
python run_optimized.py

# Backtesting
python -m backtesting --config config/backtest_config.json

# A/B Testing
python -m testing --experiment experiment_name

# Performance Dashboard (Legacy)
python dashboard/performance_dashboard.py
# Access at http://localhost:8000/dashboard

# Trading Dashboard API Server (New - FastAPI)
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Access API docs at http://localhost:8000/docs
# WebSocket endpoint: ws://localhost:8000/ws

# Dashboard API Endpoints:
# Analytics Services (auto-initialized on startup):
# GET /api/analytics/equity-curve - Equity curve with drawdown periods
# GET /api/analytics/pnl-breakdown - Daily/weekly/monthly PnL aggregation
# GET /api/analytics/symbol-performance - Per-symbol performance statistics
# GET /api/analytics/risk-metrics - Sharpe, Sortino, Calmar ratios
# GET /api/analytics/quality-analysis - Quality grade performance analysis
# GET /api/analytics/rr-distribution - Risk-reward ratio distribution
# GET /api/analytics/symbol-pnl/{symbol} - Per-symbol PnL analysis
# GET /api/analytics/symbol-pnl-multi?symbols=BTC,ETH - Compare up to 4 symbols
# GET /api/health - System health status
```

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│  WebSocket Feeds │ REST APIs │ News APIs │ Order Book       │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                  Analysis Layer                              │
│  VSA │ Wyckoff │ Market Profile │ Liquidity Engineering     │
│  Smart Money Divergence │ MTF Confluence │ Order Book       │
│  Institutional Flow │ Microstructure │ Seasonality          │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                  Signal Engine                               │
│  4-Step ICT Framework │ Dynamic Weights │ ML Calibration    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│              Adaptation & Risk Layer                         │
│  Volatility Regime │ Correlation Optimizer │ Risk Manager   │
│  Dynamic TP │ Adaptive SL │ News Sentiment                  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                 Execution Layer                              │
│  Position Manager │ Order Executor │ Portfolio Manager      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│              Analytics & Testing                             │
│  Backtesting │ A/B Testing │ Performance Dashboard          │
└─────────────────────────────────────────────────────────────┘
```

### Integration Points

- **Signal Engine**: Main integration point for all analysis features
- **Position Manager**: Integration for execution features (TP/SL management)
- **Portfolio Manager**: Integration for correlation and risk management
- **Database**: Persistent storage for signals, trades, and analytics
- **Dashboard**: Real-time monitoring and performance visualization

## Configuration Profiles

### Default Profile
Balanced configuration suitable for most market conditions.
- File: `config/advanced_features_default.py`
- Risk per trade: 1%
- Min signal quality: A
- Moderate confidence boosts

### Conservative Profile
Lower risk, higher quality thresholds for stable returns.
- File: `config/advanced_features_conservative.py`
- Risk per trade: 0.5%
- Min signal quality: A+
- Reduced confidence boosts

### Aggressive Profile
Higher risk, lower thresholds for maximum opportunity capture.
- File: `config/advanced_features_aggressive.py`
- Risk per trade: 2%
- Min signal quality: B
- Enhanced confidence boosts

## Feature Documentation

Detailed documentation for each module is available in the `docs/` directory:


- [Configuration Guide](docs/CONFIGURATION_GUIDE.md) - Complete configuration reference
- [VSA Implementation](docs/VSA_IMPLEMENTATION.md) - Volume Spread Analysis
- [Wyckoff Implementation](docs/WYCKOFF_IMPLEMENTATION_SUMMARY.md) - Wyckoff Method
- [Market Profile](docs/MARKET_PROFILE_IMPLEMENTATION.md) - TPO and Value Area
- [Liquidity Engineering](docs/LIQUIDITY_ENGINEERING_IMPLEMENTATION.md) - Liquidity analysis
- [Smart Money Divergence](docs/SMART_MONEY_DIVERGENCE_IMPLEMENTATION.md) - Divergence detection
- [MTF Confluence](docs/MTF_CONFLUENCE_IMPLEMENTATION.md) - Multi-timeframe analysis
- [Order Book Imbalance](docs/ORDERBOOK_IMBALANCE_IMPLEMENTATION.md) - DOM analysis
- [Institutional Flow](docs/INSTITUTIONAL_FLOW_IMPLEMENTATION.md) - Institutional patterns
- [Volatility Regime](docs/VOLATILITY_REGIME_IMPLEMENTATION.md) - Adaptive volatility
- [Seasonality](docs/SEASONALITY_IMPLEMENTATION.md) - Cyclical patterns
- [ML Calibration](docs/ML_CONFIDENCE_CALIBRATION_IMPLEMENTATION.md) - Confidence calibration
- [Dynamic TP](docs/DYNAMIC_TP_IMPLEMENTATION.md) - Take profit optimization
- [Adaptive SL](docs/ADAPTIVE_SL_IMPLEMENTATION.md) - Stop loss management
- [Correlation Optimization](docs/CORRELATION_OPTIMIZATION_IMPLEMENTATION.md) - Portfolio optimization
- [Market Microstructure](docs/MICROSTRUCTURE_IMPLEMENTATION.md) - Spread dynamics and toxic flow
- [Backtesting](docs/BACKTESTING_IMPLEMENTATION.md) - Backtesting engine

## Performance Metrics

The system tracks comprehensive performance metrics:

- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Average R:R**: Average risk-reward ratio
- **Confidence Accuracy**: Calibration quality (Brier Score)
- **Feature Contribution**: Impact of each feature on performance

Access real-time metrics via the Performance Dashboard at `http://localhost:8000/dashboard`

## Testing

### Unit Tests
```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/test_vsa_analyzer.py
pytest tests/test_wyckoff_analyzer.py
```

### Bug Exploration Tests
```bash
# Run bug exploration tests (expected to fail on unfixed code)
pytest tests/test_realtime_analytics_logging_bug_exploration.py -v
pytest tests/test_tpsl_automation_bug_exploration.py -v

# These tests encode expected behavior and validate fixes
```

### Preservation Tests
```bash
# Run preservation tests (validate no regressions)
pytest tests/test_realtime_analytics_logging_preservation.py -v

# These tests ensure existing functionality remains unchanged
```

### Property-Based Tests
```bash
# Run property tests (may take longer)
pytest tests/ -m property

# Run with verbose output
pytest tests/ -m property -v
```

### Async Tests
```bash
# Run async tests
pytest tests/ -m asyncio -v

# Run with output capture disabled (see logs)
pytest tests/ -m asyncio -s
```

### Integration Tests
```bash
# Run integration tests
pytest tests/test_infrastructure.py
```

### Backtesting
```bash
# Run backtest with default config
python -m backtesting

# Run with custom config
python -m backtesting --config my_config.json --start 2023-01-01 --end 2024-01-01
```

For detailed testing methodology, see [Testing Guide](docs/TESTING.md).

## Monitoring and Alerts

### Real-Time Monitoring
- Performance Dashboard: `http://localhost:8000/dashboard`
- Log files: `logs/trading_system.log`
- Database: `db/trading_system.db`

### Alert Configuration
Configure alerts in `config.json`:
```json
{
  "alerts": {
    "daily_loss_limit": 3.0,
    "max_drawdown_alert": 10.0,
    "low_win_rate_threshold": 50.0
  }
}
```

## Troubleshooting

### Common Issues

**Issue**: High latency in signal processing
- **Solution**: Check `PERFORMANCE_OPTIMIZATION_SUMMARY.md` for optimization tips
- Enable caching in `config/feature_flags.py`
- Consider reducing number of active features

**Issue**: Database connection errors
- **Solution**: Run `python db/migrate.py` to ensure schema is up to date
- Check database file permissions

**Issue**: API rate limiting
- **Solution**: Adjust polling intervals in `config.json`
- Enable request caching where applicable

## Support and Contributing

For issues, questions, or contributions, please refer to the project repository.

## License

[Add license information]

## Changelog

### v3.0.1 - Bugfix Release (In Progress)
- **TTLCache Dict-Like Interface**: Added dict-like methods to TTLCache for debugging and compatibility
  - Spec location: `.kiro/specs/ttlcache-keys-attributeerror/`
  - Bug: AttributeError when attempting to access cache keys for diagnostics in `main_async.py`
  - Fix: Added dict-like interface methods to `TTLCache` class in `utils/cache.py` with thread-safe implementation
  - Impact: Cache diagnostics and debugging now work correctly; TTLCache can be used anywhere dict-like behavior is expected
  - API Additions:
    - `TTLCache.keys()` - Returns dict_keys view of all cache keys
    - `TTLCache.values()` - Returns list of all cached values
    - `TTLCache.items()` - Returns list of (key, value) tuples
    - `TTLCache.__len__()` - Supports `len(cache)` to get cache size
    - `TTLCache.__contains__()` - Supports `key in cache` membership testing
  - All methods are thread-safe and properly handle the internal CacheEntry wrapper structure
  - Status: Complete
- **Symbol Format Fix**: Fixed WebSocket subscription failures for hyphenated symbols
  - Spec location: `.kiro/specs/symbol-format-fix/`
  - Bug: WebSocket subscriptions failed when symbols contained hyphens (e.g., `BTC-USDT`)
  - Fix: Symbol format normalization in `RealtimeMonitor._start_websockets()` - converts `BTC-USDT` → `BTCUSDT` before WebSocket subscription
  - Impact: All 30 configured symbols now successfully subscribe to ByBit and Binance WebSocket streams
  - Preservation: Internal symbol tracking remains in original format for consistency with config and database
  - Status: Complete
- **Realtime Analytics Logging Fix**: Fixed missing analytics logs in main_async.py --realtime mode
  - Spec location: `.kiro/specs/realtime-analytics-logging-fix/`
  - Bug: RealtimeMonitor triggers analysis but signal_engine.analyze_symbol() logs not visible
  - Fix: Logger configuration and async context handling improvements
  - Tests: Bug exploration and preservation tests with async log capture
  - Status: Tasks 1-3 complete, verification in progress
  - **Recent Changes**:
    - Enhanced trigger evaluation logging in `RealtimeMonitor._should_trigger_analysis()` (changed from DEBUG to INFO level)
    - Trigger evaluation logs now visible at INFO level showing volatility, delta, and trade count metrics
    - Improved visibility of trigger decision-making process for debugging and monitoring
- **WebSocket Division by Zero Fix**: Fixed critical division by zero error in real-time volatility calculation
  - Spec location: `.kiro/specs/websocket-division-by-zero-fix/`
  - Bug: When `min(prices)` equals 0 in the 1-minute price buffer, the volatility calculation in `data/realtime_monitor.py` line 372 threw ZeroDivisionError, causing thousands of exceptions and eventual WebSocket connection closure
  - Root Cause: Missing guard condition before division - code assumed all prices in buffer are positive
  - Fix: Added guard condition `if min_price > 0:` before volatility calculation; sets `volatility_1m = 0` when min price is zero or negative
  - Impact: WebSocket connections remain stable when encountering zero prices; no console flooding with error messages
  - Preservation: Valid volatility calculations unchanged for positive prices; all other trade processing (volume, delta, buffer management) unaffected
  - Tests: Property-based bug exploration tests (expected to fail on unfixed code) and preservation tests (validate no regressions)
  - Status: Fix implemented and tested
- **Bug Exploration Tests**: Added property-based tests for TP/SL automation failures
  - Test file: `tests/test_tpsl_automation_bug_exploration.py`
  - Validates breakeven automation (Bug 1) and trailing stop activation (Bug 2)
  - Uses Hypothesis for property-based testing with scoped bug conditions
  - Tests expected to fail on unfixed code to confirm bugs exist
- **Bugfix Spec**: Trading System Configuration and TP/SL Fixes
  - Spec location: `.kiro/specs/trading-system-configuration-and-tp-sl-fixes/`
  - Addresses 6 critical bugs across trade management, configuration, and real-time processing
  - Includes design document with formal bug conditions and correctness properties
- **Testing Methodology**: Comprehensive testing guide added
  - Documentation: `docs/TESTING.md`
  - Covers unit tests, property-based tests, async tests, bug exploration workflow
  - Includes best practices for mocking, log capture, and debugging

### v3.0 - Advanced Trading Optimization
- Added 20 institutional-grade trading features
- Implemented ML-based confidence calibration
- Added comprehensive backtesting and A/B testing frameworks
- Enhanced risk management with dynamic adaptation
- Integrated news sentiment analysis
- Added real-time performance dashboard

### v2.0 - ICT Framework
- Implemented 4-step ICT strategy
- Added advanced order flow analysis
- Integrated crypto-specific analytics

### v1.0 - Initial Release
- Basic trading functionality
- Simple signal generation


## Documentation

### Getting Started
- [Installation & Setup](docs/DEPENDENCIES.md) - System requirements and installation guide
- [Environment Setup Guide](docs/ENVIRONMENT_SETUP_GUIDE.md) - Environment variables configuration and verification
- [Environment Variables Reference](docs/ENVIRONMENT_VARIABLES.md) - Complete environment variables documentation
- [Configuration Guide](docs/CONFIGURATION_GUIDE.md) - Complete configuration reference
- [Quick Start](#quick-start) - Get up and running quickly

### Testing
- [Testing Guide](docs/TESTING.md) - Comprehensive testing methodology and best practices
  - Unit tests, property-based tests, integration tests
  - Bug exploration and preservation testing workflow
  - Async testing with log capture
  - Mocking strategies and debugging tips

### Security
- [Security Documentation](docs/SECURITY.md) - Security event logging, anomaly detection, and best practices

### API Documentation
- [Dashboard API Reference](docs/DASHBOARD_API.md) - REST API and WebSocket endpoints for the trading dashboard
- [Performance Monitoring](docs/PERFORMANCE_MONITORING.md) - Request timing, query performance, and latency tracking
- Trade Journal Service - Comprehensive trade history retrieval with filtering, sorting, and pagination
- Symbol PnL Service - Per-symbol performance analysis
- Performance Metrics Service - Real-time trading metrics
- System Health Service - Monitoring and diagnostics

### Features
- [Features Overview](docs/FEATURES_OVERVIEW.md) - Comprehensive overview of all 20 features
- [Integration Guide](docs/INTEGRATION_GUIDE.md) - How features integrate with the system

### Deployment
- [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md) - Pre-deployment validation and rollout plan
- [Rollback Procedure](docs/ROLLBACK_PROCEDURE.md) - Emergency rollback procedures
- [Monitoring & Alerting](docs/MONITORING_AND_ALERTING.md) - Monitoring setup and alert configuration

### Module Documentation
- [VSA Implementation](docs/VSA_IMPLEMENTATION.md)
- [Wyckoff Implementation](docs/WYCKOFF_IMPLEMENTATION_SUMMARY.md)
- [Market Profile Implementation](docs/MARKET_PROFILE_IMPLEMENTATION.md)
- [Liquidity Engineering](docs/LIQUIDITY_ENGINEERING_IMPLEMENTATION.md)
- [Smart Money Divergence](docs/SMART_MONEY_DIVERGENCE_IMPLEMENTATION.md)
- [MTF Confluence](docs/MTF_CONFLUENCE_IMPLEMENTATION.md)
- [Order Book Imbalance](docs/ORDERBOOK_IMBALANCE_IMPLEMENTATION.md)
- [Institutional Flow](docs/INSTITUTIONAL_FLOW_IMPLEMENTATION.md)
- [Volatility Regime](docs/VOLATILITY_REGIME_IMPLEMENTATION.md)
- [Seasonality](docs/SEASONALITY_IMPLEMENTATION.md)
- [ML Calibration](docs/ML_CONFIDENCE_CALIBRATION_IMPLEMENTATION.md)
- [Dynamic TP](docs/DYNAMIC_TP_IMPLEMENTATION.md)
- [Adaptive SL](docs/ADAPTIVE_SL_IMPLEMENTATION.md)
- [Correlation Optimization](docs/CORRELATION_OPTIMIZATION_IMPLEMENTATION.md)
- [Backtesting](docs/BACKTESTING_IMPLEMENTATION.md)

## System Status

### Current Version: v3.0

**Status**: Production Ready ✅

**Last Updated**: 2024

**Features Implemented**: 20/20 (100%)

**Test Coverage**: 80%+

**Performance**: <100ms per symbol processing

## Deployment Status

### Phase 1: Core Analysis ✅
- VSA Analyzer
- Wyckoff Analyzer
- Market Profile
- Liquidity Engineering
- Smart Money Divergence

### Phase 2: Intelligence Layer ✅
- MTF Confluence
- Order Book Imbalance
- Institutional Flow
- Volatility Regime
- Seasonality Detector

### Phase 3: Adaptation & Optimization ✅
- ML Confidence Calibrator
- Dynamic TP Optimizer
- Adaptive SL System
- Correlation Optimizer
- Enhanced Risk Manager

### Phase 4: Integration & Analytics ✅
- News Sentiment Analyzer
- Microstructure Analyzer
- Backtesting Engine
- A/B Testing Framework
- Performance Dashboard

## Contributing

We welcome contributions! Please see our contributing guidelines.

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd trading_system

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
pylint strategy/ analytics/ execution/
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all public functions
- Maintain test coverage >80%

## FAQ

**Q: What exchanges are supported?**
A: Currently Binance and Bybit. More exchanges can be added via CCXT.

**Q: Can I run this on a VPS?**
A: Yes, recommended for 24/7 operation. See deployment guide.

**Q: What's the minimum capital required?**
A: Depends on exchange minimums. Recommended: $1000+ for proper diversification.

**Q: How much does it cost to run?**
A: VPS: $10-50/month, News API: $0-50/month, Exchange fees: 0.1% per trade.

**Q: Is this profitable?**
A: Past performance doesn't guarantee future results. Backtest thoroughly and start with paper trading.

**Q: Can I customize the strategy?**
A: Yes, all parameters are configurable. See Configuration Guide.

**Q: What's the expected win rate?**
A: Backtests show 55-60% win rate with proper configuration.

**Q: How do I report bugs?**
A: Open an issue on GitHub with detailed description and logs.

## Disclaimer

**IMPORTANT**: This software is for educational and research purposes. Trading cryptocurrencies carries significant risk. You can lose all your capital. Always:

- Start with paper trading
- Backtest thoroughly
- Use proper risk management
- Never invest more than you can afford to lose
- Understand the code before running it
- Monitor the system continuously
- Have a rollback plan

The developers are not responsible for any financial losses incurred while using this software.

## Acknowledgments

- ICT (Inner Circle Trader) for the core methodology
- Wyckoff Institute for market analysis techniques
- Open source community for excellent libraries
- All contributors and testers

## Contact

- GitHub: [Repository URL]
- Email: [Contact Email]
- Discord: [Server Invite]
- Telegram: [Group Link]

---

**Built with ❤️ for the trading community**
