"""
Backtesting Service for OpenClaw Trading Dashboard

Retrieves and manages backtesting results including equity curves, performance metrics,
trade lists, and drawdown data. Supports comparison of multiple backtest runs.

Features:
- List available backtest runs with summary metrics
- Retrieve detailed backtest results for specific run
- Get equity curve data for visualization
- Get performance metrics (win rate, profit factor, Sharpe, etc.)
- Get trade list from backtest
- Get drawdown data
- Compare multiple backtest runs side-by-side
"""

import logging
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestService:
    """
    Service for retrieving and managing backtesting results.
    
    Responsibilities:
    - List available backtest runs from storage
    - Retrieve detailed results for specific backtest run
    - Extract equity curve, metrics, trades, drawdown data
    - Support comparison of multiple backtest runs
    """
    
    def __init__(self, backtest_dir: str = "backtesting/results"):
        """
        Initialize backtest service.
        
        Args:
            backtest_dir: Directory containing backtest result files
        """
        self.backtest_dir = backtest_dir
        
        # Ensure backtest directory exists
        Path(backtest_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BacktestService initialized with directory: {backtest_dir}")
    
    def list_backtest_runs(self) -> List[Dict]:
        """
        List all available backtest runs with summary metrics.
        
        Returns:
            list: List of backtest run summaries including:
                - id: Backtest run ID (filename without extension)
                - name: Human-readable name
                - date: Run date/timestamp
                - parameters: Configuration parameters used
                - summary: Summary metrics (win rate, profit factor, total trades)
                - status: Run status (completed, failed, in_progress)
        """
        try:
            backtest_runs = []
            
            # Scan backtest directory for result files
            backtest_path = Path(self.backtest_dir)
            
            if not backtest_path.exists():
                logger.warning(f"Backtest directory does not exist: {self.backtest_dir}")
                return []
            
            # Look for JSON result files
            for result_file in backtest_path.glob("*.json"):
                try:
                    with open(result_file, 'r') as f:
                        data = json.load(f)
                    
                    # Extract summary information
                    run_id = result_file.stem
                    
                    # Get basic info
                    config = data.get("config", {})
                    metrics = data.get("metrics", {})
                    
                    summary = {
                        "id": run_id,
                        "name": data.get("name", run_id),
                        "date": data.get("timestamp", result_file.stat().st_mtime),
                        "parameters": {
                            "start_date": config.get("start_date"),
                            "end_date": config.get("end_date"),
                            "symbols": config.get("symbols", []),
                            "initial_capital": config.get("initial_capital", 10000)
                        },
                        "summary": {
                            "total_trades": metrics.get("total_trades", 0),
                            "win_rate": round(metrics.get("win_rate", 0), 2),
                            "profit_factor": round(metrics.get("profit_factor", 0), 2),
                            "total_return": round(metrics.get("total_return_pct", 0), 2),
                            "sharpe_ratio": round(metrics.get("sharpe_ratio", 0), 2),
                            "max_drawdown": round(metrics.get("max_drawdown_pct", 0), 2)
                        },
                        "status": data.get("status", "completed")
                    }
                    
                    backtest_runs.append(summary)
                    
                except Exception as e:
                    logger.error(f"Error reading backtest file {result_file}: {e}")
                    continue
            
            # Sort by date (most recent first)
            backtest_runs.sort(key=lambda x: x["date"], reverse=True)
            
            logger.info(f"Found {len(backtest_runs)} backtest runs")
            return backtest_runs
            
        except Exception as e:
            logger.error(f"Error listing backtest runs: {e}", exc_info=True)
            return []
    
    def get_backtest_results(self, run_id: str) -> Optional[Dict]:
        """
        Get detailed results for a specific backtest run.
        
        Args:
            run_id: Backtest run ID
            
        Returns:
            dict: Detailed backtest results including:
                - id: Run ID
                - name: Run name
                - timestamp: Run timestamp
                - config: Configuration parameters
                - metrics: Performance metrics
                - equity_curve: Equity curve data points
                - trades: List of all trades
                - drawdowns: Drawdown periods
                - symbol_performance: Per-symbol performance breakdown
        """
        try:
            result_file = Path(self.backtest_dir) / f"{run_id}.json"
            
            if not result_file.exists():
                logger.warning(f"Backtest run not found: {run_id}")
                return None
            
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            # Format results for frontend
            results = {
                "id": run_id,
                "name": data.get("name", run_id),
                "timestamp": data.get("timestamp"),
                "config": data.get("config", {}),
                "metrics": self._format_metrics(data.get("metrics", {})),
                "equity_curve": self._format_equity_curve(data.get("equity_curve", [])),
                "trades": self._format_trades(data.get("trades", [])),
                "drawdowns": self._format_drawdowns(data.get("drawdowns", [])),
                "symbol_performance": data.get("symbol_performance", {}),
                "status": data.get("status", "completed")
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving backtest results for {run_id}: {e}", exc_info=True)
            return None
    
    def _format_metrics(self, metrics: Dict) -> Dict:
        """
        Format performance metrics for frontend display.
        
        Args:
            metrics: Raw metrics dictionary
            
        Returns:
            dict: Formatted metrics
        """
        return {
            "total_trades": metrics.get("total_trades", 0),
            "winning_trades": metrics.get("winning_trades", 0),
            "losing_trades": metrics.get("losing_trades", 0),
            "win_rate": round(metrics.get("win_rate", 0), 2),
            "profit_factor": round(metrics.get("profit_factor", 0), 2),
            "total_return_pct": round(metrics.get("total_return_pct", 0), 2),
            "total_return_abs": round(metrics.get("total_return_abs", 0), 2),
            "sharpe_ratio": round(metrics.get("sharpe_ratio", 0), 2),
            "sortino_ratio": round(metrics.get("sortino_ratio", 0), 2),
            "calmar_ratio": round(metrics.get("calmar_ratio", 0), 2),
            "max_drawdown_pct": round(metrics.get("max_drawdown_pct", 0), 2),
            "max_drawdown_abs": round(metrics.get("max_drawdown_abs", 0), 2),
            "avg_drawdown_pct": round(metrics.get("avg_drawdown_pct", 0), 2),
            "max_drawdown_duration_days": metrics.get("max_drawdown_duration_days", 0),
            "avg_trade_return": round(metrics.get("avg_trade_return", 0), 2),
            "avg_win": round(metrics.get("avg_win", 0), 2),
            "avg_loss": round(metrics.get("avg_loss", 0), 2),
            "largest_win": round(metrics.get("largest_win", 0), 2),
            "largest_loss": round(metrics.get("largest_loss", 0), 2),
            "avg_trade_duration_hours": round(metrics.get("avg_trade_duration_hours", 0), 2),
            "expectancy": round(metrics.get("expectancy", 0), 2)
        }
    
    def _format_equity_curve(self, equity_curve: List) -> List[Dict]:
        """
        Format equity curve data for charting.
        
        Args:
            equity_curve: Raw equity curve data
            
        Returns:
            list: Formatted equity curve points
        """
        formatted = []
        
        for point in equity_curve:
            if isinstance(point, dict):
                formatted.append({
                    "timestamp": point.get("timestamp"),
                    "equity": round(point.get("equity", 0), 2),
                    "drawdown_pct": round(point.get("drawdown_pct", 0), 2)
                })
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                # Handle [timestamp, equity] format
                formatted.append({
                    "timestamp": point[0],
                    "equity": round(point[1], 2),
                    "drawdown_pct": round(point[2], 2) if len(point) > 2 else 0
                })
        
        return formatted
    
    def _format_trades(self, trades: List) -> List[Dict]:
        """
        Format trade list for display.
        
        Args:
            trades: Raw trade data
            
        Returns:
            list: Formatted trade list
        """
        formatted = []
        
        for trade in trades:
            formatted.append({
                "trade_id": trade.get("trade_id"),
                "symbol": trade.get("symbol"),
                "direction": trade.get("direction"),
                "entry_time": trade.get("entry_time"),
                "exit_time": trade.get("exit_time"),
                "entry_price": round(trade.get("entry_price", 0), 8),
                "exit_price": round(trade.get("exit_price", 0), 8),
                "quantity": round(trade.get("quantity", 0), 8),
                "pnl_pct": round(trade.get("pnl_pct", 0), 2),
                "pnl_abs": round(trade.get("pnl_abs", 0), 2),
                "outcome": trade.get("outcome"),
                "duration_hours": round(trade.get("duration_hours", 0), 2),
                "quality": trade.get("quality"),
                "confidence": round(trade.get("confidence", 0), 2)
            })
        
        return formatted
    
    def _format_drawdowns(self, drawdowns: List) -> List[Dict]:
        """
        Format drawdown periods for visualization.
        
        Args:
            drawdowns: Raw drawdown data
            
        Returns:
            list: Formatted drawdown periods
        """
        formatted = []
        
        for dd in drawdowns:
            formatted.append({
                "start_date": dd.get("start_date"),
                "end_date": dd.get("end_date"),
                "duration_days": dd.get("duration_days", 0),
                "depth_pct": round(dd.get("depth_pct", 0), 2),
                "depth_abs": round(dd.get("depth_abs", 0), 2),
                "peak_equity": round(dd.get("peak_equity", 0), 2),
                "trough_equity": round(dd.get("trough_equity", 0), 2)
            })
        
        return formatted
    
    def compare_backtest_runs(self, run_ids: List[str]) -> Dict:
        """
        Compare multiple backtest runs side-by-side.
        
        Args:
            run_ids: List of backtest run IDs to compare
            
        Returns:
            dict: Comparison data including:
                - runs: List of run summaries
                - metrics_comparison: Side-by-side metrics comparison
                - equity_curves: Combined equity curves for overlay chart
        """
        try:
            if not run_ids or len(run_ids) < 2:
                return {
                    "error": "At least 2 backtest runs required for comparison"
                }
            
            if len(run_ids) > 4:
                return {
                    "error": "Maximum 4 backtest runs can be compared at once"
                }
            
            runs = []
            metrics_comparison = {}
            equity_curves = {}
            
            # Load each backtest run
            for run_id in run_ids:
                results = self.get_backtest_results(run_id)
                
                if not results:
                    logger.warning(f"Backtest run not found: {run_id}")
                    continue
                
                # Add to runs list
                runs.append({
                    "id": results["id"],
                    "name": results["name"],
                    "timestamp": results["timestamp"]
                })
                
                # Add metrics to comparison
                metrics = results["metrics"]
                for metric_name, value in metrics.items():
                    if metric_name not in metrics_comparison:
                        metrics_comparison[metric_name] = {}
                    metrics_comparison[metric_name][run_id] = value
                
                # Add equity curve
                equity_curves[run_id] = results["equity_curve"]
            
            return {
                "runs": runs,
                "metrics_comparison": metrics_comparison,
                "equity_curves": equity_curves
            }
            
        except Exception as e:
            logger.error(f"Error comparing backtest runs: {e}", exc_info=True)
            return {
                "error": str(e)
            }
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including data availability
        """
        try:
            backtest_runs = self.list_backtest_runs()
            
            return {
                "initialized": True,
                "backtest_dir": self.backtest_dir,
                "total_runs": len(backtest_runs),
                "has_data": len(backtest_runs) > 0,
                "latest_run": backtest_runs[0] if backtest_runs else None
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "total_runs": 0,
                "has_data": False,
                "error": str(e)
            }
