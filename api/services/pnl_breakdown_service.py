"""
PnL Breakdown Service for OpenClaw Trading Dashboard

Aggregates PnL by day, week, and month from signal_outcomes table,
calculates cumulative PnL, and identifies best/worst performing periods.

Features:
- Aggregate PnL by day, week, month from signal_outcomes table
- Calculate cumulative PnL for each time period
- Identify best and worst day/week/month
- Support time range filtering (1d, 7d, 30d, 90d, 1y, all)
- Return data in format suitable for bar charts with cumulative line overlay
"""

import logging
from typing import Dict, List
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from storage.database import Database

logger = logging.getLogger(__name__)


class PnLBreakdownService:
    """
    Service for aggregating PnL by time periods.
    
    Responsibilities:
    - Query signal_outcomes table for completed trades
    - Aggregate PnL by day, week, and month
    - Calculate cumulative PnL for each time period
    - Identify best and worst performing periods
    - Support time range filtering (1d, 7d, 30d, 90d, 1y, all)
    """
    
    def __init__(self, database: Database = None):
        """
        Initialize PnL breakdown service.
        
        Args:
            database: Database instance (creates new if None)
        """
        self.database = database or Database()
        logger.info("PnLBreakdownService initialized")
    
    def get_pnl_breakdown(self, time_range: str = "all") -> Dict:
        """
        Get PnL breakdown by day, week, and month.
        
        Args:
            time_range: Time range filter (1d, 7d, 30d, 90d, 1y, all)
            
        Returns:
            dict: PnL breakdown data including:
                - daily: List of daily PnL data points
                - weekly: List of weekly PnL data points
                - monthly: List of monthly PnL data points
                - bestDay: Best performing day
                - worstDay: Worst performing day
                - bestWeek: Best performing week
                - worstWeek: Worst performing week
                - bestMonth: Best performing month
                - worstMonth: Worst performing month
        """
        try:
            # Get completed trades from database
            trades = self._get_completed_trades(time_range)
            
            if not trades:
                logger.warning("No completed trades available")
                return self._empty_response()
            
            # Aggregate PnL by different time periods
            daily_pnl = self._aggregate_by_day(trades)
            weekly_pnl = self._aggregate_by_week(trades)
            monthly_pnl = self._aggregate_by_month(trades)
            
            # Calculate cumulative PnL for each period
            daily_with_cumulative = self._add_cumulative_pnl(daily_pnl)
            weekly_with_cumulative = self._add_cumulative_pnl(weekly_pnl)
            monthly_with_cumulative = self._add_cumulative_pnl(monthly_pnl)
            
            # Identify best and worst periods
            best_day, worst_day = self._find_best_worst(daily_pnl)
            best_week, worst_week = self._find_best_worst(weekly_pnl)
            best_month, worst_month = self._find_best_worst(monthly_pnl)
            
            return {
                "daily": daily_with_cumulative,
                "weekly": weekly_with_cumulative,
                "monthly": monthly_with_cumulative,
                "bestDay": best_day,
                "worstDay": worst_day,
                "bestWeek": best_week,
                "worstWeek": worst_week,
                "bestMonth": best_month,
                "worstMonth": worst_month
            }
            
        except Exception as e:
            logger.error(f"Error generating PnL breakdown: {e}", exc_info=True)
            return self._empty_response()
    
    def _get_completed_trades(self, time_range: str) -> List[Dict]:
        """
        Query completed trades from database with time range filter.
        
        Args:
            time_range: Time range filter (1d, 7d, 30d, 90d, 1y, all)
            
        Returns:
            list: List of completed trade dictionaries
        """
        try:
            # Calculate cutoff time based on time range
            cutoff_time = None
            now = datetime.now(timezone.utc)
            
            if time_range == "1d":
                cutoff_time = now - timedelta(days=1)
            elif time_range == "7d":
                cutoff_time = now - timedelta(days=7)
            elif time_range == "30d":
                cutoff_time = now - timedelta(days=30)
            elif time_range == "90d":
                cutoff_time = now - timedelta(days=90)
            elif time_range == "1y":
                cutoff_time = now - timedelta(days=365)
            # "all" means no cutoff
            
            # Query database
            conn = self.database._get_conn()
            
            if cutoff_time:
                # Filter by time range
                rows = conn.execute("""
                    SELECT closed_at, pnl_pct, exit_price
                    FROM signal_outcomes
                    WHERE closed_at IS NOT NULL
                    AND closed_at >= ?
                    ORDER BY closed_at ASC
                """, (cutoff_time.isoformat(),)).fetchall()
            else:
                # Get all data
                rows = conn.execute("""
                    SELECT closed_at, pnl_pct, exit_price
                    FROM signal_outcomes
                    WHERE closed_at IS NOT NULL
                    ORDER BY closed_at ASC
                """).fetchall()
            
            return [dict(r) for r in rows]
            
        except Exception as e:
            logger.error(f"Error querying completed trades: {e}")
            return []
    
    def _aggregate_by_day(self, trades: List[Dict]) -> List[Dict]:
        """
        Aggregate PnL by day.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            list: List of daily PnL aggregations with date and pnl
        """
        daily_pnl = defaultdict(float)
        
        for trade in trades:
            closed_at_str = trade.get("closed_at")
            pnl_pct = trade.get("pnl_pct", 0)
            
            if closed_at_str and pnl_pct is not None:
                try:
                    # Parse timestamp and extract date
                    dt = datetime.fromisoformat(closed_at_str.replace('Z', '+00:00'))
                    date_key = dt.date().isoformat()
                    daily_pnl[date_key] += pnl_pct
                except Exception as e:
                    logger.debug(f"Error parsing timestamp: {e}")
                    continue
        
        # Convert to sorted list
        result = [
            {"date": date, "pnl": pnl}
            for date, pnl in sorted(daily_pnl.items())
        ]
        
        return result
    
    def _aggregate_by_week(self, trades: List[Dict]) -> List[Dict]:
        """
        Aggregate PnL by week (ISO week).
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            list: List of weekly PnL aggregations with week and pnl
        """
        weekly_pnl = defaultdict(float)
        
        for trade in trades:
            closed_at_str = trade.get("closed_at")
            pnl_pct = trade.get("pnl_pct", 0)
            
            if closed_at_str and pnl_pct is not None:
                try:
                    # Parse timestamp and get ISO week
                    dt = datetime.fromisoformat(closed_at_str.replace('Z', '+00:00'))
                    year, week, _ = dt.isocalendar()
                    week_key = f"{year}-W{week:02d}"
                    weekly_pnl[week_key] += pnl_pct
                except Exception as e:
                    logger.debug(f"Error parsing timestamp: {e}")
                    continue
        
        # Convert to sorted list
        result = [
            {"week": week, "pnl": pnl}
            for week, pnl in sorted(weekly_pnl.items())
        ]
        
        return result
    
    def _aggregate_by_month(self, trades: List[Dict]) -> List[Dict]:
        """
        Aggregate PnL by month.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            list: List of monthly PnL aggregations with month and pnl
        """
        monthly_pnl = defaultdict(float)
        
        for trade in trades:
            closed_at_str = trade.get("closed_at")
            pnl_pct = trade.get("pnl_pct", 0)
            
            if closed_at_str and pnl_pct is not None:
                try:
                    # Parse timestamp and extract year-month
                    dt = datetime.fromisoformat(closed_at_str.replace('Z', '+00:00'))
                    month_key = dt.strftime("%Y-%m")
                    monthly_pnl[month_key] += pnl_pct
                except Exception as e:
                    logger.debug(f"Error parsing timestamp: {e}")
                    continue
        
        # Convert to sorted list
        result = [
            {"month": month, "pnl": pnl}
            for month, pnl in sorted(monthly_pnl.items())
        ]
        
        return result
    
    def _add_cumulative_pnl(self, period_data: List[Dict]) -> List[Dict]:
        """
        Add cumulative PnL to each period.
        
        Args:
            period_data: List of period dictionaries with pnl
            
        Returns:
            list: Period data with cumulative_pnl added
        """
        cumulative = 0
        result = []
        
        for period in period_data:
            cumulative += period["pnl"]
            result.append({
                **period,
                "cumulativePnL": cumulative
            })
        
        return result
    
    def _find_best_worst(self, period_data: List[Dict]) -> tuple:
        """
        Find best and worst performing periods.
        
        Args:
            period_data: List of period dictionaries with pnl
            
        Returns:
            tuple: (best_period, worst_period) dictionaries
        """
        if not period_data:
            return None, None
        
        best = max(period_data, key=lambda x: x["pnl"])
        worst = min(period_data, key=lambda x: x["pnl"])
        
        return best, worst
    
    def _empty_response(self) -> Dict:
        """
        Return empty response structure.
        
        Returns:
            dict: Empty PnL breakdown data
        """
        return {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "bestDay": None,
            "worstDay": None,
            "bestWeek": None,
            "worstWeek": None,
            "bestMonth": None,
            "worstMonth": None
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
                SELECT COUNT(*) as count 
                FROM signal_outcomes 
                WHERE closed_at IS NOT NULL
            """).fetchone()
            trade_count = dict(row)["count"] if row else 0
            
            return {
                "initialized": True,
                "trade_count": trade_count,
                "has_data": trade_count > 0
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "trade_count": 0,
                "has_data": False,
                "error": str(e)
            }
