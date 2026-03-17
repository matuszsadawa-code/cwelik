"""
Report Service for OpenClaw Trading Dashboard

Generates comprehensive performance reports with support for JSON, CSV, and PDF export formats.
Includes performance metrics, charts data, and trade journal with configurable sections.

Features:
- Generate comprehensive performance reports
- Support JSON, CSV, PDF export formats
- Date range selection
- Section selection (performance metrics, charts, trade journal)
- Include all key metrics and trade data
"""

import logging
import json
import csv
import io
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from api.services.performance_metrics_service import PerformanceMetricsService
from api.services.equity_curve_service import EquityCurveService
from api.services.pnl_breakdown_service import PnLBreakdownService
from api.services.symbol_performance_service import SymbolPerformanceService
from api.services.quality_analysis_service import QualityAnalysisService
from api.services.risk_metrics_service import RiskMetricsService
from api.services.trade_journal_service import TradeJournalService
from storage.database import Database

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service for generating comprehensive performance reports.
    
    Responsibilities:
    - Generate reports with selected sections
    - Support multiple export formats (JSON, CSV, PDF)
    - Aggregate data from multiple services
    - Format data for export
    """
    
    def __init__(self, database: Database = None):
        """
        Initialize report service.
        
        Args:
            database: Database instance (creates new if None)
        """
        self.database = database or Database()
        
        # Initialize dependent services
        self.performance_service = PerformanceMetricsService(self.database)
        self.equity_service = EquityCurveService(self.database)
        self.pnl_service = PnLBreakdownService(self.database)
        self.symbol_service = SymbolPerformanceService(self.database)
        self.quality_service = QualityAnalysisService(self.database)
        self.risk_service = RiskMetricsService(self.database)
        self.trade_service = TradeJournalService(self.database)
        
        logger.info("ReportService initialized")
    
    def generate_report(
        self,
        format: str = "json",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sections: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate comprehensive performance report.
        
        Args:
            format: Export format ("json", "csv", or "pdf")
            start_date: Start date for report (ISO format)
            end_date: End date for report (ISO format)
            sections: List of sections to include (if None, includes all)
                Available sections:
                - "performance_metrics": Overall performance metrics
                - "equity_curve": Equity curve data
                - "pnl_breakdown": PnL breakdown by period
                - "symbol_performance": Per-symbol performance
                - "quality_analysis": Quality grade analysis
                - "risk_metrics": Risk-adjusted metrics
                - "trade_journal": Complete trade history
                
        Returns:
            dict: Report data structure or file content
        """
        try:
            # Default to all sections if not specified
            if sections is None:
                sections = [
                    "performance_metrics",
                    "equity_curve",
                    "pnl_breakdown",
                    "symbol_performance",
                    "quality_analysis",
                    "risk_metrics",
                    "trade_journal"
                ]
            
            # Validate sections
            valid_sections = [
                "performance_metrics", "equity_curve", "pnl_breakdown",
                "symbol_performance", "quality_analysis", "risk_metrics", "trade_journal"
            ]
            
            invalid_sections = [s for s in sections if s not in valid_sections]
            if invalid_sections:
                return {
                    "error": f"Invalid sections: {', '.join(invalid_sections)}"
                }
            
            # Generate report data
            report_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "start_date": start_date,
                    "end_date": end_date,
                    "sections": sections,
                    "format": format
                }
            }
            
            # Collect data for each section
            if "performance_metrics" in sections:
                report_data["performance_metrics"] = self._get_performance_metrics(start_date, end_date)
            
            if "equity_curve" in sections:
                report_data["equity_curve"] = self._get_equity_curve(start_date, end_date)
            
            if "pnl_breakdown" in sections:
                report_data["pnl_breakdown"] = self._get_pnl_breakdown(start_date, end_date)
            
            if "symbol_performance" in sections:
                report_data["symbol_performance"] = self._get_symbol_performance(start_date, end_date)
            
            if "quality_analysis" in sections:
                report_data["quality_analysis"] = self._get_quality_analysis(start_date, end_date)
            
            if "risk_metrics" in sections:
                report_data["risk_metrics"] = self._get_risk_metrics(start_date, end_date)
            
            if "trade_journal" in sections:
                report_data["trade_journal"] = self._get_trade_journal(start_date, end_date)
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            return {
                "error": str(e)
            }
    
    def _get_performance_metrics(self, start_date: Optional[str], end_date: Optional[str]) -> Dict:
        """Get performance metrics for report."""
        try:
            metrics = self.performance_service.get_performance_metrics()
            return metrics
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    def _get_equity_curve(self, start_date: Optional[str], end_date: Optional[str]) -> Dict:
        """Get equity curve data for report."""
        try:
            # Default to 90 days if no date range specified
            days = 90
            if start_date and end_date:
                # Calculate days between dates
                from datetime import datetime
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                days = (end - start).days
            
            equity_data = self.equity_service.get_equity_curve(days=days)
            return equity_data
        except Exception as e:
            logger.error(f"Error getting equity curve: {e}")
            return {}
    
    def _get_pnl_breakdown(self, start_date: Optional[str], end_date: Optional[str]) -> Dict:
        """Get PnL breakdown for report."""
        try:
            pnl_data = self.pnl_service.get_pnl_breakdown(days=90)
            return pnl_data
        except Exception as e:
            logger.error(f"Error getting PnL breakdown: {e}")
            return {}
    
    def _get_symbol_performance(self, start_date: Optional[str], end_date: Optional[str]) -> Dict:
        """Get symbol performance for report."""
        try:
            symbol_data = self.symbol_service.get_symbol_performance()
            return symbol_data
        except Exception as e:
            logger.error(f"Error getting symbol performance: {e}")
            return {}
    
    def _get_quality_analysis(self, start_date: Optional[str], end_date: Optional[str]) -> Dict:
        """Get quality analysis for report."""
        try:
            quality_data = self.quality_service.get_quality_analysis()
            return quality_data
        except Exception as e:
            logger.error(f"Error getting quality analysis: {e}")
            return {}
    
    def _get_risk_metrics(self, start_date: Optional[str], end_date: Optional[str]) -> Dict:
        """Get risk metrics for report."""
        try:
            risk_data = self.risk_service.get_risk_metrics()
            return risk_data
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return {}
    
    def _get_trade_journal(self, start_date: Optional[str], end_date: Optional[str]) -> Dict:
        """Get trade journal for report."""
        try:
            # Get all trades within date range
            trade_data = self.trade_service.get_trade_history(
                page=1,
                page_size=10000,  # Large page size to get all trades
                start_date=start_date,
                end_date=end_date,
                sort_by="closed_at",
                sort_order="desc"
            )
            return trade_data
        except Exception as e:
            logger.error(f"Error getting trade journal: {e}")
            return {}
    
    def export_to_json(self, report_data: Dict) -> str:
        """
        Export report to JSON format.
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            str: JSON string
        """
        return json.dumps(report_data, indent=2)
    
    def export_to_csv(self, report_data: Dict) -> str:
        """
        Export report to CSV format.
        
        For CSV, we export the trade journal section as the main data,
        and include summary metrics in a header section.
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            str: CSV string
        """
        output = io.StringIO()
        
        # Write metadata header
        output.write("# OpenClaw Trading System Performance Report\n")
        output.write(f"# Generated: {report_data['metadata']['generated_at']}\n")
        output.write(f"# Date Range: {report_data['metadata']['start_date']} to {report_data['metadata']['end_date']}\n")
        output.write("\n")
        
        # Write performance metrics summary
        if "performance_metrics" in report_data:
            output.write("# Performance Metrics\n")
            metrics = report_data["performance_metrics"]
            for key, value in metrics.items():
                output.write(f"# {key}: {value}\n")
            output.write("\n")
        
        # Write trade journal as CSV table
        if "trade_journal" in report_data:
            trades = report_data["trade_journal"].get("trades", [])
            
            if trades:
                output.write("# Trade Journal\n")
                
                fieldnames = [
                    "tradeId", "symbol", "direction", "quality", "entryPrice", "exitPrice",
                    "pnl", "outcome", "rrAchieved", "mfe", "mae", "duration",
                    "entryTime", "exitTime", "entryReason", "exitReason"
                ]
                
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for trade in trades:
                    row = {field: trade.get(field, "") for field in fieldnames}
                    writer.writerow(row)
        
        return output.getvalue()
    
    def export_to_pdf(self, report_data: Dict) -> bytes:
        """
        Export report to PDF format.
        
        Note: This is a placeholder implementation. Full PDF generation
        would require a library like reportlab or weasyprint.
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            bytes: PDF file content
        """
        # For now, return a simple text-based PDF placeholder
        # In production, use reportlab or similar library
        
        text_content = f"""
OpenClaw Trading System Performance Report
Generated: {report_data['metadata']['generated_at']}
Date Range: {report_data['metadata']['start_date']} to {report_data['metadata']['end_date']}

Performance Metrics:
{json.dumps(report_data.get('performance_metrics', {}), indent=2)}

Symbol Performance:
{json.dumps(report_data.get('symbol_performance', {}), indent=2)}

Risk Metrics:
{json.dumps(report_data.get('risk_metrics', {}), indent=2)}

Trade Count: {len(report_data.get('trade_journal', {}).get('trades', []))}
"""
        
        return text_content.encode('utf-8')
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status
        """
        try:
            return {
                "initialized": True,
                "available_sections": [
                    "performance_metrics",
                    "equity_curve",
                    "pnl_breakdown",
                    "symbol_performance",
                    "quality_analysis",
                    "risk_metrics",
                    "trade_journal"
                ],
                "supported_formats": ["json", "csv", "pdf"]
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "initialized": False,
                "error": str(e)
            }
