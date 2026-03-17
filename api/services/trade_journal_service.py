"""
Trade Journal Service for OpenClaw Trading Dashboard

Retrieves and manages trade history from signal_outcomes table with comprehensive
filtering, sorting, and pagination capabilities for the trade journal interface.

Features:
- Retrieve trades from signal_outcomes table with associated signal details
- Pagination support (page, page_size parameters)
- Filter by symbol, date range, outcome (WIN/LOSS), quality grade
- Sort by any column (entry_time, exit_time, pnl, duration)
- Return complete trade data including entry/exit prices, PnL, reasons, MFE/MAE
- Query result caching with 30-60 second TTL
- Selective column queries for performance
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from storage.database import Database
from storage.query_cache import cached_query, invalidate_cache
from storage.query_optimizer import profile_query, SelectiveQueryBuilder

logger = logging.getLogger(__name__)


class TradeJournalService:
    """
    Service for retrieving and managing trade history.
    
    Responsibilities:
    - Query signal_outcomes table with associated signal details
    - Support pagination for large trade histories
    - Filter trades by multiple criteria (symbol, date range, outcome, quality)
    - Sort trades by any column
    - Return comprehensive trade data for journal display
    """
    
    def __init__(self, database: Database = None):
        """
        Initialize trade journal service.
        
        Args:
            database: Database instance (creates new if None)
        """
        self.database = database or Database()
        logger.info("TradeJournalService initialized")
    
    @cached_query(ttl=30, key_prefix="trade_journal")
    @profile_query("get_trade_history")
    def get_trade_history(
        self,
        page: int = 1,
        page_size: int = 50,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        outcome: Optional[str] = None,
        quality: Optional[str] = None,
        sort_by: str = "closed_at",
        sort_order: str = "desc"
    ) -> Dict:
        """
        Get paginated trade history with filtering and sorting.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of trades per page
            symbol: Filter by symbol (e.g., "BTCUSDT")
            start_date: Filter trades closed after this date (ISO format)
            end_date: Filter trades closed before this date (ISO format)
            outcome: Filter by outcome ("WIN" or "LOSS")
            quality: Filter by quality grade ("A+", "A", "B", "C")
            sort_by: Column to sort by (entry_time, exit_time, pnl, duration)
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            dict: Trade history data including:
                - trades: List of trade dictionaries
                - pagination: Pagination metadata (page, pageSize, totalTrades, totalPages)
                - filters: Applied filters
        """
        try:
            # Build WHERE clause based on filters
            where_clauses = ["so.closed_at IS NOT NULL"]
            params = []
            
            if symbol:
                where_clauses.append("s.symbol = ?")
                params.append(symbol)
            
            if start_date:
                where_clauses.append("so.closed_at >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("so.closed_at <= ?")
                params.append(end_date)
            
            if outcome:
                where_clauses.append("so.outcome = ?")
                params.append(outcome.upper())
            
            if quality:
                where_clauses.append("s.quality = ?")
                params.append(quality)
            
            where_clause = " AND ".join(where_clauses)
            
            # Validate and map sort column
            sort_column_map = {
                "entry_time": "s.created_at",
                "exit_time": "so.closed_at",
                "pnl": "so.pnl_pct",
                "duration": "so.duration_minutes",
                "symbol": "s.symbol",
                "quality": "s.quality",
                "closed_at": "so.closed_at"
            }
            
            sort_column = sort_column_map.get(sort_by, "so.closed_at")
            sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
            
            # Get total count for pagination
            total_trades = self._get_total_count(where_clause, params)
            
            # Calculate pagination
            total_pages = (total_trades + page_size - 1) // page_size if total_trades > 0 else 0
            offset = (page - 1) * page_size
            
            # Query trades with pagination
            trades = self._query_trades(
                where_clause=where_clause,
                params=params,
                sort_column=sort_column,
                sort_direction=sort_direction,
                limit=page_size,
                offset=offset
            )
            
            return {
                "trades": trades,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "totalTrades": total_trades,
                    "totalPages": total_pages
                },
                "filters": {
                    "symbol": symbol,
                    "startDate": start_date,
                    "endDate": end_date,
                    "outcome": outcome,
                    "quality": quality,
                    "sortBy": sort_by,
                    "sortOrder": sort_order
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving trade history: {e}", exc_info=True)
            return {
                "trades": [],
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "totalTrades": 0,
                    "totalPages": 0
                },
                "filters": {},
                "error": str(e)
            }
    
    @profile_query("get_total_count")
    def _get_total_count(self, where_clause: str, params: List) -> int:
        """
        Get total count of trades matching filters.
        
        Args:
            where_clause: SQL WHERE clause
            params: Query parameters
            
        Returns:
            int: Total number of matching trades
        """
        try:
            conn = self.database._get_conn()
            
            query = f"""
                SELECT COUNT(*) as total
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE {where_clause}
            """
            
            row = conn.execute(query, params).fetchone()
            return dict(row)["total"] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting total count: {e}")
            return 0
    
    @profile_query("query_trades")
    def _query_trades(
        self,
        where_clause: str,
        params: List,
        sort_column: str,
        sort_direction: str,
        limit: int,
        offset: int
    ) -> List[Dict]:
        """
        Query trades from database with filters, sorting, and pagination.
        Uses selective columns for better performance.
        
        Args:
            where_clause: SQL WHERE clause
            params: Query parameters
            sort_column: Column to sort by
            sort_direction: Sort direction (ASC or DESC)
            limit: Maximum number of trades to return
            offset: Number of trades to skip
            
        Returns:
            list: List of trade dictionaries
        """
        try:
            conn = self.database._get_conn()
            
            # Use selective columns instead of fetching advanced_analytics unless needed
            query = f"""
                SELECT 
                    so.id as trade_id,
                    so.signal_id,
                    s.symbol,
                    s.signal_type as direction,
                    s.quality,
                    s.confidence,
                    s.entry_price,
                    so.exit_price,
                    s.sl_price as stop_loss,
                    s.tp_price as take_profit,
                    so.pnl_pct,
                    so.outcome,
                    so.rr_achieved,
                    so.max_favorable as mfe,
                    so.max_adverse as mae,
                    so.duration_minutes,
                    s.created_at as entry_time,
                    so.closed_at as exit_time,
                    s.reasoning as entry_reason,
                    so.exit_reason,
                    so.tp_hit,
                    so.sl_hit,
                    s.market_regime
                FROM signal_outcomes so
                INNER JOIN signals s ON so.signal_id = s.signal_id
                WHERE {where_clause}
                ORDER BY {sort_column} {sort_direction}
                LIMIT ? OFFSET ?
            """
            
            rows = conn.execute(query, params + [limit, offset]).fetchall()
            
            trades = []
            for row in rows:
                trade = dict(row)
                
                # Format trade data for frontend
                formatted_trade = {
                    "tradeId": str(trade["trade_id"]),
                    "signalId": trade["signal_id"],
                    "symbol": trade["symbol"],
                    "direction": trade["direction"],
                    "quality": trade["quality"],
                    "confidence": round(trade["confidence"], 2) if trade["confidence"] else 0,
                    "entryPrice": round(trade["entry_price"], 8) if trade["entry_price"] else 0,
                    "exitPrice": round(trade["exit_price"], 8) if trade["exit_price"] else 0,
                    "stopLoss": round(trade["stop_loss"], 8) if trade["stop_loss"] else 0,
                    "takeProfit": round(trade["take_profit"], 8) if trade["take_profit"] else 0,
                    "pnl": round(trade["pnl_pct"], 2) if trade["pnl_pct"] is not None else 0,
                    "outcome": trade["outcome"],
                    "rrAchieved": round(trade["rr_achieved"], 2) if trade["rr_achieved"] else 0,
                    "mfe": round(trade["mfe"], 2) if trade["mfe"] else 0,
                    "mae": round(trade["mae"], 2) if trade["mae"] else 0,
                    "duration": trade["duration_minutes"] if trade["duration_minutes"] else 0,
                    "entryTime": trade["entry_time"],
                    "exitTime": trade["exit_time"],
                    "entryReason": trade["entry_reason"] or "",
                    "exitReason": trade["exit_reason"] or "",
                    "tpHit": bool(trade["tp_hit"]),
                    "slHit": bool(trade["sl_hit"]),
                    "marketRegime": trade["market_regime"] or "UNKNOWN"
                }
                
                trades.append(formatted_trade)
            
            return trades
            
        except Exception as e:
            logger.error(f"Error querying trades: {e}")
            return []
    
    @cached_query(ttl=60, key_prefix="trade_detail")
    @profile_query("get_trade_detail")
    def get_trade_detail(self, trade_id: str) -> Optional[Dict]:
        """
        Get detailed information for a single trade.
        
        Args:
            trade_id: Trade ID (signal_outcomes.id)
            
        Returns:
            dict: Detailed trade information including feature contributions
        """
        try:
            conn = self.database._get_conn()
            
            query = """
                SELECT 
                    so.*,
                    s.symbol,
                    s.signal_type,
                    s.quality,
                    s.confidence,
                    s.entry_price,
                    s.sl_price,
                    s.tp_price,
                    s.rr_ratio,
                    s.market_regime,
                    s.reasoning,
                    s.step1_data,
                    s.step2_data,
                    s.step3_data,
                    s.step4_data,
                    s.advanced_analytics,
                    s.created_at as entry_time
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE so.id = ?
            """
            
            row = conn.execute(query, (trade_id,)).fetchone()
            
            if not row:
                logger.warning(f"Trade not found: {trade_id}")
                return None
            
            trade = dict(row)
            
            # Parse JSON fields
            import json
            step1_data = json.loads(trade["step1_data"]) if trade["step1_data"] else {}
            step2_data = json.loads(trade["step2_data"]) if trade["step2_data"] else {}
            step3_data = json.loads(trade["step3_data"]) if trade["step3_data"] else {}
            step4_data = json.loads(trade["step4_data"]) if trade["step4_data"] else {}
            advanced_analytics = json.loads(trade["advanced_analytics"]) if trade["advanced_analytics"] else {}
            
            # Extract feature contributions from advanced_analytics
            feature_contributions = advanced_analytics.get("feature_contributions", {}) if advanced_analytics else {}
            
            return {
                "tradeId": str(trade["id"]),
                "signalId": trade["signal_id"],
                "symbol": trade["symbol"],
                "direction": trade["signal_type"],
                "quality": trade["quality"],
                "confidence": round(trade["confidence"], 2) if trade["confidence"] else 0,
                "entryPrice": round(trade["entry_price"], 8) if trade["entry_price"] else 0,
                "exitPrice": round(trade["exit_price"], 8) if trade["exit_price"] else 0,
                "stopLoss": round(trade["sl_price"], 8) if trade["sl_price"] else 0,
                "takeProfit": round(trade["tp_price"], 8) if trade["tp_price"] else 0,
                "pnl": round(trade["pnl_pct"], 2) if trade["pnl_pct"] is not None else 0,
                "outcome": trade["outcome"],
                "rrAchieved": round(trade["rr_achieved"], 2) if trade["rr_achieved"] else 0,
                "rrTarget": round(trade["rr_ratio"], 2) if trade["rr_ratio"] else 0,
                "mfe": round(trade["max_favorable"], 2) if trade["max_favorable"] else 0,
                "mae": round(trade["max_adverse"], 2) if trade["max_adverse"] else 0,
                "duration": trade["duration_minutes"] if trade["duration_minutes"] else 0,
                "entryTime": trade["entry_time"],
                "exitTime": trade["closed_at"],
                "entryReason": trade["reasoning"] or "",
                "exitReason": trade["exit_reason"] or "",
                "tpHit": bool(trade["tp_hit"]),
                "slHit": bool(trade["sl_hit"]),
                "marketRegime": trade["market_regime"] or "UNKNOWN",
                "featureContributions": feature_contributions,
                "step1Data": step1_data,
                "step2Data": step2_data,
                "step3Data": step3_data,
                "step4Data": step4_data,
                "advancedAnalytics": advanced_analytics
            }
            
        except Exception as e:
            logger.error(f"Error retrieving trade detail: {e}", exc_info=True)
            return None
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including data availability
        """
        try:
            conn = self.database._get_conn()
            
            # Get trade count and date range
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    MIN(closed_at) as earliest_trade,
                    MAX(closed_at) as latest_trade
                FROM signal_outcomes
                WHERE closed_at IS NOT NULL
            """).fetchone()
            
            result = dict(row) if row else {
                "total_trades": 0,
                "earliest_trade": None,
                "latest_trade": None
            }
            
            return {
                "initialized": True,
                "total_trades": result["total_trades"],
                "earliest_trade": result["earliest_trade"],
                "latest_trade": result["latest_trade"],
                "has_data": result["total_trades"] > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "total_trades": 0,
                "has_data": False,
                "error": str(e)
            }
