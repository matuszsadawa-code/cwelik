"""
Unit tests for Market Data Service

Tests the market data fetching, CVD calculation, and WebSocket broadcasting.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from api.services.market_data_service import MarketDataService
from api.services.websocket_manager import ConnectionManager


@pytest.fixture
def connection_manager():
    """Create a mock connection manager."""
    manager = Mock(spec=ConnectionManager)
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def market_data_service(connection_manager):
    """Create a market data service instance with test symbols."""
    test_symbols = ["BTCUSDT", "ETHUSDT"]
    service = MarketDataService(connection_manager, symbols=test_symbols)
    return service


@pytest.mark.asyncio
async def test_service_initialization(market_data_service):
    """Test that service initializes correctly."""
    assert market_data_service.running is False
    assert len(market_data_service.symbols) == 2
    assert "BTCUSDT" in market_data_service.symbols
    assert "ETHUSDT" in market_data_service.symbols
    assert len(market_data_service.market_data) == 0
    assert len(market_data_service.cvd) == 0


@pytest.mark.asyncio
async def test_cvd_calculation(market_data_service):
    """Test CVD calculation from trades."""
    symbol = "BTCUSDT"
    
    # Mock trades: 3 buys, 2 sells
    trades = [
        {"id": "1", "size": 1.0, "side": "BUY", "price": 50000},
        {"id": "2", "size": 0.5, "side": "SELL", "price": 50000},
        {"id": "3", "size": 2.0, "side": "BUY", "price": 50000},
        {"id": "4", "size": 1.5, "side": "SELL", "price": 50000},
        {"id": "5", "size": 1.0, "side": "BUY", "price": 50000},
    ]
    
    # Calculate CVD delta
    delta = market_data_service._calculate_cvd_delta(symbol, trades)
    
    # Expected: (1.0 + 2.0 + 1.0) - (0.5 + 1.5) = 4.0 - 2.0 = 2.0
    assert delta == 2.0
    
    # Update CVD
    market_data_service.cvd[symbol] += delta
    assert market_data_service.get_cvd(symbol) == 2.0


@pytest.mark.asyncio
async def test_cvd_incremental_update(market_data_service):
    """Test that CVD only processes new trades."""
    symbol = "BTCUSDT"
    
    # First batch of trades
    trades1 = [
        {"id": "1", "size": 1.0, "side": "BUY", "price": 50000},
        {"id": "2", "size": 0.5, "side": "SELL", "price": 50000},
    ]
    
    delta1 = market_data_service._calculate_cvd_delta(symbol, trades1)
    market_data_service.cvd[symbol] += delta1
    
    # Expected: 1.0 - 0.5 = 0.5
    assert market_data_service.get_cvd(symbol) == 0.5
    
    # Second batch with overlapping trades (should only process new ones)
    trades2 = [
        {"id": "1", "size": 1.0, "side": "BUY", "price": 50000},  # Already processed
        {"id": "2", "size": 0.5, "side": "SELL", "price": 50000},  # Already processed
        {"id": "3", "size": 2.0, "side": "BUY", "price": 50000},  # New
    ]
    
    delta2 = market_data_service._calculate_cvd_delta(symbol, trades2)
    market_data_service.cvd[symbol] += delta2
    
    # Expected: 0.5 + 2.0 = 2.5
    assert market_data_service.get_cvd(symbol) == 2.5


@pytest.mark.asyncio
async def test_cvd_reset(market_data_service):
    """Test CVD reset functionality."""
    symbol = "BTCUSDT"
    
    # Set some CVD value
    market_data_service.cvd[symbol] = 10.5
    market_data_service.last_trade_id[symbol] = "123"
    
    # Reset
    market_data_service.reset_cvd(symbol)
    
    # Verify reset
    assert market_data_service.get_cvd(symbol) == 0.0
    assert symbol not in market_data_service.last_trade_id


@pytest.mark.asyncio
async def test_get_market_data(market_data_service):
    """Test getting cached market data."""
    symbol = "BTCUSDT"
    
    # Add some market data
    market_data_service.market_data[symbol] = {
        "symbol": symbol,
        "price": 50000,
        "volume24h": 1000,
        "change24h": 2.5,
        "cvd": 10.0
    }
    
    # Get data
    data = market_data_service.get_market_data(symbol)
    
    assert data is not None
    assert data["symbol"] == symbol
    assert data["price"] == 50000
    assert data["cvd"] == 10.0


@pytest.mark.asyncio
async def test_get_all_market_data(market_data_service):
    """Test getting all market data."""
    # Add data for multiple symbols
    market_data_service.market_data["BTCUSDT"] = {"symbol": "BTCUSDT", "price": 50000}
    market_data_service.market_data["ETHUSDT"] = {"symbol": "ETHUSDT", "price": 3000}
    
    # Get all data
    all_data = market_data_service.get_all_market_data()
    
    assert len(all_data) == 2
    assert "BTCUSDT" in all_data
    assert "ETHUSDT" in all_data


@pytest.mark.asyncio
async def test_service_status(market_data_service):
    """Test service status reporting."""
    # Add some data
    market_data_service.market_data["BTCUSDT"] = {"symbol": "BTCUSDT", "price": 50000}
    market_data_service.cvd["BTCUSDT"] = 10.0
    market_data_service.error_counts["ETHUSDT"] = 3
    
    status = market_data_service.get_service_status()
    
    assert status["running"] is False  # Not started yet
    assert status["symbols_monitored"] == 2
    assert status["symbols_with_data"] == 1
    assert status["symbols_with_errors"] == 1
    assert status["total_errors"] == 3
    assert status["cvd_tracked_symbols"] == 1


@pytest.mark.asyncio
async def test_broadcast_market_data(market_data_service, connection_manager):
    """Test WebSocket broadcasting."""
    symbol = "BTCUSDT"
    data = {
        "symbol": symbol,
        "price": 50000,
        "volume24h": 1000,
        "change24h": 2.5,
        "bidAskSpread": 0.5,
        "cvd": 10.0,
        "timestamp": 1234567890
    }
    
    # Broadcast
    await market_data_service._broadcast_market_data(symbol, data)
    
    # Verify broadcast was called
    connection_manager.broadcast.assert_called_once()
    
    # Check message format
    call_args = connection_manager.broadcast.call_args
    message = call_args[0][0]
    channel = call_args[1]["channel"]
    
    assert message["type"] == "market_data_update"
    assert message["data"]["symbol"] == symbol
    assert message["data"]["price"] == 50000
    assert message["data"]["cvd"] == 10.0
    assert channel == "market_data"


@pytest.mark.asyncio
async def test_error_circuit_breaker(market_data_service):
    """Test that symbols with too many errors are skipped."""
    symbol = "BTCUSDT"
    
    # Simulate multiple errors
    for i in range(6):
        market_data_service.error_counts[symbol] += 1
    
    # Symbol should be skipped now
    assert market_data_service.error_counts[symbol] >= market_data_service.max_errors_before_skip


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
