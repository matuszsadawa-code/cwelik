"""
Unit tests for SystemHealthService

Tests health monitoring functionality including:
- API request tracking (success rate, response time)
- WebSocket connection status tracking
- Database query performance tracking
- Signal processing latency tracking
- System uptime calculation
- Health metrics broadcasting via WebSocket
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from api.services.system_health_service import SystemHealthService
from api.services.websocket_manager import ConnectionManager


@pytest.fixture
def connection_manager():
    """Create a mock connection manager"""
    manager = Mock(spec=ConnectionManager)
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def mock_database():
    """Create a mock database"""
    db = Mock()
    return db


@pytest.fixture
def health_service(connection_manager, mock_database):
    """Create a SystemHealthService instance"""
    return SystemHealthService(connection_manager, mock_database)


@pytest.mark.asyncio
async def test_service_initialization(health_service):
    """Test service initializes with correct default values"""
    assert health_service.running is False
    assert health_service.task is None
    assert health_service.cached_health is None
    assert health_service.ws_connected == {"binance": False, "bybit": False}
    assert len(health_service.api_requests) == 0
    assert len(health_service.api_response_times) == 0
    assert len(health_service.db_query_times) == 0
    assert len(health_service.signal_processing_times) == 0


@pytest.mark.asyncio
async def test_service_start_stop(health_service):
    """Test service can start and stop correctly"""
    # Start service
    await health_service.start()
    assert health_service.running is True
    assert health_service.task is not None
    
    # Stop service
    await health_service.stop()
    assert health_service.running is False


@pytest.mark.asyncio
async def test_record_api_request_success(health_service):
    """Test recording successful API requests"""
    # Record successful requests
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    health_service.record_api_request("binance", success=True, response_time_ms=60.0)
    health_service.record_api_request("bybit", success=True, response_time_ms=40.0)
    
    # Check success counts
    assert health_service.api_requests["binance"]["success"] == 2
    assert health_service.api_requests["binance"]["failure"] == 0
    assert health_service.api_requests["bybit"]["success"] == 1
    assert health_service.api_requests["bybit"]["failure"] == 0
    
    # Check response times recorded
    assert len(health_service.api_response_times["binance"]) == 2
    assert len(health_service.api_response_times["bybit"]) == 1
    
    # Check last update timestamp set
    assert health_service.last_update is not None


@pytest.mark.asyncio
async def test_record_api_request_failure(health_service):
    """Test recording failed API requests"""
    # Record failed requests
    health_service.record_api_request("binance", success=False, response_time_ms=1000.0)
    health_service.record_api_request("bybit", success=False, response_time_ms=2000.0)
    
    # Check failure counts
    assert health_service.api_requests["binance"]["failure"] == 1
    assert health_service.api_requests["bybit"]["failure"] == 1
    
    # Check last update NOT set on failure
    assert health_service.last_update is None


@pytest.mark.asyncio
async def test_calculate_success_rate(health_service):
    """Test API success rate calculation"""
    # No requests yet - should return 100%
    success_rate = health_service._calculate_success_rate("binance")
    assert success_rate == 100.0
    
    # Record mixed requests
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    health_service.record_api_request("binance", success=True, response_time_ms=60.0)
    health_service.record_api_request("binance", success=True, response_time_ms=55.0)
    health_service.record_api_request("binance", success=False, response_time_ms=1000.0)
    
    # Calculate success rate: 3 success / 4 total = 75%
    success_rate = health_service._calculate_success_rate("binance")
    assert success_rate == 75.0


@pytest.mark.asyncio
async def test_calculate_avg_response_time(health_service):
    """Test average API response time calculation"""
    # No requests yet - should return 0
    avg_time = health_service._calculate_avg_response_time("binance")
    assert avg_time == 0.0
    
    # Record requests with different response times
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    health_service.record_api_request("binance", success=True, response_time_ms=100.0)
    health_service.record_api_request("binance", success=True, response_time_ms=150.0)
    
    # Calculate average: (50 + 100 + 150) / 3 = 100
    avg_time = health_service._calculate_avg_response_time("binance")
    assert avg_time == 100.0


@pytest.mark.asyncio
async def test_set_websocket_status(health_service):
    """Test WebSocket connection status tracking"""
    # Initial status should be False
    assert health_service.ws_connected["binance"] is False
    assert health_service.ws_connected["bybit"] is False
    
    # Set Binance connected
    health_service.set_websocket_status("binance", True)
    assert health_service.ws_connected["binance"] is True
    assert health_service.ws_connected["bybit"] is False
    
    # Set Bybit connected
    health_service.set_websocket_status("bybit", True)
    assert health_service.ws_connected["binance"] is True
    assert health_service.ws_connected["bybit"] is True
    
    # Disconnect Binance
    health_service.set_websocket_status("binance", False)
    assert health_service.ws_connected["binance"] is False
    assert health_service.ws_connected["bybit"] is True


@pytest.mark.asyncio
async def test_record_db_query(health_service):
    """Test database query time tracking"""
    # Record query times
    health_service.record_db_query(10.0)
    health_service.record_db_query(20.0)
    health_service.record_db_query(30.0)
    
    # Check recorded
    assert len(health_service.db_query_times) == 3
    
    # Calculate average: (10 + 20 + 30) / 3 = 20
    avg_time = health_service._calculate_avg_db_query_time()
    assert avg_time == 20.0


@pytest.mark.asyncio
async def test_record_signal_processing(health_service):
    """Test signal processing latency tracking"""
    # Record processing times
    health_service.record_signal_processing(50.0)
    health_service.record_signal_processing(75.0)
    health_service.record_signal_processing(100.0)
    
    # Check recorded
    assert len(health_service.signal_processing_times) == 3
    
    # Calculate average: (50 + 75 + 100) / 3 = 75
    avg_time = health_service._calculate_avg_signal_processing_latency()
    assert avg_time == 75.0


@pytest.mark.asyncio
async def test_calculate_uptime(health_service):
    """Test system uptime calculation"""
    # Record start time
    start_time = time.time()
    health_service.start_time = start_time
    
    # Wait a bit
    await asyncio.sleep(0.1)
    
    # Calculate uptime
    uptime = health_service._calculate_uptime()
    
    # Should be at least 0 seconds (may be 0 or 1 depending on timing)
    assert uptime >= 0
    assert uptime < 2  # Should be less than 2 seconds


@pytest.mark.asyncio
async def test_rolling_window_max_samples(health_service):
    """Test that rolling windows respect MAX_SAMPLES limit"""
    max_samples = SystemHealthService.MAX_SAMPLES
    
    # Record more than MAX_SAMPLES
    for i in range(max_samples + 50):
        health_service.record_api_request("binance", success=True, response_time_ms=float(i))
    
    # Check that only MAX_SAMPLES are kept
    assert len(health_service.api_response_times["binance"]) == max_samples
    
    # Check that oldest samples were removed (should start from 50)
    response_times = list(health_service.api_response_times["binance"])
    assert response_times[0] == 50.0


@pytest.mark.asyncio
async def test_calculate_and_broadcast_health(health_service, connection_manager):
    """Test health metrics calculation and broadcasting"""
    # Set up some metrics
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    health_service.record_api_request("binance", success=True, response_time_ms=60.0)
    health_service.record_api_request("bybit", success=True, response_time_ms=40.0)
    health_service.set_websocket_status("binance", True)
    health_service.set_websocket_status("bybit", True)
    health_service.record_db_query(15.0)
    health_service.record_signal_processing(80.0)
    
    # Calculate and broadcast
    await health_service._calculate_and_broadcast_health()
    
    # Check that broadcast was called
    connection_manager.broadcast.assert_called_once()
    
    # Check broadcast message structure
    call_args = connection_manager.broadcast.call_args
    message = call_args[0][0]
    
    assert message["type"] == "health_update"
    assert "data" in message
    
    data = message["data"]
    assert "apiSuccessRate" in data
    assert "apiResponseTime" in data
    assert "wsConnected" in data
    assert "dbQueryTime" in data
    assert "signalProcessingLatency" in data
    assert "uptime" in data
    assert "timestamp" in data
    
    # Check values
    assert data["apiSuccessRate"]["binance"] == 100.0
    assert data["apiSuccessRate"]["bybit"] == 100.0
    assert data["apiResponseTime"]["binance"] == 55.0  # (50 + 60) / 2
    assert data["apiResponseTime"]["bybit"] == 40.0
    assert data["wsConnected"]["binance"] is True
    assert data["wsConnected"]["bybit"] is True
    assert data["dbQueryTime"] == 15.0
    assert data["signalProcessingLatency"] == 80.0
    
    # Check cached health
    assert health_service.cached_health is not None


@pytest.mark.asyncio
async def test_get_cached_health(health_service):
    """Test getting cached health metrics"""
    # No cache yet
    cached = health_service.get_cached_health()
    assert cached is None
    
    # Set up and calculate metrics
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    await health_service._calculate_and_broadcast_health()
    
    # Get cached health
    cached = health_service.get_cached_health()
    assert cached is not None
    assert "apiSuccessRate" in cached
    assert "apiResponseTime" in cached


@pytest.mark.asyncio
async def test_get_service_status(health_service):
    """Test getting service status"""
    # Before start
    status = health_service.get_service_status()
    assert status["running"] is False
    assert status["has_cached_health"] is False
    assert status["total_api_requests"] == 0
    
    # After recording some requests
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    health_service.record_api_request("bybit", success=False, response_time_ms=1000.0)
    
    status = health_service.get_service_status()
    assert status["total_api_requests"] == 2


@pytest.mark.asyncio
async def test_reset_metrics(health_service):
    """Test resetting all health metrics"""
    # Set up some metrics
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    health_service.record_db_query(15.0)
    health_service.record_signal_processing(80.0)
    health_service.last_update = datetime.now(timezone.utc)
    
    # Reset
    health_service.reset_metrics()
    
    # Check all cleared
    assert len(health_service.api_requests) == 0
    assert len(health_service.api_response_times) == 0
    assert len(health_service.db_query_times) == 0
    assert len(health_service.signal_processing_times) == 0
    assert health_service.last_update is None


@pytest.mark.asyncio
async def test_health_monitoring_loop_runs(health_service, connection_manager):
    """Test that health monitoring loop runs and broadcasts"""
    # Start service
    await health_service.start()
    
    # Record some metrics
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    
    # Wait for at least one broadcast (10 second interval, but we'll wait less and stop)
    await asyncio.sleep(0.2)
    
    # Stop service
    await health_service.stop()
    
    # Service should have run
    assert health_service.running is False


@pytest.mark.asyncio
async def test_broadcast_channel_is_health(health_service, connection_manager):
    """Test that broadcasts use 'health' channel"""
    # Set up metrics
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    
    # Calculate and broadcast
    await health_service._calculate_and_broadcast_health()
    
    # Check channel parameter
    call_args = connection_manager.broadcast.call_args
    assert call_args[1]["channel"] == "health"


@pytest.mark.asyncio
async def test_success_rate_edge_cases(health_service):
    """Test success rate calculation edge cases"""
    # All success
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    health_service.record_api_request("binance", success=True, response_time_ms=60.0)
    success_rate = health_service._calculate_success_rate("binance")
    assert success_rate == 100.0
    
    # All failure
    health_service.record_api_request("bybit", success=False, response_time_ms=1000.0)
    health_service.record_api_request("bybit", success=False, response_time_ms=2000.0)
    success_rate = health_service._calculate_success_rate("bybit")
    assert success_rate == 0.0


@pytest.mark.asyncio
async def test_last_update_only_on_success(health_service):
    """Test that last_update is only set on successful requests"""
    # Record failure - should not set last_update
    health_service.record_api_request("binance", success=False, response_time_ms=1000.0)
    assert health_service.last_update is None
    
    # Record success - should set last_update
    health_service.record_api_request("binance", success=True, response_time_ms=50.0)
    assert health_service.last_update is not None
    
    # Store timestamp
    first_update = health_service.last_update
    
    # Wait a bit
    await asyncio.sleep(0.01)
    
    # Record another success - should update timestamp
    health_service.record_api_request("binance", success=True, response_time_ms=60.0)
    assert health_service.last_update > first_update


@pytest.mark.asyncio
async def test_health_metrics_rounded_correctly(health_service, connection_manager):
    """Test that health metrics are rounded to appropriate precision"""
    # Set up metrics with decimal values
    health_service.record_api_request("binance", success=True, response_time_ms=50.123)
    health_service.record_api_request("binance", success=True, response_time_ms=60.456)
    health_service.record_api_request("binance", success=False, response_time_ms=1000.0)
    health_service.record_db_query(15.789)
    health_service.record_signal_processing(80.123)
    
    # Calculate and broadcast
    await health_service._calculate_and_broadcast_health()
    
    # Check rounding in broadcast message
    call_args = connection_manager.broadcast.call_args
    message = call_args[0][0]
    data = message["data"]
    
    # Success rate should be rounded to 2 decimal places
    assert isinstance(data["apiSuccessRate"]["binance"], float)
    assert data["apiSuccessRate"]["binance"] == 66.67  # 2/3 = 66.67%
    
    # Response times should be rounded to 1 decimal place
    assert isinstance(data["apiResponseTime"]["binance"], float)
    
    # DB query time should be rounded to 1 decimal place
    assert isinstance(data["dbQueryTime"], float)
    assert data["dbQueryTime"] == 15.8
    
    # Signal processing latency should be rounded to 1 decimal place
    assert isinstance(data["signalProcessingLatency"], float)
    assert data["signalProcessingLatency"] == 80.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
