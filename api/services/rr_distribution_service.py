"""
R:R Distribution Service for OpenClaw Trading Dashboard

Calculates achieved risk-reward ratio distribution from signal_outcomes table,
groups trades into R:R buckets, and compares actual vs. target R:R distribution.

Features:
- Calculate achieved R:R for each trade from signal_outcomes table
- Group trades into R:R buckets (<0.5, 0.5-1.0, 1.0-1.5, 1.5-2.0, >2.0)
- Calculate average and median R:R achieved
- Compare actual vs. target R:R distribution
- Implement GET /api/analytics/rr-distribution endpoint
"""

import logging
from typing import Dict, List
from collections import defaultdict
import statistics

from storage.database import Database

logger = logging.getLogger(__name__)


class RRDistributionService:
    """
    Service for analyzing risk-reward ratio distribution.
    
    Responsibilities:
    - Query signal_outcomes table for completed trades with rr_achieved values
    - Group trades into predefined R:R buckets
    - Calculate average and median R:R achieved
    - Calculate percentage of trades in each bucket
    - Compare actual distribution to target distribution
    - Detect warning when average R:R < 1.0
    
    R:R Buckets:
    - <0.5: Very poor risk-reward (stopped out early)
    - 0.5-1.0: Below target risk-reward
    - 1.0-1.5: Acceptable risk-reward
    - 1.5-2.0: Good risk-reward
    - >2.0: Excellent risk-reward
    """
    
    def __init__(self, database: Database = None):
        """
        Initialize R:R distribution service.
        
        Args:
            database: Database instance (creates new if None)
        """
        self.database = database or Database()
        
        # Define R:R bucket boundaries
        self.buckets = [
            {"label": "<0.5", "min": float('-inf'), "max": 0.5},
            {"label": "0.5-1.0", "min": 0.5, "max": 1.0},
            {"label": "1.0-1.5", "min": 1.0, "max": 1.5},
            {"label": "1.5-2.0", "min": 1.5, "max": 2.0},
            {"label": ">2.0", "min": 2.0, "max": float('inf')}
        ]
        
        # Target distribution (ideal percentages for each bucket)
        # Based on typical profitable trading system expectations
        self.target_distribution = {
            "<0.5": 15.0,      # 15% stopped out early
            "0.5-1.0": 20.0,   # 20% below target
            "1.0-1.5": 30.0,   # 30% at target
            "1.5-2.0": 25.0,   # 25% above target
            ">2.0": 10.0       # 10% excellent trades
        }
        
        logger.info("RRDistributionService initialized")
    
    def get_rr_distribution(self) -> Dict:
        """
        Get comprehensive R:R distribution analysis.
        
        Returns:
            dict: R:R distribution data including:
                - buckets: Dictionary mapping bucket label to trade count
                - percentages: Dictionary mapping bucket label to percentage
                - avgRR: Average R:R achieved across all trades
                - medianRR: Median R:R achieved
                - totalTrades: Total number of trades analyzed
                - targetDistribution: Target distribution percentages
                - warning: Warning message if average R:R < 1.0
        """
        try:
            # Get all completed trades with R:R values
            trades = self._get_trades_with_rr()
            
            if not trades:
                logger.warning("No completed trades with R:R data available")
                return {
                    "buckets": {bucket["label"]: 0 for bucket in self.buckets},
                    "percentages": {bucket["label"]: 0.0 for bucket in self.buckets},
                    "avgRR": 0.0,
                    "medianRR": 0.0,
                    "totalTrades": 0,
                    "targetDistribution": self.target_distribution,
                    "warning": None
                }
            
            # Group trades into buckets
            bucket_counts = self._group_into_buckets(trades)
            
            # Calculate percentages
            total_trades = len(trades)
            bucket_percentages = {
                label: (count / total_trades * 100) if total_trades > 0 else 0.0
                for label, count in bucket_counts.items()
            }
            
            # Calculate average and median R:R
            rr_values = [t["rr_achieved"] for t in trades]
            avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0.0
            median_rr = statistics.median(rr_values) if rr_values else 0.0
            
            # Check for warning condition
            warning = None
            if avg_rr < 1.0:
                warning = {
                    "severity": "warning",
                    "message": f"Average R:R ({avg_rr:.2f}) is below 1.0. System is not achieving target risk-reward ratios.",
                    "avgRR": round(avg_rr, 2),
                    "recommendation": "Review stop loss placement and take profit targets. Consider tightening entry criteria or adjusting position sizing."
                }
            
            return {
                "buckets": bucket_counts,
                "percentages": {k: round(v, 2) for k, v in bucket_percentages.items()},
                "avgRR": round(avg_rr, 2),
                "medianRR": round(median_rr, 2),
                "totalTrades": total_trades,
                "targetDistribution": self.target_distribution,
                "warning": warning
            }
            
        except Exception as e:
            logger.error(f"Error generating R:R distribution: {e}", exc_info=True)
            return {
                "buckets": {bucket["label"]: 0 for bucket in self.buckets},
                "percentages": {bucket["label"]: 0.0 for bucket in self.buckets},
                "avgRR": 0.0,
                "medianRR": 0.0,
                "totalTrades": 0,
                "targetDistribution": self.target_distribution,
                "warning": None
            }
    
    def _get_trades_with_rr(self) -> List[Dict]:
        """
        Query completed trades with R:R achieved values from database.
        
        Returns:
            list: List of trade dictionaries with rr_achieved values
        """
        try:
            conn = self.database._get_conn()
            
            # Query all completed trades with R:R achieved
            rows = conn.execute("""
                SELECT 
                    so.outcome_id,
                    so.signal_id,
                    so.rr_achieved,
                    so.pnl_pct,
                    so.closed_at,
                    s.symbol
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE so.closed_at IS NOT NULL
                AND so.outcome IS NOT NULL
                AND so.rr_achieved IS NOT NULL
                ORDER BY so.closed_at ASC
            """).fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error querying trades with R:R: {e}")
            return []
    
    def _group_into_buckets(self, trades: List[Dict]) -> Dict[str, int]:
        """
        Group trades into R:R buckets based on rr_achieved values.
        
        Args:
            trades: List of trade dictionaries with rr_achieved values
            
        Returns:
            dict: Dictionary mapping bucket label to trade count
        """
        # Initialize bucket counts
        bucket_counts = {bucket["label"]: 0 for bucket in self.buckets}
        
        # Assign each trade to appropriate bucket
        for trade in trades:
            rr_achieved = trade.get("rr_achieved", 0)
            
            # Find matching bucket
            for bucket in self.buckets:
                if bucket["min"] <= rr_achieved < bucket["max"]:
                    bucket_counts[bucket["label"]] += 1
                    break
                # Handle edge case: rr_achieved exactly equals max of last bucket
                elif bucket["label"] == ">2.0" and rr_achieved >= bucket["min"]:
                    bucket_counts[bucket["label"]] += 1
                    break
        
        return bucket_counts
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including data availability
        """
        try:
            # Check if we have any completed trades with R:R data
            conn = self.database._get_conn()
            row = conn.execute("""
                SELECT COUNT(*) as trade_count
                FROM signal_outcomes
                WHERE closed_at IS NOT NULL
                AND outcome IS NOT NULL
                AND rr_achieved IS NOT NULL
            """).fetchone()
            
            result = dict(row) if row else {"trade_count": 0}
            
            return {
                "initialized": True,
                "trade_count": result["trade_count"],
                "has_data": result["trade_count"] > 0
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "trade_count": 0,
                "has_data": False,
                "error": str(e)
            }
