"""
Risk Metrics Service for OpenClaw Trading Dashboard

Calculates risk-adjusted return metrics including Sharpe ratio, Sortino ratio,
Calmar ratio, maximum drawdown, average drawdown duration, rolling Sharpe ratio,
and drawdown duration histogram.

Features:
- Calculate Sharpe ratio from returns series
- Calculate Sortino ratio using downside deviation
- Calculate Calmar ratio (return / max drawdown)
- Calculate maximum drawdown
- Calculate average drawdown duration
- Generate rolling Sharpe ratio time series (30-day window)
- Generate drawdown duration histogram data
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import math

from storage.database import Database

logger = logging.getLogger(__name__)


class RiskMetricsService:
    """
    Service for calculating risk-adjusted return metrics.
    
    Responsibilities:
    - Query signal_outcomes and equity_snapshots tables for returns data
    - Calculate Sharpe ratio from returns series
    - Calculate Sortino ratio using downside deviation
    - Calculate Calmar ratio (return / max drawdown)
    - Calculate maximum drawdown and average drawdown duration
    - Generate rolling Sharpe ratio time series (30-day window)
    - Generate drawdown duration histogram data
    """
    
    def __init__(self, database: Database = None):
        """
        Initialize risk metrics service.
        
        Args:
            database: Database instance (creates new if None)
        """
        self.database = database or Database()
        logger.info("RiskMetricsService initialized")
    
    def get_risk_metrics(self) -> Dict:
        """
        Get comprehensive risk-adjusted return metrics.
        
        Returns:
            dict: Risk metrics including:
                - sharpeRatio: Annualized Sharpe ratio
                - sortinoRatio: Sortino ratio (downside deviation)
                - calmarRatio: Calmar ratio (return / max drawdown)
                - maxDrawdown: Maximum drawdown percentage
                - avgDrawdownDuration: Average drawdown duration in minutes
                - rollingSharpe: List of rolling Sharpe ratio data points
                - drawdownHistogram: Histogram of drawdown durations
        """
        try:
            # Get returns series from signal outcomes
            returns = self._get_returns_series()
            
            if not returns:
                logger.warning("No returns data available")
                return self._empty_metrics()
            
            # Calculate risk metrics
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            sortino_ratio = self._calculate_sortino_ratio(returns)
            
            # Get drawdown metrics from equity curve
            max_drawdown, avg_dd_duration, drawdown_periods = self._calculate_drawdown_metrics()
            
            # Calculate Calmar ratio
            total_return = sum(r[1] for r in returns)  # Extract return values from tuples
            calmar_ratio = self._calculate_calmar_ratio(total_return, max_drawdown)
            
            # Generate rolling Sharpe ratio (30-day window)
            rolling_sharpe = self._calculate_rolling_sharpe(returns, window_days=30)
            
            # Generate drawdown duration histogram
            drawdown_histogram = self._generate_drawdown_histogram(drawdown_periods)
            
            return {
                "sharpeRatio": round(sharpe_ratio, 2),
                "sortinoRatio": round(sortino_ratio, 2),
                "calmarRatio": round(calmar_ratio, 2),
                "maxDrawdown": round(max_drawdown, 2),
                "avgDrawdownDuration": round(avg_dd_duration, 2),
                "rollingSharpe": rolling_sharpe,
                "drawdownHistogram": drawdown_histogram
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}", exc_info=True)
            return self._empty_metrics()
    
    def _get_returns_series(self) -> List[Tuple[datetime, float]]:
        """
        Get returns series from signal_outcomes table.
        
        Returns:
            list: List of (timestamp, return_pct) tuples sorted by time
        """
        try:
            conn = self.database._get_conn()
            
            # Query completed trades with PnL
            rows = conn.execute("""
                SELECT closed_at, pnl_pct
                FROM signal_outcomes
                WHERE closed_at IS NOT NULL
                AND pnl_pct IS NOT NULL
                ORDER BY closed_at ASC
            """).fetchall()
            
            returns = []
            for row in rows:
                try:
                    timestamp = datetime.fromisoformat(row["closed_at"])
                    pnl_pct = float(row["pnl_pct"])
                    returns.append((timestamp, pnl_pct))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid return data: {e}")
                    continue
            
            return returns
            
        except Exception as e:
            logger.error(f"Error querying returns series: {e}")
            return []
    
    def _calculate_sharpe_ratio(self, returns: List[Tuple[datetime, float]]) -> float:
        """
        Calculate annualized Sharpe ratio.
        
        Formula: (mean_return - risk_free_rate) / std_dev * sqrt(252)
        
        Args:
            returns: List of (timestamp, return_pct) tuples
            
        Returns:
            float: Annualized Sharpe ratio
        """
        if not returns:
            return 0.0
        
        # Extract return values
        return_values = [r[1] for r in returns]
        
        if len(return_values) < 2:
            return 0.0
        
        # Calculate mean and standard deviation
        mean_return = sum(return_values) / len(return_values)
        variance = sum((r - mean_return) ** 2 for r in return_values) / len(return_values)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Assume risk-free rate of 0 for crypto
        risk_free_rate = 0.0
        
        # Annualize using sqrt(252) for trading days
        sharpe_ratio = (mean_return - risk_free_rate) / std_dev * math.sqrt(252)
        
        return sharpe_ratio
    
    def _calculate_sortino_ratio(self, returns: List[Tuple[datetime, float]]) -> float:
        """
        Calculate Sortino ratio using downside deviation.
        
        Formula: (mean_return - risk_free_rate) / downside_deviation * sqrt(252)
        
        Args:
            returns: List of (timestamp, return_pct) tuples
            
        Returns:
            float: Annualized Sortino ratio
        """
        if not returns:
            return 0.0
        
        # Extract return values
        return_values = [r[1] for r in returns]
        
        if len(return_values) < 2:
            return 0.0
        
        # Calculate mean return
        mean_return = sum(return_values) / len(return_values)
        
        # Calculate downside deviation (only negative returns)
        downside_returns = [r for r in return_values if r < 0]
        
        if not downside_returns:
            # No downside, return high Sortino ratio
            return 999.99
        
        downside_variance = sum(r ** 2 for r in downside_returns) / len(return_values)
        downside_deviation = math.sqrt(downside_variance)
        
        if downside_deviation == 0:
            return 999.99
        
        # Assume risk-free rate of 0 for crypto
        risk_free_rate = 0.0
        
        # Annualize using sqrt(252)
        sortino_ratio = (mean_return - risk_free_rate) / downside_deviation * math.sqrt(252)
        
        return sortino_ratio
    
    def _calculate_drawdown_metrics(self) -> Tuple[float, float, List[Dict]]:
        """
        Calculate maximum drawdown and average drawdown duration from equity curve.
        
        Returns:
            tuple: (max_drawdown_pct, avg_duration_minutes, drawdown_periods)
        """
        try:
            conn = self.database._get_conn()
            
            # Query equity snapshots
            rows = conn.execute("""
                SELECT timestamp, equity
                FROM equity_snapshots
                ORDER BY timestamp ASC
            """).fetchall()
            
            if not rows:
                logger.warning("No equity snapshots available")
                return 0.0, 0.0, []
            
            # Build equity curve
            equity_curve = []
            for row in rows:
                try:
                    timestamp = datetime.fromisoformat(row["timestamp"])
                    equity = float(row["equity"])
                    equity_curve.append((timestamp, equity))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid equity data: {e}")
                    continue
            
            if len(equity_curve) < 2:
                return 0.0, 0.0, []
            
            # Calculate drawdowns
            drawdown_periods = []
            peak_equity = equity_curve[0][1]
            peak_time = equity_curve[0][0]
            in_drawdown = False
            drawdown_start = None
            max_drawdown_pct = 0.0
            
            for timestamp, equity in equity_curve:
                if equity > peak_equity:
                    # New peak
                    if in_drawdown:
                        # End of drawdown period
                        duration_minutes = (timestamp - drawdown_start).total_seconds() / 60
                        drawdown_periods.append({
                            "start": drawdown_start,
                            "end": timestamp,
                            "duration": duration_minutes,
                            "depth": ((peak_equity - trough_equity) / peak_equity * 100)
                        })
                        in_drawdown = False
                    
                    peak_equity = equity
                    peak_time = timestamp
                else:
                    # In drawdown
                    drawdown_pct = (peak_equity - equity) / peak_equity * 100
                    
                    if not in_drawdown and drawdown_pct > 0:
                        # Start of new drawdown
                        in_drawdown = True
                        drawdown_start = peak_time
                        trough_equity = equity
                    
                    if in_drawdown and equity < trough_equity:
                        trough_equity = equity
                    
                    if drawdown_pct > max_drawdown_pct:
                        max_drawdown_pct = drawdown_pct
            
            # Handle ongoing drawdown
            if in_drawdown:
                duration_minutes = (equity_curve[-1][0] - drawdown_start).total_seconds() / 60
                drawdown_periods.append({
                    "start": drawdown_start,
                    "end": equity_curve[-1][0],
                    "duration": duration_minutes,
                    "depth": ((peak_equity - trough_equity) / peak_equity * 100)
                })
            
            # Calculate average drawdown duration
            if drawdown_periods:
                avg_duration = sum(dd["duration"] for dd in drawdown_periods) / len(drawdown_periods)
            else:
                avg_duration = 0.0
            
            return max_drawdown_pct, avg_duration, drawdown_periods
            
        except Exception as e:
            logger.error(f"Error calculating drawdown metrics: {e}")
            return 0.0, 0.0, []
    
    def _calculate_calmar_ratio(self, total_return: float, max_drawdown: float) -> float:
        """
        Calculate Calmar ratio (return / max drawdown).
        
        Args:
            total_return: Total return percentage
            max_drawdown: Maximum drawdown percentage
            
        Returns:
            float: Calmar ratio
        """
        if max_drawdown == 0:
            return 999.99 if total_return > 0 else 0.0
        
        return total_return / max_drawdown
    
    def _calculate_rolling_sharpe(self, returns: List[Tuple[datetime, float]], 
                                   window_days: int = 30) -> List[Dict]:
        """
        Calculate rolling Sharpe ratio with specified window.
        
        Args:
            returns: List of (timestamp, return_pct) tuples
            window_days: Rolling window size in days
            
        Returns:
            list: List of {"timestamp": str, "sharpe": float} dictionaries
        """
        if len(returns) < 2:
            return []
        
        rolling_sharpe = []
        
        for i in range(len(returns)):
            # Get window of returns ending at current point
            window_end = returns[i][0]
            window_start = window_end - timedelta(days=window_days)
            
            # Filter returns within window
            window_returns = [(ts, ret) for ts, ret in returns[:i+1] 
                            if ts >= window_start]
            
            if len(window_returns) >= 2:
                sharpe = self._calculate_sharpe_ratio(window_returns)
                rolling_sharpe.append({
                    "timestamp": returns[i][0].isoformat(),
                    "sharpe": round(sharpe, 2)
                })
        
        return rolling_sharpe
    
    def _generate_drawdown_histogram(self, drawdown_periods: List[Dict]) -> Dict:
        """
        Generate histogram of drawdown durations.
        
        Args:
            drawdown_periods: List of drawdown period dictionaries
            
        Returns:
            dict: Histogram with buckets and counts
        """
        if not drawdown_periods:
            return {
                "buckets": [],
                "counts": []
            }
        
        # Define duration buckets (in minutes)
        buckets = [
            {"label": "<1h", "min": 0, "max": 60},
            {"label": "1-4h", "min": 60, "max": 240},
            {"label": "4-24h", "min": 240, "max": 1440},
            {"label": "1-7d", "min": 1440, "max": 10080},
            {"label": ">7d", "min": 10080, "max": float('inf')}
        ]
        
        # Count drawdowns in each bucket
        counts = [0] * len(buckets)
        
        for dd in drawdown_periods:
            duration = dd["duration"]
            for i, bucket in enumerate(buckets):
                if bucket["min"] <= duration < bucket["max"]:
                    counts[i] += 1
                    break
        
        return {
            "buckets": [b["label"] for b in buckets],
            "counts": counts
        }
    
    def _empty_metrics(self) -> Dict:
        """
        Return empty metrics structure.
        
        Returns:
            dict: Empty metrics with zero values
        """
        return {
            "sharpeRatio": 0.0,
            "sortinoRatio": 0.0,
            "calmarRatio": 0.0,
            "maxDrawdown": 0.0,
            "avgDrawdownDuration": 0.0,
            "rollingSharpe": [],
            "drawdownHistogram": {
                "buckets": [],
                "counts": []
            }
        }
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including data availability
        """
        try:
            # Check if we have returns data
            conn = self.database._get_conn()
            
            returns_row = conn.execute("""
                SELECT COUNT(*) as count
                FROM signal_outcomes
                WHERE closed_at IS NOT NULL
                AND pnl_pct IS NOT NULL
            """).fetchone()
            
            equity_row = conn.execute("""
                SELECT COUNT(*) as count
                FROM equity_snapshots
            """).fetchone()
            
            returns_count = returns_row["count"] if returns_row else 0
            equity_count = equity_row["count"] if equity_row else 0
            
            return {
                "initialized": True,
                "returns_count": returns_count,
                "equity_snapshots_count": equity_count,
                "has_data": returns_count > 0 and equity_count > 0
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "returns_count": 0,
                "equity_snapshots_count": 0,
                "has_data": False,
                "error": str(e)
            }
