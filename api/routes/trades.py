"""
Trade Journal API Routes

Provides endpoints for retrieving trade history with filtering, sorting, and pagination.
Also provides export functionality for trades in CSV and JSON formats.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import io
import csv
import json

from api.services.trade_journal_service import TradeJournalService
from api.utils.database import get_database

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/trades", tags=["trades"])

# Initialize service
trade_journal_service = None


def init_trade_journal_service():
    """Initialize trade journal service with database connection"""
    global trade_journal_service
    db = get_database()
    trade_journal_service = TradeJournalService(db)
    logger.info("Trade journal service initialized")


@router.get("/history")
async def get_trade_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=500, description="Number of trades per page"),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTCUSDT)"),
    start_date: Optional[str] = Query(None, description="Filter trades closed after this date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter trades closed before this date (ISO format)"),
    outcome: Optional[str] = Query(None, description="Filter by outcome (WIN or LOSS)"),
    quality: Optional[str] = Query(None, description="Filter by quality grade (A+, A, B, C)"),
    sort_by: str = Query("closed_at", description="Column to sort by (entry_time, exit_time, pnl, duration, symbol, quality, closed_at)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)")
):
    """
    Get paginated trade history with filtering and sorting.
    
    Retrieves trades from signal_outcomes table with associated signal details.
    Supports comprehensive filtering by symbol, date range, outcome, and quality grade.
    Supports sorting by any column with ascending or descending order.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of trades per page (1-500)
        symbol: Filter by symbol (e.g., "BTCUSDT")
        start_date: Filter trades closed after this date (ISO format: "2024-01-01T00:00:00")
        end_date: Filter trades closed before this date (ISO format: "2024-12-31T23:59:59")
        outcome: Filter by outcome ("WIN" or "LOSS")
        quality: Filter by quality grade ("A+", "A", "B", "C")
        sort_by: Column to sort by (entry_time, exit_time, pnl, duration, symbol, quality, closed_at)
        sort_order: Sort order ("asc" or "desc")
        
    Returns:
        dict: Trade history data including:
            - trades: List of trade dictionaries with:
                - tradeId: Unique trade identifier
                - signalId: Associated signal ID
                - symbol: Trading pair symbol
                - direction: Trade direction (LONG or SHORT)
                - quality: Signal quality grade (A+, A, B, C)
                - confidence: Signal confidence score (0-100)
                - entryPrice: Entry price
                - exitPrice: Exit price
                - stopLoss: Stop loss price
                - takeProfit: Take profit price
                - pnl: Profit/Loss percentage
                - outcome: Trade outcome (WIN or LOSS)
                - rrAchieved: Risk-reward ratio achieved
                - mfe: Maximum Favorable Excursion
                - mae: Maximum Adverse Excursion
                - duration: Trade duration in minutes
                - entryTime: Entry timestamp (ISO format)
                - exitTime: Exit timestamp (ISO format)
                - entryReason: Entry reason/reasoning
                - exitReason: Exit reason (TP hit, SL hit, manual, etc.)
                - tpHit: Whether take profit was hit
                - slHit: Whether stop loss was hit
                - marketRegime: Market regime at entry (TRENDING, RANGING, VOLATILE, QUIET)
            - pagination: Pagination metadata
                - page: Current page number
                - pageSize: Number of trades per page
                - totalTrades: Total number of matching trades
                - totalPages: Total number of pages
            - filters: Applied filters
    
    Example:
        GET /api/trades/history?page=1&page_size=50&symbol=BTCUSDT&outcome=WIN&sort_by=pnl&sort_order=desc
    """
    if not trade_journal_service:
        init_trade_journal_service()
    
    try:
        # Validate outcome parameter
        if outcome and outcome.upper() not in ["WIN", "LOSS"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid outcome parameter. Must be 'WIN' or 'LOSS'"
            )
        
        # Validate quality parameter
        if quality and quality not in ["A+", "A", "B", "C"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid quality parameter. Must be 'A+', 'A', 'B', or 'C'"
            )
        
        # Validate sort_by parameter
        valid_sort_columns = ["entry_time", "exit_time", "pnl", "duration", "symbol", "quality", "closed_at"]
        if sort_by not in valid_sort_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort_by parameter. Must be one of: {', '.join(valid_sort_columns)}"
            )
        
        # Validate sort_order parameter
        if sort_order.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort_order parameter. Must be 'asc' or 'desc'"
            )
        
        # Get trade history
        result = trade_journal_service.get_trade_history(
            page=page,
            page_size=page_size,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            outcome=outcome,
            quality=quality,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Check for errors
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving trade history: {result['error']}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_trade_history endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/export")
async def export_trades(
    format: str = Query("csv", description="Export format (csv or json)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTCUSDT)"),
    start_date: Optional[str] = Query(None, description="Filter trades closed after this date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter trades closed before this date (ISO format)"),
    outcome: Optional[str] = Query(None, description="Filter by outcome (WIN or LOSS)"),
    quality: Optional[str] = Query(None, description="Filter by quality grade (A+, A, B, C)")
):
    """
    Export trades to CSV or JSON format.
    
    Retrieves all trades matching the filter criteria (no pagination) and exports them
    in the requested format. Includes all trade fields for comprehensive analysis.
    
    Args:
        format: Export format ("csv" or "json")
        symbol: Filter by symbol (e.g., "BTCUSDT")
        start_date: Filter trades closed after this date (ISO format)
        end_date: Filter trades closed before this date (ISO format)
        outcome: Filter by outcome ("WIN" or "LOSS")
        quality: Filter by quality grade ("A+", "A", "B", "C")
        
    Returns:
        StreamingResponse: File download with trades in requested format
        
    Example:
        GET /api/trades/export?format=csv&symbol=BTCUSDT&start_date=2024-01-01T00:00:00
    """
    if not trade_journal_service:
        init_trade_journal_service()
    
    try:
        # Validate format parameter
        if format.lower() not in ["csv", "json"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid format parameter. Must be 'csv' or 'json'"
            )
        
        # Validate outcome parameter
        if outcome and outcome.upper() not in ["WIN", "LOSS"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid outcome parameter. Must be 'WIN' or 'LOSS'"
            )
        
        # Validate quality parameter
        if quality and quality not in ["A+", "A", "B", "C"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid quality parameter. Must be 'A+', 'A', 'B', or 'C'"
            )
        
        # Get all trades matching filters (no pagination)
        result = trade_journal_service.get_trade_history(
            page=1,
            page_size=10000,  # Large page size to get all trades
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            outcome=outcome,
            quality=quality,
            sort_by="closed_at",
            sort_order="desc"
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving trades for export: {result['error']}"
            )
        
        trades = result.get("trades", [])
        
        if not trades:
            raise HTTPException(
                status_code=404,
                detail="No trades found matching the specified criteria"
            )
        
        # Generate export based on format
        if format.lower() == "csv":
            return _export_csv(trades, symbol, start_date, end_date)
        else:  # json
            return _export_json(trades, symbol, start_date, end_date)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in export_trades endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


def _export_csv(trades: list, symbol: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> StreamingResponse:
    """
    Export trades to CSV format.
    
    Args:
        trades: List of trade dictionaries
        symbol: Symbol filter (for filename)
        start_date: Start date filter (for filename)
        end_date: End date filter (for filename)
        
    Returns:
        StreamingResponse: CSV file download
    """
    # Create CSV in memory
    output = io.StringIO()
    
    # Define CSV columns (all trade fields)
    fieldnames = [
        "tradeId", "signalId", "symbol", "direction", "quality", "confidence",
        "entryPrice", "exitPrice", "stopLoss", "takeProfit", "pnl", "outcome",
        "rrAchieved", "mfe", "mae", "duration", "entryTime", "exitTime",
        "entryReason", "exitReason", "tpHit", "slHit", "marketRegime"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # Write trade rows
    for trade in trades:
        # Extract only the fields we want in CSV
        row = {field: trade.get(field, "") for field in fieldnames}
        writer.writerow(row)
    
    # Generate filename
    filename_parts = ["trades"]
    if symbol:
        filename_parts.append(symbol)
    if start_date:
        filename_parts.append(f"from_{start_date[:10]}")
    if end_date:
        filename_parts.append(f"to_{end_date[:10]}")
    filename = "_".join(filename_parts) + ".csv"
    
    # Return as streaming response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _export_json(trades: list, symbol: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> StreamingResponse:
    """
    Export trades to JSON format.
    
    Args:
        trades: List of trade dictionaries
        symbol: Symbol filter (for filename)
        start_date: Start date filter (for filename)
        end_date: End date filter (for filename)
        
    Returns:
        StreamingResponse: JSON file download
    """
    # Create JSON structure
    export_data = {
        "exportDate": json.dumps({"$date": {"$numberLong": str(int(__import__("time").time() * 1000))}}),
        "filters": {
            "symbol": symbol,
            "startDate": start_date,
            "endDate": end_date
        },
        "totalTrades": len(trades),
        "trades": trades
    }
    
    # Generate filename
    filename_parts = ["trades"]
    if symbol:
        filename_parts.append(symbol)
    if start_date:
        filename_parts.append(f"from_{start_date[:10]}")
    if end_date:
        filename_parts.append(f"to_{end_date[:10]}")
    filename = "_".join(filename_parts) + ".json"
    
    # Return as streaming response
    json_str = json.dumps(export_data, indent=2)
    return StreamingResponse(
        iter([json_str]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{trade_id}")
async def get_trade_detail(trade_id: str):
    """
    Get detailed information for a single trade.
    
    Retrieves complete trade details including all feature contributions,
    step data, and advanced analytics for detailed trade analysis.
    
    Args:
        trade_id: Trade ID (signal_outcomes.id)
        
    Returns:
        dict: Detailed trade information including:
            - All fields from trade history
            - featureContributions: Dictionary of feature contributions to signal
            - step1Data: Step 1 (Trend Analysis) data
            - step2Data: Step 2 (Zone Identification) data
            - step3Data: Step 3 (Volume Confirmation) data
            - step4Data: Step 4 (Order Flow Validation) data
            - advancedAnalytics: Advanced analytics data
            - rrTarget: Target risk-reward ratio
    
    Example:
        GET /api/trades/12345
    """
    if not trade_journal_service:
        init_trade_journal_service()
    
    try:
        trade = trade_journal_service.get_trade_detail(trade_id)
        
        if not trade:
            raise HTTPException(
                status_code=404,
                detail=f"Trade not found: {trade_id}"
            )
        
        return trade
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_trade_detail endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/status")
async def get_service_status():
    """
    Get trade journal service status.
    
    Returns service health information including total trade count,
    date range of available trades, and data availability status.
    
    Returns:
        dict: Service status including:
            - initialized: Whether service is initialized
            - total_trades: Total number of completed trades
            - earliest_trade: Timestamp of earliest trade
            - latest_trade: Timestamp of latest trade
            - has_data: Whether any trade data is available
    """
    if not trade_journal_service:
        init_trade_journal_service()
    
    try:
        return trade_journal_service.get_service_status()
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        return {
            "initialized": False,
            "total_trades": 0,
            "has_data": False,
            "error": str(e)
        }
