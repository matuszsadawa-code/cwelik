"""
Database Query Timer

Wrapper for database operations to track query performance.
Automatically logs slow queries (>50ms) and integrates with performance monitoring.
"""

import time
import logging
from typing import Any, Callable, Optional
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class QueryTimer:
    """
    Database query timing wrapper
    
    Tracks query execution time and logs slow queries.
    Integrates with PerformanceMonitor for centralized metrics.
    """
    
    SLOW_QUERY_THRESHOLD_MS = 50.0
    
    def __init__(self):
        """Initialize query timer"""
        self.performance_monitor = None
    
    def set_performance_monitor(self, monitor):
        """
        Set performance monitor for metrics recording
        
        Args:
            monitor: PerformanceMonitor instance
        """
        self.performance_monitor = monitor
    
    @contextmanager
    def time_query(self, query: str):
        """
        Context manager for timing database queries
        
        Usage:
            with query_timer.time_query("SELECT * FROM signals"):
                result = db.execute(query)
        
        Args:
            query: SQL query string
        """
        start_time = time.time()
        
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log slow queries
            if duration_ms > self.SLOW_QUERY_THRESHOLD_MS:
                query_preview = query[:100] + "..." if len(query) > 100 else query
                logger.warning(
                    f"Slow query detected ({duration_ms:.2f}ms): {query_preview}"
                )
            
            # Record in performance monitor if available
            if self.performance_monitor:
                self.performance_monitor.record_query(query, duration_ms)
    
    def time_function(self, query_description: str):
        """
        Decorator for timing database functions
        
        Usage:
            @query_timer.time_function("Get active signals")
            def get_active_signals(self):
                return self.db.execute(...)
        
        Args:
            query_description: Description of the query/operation
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log slow operations
                    if duration_ms > self.SLOW_QUERY_THRESHOLD_MS:
                        logger.warning(
                            f"Slow database operation ({duration_ms:.2f}ms): {query_description}"
                        )
                    
                    # Record in performance monitor if available
                    if self.performance_monitor:
                        self.performance_monitor.record_query(query_description, duration_ms)
            
            return wrapper
        return decorator
    
    def time_async_function(self, query_description: str):
        """
        Decorator for timing async database functions
        
        Usage:
            @query_timer.time_async_function("Get active signals")
            async def get_active_signals(self):
                return await self.db.execute(...)
        
        Args:
            query_description: Description of the query/operation
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log slow operations
                    if duration_ms > self.SLOW_QUERY_THRESHOLD_MS:
                        logger.warning(
                            f"Slow async database operation ({duration_ms:.2f}ms): {query_description}"
                        )
                    
                    # Record in performance monitor if available
                    if self.performance_monitor:
                        self.performance_monitor.record_query(query_description, duration_ms)
            
            return wrapper
        return decorator


# Global query timer instance
query_timer = QueryTimer()


def get_query_timer() -> QueryTimer:
    """
    Get global query timer instance
    
    Returns:
        QueryTimer instance
    """
    return query_timer
