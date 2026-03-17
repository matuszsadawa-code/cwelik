"""
Performance Monitoring Middleware

Tracks request timing, database query performance, and WebSocket message latency.

Features:
- Request timing with automatic logging of slow requests (>200ms)
- Database query timing with slow query detection (>50ms)
- WebSocket message latency tracking
- Performance metrics aggregation
- Real-time performance monitoring

Performance Thresholds:
- Slow API request: >200ms
- Slow database query: >50ms
- Target WebSocket latency: <100ms
"""

import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    path: str
    method: str
    duration_ms: float
    status_code: int
    timestamp: datetime
    is_slow: bool = False


@dataclass
class QueryMetrics:
    """Metrics for a single database query"""
    query: str
    duration_ms: float
    timestamp: datetime
    is_slow: bool = False


@dataclass
class WebSocketMetrics:
    """Metrics for WebSocket messages"""
    message_type: str
    latency_ms: float
    timestamp: datetime
    is_slow: bool = False


@dataclass
class PerformanceStats:
    """Aggregated performance statistics"""
    total_requests: int = 0
    slow_requests: int = 0
    avg_request_time_ms: float = 0.0
    max_request_time_ms: float = 0.0
    
    total_queries: int = 0
    slow_queries: int = 0
    avg_query_time_ms: float = 0.0
    max_query_time_ms: float = 0.0
    
    total_ws_messages: int = 0
    slow_ws_messages: int = 0
    avg_ws_latency_ms: float = 0.0
    max_ws_latency_ms: float = 0.0
    
    # Recent metrics (last 100 of each type)
    recent_requests: List[RequestMetrics] = field(default_factory=list)
    recent_queries: List[QueryMetrics] = field(default_factory=list)
    recent_ws_messages: List[WebSocketMetrics] = field(default_factory=list)


class PerformanceMonitor:
    """
    Performance monitoring system
    
    Tracks request timing, database queries, and WebSocket latency.
    Automatically logs slow operations and maintains statistics.
    """
    
    # Performance thresholds (milliseconds)
    SLOW_REQUEST_THRESHOLD_MS = 200.0
    SLOW_QUERY_THRESHOLD_MS = 50.0
    SLOW_WS_THRESHOLD_MS = 100.0
    
    # Maximum recent metrics to keep in memory
    MAX_RECENT_METRICS = 100
    
    def __init__(self):
        """Initialize performance monitor"""
        self.stats = PerformanceStats()
        
        # Per-endpoint statistics
        self.endpoint_stats: Dict[str, List[float]] = defaultdict(list)
        
        # Query pattern statistics
        self.query_patterns: Dict[str, List[float]] = defaultdict(list)
        
        logger.info("Performance monitor initialized")
    
    def record_request(self, path: str, method: str, duration_ms: float, status_code: int):
        """
        Record API request metrics
        
        Args:
            path: Request path
            method: HTTP method
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
        """
        is_slow = duration_ms > self.SLOW_REQUEST_THRESHOLD_MS
        
        # Create metrics record
        metrics = RequestMetrics(
            path=path,
            method=method,
            duration_ms=duration_ms,
            status_code=status_code,
            timestamp=datetime.utcnow(),
            is_slow=is_slow
        )
        
        # Update statistics
        self.stats.total_requests += 1
        if is_slow:
            self.stats.slow_requests += 1
            logger.warning(
                f"Slow API request detected: {method} {path} took {duration_ms:.2f}ms "
                f"(threshold: {self.SLOW_REQUEST_THRESHOLD_MS}ms)"
            )
        
        # Update averages
        total_time = self.stats.avg_request_time_ms * (self.stats.total_requests - 1) + duration_ms
        self.stats.avg_request_time_ms = total_time / self.stats.total_requests
        
        # Update max
        if duration_ms > self.stats.max_request_time_ms:
            self.stats.max_request_time_ms = duration_ms
        
        # Store recent metrics (keep last 100)
        self.stats.recent_requests.append(metrics)
        if len(self.stats.recent_requests) > self.MAX_RECENT_METRICS:
            self.stats.recent_requests.pop(0)
        
        # Store per-endpoint stats
        self.endpoint_stats[f"{method} {path}"].append(duration_ms)
        if len(self.endpoint_stats[f"{method} {path}"]) > self.MAX_RECENT_METRICS:
            self.endpoint_stats[f"{method} {path}"].pop(0)
    
    def record_query(self, query: str, duration_ms: float):
        """
        Record database query metrics
        
        Args:
            query: SQL query (truncated for logging)
            duration_ms: Query duration in milliseconds
        """
        is_slow = duration_ms > self.SLOW_QUERY_THRESHOLD_MS
        
        # Truncate query for storage (first 100 chars)
        query_truncated = query[:100] + "..." if len(query) > 100 else query
        
        # Create metrics record
        metrics = QueryMetrics(
            query=query_truncated,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            is_slow=is_slow
        )
        
        # Update statistics
        self.stats.total_queries += 1
        if is_slow:
            self.stats.slow_queries += 1
            logger.warning(
                f"Slow database query detected: {query_truncated} took {duration_ms:.2f}ms "
                f"(threshold: {self.SLOW_QUERY_THRESHOLD_MS}ms)"
            )
        
        # Update averages
        total_time = self.stats.avg_query_time_ms * (self.stats.total_queries - 1) + duration_ms
        self.stats.avg_query_time_ms = total_time / self.stats.total_queries
        
        # Update max
        if duration_ms > self.stats.max_query_time_ms:
            self.stats.max_query_time_ms = duration_ms
        
        # Store recent metrics (keep last 100)
        self.stats.recent_queries.append(metrics)
        if len(self.stats.recent_queries) > self.MAX_RECENT_METRICS:
            self.stats.recent_queries.pop(0)
        
        # Extract query pattern (first word, usually SELECT/INSERT/UPDATE/DELETE)
        query_pattern = query.split()[0].upper() if query.split() else "UNKNOWN"
        self.query_patterns[query_pattern].append(duration_ms)
        if len(self.query_patterns[query_pattern]) > self.MAX_RECENT_METRICS:
            self.query_patterns[query_pattern].pop(0)
    
    def record_websocket_message(self, message_type: str, latency_ms: float):
        """
        Record WebSocket message latency
        
        Args:
            message_type: Type of WebSocket message
            latency_ms: Message latency in milliseconds
        """
        is_slow = latency_ms > self.SLOW_WS_THRESHOLD_MS
        
        # Create metrics record
        metrics = WebSocketMetrics(
            message_type=message_type,
            latency_ms=latency_ms,
            timestamp=datetime.utcnow(),
            is_slow=is_slow
        )
        
        # Update statistics
        self.stats.total_ws_messages += 1
        if is_slow:
            self.stats.slow_ws_messages += 1
            logger.warning(
                f"Slow WebSocket message detected: {message_type} took {latency_ms:.2f}ms "
                f"(threshold: {self.SLOW_WS_THRESHOLD_MS}ms)"
            )
        
        # Update averages
        total_time = self.stats.avg_ws_latency_ms * (self.stats.total_ws_messages - 1) + latency_ms
        self.stats.avg_ws_latency_ms = total_time / self.stats.total_ws_messages
        
        # Update max
        if latency_ms > self.stats.max_ws_latency_ms:
            self.stats.max_ws_latency_ms = latency_ms
        
        # Store recent metrics (keep last 100)
        self.stats.recent_ws_messages.append(metrics)
        if len(self.stats.recent_ws_messages) > self.MAX_RECENT_METRICS:
            self.stats.recent_ws_messages.pop(0)
    
    def get_stats(self) -> Dict:
        """
        Get current performance statistics
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            "requests": {
                "total": self.stats.total_requests,
                "slow_count": self.stats.slow_requests,
                "slow_percentage": (self.stats.slow_requests / self.stats.total_requests * 100) 
                    if self.stats.total_requests > 0 else 0.0,
                "avg_time_ms": round(self.stats.avg_request_time_ms, 2),
                "max_time_ms": round(self.stats.max_request_time_ms, 2),
                "threshold_ms": self.SLOW_REQUEST_THRESHOLD_MS
            },
            "queries": {
                "total": self.stats.total_queries,
                "slow_count": self.stats.slow_queries,
                "slow_percentage": (self.stats.slow_queries / self.stats.total_queries * 100) 
                    if self.stats.total_queries > 0 else 0.0,
                "avg_time_ms": round(self.stats.avg_query_time_ms, 2),
                "max_time_ms": round(self.stats.max_query_time_ms, 2),
                "threshold_ms": self.SLOW_QUERY_THRESHOLD_MS
            },
            "websocket": {
                "total_messages": self.stats.total_ws_messages,
                "slow_count": self.stats.slow_ws_messages,
                "slow_percentage": (self.stats.slow_ws_messages / self.stats.total_ws_messages * 100) 
                    if self.stats.total_ws_messages > 0 else 0.0,
                "avg_latency_ms": round(self.stats.avg_ws_latency_ms, 2),
                "max_latency_ms": round(self.stats.max_ws_latency_ms, 2),
                "threshold_ms": self.SLOW_WS_THRESHOLD_MS
            }
        }
    
    def get_endpoint_stats(self) -> Dict[str, Dict]:
        """
        Get per-endpoint performance statistics
        
        Returns:
            Dictionary mapping endpoints to their statistics
        """
        endpoint_summary = {}
        
        for endpoint, durations in self.endpoint_stats.items():
            if durations:
                endpoint_summary[endpoint] = {
                    "count": len(durations),
                    "avg_ms": round(sum(durations) / len(durations), 2),
                    "min_ms": round(min(durations), 2),
                    "max_ms": round(max(durations), 2),
                    "slow_count": sum(1 for d in durations if d > self.SLOW_REQUEST_THRESHOLD_MS)
                }
        
        return endpoint_summary
    
    def get_query_pattern_stats(self) -> Dict[str, Dict]:
        """
        Get per-query-pattern performance statistics
        
        Returns:
            Dictionary mapping query patterns to their statistics
        """
        pattern_summary = {}
        
        for pattern, durations in self.query_patterns.items():
            if durations:
                pattern_summary[pattern] = {
                    "count": len(durations),
                    "avg_ms": round(sum(durations) / len(durations), 2),
                    "min_ms": round(min(durations), 2),
                    "max_ms": round(max(durations), 2),
                    "slow_count": sum(1 for d in durations if d > self.SLOW_QUERY_THRESHOLD_MS)
                }
        
        return pattern_summary
    
    def get_recent_slow_requests(self, limit: int = 10) -> List[Dict]:
        """
        Get recent slow API requests
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of slow request metrics
        """
        slow_requests = [r for r in self.stats.recent_requests if r.is_slow]
        slow_requests.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "path": r.path,
                "method": r.method,
                "duration_ms": round(r.duration_ms, 2),
                "status_code": r.status_code,
                "timestamp": r.timestamp.isoformat()
            }
            for r in slow_requests[:limit]
        ]
    
    def get_recent_slow_queries(self, limit: int = 10) -> List[Dict]:
        """
        Get recent slow database queries
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of slow query metrics
        """
        slow_queries = [q for q in self.stats.recent_queries if q.is_slow]
        slow_queries.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "query": q.query,
                "duration_ms": round(q.duration_ms, 2),
                "timestamp": q.timestamp.isoformat()
            }
            for q in slow_queries[:limit]
        ]
    
    def reset_stats(self):
        """Reset all performance statistics"""
        self.stats = PerformanceStats()
        self.endpoint_stats.clear()
        self.query_patterns.clear()
        logger.info("Performance statistics reset")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for request timing
    
    Automatically tracks request duration and logs slow requests.
    Adds X-Response-Time header to all responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with timing
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response with X-Response-Time header
        """
        # Skip timing for WebSocket upgrade requests
        if request.headers.get("upgrade") == "websocket":
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        performance_monitor.record_request(
            path=request.url.path,
            method=request.method,
            duration_ms=duration_ms,
            status_code=response.status_code
        )
        
        # Add response time header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get global performance monitor instance
    
    Returns:
        PerformanceMonitor instance
    """
    return performance_monitor
