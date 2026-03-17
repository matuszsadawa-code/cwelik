"""
CLI interface for backtesting engine.

Usage:
    python -m backtesting --start 2024-01-01 --end 2024-12-31
    python -m backtesting --walk-forward --train-months 6 --test-months 2
    python -m backtesting --optimize --param atr_multiplier=1.5,2.0,2.5
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.backtest_engine import BacktestingEngine
from storage.database import Database
from utils.logger import get_logger

log = get_logger("backtesting.cli")

# Import data components conditionally
try:
    from data.candle_manager import CandleManager
    from data.bybit_client import BybitClient
    from data.binance_client import BinanceClient
    HAS_DATA_CLIENTS = True
except ImportError:
    log.warning("Data clients not available, using database only")
    HAS_DATA_CLIENTS = False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Backtesting Engine CLI")
    
    # Date range
    parser.add_argument("--start", type=str, required=True,
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True,
                       help="End date (YYYY-MM-DD)")
    
    # Symbols
    parser.add_argument("--symbols", type=str, default="BTCUSDT",
                       help="Comma-separated list of symbols (default: BTCUSDT)")
    
    # Walk-forward analysis
    parser.add_argument("--walk-forward", action="store_true",
                       help="Run walk-forward analysis")
    parser.add_argument("--train-months", type=int, default=6,
                       help="Training period in months (default: 6)")
    parser.add_argument("--test-months", type=int, default=2,
                       help="Testing period in months (default: 2)")
    
    # Parameter optimization
    parser.add_argument("--optimize", action="store_true",
                       help="Run parameter optimization")
    parser.add_argument("--param", type=str, action="append",
                       help="Parameter grid: name=val1,val2,val3")
    
    # Output
    parser.add_argument("--output", type=str, default="backtest_report.json",
                       help="Output report path (default: backtest_report.json)")
    
    return parser.parse_args()


def parse_param_grid(param_args):
    """Parse parameter grid from command line arguments."""
    if not param_args:
        return {}
    
    param_grid = {}
    for param_str in param_args:
        name, values_str = param_str.split("=")
        values = [float(v) if "." in v else int(v) for v in values_str.split(",")]
        param_grid[name] = values
    
    return param_grid


def main():
    """Main CLI entry point."""
    args = parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError as e:
        log.error(f"Invalid date format: {e}")
        sys.exit(1)
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(",")]
    
    log.info(f"Initializing backtesting engine")
    log.info(f"Date range: {start_date.date()} to {end_date.date()}")
    log.info(f"Symbols: {symbols}")
    
    # Initialize components
    db = Database()
    
    if HAS_DATA_CLIENTS:
        bybit = BybitClient()
        binance = BinanceClient()
        candle_mgr = CandleManager(bybit, binance, db)
    else:
        candle_mgr = None
    
    engine = BacktestingEngine(db, candle_mgr)
    
    # Base strategy config
    strategy_config = {
        "symbols": symbols,
        "min_quality": "A",
        "risk_per_trade_pct": 1.0,
    }
    
    # Run appropriate analysis
    if args.optimize:
        log.info("Running parameter optimization")
        param_grid = parse_param_grid(args.param)
        
        if not param_grid:
            log.error("No parameters specified for optimization. Use --param name=val1,val2,val3")
            sys.exit(1)
        
        result = engine.optimize_parameters(
            param_grid=param_grid,
            base_config=strategy_config,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols
        )
        
        log.info(f"Optimization complete!")
        log.info(f"Best parameters: {result.best_params}")
        log.info(f"Best score: {result.best_score:.3f}")
        
    elif args.walk_forward:
        log.info("Running walk-forward analysis")
        result = engine.run_walk_forward_analysis(
            strategy_config=strategy_config,
            start_date=start_date,
            end_date=end_date,
            train_months=args.train_months,
            test_months=args.test_months,
            symbols=symbols
        )
        
        if result:
            log.info(f"Walk-forward analysis complete!")
            log.info(f"Periods: {len(result.periods)}")
            log.info(f"Avg In-Sample Win Rate: {result.avg_in_sample_performance.win_rate:.2f}%")
            log.info(f"Avg Out-Sample Win Rate: {result.avg_out_sample_performance.win_rate:.2f}%")
            log.info(f"Consistency Score: {result.consistency_score:.2f}")
            log.info(f"Overfitting Detected: {result.overfitting_detected}")
        
    else:
        log.info("Running standard backtest")
        result = engine.run_backtest(
            strategy_config=strategy_config,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols
        )
        
        if result:
            log.info(f"Backtest complete!")
            log.info(f"Total Trades: {result.total_trades}")
            log.info(f"Win Rate: {result.metrics.win_rate:.2f}%")
            log.info(f"Profit Factor: {result.metrics.profit_factor:.2f}")
            log.info(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
            log.info(f"Max Drawdown: {result.metrics.max_drawdown:.2f}%")
            log.info(f"Total Return: {result.metrics.total_return:.2f}%")
            
            # Generate report
            report = engine.generate_report(result, args.output)
            log.info(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
