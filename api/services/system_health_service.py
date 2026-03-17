"""
System Health Service for OpenClaw Trading Dashboard

Monitors system health metrics including exchange API connectivity, database performance,
and signal processing latency. Broadcasts health updates via WebSocket every 10 seconds.

Features:
- Track API request success rate for each exchange (Binance, Bybit)
- Track average API response time for each exchange
- Track WebSocket connection status for each exchange
- Track database query performance (average query time)
- Track signal processing latency
- Calculate system uptime from service start time
- Broadcast health_update messages every 10 seconds via WebSocket
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import deque, defaultdict

from api.services.websocket_manager import ConnectionManager
from storage.database import Database

logger = logging.getLogger(__name__)


class SystemHealthService:
    """
    Service for monitoring system health metrics.
    
    Responsibilities:
    - Track API request success/failure counts per exchange
    - Calculate API success rate: (successful requests / total requests) × 100
    - Track API response times and calculate averages per exchange
    - Monitor WebSocket connection status for each exchange
    - Track database query execution times
    - Track signal processing latency (time to process signals)
    - Calculate system uptime from service start time
    - Broadcast health_update messages every 10 seconds via WebSocket
    """
    
    # Maximum number of samples to keep for rolling averages
    MAX_SAMPLES = 100
    
    def __init__(self, connection_manager: ConnectionManager, database: Database = None):
        """
        Initialize system health service.
        
        Args:
            connection_manager: WebSocket connection manager for broadcasting
            database: Database instance (creates new if None)
        """
        self.connection_manager = connection_manager
        self.database = database or Database()
        
        # Service start time for uptime calculation
        self.start_time = time.time()
        
        # API metrics per exchange
        # Format: {exchange: {"success": count, "failure": count}}
        self.api_requests: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        
        # API response times per exchange (rolling window)
        # Format: {exchange: deque([response_time_ms, ...])}
        self.api_response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.MAX_SAMPLES))
        
        # WebSocket connection status per exchange
        # Format: {exchange: bool}
        self.ws_connected: Dict[str, bool] = {
            "binance": False,
            "bybit": False,
        }
        
        # Database query times (rolling window)
        self.db_query_times: deque = deque(maxlen=self.MAX_SAMPLES)
        
        # Signal processing latency (rolling window)
        self.signal_processing_times: deque = deque(maxlen=self.MAX_SAMPLES)
        
        # Last successful data update timestamp
        self.last_update: Optional[datetime] = None
        
        # Service state
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Cached health metrics
        self.cached_health: Optional[Dict] = None
        
        logger.info("SystemHealthService initialized")
    
    async def start(self):
        """Start the system health service background task."""
        if self.running:
            logger.warning("SystemHealthService already running")
            return
        
        self.running = True
        self.start_time = time.time()  # Reset start time
        
        # Start background task
        self.task = asyncio.create_task(self._health_monitoring_loop())
        
        logger.info("SystemHealthService started")
    
    async def stop(self):
        """Stop the system health service and cleanup."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel background task
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("SystemHealthService stopped")
    
    async def _health_monitoring_loop(self):
        """
        Background task: Calculate and broadcast health metrics every 10 seconds.
        
        Aggregates all health metrics and broadcasts health_update messages.
        """
        logger.info("Health monitoring loop started (10s interval)")
        
        while self.running:
            try:
                await self._calculate_and_broadcast_health()
                await asyncio.sleep(10.0)  # 10 second interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(10.0)  # Continue on error
    
    async def _calculate_and_broadcast_health(self):
        """
        Calculate all health metrics and broadcast via WebSocket.
        
        Calculates success rates, average response times, and broadcasts
        health_update message to all connected clients.
        """
        try:
            # Calculate API success rates
            api_success_rate = {}
            for exchange in ["binance", "bybit"]:
                success_rate = self._calculate_success_rate(exchange)
                api_success_rate[exchange] = success_rate
            
            # Calculate average API response times
            api_response_time = {}
            for exchange in ["binance", "bybit"]:
                avg_response_time = self._calculate_avg_response_time(exchange)
                api_response_time[exchange] = avg_response_time
            
            # Get WebSocket connection status
            ws_connected = self.ws_connected.copy()
            
            # Calculate average database query time
            db_query_time = self._calculate_avg_db_query_time()
            
            # Calculate average signal processing latency
            signal_processing_latency = self._calculate_avg_signal_processing_latency()
            
            # Calculate system uptime
            uptime = self._calculate_uptime()
            
            # Get last update timestamp
            last_update = int(self.last_update.timestamp() * 1000) if self.last_update else None
            
            # Build health metrics
            health = {
                "apiSuccessRate": api_success_rate,
                "apiResponseTime": api_response_time,
                "wsConnected": ws_connected,
                "dbQueryTime": db_query_time,
                "signalProcessingLatency": signal_processing_latency,
                "lastUpdate": last_update,
                "uptime": uptime,
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            
            # Cache health metrics
            self.cached_health = health
            
            # Broadcast to WebSocket clients
            await self._broadcast_health(health)
            
            logger.debug(
                f"Health metrics: Binance={api_success_rate.get('binance', 0):.1f}% "
                f"({api_response_time.get('binance', 0):.0f}ms), "
                f"Bybit={api_success_rate.get('bybit', 0):.1f}% "
                f"({api_response_time.get('bybit', 0):.0f}ms), "
                f"DB={db_query_time:.1f}ms"
            )
            
        except Exception as e:
            logger.error(f"Error calculating health metrics: {e}", exc_info=True)
    
    def _calculate_success_rate(self, exchange: str) -> float:
        """
        Calculate API success rate for an exchange.
        
        Success Rate = (successful requests / total requests) × 100
        
        Args:
            exchange: Exchange name (binance, bybit)
            
        Returns:
            float: Success rate as percentage (0-100)
        """
        metrics = self.api_requests[exchange]
        success = metrics["success"]
        failure = metrics["failure"]
        total = success + failure
        
        if total == 0:
            return 100.0  # No requests yet, assume healthy
        
        return (success / total) * 100
    
    def _calculate_avg_response_time(self, exchange: str) -> float:
        """
        Calculate average API response time for an exchange.
        
        Args:
            exchange: Exchange name (binance, bybit)
            
        Returns:
            float: Average response time in milliseconds
        """
        times = self.api_response_times[exchange]
        
        if not times:
            return 0.0
        
        return sum(times) / len(times)
    
    def _calculate_avg_db_query_time(self) -> float:
        """
        Calculate average database query time.
        
        Returns:
            float: Average query time in milliseconds
        """
        if not self.db_query_times:
            return 0.0
        
        return sum(self.db_query_times) / len(self.db_query_times)
    
    def _calculate_avg_signal_processing_latency(self) -> float:
        """
        Calculate average signal processing latency.
        
        Returns:
            float: Average processing time in milliseconds
        """
        if not self.signal_processing_times:
            return 0.0
        
        return sum(self.signal_processing_times) / len(self.signal_processing_times)
    
    def _calculate_uptime(self) -> int:
        """
        Calculate system uptime in seconds.
        
        Returns:
            int: Uptime in seconds since service start
        """
        return int(time.time() - self.start_time)
    
    async def _broadcast_health(self, health: Dict):
        """
        Broadcast health update to all WebSocket clients.
        
        Args:
            health: Health metrics dictionary
        """
        message = {
            "type": "health_update",
            "data": {
                "apiSuccessRate": {
                    "binance": round(health["apiSuccessRate"]["binance"], 2),
                    "bybit": round(health["apiSuccessRate"]["bybit"], 2),
                },
                "apiResponseTime": {
                    "binance": round(health["apiResponseTime"]["binance"], 1),
                    "bybit": round(health["apiResponseTime"]["bybit"], 1),
                },
                "wsConnected": health["wsConnected"],
                "dbQueryTime": round(health["dbQueryTime"], 1),
                "signalProcessingLatency": round(health["signalProcessingLatency"], 1),
                "lastUpdate": health["lastUpdate"],
                "uptime": health["uptime"],
                "timestamp": health["timestamp"],
            }
        }
        
        # Broadcast to all clients subscribed to health channel
        await self.connection_manager.broadcast(message, channel="health")
    
    # Public methods for tracking metrics
    
    def record_api_request(self, exchange: str, success: bool, response_time_ms: float):
        """
        Record an API request result.
        
        Args:
            exchange: Exchange name (binance, bybit)
            success: Whether the request succeeded
            response_time_ms: Response time in milliseconds
        """
        # Update success/failure counts
        if success:
            self.api_requests[exchange]["success"] += 1
        else:
            self.api_requests[exchange]["failure"] += 1
        
        # Record response time
        self.api_response_times[exchange].append(response_time_ms)
        
        # Update last successful update timestamp
        if success:
            self.last_update = datetime.now(timezone.utc)
    
    def set_websocket_status(self, exchange: str, connected: bool):
        """
        Update WebSocket connection status for an exchange.
        
        Args:
            exchange: Exchange name (binance, bybit)
            connected: Whether WebSocket is connected
        """
        self.ws_connected[exchange] = connected
        logger.info(f"WebSocket status updated: {exchange} = {connected}")
    
    def record_db_query(self, query_time_ms: float):
        """
        Record a database query execution time.
        
        Args:
            query_time_ms: Query execution time in milliseconds
        """
        self.db_query_times.append(query_time_ms)
    
    def record_signal_processing(self, processing_time_ms: float):
        """
        Record signal processing latency.
        
        Args:
            processing_time_ms: Processing time in milliseconds
        """
        self.signal_processing_times.append(processing_time_ms)
    
    def get_cached_health(self) -> Optional[Dict]:
        """
        Get cached health metrics.
        
        Returns:
            dict: Cached health metrics or None if not available
        """
        return self.cached_health.copy() if self.cached_health else None
    
    def get_service_status(self) -> Dict:
        """
        Get service status for health monitoring.
        
        Returns:
            dict: Service status including running state and uptime
        """
        return {
            "running": self.running,
            "uptime_seconds": self._calculate_uptime(),
            "has_cached_health": self.cached_health is not None,
            "total_api_requests": sum(
                self.api_requests[ex]["success"] + self.api_requests[ex]["failure"]
                for ex in ["binance", "bybit"]
            ),
        }
    
    def reset_metrics(self):
        """Reset all health metrics (useful for testing)."""
        self.api_requests.clear()
        self.api_response_times.clear()
        self.db_query_times.clear()
        self.signal_processing_times.clear()
        self.last_update = None
        logger.info("Health metrics reset")
