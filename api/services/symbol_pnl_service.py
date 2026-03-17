"""
Symbol PnL Service for OpenClaw Trading Dashboard

Provides per-symbol PnL analysis including cumulative PnL and trade-by-trade data.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from storage.database import Database

logger = logging.getLogger(__name__)


class SymbolPnLService:
    """Service for calculating per-symbol PnL metrics and trade data"""
    
    def __init__(self, db: Database):
        self.db = db
        logger.info("SymbolPnLService initialized")
    
    def get_symbol_pnl(self, symbol: str) -> Dict[str, Any]:
        """
        Get PnL data for a specific symbol
        
        Args:
            symbol: Symbol name (e.g., "BTCUSDT")
            
        Returns:
            dict: Symbol PnL data including:
                - symbol: Symbol name
                - trades: List of trade data points
                - cumulativePnL: Cumulative PnL series
                - winRate: Win rate percentage
                - profitFactor: Profit factor
                - totalTrades: Total number of trades
                - totalPnL: Total PnL percentage
        """
        try:
            # Query all trades for this symbol
            query = """
                SELECT 
                    outcome_id,
                    signal_id,
                    outcome,
                    pnl_pct,
                    entry_price,
                    exit_price,
                    exit_reason,
                    mfe,
                    mae,
                    rr_achieved,
                    duration_minutes,
                    created_at,
                    closed_at
                FROM signal_outcomes
                WHERE signal_id IN (
                    SELECT signal_id FROM signals WHERE symbol = ?
                )
                ORDER BY closed_at ASC
            """
            
            trades_data = self.db.execute_query(query, (symbol,))
            
            if not trades_data:
                return {
                    "symbol": symbol,
                    "trades": [],
                    "cumulativePnL": [],
                    "winRate": 0,
                    "profitFactor": 0,
                    "totalTrades": 0,
                    "totalPnL": 0
                }
            
            # Process trades
            trades = []
            cumulative_pnl = 0
            winning_trades = 0
            total_wins = 0
            total_losses = 0
            
            for trade in trades_data:
                pnl = trade[3]  # pnl_pct
                outcome = trade[2]  # outcome
                closed_at = trade[12]  # closed_at
                
                cumulative_pnl += pnl
                
                if outcome == 'WIN':
                    winning_trades += 1
                    total_wins += pnl
                else:
                    total_losses += abs(pnl)
                
                # Convert timestamp to milliseconds
                if isinstance(closed_at, str):
                    closed_timestamp = int(datetime.fromisoformat(closed_at.replace('Z', '+00:00')).timestamp() * 1000)
                else:
                    closed_timestamp = int(closed_at * 1000) if closed_at else 0
                
                trades.append({
                    "tradeId": trade[0],  # outcome_id
                    "signalId": trade[1],  # signal_id
                    "outcome": outcome,
                    "pnl": pnl,
                    "cumulativePnL": cumulative_pnl,
                    "entryPrice": trade[4],  # entry_price
                    "exitPrice": trade[5],  # exit_price
                    "exitReason": trade[6],  # exit_reason
                    "mfe": trade[7],  # mfe
                    "mae": trade[8],  # mae
                    "rrAchieved": trade[9],  # rr_achieved
                    "duration": trade[10],  # duration_minutes
                    "timestamp": closed_timestamp
                })
            
            # Calculate metrics
            total_trades = len(trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (total_wins / total_losses) if total_losses > 0 else (total_wins if total_wins > 0 else 0)
            
            return {
                "symbol": symbol,
                "trades": trades,
                "winRate": round(win_rate, 2),
                "profitFactor": round(profit_factor, 2),
                "totalTrades": total_trades,
                "totalPnL": round(cumulative_pnl, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol PnL for {symbol}: {e}", exc_info=True)
            raise
    
    def get_multi_symbol_pnl(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get PnL data for multiple symbols for comparison
        
        Args:
            symbols: List of symbol names (max 4)
            
        Returns:
            dict: Multi-symbol PnL data with:
                - symbols: List of symbol PnL data
        """
        if len(symbols) > 4:
            raise ValueError("Maximum 4 symbols allowed for comparison")
        
        try:
            result = {
                "symbols": []
            }
            
            for symbol in symbols:
                symbol_data = self.get_symbol_pnl(symbol)
                result["symbols"].append(symbol_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting multi-symbol PnL: {e}", exc_info=True)
            raise
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status
        
        Returns:
            dict: Service status information
        """
        try:
            # Count unique symbols with trades
            query = """
                SELECT COUNT(DISTINCT s.symbol)
                FROM signals s
                INNER JOIN signal_outcomes so ON s.signal_id = so.signal_id
            """
            result = self.db.execute_query(query)
            symbol_count = result[0][0] if result else 0
            
            # Count total trades
            query = "SELECT COUNT(*) FROM signal_outcomes"
            result = self.db.execute_query(query)
            trade_count = result[0][0] if result else 0
            
            return {
                "initialized": True,
                "symbol_count": symbol_count,
                "trade_count": trade_count,
                "has_data": trade_count > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}", exc_info=True)
            return {
                "initialized": False,
                "symbol_count": 0,
                "trade_count": 0,
                "has_data": False,
                "error": str(e)
            }
