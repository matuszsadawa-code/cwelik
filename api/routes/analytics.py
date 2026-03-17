"""
Analytics API routes for OpenClaw Trading Dashboard

Provides endpoints for performance analytics including:
- Equity curve visualization
- PnL breakdown by time period
- Per-symbol performance statistics
- Risk-adjusted returns
- Quality grade analysis
- R:R distribution
"""

import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from api.services.equity_curve_service import EquityCurveService
from api.services.pnl_breakdown_service import PnLBreakdownService
from api.services.symbol_performance_service import SymbolPerformanceService
from api.services.risk_metrics_service import RiskMetricsService
from api.services.quality_analysis_service import QualityAnalysisService
from api.services.rr_distribution_service import RRDistributionService
from api.services.symbol_pnl_service import SymbolPnLService
from storage.database import Database

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Initialize services
equity_curve_service = None
pnl_breakdown_service = None
symbol_performance_service = None
risk_metrics_service = None
quality_analysis_service = None
rr_distribution_service = None
symbol_pnl_service = None


def init_analytics_services():
    """Initialize analytics services"""
    global equity_curve_service, pnl_breakdown_service, symbol_performance_service, risk_metrics_service, quality_analysis_service, rr_distribution_service, symbol_pnl_service
    
    db = Database()
    equity_curve_service = EquityCurveService(db)
    pnl_breakdown_service = PnLBreakdownService(db)
    symbol_performance_service = SymbolPerformanceService(db)
    risk_metrics_service = RiskMetricsService(db)
    quality_analysis_service = QualityAnalysisService(db)
    rr_distribution_service = RRDistributionService(db)
    symbol_pnl_service = SymbolPnLService(db)
    logger.info("Analytics services initialized")


@router.get("/equity-curve")
async def get_equity_curve(
    time_range: str = Query(
        default="all",
        description="Time range filter: 1d, 7d, 30d, 90d, 1y, all",
        regex="^(1d|7d|30d|90d|1y|all)$"
    )
):
    """
    Get equity curve data with drawdown periods
    
    Generates equity curve from equity_snapshots table and identifies
    drawdown periods exceeding 5%.
    
    Args:
        time_range: Time range filter (1d, 7d, 30d, 90d, 1y, all)
        
    Returns:
        dict: Equity curve data including:
            - timestamps: List of Unix timestamps in milliseconds
            - equityValues: List of equity values
            - drawdownPeriods: List of drawdown periods with:
                - startDate: Start timestamp (ms)
                - endDate: End timestamp (ms)
                - depth: Drawdown depth as percentage (negative)
                - duration: Duration in minutes
                - peakEquity: Peak equity before drawdown
                - troughEquity: Lowest equity during drawdown
            - peakEquity: Peak equity value
            - currentEquity: Current equity value
            - maxDrawdown: Maximum drawdown depth (%)
            - maxDrawdownDuration: Maximum drawdown duration (minutes)
    
    Example response:
    ```json
    {
        "timestamps": [1704067200000, 1704153600000, ...],
        "equityValues": [10000, 10250, 10100, ...],
        "drawdownPeriods": [
            {
                "startDate": 1704153600000,
                "endDate": 1704326400000,
                "depth": -8.5,
                "duration": 2880,
                "peakEquity": 10250,
                "troughEquity": 9378.75
            }
        ],
        "peakEquity": 10500,
        "currentEquity": 10350,
        "maxDrawdown": -8.5,
        "maxDrawdownDuration": 2880
    }
    ```
    """
    if not equity_curve_service:
        init_analytics_services()
    
    try:
        data = equity_curve_service.get_equity_curve(time_range)
        return data
    except Exception as e:
        logger.error(f"Error getting equity curve: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating equity curve: {str(e)}")


@router.get("/equity-curve/status")
async def get_equity_curve_status():
    """
    Get equity curve service status
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - snapshot_count: Number of equity snapshots in database
            - has_data: Whether any equity data is available
    """
    if not equity_curve_service:
        init_analytics_services()
    
    try:
        status = equity_curve_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")


@router.get("/pnl-breakdown")
async def get_pnl_breakdown(
    time_range: str = Query(
        default="all",
        description="Time range filter: 1d, 7d, 30d, 90d, 1y, all",
        regex="^(1d|7d|30d|90d|1y|all)$"
    )
):
    """
    Get PnL breakdown by day, week, and month
    
    Aggregates PnL from signal_outcomes table by different time periods,
    calculates cumulative PnL, and identifies best/worst performing periods.
    
    Args:
        time_range: Time range filter (1d, 7d, 30d, 90d, 1y, all)
        
    Returns:
        dict: PnL breakdown data including:
            - daily: List of daily PnL data points with:
                - date: Date string (YYYY-MM-DD)
                - pnl: PnL percentage for that day
                - cumulativePnL: Cumulative PnL up to that day
            - weekly: List of weekly PnL data points with:
                - week: Week string (YYYY-Www)
                - pnl: PnL percentage for that week
                - cumulativePnL: Cumulative PnL up to that week
            - monthly: List of monthly PnL data points with:
                - month: Month string (YYYY-MM)
                - pnl: PnL percentage for that month
                - cumulativePnL: Cumulative PnL up to that month
            - bestDay: Best performing day {date, pnl}
            - worstDay: Worst performing day {date, pnl}
            - bestWeek: Best performing week {week, pnl}
            - worstWeek: Worst performing week {week, pnl}
            - bestMonth: Best performing month {month, pnl}
            - worstMonth: Worst performing month {month, pnl}
    
    Example response:
    ```json
    {
        "daily": [
            {"date": "2024-01-01", "pnl": 2.5, "cumulativePnL": 2.5},
            {"date": "2024-01-02", "pnl": -1.2, "cumulativePnL": 1.3},
            {"date": "2024-01-03", "pnl": 3.8, "cumulativePnL": 5.1}
        ],
        "weekly": [
            {"week": "2024-W01", "pnl": 5.1, "cumulativePnL": 5.1},
            {"week": "2024-W02", "pnl": 2.3, "cumulativePnL": 7.4}
        ],
        "monthly": [
            {"month": "2024-01", "pnl": 12.5, "cumulativePnL": 12.5}
        ],
        "bestDay": {"date": "2024-01-03", "pnl": 3.8},
        "worstDay": {"date": "2024-01-02", "pnl": -1.2},
        "bestWeek": {"week": "2024-W01", "pnl": 5.1},
        "worstWeek": {"week": "2024-W02", "pnl": 2.3},
        "bestMonth": {"month": "2024-01", "pnl": 12.5},
        "worstMonth": {"month": "2024-01", "pnl": 12.5}
    }
    ```
    """
    if not pnl_breakdown_service:
        init_analytics_services()
    
    try:
        data = pnl_breakdown_service.get_pnl_breakdown(time_range)
        return data
    except Exception as e:
        logger.error(f"Error getting PnL breakdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating PnL breakdown: {str(e)}")


@router.get("/pnl-breakdown/status")
async def get_pnl_breakdown_status():
    """
    Get PnL breakdown service status
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - trade_count: Number of completed trades in database
            - has_data: Whether any trade data is available
    """
    if not pnl_breakdown_service:
        init_analytics_services()
    
    try:
        status = pnl_breakdown_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")


@router.get("/symbol-performance")
async def get_symbol_performance():
    """
    Get per-symbol performance statistics
    
    Calculates detailed performance metrics for each symbol from signal_outcomes table,
    including win rate, profit factor, average PnL, total PnL, best/worst trades,
    average hold time, and trade count.
    
    Returns:
        dict: Symbol performance data including:
            - symbols: List of symbol performance dictionaries, each containing:
                - symbol: Symbol name (e.g., "BTCUSDT")
                - totalTrades: Total number of trades for this symbol
                - winRate: Win rate percentage (0-100)
                - profitFactor: Profit factor (sum of wins / abs(sum of losses))
                - avgPnL: Average PnL percentage per trade
                - totalPnL: Total PnL percentage for all trades
                - bestTrade: Best trade PnL percentage
                - worstTrade: Worst trade PnL percentage
                - avgHoldTime: Average hold time in minutes
    
    Example response:
    ```json
    {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "totalTrades": 45,
                "winRate": 62.22,
                "profitFactor": 2.15,
                "avgPnL": 1.85,
                "totalPnL": 83.25,
                "bestTrade": 12.5,
                "worstTrade": -5.2,
                "avgHoldTime": 245.5
            },
            {
                "symbol": "ETHUSDT",
                "totalTrades": 38,
                "winRate": 55.26,
                "profitFactor": 1.45,
                "avgPnL": 0.95,
                "totalPnL": 36.1,
                "bestTrade": 8.3,
                "worstTrade": -6.1,
                "avgHoldTime": 198.2
            }
        ]
    }
    ```
    
    Note: Symbols are sorted by totalPnL descending (best performers first)
    """
    if not symbol_performance_service:
        init_analytics_services()
    
    try:
        data = symbol_performance_service.get_symbol_performance()
        return data
    except Exception as e:
        logger.error(f"Error getting symbol performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating symbol performance: {str(e)}")


@router.get("/symbol-performance/status")
async def get_symbol_performance_status():
    """
    Get symbol performance service status
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - symbol_count: Number of unique symbols with trades
            - trade_count: Number of completed trades in database
            - has_data: Whether any trade data is available
    """
    if not symbol_performance_service:
        init_analytics_services()
    
    try:
        status = symbol_performance_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")


@router.get("/risk-metrics")
async def get_risk_metrics():
    """
    Get risk-adjusted return metrics
    
    Calculates comprehensive risk-adjusted return metrics including Sharpe ratio,
    Sortino ratio, Calmar ratio, maximum drawdown, average drawdown duration,
    rolling Sharpe ratio time series, and drawdown duration histogram.
    
    Returns:
        dict: Risk metrics including:
            - sharpeRatio: Annualized Sharpe ratio
            - sortinoRatio: Sortino ratio (downside deviation)
            - calmarRatio: Calmar ratio (return / max drawdown)
            - maxDrawdown: Maximum drawdown percentage
            - avgDrawdownDuration: Average drawdown duration in minutes
            - rollingSharpe: List of rolling Sharpe ratio data points with:
                - timestamp: ISO timestamp string
                - sharpe: Sharpe ratio value
            - drawdownHistogram: Histogram of drawdown durations with:
                - buckets: List of bucket labels
                - counts: List of counts per bucket
    
    Example response:
    ```json
    {
        "sharpeRatio": 1.42,
        "sortinoRatio": 2.15,
        "calmarRatio": 1.85,
        "maxDrawdown": -12.5,
        "avgDrawdownDuration": 245.5,
        "rollingSharpe": [
            {"timestamp": "2024-01-01T00:00:00", "sharpe": 1.25},
            {"timestamp": "2024-01-02T00:00:00", "sharpe": 1.38},
            {"timestamp": "2024-01-03T00:00:00", "sharpe": 1.42}
        ],
        "drawdownHistogram": {
            "buckets": ["<1h", "1-4h", "4-24h", "1-7d", ">7d"],
            "counts": [5, 12, 8, 3, 1]
        }
    }
    ```
    
    Notes:
    - Sharpe ratio: (mean return - risk-free rate) / std dev × √252
    - Sortino ratio: Uses downside deviation instead of total std dev
    - Calmar ratio: Total return / max drawdown
    - Rolling Sharpe: 30-day rolling window
    - Drawdown histogram: Groups drawdowns by duration
    """
    if not risk_metrics_service:
        init_analytics_services()
    
    try:
        data = risk_metrics_service.get_risk_metrics()
        return data
    except Exception as e:
        logger.error(f"Error getting risk metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculating risk metrics: {str(e)}")


@router.get("/risk-metrics/status")
async def get_risk_metrics_status():
    """
    Get risk metrics service status
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - returns_count: Number of completed trades with PnL data
            - equity_snapshots_count: Number of equity snapshots
            - has_data: Whether sufficient data is available for calculations
    """
    if not risk_metrics_service:
        init_analytics_services()
    
    try:
        status = risk_metrics_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")


@router.get("/quality-analysis")
async def get_quality_analysis():
    """
    Get quality grade performance analysis
    
    Analyzes performance broken down by signal quality grade (A+, A, B, C)
    to validate the quality scoring system and detect calibration issues.
    
    Returns:
        dict: Quality analysis data including:
            - qualityMetrics: List of metrics per quality grade, each containing:
                - quality: Quality grade (A+, A, B, C)
                - totalTrades: Total number of trades for this grade
                - winRate: Win rate percentage (0-100)
                - avgPnL: Average PnL percentage per trade
                - totalPnL: Total PnL percentage for all trades
                - avgConfidence: Average confidence score (0-100)
            - scatterData: Confidence vs. win rate scatter plot data with:
                - quality: Quality grade
                - confidence: Average confidence score
                - winRate: Actual win rate
                - tradeCount: Number of trades
            - calibrationWarnings: List of calibration issues detected with:
                - quality: Quality grade with issue
                - severity: "info" or "warning"
                - message: Description of the issue
                - actualWinRate: Actual win rate achieved
                - expectedRange: Expected win rate range
                - tradeCount: Number of trades
                - deviation: Deviation from expected (if applicable)
    
    Example response:
    ```json
    {
        "qualityMetrics": [
            {
                "quality": "A+",
                "totalTrades": 25,
                "winRate": 68.0,
                "avgPnL": 2.45,
                "totalPnL": 61.25,
                "avgConfidence": 85.5
            },
            {
                "quality": "A",
                "totalTrades": 42,
                "winRate": 64.29,
                "avgPnL": 1.85,
                "totalPnL": 77.7,
                "avgConfidence": 75.2
            },
            {
                "quality": "B",
                "totalTrades": 38,
                "winRate": 57.89,
                "avgPnL": 1.15,
                "totalPnL": 43.7,
                "avgConfidence": 65.8
            },
            {
                "quality": "C",
                "totalTrades": 15,
                "winRate": 53.33,
                "avgPnL": 0.65,
                "totalPnL": 9.75,
                "avgConfidence": 55.3
            }
        ],
        "scatterData": [
            {"quality": "A+", "confidence": 85.5, "winRate": 68.0, "tradeCount": 25},
            {"quality": "A", "confidence": 75.2, "winRate": 64.29, "tradeCount": 42},
            {"quality": "B", "confidence": 65.8, "winRate": 57.89, "tradeCount": 38},
            {"quality": "C", "confidence": 55.3, "winRate": 53.33, "tradeCount": 15}
        ],
        "calibrationWarnings": [
            {
                "quality": "C",
                "severity": "info",
                "message": "Low sample size for C grade (15 trades). Need at least 20 trades for reliable calibration.",
                "actualWinRate": 53.33,
                "expectedRange": "50-60%",
                "tradeCount": 15
            }
        ]
    }
    ```
    
    Notes:
    - Quality grades represent signal quality: A+ (highest) to C (lowest)
    - Expected win rates: A+ (65-75%), A (60-70%), B (55-65%), C (50-60%)
    - Calibration warnings appear when performance deviates >10% from expected
    - Low sample size warnings appear when trade count < 20
    """
    if not quality_analysis_service:
        init_analytics_services()
    
    try:
        data = quality_analysis_service.get_quality_analysis()
        return data
    except Exception as e:
        logger.error(f"Error getting quality analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating quality analysis: {str(e)}")


@router.get("/quality-analysis/status")
async def get_quality_analysis_status():
    """
    Get quality analysis service status
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - quality_count: Number of unique quality grades with trades
            - trade_count: Number of completed trades in database
            - has_data: Whether any trade data is available
    """
    if not quality_analysis_service:
        init_analytics_services()
    
    try:
        status = quality_analysis_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")



@router.get("/rr-distribution")
async def get_rr_distribution():
    """
    Get risk-reward ratio distribution analysis
    
    Analyzes the distribution of achieved risk-reward ratios from completed trades,
    groups them into predefined buckets, and compares actual vs. target distribution.
    
    Returns:
        dict: R:R distribution data including:
            - buckets: Dictionary mapping bucket label to trade count with:
                - "<0.5": Trades with R:R < 0.5 (very poor)
                - "0.5-1.0": Trades with R:R 0.5-1.0 (below target)
                - "1.0-1.5": Trades with R:R 1.0-1.5 (acceptable)
                - "1.5-2.0": Trades with R:R 1.5-2.0 (good)
                - ">2.0": Trades with R:R > 2.0 (excellent)
            - percentages: Dictionary mapping bucket label to percentage
            - avgRR: Average R:R achieved across all trades
            - medianRR: Median R:R achieved
            - totalTrades: Total number of trades analyzed
            - targetDistribution: Target distribution percentages for comparison
            - warning: Warning object if average R:R < 1.0 with:
                - severity: "warning"
                - message: Description of the issue
                - avgRR: Average R:R value
                - recommendation: Suggested actions
    
    Example response:
    ```json
    {
        "buckets": {
            "<0.5": 8,
            "0.5-1.0": 12,
            "1.0-1.5": 18,
            "1.5-2.0": 15,
            ">2.0": 7
        },
        "percentages": {
            "<0.5": 13.33,
            "0.5-1.0": 20.0,
            "1.0-1.5": 30.0,
            "1.5-2.0": 25.0,
            ">2.0": 11.67
        },
        "avgRR": 1.35,
        "medianRR": 1.28,
        "totalTrades": 60,
        "targetDistribution": {
            "<0.5": 15.0,
            "0.5-1.0": 20.0,
            "1.0-1.5": 30.0,
            "1.5-2.0": 25.0,
            ">2.0": 10.0
        },
        "warning": null
    }
    ```
    
    Example with warning (avgRR < 1.0):
    ```json
    {
        "buckets": {...},
        "percentages": {...},
        "avgRR": 0.85,
        "medianRR": 0.78,
        "totalTrades": 45,
        "targetDistribution": {...},
        "warning": {
            "severity": "warning",
            "message": "Average R:R (0.85) is below 1.0. System is not achieving target risk-reward ratios.",
            "avgRR": 0.85,
            "recommendation": "Review stop loss placement and take profit targets. Consider tightening entry criteria or adjusting position sizing."
        }
    }
    ```
    
    Notes:
    - R:R (Risk-Reward) = (Exit Price - Entry Price) / (Entry Price - Stop Loss)
    - Positive R:R indicates profit relative to risk taken
    - Target is typically R:R >= 1.5 for profitable trading
    - Warning appears when average R:R < 1.0 (losing more than risking)
    - Data comes from rr_achieved column in signal_outcomes table
    """
    if not rr_distribution_service:
        init_analytics_services()
    
    try:
        data = rr_distribution_service.get_rr_distribution()
        return data
    except Exception as e:
        logger.error(f"Error getting R:R distribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating R:R distribution: {str(e)}")


@router.get("/rr-distribution/status")
async def get_rr_distribution_status():
    """
    Get R:R distribution service status
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - trade_count: Number of completed trades with R:R data
            - has_data: Whether any R:R data is available
    """
    if not rr_distribution_service:
        init_analytics_services()
    
    try:
        status = rr_distribution_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")



@router.get("/symbol-pnl/{symbol}")
async def get_symbol_pnl(symbol: str):
    """
    Get per-symbol PnL data including cumulative PnL and trade-by-trade details
    
    Retrieves all trades for a specific symbol and calculates cumulative PnL,
    win rate, profit factor, and provides detailed trade information for
    visualization.
    
    Args:
        symbol: Symbol name (e.g., "BTCUSDT")
        
    Returns:
        dict: Symbol PnL data including:
            - symbol: Symbol name
            - trades: List of trade data points, each containing:
                - tradeId: Unique trade identifier
                - signalId: Associated signal ID
                - outcome: "WIN" or "LOSS"
                - pnl: PnL percentage for this trade
                - cumulativePnL: Cumulative PnL up to this trade
                - entryPrice: Entry price
                - exitPrice: Exit price
                - exitReason: Reason for exit (TP/SL/manual)
                - mfe: Maximum Favorable Excursion
                - mae: Maximum Adverse Excursion
                - rrAchieved: Risk-reward ratio achieved
                - duration: Trade duration in minutes
                - timestamp: Trade close timestamp (milliseconds)
            - winRate: Win rate percentage (0-100)
            - profitFactor: Profit factor (sum of wins / abs(sum of losses))
            - totalTrades: Total number of trades
            - totalPnL: Total cumulative PnL percentage
    
    Example response:
    ```json
    {
        "symbol": "BTCUSDT",
        "trades": [
            {
                "tradeId": "trade_001",
                "signalId": "signal_001",
                "outcome": "WIN",
                "pnl": 2.5,
                "cumulativePnL": 2.5,
                "entryPrice": 45000.0,
                "exitPrice": 46125.0,
                "exitReason": "TP",
                "mfe": 3.2,
                "mae": -0.8,
                "rrAchieved": 2.1,
                "duration": 245,
                "timestamp": 1704067200000
            },
            {
                "tradeId": "trade_002",
                "signalId": "signal_002",
                "outcome": "LOSS",
                "pnl": -1.2,
                "cumulativePnL": 1.3,
                "entryPrice": 46500.0,
                "exitPrice": 45942.0,
                "exitReason": "SL",
                "mfe": 0.5,
                "mae": -1.5,
                "rrAchieved": -0.8,
                "duration": 120,
                "timestamp": 1704153600000
            }
        ],
        "winRate": 62.5,
        "profitFactor": 2.15,
        "totalTrades": 45,
        "totalPnL": 83.25
    }
    ```
    
    Notes:
    - Trades are sorted by close timestamp (ascending)
    - Cumulative PnL is calculated as running sum of individual trade PnLs
    - Win rate = (winning trades / total trades) × 100
    - Profit factor = sum(winning PnLs) / abs(sum(losing PnLs))
    - Empty trades array returned if no trades found for symbol
    """
    if not symbol_pnl_service:
        init_analytics_services()
    
    try:
        data = symbol_pnl_service.get_symbol_pnl(symbol)
        return data
    except Exception as e:
        logger.error(f"Error getting symbol PnL for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting symbol PnL: {str(e)}")


@router.get("/symbol-pnl-multi")
async def get_multi_symbol_pnl(
    symbols: str = Query(
        ...,
        description="Comma-separated list of symbols (max 4)",
        regex="^[A-Z0-9]+(,[A-Z0-9]+){0,3}$"
    )
):
    """
    Get PnL data for multiple symbols for comparison
    
    Retrieves PnL data for up to 4 symbols to enable side-by-side comparison
    of performance metrics and cumulative PnL curves.
    
    Args:
        symbols: Comma-separated list of symbols (e.g., "BTCUSDT,ETHUSDT,BNBUSDT")
                 Maximum 4 symbols allowed
        
    Returns:
        dict: Multi-symbol PnL data including:
            - symbols: List of symbol PnL data (same format as /symbol-pnl/{symbol})
    
    Example request:
        GET /api/analytics/symbol-pnl-multi?symbols=BTCUSDT,ETHUSDT,BNBUSDT
    
    Example response:
    ```json
    {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "trades": [...],
                "winRate": 62.5,
                "profitFactor": 2.15,
                "totalTrades": 45,
                "totalPnL": 83.25
            },
            {
                "symbol": "ETHUSDT",
                "trades": [...],
                "winRate": 58.3,
                "profitFactor": 1.85,
                "totalTrades": 38,
                "totalPnL": 45.6
            },
            {
                "symbol": "BNBUSDT",
                "trades": [...],
                "winRate": 55.0,
                "profitFactor": 1.45,
                "totalTrades": 32,
                "totalPnL": 28.4
            }
        ]
    }
    ```
    
    Notes:
    - Maximum 4 symbols allowed for comparison
    - Returns 400 error if more than 4 symbols requested
    - Empty trades array returned for symbols with no trades
    """
    if not symbol_pnl_service:
        init_analytics_services()
    
    try:
        symbol_list = [s.strip() for s in symbols.split(',')]
        
        if len(symbol_list) > 4:
            raise HTTPException(
                status_code=400,
                detail="Maximum 4 symbols allowed for comparison"
            )
        
        data = symbol_pnl_service.get_multi_symbol_pnl(symbol_list)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting multi-symbol PnL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting multi-symbol PnL: {str(e)}")


@router.get("/symbol-pnl/status")
async def get_symbol_pnl_status():
    """
    Get symbol PnL service status
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - symbol_count: Number of unique symbols with trades
            - trade_count: Number of completed trades in database
            - has_data: Whether any trade data is available
    """
    if not symbol_pnl_service:
        init_analytics_services()
    
    try:
        status = symbol_pnl_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")
