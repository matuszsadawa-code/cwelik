"""
Export and Reporting API Routes

Provides endpoints for generating and exporting comprehensive performance reports.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
import io

from api.services.report_service import ReportService
from api.utils.database import get_database

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/export", tags=["export"])

# Initialize service
report_service = None


def init_report_service():
    """Initialize report service with database connection"""
    global report_service
    db = get_database()
    report_service = ReportService(db)
    logger.info("Report service initialized")


class ExportReportRequest(BaseModel):
    """Request model for report export"""
    format: str = "json"
    date_range: Optional[dict] = None
    sections: Optional[List[str]] = None


@router.post("/report")
async def export_report(request: ExportReportRequest = Body(...)):
    """
    Generate and export comprehensive performance report.
    
    Generates a report with selected sections and exports in the requested format.
    Supports JSON, CSV, and PDF formats with configurable date ranges and sections.
    
    Request Body:
        format: Export format ("json", "csv", or "pdf")
        date_range: Optional date range filter
            - start_date: Start date (ISO format)
            - end_date: End date (ISO format)
        sections: Optional list of sections to include (if not specified, includes all)
            Available sections:
            - "performance_metrics": Overall performance metrics
            - "equity_curve": Equity curve data
            - "pnl_breakdown": PnL breakdown by period
            - "symbol_performance": Per-symbol performance
            - "quality_analysis": Quality grade analysis
            - "risk_metrics": Risk-adjusted metrics
            - "trade_journal": Complete trade history
    
    Returns:
        File download with report in requested format
    
    Example Request:
        POST /api/export/report
        {
            "format": "json",
            "date_range": {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-12-31T23:59:59"
            },
            "sections": ["performance_metrics", "trade_journal"]
        }
    """
    if not report_service:
        init_report_service()
    
    try:
        # Validate format
        if request.format.lower() not in ["json", "csv", "pdf"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid format. Must be 'json', 'csv', or 'pdf'"
            )
        
        # Extract date range
        start_date = None
        end_date = None
        if request.date_range:
            start_date = request.date_range.get("start_date")
            end_date = request.date_range.get("end_date")
        
        # Generate report
        report_data = report_service.generate_report(
            format=request.format,
            start_date=start_date,
            end_date=end_date,
            sections=request.sections
        )
        
        # Check for errors
        if "error" in report_data:
            raise HTTPException(
                status_code=400,
                detail=f"Error generating report: {report_data['error']}"
            )
        
        # Export based on format
        if request.format.lower() == "json":
            return _export_json_response(report_data, start_date, end_date)
        elif request.format.lower() == "csv":
            return _export_csv_response(report_data, start_date, end_date)
        else:  # pdf
            return _export_pdf_response(report_data, start_date, end_date)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in export_report endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


def _export_json_response(report_data: dict, start_date: Optional[str], end_date: Optional[str]) -> StreamingResponse:
    """
    Export report as JSON file.
    
    Args:
        report_data: Report data dictionary
        start_date: Start date filter
        end_date: End date filter
        
    Returns:
        StreamingResponse: JSON file download
    """
    # Generate filename
    filename_parts = ["openclaw_report"]
    if start_date:
        filename_parts.append(f"from_{start_date[:10]}")
    if end_date:
        filename_parts.append(f"to_{end_date[:10]}")
    filename = "_".join(filename_parts) + ".json"
    
    # Export to JSON
    json_content = report_service.export_to_json(report_data)
    
    return StreamingResponse(
        iter([json_content]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _export_csv_response(report_data: dict, start_date: Optional[str], end_date: Optional[str]) -> StreamingResponse:
    """
    Export report as CSV file.
    
    Args:
        report_data: Report data dictionary
        start_date: Start date filter
        end_date: End date filter
        
    Returns:
        StreamingResponse: CSV file download
    """
    # Generate filename
    filename_parts = ["openclaw_report"]
    if start_date:
        filename_parts.append(f"from_{start_date[:10]}")
    if end_date:
        filename_parts.append(f"to_{end_date[:10]}")
    filename = "_".join(filename_parts) + ".csv"
    
    # Export to CSV
    csv_content = report_service.export_to_csv(report_data)
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _export_pdf_response(report_data: dict, start_date: Optional[str], end_date: Optional[str]) -> Response:
    """
    Export report as PDF file.
    
    Args:
        report_data: Report data dictionary
        start_date: Start date filter
        end_date: End date filter
        
    Returns:
        Response: PDF file download
    """
    # Generate filename
    filename_parts = ["openclaw_report"]
    if start_date:
        filename_parts.append(f"from_{start_date[:10]}")
    if end_date:
        filename_parts.append(f"to_{end_date[:10]}")
    filename = "_".join(filename_parts) + ".pdf"
    
    # Export to PDF
    pdf_content = report_service.export_to_pdf(report_data)
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/status")
async def get_service_status():
    """
    Get export/report service status.
    
    Returns service health information including available sections
    and supported export formats.
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - available_sections: List of available report sections
            - supported_formats: List of supported export formats
    """
    if not report_service:
        init_report_service()
    
    try:
        return report_service.get_service_status()
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        return {
            "initialized": False,
            "error": str(e)
        }
