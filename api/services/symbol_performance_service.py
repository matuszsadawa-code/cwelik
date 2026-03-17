"""
Symbol Performance Service for OpenClaw Trading Dashboard

Calculates detailed performance statistics per symbol from signal_outcomes table,
including win rate, profit factor, average PnL, total PnL, best/worst trades,
average hold time, and trade count.

Features:
- Calculate win rate per symbol from signal_outcomes table
- Calculate profit factor per symbol (sum of wins / abs(sum of losses))
- Calculate average PnL and total PnL per symbol
- Identify best and worst trade per symbol
- Calculate average hold time per symbol
- Calculate trade count per symbol
- Return data suitable for sortable table display
"""

import logging
from typing import Dict, List
from datetime import datetime, timezone
from collections import defaultdict

from storage.database import Database

logger = logging.getLogger(__name__)


class SymbolPerformanceService:
    """
    Service for calculating per-symbol performance statistics.
    
    Responsibilities:
    - Query signal_outcomes table for completed trades grouped by symbol
    - Calculate win rate per symbol: (winning trades / total trades) × 100
    - Calculate profit factor per symbol: sum(wins) / abs(sum(losses))
    - Calculate average PnL and total PnL per symbol
    - Identify best and worst trade per symbol
    - Calculate average hold time per symbol
    - Calculate trade count per symbol
    """
    
    def __init__(self, database: Database = None):
        """
        Initialize symbol performance service.
        
        Args:
            database: Database instance (creates new if None)
        """
        self.database = database or Database()
        logger.info("SymbolPerformanceService initialized")
    
    def get_symbol_performance(self) -> Dict:
        """
        Get performance statistics for all symbols.
        
        Returns:
            dict: Symbol performance data including:
                - symbols: List of symbol performance dictionaries
                - Each symbol dict contains:
                    - symbol: Symbol name
                    - totalTrades: Total number of trades
                    - winRate: Win rate percentage
                    - profitFactor: Profit factor (wins / losses)
                    - avgPnL: Average PnL percentage
                    - totalPnL: Total PnL percentage
                    - bestTrade: Best trade PnL percentage
                    - worstTrade: Worst trade PnL percentage
                    - avgHoldTime: Average hold time in minutes
        """
        try:
            # Get completed trades from database grouped by symbol
            trades_by_symbol = self._get_trades_by_symbol()
            
            if not trades_by_symbol:
                logger.warning("No completed trades available")
                return {"symbols": []}
            
            # Calculate performance metrics for each symbol
            symbol_metrics = []
            for symbol, trades in trades_by_symbol.items():
                metrics = self._calculate_symbol_metrics(symbol, trades)
                symbol_metrics.append(metrics)
            
            # Sort by total PnL descending (best performers first)
            symbol_metrics.sort(key=lambda x: x["totalPnL"], reverse=True)
            
            return {"symbols": symbol_metrics}
            
        except Exception as e:
            logger.error(f"Error generating symbol performance: {e}", exc_info=True)
            return {"symbols": []}
    
    def _get_trades_by_symbol(self) -> Dict[str, List[Dict]]:
        """
        Query completed trades from database grouped by symbol.
        
        Returns:
            dict: Dictionary mapping symbol to list of trade dictionaries
        """
        try:
            conn = self.database._get_conn()
            
            # Query all completed trades with symbol information
            rows = conn.execute("""
                SELECT 
                    s.symbol,
                    so.outcome,
                    so.pnl_pct,
                    so.duration_minutes,
                    so.closed_at
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE so.closed_at IS NOT NULL
                AND so.outcome IS NOT NULL
                ORDER BY s.symbol, so.closed_at ASC
            """).fetchall()
            
            # Group trades by symbol
            trades_by_symbol = defaultdict(list)
            for row in rows:
                trade = dict(row)
                symbol = trade["symbol"]
                trades_by_symbol[symbol].append(trade)
            
            return dict(trades_by_symbol)
            
        except Exception as e:
            logger.error(f"Error querying trades by symbol: {e}")
            return {}
    
    def _calculate_symbol_metrics(self, symbol: str, trades: List[Dict]) -> Dict:
        """
        Calculate performance metrics for a single symbol.
        
        Args:
            symbol: Symbol name
            trades: List of trade dictionaries for this symbol
            
        Returns:
            dict: Symbol performance metrics
        """
        total_trades = len(trades)
        
        # Separate winning and losing trades
        winning_trades = [t for t in trades if t.get("outcome") == "WIN"]
        losing_trades = [t for t in trades if t.get("outcome") == "LOSS"]
        
        # Calculate win rate
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate profit factor
        total_wins = sum(t.get("pnl_pct", 0) for t in winning_trades)
        total_losses = sum(t.get("pnl_pct", 0) for t in losing_trades)
        profit_factor = (total_wins / abs(total_losses)) if total_losses != 0 else (float('inf') if total_wins > 0 else 0)
        
        # Calculate average and total PnL
        all_pnls = [t.get("pnl_pct", 0) for t in trades]
        avg_pnl = sum(all_pnls) / len(all_pnls) if all_pnls else 0
        total_pnl = sum(all_pnls)
        
        # Identify best and worst trades
        best_trade = max(all_pnls) if all_pnls else 0
        worst_trade = min(all_pnls) if all_pnls else 0
        
        # Calculate average hold time
        durations = [t.get("duration_minutes", 0) for t in trades if t.get("duration_minutes") is not None]
        avg_hold_time = sum(durations) / len(durations) if durations else 0
        
        return {
            "symbol": symbol,
            "totalTrades": total_trades,
            "winRate": round(win_rate, 2),
            "profitFactor": round(profit_factor, 2) if profit_factor != float('inf') else 999.99,
            "avgPnL": round(avg_pnl, 2),
            "totalPnL": round(total_pnl, 2),
            "bestTrade": round(best_trade, 2),
            "worstTrade": round(worst_trade, 2),
            "avgHoldTime": round(avg_hold_time, 2)
        }
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including data availability
        """
        try:
            # Check if we have any completed trades
            conn = self.database._get_conn()
            row = conn.execute("""
                SELECT COUNT(DISTINCT s.symbol) as symbol_count,
                       COUNT(*) as trade_count
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE so.closed_at IS NOT NULL
                AND so.outcome IS NOT NULL
            """).fetchone()
            
            result = dict(row) if row else {"symbol_count": 0, "trade_count": 0}
            
            return {
                "initialized": True,
                "symbol_count": result["symbol_count"],
                "trade_count": result["trade_count"],
                "has_data": result["trade_count"] > 0
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "symbol_count": 0,
                "trade_count": 0,
                "has_data": False,
                "error": str(e)
            }
