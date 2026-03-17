"""
Unit tests for SymbolPerformanceService

Tests per-symbol performance statistics calculation including:
- Win rate calculation per symbol
- Profit factor calculation per symbol
- Average and total PnL per symbol
- Best and worst trade identification
- Average hold time calculation
- Trade count per symbol
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from api.services.symbol_performance_service import SymbolPerformanceService


@pytest.fixture
def mock_database():
    """Create a mock database with test data"""
    db = Mock()
    conn = MagicMock()
    db._get_conn.return_value = conn
    return db, conn


@pytest.fixture
def service(mock_database):
    """Create service instance with mock database"""
    db, _ = mock_database
    return SymbolPerformanceService(database=db)


def test_get_symbol_performance_with_data(service, mock_database):
    """Test symbol performance calculation with valid data"""
    _, conn = mock_database
    
    # Mock database response with trades for two symbols
    now = datetime.utcnow()
    mock_rows = [
        # BTCUSDT trades
        {"symbol": "BTCUSDT", "outcome": "WIN", "pnl_pct": 5.0, "duration_minutes": 120, "closed_at": now.isoformat()},
        {"symbol": "BTCUSDT", "outcome": "WIN", "pnl_pct": 3.0, "duration_minutes": 180, "closed_at": now.isoformat()},
        {"symbol": "BTCUSDT", "outcome": "LOSS", "pnl_pct": -2.0, "duration_minutes": 90, "closed_at": now.isoformat()},
        # ETHUSDT trades
        {"symbol": "ETHUSDT", "outcome": "WIN", "pnl_pct": 4.0, "duration_minutes": 150, "closed_at": now.isoformat()},
        {"symbol": "ETHUSDT", "outcome": "LOSS", "pnl_pct": -3.0, "duration_minutes": 100, "closed_at": now.isoformat()},
    ]
    
    conn.execute.return_value.fetchall.return_value = mock_rows
    
    result = service.get_symbol_performance()
    
    # Verify result structure
    assert "symbols" in result
    assert len(result["symbols"]) == 2
    
    # Find BTCUSDT metrics (should be first due to higher total PnL)
    btc_metrics = next(s for s in result["symbols"] if s["symbol"] == "BTCUSDT")
    
    # Verify BTCUSDT metrics
    assert btc_metrics["totalTrades"] == 3
    assert btc_metrics["winRate"] == 66.67  # 2 wins out of 3 trades
    assert btc_metrics["profitFactor"] == 4.0  # (5.0 + 3.0) / abs(-2.0)
    assert btc_metrics["avgPnL"] == 2.0  # (5.0 + 3.0 - 2.0) / 3
    assert btc_metrics["totalPnL"] == 6.0  # 5.0 + 3.0 - 2.0
    assert btc_metrics["bestTrade"] == 5.0
    assert btc_metrics["worstTrade"] == -2.0
    assert btc_metrics["avgHoldTime"] == 130.0  # (120 + 180 + 90) / 3
    
    # Find ETHUSDT metrics
    eth_metrics = next(s for s in result["symbols"] if s["symbol"] == "ETHUSDT")
    
    # Verify ETHUSDT metrics
    assert eth_metrics["totalTrades"] == 2
    assert eth_metrics["winRate"] == 50.0  # 1 win out of 2 trades
    assert eth_metrics["profitFactor"] == 1.33  # 4.0 / abs(-3.0)
    assert eth_metrics["avgPnL"] == 0.5  # (4.0 - 3.0) / 2
    assert eth_metrics["totalPnL"] == 1.0  # 4.0 - 3.0
    assert eth_metrics["bestTrade"] == 4.0
    assert eth_metrics["worstTrade"] == -3.0
    assert eth_metrics["avgHoldTime"] == 125.0  # (150 + 100) / 2


def test_get_symbol_performance_empty_database(service, mock_database):
    """Test symbol performance with no trades"""
    _, conn = mock_database
    
    # Mock empty database response
    conn.execute.return_value.fetchall.return_value = []
    
    result = service.get_symbol_performance()
    
    # Verify empty result
    assert "symbols" in result
    assert len(result["symbols"]) == 0


def test_get_symbol_performance_all_wins(service, mock_database):
    """Test symbol performance with all winning trades"""
    _, conn = mock_database
    
    now = datetime.utcnow()
    mock_rows = [
        {"symbol": "BTCUSDT", "outcome": "WIN", "pnl_pct": 5.0, "duration_minutes": 120, "closed_at": now.isoformat()},
        {"symbol": "BTCUSDT", "outcome": "WIN", "pnl_pct": 3.0, "duration_minutes": 180, "closed_at": now.isoformat()},
    ]
    
    conn.execute.return_value.fetchall.return_value = mock_rows
    
    result = service.get_symbol_performance()
    
    btc_metrics = result["symbols"][0]
    assert btc_metrics["winRate"] == 100.0
    assert btc_metrics["profitFactor"] == 999.99  # Capped infinity value
    assert btc_metrics["totalPnL"] == 8.0


def test_get_symbol_performance_all_losses(service, mock_database):
    """Test symbol performance with all losing trades"""
    _, conn = mock_database
    
    now = datetime.utcnow()
    mock_rows = [
        {"symbol": "BTCUSDT", "outcome": "LOSS", "pnl_pct": -2.0, "duration_minutes": 90, "closed_at": now.isoformat()},
        {"symbol": "BTCUSDT", "outcome": "LOSS", "pnl_pct": -3.0, "duration_minutes": 100, "closed_at": now.isoformat()},
    ]
    
    conn.execute.return_value.fetchall.return_value = mock_rows
    
    result = service.get_symbol_performance()
    
    btc_metrics = result["symbols"][0]
    assert btc_metrics["winRate"] == 0.0
    assert btc_metrics["profitFactor"] == 0.0
    assert btc_metrics["totalPnL"] == -5.0


def test_get_service_status_with_data(service, mock_database):
    """Test service status with data available"""
    _, conn = mock_database
    
    # Mock status query response
    mock_row = {"symbol_count": 5, "trade_count": 42}
    conn.execute.return_value.fetchone.return_value = mock_row
    
    status = service.get_service_status()
    
    assert status["initialized"] is True
    assert status["symbol_count"] == 5
    assert status["trade_count"] == 42
    assert status["has_data"] is True


def test_get_service_status_empty(service, mock_database):
    """Test service status with no data"""
    _, conn = mock_database
    
    # Mock empty status query response
    mock_row = {"symbol_count": 0, "trade_count": 0}
    conn.execute.return_value.fetchone.return_value = mock_row
    
    status = service.get_service_status()
    
    assert status["initialized"] is True
    assert status["symbol_count"] == 0
    assert status["trade_count"] == 0
    assert status["has_data"] is False


def test_symbol_sorting_by_total_pnl(service, mock_database):
    """Test that symbols are sorted by total PnL descending"""
    _, conn = mock_database
    
    now = datetime.utcnow()
    mock_rows = [
        # ETHUSDT - lower total PnL
        {"symbol": "ETHUSDT", "outcome": "WIN", "pnl_pct": 2.0, "duration_minutes": 100, "closed_at": now.isoformat()},
        # BTCUSDT - higher total PnL
        {"symbol": "BTCUSDT", "outcome": "WIN", "pnl_pct": 10.0, "duration_minutes": 120, "closed_at": now.isoformat()},
    ]
    
    conn.execute.return_value.fetchall.return_value = mock_rows
    
    result = service.get_symbol_performance()
    
    # Verify BTCUSDT is first (higher total PnL)
    assert result["symbols"][0]["symbol"] == "BTCUSDT"
    assert result["symbols"][1]["symbol"] == "ETHUSDT"


def test_missing_duration_handling(service, mock_database):
    """Test handling of trades with missing duration"""
    _, conn = mock_database
    
    now = datetime.utcnow()
    mock_rows = [
        {"symbol": "BTCUSDT", "outcome": "WIN", "pnl_pct": 5.0, "duration_minutes": 120, "closed_at": now.isoformat()},
        {"symbol": "BTCUSDT", "outcome": "WIN", "pnl_pct": 3.0, "duration_minutes": None, "closed_at": now.isoformat()},
    ]
    
    conn.execute.return_value.fetchall.return_value = mock_rows
    
    result = service.get_symbol_performance()
    
    btc_metrics = result["symbols"][0]
    # Should only average the non-None duration
    assert btc_metrics["avgHoldTime"] == 120.0
