"""
Backtesting Engine with Walk-Forward Analysis

Comprehensive backtesting system for strategy validation and parameter optimization.
Implements walk-forward analysis to detect overfitting and ensure robust strategies.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import json

import sys
from pathlib import Path

# Ensure parent directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import Database
from utils.logger import get_logger

log = get_logger("backtesting.engine")


@dataclass
class TradeOutcome:
    """Result of a single trade simulation."""
    signal_id: str
    entry_price: float
    exit_price: float
    exit_reason: str  # TP1, TP2, SL, EXPIRED
    pnl: float
    pnl_pct: float
    duration_hours: float
    rr_achieved: float
    entry_time: datetime
    exit_time: datetime


@dataclass
class PerformanceMetrics:
    """Performance metrics for backtesting results."""
    win_rate: float  # %
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float  # %
    avg_rr: float
    expectancy: float  # $ per trade
    total_return: float  # %
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int


@dataclass
class BacktestResult:
    """Complete backtest result with all metrics and trades."""
    start_date: datetime
    end_date: datetime
    total_trades: int
    metrics: PerformanceMetrics
    trades: List[TradeOutcome]
    equity_curve: List[Tuple[datetime, float]]
    drawdown_curve: List[Tuple[datetime, float]]
    config: Dict[str, Any]


@dataclass
class WalkForwardPeriod:
    """Single walk-forward period with in-sample and out-of-sample results."""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    in_sample_metrics: PerformanceMetrics
    out_sample_metrics: PerformanceMetrics
    best_params: Optional[Dict] = None


@dataclass
class WalkForwardResult:
    """Complete walk-forward analysis result."""
    periods: List[WalkForwardPeriod]
    avg_in_sample_performance: PerformanceMetrics
    avg_out_sample_performance: PerformanceMetrics
    consistency_score: float  # 0-100
    overfitting_detected: bool


@dataclass
class OverfittingAnalysis:
    """Overfitting detection analysis."""
    is_overfitted: bool
    in_sample_win_rate: float
    out_sample_win_rate: float
    performance_ratio: float  # out/in
    recommendation: str


@dataclass
class OptimizationResult:
    """Parameter optimization result."""
    best_params: Dict
    best_score: float
    all_results: List[Tuple[Dict, float]]
    optimization_time_seconds: float


class BacktestingEngine:
    """
    Comprehensive backtesting engine with walk-forward analysis.
    
    Features:
    - Historical data loading from database
    - Full signal lifecycle simulation
    - Performance metrics calculation
    - Walk-forward analysis
    - Overfitting detection
    - Parameter optimization
    """

    
    def __init__(self, db: Database, candle_manager=None, config: Dict = None):
        """
        Initialize backtesting engine.
        
        Args:
            db: Database instance for historical data
            candle_manager: CandleManager for fetching candles (optional)
            config: Backtesting configuration
        """
        self.db = db
        self.candle_mgr = candle_manager
        self.config = config or self._default_config()
        self.results: List[BacktestResult] = []
        log.info("BacktestingEngine initialized")
    
    def _default_config(self) -> Dict:
        """Get default backtesting configuration."""
        return {
            "walk_forward_train_months": 6,
            "walk_forward_test_months": 2,
            "overfitting_threshold": 0.7,
            "slippage_pct": 0.05,
            "commission_pct": 0.06,
            "initial_capital": 10000,
            "max_concurrent_positions": 5,
            "risk_per_trade_pct": 1.0,
        }
    
    def load_historical_data(
        self, 
        symbols: List[str], 
        start_date: datetime, 
        end_date: datetime,
        timeframe: str = "5"
    ) -> Dict[str, List[Dict]]:
        """
        Load historical OHLCV data for backtesting.
        
        Args:
            symbols: List of symbols to load
            start_date: Start date for data
            end_date: End date for data
            timeframe: Timeframe in minutes
            
        Returns:
            Dict mapping symbol to list of candles
        """
        log.info(f"Loading historical data for {len(symbols)} symbols from {start_date} to {end_date}")
        
        historical_data = {}
        for symbol in symbols:
            try:
                # Try to load from database cache first
                candles = self.db.get_cached_candles(symbol, timeframe, "cross", limit=10000)
                
                # Filter by date range
                filtered_candles = [
                    c for c in candles
                    if start_date.timestamp() * 1000 <= c["open_time"] <= end_date.timestamp() * 1000
                ]
                
                if filtered_candles:
                    historical_data[symbol] = filtered_candles
                    log.info(f"Loaded {len(filtered_candles)} candles for {symbol}")
                else:
                    log.warning(f"No historical data found for {symbol}")
                    
            except Exception as e:
                log.error(f"Failed to load data for {symbol}: {e}")
        
        return historical_data

    
    def run_backtest(
        self,
        strategy_config: Dict,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str] = None
    ) -> BacktestResult:
        """
        Run full backtest simulation.
        
        Simulates:
        - Signal generation
        - Entry execution
        - TP/SL hits
        - Position management
        
        Args:
            strategy_config: Strategy configuration
            start_date: Backtest start date
            end_date: Backtest end date
            symbols: List of symbols to test (default: from config)
            
        Returns:
            BacktestResult with performance metrics
        """
        log.info(f"Running backtest from {start_date} to {end_date}")
        
        if symbols is None:
            symbols = strategy_config.get("symbols", ["BTCUSDT"])
        
        # Load historical data
        historical_data = self.load_historical_data(symbols, start_date, end_date)
        
        if not historical_data:
            log.error("No historical data available for backtest")
            return None
        
        # Simulate trades
        all_trades = []
        for symbol, candles in historical_data.items():
            trades = self._simulate_symbol_trades(symbol, candles, strategy_config)
            all_trades.extend(trades)
        
        # Calculate metrics
        metrics = self.calculate_metrics(all_trades)
        
        # Generate equity curve
        equity_curve = self._generate_equity_curve(all_trades)
        drawdown_curve = self._calculate_drawdown_curve(equity_curve)
        
        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            total_trades=len(all_trades),
            metrics=metrics,
            trades=all_trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            config=strategy_config
        )
        
        self.results.append(result)
        log.info(f"Backtest complete: {len(all_trades)} trades, Win Rate: {metrics.win_rate:.2f}%")
        
        return result
    
    def _simulate_symbol_trades(
        self,
        symbol: str,
        candles: List[Dict],
        strategy_config: Dict
    ) -> List[TradeOutcome]:
        """
        Simulate trades for a single symbol.
        
        Args:
            symbol: Trading symbol
            candles: Historical candle data
            strategy_config: Strategy configuration
            
        Returns:
            List of trade outcomes
        """
        trades = []
        
        # Simple simulation: generate signals based on basic criteria
        # In production, this would use the actual SignalEngine
        for i in range(100, len(candles) - 50):  # Need history and future data
            signal = self._generate_test_signal(symbol, candles[:i+1], strategy_config)
            
            if signal:
                future_candles = candles[i+1:i+51]  # Next 50 candles
                outcome = self.simulate_signal_lifecycle(signal, future_candles)
                if outcome:
                    trades.append(outcome)
        
        return trades

    
    def _generate_test_signal(
        self,
        symbol: str,
        candles: List[Dict],
        strategy_config: Dict
    ) -> Optional[Dict]:
        """
        Generate a test signal for backtesting.
        
        This is a simplified signal generator for testing.
        In production, use the actual SignalEngine.
        
        Args:
            symbol: Trading symbol
            candles: Historical candles
            strategy_config: Strategy config
            
        Returns:
            Signal dict or None
        """
        if len(candles) < 20:
            return None
        
        current = candles[-1]
        prev = candles[-2]
        
        # Simple momentum-based signal
        price_change = (current["close"] - prev["close"]) / prev["close"]
        
        # Generate signal if price moves >1%
        if abs(price_change) > 0.01:
            direction = "LONG" if price_change > 0 else "SHORT"
            entry_price = current["close"]
            
            # Calculate SL and TP based on ATR
            atr = self._calculate_atr(candles[-20:])
            
            if direction == "LONG":
                sl_price = entry_price - (atr * 2.0)
                tp1_price = entry_price + (atr * 1.5)
                tp2_price = entry_price + (atr * 3.0)
            else:
                sl_price = entry_price + (atr * 2.0)
                tp1_price = entry_price - (atr * 1.5)
                tp2_price = entry_price - (atr * 3.0)
            
            return {
                "signal_id": f"TEST-{symbol}-{current['open_time']}",
                "symbol": symbol,
                "signal_type": direction,
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "entry_time": datetime.fromtimestamp(current["open_time"] / 1000),
                "confidence": 75.0,
            }
        
        return None
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(candles) < period:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i-1]["close"]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges[-period:]) / period if true_ranges else 0.0

    
    def simulate_signal_lifecycle(
        self,
        signal: Dict,
        future_candles: List[Dict]
    ) -> Optional[TradeOutcome]:
        """
        Simulate signal from generation to TP/SL hit.
        
        Args:
            signal: Trading signal
            future_candles: Future candle data after signal
            
        Returns:
            TradeOutcome or None if signal expires
        """
        if not future_candles:
            return None
        
        entry_price = signal["entry_price"]
        sl_price = signal["sl_price"]
        tp1_price = signal.get("tp1_price", signal.get("tp_price"))
        tp2_price = signal.get("tp2_price", tp1_price)
        direction = signal["signal_type"]
        
        # Apply slippage to entry
        slippage = entry_price * (self.config["slippage_pct"] / 100)
        entry_price = entry_price + slippage if direction == "LONG" else entry_price - slippage
        
        # Simulate candle-by-candle
        for i, candle in enumerate(future_candles):
            high = candle["high"]
            low = candle["low"]
            
            # Check SL hit
            if direction == "LONG":
                if low <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_time = datetime.fromtimestamp(candle["open_time"] / 1000)
                    break
                # Check TP hit
                elif high >= tp2_price:
                    exit_price = tp2_price
                    exit_reason = "TP2"
                    exit_time = datetime.fromtimestamp(candle["open_time"] / 1000)
                    break
                elif high >= tp1_price:
                    exit_price = tp1_price
                    exit_reason = "TP1"
                    exit_time = datetime.fromtimestamp(candle["open_time"] / 1000)
                    break
            else:  # SHORT
                if high >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_time = datetime.fromtimestamp(candle["open_time"] / 1000)
                    break
                # Check TP hit
                elif low <= tp2_price:
                    exit_price = tp2_price
                    exit_reason = "TP2"
                    exit_time = datetime.fromtimestamp(candle["open_time"] / 1000)
                    break
                elif low <= tp1_price:
                    exit_price = tp1_price
                    exit_reason = "TP1"
                    exit_time = datetime.fromtimestamp(candle["open_time"] / 1000)
                    break
        else:
            # Signal expired without hitting TP/SL
            exit_price = future_candles[-1]["close"]
            exit_reason = "EXPIRED"
            exit_time = datetime.fromtimestamp(future_candles[-1]["open_time"] / 1000)
        
        # Calculate PnL
        if direction == "LONG":
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
        
        # Apply commission
        pnl_pct -= self.config["commission_pct"]
        
        # Calculate R:R achieved
        risk = abs(entry_price - sl_price)
        reward = abs(exit_price - entry_price)
        rr_achieved = reward / risk if risk > 0 else 0
        
        # Calculate duration
        duration_hours = (exit_time - signal["entry_time"]).total_seconds() / 3600
        
        # Calculate PnL in dollars
        position_size = self.config["initial_capital"] * (self.config["risk_per_trade_pct"] / 100)
        pnl = position_size * (pnl_pct / 100)
        
        return TradeOutcome(
            signal_id=signal["signal_id"],
            entry_price=entry_price,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl=pnl,
            pnl_pct=pnl_pct,
            duration_hours=duration_hours,
            rr_achieved=rr_achieved,
            entry_time=signal["entry_time"],
            exit_time=exit_time
        )

    
    def calculate_metrics(self, trades: List[TradeOutcome]) -> PerformanceMetrics:
        """
        Calculate performance metrics from trades.
        
        Metrics:
        - Win Rate
        - Profit Factor
        - Sharpe Ratio
        - Max Drawdown
        - Average R:R
        - Expectancy
        
        Args:
            trades: List of trade outcomes
            
        Returns:
            PerformanceMetrics
        """
        if not trades:
            return PerformanceMetrics(
                win_rate=0, profit_factor=0, sharpe_ratio=0,
                max_drawdown=0, avg_rr=0, expectancy=0,
                total_return=0, total_trades=0, winning_trades=0,
                losing_trades=0, avg_win=0, avg_loss=0,
                max_consecutive_wins=0, max_consecutive_losses=0
            )
        
        # Basic stats
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        wins = len(winning_trades)
        losses = len(losing_trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        # PnL stats
        total_pnl = sum(t.pnl for t in trades)
        total_return = (total_pnl / self.config["initial_capital"]) * 100
        
        avg_win = sum(t.pnl for t in winning_trades) / wins if wins > 0 else 0
        avg_loss = abs(sum(t.pnl for t in losing_trades) / losses) if losses > 0 else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Expectancy
        expectancy = total_pnl / total_trades if total_trades > 0 else 0
        
        # Average R:R
        avg_rr = sum(t.rr_achieved for t in trades) / total_trades if total_trades > 0 else 0
        
        # Sharpe Ratio
        returns = [t.pnl_pct for t in trades]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        
        # Max Drawdown
        equity_curve = self._generate_equity_curve(trades)
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        # Consecutive wins/losses
        max_consecutive_wins = self._calculate_max_consecutive(trades, win=True)
        max_consecutive_losses = self._calculate_max_consecutive(trades, win=False)
        
        return PerformanceMetrics(
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            avg_rr=avg_rr,
            expectancy=expectancy,
            total_return=total_return,
            total_trades=total_trades,
            winning_trades=wins,
            losing_trades=losses,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses
        )

    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0) -> float:
        """Calculate Sharpe Ratio."""
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe (assuming daily returns)
        sharpe = (mean_return - risk_free_rate) / std_return * np.sqrt(252)
        return sharpe
    
    def _generate_equity_curve(self, trades: List[TradeOutcome]) -> List[Tuple[datetime, float]]:
        """Generate equity curve from trades."""
        equity = self.config["initial_capital"]
        curve = [(trades[0].entry_time if trades else datetime.now(), equity)]
        
        for trade in trades:
            equity += trade.pnl
            curve.append((trade.exit_time, equity))
        
        return curve
    
    def _calculate_drawdown_curve(self, equity_curve: List[Tuple[datetime, float]]) -> List[Tuple[datetime, float]]:
        """Calculate drawdown curve from equity curve."""
        if not equity_curve:
            return []
        
        drawdown_curve = []
        peak = equity_curve[0][1]
        
        for timestamp, equity in equity_curve:
            if equity > peak:
                peak = equity
            
            drawdown = ((peak - equity) / peak * 100) if peak > 0 else 0
            drawdown_curve.append((timestamp, drawdown))
        
        return drawdown_curve
    
    def _calculate_max_drawdown(self, equity_curve: List[Tuple[datetime, float]]) -> float:
        """Calculate maximum drawdown percentage."""
        if not equity_curve:
            return 0.0
        
        peak = equity_curve[0][1]
        max_dd = 0.0
        
        for _, equity in equity_curve:
            if equity > peak:
                peak = equity
            
            drawdown = ((peak - equity) / peak * 100) if peak > 0 else 0
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_max_consecutive(self, trades: List[TradeOutcome], win: bool = True) -> int:
        """Calculate maximum consecutive wins or losses."""
        if not trades:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            is_win = trade.pnl > 0
            
            if is_win == win:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive

    
    def run_walk_forward_analysis(
        self,
        strategy_config: Dict,
        start_date: datetime,
        end_date: datetime,
        train_months: int = None,
        test_months: int = None,
        symbols: List[str] = None
    ) -> WalkForwardResult:
        """
        Run walk-forward analysis.
        
        Process:
        1. Train on N months
        2. Test on M months
        3. Roll window forward
        4. Repeat
        
        Args:
            strategy_config: Strategy configuration
            start_date: Analysis start date
            end_date: Analysis end date
            train_months: Training period in months
            test_months: Testing period in months
            symbols: List of symbols to test
            
        Returns:
            WalkForwardResult with in-sample vs out-of-sample performance
        """
        train_months = train_months or self.config["walk_forward_train_months"]
        test_months = test_months or self.config["walk_forward_test_months"]
        
        log.info(f"Running walk-forward analysis: train={train_months}m, test={test_months}m")
        
        periods = []
        current_date = start_date
        
        while current_date < end_date:
            # Define train period
            train_start = current_date
            train_end = train_start + timedelta(days=train_months * 30)
            
            # Define test period
            test_start = train_end
            test_end = test_start + timedelta(days=test_months * 30)
            
            if test_end > end_date:
                break
            
            log.info(f"WF Period: Train {train_start.date()} to {train_end.date()}, "
                    f"Test {test_start.date()} to {test_end.date()}")
            
            # Run in-sample backtest (training period)
            in_sample_result = self.run_backtest(
                strategy_config, train_start, train_end, symbols
            )
            
            # Run out-of-sample backtest (testing period)
            out_sample_result = self.run_backtest(
                strategy_config, test_start, test_end, symbols
            )
            
            if in_sample_result and out_sample_result:
                period = WalkForwardPeriod(
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    in_sample_metrics=in_sample_result.metrics,
                    out_sample_metrics=out_sample_result.metrics
                )
                periods.append(period)
            
            # Move window forward by test period
            current_date = test_end
        
        if not periods:
            log.warning("No walk-forward periods completed")
            return None
        
        # Calculate average performance
        avg_in_sample = self._average_metrics([p.in_sample_metrics for p in periods])
        avg_out_sample = self._average_metrics([p.out_sample_metrics for p in periods])
        
        # Calculate consistency score
        consistency_score = self._calculate_consistency_score(periods)
        
        # Detect overfitting
        overfitting_analysis = self.detect_overfitting_from_periods(periods)
        
        result = WalkForwardResult(
            periods=periods,
            avg_in_sample_performance=avg_in_sample,
            avg_out_sample_performance=avg_out_sample,
            consistency_score=consistency_score,
            overfitting_detected=overfitting_analysis.is_overfitted
        )
        
        log.info(f"Walk-forward complete: {len(periods)} periods, "
                f"Overfitting: {overfitting_analysis.is_overfitted}")
        
        return result

    
    def _average_metrics(self, metrics_list: List[PerformanceMetrics]) -> PerformanceMetrics:
        """Calculate average of multiple performance metrics."""
        if not metrics_list:
            return PerformanceMetrics(
                win_rate=0, profit_factor=0, sharpe_ratio=0,
                max_drawdown=0, avg_rr=0, expectancy=0,
                total_return=0, total_trades=0, winning_trades=0,
                losing_trades=0, avg_win=0, avg_loss=0,
                max_consecutive_wins=0, max_consecutive_losses=0
            )
        
        return PerformanceMetrics(
            win_rate=np.mean([m.win_rate for m in metrics_list]),
            profit_factor=np.mean([m.profit_factor for m in metrics_list]),
            sharpe_ratio=np.mean([m.sharpe_ratio for m in metrics_list]),
            max_drawdown=np.mean([m.max_drawdown for m in metrics_list]),
            avg_rr=np.mean([m.avg_rr for m in metrics_list]),
            expectancy=np.mean([m.expectancy for m in metrics_list]),
            total_return=np.mean([m.total_return for m in metrics_list]),
            total_trades=int(np.sum([m.total_trades for m in metrics_list])),
            winning_trades=int(np.sum([m.winning_trades for m in metrics_list])),
            losing_trades=int(np.sum([m.losing_trades for m in metrics_list])),
            avg_win=np.mean([m.avg_win for m in metrics_list]),
            avg_loss=np.mean([m.avg_loss for m in metrics_list]),
            max_consecutive_wins=int(np.max([m.max_consecutive_wins for m in metrics_list])),
            max_consecutive_losses=int(np.max([m.max_consecutive_losses for m in metrics_list]))
        )
    
    def _calculate_consistency_score(self, periods: List[WalkForwardPeriod]) -> float:
        """
        Calculate consistency score (0-100) across walk-forward periods.
        
        Higher score = more consistent performance across periods.
        """
        if not periods:
            return 0.0
        
        # Calculate variance in win rates
        win_rates = [p.out_sample_metrics.win_rate for p in periods]
        win_rate_std = np.std(win_rates)
        
        # Calculate variance in returns
        returns = [p.out_sample_metrics.total_return for p in periods]
        return_std = np.std(returns)
        
        # Lower variance = higher consistency
        # Normalize to 0-100 scale
        consistency = 100 - min(win_rate_std + return_std / 10, 100)
        
        return max(0, consistency)
    
    def detect_overfitting(self, wf_result: WalkForwardResult) -> OverfittingAnalysis:
        """
        Detect overfitting by comparing in-sample vs out-of-sample.
        
        Overfitting if out-of-sample <70% of in-sample performance.
        
        Args:
            wf_result: Walk-forward result
            
        Returns:
            OverfittingAnalysis
        """
        in_sample_wr = wf_result.avg_in_sample_performance.win_rate
        out_sample_wr = wf_result.avg_out_sample_performance.win_rate
        
        performance_ratio = out_sample_wr / in_sample_wr if in_sample_wr > 0 else 0
        
        is_overfitted = performance_ratio < self.config["overfitting_threshold"]
        
        if is_overfitted:
            recommendation = (
                f"Strategy appears overfitted. Out-of-sample performance "
                f"({out_sample_wr:.1f}%) is only {performance_ratio*100:.1f}% of "
                f"in-sample ({in_sample_wr:.1f}%). Consider simplifying strategy."
            )
        else:
            recommendation = (
                f"Strategy shows good generalization. Out-of-sample performance "
                f"({out_sample_wr:.1f}%) is {performance_ratio*100:.1f}% of "
                f"in-sample ({in_sample_wr:.1f}%)."
            )
        
        return OverfittingAnalysis(
            is_overfitted=is_overfitted,
            in_sample_win_rate=in_sample_wr,
            out_sample_win_rate=out_sample_wr,
            performance_ratio=performance_ratio,
            recommendation=recommendation
        )
    
    def detect_overfitting_from_periods(self, periods: List[WalkForwardPeriod]) -> OverfittingAnalysis:
        """Detect overfitting from walk-forward periods."""
        avg_in_sample = self._average_metrics([p.in_sample_metrics for p in periods])
        avg_out_sample = self._average_metrics([p.out_sample_metrics for p in periods])
        
        wf_result = WalkForwardResult(
            periods=periods,
            avg_in_sample_performance=avg_in_sample,
            avg_out_sample_performance=avg_out_sample,
            consistency_score=0,
            overfitting_detected=False
        )
        
        return self.detect_overfitting(wf_result)

    
    def optimize_parameters(
        self,
        param_grid: Dict[str, List],
        base_config: Dict,
        start_date: datetime,
        end_date: datetime,
        optimization_method: str = "grid",
        symbols: List[str] = None
    ) -> OptimizationResult:
        """
        Optimize strategy parameters.
        
        Methods:
        - grid: Grid search (exhaustive)
        - bayesian: Bayesian optimization (not implemented yet)
        
        Args:
            param_grid: Dict of parameter names to lists of values
            base_config: Base strategy configuration
            start_date: Optimization start date
            end_date: Optimization end date
            optimization_method: Optimization method
            symbols: List of symbols to test
            
        Returns:
            OptimizationResult with best parameters
        """
        import time
        start_time = time.time()
        
        log.info(f"Starting parameter optimization using {optimization_method} search")
        
        if optimization_method == "grid":
            result = self._grid_search(param_grid, base_config, start_date, end_date, symbols)
        elif optimization_method == "bayesian":
            log.warning("Bayesian optimization not implemented yet, falling back to grid search")
            result = self._grid_search(param_grid, base_config, start_date, end_date, symbols)
        else:
            raise ValueError(f"Unknown optimization method: {optimization_method}")
        
        optimization_time = time.time() - start_time
        result.optimization_time_seconds = optimization_time
        
        log.info(f"Optimization complete in {optimization_time:.1f}s. "
                f"Best score: {result.best_score:.2f}")
        
        return result
    
    def _grid_search(
        self,
        param_grid: Dict[str, List],
        base_config: Dict,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str]
    ) -> OptimizationResult:
        """Perform grid search optimization."""
        from itertools import product
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        log.info(f"Testing {len(combinations)} parameter combinations")
        
        all_results = []
        best_score = -float('inf')
        best_params = None
        
        for i, combo in enumerate(combinations):
            # Create config with current parameters
            config = base_config.copy()
            params = dict(zip(param_names, combo))
            config.update(params)
            
            # Run backtest
            try:
                result = self.run_backtest(config, start_date, end_date, symbols)
                
                if result:
                    # Score based on Sharpe Ratio (can be customized)
                    score = result.metrics.sharpe_ratio
                    all_results.append((params, score))
                    
                    if score > best_score:
                        best_score = score
                        best_params = params
                        log.info(f"New best: {params} -> Score: {score:.3f}")
                
            except Exception as e:
                log.error(f"Error testing params {params}: {e}")
            
            if (i + 1) % 10 == 0:
                log.info(f"Progress: {i+1}/{len(combinations)} combinations tested")
        
        return OptimizationResult(
            best_params=best_params or {},
            best_score=best_score,
            all_results=all_results,
            optimization_time_seconds=0  # Will be set by caller
        )

    
    def generate_report(self, result: BacktestResult, output_path: str = None) -> Dict:
        """
        Generate detailed backtest report with charts.
        
        Args:
            result: Backtest result
            output_path: Optional path to save report
            
        Returns:
            Report dict with summary and chart data
        """
        log.info("Generating backtest report")
        
        report = {
            "summary": {
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
                "total_trades": result.total_trades,
                "win_rate": f"{result.metrics.win_rate:.2f}%",
                "profit_factor": f"{result.metrics.profit_factor:.2f}",
                "sharpe_ratio": f"{result.metrics.sharpe_ratio:.2f}",
                "max_drawdown": f"{result.metrics.max_drawdown:.2f}%",
                "total_return": f"{result.metrics.total_return:.2f}%",
                "avg_rr": f"{result.metrics.avg_rr:.2f}",
                "expectancy": f"${result.metrics.expectancy:.2f}",
            },
            "trades": {
                "winning_trades": result.metrics.winning_trades,
                "losing_trades": result.metrics.losing_trades,
                "avg_win": f"${result.metrics.avg_win:.2f}",
                "avg_loss": f"${result.metrics.avg_loss:.2f}",
                "max_consecutive_wins": result.metrics.max_consecutive_wins,
                "max_consecutive_losses": result.metrics.max_consecutive_losses,
            },
            "equity_curve": [
                {"timestamp": ts.isoformat(), "equity": eq}
                for ts, eq in result.equity_curve
            ],
            "drawdown_curve": [
                {"timestamp": ts.isoformat(), "drawdown": dd}
                for ts, dd in result.drawdown_curve
            ],
            "trade_distribution": self._analyze_trade_distribution(result.trades),
        }
        
        # Save to file if path provided
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    json.dump(report, f, indent=2)
                log.info(f"Report saved to {output_path}")
            except Exception as e:
                log.error(f"Failed to save report: {e}")
        
        return report
    
    def _analyze_trade_distribution(self, trades: List[TradeOutcome]) -> Dict:
        """Analyze trade distribution for report."""
        if not trades:
            return {}
        
        # R:R distribution
        rr_buckets = defaultdict(int)
        for trade in trades:
            if trade.rr_achieved < 0.5:
                rr_buckets["<0.5"] += 1
            elif trade.rr_achieved < 1.0:
                rr_buckets["0.5-1.0"] += 1
            elif trade.rr_achieved < 2.0:
                rr_buckets["1.0-2.0"] += 1
            elif trade.rr_achieved < 3.0:
                rr_buckets["2.0-3.0"] += 1
            else:
                rr_buckets[">3.0"] += 1
        
        # Duration distribution
        duration_buckets = defaultdict(int)
        for trade in trades:
            if trade.duration_hours < 1:
                duration_buckets["<1h"] += 1
            elif trade.duration_hours < 4:
                duration_buckets["1-4h"] += 1
            elif trade.duration_hours < 24:
                duration_buckets["4-24h"] += 1
            else:
                duration_buckets[">24h"] += 1
        
        # Exit reason distribution
        exit_reasons = defaultdict(int)
        for trade in trades:
            exit_reasons[trade.exit_reason] += 1
        
        return {
            "rr_distribution": dict(rr_buckets),
            "duration_distribution": dict(duration_buckets),
            "exit_reasons": dict(exit_reasons),
        }
