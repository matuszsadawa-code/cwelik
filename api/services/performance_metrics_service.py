"""
Performance Metrics Service for OpenClaw Trading Dashboard

Calculates key performance metrics from signal_outcomes and equity_snapshots tables
and broadcasts updates via WebSocket every 30 seconds.

Features:
- Calculate win rate from signal_outcomes table
- Calculate profit factor (sum of wins / abs(sum of losses))
- Calculate Sharpe ratio from returns series
- Calculate current drawdown and max drawdown from equity_snapshots
- Calculate daily, weekly, monthly PnL aggregations
- Broadcast performance_update messages via WebSocket
- Real-time metrics updates every 30 seconds
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
import math

from storage.database import Database
from api.services.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)


class PerformanceMetricsService:
    """
    Service for calculating and broadcasting performance metrics.
    
    Responsibilities:
    - Query signal_outcomes table for completed trades every 30 seconds
    - Calculate win rate: (winning trades / total trades) × 100
    - Calculate profit factor: sum(winning P&L) / abs(sum(losing P&L))
    - Calculate Sharpe ratio: (mean return - risk-free rate) / std(returns) × √252
    - Query equity_snapshots table for equity curve data
    - Calculate current drawdown from peak equity
    - Calculate max drawdown (peak-to-trough decline)
    - Aggregate P&L by day, week, month from signal_outcomes
    - Count total trades and active positions
    - Broadcast performance_update messages via WebSocket
    """

    
    def __init__(self, connection_manager: ConnectionManager, database: Database = None):
        """
        Initialize performance metrics service.
        
        Args:
            connection_manager: WebSocket connection manager for broadcasting
            database: Database instance (creates new if None)
        """
        self.connection_manager = connection_manager
        self.database = database or Database()
        
        # Service state
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Cached metrics
        self.cached_metrics: Optional[Dict] = None
        
        logger.info("PerformanceMetricsService initialized")
    
    async def start(self):
        """Start the performance metrics service background task."""
        if self.running:
            logger.warning("PerformanceMetricsService already running")
            return
        
        self.running = True
        
        # Start background task
        self.task = asyncio.create_task(self._metrics_calculation_loop())
        
        logger.info("PerformanceMetricsService started")
    
    async def stop(self):
        """Stop the performance metrics service and cleanup."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel background task
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("PerformanceMetricsService stopped")

    
    async def _metrics_calculation_loop(self):
        """
        Background task: Calculate performance metrics every 30 seconds.
        
        Queries database, calculates all metrics, and broadcasts updates.
        """
        logger.info("Performance metrics calculation loop started (30s interval)")
        
        while self.running:
            try:
                await self._calculate_and_broadcast_metrics()
                await asyncio.sleep(30.0)  # 30 second interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics calculation loop: {e}", exc_info=True)
                await asyncio.sleep(30.0)  # Continue on error
    
    async def _calculate_and_broadcast_metrics(self):
        """
        Calculate all performance metrics and broadcast via WebSocket.
        
        Queries signal_outcomes and equity_snapshots tables, calculates metrics,
        and broadcasts performance_update message.
        """
        try:
            # Get completed trades from signal_outcomes table
            outcomes = self._get_signal_outcomes()
            
            # Get equity curve data from equity_snapshots table
            equity_data = self._get_equity_snapshots()
            
            # Get active positions count
            active_positions = self._get_active_positions_count()
            
            # Calculate metrics
            metrics = {
                "winRate": self._calculate_win_rate(outcomes),
                "profitFactor": self._calculate_profit_factor(outcomes),
                "sharpeRatio": self._calculate_sharpe_ratio(outcomes),
                "maxDrawdown": self._calculate_max_drawdown(equity_data),
                "currentDrawdown": self._calculate_current_drawdown(equity_data),
                "dailyPnL": self._calculate_daily_pnl(outcomes),
                "weeklyPnL": self._calculate_weekly_pnl(outcomes),
                "monthlyPnL": self._calculate_monthly_pnl(outcomes),
                "totalTrades": len(outcomes),
                "activePositions": active_positions,
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            
            # Cache metrics
            self.cached_metrics = metrics
            
            # Broadcast to WebSocket clients
            await self._broadcast_metrics(metrics)
            
            logger.debug(
                f"Metrics calculated: WinRate={metrics['winRate']:.2f}%, "
                f"ProfitFactor={metrics['profitFactor']:.2f}, "
                f"Sharpe={metrics['sharpeRatio']:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}", exc_info=True)

    
    def _get_signal_outcomes(self) -> List[Dict]:
        """
        Query all signal outcomes from database.
        
        Returns:
            list: List of signal outcome dictionaries
        """
        try:
            conn = self.database._get_conn()
            rows = conn.execute("""
                SELECT * FROM signal_outcomes
                WHERE outcome IS NOT NULL
                ORDER BY created_at DESC
            """).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying signal outcomes: {e}")
            return []
    
    def _get_equity_snapshots(self) -> List[Dict]:
        """
        Query equity snapshots from database.
        
        Returns:
            list: List of equity snapshot dictionaries
        """
        try:
            return self.database.get_equity_history(limit=1000)
        except Exception as e:
            logger.error(f"Error querying equity snapshots: {e}")
            return []
    
    def _get_active_positions_count(self) -> int:
        """
        Count active positions from executions table.
        
        Returns:
            int: Number of active positions
        """
        try:
            conn = self.database._get_conn()
            row = conn.execute("""
                SELECT COUNT(*) as count FROM executions
                WHERE status = 'OPEN'
            """).fetchone()
            return dict(row)["count"] if row else 0
        except Exception as e:
            logger.error(f"Error counting active positions: {e}")
            return 0

    
    def _calculate_win_rate(self, outcomes: List[Dict]) -> float:
        """
        Calculate win rate: (winning trades / total trades) × 100.
        
        Args:
            outcomes: List of signal outcome dictionaries
            
        Returns:
            float: Win rate as percentage (0-100)
        """
        if not outcomes:
            return 0.0
        
        wins = sum(1 for o in outcomes if o.get("outcome") == "WIN")
        total = len(outcomes)
        
        return (wins / total * 100) if total > 0 else 0.0
    
    def _calculate_profit_factor(self, outcomes: List[Dict]) -> float:
        """
        Calculate profit factor: sum(winning P&L) / abs(sum(losing P&L)).
        
        Args:
            outcomes: List of signal outcome dictionaries
            
        Returns:
            float: Profit factor (>1 is profitable, <1 is losing)
        """
        if not outcomes:
            return 0.0
        
        winning_pnl = sum(o.get("pnl_pct", 0) for o in outcomes if o.get("pnl_pct", 0) > 0)
        losing_pnl = sum(o.get("pnl_pct", 0) for o in outcomes if o.get("pnl_pct", 0) < 0)
        
        if losing_pnl == 0:
            return winning_pnl if winning_pnl > 0 else 0.0
        
        return winning_pnl / abs(losing_pnl)
    
    def _calculate_sharpe_ratio(self, outcomes: List[Dict], risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio: (mean return - risk-free rate) / std(returns) × √252.
        
        Annualized Sharpe ratio assuming 252 trading days per year.
        
        Args:
            outcomes: List of signal outcome dictionaries
            risk_free_rate: Annual risk-free rate (default: 0.0)
            
        Returns:
            float: Sharpe ratio
        """
        if not outcomes or len(outcomes) < 2:
            return 0.0
        
        # Extract returns (pnl_pct as decimal)
        returns = [o.get("pnl_pct", 0) / 100 for o in outcomes if o.get("pnl_pct") is not None]
        
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculate mean and standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Annualize: multiply by √252 (trading days per year)
        sharpe = (mean_return - risk_free_rate) / std_dev * math.sqrt(252)
        
        return sharpe

    
    def _calculate_max_drawdown(self, equity_data: List[Dict]) -> float:
        """
        Calculate maximum drawdown (peak-to-trough decline) from equity curve.
        
        Max Drawdown = (Trough Value - Peak Value) / Peak Value × 100
        
        Args:
            equity_data: List of equity snapshot dictionaries
            
        Returns:
            float: Maximum drawdown as percentage (negative value)
        """
        if not equity_data or len(equity_data) < 2:
            return 0.0
        
        # Extract equity values
        equity_values = [e.get("equity", 0) for e in equity_data]
        
        if not equity_values:
            return 0.0
        
        max_drawdown = 0.0
        peak = equity_values[0]
        
        for equity in equity_values:
            # Update peak if new high
            if equity > peak:
                peak = equity
            
            # Calculate drawdown from peak
            if peak > 0:
                drawdown = (equity - peak) / peak * 100
                max_drawdown = min(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_current_drawdown(self, equity_data: List[Dict]) -> float:
        """
        Calculate current drawdown from peak equity.
        
        Current Drawdown = (Current Equity - Peak Equity) / Peak Equity × 100
        
        Args:
            equity_data: List of equity snapshot dictionaries
            
        Returns:
            float: Current drawdown as percentage (negative value or 0)
        """
        if not equity_data:
            return 0.0
        
        # Extract equity values
        equity_values = [e.get("equity", 0) for e in equity_data]
        
        if not equity_values:
            return 0.0
        
        # Find peak equity
        peak_equity = max(equity_values)
        
        # Get current equity (last value)
        current_equity = equity_values[-1]
        
        if peak_equity == 0:
            return 0.0
        
        # Calculate current drawdown
        drawdown = (current_equity - peak_equity) / peak_equity * 100
        
        return min(drawdown, 0.0)  # Return 0 if at peak, negative otherwise

    
    def _calculate_daily_pnl(self, outcomes: List[Dict]) -> float:
        """
        Calculate P&L for the current day.
        
        Args:
            outcomes: List of signal outcome dictionaries
            
        Returns:
            float: Daily P&L as percentage
        """
        if not outcomes:
            return 0.0
        
        # Get today's date
        today = datetime.now(timezone.utc).date()
        
        # Filter outcomes from today
        daily_pnl = 0.0
        for outcome in outcomes:
            closed_at = outcome.get("closed_at")
            if closed_at:
                try:
                    closed_date = datetime.fromisoformat(closed_at.replace('Z', '+00:00')).date()
                    if closed_date == today:
                        daily_pnl += outcome.get("pnl_pct", 0)
                except Exception as e:
                    logger.debug(f"Error parsing closed_at date: {e}")
        
        return daily_pnl
    
    def _calculate_weekly_pnl(self, outcomes: List[Dict]) -> float:
        """
        Calculate P&L for the current week (last 7 days).
        
        Args:
            outcomes: List of signal outcome dictionaries
            
        Returns:
            float: Weekly P&L as percentage
        """
        if not outcomes:
            return 0.0
        
        # Get date 7 days ago
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Filter outcomes from last 7 days
        weekly_pnl = 0.0
        for outcome in outcomes:
            closed_at = outcome.get("closed_at")
            if closed_at:
                try:
                    closed_time = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                    if closed_time >= week_ago:
                        weekly_pnl += outcome.get("pnl_pct", 0)
                except Exception as e:
                    logger.debug(f"Error parsing closed_at date: {e}")
        
        return weekly_pnl
    
    def _calculate_monthly_pnl(self, outcomes: List[Dict]) -> float:
        """
        Calculate P&L for the current month (last 30 days).
        
        Args:
            outcomes: List of signal outcome dictionaries
            
        Returns:
            float: Monthly P&L as percentage
        """
        if not outcomes:
            return 0.0
        
        # Get date 30 days ago
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Filter outcomes from last 30 days
        monthly_pnl = 0.0
        for outcome in outcomes:
            closed_at = outcome.get("closed_at")
            if closed_at:
                try:
                    closed_time = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                    if closed_time >= month_ago:
                        monthly_pnl += outcome.get("pnl_pct", 0)
                except Exception as e:
                    logger.debug(f"Error parsing closed_at date: {e}")
        
        return monthly_pnl

    
    async def _broadcast_metrics(self, metrics: Dict):
        """
        Broadcast performance metrics update to all WebSocket clients.
        
        Args:
            metrics: Performance metrics dictionary
        """
        message = {
            "type": "performance_update",
            "data": {
                "winRate": round(metrics["winRate"], 2),
                "profitFactor": round(metrics["profitFactor"], 2),
                "sharpeRatio": round(metrics["sharpeRatio"], 2),
                "maxDrawdown": round(metrics["maxDrawdown"], 2),
                "currentDrawdown": round(metrics["currentDrawdown"], 2),
                "dailyPnL": round(metrics["dailyPnL"], 2),
                "weeklyPnL": round(metrics["weeklyPnL"], 2),
                "monthlyPnL": round(metrics["monthlyPnL"], 2),
                "totalTrades": metrics["totalTrades"],
                "activePositions": metrics["activePositions"],
                "timestamp": metrics["timestamp"],
            }
        }
        
        # Broadcast to all clients subscribed to performance channel
        await self.connection_manager.broadcast(message, channel="performance")
    
    def get_cached_metrics(self) -> Optional[Dict]:
        """
        Get cached performance metrics.
        
        Returns:
            dict: Cached metrics or None if not available
        """
        return self.cached_metrics.copy() if self.cached_metrics else None
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including running state
        """
        return {
            "running": self.running,
            "has_cached_metrics": self.cached_metrics is not None,
        }
