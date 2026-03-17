"""
Quality Analysis Service for OpenClaw Trading Dashboard

Calculates performance metrics broken down by signal quality grade (A+, A, B, C)
to validate the quality scoring system and detect calibration issues.

Features:
- Calculate win rate per quality grade from signal_outcomes table
- Calculate average PnL per quality grade
- Calculate trade count per quality grade
- Calculate average confidence per quality grade
- Generate confidence vs. actual win rate scatter plot data
- Detect calibration warnings when performance deviates from expected
- Implement GET /api/analytics/quality-analysis endpoint
"""

import logging
from typing import Dict, List
from collections import defaultdict

from storage.database import Database

logger = logging.getLogger(__name__)


class QualityAnalysisService:
    """
    Service for analyzing performance by signal quality grade.
    
    Responsibilities:
    - Query signal_outcomes joined with signals table to get quality grades
    - Calculate win rate per quality grade: (winning trades / total trades) × 100
    - Calculate average PnL per quality grade
    - Calculate trade count per quality grade
    - Calculate average confidence per quality grade
    - Generate scatter plot data: confidence vs. actual win rate
    - Detect calibration warnings when performance deviates significantly
    
    Quality Grades:
    - A+: Highest quality signals (expected win rate: 65-75%)
    - A: High quality signals (expected win rate: 60-70%)
    - B: Medium quality signals (expected win rate: 55-65%)
    - C: Lower quality signals (expected win rate: 50-60%)
    """
    
    def __init__(self, database: Database = None):
        """
        Initialize quality analysis service.
        
        Args:
            database: Database instance (creates new if None)
        """
        self.database = database or Database()
        
        # Expected win rate ranges for calibration detection
        self.expected_win_rates = {
            "A+": (65, 75),
            "A": (60, 70),
            "B": (55, 65),
            "C": (50, 60)
        }
        
        logger.info("QualityAnalysisService initialized")
    
    def get_quality_analysis(self) -> Dict:
        """
        Get comprehensive quality grade performance analysis.
        
        Returns:
            dict: Quality analysis data including:
                - qualityMetrics: List of metrics per quality grade
                - scatterData: Confidence vs. win rate scatter plot data
                - calibrationWarnings: List of calibration issues detected
        """
        try:
            # Get trades grouped by quality grade
            trades_by_quality = self._get_trades_by_quality()
            
            if not trades_by_quality:
                logger.warning("No completed trades available for quality analysis")
                return {
                    "qualityMetrics": [],
                    "scatterData": [],
                    "calibrationWarnings": []
                }
            
            # Calculate metrics for each quality grade
            quality_metrics = []
            scatter_data = []
            calibration_warnings = []
            
            for quality in ["A+", "A", "B", "C"]:
                trades = trades_by_quality.get(quality, [])
                
                if not trades:
                    # Include quality grade even if no trades
                    quality_metrics.append({
                        "quality": quality,
                        "totalTrades": 0,
                        "winRate": 0.0,
                        "avgPnL": 0.0,
                        "totalPnL": 0.0,
                        "avgConfidence": 0.0
                    })
                    continue
                
                # Calculate metrics
                metrics = self._calculate_quality_metrics(quality, trades)
                quality_metrics.append(metrics)
                
                # Add to scatter plot data
                scatter_data.append({
                    "quality": quality,
                    "confidence": metrics["avgConfidence"],
                    "winRate": metrics["winRate"],
                    "tradeCount": metrics["totalTrades"]
                })
                
                # Check for calibration issues
                warning = self._check_calibration(quality, metrics)
                if warning:
                    calibration_warnings.append(warning)
            
            return {
                "qualityMetrics": quality_metrics,
                "scatterData": scatter_data,
                "calibrationWarnings": calibration_warnings
            }
            
        except Exception as e:
            logger.error(f"Error generating quality analysis: {e}", exc_info=True)
            return {
                "qualityMetrics": [],
                "scatterData": [],
                "calibrationWarnings": []
            }
    
    def _get_trades_by_quality(self) -> Dict[str, List[Dict]]:
        """
        Query completed trades from database grouped by quality grade.
        
        Returns:
            dict: Dictionary mapping quality grade to list of trade dictionaries
        """
        try:
            conn = self.database._get_conn()
            
            # Query all completed trades with quality grade and confidence
            rows = conn.execute("""
                SELECT 
                    s.quality,
                    s.confidence,
                    so.outcome,
                    so.pnl_pct,
                    so.closed_at
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE so.closed_at IS NOT NULL
                AND so.outcome IS NOT NULL
                ORDER BY s.quality, so.closed_at ASC
            """).fetchall()
            
            # Group trades by quality grade
            trades_by_quality = defaultdict(list)
            for row in rows:
                trade = dict(row)
                quality = trade["quality"]
                trades_by_quality[quality].append(trade)
            
            return dict(trades_by_quality)
            
        except Exception as e:
            logger.error(f"Error querying trades by quality: {e}")
            return {}
    
    def _calculate_quality_metrics(self, quality: str, trades: List[Dict]) -> Dict:
        """
        Calculate performance metrics for a single quality grade.
        
        Args:
            quality: Quality grade (A+, A, B, C)
            trades: List of trade dictionaries for this quality grade
            
        Returns:
            dict: Quality grade performance metrics
        """
        total_trades = len(trades)
        
        # Separate winning and losing trades
        winning_trades = [t for t in trades if t.get("outcome") == "WIN"]
        losing_trades = [t for t in trades if t.get("outcome") == "LOSS"]
        
        # Calculate win rate
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate average and total PnL
        all_pnls = [t.get("pnl_pct", 0) for t in trades]
        avg_pnl = sum(all_pnls) / len(all_pnls) if all_pnls else 0
        total_pnl = sum(all_pnls)
        
        # Calculate average confidence
        confidences = [t.get("confidence", 0) for t in trades]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "quality": quality,
            "totalTrades": total_trades,
            "winRate": round(win_rate, 2),
            "avgPnL": round(avg_pnl, 2),
            "totalPnL": round(total_pnl, 2),
            "avgConfidence": round(avg_confidence, 2)
        }
    
    def _check_calibration(self, quality: str, metrics: Dict) -> Dict:
        """
        Check if quality grade performance deviates significantly from expected.
        
        Calibration is considered poor if:
        - Win rate is outside expected range by more than 10 percentage points
        - Trade count is too low for statistical significance (< 20 trades)
        
        Args:
            quality: Quality grade (A+, A, B, C)
            metrics: Calculated metrics for this quality grade
            
        Returns:
            dict: Calibration warning or None if calibration is good
        """
        win_rate = metrics["winRate"]
        trade_count = metrics["totalTrades"]
        
        # Get expected win rate range
        expected_min, expected_max = self.expected_win_rates.get(quality, (50, 60))
        
        # Check for low sample size
        if trade_count < 20:
            return {
                "quality": quality,
                "severity": "info",
                "message": f"Low sample size for {quality} grade ({trade_count} trades). Need at least 20 trades for reliable calibration.",
                "actualWinRate": win_rate,
                "expectedRange": f"{expected_min}-{expected_max}%",
                "tradeCount": trade_count
            }
        
        # Check if win rate is significantly below expected
        if win_rate < expected_min - 10:
            return {
                "quality": quality,
                "severity": "warning",
                "message": f"{quality} grade performing significantly below expected. Actual: {win_rate:.1f}%, Expected: {expected_min}-{expected_max}%",
                "actualWinRate": win_rate,
                "expectedRange": f"{expected_min}-{expected_max}%",
                "tradeCount": trade_count,
                "deviation": round(win_rate - expected_min, 2)
            }
        
        # Check if win rate is significantly above expected
        if win_rate > expected_max + 10:
            return {
                "quality": quality,
                "severity": "info",
                "message": f"{quality} grade performing significantly above expected. Actual: {win_rate:.1f}%, Expected: {expected_min}-{expected_max}%",
                "actualWinRate": win_rate,
                "expectedRange": f"{expected_min}-{expected_max}%",
                "tradeCount": trade_count,
                "deviation": round(win_rate - expected_max, 2)
            }
        
        # Calibration is good
        return None
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including data availability
        """
        try:
            # Check if we have any completed trades with quality grades
            conn = self.database._get_conn()
            row = conn.execute("""
                SELECT 
                    COUNT(DISTINCT s.quality) as quality_count,
                    COUNT(*) as trade_count
                FROM signal_outcomes so
                JOIN signals s ON so.signal_id = s.signal_id
                WHERE so.closed_at IS NOT NULL
                AND so.outcome IS NOT NULL
            """).fetchone()
            
            result = dict(row) if row else {"quality_count": 0, "trade_count": 0}
            
            return {
                "initialized": True,
                "quality_count": result["quality_count"],
                "trade_count": result["trade_count"],
                "has_data": result["trade_count"] > 0
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "quality_count": 0,
                "trade_count": 0,
                "has_data": False,
                "error": str(e)
            }
