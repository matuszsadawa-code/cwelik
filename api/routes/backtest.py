"""
Backtesting API Routes

Provides endpoints for retrieving backtesting results, equity curves, and comparing runs.
"""

import logging
from typing import List
from fastapi import APIRouter, Query, HTTPException, Path

from api.services.backtest_service import BacktestService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/backtest", tags=["backtest"])

# Initialize service
backtest_service = BacktestService()


@router.get("/runs")
async def list_backtest_runs():
    """
    List all available backtest runs with summary metrics.
    
    Returns:
        list: List of backtest run summaries including:
            - id: Backtest run ID
            - name: Human-readable name
            - date: Run date/timestamp
            - parameters: Configuration parameters (start_date, end_date, symbols, initial_capital)
            - summary: Summary metrics (total_trades, win_rate, profit_factor, total_return, sharpe_ratio, max_drawdown)
            - status: Run status (completed, failed, in_progress)
    
    Example:
        GET /api/backtest/runs
    """
    try:
        runs = backtest_service.list_backtest_runs()
        return {
            "runs": runs,
            "total": len(runs)
        }
    except Exception as e:
        logger.error(f"Error listing backtest runs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/runs/{run_id}")
async def get_backtest_results(
    run_id: str = Path(..., description="Backtest run ID")
):
    """
    Get detailed results for a specific backtest run.
    
    Retrieves comprehensive backtest results including equity curve, performance metrics,
    complete trade list, drawdown periods, and per-symbol performance breakdown.
    
    Args:
        run_id: Backtest run ID
        
    Returns:
        dict: Detailed backtest results including:
            - id: Run ID
            - name: Run name
            - timestamp: Run timestamp
            - config: Configuration parameters used
            - metrics: Performance metrics (win_rate, profit_factor, sharpe_ratio, etc.)
            - equity_curve: Equity curve data points for visualization
            - trades: List of all trades with entry/exit details
            - drawdowns: Drawdown periods with depth and duration
            - symbol_performance: Per-symbol performance breakdown
            - status: Run status
    
    Example:
        GET /api/backtest/runs/backtest_2024_01_15_143022
    """
    try:
        results = backtest_service.get_backtest_results(run_id)
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Backtest run not found: {run_id}"
            )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving backtest results: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/compare")
async def compare_backtest_runs(
    run_ids: List[str] = Query(..., description="List of backtest run IDs to compare (2-4 runs)")
):
    """
    Compare multiple backtest runs side-by-side.
    
    Allows comparison of 2-4 backtest runs with side-by-side metrics comparison
    and combined equity curves for overlay visualization.
    
    Args:
        run_ids: List of 2-4 backtest run IDs to compare
        
    Returns:
        dict: Comparison data including:
            - runs: List of run summaries (id, name, timestamp)
            - metrics_comparison: Side-by-side metrics comparison
            - equity_curves: Combined equity curves for overlay chart
    
    Example:
        GET /api/backtest/compare?run_ids=run1&run_ids=run2&run_ids=run3
    """
    try:
        # Validate number of runs
        if len(run_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 backtest runs required for comparison"
            )
        
        if len(run_ids) > 4:
            raise HTTPException(
                status_code=400,
                detail="Maximum 4 backtest runs can be compared at once"
            )
        
        comparison = backtest_service.compare_backtest_runs(run_ids)
        
        if "error" in comparison:
            raise HTTPException(
                status_code=400,
                detail=comparison["error"]
            )
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing backtest runs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/status")
async def get_service_status():
    """
    Get backtest service status.
    
    Returns service health information including total run count,
    latest run details, and data availability status.
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - backtest_dir: Directory containing backtest results
            - total_runs: Total number of backtest runs available
            - has_data: Whether any backtest data is available
            - latest_run: Summary of most recent backtest run
    """
    try:
        return backtest_service.get_service_status()
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        return {
            "initialized": False,
            "total_runs": 0,
            "has_data": False,
            "error": str(e)
        }
