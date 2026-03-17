"""
Example usage of the Backtesting Engine.

This script demonstrates how to use the backtesting engine for:
1. Basic backtesting
2. Walk-forward analysis
3. Parameter optimization
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.backtest_engine import BacktestingEngine
from storage.database import Database
from utils.logger import get_logger

log = get_logger("backtesting.example")


def example_basic_backtest():
    """Example: Basic backtest."""
    log.info("=" * 60)
    log.info("Example 1: Basic Backtest")
    log.info("=" * 60)
    
    # Initialize
    db = Database()
    engine = BacktestingEngine(db, candle_manager=None)
    
    # Define date range (last 6 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Strategy configuration
    strategy_config = {
        "symbols": ["BTCUSDT"],
        "min_quality": "A",
        "risk_per_trade_pct": 1.0,
    }
    
    # Run backtest
    log.info(f"Running backtest from {start_date.date()} to {end_date.date()}")
    result = engine.run_backtest(
        strategy_config=strategy_config,
        start_date=start_date,
        end_date=end_date
    )
    
    if result:
        # Print results
        log.info("\n" + "=" * 60)
        log.info("BACKTEST RESULTS")
        log.info("=" * 60)
        log.info(f"Total Trades: {result.total_trades}")
        log.info(f"Win Rate: {result.metrics.win_rate:.2f}%")
        log.info(f"Profit Factor: {result.metrics.profit_factor:.2f}")
        log.info(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
        log.info(f"Max Drawdown: {result.metrics.max_drawdown:.2f}%")
        log.info(f"Total Return: {result.metrics.total_return:.2f}%")
        log.info(f"Average R:R: {result.metrics.avg_rr:.2f}")
        log.info(f"Expectancy: ${result.metrics.expectancy:.2f}")
        log.info("=" * 60)
        
        # Generate report
        report = engine.generate_report(result, "example_backtest_report.json")
        log.info(f"Report saved to example_backtest_report.json")
    else:
        log.warning("No backtest results (insufficient historical data)")


def example_walk_forward_analysis():
    """Example: Walk-forward analysis."""
    log.info("\n" + "=" * 60)
    log.info("Example 2: Walk-Forward Analysis")
    log.info("=" * 60)
    
    # Initialize
    db = Database()
    engine = BacktestingEngine(db, candle_manager=None)
    
    # Define date range (last 12 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Strategy configuration
    strategy_config = {
        "symbols": ["BTCUSDT"],
        "min_quality": "A",
        "risk_per_trade_pct": 1.0,
    }
    
    # Run walk-forward analysis
    log.info(f"Running walk-forward analysis from {start_date.date()} to {end_date.date()}")
    log.info("Train: 6 months, Test: 2 months")
    
    wf_result = engine.run_walk_forward_analysis(
        strategy_config=strategy_config,
        start_date=start_date,
        end_date=end_date,
        train_months=6,
        test_months=2
    )
    
    if wf_result:
        # Print results
        log.info("\n" + "=" * 60)
        log.info("WALK-FORWARD ANALYSIS RESULTS")
        log.info("=" * 60)
        log.info(f"Periods Tested: {len(wf_result.periods)}")
        log.info(f"Consistency Score: {wf_result.consistency_score:.2f}")
        log.info(f"Overfitting Detected: {wf_result.overfitting_detected}")
        log.info("")
        log.info("In-Sample Performance:")
        log.info(f"  Win Rate: {wf_result.avg_in_sample_performance.win_rate:.2f}%")
        log.info(f"  Profit Factor: {wf_result.avg_in_sample_performance.profit_factor:.2f}")
        log.info(f"  Sharpe Ratio: {wf_result.avg_in_sample_performance.sharpe_ratio:.2f}")
        log.info("")
        log.info("Out-of-Sample Performance:")
        log.info(f"  Win Rate: {wf_result.avg_out_sample_performance.win_rate:.2f}%")
        log.info(f"  Profit Factor: {wf_result.avg_out_sample_performance.profit_factor:.2f}")
        log.info(f"  Sharpe Ratio: {wf_result.avg_out_sample_performance.sharpe_ratio:.2f}")
        log.info("=" * 60)
        
        # Overfitting analysis
        overfitting = engine.detect_overfitting(wf_result)
        log.info("\nOverfitting Analysis:")
        log.info(overfitting.recommendation)
    else:
        log.warning("No walk-forward results (insufficient historical data)")


def example_parameter_optimization():
    """Example: Parameter optimization."""
    log.info("\n" + "=" * 60)
    log.info("Example 3: Parameter Optimization")
    log.info("=" * 60)
    
    # Initialize
    db = Database()
    engine = BacktestingEngine(db, candle_manager=None)
    
    # Define date range (last 6 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Base strategy configuration
    base_config = {
        "symbols": ["BTCUSDT"],
        "min_quality": "A",
    }
    
    # Parameter grid to optimize
    param_grid = {
        "risk_per_trade_pct": [0.5, 1.0, 1.5],
    }
    
    # Run optimization
    log.info(f"Optimizing parameters from {start_date.date()} to {end_date.date()}")
    log.info(f"Parameter grid: {param_grid}")
    
    opt_result = engine.optimize_parameters(
        param_grid=param_grid,
        base_config=base_config,
        start_date=start_date,
        end_date=end_date,
        optimization_method="grid"
    )
    
    if opt_result:
        # Print results
        log.info("\n" + "=" * 60)
        log.info("OPTIMIZATION RESULTS")
        log.info("=" * 60)
        log.info(f"Best Parameters: {opt_result.best_params}")
        log.info(f"Best Score (Sharpe): {opt_result.best_score:.3f}")
        log.info(f"Optimization Time: {opt_result.optimization_time_seconds:.1f}s")
        log.info("")
        log.info("All Results:")
        for params, score in sorted(opt_result.all_results, key=lambda x: x[1], reverse=True):
            log.info(f"  {params} -> Score: {score:.3f}")
        log.info("=" * 60)
    else:
        log.warning("No optimization results")


def main():
    """Run all examples."""
    log.info("Backtesting Engine - Example Usage")
    log.info("=" * 60)
    
    try:
        # Example 1: Basic backtest
        example_basic_backtest()
        
        # Example 2: Walk-forward analysis
        example_walk_forward_analysis()
        
        # Example 3: Parameter optimization
        example_parameter_optimization()
        
        log.info("\n" + "=" * 60)
        log.info("All examples completed!")
        log.info("=" * 60)
        
    except Exception as e:
        log.error(f"Error running examples: {e}", exc_info=True)


if __name__ == "__main__":
    main()
