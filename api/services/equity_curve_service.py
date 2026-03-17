"""
Equity Curve Service for OpenClaw Trading Dashboard

Generates equity curve from equity_snapshots table, identifies drawdown periods,
and calculates peak/current equity values.

Features:
- Generate equity curve from equity_snapshots table
- Identify drawdown periods exceeding 5%
- Calculate peak equity and current equity
- Support time range filtering (1d, 7d, 30d, 90d, 1y, all)
- Return data in format suitable for TradingView Lightweight Charts
"""

import logging
from typing import Dict, List
from datetime import datetime, timezone, timedelta

from storage.database import Database

logger = logging.getLogger(__name__)


class EquityCurveService:
    """
    Service for generating equity curve and identifying drawdown periods.
    
    Responsibilities:
    - Query equity_snapshots table for historical equity data
    - Calculate drawdown periods where equity drops >5% from peak
    - Identify peak equity and current equity values
    - Support time range filtering (1d, 7d, 30d, 90d, 1y, all)
    - Format data for TradingView Lightweight Charts
    """
    
    def __init__(self, database: Database = None):
        """
        Initialize equity curve service.
        
        Args:
            database: Database instance (creates new if None)
        """
        self.database = database or Database()
        logger.info("EquityCurveService initialized")
    
    def get_equity_curve(self, time_range: str = "all") -> Dict:
        """
        Get equity curve data with drawdown periods.
        
        Args:
            time_range: Time range filter (1d, 7d, 30d, 90d, 1y, all)
            
        Returns:
            dict: Equity curve data including:
                - timestamps: List of Unix timestamps in milliseconds
                - equityValues: List of equity values
                - drawdownPeriods: List of drawdown periods exceeding 5%
                - peakEquity: Peak equity value
                - currentEquity: Current equity value
                - maxDrawdown: Maximum drawdown depth (%)
                - maxDrawdownDuration: Maximum drawdown duration (minutes)
        """
        try:
            # Get equity snapshots from database
            equity_data = self._get_equity_snapshots(time_range)
            
            if not equity_data:
                logger.warning("No equity data available")
                return {
                    "timestamps": [],
                    "equityValues": [],
                    "drawdownPeriods": [],
                    "peakEquity": 0,
                    "currentEquity": 0,
                    "maxDrawdown": 0,
                    "maxDrawdownDuration": 0
                }
            
            # Extract timestamps and equity values
            timestamps = []
            equity_values = []
            
            for snapshot in equity_data:
                # Parse timestamp
                timestamp_str = snapshot.get("timestamp")
                if timestamp_str:
                    try:
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        # Convert to Unix timestamp in milliseconds
                        timestamps.append(int(dt.timestamp() * 1000))
                    except Exception as e:
                        logger.debug(f"Error parsing timestamp: {e}")
                        continue
                
                equity_values.append(snapshot.get("equity", 0))
            
            # Calculate peak and current equity
            peak_equity = max(equity_values) if equity_values else 0
            current_equity = equity_values[-1] if equity_values else 0
            
            # Identify drawdown periods exceeding 5%
            drawdown_periods = self._identify_drawdown_periods(timestamps, equity_values)
            
            # Calculate max drawdown depth and duration
            max_drawdown = 0
            max_drawdown_duration = 0
            
            if drawdown_periods:
                max_drawdown = min(period["depth"] for period in drawdown_periods)
                max_drawdown_duration = max(period["duration"] for period in drawdown_periods)
            
            return {
                "timestamps": timestamps,
                "equityValues": equity_values,
                "drawdownPeriods": drawdown_periods,
                "peakEquity": peak_equity,
                "currentEquity": current_equity,
                "maxDrawdown": max_drawdown,
                "maxDrawdownDuration": max_drawdown_duration
            }
            
        except Exception as e:
            logger.error(f"Error generating equity curve: {e}", exc_info=True)
            return {
                "timestamps": [],
                "equityValues": [],
                "drawdownPeriods": [],
                "peakEquity": 0,
                "currentEquity": 0,
                "maxDrawdown": 0,
                "maxDrawdownDuration": 0
            }
    
    def _get_equity_snapshots(self, time_range: str) -> List[Dict]:
        """
        Query equity snapshots from database with time range filter.
        
        Args:
            time_range: Time range filter (1d, 7d, 30d, 90d, 1y, all)
            
        Returns:
            list: List of equity snapshot dictionaries
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
                    SELECT * FROM equity_snapshots
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """, (cutoff_time.isoformat(),)).fetchall()
            else:
                # Get all data
                rows = conn.execute("""
                    SELECT * FROM equity_snapshots
                    ORDER BY timestamp ASC
                """).fetchall()
            
            return [dict(r) for r in rows]
            
        except Exception as e:
            logger.error(f"Error querying equity snapshots: {e}")
            return []
    
    def _identify_drawdown_periods(self, timestamps: List[int], equity_values: List[float]) -> List[Dict]:
        """
        Identify drawdown periods exceeding 5%.
        
        A drawdown period starts when equity drops >5% from a peak and ends when
        equity recovers to a new peak.
        
        Args:
            timestamps: List of Unix timestamps in milliseconds
            equity_values: List of equity values
            
        Returns:
            list: List of drawdown period dictionaries, each containing:
                - startDate: Start timestamp (ms)
                - endDate: End timestamp (ms)
                - depth: Drawdown depth as percentage (negative value)
                - duration: Duration in minutes
                - peakEquity: Peak equity before drawdown
                - troughEquity: Lowest equity during drawdown
        """
        if not equity_values or len(equity_values) < 2:
            return []
        
        drawdown_periods = []
        peak_equity = equity_values[0]
        peak_index = 0
        in_drawdown = False
        drawdown_start_index = None
        drawdown_peak_equity = None
        min_equity_in_drawdown = None
        
        for i, equity in enumerate(equity_values):
            # Update peak if new high
            if equity > peak_equity:
                # If we were in a drawdown, it has ended
                if in_drawdown:
                    # Record the drawdown period
                    drawdown_periods.append({
                        "startDate": timestamps[drawdown_start_index],
                        "endDate": timestamps[i],
                        "depth": (min_equity_in_drawdown - drawdown_peak_equity) / drawdown_peak_equity * 100,
                        "duration": (timestamps[i] - timestamps[drawdown_start_index]) // 60000,  # Convert ms to minutes
                        "peakEquity": drawdown_peak_equity,
                        "troughEquity": min_equity_in_drawdown
                    })
                    in_drawdown = False
                
                peak_equity = equity
                peak_index = i
            else:
                # Calculate drawdown from peak
                if peak_equity > 0:
                    drawdown_pct = (equity - peak_equity) / peak_equity * 100
                    
                    # Check if drawdown exceeds 5%
                    if drawdown_pct < -5:
                        if not in_drawdown:
                            # Start new drawdown period
                            in_drawdown = True
                            drawdown_start_index = peak_index
                            drawdown_peak_equity = peak_equity
                            min_equity_in_drawdown = equity
                            min_equity_index = i
                        else:
                            # Update minimum equity in current drawdown
                            if equity < min_equity_in_drawdown:
                                min_equity_in_drawdown = equity
                                min_equity_index = i
        
        # If still in drawdown at the end, record it
        if in_drawdown:
            drawdown_periods.append({
                "startDate": timestamps[drawdown_start_index],
                "endDate": timestamps[-1],
                "depth": (min_equity_in_drawdown - drawdown_peak_equity) / drawdown_peak_equity * 100,
                "duration": (timestamps[-1] - timestamps[drawdown_start_index]) // 60000,  # Convert ms to minutes
                "peakEquity": drawdown_peak_equity,
                "troughEquity": min_equity_in_drawdown
            })
        
        return drawdown_periods
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including data availability
        """
        try:
            # Check if we have any equity data
            conn = self.database._get_conn()
            row = conn.execute("SELECT COUNT(*) as count FROM equity_snapshots").fetchone()
            snapshot_count = dict(row)["count"] if row else 0
            
            return {
                "initialized": True,
                "snapshot_count": snapshot_count,
                "has_data": snapshot_count > 0
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "snapshot_count": 0,
                "has_data": False,
                "error": str(e)
            }
