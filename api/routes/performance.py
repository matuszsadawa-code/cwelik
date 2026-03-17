"""
Performance Monitoring API Routes

Provides endpoints for accessing performance metrics, slow request/query logs,
and system performance statistics.
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Query
from api.middleware import get_performance_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/metrics")
async def get_performance_metrics() -> Dict:
    """
    Get current performance metrics
    
    Returns aggregated statistics for:
    - API request timing
    - Database query performance
    - WebSocket message latency
    
    **Returns:**
    - requests: Request timing statistics
    - queries: Database query statistics
    - websocket: WebSocket latency statistics
    """
    monitor = get_performance_monitor()
    return monitor.get_stats()


@router.get("/endpoints")
async def get_endpoint_stats() -> Dict[str, Dict]:
    """
    Get per-endpoint performance statistics
    
    Returns detailed statistics for each API endpoint including:
    - Request count
    - Average, min, max response time
    - Slow request count
    
    **Returns:**
    Dictionary mapping endpoints to their statistics
    """
    monitor = get_performance_monitor()
    return monitor.get_endpoint_stats()


@router.get("/queries")
async def get_query_pattern_stats() -> Dict[str, Dict]:
    """
    Get per-query-pattern performance statistics
    
    Returns statistics grouped by query type (SELECT, INSERT, UPDATE, DELETE):
    - Query count
    - Average, min, max execution time
    - Slow query count
    
    **Returns:**
    Dictionary mapping query patterns to their statistics
    """
    monitor = get_performance_monitor()
    return monitor.get_query_pattern_stats()


@router.get("/slow-requests")
async def get_slow_requests(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results")
) -> List[Dict]:
    """
    Get recent slow API requests
    
    Returns list of recent requests that exceeded the slow request threshold (>200ms).
    
    **Parameters:**
    - limit: Maximum number of results (1-100, default: 10)
    
    **Returns:**
    List of slow request details including path, method, duration, status code, timestamp
    """
    monitor = get_performance_monitor()
    return monitor.get_recent_slow_requests(limit=limit)


@router.get("/slow-queries")
async def get_slow_queries(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results")
) -> List[Dict]:
    """
    Get recent slow database queries
    
    Returns list of recent queries that exceeded the slow query threshold (>50ms).
    
    **Parameters:**
    - limit: Maximum number of results (1-100, default: 10)
    
    **Returns:**
    List of slow query details including query text, duration, timestamp
    """
    monitor = get_performance_monitor()
    return monitor.get_recent_slow_queries(limit=limit)


@router.post("/reset")
async def reset_performance_stats() -> Dict:
    """
    Reset all performance statistics
    
    Clears all accumulated performance metrics and resets counters to zero.
    Useful for starting fresh monitoring after configuration changes.
    
    **Returns:**
    Success confirmation message
    """
    monitor = get_performance_monitor()
    monitor.reset_stats()
    
    logger.info("Performance statistics reset via API")
    
    return {
        "status": "success",
        "message": "Performance statistics have been reset"
    }
