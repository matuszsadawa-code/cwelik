"""
Health Check Routes for OpenClaw Trading Dashboard

Provides endpoints for monitoring system health including database performance,
query statistics, cache statistics, service availability, and alert history.

Endpoints:
- GET /api/health - Overall system health
- GET /api/health/database - Database health and performance
- GET /api/health/cache - Cache statistics
- GET /api/health/queries - Query profiler statistics
- GET /api/health/alerts - Alert history
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import time

from storage.database import Database
from storage.query_cache import get_cache
from storage.query_optimizer import get_profiler
from api.services.alert_service import AlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])

# Initialize database
db = Database()

# Initialize alert service
alert_service = AlertService(db=db)


@router.get("")
async def get_system_health() -> Dict[str, Any]:
    """
    Get overall system health status.
    
    Returns:
        dict: System health including database, cache, and service status
    """
    try:
        # Check database connectivity
        start_time = time.perf_counter()
        conn = db._get_conn()
        conn.execute("SELECT 1").fetchone()
        db_response_time = (time.perf_counter() - start_time) * 1000
        
        # Get cache stats
        cache = get_cache()
        cache_stats = cache.get_stats()
        
        # Get profiler stats
        profiler = get_profiler()
        query_stats = profiler.get_stats()
        
        # Calculate overall health
        db_healthy = db_response_time < 100  # Less than 100ms
        cache_healthy = cache_stats['hit_rate'] > 50 or cache_stats['total_requests'] < 100
        
        overall_healthy = db_healthy and cache_healthy
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": time.time(),
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "degraded",
                    "response_time_ms": round(db_response_time, 2)
                },
                "cache": {
                    "status": "healthy" if cache_healthy else "degraded",
                    "hit_rate": cache_stats['hit_rate'],
                    "size": cache_stats['size']
                },
                "query_profiler": {
                    "status": "active",
                    "tracked_queries": len(query_stats)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking system health: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }


@router.get("/database")
async def get_database_health() -> Dict[str, Any]:
    """
    Get detailed database health and performance metrics.
    
    Returns:
        dict: Database health including connection status, query performance,
              table sizes, and index usage
    """
    try:
        conn = db._get_conn()
        
        # Test connection
        start_time = time.perf_counter()
        conn.execute("SELECT 1").fetchone()
        connection_time = (time.perf_counter() - start_time) * 1000
        
        # Get table sizes
        tables = ['signals', 'signal_outcomes', 'executions', 'equity_snapshots', 
                  'candle_cache', 'orderbook_snapshots', 'trade_clusters']
        
        table_stats = {}
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                table_stats[table] = dict(row)['count'] if row else 0
            except Exception as e:
                logger.error(f"Error getting count for {table}: {e}")
                table_stats[table] = -1
        
        # Get database file size
        db_size_row = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()").fetchone()
        db_size_bytes = dict(db_size_row)['size'] if db_size_row else 0
        db_size_mb = db_size_bytes / (1024 * 1024)
        
        # Check indexes
        index_list = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        indexes = [dict(row)['name'] for row in index_list]
        
        # Get WAL mode status
        wal_mode = conn.execute("PRAGMA journal_mode").fetchone()
        journal_mode = dict(wal_mode)[0] if wal_mode else "unknown"
        
        return {
            "status": "healthy" if connection_time < 100 else "degraded",
            "connection_time_ms": round(connection_time, 2),
            "database_path": db.db_path,
            "database_size_mb": round(db_size_mb, 2),
            "journal_mode": journal_mode,
            "table_counts": table_stats,
            "index_count": len(indexes),
            "indexes": indexes
        }
        
    except Exception as e:
        logger.error(f"Error checking database health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        dict: Cache statistics including hits, misses, hit rate, size
    """
    try:
        cache = get_cache()
        stats = cache.get_stats()
        
        return {
            "status": "active",
            "statistics": stats,
            "default_ttl": cache.default_ttl
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache() -> Dict[str, str]:
    """
    Clear all cached data.
    
    Returns:
        dict: Success message
    """
    try:
        cache = get_cache()
        cache.clear()
        
        return {
            "status": "success",
            "message": "Cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries")
async def get_query_stats() -> Dict[str, Any]:
    """
    Get query profiler statistics.
    
    Returns:
        dict: Query statistics including execution times and slow query counts
    """
    try:
        profiler = get_profiler()
        stats = profiler.get_stats()
        
        # Sort by total time (slowest first)
        sorted_stats = dict(sorted(
            stats.items(),
            key=lambda x: x[1]['total_time_ms'],
            reverse=True
        ))
        
        # Calculate summary
        total_queries = sum(s['count'] for s in stats.values())
        total_time = sum(s['total_time_ms'] for s in stats.values())
        total_slow = sum(s['slow_count'] for s in stats.values())
        
        return {
            "status": "active",
            "summary": {
                "total_queries": total_queries,
                "total_time_ms": round(total_time, 2),
                "avg_time_ms": round(total_time / total_queries, 2) if total_queries > 0 else 0,
                "slow_queries": total_slow,
                "slow_query_threshold_ms": profiler.slow_query_threshold_ms
            },
            "queries": sorted_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting query stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queries/reset")
async def reset_query_stats() -> Dict[str, str]:
    """
    Reset query profiler statistics.
    
    Returns:
        dict: Success message
    """
    try:
        profiler = get_profiler()
        profiler.reset_stats()
        
        return {
            "status": "success",
            "message": "Query statistics reset successfully"
        }
        
    except Exception as e:
        logger.error(f"Error resetting query stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alert_history(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of alerts to return"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (info, warning, error)"),
    category: Optional[str] = Query(default=None, description="Filter by category (signal, position, system, risk, health)"),
    dismissed: Optional[bool] = Query(default=None, description="Filter by dismissed status")
) -> Dict[str, Any]:
    """
    Get alert history with optional filters.
    
    Retrieves historical alerts from the alert_history table with support for filtering
    by severity, category, and dismissed status.
    
    Args:
        limit: Maximum number of alerts to return (1-1000, default 100)
        severity: Filter by severity level (info, warning, error)
        category: Filter by category (signal, position, system, risk, health)
        dismissed: Filter by dismissed status (true/false)
        
    Returns:
        dict: Alert history including:
            - alerts: List of alert objects with:
                - alert_id: Unique alert identifier
                - severity: Alert severity (info, warning, error)
                - category: Alert category (signal, position, system, risk, health)
                - message: Alert message
                - details: Additional alert details (JSON object)
                - dismissed: Whether alert has been dismissed
                - created_at: Alert creation timestamp (ISO 8601)
            - count: Number of alerts returned
            - filters: Applied filters
    
    Example:
        GET /api/health/alerts?limit=50&severity=error&dismissed=false
    """
    try:
        # Validate severity if provided
        if severity and severity not in alert_service.SEVERITIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Must be one of: {', '.join(alert_service.SEVERITIES)}"
            )
        
        # Validate category if provided
        if category and category not in alert_service.CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(alert_service.CATEGORIES)}"
            )
        
        # Get alert history
        alerts = alert_service.get_alert_history(
            limit=limit,
            severity=severity,
            category=category,
            dismissed=dismissed
        )
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "filters": {
                "limit": limit,
                "severity": severity,
                "category": category,
                "dismissed": dismissed
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
