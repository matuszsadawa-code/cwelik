# Backtesting Engine

Comprehensive backtesting system for strategy validation and parameter optimization with walk-forward analysis to detect overfitting.

## Features

- **Historical Data Loading**: Load OHLCV data from database for backtesting
- **Full Signal Lifecycle Simulation**: Simulate signal generation → entry → TP/SL → exit
- **Performance Metrics**: Win Rate, Profit Factor, Sharpe Ratio, Max Drawdown, Avg R:R, Expectancy
- **Walk-Forward Analysis**: Train on N months, test on M months, rolling window
- **Overfitting Detection**: Compare in-sample vs out-of-sample performance
- **Parameter Optimization**: Grid search or Bayesian optimization
- **Detailed Reports**: Equity curve, drawdown chart, trade distribution

## Installation

The backtesting engine is part of the trading system. No additional installation required.

## Usage

### Command Line Interface

#### Basic Backtest

```bash
python -m backtesting --start 2024-01-01 --end 2024-12-31 --symbols BTCUSDT
```

#### Walk-Forward Analysis

```bash
python -m backtesting \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --walk-forward \
  --train-months 6 \
  --test-months 2 \
  --symbols BTCUSDT,ETHUSDT
```

#### Parameter Optimization

```bash
python -m backtesting \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --optimize \
  --param atr_multiplier=1.5,2.0,2.5 \
  --param risk_per_trade_pct=0.5,1.0,1.5 \
  --symbols BTCUSDT
```

### Python API

```python
from datetime import datetime
from backtesting import BacktestingEngine
from storage.database import Database
from data.candle_manager import CandleManager

# Initialize
db = Database()
candle_mgr = CandleManager(bybit, binance, db)
engine = BacktestingEngine(db, candle_mgr)

# Run backtest
result = engine.run_backtest(
    strategy_config={
        "symbols": ["BTCUSDT"],
        "min_quality": "A",
        "risk_per_trade_pct": 1.0,
    },
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# Print results
print(f"Win Rate: {result.metrics.win_rate:.2f}%")
print(f"Profit Factor: {result.metrics.profit_factor:.2f}")
print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.metrics.max_drawdown:.2f}%")

# Generate report
report = engine.generate_report(result, "backtest_report.json")
```

### Walk-Forward Analysis

```python
# Run walk-forward analysis
wf_result = engine.run_walk_forward_analysis(
    strategy_config={"symbols": ["BTCUSDT"]},
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    train_months=6,
    test_months=2
)

# Check for overfitting
print(f"Overfitting Detected: {wf_result.overfitting_detected}")
print(f"In-Sample Win Rate: {wf_result.avg_in_sample_performance.win_rate:.2f}%")
print(f"Out-Sample Win Rate: {wf_result.avg_out_sample_performance.win_rate:.2f}%")
print(f"Consistency Score: {wf_result.consistency_score:.2f}")
```

### Parameter Optimization

```python
# Optimize parameters
param_grid = {
    "atr_multiplier": [1.5, 2.0, 2.5, 3.0],
    "risk_per_trade_pct": [0.5, 1.0, 1.5],
}

opt_result = engine.optimize_parameters(
    param_grid=param_grid,
    base_config={"symbols": ["BTCUSDT"]},
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    optimization_method="grid"
)

print(f"Best Parameters: {opt_result.best_params}")
print(f"Best Score: {opt_result.best_score:.3f}")
```

## Configuration

Default configuration:

```python
{
    "walk_forward_train_months": 6,      # Train on 6 months
    "walk_forward_test_months": 2,       # Test on 2 months
    "overfitting_threshold": 0.7,        # Out-sample must be >70% in-sample
    "slippage_pct": 0.05,                # 0.05% slippage per trade
    "commission_pct": 0.06,              # 0.06% commission (maker+taker)
    "initial_capital": 10000,            # $10k starting capital
    "max_concurrent_positions": 5,       # Max 5 positions
    "risk_per_trade_pct": 1.0,          # 1% risk per trade
}
```

## Performance Metrics

### Win Rate
Percentage of winning trades: `wins / total_trades * 100`

### Profit Factor
Ratio of gross profit to gross loss: `gross_profit / gross_loss`

### Sharpe Ratio
Risk-adjusted return: `(mean_return - risk_free_rate) / std_return * sqrt(252)`

### Max Drawdown
Maximum peak-to-trough decline: `(peak - trough) / peak * 100`

### Average R:R
Average risk-reward ratio achieved across all trades

### Expectancy
Expected profit per trade: `total_pnl / total_trades`

## Walk-Forward Analysis

Walk-forward analysis prevents overfitting by:

1. **Training Period**: Optimize parameters on N months of data
2. **Testing Period**: Test optimized parameters on next M months (out-of-sample)
3. **Rolling Window**: Move forward by M months and repeat
4. **Validation**: Compare in-sample vs out-of-sample performance

**Overfitting Detection**: If out-of-sample performance is <70% of in-sample, the strategy is likely overfitted.

## Output Reports

Reports include:

- **Summary**: Win rate, profit factor, Sharpe ratio, max drawdown, total return
- **Trade Statistics**: Winning/losing trades, avg win/loss, consecutive streaks
- **Equity Curve**: Timestamp and equity value over time
- **Drawdown Curve**: Drawdown percentage over time
- **Trade Distribution**: R:R distribution, duration distribution, exit reasons

Example report structure:

```json
{
  "summary": {
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-12-31T23:59:59",
    "total_trades": 150,
    "win_rate": "62.67%",
    "profit_factor": "1.85",
    "sharpe_ratio": "1.42",
    "max_drawdown": "12.34%",
    "total_return": "45.67%"
  },
  "trades": {
    "winning_trades": 94,
    "losing_trades": 56,
    "avg_win": "$125.50",
    "avg_loss": "$75.25"
  },
  "equity_curve": [...],
  "drawdown_curve": [...],
  "trade_distribution": {
    "rr_distribution": {"<0.5": 20, "0.5-1.0": 30, "1.0-2.0": 50, ...},
    "duration_distribution": {"<1h": 40, "1-4h": 60, "4-24h": 40, ...},
    "exit_reasons": {"TP1": 60, "TP2": 34, "SL": 50, "EXPIRED": 6}
  }
}
```

## Testing

Run unit tests:

```bash
python -m pytest tests/test_backtest_engine.py -v
```

## Requirements

- Python 3.8+
- numpy
- pandas
- Database with historical candle data

## Integration

The backtesting engine integrates with:

- **Database**: Loads historical OHLCV data
- **CandleManager**: Fetches candle data
- **SignalEngine**: (Future) Use actual signal generation logic

## Limitations

- Current implementation uses simplified signal generation for testing
- For production backtesting, integrate with actual SignalEngine
- Slippage and commission are simplified models
- Does not account for market impact or liquidity constraints

## Future Enhancements

- [ ] Bayesian optimization implementation
- [ ] Multi-asset portfolio backtesting
- [ ] Monte Carlo simulation
- [ ] Integration with actual SignalEngine
- [ ] Real-time strategy monitoring
- [ ] Advanced slippage models
- [ ] Market impact modeling

## License

Part of the OpenClaw v3.0 trading system.
