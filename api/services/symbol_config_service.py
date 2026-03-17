"""
Symbol Selection Configuration Service for OpenClaw Trading Dashboard

Manages symbol selection with performance metrics and exchange integration.

Features:
- Retrieve available symbols from exchanges
- Get currently monitored symbols from config.py
- Update monitored symbols list
- Fetch performance metrics for each symbol
- Persist symbol configuration changes
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SymbolConfigService:
    """
    Service for managing symbol selection configuration.
    
    Responsibilities:
    - List available symbols from exchanges
    - Get currently monitored symbols
    - Update monitored symbols list
    - Fetch performance metrics per symbol
    - Persist symbol configuration changes
    """
    
    def __init__(self, db=None):
        """
        Initialize symbol configuration service.
        
        Args:
            db: Database instance for fetching performance metrics (optional)
        """
        self.config_path = "config.py"
        self.db = db
        logger.info("SymbolConfigService initialized")
    
    def get_available_symbols(self) -> Dict[str, Any]:
        """
        Get list of available symbols from exchanges.
        
        Returns:
            dict: Available symbols with metadata
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "exchange": "bybit",
                        "volume24h": 1000000000,
                        "price": 50000,
                        "change24h": 2.5
                    },
                    ...
                ],
                "count": 150
            }
        """
        try:
            # Common perpetual symbols across exchanges
            # In production, this would fetch from exchange APIs
            common_symbols = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                "ADAUSDT", "DOGEUSDT", "MATICUSDT", "DOTUSDT", "LINKUSDT",
                "AVAXUSDT", "UNIUSDT", "ATOMUSDT", "LTCUSDT", "ETCUSDT",
                "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT",
                "AAVEUSDT", "HBARUSDT", "BCHUSDT", "JUPUSDT", "TAOUSDT",
                "1000PEPEUSDT", "FARTCOINUSDT", "HYPEUSDT", "POPCATUSDT",
                "SPXUSDT", "TONUSDT", "LDOUSDT", "NOTUSDT", "CHILLGUYUSDT",
                "WLDUSDT", "1000BONKUSDT"
            ]
            
            symbols = []
            for symbol in sorted(common_symbols):
                # Get performance metrics if available
                metrics = self._get_symbol_metrics(symbol)
                
                symbols.append({
                    "symbol": symbol,
                    "exchange": "cross",  # Available on both exchanges
                    "volume24h": metrics.get("volume24h", 0),
                    "price": metrics.get("price", 0),
                    "change24h": metrics.get("change24h", 0),
                    "win_rate": metrics.get("win_rate", 0),
                    "total_trades": metrics.get("total_trades", 0),
                    "total_pnl": metrics.get("total_pnl", 0)
                })
            
            logger.debug(f"Retrieved {len(symbols)} available symbols")
            return {
                "symbols": symbols,
                "count": len(symbols)
            }
            
        except Exception as e:
            logger.error(f"Error loading available symbols: {e}", exc_info=True)
            raise
    
    def get_monitored_symbols(self) -> Dict[str, Any]:
        """
        Get currently monitored symbols from configuration.
        
        Returns:
            dict: Monitored symbols with performance metrics
            {
                "fixed_symbols": ["BTCUSDT", "ETHUSDT", ...],
                "dynamic_config": {
                    "top_gainers": 10,
                    "top_losers": 10,
                    "update_interval_minutes": 60
                },
                "all_symbols": ["BTCUSDT", "ETHUSDT", ...],
                "count": 30
            }
        """
        try:
            import config
            
            fixed_symbols = config.FIXED_SYMBOLS.copy()
            dynamic_config = config.DYNAMIC_SYMBOLS_CONFIG.copy()
            all_symbols = config.SYMBOLS.copy()
            
            logger.debug(f"Retrieved {len(all_symbols)} monitored symbols")
            return {
                "fixed_symbols": fixed_symbols,
                "dynamic_config": dynamic_config,
                "all_symbols": all_symbols,
                "count": len(all_symbols)
            }
            
        except Exception as e:
            logger.error(f"Error loading monitored symbols: {e}", exc_info=True)
            raise
    
    def update_monitored_symbols(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Update the list of monitored symbols.
        
        Args:
            symbols: List of symbol names to monitor
            
        Returns:
            dict: Result with success status
            {
                "success": True,
                "symbols": [...],
                "count": 30,
                "message": "Monitored symbols updated successfully"
            }
            
        Raises:
            ValueError: If symbol list is invalid
            IOError: If unable to persist changes
        """
        try:
            # Validate symbols
            if not symbols or not isinstance(symbols, list):
                raise ValueError("Symbols must be a non-empty list")
            
            if len(symbols) < 1:
                raise ValueError("At least 1 symbol must be monitored")
            
            if len(symbols) > 100:
                raise ValueError("Maximum 100 symbols can be monitored")
            
            # Validate symbol format
            for symbol in symbols:
                if not isinstance(symbol, str) or not symbol.endswith("USDT"):
                    raise ValueError(f"Invalid symbol format: {symbol}")
            
            # Update in-memory configuration
            self._update_in_memory(symbols)
            
            # Persist to file
            self._persist_to_file(symbols)
            
            logger.info(f"Updated monitored symbols: {len(symbols)} symbols")
            
            return {
                "success": True,
                "symbols": symbols,
                "count": len(symbols),
                "message": f"Updated monitored symbols successfully ({len(symbols)} symbols)",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
            
        except ValueError as e:
            logger.warning(f"Validation error updating symbols: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"Error updating monitored symbols: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update symbols: {str(e)}",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
    
    def _get_symbol_metrics(self, symbol: str) -> Dict[str, Any]:
        """
        Get performance metrics for a symbol from database.
        
        Args:
            symbol: Symbol name
            
        Returns:
            dict: Performance metrics
        """
        metrics = {
            "volume24h": 0,
            "price": 0,
            "change24h": 0,
            "win_rate": 0,
            "total_trades": 0,
            "total_pnl": 0
        }
        
        if not self.db:
            return metrics
        
        try:
            # Get signal outcomes for this symbol
            conn = self.db._get_conn()
            
            # Get trade statistics
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(pnl_pct) as total_pnl,
                    AVG(pnl_pct) as avg_pnl
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE s.symbol = ?
            """, (symbol,)).fetchone()
            
            if row:
                total_trades = row["total_trades"] or 0
                wins = row["wins"] or 0
                metrics["total_trades"] = total_trades
                metrics["total_pnl"] = round(row["total_pnl"] or 0, 2)
                metrics["win_rate"] = round((wins / total_trades * 100) if total_trades > 0 else 0, 2)
            
        except Exception as e:
            logger.error(f"Error fetching metrics for {symbol}: {e}")
        
        return metrics
    
    def _update_in_memory(self, symbols: List[str]):
        """
        Update symbols in the in-memory configuration.
        
        Args:
            symbols: List of symbol names
        """
        import config
        config.FIXED_SYMBOLS = symbols.copy()
        config.SYMBOLS = symbols.copy()
    
    def _persist_to_file(self, symbols: List[str]):
        """
        Persist symbol changes to configuration file.
        
        Updates the config.py file by modifying the FIXED_SYMBOLS list.
        
        Args:
            symbols: List of symbol names
            
        Raises:
            IOError: If unable to read or write configuration file
        """
        try:
            # Read current file content
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find FIXED_SYMBOLS list and replace it
            # Pattern: FIXED_SYMBOLS = [...]
            pattern = r'(FIXED_SYMBOLS\s*=\s*\[)[^\]]*(\])'
            
            # Check if pattern exists
            if not re.search(pattern, content):
                raise ValueError("Could not find 'FIXED_SYMBOLS' in configuration file")
            
            # Format new symbols list
            symbols_str = ',\n    '.join(f'"{s}"' for s in symbols)
            new_list = f'\n    {symbols_str},\n'
            
            # Replace list
            updated_content = re.sub(pattern, rf'\g<1>{new_list}\g<2>', content)
            
            # Write back to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.debug(f"Persisted {len(symbols)} symbols to {self.config_path}")
            
        except FileNotFoundError:
            raise IOError(f"Configuration file not found: {self.config_path}")
        except Exception as e:
            raise IOError(f"Failed to persist configuration: {str(e)}")
    
    def get_symbol_performance(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed performance metrics for a specific symbol.
        
        Args:
            symbol: Symbol name
            
        Returns:
            dict: Detailed performance metrics
        """
        try:
            if not self.db:
                return {
                    "symbol": symbol,
                    "error": "Database not available"
                }
            
            conn = self.db._get_conn()
            
            # Get comprehensive statistics
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(pnl_pct) as total_pnl,
                    AVG(pnl_pct) as avg_pnl,
                    MAX(pnl_pct) as best_trade,
                    MIN(pnl_pct) as worst_trade,
                    AVG(duration_minutes) as avg_duration,
                    AVG(rr_achieved) as avg_rr
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE s.symbol = ?
            """, (symbol,)).fetchone()
            
            if not row or row["total_trades"] == 0:
                return {
                    "symbol": symbol,
                    "total_trades": 0,
                    "message": "No trading history for this symbol"
                }
            
            total_trades = row["total_trades"]
            wins = row["wins"] or 0
            losses = row["losses"] or 0
            
            # Calculate profit factor
            winning_pnl = conn.execute("""
                SELECT SUM(pnl_pct) as sum_wins
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE s.symbol = ? AND outcome = 'WIN'
            """, (symbol,)).fetchone()["sum_wins"] or 0
            
            losing_pnl = abs(conn.execute("""
                SELECT SUM(pnl_pct) as sum_losses
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE s.symbol = ? AND outcome = 'LOSS'
            """, (symbol,)).fetchone()["sum_losses"] or 0)
            
            profit_factor = (winning_pnl / losing_pnl) if losing_pnl > 0 else 0
            
            return {
                "symbol": symbol,
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round((wins / total_trades * 100) if total_trades > 0 else 0, 2),
                "total_pnl": round(row["total_pnl"] or 0, 2),
                "avg_pnl": round(row["avg_pnl"] or 0, 2),
                "best_trade": round(row["best_trade"] or 0, 2),
                "worst_trade": round(row["worst_trade"] or 0, 2),
                "avg_duration_minutes": round(row["avg_duration"] or 0, 2),
                "avg_rr": round(row["avg_rr"] or 0, 2),
                "profit_factor": round(profit_factor, 2)
            }
            
        except Exception as e:
            logger.error(f"Error fetching performance for {symbol}: {e}", exc_info=True)
            return {
                "symbol": symbol,
                "error": str(e)
            }
